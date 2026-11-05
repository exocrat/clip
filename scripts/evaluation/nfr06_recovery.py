"""Exact-plan-gated ECS task-loss observer for NFR-06; never runs by import."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import time
from typing import Any, Callable, cast
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from scripts.evaluation.observer_journal import record as _record_observation

from scripts.evaluation.k6.real_target_preflight import (
    check_session_identity,
    inspect_target,
    validate_plan as validate_shared_target_plan,
)

COOKIE = re.compile(r"__Host-clip_session=[A-Za-z0-9._~+/=-]{1,2048}\Z")
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}\Z")
AWS_ID = re.compile(r"^[0-9]{12}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ARN = re.compile(r"^arn:aws:[a-z0-9-]+:[a-z0-9-]*:[0-9]{12}:.+$")
REGION = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+(?:-[a-z]+)?-\d$")


def _safe(value: Any, pattern: re.Pattern[str], code: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(code)
    return value


def validate_plan(plan: Any) -> dict[str, Any]:
    """Refuse partial, non-HTTPS, or unbounded run plans before AWS/session use."""
    if (
        not isinstance(plan, dict)
        or plan.get("nfr_id") != "nfr-06"
        or plan.get("execution_permitted") is not True
        or plan.get("nfr_accepted") is not False
    ):
        raise ValueError("approved_nfr06_plan_required")
    _safe(plan.get("run_id"), RUN_ID, "invalid_run_id")
    _safe(plan.get("account_id"), AWS_ID, "invalid_account_id")
    _safe(plan.get("cluster_arn"), ARN, "invalid_cluster_arn")
    _safe(plan.get("service_arn"), ARN, "invalid_service_arn")
    _safe(plan.get("task_arn"), ARN, "invalid_task_arn")
    _safe(plan.get("target_group_arn"), ARN, "invalid_target_group_arn")
    if (
        plan.get("configuration") not in {"A", "B"}
        or not isinstance(plan.get("region"), str)
        or not REGION.fullmatch(plan["region"])
    ):
        raise ValueError("invalid_nfr06_target")
    if (
        type(plan.get("desired_count")) is not int
        or plan["desired_count"] < 2
        or plan["desired_count"] > 10
    ):
        raise ValueError("invalid_configured_capacity")
    if (
        plan.get("baseline_seconds") != 60
        or plan.get("rate_rps") != 1
        or plan.get("recovery_deadline_seconds") != 240
        or plan.get("observation_seconds") != 300
        or plan.get("request_timeout_seconds") != 5
    ):
        raise ValueError("nfr06_schedule_mismatch")
    origin = urlsplit(plan.get("target_origin", ""))
    if (
        origin.scheme != "https"
        or not origin.hostname
        or origin.username
        or origin.password
        or origin.path
        or origin.query
        or origin.fragment
    ):
        raise ValueError("https_target_required")
    for key in ("listing_read_path", "ecs_read_path"):
        path = plan.get(key)
        if not isinstance(path, str) or not path.startswith("/api/") or "#" in path:
            raise ValueError("invalid_nfr06_read_path")
    _safe(
        plan.get("session_secret_reference"),
        re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$"),
        "invalid_session_reference",
    )
    _safe(plan.get("target_manifest_sha256"), SHA256, "invalid_target_manifest_hash")
    _safe(
        plan.get("target_plan_path"),
        re.compile(r"^[A-Za-z0-9_./-]{1,512}$"),
        "invalid_target_plan_path",
    )
    _safe(
        plan.get("expected_user_id"),
        re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        ),
        "invalid_expected_test_user",
    )
    return plan


def _load_target_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Verify the shared A/B target plan hash and bind it to the recovery plan."""
    root = Path(__file__).resolve().parents[2]
    relative = Path(plan["target_plan_path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe_target_plan_path")
    path = root / relative
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("target_plan_symlink")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not os.path.isfile(path) or info.st_size > 100_000:
            raise ValueError("invalid_target_plan_file")
        raw = os.read(descriptor, 100_001)
    finally:
        os.close(descriptor)
    if (
        len(raw) > 100_000
        or hashlib.sha256(raw).hexdigest() != plan["target_manifest_sha256"]
    ):
        raise ValueError("target_plan_hash_mismatch")
    target = validate_shared_target_plan(json.loads(raw))
    resources = target["resources"]
    if (
        target["run_id"] != plan["run_id"]
        or target["configuration"] != plan["configuration"]
        or target["account_id"] != plan["account_id"]
        or target["region"] != plan["region"]
        or target["api_origin"] != plan["target_origin"]
        or target["expected_user_id"] != plan["expected_user_id"]
        or resources["ecs_cluster_arn"] != plan["cluster_arn"]
        or resources["ecs_service_arn"] != plan["service_arn"]
        or resources["ecs_target_group_arn"] != plan["target_group_arn"]
    ):
        raise ValueError("recovery_target_binding_mismatch")
    return target


def validate_stop_approval(
    plan: dict[str, Any], approval: Any, plan_sha256: str | None = None
) -> dict[str, Any]:
    """Require separate approval for the one precise ECS task-stop action."""
    fields = {
        "approval_id",
        "human_approved",
        "approved_at_utc",
        "expires_at_utc",
        "plan_sha256",
        "action",
        "run_id",
        "account_id",
        "region",
        "cluster_arn",
        "service_arn",
        "task_arn",
    }
    if (
        not isinstance(approval, dict)
        or set(approval) != fields
        or approval.get("human_approved") is not True
        or approval.get("action") != "ecs.stop_task"
    ):
        raise ValueError("exact_stop_action_approval_required")
    if plan_sha256 is None or approval.get("plan_sha256") != plan_sha256:
        raise ValueError("stop_approval_plan_hash_mismatch")
    for key in (
        "run_id",
        "account_id",
        "region",
        "cluster_arn",
        "service_arn",
        "task_arn",
    ):
        if approval.get(key) != plan.get(key):
            raise ValueError("stop_approval_target_mismatch")
    if (
        not isinstance(approval.get("approval_id"), str)
        or not approval["approval_id"].strip()
    ):
        raise ValueError("invalid_stop_approval_id")
    for key in ("approved_at_utc", "expires_at_utc"):
        value = approval.get(key)
        if not isinstance(value, str):
            raise ValueError("invalid_stop_approval_time")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("invalid_stop_approval_time") from None
        if parsed.tzinfo is None:
            raise ValueError("invalid_stop_approval_time")
    now = datetime.now(timezone.utc)
    approved_at = datetime.fromisoformat(
        approval["approved_at_utc"].replace("Z", "+00:00")
    )
    expires = datetime.fromisoformat(approval["expires_at_utc"].replace("Z", "+00:00"))
    if approved_at > now or expires <= now or expires <= approved_at:
        raise ValueError("stop_approval_expired")
    return approval


def _utc() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _write_exclusive(path: Path, document: dict[str, Any]) -> None:
    """Write a private new receipt without replacing earlier evidence."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        payload = (
            json.dumps(document, indent=2, sort_keys=True, default=str) + "\n"
        ).encode()
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("evidence_write_failed")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _describe_capacity(ecs: Any, elbv2: Any, plan: dict[str, Any]) -> dict[str, Any]:
    """Count serving capacity only when healthy targets belong to these API tasks."""
    from scripts.evaluation.fresh_runtime import _targets_match

    service_result = ecs.describe_services(
        cluster=plan["cluster_arn"], services=[plan["service_arn"]]
    )
    services = service_result.get("services") or []
    if len(services) != 1 or service_result.get("failures"):
        raise ValueError("ecs_service_not_found")
    service = services[0]
    tasks_result = ecs.list_tasks(
        cluster=plan["cluster_arn"],
        serviceName=plan["service_arn"].rsplit("/", 1)[-1],
        desiredStatus="RUNNING",
        maxResults=100,
    )
    task_arns = tasks_result.get("taskArns") or []
    tasks: list[dict[str, Any]] = []
    for offset in range(0, len(task_arns), 100):
        described = ecs.describe_tasks(
            cluster=plan["cluster_arn"], tasks=task_arns[offset : offset + 100]
        )
        if described.get("failures"):
            raise ValueError("ecs_task_describe_failed")
        tasks.extend(described.get("tasks") or [])
    healthy_tasks = [
        task
        for task in tasks
        if task.get("lastStatus") == "RUNNING"
        and task.get("healthStatus", "UNKNOWN") in {"HEALTHY", "UNKNOWN"}
    ]
    targets = (
        elbv2.describe_target_health(TargetGroupArn=plan["target_group_arn"]).get(
            "TargetHealthDescriptions"
        )
        or []
    )
    healthy_targets = [
        row for row in targets if row.get("TargetHealth", {}).get("State") == "healthy"
    ]
    # In bridge mode the ALB registers EC2 instance IDs and host ports. An old
    # target or a different service must not establish recovery of this task set.
    targets_match = len(healthy_tasks) == plan["desired_count"] and _targets_match(
        ecs,
        {"ecs_cluster_arn": plan["cluster_arn"]},
        healthy_tasks,
        healthy_targets,
    )
    return {
        "desired_count": service.get("desiredCount"),
        "running_count": service.get("runningCount"),
        "pending_count": service.get("pendingCount"),
        "healthy_ecs_tasks": len(healthy_tasks),
        "healthy_alb_targets": len(healthy_targets),
        "healthy_targets_match_api_tasks": targets_match,
        "task_arns": [task.get("taskArn") for task in healthy_tasks],
        "service_stable": service.get("desiredCount") == plan["desired_count"]
        and service.get("runningCount") == plan["desired_count"]
        and service.get("pendingCount", 0) == 0,
        "serving_capacity_restored": targets_match
        and service.get("desiredCount") == plan["desired_count"]
        and service.get("runningCount") == plan["desired_count"]
        and service.get("pendingCount", 0) == 0,
    }


def _request(
    opener: Any, origin: str, path: str, cookie: str
) -> tuple[int | None, str]:
    request = Request(
        origin.rstrip("/") + path,
        headers={
            "Accept": "application/json",
            "Cookie": cookie,
            "Cache-Control": "no-cache",
        },
        method="GET",
    )
    try:
        with opener.open(request, timeout=5) as response:
            response.read(1_000_000)
            return response.status, (
                "success" if response.status == 200 else "http_error"
            )
    except HTTPError as error:
        return error.code, (
            "unauthorized"
            if error.code in {401, 403}
            else "throttled" if error.code == 429 else "http_error"
        )
    except TimeoutError:
        return None, "timeout"
    except URLError as error:
        return None, (
            "timeout" if isinstance(error.reason, TimeoutError) else "transport_error"
        )
    except OSError:
        return None, "transport_error"


def _load_window(
    plan: dict[str, Any],
    cookie: str,
    phase: str,
    seconds: int,
    *,
    stop_at_deadline: bool = False,
    recovery_probe: Callable[[], dict[str, Any]] | None = None,
    deadline_ns: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Issue one read each second, retaining slow overlapping requests and drops.

    Six bounded slots accommodate the five-second timeout without serializing
    subsequent samples behind a slow response. No HTTP request is retried.
    Recovery uses the absolute deadline that started before the stop API call.
    """
    opener = build_opener(
        ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context())
    )
    events: list[dict[str, Any]] = []
    executor = ThreadPoolExecutor(max_workers=6)
    pending: dict[Any, dict[str, Any]] = {}
    started = time.monotonic_ns()
    recovery = None
    if deadline_ns is None:
        deadline_ns = started + 240_000_000_000

    def finish(future: Any, row: dict[str, Any]) -> None:
        try:
            status, outcome, ended = future.result(timeout=6)
        except Exception:
            status, outcome, ended = None, "timeout", time.monotonic_ns()
        if (
            row["issued_monotonic_ns"] is not None
            and ended - row["issued_monotonic_ns"] > 5_000_000_000
        ):
            outcome = "timeout"
        row.update(completed_monotonic_ns=ended, status=status, outcome=outcome)
        _record_observation(plan, {"event": "request_outcome", **row})

    try:
        for index in range(seconds):
            scheduled = started + index * 1_000_000_000
            wait_ns = scheduled - time.monotonic_ns()
            if wait_ns > 0:
                time.sleep(wait_ns / 1_000_000_000)
            if (
                stop_at_deadline
                and recovery is None
                and time.monotonic_ns() >= deadline_ns
            ):
                break
            for future, previous in list(pending.items()):
                if future.done():
                    finish(future, previous)
                    del pending[future]
            route = "listing_read" if index % 2 == 0 else "ecs_read"
            path = (
                plan["listing_read_path"]
                if route == "listing_read"
                else plan["ecs_read_path"]
            )
            row = {
                "phase": phase,
                "index": index,
                "route": route,
                "scheduled_monotonic_ns": scheduled,
                "issued_monotonic_ns": None,
                "completed_monotonic_ns": None,
                "status": None,
                "outcome": None,
            }
            if len(pending) < 6:
                row["issued_monotonic_ns"] = time.monotonic_ns()

                def call(p: str = path) -> tuple[int | None, str, int]:
                    status, outcome = _request(opener, plan["target_origin"], p, cookie)
                    return status, outcome, time.monotonic_ns()

                pending[executor.submit(call)] = row
            else:
                row["outcome"] = "generator_drop"
                _record_observation(plan, {"event": "request_outcome", **row})
            events.append(row)
            if recovery_probe:
                state = recovery_probe()
                observed = time.monotonic_ns()
                _record_observation(
                    plan,
                    {
                        "event": "capacity_observation",
                        "observed_monotonic_ns": observed,
                        "state": state,
                    },
                )
                if state["serving_capacity_restored"] and recovery is None:
                    recovery = {"elapsed_monotonic_ns": observed, "state": state}
                if stop_at_deadline and recovery is None and observed >= deadline_ns:
                    break
        for future, row in pending.items():
            finish(future, row)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    return events, recovery


def run(
    plan: dict[str, Any], approval: dict[str, Any], *, profile_name: str | None = None
) -> dict[str, Any]:
    """Run one exact approved task-stop and bounded read observation."""
    from data.generators.reference_login import sdk_profile_session

    target = _load_target_plan(plan)
    inspect_target(target)
    if profile_name is not None and profile_name != target["aws_profile"]:
        raise ValueError("aws_profile_mismatch")
    cookie = os.environ.get("CLIP_NFR06_SESSION_COOKIE", "")
    check_session_identity(target, cookie)
    session = cast(Any, sdk_profile_session)(
        profile_name=target["aws_profile"], region_name=plan["region"]
    )
    sts = session.client("sts")
    identity = sts.get_caller_identity()
    if identity.get("Account") != plan["account_id"]:
        raise ValueError("aws_account_mismatch")
    ecs = session.client("ecs")
    elbv2 = session.client("elbv2")
    baseline_state = _describe_capacity(ecs, elbv2, plan)
    if (
        not baseline_state["serving_capacity_restored"]
        or plan["task_arn"] not in baseline_state["task_arns"]
    ):
        raise ValueError("two_healthy_tasks_and_named_target_required")
    baseline_events, _ = _load_window(plan, cookie, "baseline", 60)
    if len(baseline_events) != 60 or any(
        event["outcome"] != "success" for event in baseline_events
    ):
        raise ValueError("baseline_request_stream_incomplete")
    before_stop = _describe_capacity(ecs, elbv2, plan)
    if (
        not before_stop["serving_capacity_restored"]
        or plan["task_arn"] not in before_stop["task_arns"]
    ):
        raise ValueError("baseline_capacity_changed_before_stop")
    stop_started_ns = time.monotonic_ns()
    stop_started_utc = _utc()
    _record_observation(
        plan,
        {
            "event": "stop_requested",
            "at_utc": stop_started_utc,
            "monotonic_ns": stop_started_ns,
            "task_arn": plan["task_arn"],
        },
    )
    stopped = ecs.stop_task(
        cluster=plan["cluster_arn"],
        task=plan["task_arn"],
        reason=f"Approved NFR-06 run {plan['run_id']} action {approval['approval_id']}",
    )
    stop_ack_ns = time.monotonic_ns()
    stop_state = stopped.get("task", {})
    if stop_state.get("taskArn") != plan["task_arn"]:
        raise ValueError("ecs_stop_response_mismatch")

    def replacement_capacity() -> dict[str, Any]:
        """Exclude stale AWS listings of the stopped task from recovery evidence."""
        state = _describe_capacity(ecs, elbv2, plan)
        state["stopped_task_absent"] = plan["task_arn"] not in state["task_arns"]
        state["serving_capacity_restored"] = (
            state["serving_capacity_restored"] and state["stopped_task_absent"]
        )
        return state

    recovery_events, recovery = _load_window(
        plan,
        cookie,
        "recovery",
        300,
        stop_at_deadline=True,
        deadline_ns=stop_started_ns + 240_000_000_000,
        recovery_probe=replacement_capacity,
    )
    restored = recovery is not None
    recovery_elapsed_ms = (
        (recovery["elapsed_monotonic_ns"] - stop_started_ns) / 1_000_000
        if recovery
        else None
    )
    events = baseline_events + recovery_events
    output = {
        "format_version": 1,
        "nfr_id": "nfr-06",
        "run_id": plan["run_id"],
        "configuration": plan["configuration"],
        "account_id": plan["account_id"],
        "region": plan["region"],
        "cluster_arn": plan["cluster_arn"],
        "service_arn": plan["service_arn"],
        "task_arn": plan["task_arn"],
        "target_group_arn": plan["target_group_arn"],
        "target_manifest_sha256": plan["target_manifest_sha256"],
        "approval_id": approval["approval_id"],
        "operator_arn": identity.get("Arn"),
        "stop_requested_at_utc": stop_started_utc,
        "stop_call_elapsed_ms": (stop_ack_ns - stop_started_ns) / 1_000_000,
        "recovery_elapsed_ms": recovery_elapsed_ms,
        "restored_within_240_seconds": (
            restored
            and recovery_elapsed_ms is not None
            and recovery_elapsed_ms <= 240_000
        ),
        "restored_capacity_state": recovery["state"] if recovery else None,
        "baseline_capacity_state": baseline_state,
        "baseline_requests": baseline_events,
        "recovery_requests": recovery_events,
        "request_denominator": len(recovery_events),
        "request_failures": sum(
            event["outcome"] not in {"success", "generator_drop"}
            for event in recovery_events
        ),
        "generator_drops": sum(
            event["outcome"] == "generator_drop" for event in recovery_events
        ),
        "nfr_accepted": False,
        "cleanup_status": "no_new_resources_created",
    }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--profile")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = None
    approval = None
    try:
        if (
            args.plan.stat().st_size > 1_000_000
            or args.approval.stat().st_size > 32_000
        ):
            raise ValueError("input_too_large")
        plan_bytes = args.plan.read_bytes()
        plan = validate_plan(json.loads(plan_bytes))
        approval = validate_stop_approval(
            plan,
            json.loads(args.approval.read_text(encoding="utf-8")),
            hashlib.sha256(plan_bytes).hexdigest(),
        )
        output = run(plan, approval, profile_name=args.profile)
        _write_exclusive(args.output, output)
        print(
            json.dumps(
                {
                    "nfr_id": "nfr-06",
                    "run_id": plan["run_id"],
                    "restored_within_240_seconds": output[
                        "restored_within_240_seconds"
                    ],
                    "nfr_accepted": False,
                    "output": str(args.output),
                },
                sort_keys=True,
            )
        )
        return 0 if output["restored_within_240_seconds"] else 1
    except Exception:
        if plan is not None and approval is not None and not args.output.exists():
            failure = {
                "format_version": 1,
                "nfr_id": "nfr-06",
                "run_id": plan["run_id"],
                "configuration": plan["configuration"],
                "account_id": plan["account_id"],
                "region": plan["region"],
                "task_arn": plan["task_arn"],
                "approval_id": approval["approval_id"],
                "run_outcome": "failed_or_incomplete",
                "failure_type": "input_provider_or_observation_error",
                "action_may_have_started": True,
                "nfr_accepted": False,
                "cleanup_status": "inspect_exact_service_and_task_state_before_any_follow_up",
            }
            _write_exclusive(args.output, failure)
            print(
                json.dumps(
                    {
                        "nfr_id": "nfr-06",
                        "run_id": plan["run_id"],
                        "run_outcome": "failed_or_incomplete",
                        "nfr_accepted": False,
                        "output": str(args.output),
                    },
                    sort_keys=True,
                )
            )
            return 1
        parser.exit(2, "NFR-06 recovery run refused or incomplete\n")


if __name__ == "__main__":
    raise SystemExit(main())
