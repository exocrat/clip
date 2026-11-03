"""Convert synthetic chat events to NFR-05 preview input without a browser.

Callers supply timestamps; this helper neither captures nor verifies real UI
events or the clock and must not be used as proof of a measured outcome.
"""

from __future__ import annotations

from typing import Any

from scripts.evaluation.nfr05_report import DEADLINE_NS, SAMPLE_COUNT, summarize


def collect(events: Any) -> dict[str, Any]:
    """Pair bounded submission and explicit terminal events by sample index."""
    if not isinstance(events, list) or len(events) > 2 * SAMPLE_COUNT:
        raise ValueError("invalid_events")
    submissions: dict[int, int] = {}
    terminals: dict[int, tuple[str, int]] = {}
    for event in events:
        if not isinstance(event, dict) or set(event) != {"index", "event", "time_ns"}:
            raise ValueError("invalid_event")
        index, kind, timestamp = event["index"], event["event"], event["time_ns"]
        if type(index) is not int or index not in range(SAMPLE_COUNT):
            raise ValueError("invalid_index")
        if type(timestamp) is not int or timestamp < 0:
            raise ValueError("invalid_timestamp")
        if kind == "submitted":
            if index in submissions or index in terminals:
                raise ValueError("invalid_submission")
            submissions[index] = timestamp
        elif kind in ("displayed", "failed", "undisplayed"):
            if index in terminals:
                raise ValueError("duplicate_terminal")
            if kind != "failed" and index not in submissions:
                raise ValueError("submission_required")
            if index in submissions and timestamp < submissions[index]:
                raise ValueError("invalid_event_order")
            if kind == "undisplayed" and timestamp - submissions[index] < DEADLINE_NS:
                raise ValueError("deadline_not_reached")
            terminals[index] = (kind, timestamp)
        else:
            raise ValueError("invalid_event_kind")

    samples = []
    for index, (outcome, timestamp) in sorted(terminals.items()):
        samples.append(
            {
                "index": index,
                "outcome": outcome,
                "submitted_ns": submissions.get(index),
                "displayed_ns": timestamp if outcome == "displayed" else None,
            }
        )
    observations = {"samples": samples}
    return {"observations": observations, "preview": summarize(observations)}
