"""Capture bounded read-only AWS telemetry for one approved experiment run.

This command reads CloudWatch metrics only. It never creates, changes, or stops
resources. Captured bytes are immutable per-run files and remain evidence, not
an NFR decision.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Protocol

from scripts.evaluation.k6.real_target_preflight import validate_plan

MAX_WINDOW = timedelta(hours=6)
PERIOD_SECONDS = 60
MAX_OUTPUT_BYTES = 100_000_000
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")


class CloudWatchClient(Protocol):
    """Small surface needed by the read-only metrics collector."""

    def get_metric_data(self, **kwargs: Any) -> dict[str, Any]: ...


class STSClient(Protocol):
    """Caller identity surface used to bind evidence to the target account."""

    def get_caller_identity(self) -> dict[str, Any]: ...


def _utc(value: object, name: str) -> datetime:
    if not isinstance(value, str) or not UTC.fullmatch(value):
        raise ValueError(f"{name}_must_be_utc")
    try:
        return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        raise ValueError(f"{name}_must_be_utc") from None


def _resource_name(arn: str, prefix: str) -> str:
    resource = arn.split(":", 5)[5]
    if not resource.startswith(prefix):
        raise ValueError("target_resource_arn_shape_invalid")
    return resource.removeprefix(prefix)


def _query(
    query_id: str,
    namespace: str,
    metric_name: str,
    dimensions: list[dict[str, str]],
    stat: str,
) -> dict[str, Any]:
    return {
        "Id": query_id,
        "Label": metric_name,
        "MetricStat": {
            "Metric": {
                "Namespace": namespace,
                "MetricName": metric_name,
                "Dimensions": dimensions,
            },
            "Period": PERIOD_SECONDS,
            "Stat": stat,
        },
        "ReturnData": True,
    }


def build_queries(plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Build fixed metric queries from the exact target ARNs in a validated plan."""
    resources = plan["resources"]
    load_balancer = _resource_name(resources["load_balancer_arn"], "loadbalancer/")
    ecs_target_group = _resource_name(resources["ecs_target_group_arn"], "targetgroup/")
    cluster_parts = _resource_name(resources["ecs_cluster_arn"], "cluster/").split("/")
    service_parts = _resource_name(resources["ecs_service_arn"], "service/").split("/")
    if len(cluster_parts) != 1 or len(service_parts) not in {1, 2}:
        raise ValueError("target_ecs_arn_shape_invalid")
    cluster_name = cluster_parts[0]
    service_name = service_parts[-1]

    alb_dims = [{"Name": "LoadBalancer", "Value": load_balancer}]
    ecs_tg_dims = alb_dims + [{"Name": "TargetGroup", "Value": ecs_target_group}]
    ecs_dims = [
        {"Name": "ClusterName", "Value": cluster_name},
        {"Name": "ServiceName", "Value": service_name},
    ]
    groups: dict[str, list[dict[str, Any]]] = {
        "ecs": [
            _query("ecs_cpu", "AWS/ECS", "CPUUtilization", ecs_dims, "Average"),
            _query("ecs_memory", "AWS/ECS", "MemoryUtilization", ecs_dims, "Average"),
            _query(
                "alb_ecs_requests",
                "AWS/ApplicationELB",
                "RequestCount",
                ecs_tg_dims,
                "Sum",
            ),
            _query(
                "alb_ecs_target_5xx",
                "AWS/ApplicationELB",
                "HTTPCode_Target_5XX_Count",
                ecs_tg_dims,
                "Sum",
            ),
            _query(
                "alb_ecs_target_response_p95",
                "AWS/ApplicationELB",
                "TargetResponseTime",
                ecs_tg_dims,
                "p95",
            ),
            _query(
                "alb_load_balancer_5xx",
                "AWS/ApplicationELB",
                "HTTPCode_ELB_5XX_Count",
                alb_dims,
                "Sum",
            ),
        ],
        "lambda": [],
        "postgres": [
            _query(
                "rds_connections",
                "AWS/RDS",
                "DatabaseConnections",
                [
                    {
                        "Name": "DBInstanceIdentifier",
                        "Value": resources["database_instance_id"],
                    }
                ],
                "Maximum",
            ),
            _query(
                "rds_cpu",
                "AWS/RDS",
                "CPUUtilization",
                [
                    {
                        "Name": "DBInstanceIdentifier",
                        "Value": resources["database_instance_id"],
                    }
                ],
                "Average",
            ),
            _query(
                "rds_free_memory",
                "AWS/RDS",
                "FreeableMemory",
                [
                    {
                        "Name": "DBInstanceIdentifier",
                        "Value": resources["database_instance_id"],
                    }
                ],
                "Minimum",
            ),
            _query(
                "rds_read_latency",
                "AWS/RDS",
                "ReadLatency",
                [
                    {
                        "Name": "DBInstanceIdentifier",
                        "Value": resources["database_instance_id"],
                    }
                ],
                "Average",
            ),
            _query(
                "rds_write_latency",
                "AWS/RDS",
                "WriteLatency",
                [
                    {
                        "Name": "DBInstanceIdentifier",
                        "Value": resources["database_instance_id"],
                    }
                ],
                "Average",
            ),
            _query(
                "rds_disk_queue",
                "AWS/RDS",
                "DiskQueueDepth",
                [
                    {
                        "Name": "DBInstanceIdentifier",
                        "Value": resources["database_instance_id"],
                    }
                ],
                "Maximum",
            ),
        ],
    }

    lambda_arn = resources["lambda_function_arn"]
    lambda_target_arn = resources["lambda_target_group_arn"]
    if plan["configuration"] == "B":
        if not isinstance(lambda_arn, str) or not isinstance(lambda_target_arn, str):
            raise ValueError("configuration_b_lambda_resources_missing")
        lambda_name = _resource_name(lambda_arn, "function:").split(":", 1)[0]
        lambda_target_group = _resource_name(lambda_target_arn, "targetgroup/")
        lambda_dims = [{"Name": "FunctionName", "Value": lambda_name}]
        lambda_tg_dims = alb_dims + [
            {"Name": "TargetGroup", "Value": lambda_target_group}
        ]
        groups["lambda"] = [
            _query(
                "lambda_invocations", "AWS/Lambda", "Invocations", lambda_dims, "Sum"
            ),
            _query("lambda_errors", "AWS/Lambda", "Errors", lambda_dims, "Sum"),
            _query("lambda_throttles", "AWS/Lambda", "Throttles", lambda_dims, "Sum"),
            _query("lambda_duration_p95", "AWS/Lambda", "Duration", lambda_dims, "p95"),
            _query(
                "lambda_concurrency",
                "AWS/Lambda",
                "ConcurrentExecutions",
                lambda_dims,
                "Maximum",
            ),
            _query(
                "alb_lambda_requests",
                "AWS/ApplicationELB",
                "RequestCount",
                lambda_tg_dims,
                "Sum",
            ),
            _query(
                "alb_lambda_user_errors",
                "AWS/ApplicationELB",
                "LambdaUserError",
                lambda_tg_dims,
                "Sum",
            ),
            _query(
                "alb_lambda_internal_errors",
                "AWS/ApplicationELB",
                "LambdaInternalError",
                lambda_tg_dims,
                "Sum",
            ),
        ]
    return groups


def validate_window(
    window: object, plan: dict[str, Any]
) -> tuple[datetime, datetime, str]:
    """Bind a bounded actual run interval to the target plan's run ID."""
    if not isinstance(window, dict) or set(window) != {
        "format_version",
        "run_id",
        "actual_start_utc",
        "actual_end_utc",
    }:
        raise ValueError("invalid_run_window_shape")
    if (
        type(window["format_version"]) is not int
        or window["format_version"] != 1
        or window["run_id"] != plan["run_id"]
        or not isinstance(window["run_id"], str)
        or not RUN_ID.fullmatch(window["run_id"])
    ):
        raise ValueError("run_window_target_mismatch")
    start = _utc(window["actual_start_utc"], "actual_start")
    end = _utc(window["actual_end_utc"], "actual_end")
    if end <= start or end - start > MAX_WINDOW:
        raise ValueError("run_window_out_of_bounds")
    # CloudWatch period boundaries are UTC minutes. Expand, never shrink, the
    # query range so the requested run is covered by the returned datapoints.
    query_start = start.replace(second=0, microsecond=0)
    query_end = end.replace(second=0, microsecond=0)
    if query_end < end:
        query_end += timedelta(minutes=1)
    return query_start, query_end, window["run_id"]


def _collect_group(
    client: CloudWatchClient,
    queries: list[dict[str, Any]],
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    if not queries:
        return []
    output: dict[str, dict[str, Any]] = {}
    token: str | None = None
    seen_tokens: set[str] = set()
    while True:
        request: dict[str, Any] = {
            "MetricDataQueries": queries,
            "StartTime": start,
            "EndTime": end,
            "ScanBy": "TimestampAscending",
            "MaxDatapoints": 100800,
        }
        if token:
            request["NextToken"] = token
        response = client.get_metric_data(**request)
        results = response.get("MetricDataResults")
        if not isinstance(results, list):
            raise ValueError("cloudwatch_response_missing_results")
        for result in results:
            if not isinstance(result, dict) or not isinstance(result.get("Id"), str):
                raise ValueError("cloudwatch_response_invalid_result")
            query_id = result["Id"]
            if query_id not in {query["Id"] for query in queries}:
                raise ValueError("cloudwatch_response_unexpected_metric")
            current = output.setdefault(
                query_id,
                {
                    "id": query_id,
                    "label": result.get("Label"),
                    "status_code": result.get("StatusCode"),
                    "timestamps": [],
                    "values": [],
                    "messages": [],
                },
            )
            if result.get("StatusCode") != "Complete":
                current["status_code"] = result.get("StatusCode")
            for field, target in (("Timestamps", "timestamps"), ("Values", "values")):
                values = result.get(field, [])
                if not isinstance(values, list):
                    raise ValueError("cloudwatch_response_invalid_series")
                if field == "Timestamps":
                    if any(
                        not isinstance(value, datetime)
                        or value.tzinfo is None
                        or not start <= value.astimezone(timezone.utc) <= end
                        for value in values
                    ):
                        raise ValueError("cloudwatch_response_timestamp_invalid")
                    current[target].extend(
                        value.astimezone(timezone.utc)
                        .isoformat()
                        .replace("+00:00", "Z")
                        for value in values
                    )
                else:
                    if any(
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                        or value < 0
                        for value in values
                    ):
                        raise ValueError("cloudwatch_response_value_invalid")
                    current[target].extend(values)
            messages = result.get("Messages", [])
            if isinstance(messages, list):
                # Preserve only code, never provider prose or request metadata.
                current["messages"].extend(
                    {"code": item.get("Code")}
                    for item in messages
                    if isinstance(item, dict) and isinstance(item.get("Code"), str)
                )
        next_token = response.get("NextToken")
        if not next_token:
            break
        if not isinstance(next_token, str) or next_token in seen_tokens:
            raise ValueError("cloudwatch_pagination_invalid")
        seen_tokens.add(next_token)
        token = next_token

    for query in queries:
        series = output.setdefault(
            query["Id"],
            {
                "id": query["Id"],
                "label": query["Label"],
                "status_code": "NoData",
                "timestamps": [],
                "values": [],
                "messages": [],
            },
        )
        if not series["timestamps"]:
            series["status_code"] = "NoData"
        if len(series["timestamps"]) != len(series["values"]):
            raise ValueError("cloudwatch_response_series_length_mismatch")
    return [output[query["Id"]] for query in queries]


def capture(
    plan: dict[str, Any],
    window: object,
    sts: STSClient,
    cloudwatch: CloudWatchClient,
    output_dir: Path,
    target_plan_sha256: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Collect and write three immutable component files; never accept a run."""
    plan = validate_plan(plan)
    query_start, query_end, run_id = validate_window(window, plan)
    if not re.fullmatch(r"[0-9a-f]{64}", target_plan_sha256):
        raise ValueError("target_plan_hash_invalid")
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("output_directory_must_be_new")
    caller = sts.get_caller_identity()
    if (
        caller.get("Account") != plan["account_id"]
        or caller.get("Arn") != plan["expected_caller_arn"]
    ):
        raise ValueError("aws_caller_target_mismatch")
    groups = build_queries(plan)
    raw: dict[str, list[dict[str, Any]]] = {
        group: _collect_group(cloudwatch, queries, query_start, query_end)
        for group, queries in groups.items()
    }
    collected_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("output_directory_must_be_new")
    output_dir.mkdir(parents=True, exist_ok=False)
    artifacts: dict[str, dict[str, Any]] = {}
    for group, series in raw.items():
        body = {
            "format_version": 1,
            "artifact_kind": f"cloudwatch_{group}",
            "run_id": run_id,
            "configuration": plan["configuration"],
            "target_plan_sha256": target_plan_sha256,
            "account_id": plan["account_id"],
            "region": plan["region"],
            "period_seconds": PERIOD_SECONDS,
            "requested_run_window_utc": window,
            "metric_query_window_start_utc": query_start.isoformat().replace(
                "+00:00", "Z"
            ),
            "metric_query_window_end_utc": query_end.isoformat().replace("+00:00", "Z"),
            "collected_at_utc": collected_at.isoformat().replace("+00:00", "Z"),
            "state": (
                "not_applicable" if group == "lambda" and not series else "captured"
            ),
            "not_applicable_reason": (
                "configuration_a_ecs_only" if group == "lambda" and not series else None
            ),
            "queries": groups[group],
            "series": series,
        }
        encoded = (
            json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        if len(encoded) > MAX_OUTPUT_BYTES:
            raise ValueError("cloudwatch_artifact_too_large")
        path = output_dir / f"{group}-cloudwatch.json"
        with path.open("xb") as stream:
            stream.write(encoded)
        artifacts[group] = {
            "reference": path.as_posix(),
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "series_count": len(series),
            "series_with_data": sum(bool(item["timestamps"]) for item in series),
        }
    return {
        "run_id": run_id,
        "configuration": plan["configuration"],
        "measurement_authorized": False,
        "nfr_accepted": False,
        "artifacts": artifacts,
    }


def main() -> int:
    """Read exact run window and target plan, then save CloudWatch evidence."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("target_plan", type=Path)
    parser.add_argument("run_window", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        plan_bytes = args.target_plan.read_bytes()
        plan = json.loads(plan_bytes)
        window = json.loads(args.run_window.read_text(encoding="utf-8"))
        plan = validate_plan(plan)
        if (
            args.output_dir.is_absolute()
            or ".." in args.output_dir.parts
            or not args.output_dir.parts
            or args.output_dir.parts[0] != "docs"
            or len(args.output_dir.parts) < 3
            or args.output_dir.parts[:3] != ("docs", "evaluation", "experiment-runs")
        ):
            raise ValueError("output_directory_must_be_relative")
        import boto3  # type: ignore[import-untyped]

        session = boto3.Session(
            profile_name=plan["aws_profile"], region_name=plan["region"]
        )
        result = capture(
            plan,
            window,
            session.client("sts"),
            session.client("cloudwatch"),
            args.output_dir,
            hashlib.sha256(plan_bytes).hexdigest(),
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"CloudWatch capture failed: {type(exc).__name__}\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
