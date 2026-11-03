"""Build an offline NFR-01/02 preview from untouched k6 JSONL and a profile.

The report applies the two different NFR denominators, retains failed-work
accounting, and can never mark an NFR accepted or validate timing provenance.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

MAX_BYTES = 100_000_000
OUTCOMES = {
    "correct",
    "completed",
    "incorrect",
    "timeout",
    "throttled",
    "unauthorized",
    "http_error",
    "transport_error",
}


def _number(point: dict[str, Any]) -> float:
    value = point.get("data", {}).get("value")
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("invalid k6 metric value")
    return float(value)


def _quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _tags(point: dict[str, Any]) -> dict[str, Any]:
    tags = point.get("data", {}).get("tags") or {}
    if not isinstance(tags, dict):
        raise ValueError("invalid metric tags")
    return tags


def summarize(points: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    nfr = profile.get("nfr_id")
    if (
        nfr not in {"nfr-01", "nfr-02"}
        or profile.get("purpose") != "nfr-local-preparation"
    ):
        raise ValueError("local NFR preparation profile required")
    rate = 20 if nfr == "nfr-01" else 10
    warmup, measured = profile.get("warmup_seconds"), profile.get("measured_seconds")
    if (
        profile.get("rate_rps") != rate
        or warmup != 60
        or measured != 300
        or profile.get("drain_seconds") != 5
    ):
        raise ValueError("NFR schedule mismatch")
    cases_bytes = json.dumps(
        profile.get("cases"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    if hashlib.sha256(cases_bytes).hexdigest() != profile.get("case_bundle_sha256"):
        raise ValueError("NFR case bundle hash mismatch")
    expected = {"nfr_warmup": rate * warmup, "nfr_measured": rate * measured}
    # k6 metrics arrive as a tagged stream, so each phase combines counters,
    # outcome counts, and raw latency samples in one internal accumulator.
    records: dict[str, dict[str, Any]] = {
        phase: {
            "issued": 0,
            "http": 0,
            "dropped": 0,
            "invalid_clock": 0,
            "outcomes": Counter(),
            "latencies": [],
        }
        for phase in expected
    }
    tracked = {
        "clip_nfr_issued",
        "http_reqs",
        "dropped_iterations",
        "clip_nfr_clock_invalid",
        "clip_nfr_outcomes",
        "clip_nfr_elapsed_ms",
    }
    for point in points:
        if point.get("type") != "Point":
            continue
        metric = point.get("metric")
        if metric not in tracked:
            continue
        tags = _tags(point)
        scenario = tags.get("scenario")
        phase = scenario if metric == "dropped_iterations" else tags.get("phase")
        if phase not in records or scenario is not None and scenario != phase:
            raise ValueError("missing or invalid NFR phase")
        if metric != "dropped_iterations" and (
            tags.get("nfr_id") != nfr
            or tags.get("configuration") != profile.get("configuration")
            or tags.get("run_id") != profile.get("run_id")
        ):
            raise ValueError("NFR run identity missing or mismatched in metric")
        value = _number(point)
        record = records[phase]
        if (
            metric
            in {
                "clip_nfr_issued",
                "http_reqs",
                "clip_nfr_clock_invalid",
                "clip_nfr_outcomes",
            }
            and not value.is_integer()
        ):
            raise ValueError("counter metric must be an integer")
        if metric == "clip_nfr_issued":
            record["issued"] += int(value)
        elif metric == "http_reqs":
            record["http"] += int(value)
        elif metric == "dropped_iterations":
            record["dropped"] += int(value)
        elif metric == "clip_nfr_clock_invalid":
            record["invalid_clock"] += int(value)
        elif metric == "clip_nfr_outcomes":
            outcome = tags.get("outcome")
            if outcome not in OUTCOMES:
                raise ValueError("invalid NFR outcome")
            record["outcomes"][outcome] += int(value)
        elif metric == "clip_nfr_elapsed_ms":
            outcome = tags.get("outcome")
            if outcome not in OUTCOMES:
                raise ValueError("invalid NFR latency outcome")
            record["latencies"].append((value, outcome))

    phases: dict[str, Any] = {}
    complete = True
    delivery_complete = True
    for phase, row in records.items():
        outcomes = dict(row["outcomes"])
        finished = sum(outcomes.values())
        latency_counts = Counter(label for _, label in row["latencies"])
        labels_match = Counter(outcomes) == latency_counts
        issued = row["issued"]
        accounting = (
            issued == row["http"] == finished == len(row["latencies"])
            and row["invalid_clock"] == 0
            and labels_match
        )
        delivered = (
            issued + row["dropped"] == expected[phase]
            and row["dropped"] == 0
            and issued == expected[phase]
        )
        complete = complete and accounting
        delivery_complete = delivery_complete and delivered
        successful_ms = [
            duration
            for duration, label in row["latencies"]
            if label in {"correct", "completed"}
        ]
        phases[phase] = {
            "scheduled": expected[phase],
            "issued": issued,
            "http_requests": row["http"],
            "dropped_iterations": row["dropped"],
            "outcomes": outcomes,
            "invalid_clock_samples": row["invalid_clock"],
            "accounting_complete": accounting,
            "delivery_complete": delivered,
            "all_latency_ms": {
                f"p{p}": _quantile([v for v, _ in row["latencies"]], p / 100)
                for p in (50, 95, 99)
            },
            "successful_latency_ms": {
                f"p{p}": _quantile(successful_ms, p / 100) for p in (50, 95, 99)
            },
        }

    measured_row = records["nfr_measured"]
    measured_outcomes = measured_row["outcomes"]
    successful_outcome = "correct" if nfr == "nfr-01" else "completed"
    completed_success = measured_outcomes.get(successful_outcome, 0)
    fast_success = sum(
        1
        for duration, label in measured_row["latencies"]
        if label == successful_outcome and duration <= 1000
    )
    if nfr == "nfr-01":
        denominator = completed_success
        numerator = fast_success
        denominator_rule = "correctly completed browse requests"
    else:
        denominator = measured_row["issued"]
        numerator = fast_success
        denominator_rule = "all issued eligible indexed-search requests; unsuccessful HTTP responses and timeouts count as violations; ranking quality is measured separately by NFR-04"
    ratio = numerator / denominator if denominator else None
    return {
        "preview_only": True,
        "nfr_id": nfr,
        "configuration": profile["configuration"],
        "run_id": profile["run_id"],
        "nfr_accepted": False,
        "dataset_fingerprint": profile["dataset_fingerprint"],
        "case_bundle_sha256": profile["case_bundle_sha256"],
        "accounting_complete": complete,
        "delivery_complete": delivery_complete,
        "latency_timing_verified": False,
        "latency_provenance_limitation": "Monotonic samples are emitted by the custom extension, but this report does not prove the run used a hash-bound reviewed binary.",
        "denominator_rule": denominator_rule,
        "successful_responses_within_1000ms": numerator,
        "denominator": denominator,
        "fraction_within_1000ms": ratio,
        "threshold_met_in_preview": ratio is not None
        and ratio >= 0.95
        and complete
        and delivery_complete,
        "phases": phases,
        "infrastructure_metrics": {"status": "not_collected_local_preparation"},
        "raw_data": "Read only; source JSONL is not rewritten.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("raw", type=Path)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution-receipt", type=Path)
    parser.add_argument("--run-plan", type=Path)
    args = parser.parse_args()
    try:
        if (
            args.raw.stat().st_size > MAX_BYTES
            or args.profile.stat().st_size > 5_000_000
        ):
            raise ValueError("input too large")
        points = [
            json.loads(line)
            for line in args.raw.read_text().splitlines()
            if line.strip()
        ]
        profile = json.loads(args.profile.read_text())
        report = summarize(points, profile)
        if bool(args.execution_receipt) != bool(args.run_plan):
            raise ValueError("both execution receipt and run plan are required")
        if args.execution_receipt:
            try:
                from scripts.evaluation.k6.real_run_evidence import verify_execution

                binding = verify_execution(
                    args.execution_receipt,
                    args.run_plan,
                    args.raw,
                    args.profile,
                    workload_kind=profile["nfr_id"],
                    configuration=profile["configuration"],
                    run_id=profile["run_id"],
                )
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
                binding = {
                    "execution_artifact_binding_verified": False,
                    "failure_code": (
                        str(error)
                        if isinstance(error, ValueError)
                        else "execution_evidence_invalid"
                    ),
                    "nfr_accepted": False,
                }
            report["execution_provenance"] = binding
            report["latency_timing_verified"] = (
                binding.get("execution_artifact_binding_verified") is True
                and binding.get("latency_timing_binary_hash_bound") is True
            )
            if not report["latency_timing_verified"]:
                report["threshold_met_in_preview"] = False
            if report["latency_timing_verified"]:
                report["latency_provenance_limitation"] = (
                    "The raw output, checked profile, completed receipt, and monotonic-timer binary hash match the approved run plan; human validity review remains pending."
                )
        else:
            report["execution_provenance"] = None
        with args.output.open("x") as output:
            output.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        if not report["accounting_complete"] or not report["delivery_complete"]:
            raise SystemExit(1)
    except OSError, ValueError, KeyError, json.JSONDecodeError:
        parser.exit(2, "Could not produce a complete NFR preview report\n")


if __name__ == "__main__":
    main()
