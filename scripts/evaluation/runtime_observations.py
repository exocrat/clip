"""Join safe server correlation metadata to immutable client timing samples.

No response bodies, cookies, query text or raw log messages are retained. A
platform Init Duration proves observed initialization; a missing report or ID
remains unknown. Warm-up and measured intervals are never silently combined.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, TypedDict

from scripts.evaluation.k6.comparison_report import quantile
from scripts.evaluation.k6.lambda_initialization import parse_event

UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z"
)
HASH = re.compile(r"[0-9a-f]{64}\Z")
ELAPSED = {"clip_comparison_elapsed_ms", "clip_nfr_elapsed_ms", "clip_nfr03_elapsed_ms"}
STAGES = frozenset(
    [
        "identity.account_lookup",
        "identity.authenticate",
        "identity.eligibility",
        "identity.pool_acquire",
        "identity.session_lookup",
        "identity.session_touch",
        "identity.transaction_setup",
        "listings.browse",
        "listings.detail",
        "listings.pool_acquire",
        "listings.search",
        "listings.snapshot",
    ]
)


def stage_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """Retain only allowlisted numeric stage timings and hashed correlation."""
    try:
        body = json.loads(event.get("message", ""))
    except TypeError, ValueError:
        return None
    if not isinstance(body, dict) or body.get("event") != "request_stage":
        return None
    identifier = body.get("request_id")
    duration: Any = body.get("duration_ms")
    if (
        body.get("stage") not in STAGES
        or not isinstance(identifier, str)
        or not UUID.fullmatch(identifier)
        or type(duration) not in (int, float)
        or not math.isfinite(duration)
        or duration < 0
        or type(event.get("timestamp")) is not int
    ):
        return None
    return {
        "request_id_sha256": hashlib.sha256(identifier.encode()).hexdigest(),
        "stage": body["stage"],
        "duration_ms": duration,
        "timestamp_ms": event["timestamp"],
    }


def invocation_start(event: dict[str, Any]) -> dict[str, Any] | None:
    """Sanitize platform START records for unambiguous invocation boundaries."""
    message = event.get("message", "")
    match = (
        re.match(r"^START RequestId:\s+([A-Za-z0-9-]{1,100})\s", message)
        if isinstance(message, str)
        else None
    )
    if match:
        identifier = match[1]
    else:
        try:
            body = json.loads(message)
        except TypeError, ValueError:
            return None
        if not isinstance(body, dict) or body.get("type") != "platform.start":
            return None
        record = body.get("record", {})
        identifier = record.get("requestId") if isinstance(record, dict) else None
    if (
        not isinstance(identifier, str)
        or not re.fullmatch(r"[A-Za-z0-9-]{1,100}", identifier)
        or type(event.get("timestamp")) is not int
    ):
        return None
    return {
        "request_id_sha256": hashlib.sha256(identifier.encode()).hexdigest(),
        "log_stream_sha256": hashlib.sha256(
            str(event.get("logStreamName", "")).encode()
        ).hexdigest(),
        "timestamp_ms": event["timestamp"],
    }


def request_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """Allow only the server-generated ID and numeric request completion fields."""
    try:
        body = json.loads(event.get("message", ""))
    except TypeError, ValueError:
        return None
    if not isinstance(body, dict) or body.get("event") not in {
        "request_completed",
        "request_failed",
    }:
        return None
    identifier = body.get("request_id")
    duration: Any = body.get("duration_ms")
    if (
        not isinstance(identifier, str)
        or not UUID.fullmatch(identifier)
        or type(duration) not in (int, float)
        or not math.isfinite(duration)
        or duration < 0
        or type(event.get("timestamp")) is not int
        or not isinstance(event.get("logStreamName"), str)
        or not event["logStreamName"]
        or type(body.get("status")) is not int
        or not 100 <= body["status"] <= 599
    ):
        return None
    return {
        "request_id_sha256": hashlib.sha256(identifier.encode()).hexdigest(),
        "log_stream_sha256": hashlib.sha256(
            event["logStreamName"].encode()
        ).hexdigest(),
        "timestamp_ms": event["timestamp"],
        "server_duration_ms": duration,
        "status": body["status"],
    }


def collect(logs: Any, group: str, start_ms: int, end_ms: int) -> dict[str, Any]:
    """Bound CloudWatch pagination; sanitize each event before returning anything."""
    requests: dict[str, dict[str, Any]] = {}
    platforms: dict[tuple[str, str], dict[str, Any]] = {}
    starts: dict[tuple[str, str], dict[str, Any]] = {}
    stages: dict[Any, dict[str, Any]] = {}
    seen: set[str] = set()
    token = None
    count = 0
    for _ in range(100):
        args = dict(logGroupName=group, startTime=start_ms, endTime=end_ms, limit=10000)
        if token:
            args["nextToken"] = token
        response = logs.filter_log_events(**args)
        events = response.get("events")
        if not isinstance(events, list):
            raise ValueError("runtime_events_missing")
        count += len(events)
        if count > 400_000:
            raise ValueError("runtime_event_cap_exceeded")
        for event in events:
            if not start_ms <= event.get("timestamp", -1) < end_ms:
                continue
            app = request_event(event)
            stage = stage_event(event)
            if stage:
                stage_key = event.get("eventId") or tuple(stage.values())
                stages[stage_key] = stage
            if app:
                key = app["request_id_sha256"]
                if key in requests and requests[key] != app:
                    raise ValueError("conflicting_request_log")
                requests[key] = app
            platform = parse_event(event)
            if platform:
                key = (platform["request_id_sha256"], platform["log_stream_sha256"])
                if key in platforms and platforms[key] != platform:
                    raise ValueError("conflicting_initialization_log")
                platforms[key] = platform
            start = invocation_start(event)
            if start:
                key = (start["request_id_sha256"], start["log_stream_sha256"])
                if key in starts and starts[key] != start:
                    raise ValueError("conflicting_invocation_start")
                starts[key] = start
        token = response.get("nextToken")
        if not token:
            return {
                "requests": list(requests.values()),
                "platform_reports": list(platforms.values()),
                "invocation_starts": list(starts.values()),
                "stages": list(stages.values()),
                "collection_complete": True,
            }
        if not isinstance(token, str) or token in seen:
            raise ValueError("runtime_pagination_invalid")
        seen.add(token)
    raise ValueError("runtime_page_cap_exceeded")


class _Phase(TypedDict):
    """Typed accumulator for one phase; stages remain separate nested spans."""

    latencies: list[float]
    correlated: int
    unattributed: int
    outcomes: Counter[str]
    streams: set[str]
    confirmed_init_latencies: list[float]


def _new_phase() -> _Phase:
    """Construct fresh mutable counters for exactly one workload phase."""
    return {
        "latencies": [],
        "correlated": 0,
        "unattributed": 0,
        "outcomes": Counter(),
        "streams": set(),
        "confirmed_init_latencies": [],
    }


def summarize(raw: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    """Keep phase distributions and unknowns; never infer a cold request by speed.

    Lambda's invocation ID differs from the application's UUID. A confirmed
    cold sample requires one completion between matching platform START/REPORT
    records in the same stream, plus explicit Init Duration. Missing/ambiguous
    boundaries remain unattributed; no-init does not by itself prove warmth.
    """
    requests = {row["request_id_sha256"]: row for row in evidence["requests"]}
    starts = {
        (row["request_id_sha256"], row["log_stream_sha256"]): row
        for row in evidence.get("invocation_starts", [])
    }
    candidates = defaultdict(list)
    by_stream = defaultdict(list)
    for row in requests.values():
        by_stream[row["log_stream_sha256"]].append(row)
    for platform in evidence["platform_reports"]:
        key = (platform["request_id_sha256"], platform["log_stream_sha256"])
        start = starts.get(key)
        if start:
            matches = [
                row
                for row in by_stream[platform["log_stream_sha256"]]
                if start["timestamp_ms"]
                <= row["timestamp_ms"]
                <= platform["timestamp_ms"]
            ]
            if len(matches) == 1:
                candidates[matches[0]["request_id_sha256"]].append(platform)
    phases: defaultdict[str, _Phase] = defaultdict(_new_phase)
    seen = set()
    request_phases = {}
    with raw.open() as stream:
        for line in stream:
            point = json.loads(line)
            if point.get("type") != "Point" or point.get("metric") not in ELAPSED:
                continue
            data = point["data"]
            tags = data.get("tags", {})
            phase = tags.get("phase")
            index = tags.get("sample_index")
            value = data["value"]
            if not isinstance(phase, str) or not isinstance(index, str):
                raise ValueError("runtime_sample_identity_missing")
            key = (phase, index)
            if key in seen:
                raise ValueError("duplicate_runtime_sample")
            seen.add(key)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("invalid_runtime_latency")
            row = phases[phase]
            row["latencies"].append(value)
            row["outcomes"][tags.get("outcome", "unknown")] += 1
            digest = tags.get("request_id_sha256", "")
            match = (
                requests.get(digest)
                if isinstance(digest, str) and HASH.fullmatch(digest)
                else None
            )
            if match:
                request_phases[digest] = phase
                row["correlated"] += 1
                row["streams"].add(match["log_stream_sha256"])
                invocation = candidates.get(digest, [])
                if len(invocation) == 1 and invocation[0]["initialization_observed"]:
                    row["confirmed_init_latencies"].append(value)
            else:
                row["unattributed"] += 1
    result = {}
    for phase, row in phases.items():
        values = row["latencies"]
        result[phase] = {
            "samples": len(values),
            "p50_ms": quantile(values, 0.5),
            "p95_ms": quantile(values, 0.95),
            "p99_ms": quantile(values, 0.99),
            "maximum_ms": max(values),
            "correlated": row["correlated"],
            "unattributed": row["unattributed"],
            "outcomes": dict(row["outcomes"]),
            "observed_streams_sha256": sorted(row["streams"]),
            "confirmed_initialization_client_samples": len(
                row["confirmed_init_latencies"]
            ),
            "confirmed_initialization_client_p95_ms": quantile(
                row["confirmed_init_latencies"], 0.95
            ),
        }
    init = [
        row for row in evidence["platform_reports"] if row["initialization_observed"]
    ]
    stage_totals: defaultdict[tuple[str, str, str], float] = defaultdict(float)
    unattributed_stages = 0
    for stage in evidence.get("stages", []):
        phase = request_phases.get(stage["request_id_sha256"])
        if phase is None:
            unattributed_stages += 1
        else:
            stage_totals[(phase, stage["stage"], stage["request_id_sha256"])] += stage[
                "duration_ms"
            ]
    stage_samples = defaultdict(list)
    for (phase, name, _), value in stage_totals.items():
        stage_samples[(phase, name)].append(value)
    return {
        "format_version": 1,
        "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "phases": result,
        "initialization_observations": init,
        "initialization_count": len(init),
        "missing_initialization_means_warm": False,
        "cold_request_latency_attribution_verified": any(
            row["confirmed_initialization_client_samples"] for row in result.values()
        ),
        "collection_complete": evidence.get("collection_complete") is True,
        "stage_timings": [
            {
                "phase": phase,
                "stage": name,
                "requests": len(values),
                "p50_ms": quantile(values, 0.5),
                "p95_ms": quantile(values, 0.95),
                "p99_ms": quantile(values, 0.99),
            }
            for (phase, name), values in sorted(stage_samples.items())
        ],
        "unattributed_stage_events": unattributed_stages,
        "nested_stages_must_not_be_summed": True,
        "nfr_accepted": False,
    }
