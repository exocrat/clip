"""Actual billed duration must survive sanitization; execution time is insufficient."""

from __future__ import annotations
from typing import Any
import json
from types import SimpleNamespace
import pytest
from scripts.evaluation.lambda_billing import collect, parse_billed_usage


def report() -> dict[str, Any]:
    return {
        "timestamp": 1000,
        "logStreamName": "owned-stream",
        "message": "REPORT RequestId: abc-123 Duration: 15.00 ms Billed Duration: 4200 ms Memory Size: 3008 MB Max Memory Used: 500 MB Init Duration: 4180 ms",
    }


def test_billed_duration_is_not_execution_duration_and_ids_are_hashed() -> None:
    row = parse_billed_usage(report())
    assert row and row["billed_duration_ms"] == 4200 and row["memory_size_mib"] == 3008
    assert row["billed_gb_seconds"] == pytest.approx(4.2 * 3008 / 1024)
    assert "owned-stream" not in json.dumps(row) and "abc-123" not in json.dumps(row)


def test_structured_and_text_usage_are_equivalent() -> None:
    event = report()
    event["message"] = json.dumps(
        {
            "type": "platform.report",
            "record": {
                "requestId": "abc-123",
                "metrics": {
                    "durationMs": 15,
                    "billedDurationMs": 4200,
                    "memorySizeMB": 3008,
                },
            },
        }
    )
    assert parse_billed_usage(event) == parse_billed_usage(report())


def test_collection_rejects_conflicts_and_pagination_cycles() -> None:
    first = report()
    second = report()
    second["message"] = second["message"].replace("4200", "4201")
    logs = SimpleNamespace(filter_log_events=lambda **_: {"events": [first, second]})
    with pytest.raises(ValueError, match="conflicting"):
        collect(logs, "/aws/lambda/clip-exp03-exp261103", 1, 2000)
    logs = SimpleNamespace(
        filter_log_events=lambda **_: {"events": [first], "nextToken": "repeat"}
    )
    with pytest.raises(ValueError, match="pagination"):
        collect(logs, "/aws/lambda/clip-exp03-exp261103", 1, 2000)


def test_request_or_content_events_are_never_retained() -> None:
    assert parse_billed_usage({"message": "private app text"}) is None
    assert (
        parse_billed_usage(
            {
                "message": json.dumps(
                    {"event": "request_completed", "content": "private"}
                )
            }
        )
        is None
    )
    event = report()
    event["message"] = event["message"].replace("Billed Duration: 4200 ms", "")
    with pytest.raises(ValueError, match="missing"):
        parse_billed_usage(event)
