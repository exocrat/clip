"""Separately approved fresh application runtimes before formal performance runs.

This never reboots hosts, restarts the shared pool, edits data, changes images,
resizes services, or sends workload requests. Reset receipts describe readiness;
request/initialization logs must independently confirm the observed cold cohort.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, cast, Callable

from scripts.evaluation.k6.live_parity import read_bound
from scripts.evaluation.k6.real_target_preflight import inspect_target, validate_plan

ROOT = Path(__file__).resolve().parents[2]
MARKER = "CLIP_EVALUATION_RESET_ID"


def build_plan(target_path: str, target_sha256: str) -> dict[str, Any]:
    """Bind only the already-reviewed service/function, with no live calls."""
    if not isinstance(target_path, str) or not isinstance(target_sha256, str):
        raise ValueError("target_binding_required")
    target = validate_plan(read_bound(target_path, target_sha256))
    return {
        "format_version": 1,
        "purpose": "fresh-application-runtimes",
        "run_id": target["run_id"],
        "configuration": target["configuration"],
        "target_plan_path": target_path,
        "target_plan_sha256": target_sha256,
        "restart_ecs": True,
        "recycle_lambda": target["configuration"] == "B",
        "expected_ecs_count": 2,
        "maximum_transition_seconds": 900,
        "poll_seconds": 5,
        "lambda_marker": MARKER,
        "host_pool_database_unchanged": True,
        "cold_confirmation_required": True,
        "execution_authorized": False,
    }


def validate_reset(plan: Any) -> dict[str, Any]:
    """Reject unknown actions and any weakening of the frozen reset policy."""
    if not isinstance(plan, dict):
        raise ValueError("invalid_reset_plan")
    target_path, target_digest = plan.get("target_plan_path"), plan.get(
        "target_plan_sha256"
    )
    if not isinstance(target_path, str) or not isinstance(target_digest, str):
        raise ValueError("target_binding_required")
    expected = build_plan(target_path, target_digest)
    if plan != expected:
        raise ValueError("reset_plan_mismatch")
    return validate_plan(
        read_bound(plan["target_plan_path"], plan["target_plan_sha256"])
    )


def validate_approval(plan_bytes: bytes, approval: Any, now: datetime) -> None:
    """Require an exact, expiring reset approval, distinct from load approval."""
    if (
        not isinstance(approval, dict)
        or approval.get("action") != "prepare_fresh_application_runtimes"
        or approval.get("approved") is not True
        or approval.get("plan_sha256") != hashlib.sha256(plan_bytes).hexdigest()
        or not isinstance(approval.get("review_record"), str)
        or not approval["review_record"].strip()
    ):
        raise ValueError("exact_reset_approval_required")
    start = datetime.fromisoformat(approval["approved_at_utc"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(approval["expires_at_utc"].replace("Z", "+00:00"))
    if start.tzinfo is None or end.tzinfo is None or not start <= now < end:
        raise ValueError("reset_approval_expired")


def _running(ecs: Any, resources: dict[str, Any]) -> list[str]:
    """Use the exact service only; never select pool or standalone tasks."""
    result = ecs.list_tasks(
        cluster=resources["ecs_cluster_arn"],
        serviceName=resources["ecs_service_arn"].rsplit("/", 1)[-1],
        desiredStatus="RUNNING",
    )
    if result.get("nextToken"):
        raise ValueError("unexpected_service_task_pagination")
    return sorted(result["taskArns"])


def reset(
    plan: dict[str, Any],
    target: dict[str, Any],
    session: Any,
    *,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    progress: Callable[[dict[str, Any]], None] = lambda _: None,
) -> dict[str, Any]:
    """Restart the exact API service, wait for new healthy tasks, then recycle B.

    The CLI performs approval and target checks first. Injected clients/clocks
    support local failure tests. Every partial outcome is persisted by the CLI.
    A reset is preparation, never an NFR-06 fault-injection result.
    """
    resources = target["resources"]
    ecs, elb = session.client("ecs"), session.client("elbv2")
    begin = monotonic()
    deadline = begin + plan["maximum_transition_seconds"]
    old = _running(ecs, resources)
    if len(old) != 2:
        raise ValueError("two_initial_api_tasks_required")
    receipt: dict[str, Any] = {
        "run_id": plan["run_id"],
        "configuration": plan["configuration"],
        "target_plan_sha256": plan["target_plan_sha256"],
        "started_at_utc": datetime.now(UTC).isoformat(),
        "old_ecs_tasks": old,
        "state": "restarting_ecs",
        "cold_observations_confirmed": False,
    }
    progress(receipt)
    ecs.update_service(
        cluster=resources["ecs_cluster_arn"],
        service=resources["ecs_service_arn"],
        forceNewDeployment=True,
    )
    while monotonic() < deadline:
        service = ecs.describe_services(
            cluster=resources["ecs_cluster_arn"],
            services=[resources["ecs_service_arn"]],
        )["services"][0]
        if (
            service["desiredCount"] != 2
            or service["taskDefinition"] != resources["ecs_task_definition_arn"]
        ):
            raise ValueError("api_service_changed_during_reset")
        new = _running(ecs, resources)
        if len(new) == 2 and not set(new) & set(old):
            previous = ecs.describe_tasks(
                cluster=resources["ecs_cluster_arn"], tasks=old
            )
            healthy = elb.describe_target_health(
                TargetGroupArn=resources["ecs_target_group_arn"]
            )["TargetHealthDescriptions"]
            if (
                not previous.get("failures")
                and len(previous["tasks"]) == 2
                and all(task["lastStatus"] == "STOPPED" for task in previous["tasks"])
                and sum(row["TargetHealth"]["State"] == "healthy" for row in healthy)
                == 2
                and service["runningCount"] == 2
                and service["pendingCount"] == 0
            ):
                tasks = ecs.describe_tasks(
                    cluster=resources["ecs_cluster_arn"], tasks=new
                )["tasks"]
                if len(tasks) != 2 or any(
                    task["taskDefinitionArn"] != resources["ecs_task_definition_arn"]
                    or task["lastStatus"] != "RUNNING"
                    for task in tasks
                ):
                    raise ValueError("fresh_task_revision_mismatch")
                task_ips = {
                    item["value"]
                    for task in tasks
                    for attachment in task.get("attachments", [])
                    for item in attachment.get("details", [])
                    if item.get("name") == "privateIPv4Address"
                }
                healthy_ips = {
                    row["Target"]["Id"]
                    for row in healthy
                    if row["TargetHealth"]["State"] == "healthy"
                }
                if len(task_ips) != 2 or task_ips != healthy_ips:
                    sleep(plan["poll_seconds"])
                    continue
                receipt["new_ecs_tasks"] = [
                    {
                        "task_arn": task["taskArn"],
                        "created_at": task["createdAt"].isoformat(),
                        "started_at": task["startedAt"].isoformat(),
                    }
                    for task in tasks
                ]
                receipt["ecs_ready_elapsed_seconds"] = monotonic() - begin
                break
        sleep(plan["poll_seconds"])
    else:
        raise ValueError("ecs_fresh_start_deadline_exceeded")
    if plan["recycle_lambda"]:
        lam = session.client("lambda")
        function = resources["lambda_function_arn"]
        original = lam.get_function_configuration(FunctionName=function)
        if original["LastUpdateStatus"] != "Successful":
            raise ValueError("lambda_configuration_not_stable")
        env = dict(original["Environment"]["Variables"])
        if env.get(MARKER) == plan["run_id"]:
            raise ValueError("reset_id_already_used")
        env[MARKER] = plan["run_id"]
        receipt["state"] = "recycling_lambda"
        receipt["lambda_original_revision"] = original["RevisionId"]
        progress(receipt)
        lam.update_function_configuration(
            FunctionName=function,
            RevisionId=original["RevisionId"],
            Environment={"Variables": env},
        )
        while monotonic() < deadline:
            updated = lam.get_function_configuration(FunctionName=function)
            if updated["LastUpdateStatus"] == "Failed":
                raise ValueError("lambda_reset_failed")
            if (
                updated["LastUpdateStatus"] == "Successful"
                and updated["RevisionId"] != original["RevisionId"]
            ):
                if (
                    updated["MemorySize"] != original["MemorySize"]
                    or updated["Timeout"] != original["Timeout"]
                    or updated["Environment"]["Variables"] != env
                ):
                    raise ValueError("lambda_settings_changed_during_reset")
                receipt["lambda_revision"] = updated["RevisionId"]
                receipt["lambda_reset_marker"] = plan["run_id"]
                break
            sleep(plan["poll_seconds"])
        else:
            raise ValueError("lambda_reset_deadline_exceeded")
    receipt.update(
        state="prepared_requires_log_confirmation",
        elapsed_seconds=monotonic() - begin,
        ended_at_utc=datetime.now(UTC).isoformat(),
    )
    progress(receipt)
    return receipt


def main() -> None:
    """Require explicit execution and exact separate approval; preserve partial state."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error("new_output_required")
    from scripts.evaluation.k6.real_run_coordinator import _read_bounded

    raw = _read_bounded(args.plan, 100_000)
    plan = json.loads(raw)
    target = validate_reset(plan)
    validate_approval(
        raw, json.loads(_read_bounded(args.approval, 100_000)), datetime.now(UTC)
    )
    from data.generators.reference_login import sdk_profile_session

    session = cast(Any, sdk_profile_session)(
        profile_name=target["aws_profile"], region_name=target["region"]
    )
    who = session.client("sts").get_caller_identity()
    if (
        who["Account"] != target["account_id"]
        or who["Arn"] != target["expected_caller_arn"]
    ):
        parser.error("aws_identity_mismatch")
    inspect_target(target)
    partial = args.output.with_suffix(args.output.suffix + ".partial")
    if partial.exists() or partial.is_symlink():
        parser.error("partial_output_exists")

    # Append-only partial observations survive failure, without following links.
    descriptor = os.open(
        partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w") as progress_stream:

        def persist(value: dict[str, Any]) -> None:
            progress_stream.write(json.dumps(value) + "\n")
            progress_stream.flush()
            os.fsync(progress_stream.fileno())

        result = reset(plan, target, session, progress=persist)
    result["plan_sha256"] = hashlib.sha256(raw).hexdigest()
    descriptor = os.open(
        args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(result, stream, indent=2)
    args.output.chmod(0o400)
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "state": result["state"],
                "elapsed_seconds": result["elapsed_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
