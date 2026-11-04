"""Bounded, content-free PgBouncer counter capture from its own log group."""

import json
import math
from typing import Any

ROLES = {
    "clip_test_identity_app",
    "clip_test_marketplace_app",
    "clip_test_conversations_app",
    "pgbouncer",
}
DATABASES = {"clip_next06_reference", "pgbouncer"}


def safe_counter_event(message: str) -> dict[str, Any]:
    """Reject unexpected text/fields instead of copying arbitrary application logs."""
    event = json.loads(message)
    if (
        not isinstance(event, dict)
        or event.get("kind") not in {"clip_pool_stats", "clip_pool_stats_unavailable"}
        or type(event.get("at_unix_ms")) is not int
    ):
        raise ValueError("invalid_pool_counter_event")
    expected = {"kind", "at_unix_ms"} | (
        {"stats", "pools"} if event["kind"] == "clip_pool_stats" else set()
    )
    if set(event) != expected:
        raise ValueError("unexpected_pool_counter_fields")
    for group in ("stats", "pools"):
        rows = event.get(group, [])
        if not isinstance(rows, list) or len(rows) > 8:
            raise ValueError("invalid_pool_counter_rows")
        for row in rows:
            if not isinstance(row, dict) or row.get("database") not in DATABASES:
                raise ValueError("unexpected_pool_database")
            for key, value in row.items():
                if key == "load_balance_hosts" and value is None:
                    continue
                if key == "database":
                    continue
                if key == "user" and value in ROLES:
                    continue
                if key == "pool_mode" and value in {"transaction", "statement"}:
                    continue
                if (
                    type(value) not in {int, float}
                    or not math.isfinite(value)
                    or value < 0
                ):
                    raise ValueError("non_numeric_pool_counter")
    return event


def collect(logs: Any, start: Any, end: Any) -> dict[str, Any]:
    """Keep every success/unavailable event in the bounded interval, with IDs."""
    events = []
    token = None
    seen_tokens = set()
    seen_events = set()
    while True:
        request = {
            "logGroupName": "/clip/test/pgbouncer",
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000),
            "filterPattern": '{ $.kind = "clip_pool_stats" || $.kind = "clip_pool_stats_unavailable" }',
            "limit": 1000,
        }
        if token:
            request["nextToken"] = token
        response = logs.filter_log_events(**request)
        for item in response.get("events", []):
            if item["eventId"] in seen_events:
                continue
            seen_events.add(item["eventId"])
            events.append(
                {
                    "event_id": item["eventId"],
                    "timestamp": item["timestamp"],
                    "value": safe_counter_event(item["message"]),
                }
            )
            if len(events) > 10000:
                raise ValueError("pool_counter_window_too_large")
        token = response.get("nextToken")
        if not token:
            break
        if token in seen_tokens:
            raise ValueError("pool_counter_pagination_repeated")
        seen_tokens.add(token)
    return {
        "events": events,
        "state": (
            "captured"
            if any(item["value"]["kind"] == "clip_pool_stats" for item in events)
            else "no_counter_data"
        ),
        "nfr_accepted": False,
        "limitation": "Log delivery can be delayed; retain missing/unavailable intervals and recollect into a new artifact.",
    }
