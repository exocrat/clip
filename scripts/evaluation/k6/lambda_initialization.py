"""Read bounded Lambda logs and retain only sanitized platform REPORT evidence.

An explicit Init Duration proves initialization was observed. Its absence does
not prove a warm invocation: suppressed initialization may not have that field.
Client latency is not classified from a slow response or assumed idle timeout.
"""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Any
from scripts.evaluation.k6.cloudwatch_capture import validate_window
from scripts.evaluation.k6.real_target_preflight import validate_plan

REPORT = re.compile(
    r"^REPORT RequestId:\s+([A-Za-z0-9-]+)\s+Duration:\s+([0-9.]+)\s+ms\b"
)
INIT = re.compile(r"\bInit Duration:\s+([0-9.]+)\s+ms\b")


def parse_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """Discard application messages; retain finite numeric platform fields only."""
    message = event.get("message", "")
    if not isinstance(message, str):
        return None
    match = REPORT.match(message)
    request_id: str | None = None
    duration: Any = None
    init: Any = None
    if match:
        request_id = match[1]
        duration = float(match[2])
        found = INIT.search(message)
        init = float(found[1]) if found else None
    else:
        try:
            body = json.loads(message)
        except ValueError:
            return None
        if not isinstance(body, dict) or body.get("type") != "platform.report":
            return None
        record = body.get("record", {})
        if not isinstance(record, dict) or not isinstance(record.get("metrics"), dict):
            raise ValueError("malformed_platform_report")
        request_id = record.get("requestId")
        duration = record["metrics"].get("durationMs")
        init = record["metrics"].get("initDurationMs")
    if not isinstance(request_id, str) or not re.fullmatch(
        r"[A-Za-z0-9-]{1,100}", request_id
    ):
        raise ValueError("invalid_platform_request_id")
    for value in (duration, init):
        if value is not None and (
            type(value) not in (int, float) or not math.isfinite(value) or value < 0
        ):
            raise ValueError("invalid_platform_duration")
    if duration is None or type(event.get("timestamp")) is not int:
        raise ValueError("incomplete_platform_report")
    return {
        "request_id_sha256": hashlib.sha256(request_id.encode()).hexdigest(),
        "log_stream_sha256": hashlib.sha256(
            str(event.get("logStreamName", "")).encode()
        ).hexdigest(),
        "timestamp_ms": event["timestamp"],
        "duration_ms": duration,
        "init_duration_ms": init,
        "initialization_observed": init is not None,
    }


def collect(
    logs: Any, log_group: str, start_ms: int, end_ms: int
) -> list[dict[str, Any]]:
    """Read at most 100 pages/200,000 events; pagination failure is incomplete evidence."""
    rows = []
    seen = set()
    token = None
    count = 0
    for _ in range(100):
        kwargs = {
            "logGroupName": log_group,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": 10000,
        }
        if token:
            kwargs["nextToken"] = token
        response = logs.filter_log_events(**kwargs)
        events = response.get("events")
        if not isinstance(events, list):
            raise ValueError("log_events_missing")
        count += len(events)
        if count > 200000:
            raise ValueError("log_event_cap_exceeded")
        for event in events:
            row = parse_event(event)
            if row is not None and start_ms <= row["timestamp_ms"] < end_ms:
                rows.append(row)
        next_token = response.get("nextToken")
        if not next_token:
            unique: dict[tuple[str, str], dict[str, Any]] = {}
            for row in rows:
                key = (row["request_id_sha256"], row["log_stream_sha256"])
                if key in unique and unique[key] != row:
                    raise ValueError("conflicting_platform_reports")
                unique[key] = row
            return sorted(unique.values(), key=lambda row: row["timestamp_ms"])
        if not isinstance(next_token, str) or next_token in seen:
            raise ValueError("log_pagination_invalid")
        seen.add(next_token)
        token = next_token
    raise ValueError("log_page_cap_exceeded")


def main() -> None:
    """Bind the real function/window and write a new owner-only evidence file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target_plan", type=Path)
    parser.add_argument("run_window", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("output_must_be_new")
        raw = args.target_plan.read_bytes()
        plan = validate_plan(json.loads(raw))
        window = json.loads(args.run_window.read_bytes())
        validate_window(window, plan)
        if plan["configuration"] != "B":
            raise ValueError("lambda_configuration_b_required")
        start = datetime.fromisoformat(
            window["actual_start_utc"].replace("Z", "+00:00")
        )
        end = datetime.fromisoformat(window["actual_end_utc"].replace("Z", "+00:00"))
        from data.generators.reference_login import sdk_profile_session

        session = sdk_profile_session(
            profile_name=plan["aws_profile"], region_name=plan["region"]
        )
        caller = session.client("sts").get_caller_identity()
        if (
            caller["Account"] != plan["account_id"]
            or caller["Arn"] != plan["expected_caller_arn"]
        ):
            raise ValueError("aws_caller_target_mismatch")
        function = session.client("lambda").get_function(
            FunctionName=plan["resources"]["lambda_function_arn"]
        )
        if (
            function["Code"]["ResolvedImageUri"]
            != plan["revisions"]["lambda_image_uri"]
        ):
            raise ValueError("lambda_image_changed")
        config = function["Configuration"]
        group = (
            config.get("LoggingConfig", {}).get("LogGroup")
            or "/aws/lambda/" + config["FunctionName"]
        )
        rows = collect(
            session.client("logs"),
            group,
            int(start.timestamp() * 1000),
            int(end.timestamp() * 1000),
        )
        result = {
            "format_version": 1,
            "run_id": plan["run_id"],
            "target_plan_sha256": hashlib.sha256(raw).hexdigest(),
            "function_arn": plan["resources"]["lambda_function_arn"],
            "image_uri": plan["revisions"]["lambda_image_uri"],
            "run_window": window,
            "collected_at_utc": datetime.now(timezone.utc).isoformat(),
            "reports": rows,
            "report_count": len(rows),
            "initializations_observed": sum(r["initialization_observed"] for r in rows),
            "state": "captured" if rows else "no_data",
            "warm_classification_verified": False,
            "client_request_correlation_verified": False,
            "billing_or_log_delivery_completeness_verified": False,
            "measurement_authorized": False,
        }
        descriptor = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w") as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write("\n")
        if not rows:
            parser.exit(2, "No platform reports found; evidence incomplete\n")
    except OSError, ValueError, KeyError, TypeError:
        parser.exit(2, "Lambda initialization capture failed\n")


if __name__ == "__main__":
    main()
