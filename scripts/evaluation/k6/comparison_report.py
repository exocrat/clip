"""Derive route-tagged accounting from immutable k6 JSON output.

This parser reports client-side request outcomes only. It cannot infer AWS or
PostgreSQL telemetry, and a complete local report never accepts an NFR.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / "data/evaluation/workloads/ecs-lambda-comparison-schedule-v1.json"
MAX_RAW_BYTES = 100_000_000
OUTCOMES = {
    "correct",
    "incorrect",
    "timeout",
    "throttled",
    "unauthorized",
    "http_error",
    "transport_error",
}
ROUTES = {"browse", "search", "detail"}


def quantile(values: list[float], probability: float) -> float | None:
    """Use R7 linear interpolation; an empty sample has no quantile."""
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower, upper = math.floor(index), math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def expected_cohorts(
    profile: dict[str, Any], condition: str | None = None
) -> dict[str, int]:
    """Translate the approved per-second rates into scheduled iterations."""
    if condition is not None and condition not in {"low", "normal", "burst"}:
        raise ValueError("Invalid condition")
    expected = {}
    matched = 0
    for item in profile["conditions"]:
        if condition is not None and item["name"] != condition:
            continue
        matched += 1
        for cohort, duration, rate_key in (
            ("warmup", profile["warmup_seconds"], "warmup_rate"),
            ("measured", profile["measured_seconds"], "measured_rate"),
        ):
            count = item[rate_key] * duration
            if (
                not isinstance(count, (int, float))
                or isinstance(count, bool)
                or not math.isfinite(count)
                or count < 1
                or not float(count).is_integer()
            ):
                raise ValueError(
                    "Cohort schedule must produce a positive integer request count"
                )
            expected[f"{item['name']}_{cohort}"] = int(count)
    if condition is not None and matched != 1:
        raise ValueError("Missing or duplicate condition")
    return expected


def _tags(point: dict[str, Any]) -> dict[str, Any]:
    tags = point.get("data", {}).get("tags") or {}
    return tags if isinstance(tags, dict) else {}


def _number(point: dict[str, Any]) -> float:
    value = point.get("data", {}).get("value")
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("Invalid k6 metric value")
    return float(value)


def _count(point: dict[str, Any]) -> int:
    value = _number(point)
    if not value.is_integer():
        raise ValueError("Counter metric must be an integer")
    return int(value)


def summarize_points(
    points: list[dict[str, Any]], profile: dict[str, Any], condition: str | None = None
) -> dict[str, Any]:
    """Summarize route and phase counters without changing or copying raw data."""
    expected = expected_cohorts(profile, condition)
    phases: dict[str, dict[str, Any]] = {
        name: {
            "scheduled": count,
            "issued": 0,
            "actual_http_requests": 0,
            "dropped_iterations": 0,
            "clock_invalid": 0,
            "uncompleted": 0,
            "outcomes": Counter(),
            "latencies": [],
            "route_data": defaultdict(
                lambda: {
                    "issued": 0,
                    "actual_http_requests": 0,
                    "outcomes": Counter(),
                    "latencies": [],
                }
            ),
        }
        for name, count in expected.items()
    }
    scenario_to_phase: dict[Any, str] = {
        name: name for name in expected_cohorts(profile)
    }
    tracked_metrics = {
        "clip_comparison_issued",
        "http_reqs",
        "dropped_iterations",
        "clip_comparison_clock_invalid",
        "clip_comparison_outcomes",
        "clip_comparison_elapsed_ms",
    }
    for point in points:
        if point.get("type") != "Point":
            continue
        metric = point.get("metric")
        tags = _tags(point)
        phase = tags.get("phase")
        scenario = tags.get("scenario")
        if condition is not None and metric in tracked_metrics:
            if scenario is not None and scenario not in scenario_to_phase:
                raise ValueError("Invalid scenario in run output")
            if phase is not None and scenario is not None and phase != scenario:
                raise ValueError("Scenario and phase mismatch")
            if metric == "dropped_iterations":
                phase = scenario_to_phase.get(scenario, phase)
            if phase not in scenario_to_phase:
                raise ValueError("Missing or invalid phase in run output")
            if phase not in phases:
                raise ValueError("Unexpected condition in run output")
        elif metric == "dropped_iterations":
            phase = scenario_to_phase.get(scenario, phase)
        if phase not in phases:
            continue
        record = phases[phase]
        route = tags.get("kind")
        if route is not None and route not in ROUTES:
            raise ValueError("Unexpected route tag")
        if (
            condition is not None
            and metric in tracked_metrics - {"dropped_iterations"}
            and route is None
        ):
            raise ValueError("Missing route tag")
        route_record = record["route_data"][route] if route else None
        value = _number(point)

        if metric == "clip_comparison_issued":
            count = _count(point)
            record["issued"] += count
            if route_record is not None:
                route_record["issued"] += count
        elif metric == "http_reqs":
            count = _count(point)
            record["actual_http_requests"] += count
            if route_record is not None:
                route_record["actual_http_requests"] += count
        elif metric == "dropped_iterations":
            record["dropped_iterations"] += _count(point)
        elif metric == "clip_comparison_clock_invalid":
            record["clock_invalid"] += _count(point)
        elif metric == "clip_comparison_outcomes":
            outcome = tags.get("outcome")
            if outcome not in OUTCOMES:
                raise ValueError("Unexpected outcome tag")
            count = _count(point)
            record["outcomes"][outcome] += count
            if route_record is not None:
                route_record["outcomes"][outcome] += count
        elif metric == "clip_comparison_elapsed_ms":
            outcome = tags.get("outcome")
            if outcome not in OUTCOMES:
                raise ValueError("Unexpected latency outcome tag")
            record["latencies"].append((value, outcome))
            if route_record is not None:
                route_record["latencies"].append((value, outcome))

    result = {}
    for phase, record in phases.items():
        outcomes = dict(record["outcomes"])
        completed = sum(outcomes.values())
        correct = outcomes.get("correct", 0)
        dropped = record["dropped_iterations"]
        issued = record["issued"]
        actual = record["actual_http_requests"]
        expected_count = record["scheduled"]
        uncompleted = max(0, issued - min(completed, len(record["latencies"])))
        offered = issued + dropped
        successful_latencies = [
            duration
            for duration, outcome in record["latencies"]
            if outcome == "correct"
        ]
        all_latencies = [duration for duration, _ in record["latencies"]]
        route_results = {}
        route_accounting_matches = True
        for route, route_record in sorted(record["route_data"].items()):
            route_outcomes = dict(route_record["outcomes"])
            route_latencies = [duration for duration, _ in route_record["latencies"]]
            route_success_latencies = [
                duration
                for duration, outcome in route_record["latencies"]
                if outcome == "correct"
            ]
            route_outcomes_match = Counter(route_outcomes) == Counter(
                outcome for _, outcome in route_record["latencies"]
            )
            route_accounting = (
                route_record["issued"]
                == route_record["actual_http_requests"]
                == sum(route_outcomes.values())
                == len(route_record["latencies"])
                and route_outcomes_match
            )
            route_accounting_matches = route_accounting_matches and route_accounting
            route_results[route] = {
                "issued": route_record["issued"],
                "actual_http_requests": route_record["actual_http_requests"],
                "outcomes": route_outcomes,
                "outcome_latency_counts_match": route_outcomes_match,
                "accounting_complete": route_accounting,
                "all_completed_latency_ms": _quantiles(route_latencies),
                "correct_latency_ms": (
                    _quantiles(route_success_latencies) if route_accounting else None
                ),
            }
        outcome_count_matches_latency = Counter(outcomes) == Counter(
            outcome for _, outcome in record["latencies"]
        )
        result[phase] = {
            "scheduled": expected_count,
            "issued": issued,
            "actual_http_requests": actual,
            "completed": completed,
            "uncompleted": uncompleted,
            "dropped_iterations": dropped,
            "clock_invalid": record["clock_invalid"],
            "schedule_shortfall": max(0, expected_count - offered),
            "schedule_matches": offered == expected_count,
            "offered_requests": offered,
            "offered_rps": offered
            / (
                profile["warmup_seconds"]
                if phase.endswith("warmup")
                else profile["measured_seconds"]
            ),
            "correct": correct,
            "failed": completed - correct,
            "timeouts": outcomes.get("timeout", 0),
            "throttled": outcomes.get("throttled", 0),
            "outcomes": outcomes,
            "successful_rps": correct
            / (
                profile["warmup_seconds"]
                if phase.endswith("warmup")
                else profile["measured_seconds"]
            ),
            "all_completed_latency_ms": _quantiles(all_latencies),
            "correct_latency_ms": (
                _quantiles(successful_latencies)
                if outcome_count_matches_latency and route_accounting_matches
                else None
            ),
            "routes": route_results,
            "route_accounting_matches": route_accounting_matches,
            "accounting_complete": issued
            == actual
            == completed
            == len(record["latencies"])
            and record["clock_invalid"] == 0
            and outcome_count_matches_latency
            and route_accounting_matches,
            "delivery_complete": issued + dropped == expected_count
            and dropped == 0
            and issued == expected_count,
            "outcome_latency_counts_match": outcome_count_matches_latency,
        }

    accounting_complete = all(item["accounting_complete"] for item in result.values())
    delivery_complete = all(item["delivery_complete"] for item in result.values())
    return {
        "preview_only": True,
        "selected_condition": condition,
        "nfr_accepted": False,
        "accounting_complete": accounting_complete,
        "delivery_complete": delivery_complete,
        "latency_timing_verified": False,
        "individual_request_outcome_binding_verified": False,
        "latency_limitation": (
            "Preview only: timing now uses the repository's monotonic k6 "
            "extension, but the run is not bound to its custom binary hash. "
            "Complete accounting alone does not validate timing provenance."
        ),
        "client_metrics": result,
        "infrastructure_metrics": {
            "status": "not_collected_local_preparation",
            "required": [
                "ECS task health/count/scaling",
                "Lambda concurrency/cold starts/errors/throttles",
                "PostgreSQL latency/connections/saturation",
            ],
        },
        "raw_data": "Read only; this report is a derived calculation and does not rewrite the k6 file.",
    }


def _quantiles(values: list[float]) -> dict[str, Any]:
    return {
        f"p{percentile}_ms": quantile(values, percentile / 100)
        for percentile in (50, 95, 99)
    } | {"samples": len(values)}


def summarize_file(
    raw_path: Path, profile_path: Path = PROFILE, condition: str | None = None
) -> dict[str, Any]:
    if raw_path.stat().st_size > MAX_RAW_BYTES:
        raise ValueError("k6 raw output exceeds size limit")
    profile = json.loads(profile_path.read_text())
    points = [
        json.loads(line) for line in raw_path.read_text().splitlines() if line.strip()
    ]
    return summarize_points(points, profile, condition)


def bound_schedule(plan: dict[str, Any], run_dir: Path) -> Path:
    """Use the immutable schedule actually staged for a formal comparison.

    Formal case profiles contain cases/capacity, while their separate schedule
    defines offered counts. Pilot profiles include both. Keep the original case
    profile for execution-hash checks and verify the staged schedule separately.
    """
    stage = run_dir / "stage-root" / str(plan["run_id"])
    record = json.loads((stage / "staged-files.json").read_text())
    schedule = stage / "schedule.json"
    if (
        record.get("run_id") != plan["run_id"]
        or record.get("condition") != plan["condition"]
        or hashlib.sha256(schedule.read_bytes()).hexdigest()
        != record.get("files", {}).get("schedule.json")
    ):
        raise ValueError("staged_schedule_binding_mismatch")
    return schedule


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("raw", type=Path, help="unchanged k6 --out json=... file")
    parser.add_argument(
        "--output", type=Path, help="new report path; refuses overwrite"
    )
    parser.add_argument(
        "--condition", choices=("low", "normal", "burst"), required=True
    )
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--execution-receipt", type=Path)
    parser.add_argument("--run-plan", type=Path)
    args = parser.parse_args()
    try:
        if bool(args.execution_receipt) != bool(args.run_plan):
            raise ValueError("both execution receipt and run plan are required")
        profile_path = args.profile or PROFILE
        run_plan = json.loads(args.run_plan.read_text()) if args.run_plan else None
        profile_input = json.loads(profile_path.read_text())
        schedule_path = profile_path
        if "conditions" not in profile_input:
            if run_plan is None or run_plan.get("workload_kind") != "comparison":
                raise ValueError("formal_comparison_run_plan_required")
            schedule_path = bound_schedule(run_plan, args.raw.parent)
        report = summarize_file(args.raw, schedule_path, args.condition)
        if args.execution_receipt:
            assert isinstance(run_plan, dict)
            try:
                from scripts.evaluation.k6.real_run_evidence import verify_execution

                profile = json.loads(profile_path.read_text())
                workload_kind = (
                    "exp05-pilot"
                    if profile.get("purpose") == "exp05-pilot-workload"
                    else "comparison"
                )
                binding = verify_execution(
                    args.execution_receipt,
                    args.run_plan,
                    args.raw,
                    profile_path,
                    workload_kind=workload_kind,
                    configuration=run_plan["configuration"],
                    run_id=run_plan["run_id"],
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
        else:
            report["execution_provenance"] = None
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            with args.output.open("x") as stream:
                stream.write(rendered)
        else:
            sys.stdout.write(rendered)
        if not report["accounting_complete"] or not report["delivery_complete"]:
            raise SystemExit(1)
    except OSError, ValueError, KeyError, json.JSONDecodeError:
        parser.exit(2, "Could not produce a complete comparison accounting report\n")


if __name__ == "__main__":
    main()
