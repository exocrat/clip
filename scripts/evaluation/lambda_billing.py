"""Retain only numeric Lambda billed-usage evidence from bounded REPORT queries.

This supplements immutable run telemetry after measurement. It never issues app
requests, changes resources, accepts a run or infers a billed duration from an
execution-duration percentile. IDs are hashed; log bodies are never retained.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

REPORT = re.compile(r"^REPORT RequestId:\s+([A-Za-z0-9-]{1,100})\s")
BILLED = re.compile(r"\bBilled Duration:\s+([0-9.]+)\s+ms\b")
MEMORY = re.compile(r"\bMemory Size:\s+([0-9]+)\s+MB\b")


def parse_billed_usage(event: dict[str, Any]) -> dict[str, Any] | None:
    """Parse text or structured platform reports, rejecting missing usage fields."""
    message = event.get("message")
    if not isinstance(message, str):
        return None
    match = REPORT.match(message)
    duration: Any
    size: Any
    if match:
        billed, memory = BILLED.search(message), MEMORY.search(message)
        if not billed or not memory:
            raise ValueError("billed_platform_fields_missing")
        identifier, duration, size = match[1], float(billed[1]), int(memory[1])
    else:
        try:
            body = json.loads(message)
        except ValueError:
            return None
        if not isinstance(body, dict) or body.get("type") != "platform.report":
            return None
        record = body.get("record")
        metrics = record.get("metrics") if isinstance(record, dict) else None
        if not isinstance(record, dict) or not isinstance(metrics, dict):
            raise ValueError("billed_platform_fields_missing")
        identifier = record.get("requestId")
        duration, size = metrics.get("billedDurationMs"), metrics.get("memorySizeMB")
    if (
        not isinstance(identifier, str)
        or not re.fullmatch(r"[A-Za-z0-9-]{1,100}", identifier)
        or type(duration) not in (int, float)
        or not math.isfinite(duration)
        or duration < 0
        or type(size) not in (int, float)
        or not math.isfinite(size)
        or size != int(size)
        or not 128 <= size <= 10240
        or type(event.get("timestamp")) is not int
        or not isinstance(event.get("logStreamName"), str)
        or not event["logStreamName"]
    ):
        raise ValueError("invalid_billed_platform_fields")
    return {
        "request_id_sha256": hashlib.sha256(identifier.encode()).hexdigest(),
        "log_stream_sha256": hashlib.sha256(
            event["logStreamName"].encode()
        ).hexdigest(),
        "timestamp_ms": event["timestamp"],
        "billed_duration_ms": duration,
        "memory_size_mib": int(size),
        "billed_gb_seconds": duration / 1000 * size / 1024,
    }


def collect(logs: Any, group: str, start_ms: int, end_ms: int) -> dict[str, Any]:
    """Fetch REPORT-only events with bounded pagination and immutable-key deduping.

    Optional-term CloudWatch filtering selects text REPORT or structured
    platform.report events. Scope/phase attribution and delayed-delivery checks
    remain the caller's responsibility; a complete query is not complete billing.
    """
    if (
        group != "/aws/lambda/clip-exp03-exp261103"
        or type(start_ms) is not int
        or type(end_ms) is not int
        or not 0 < end_ms - start_ms <= 3_600_000
    ):
        raise ValueError("bounded_billing_window_required")
    seen: set[str] = set()
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    token = None
    count = 0
    for _ in range(100):
        args: dict[str, Any] = {
            "logGroupName": group,
            "startTime": start_ms,
            "endTime": end_ms,
            "filterPattern": '?REPORT ?"platform.report"',
            "limit": 10000,
        }
        if token:
            args["nextToken"] = token
        result = logs.filter_log_events(**args)
        events = result.get("events")
        if not isinstance(events, list):
            raise ValueError("billing_events_missing")
        count += len(events)
        if count > 100000:
            raise ValueError("billing_event_cap_exceeded")
        for event in events:
            if not start_ms <= event.get("timestamp", -1) < end_ms:
                continue
            row = parse_billed_usage(event)
            if row is None:
                continue
            key = row["request_id_sha256"], row["log_stream_sha256"]
            if key in rows and rows[key] != row:
                raise ValueError("conflicting_billed_platform_report")
            rows[key] = row
        token = result.get("nextToken")
        if not token:
            values = list(rows.values())
            return {
                "format_version": 1,
                "collection_complete": True,
                "run_or_phase_attribution_verified": False,
                "query_start_ms": start_ms,
                "query_end_ms": end_ms,
                "reports": values,
                "billed_gb_seconds": sum(row["billed_gb_seconds"] for row in values),
            }
        if not isinstance(token, str) or token in seen:
            raise ValueError("billing_pagination_invalid")
        seen.add(token)
    raise ValueError("billing_page_cap_exceeded")
