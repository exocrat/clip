"""Calculate the frozen EXP-07 weighted comparison from retained run reports.

This offline tool verifies report/cost bindings and applies the pre-run score
specification. It never accepts an NFR, validates deployment telemetry, or
turns a score into a product decision.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}\Z")
CONDITIONS = ("low", "normal", "burst")
REPETITIONS = (1, 2, 3)
WEIGHTS = {"burst": 0.35, "cost": 0.30, "normal": 0.20, "reliability": 0.15}
SENSITIVITY = (
    {"burst": 0.30, "cost": 0.30, "normal": 0.25, "reliability": 0.15},
    {"burst": 0.30, "cost": 0.40, "normal": 0.15, "reliability": 0.15},
)
RUN_KEYS = {
    "run_id",
    "configuration",
    "condition",
    "repetition",
    "validity",
    "validity_review",
    "report_path",
    "report_sha256",
    "cost_path",
    "cost_sha256",
}
INPUT_KEYS = {"format_version", "purpose", "score_spec", "eligibility", "runs"}
SPEC_KEYS = {
    "state",
    "frozen_before_results",
    "frozen_at_utc",
    "review_record",
    "cost_good_usd_per_1000",
    "cost_poor_usd_per_1000",
    "cost_model_reference",
}


def _canonical_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _repo_file(value: Any, limit: int) -> tuple[Path, bytes]:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise ValueError("unsafe_analysis_input_path")
    current = ROOT
    for part in Path(value).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("analysis_input_symlink")
    resolved = current.resolve(strict=True)
    if (
        not resolved.is_relative_to(ROOT)
        or not resolved.is_file()
        or resolved.stat().st_size > limit
    ):
        raise ValueError("analysis_input_not_bounded_repository_file")
    data = resolved.read_bytes()
    if len(data) > limit:
        raise ValueError("analysis_input_too_large")
    return resolved, data


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    if len(ordered) != 3:
        raise ValueError("three_valid_repetitions_required")
    return ordered[1]


def _score(value: float, good: float, poor: float) -> float:
    if not math.isfinite(value) or good < 0 or poor <= good:
        raise ValueError("invalid_score_value_or_anchors")
    return min(100.0, max(0.0, 100.0 * (poor - value) / (poor - good)))


def _validate_spec(spec: Any) -> dict[str, Any]:
    if not isinstance(spec, dict) or set(spec) != SPEC_KEYS:
        raise ValueError("frozen_score_spec_required")
    frozen_time = spec.get("frozen_at_utc")
    try:
        parsed_time = (
            datetime.fromisoformat(frozen_time.replace("Z", "+00:00"))
            if isinstance(frozen_time, str)
            else None
        )
    except ValueError:
        parsed_time = None
    if (
        spec["state"] != "frozen"
        or spec["frozen_before_results"] is not True
        or parsed_time is None
        or parsed_time.tzinfo is None
        or parsed_time.utcoffset() != timezone.utc.utcoffset(parsed_time)
        or not isinstance(spec["review_record"], str)
        or not spec["review_record"].strip()
        or not isinstance(spec["cost_model_reference"], str)
        or not spec["cost_model_reference"].strip()
        or isinstance(spec["cost_good_usd_per_1000"], bool)
        or not isinstance(spec["cost_good_usd_per_1000"], (int, float))
        or isinstance(spec["cost_poor_usd_per_1000"], bool)
        or not isinstance(spec["cost_poor_usd_per_1000"], (int, float))
        or spec["cost_good_usd_per_1000"] < 0
        or spec["cost_poor_usd_per_1000"] <= spec["cost_good_usd_per_1000"]
    ):
        raise ValueError("score_spec_not_frozen_or_cost_anchors_invalid")
    return spec


def _report_record(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    _, report_bytes = _repo_file(row["report_path"], 10_000_000)
    if _canonical_hash(report_bytes) != row["report_sha256"]:
        raise ValueError("derived_report_hash_mismatch")
    report = json.loads(report_bytes)
    if (
        not isinstance(report, dict)
        or report.get("run_id") != row["run_id"]
        or report.get("configuration") != row["configuration"]
        or report.get("selected_condition") != row["condition"]
        or report.get("nfr_accepted") is not False
        or report.get("accounting_complete") is not True
        or report.get("delivery_complete") is not True
    ):
        raise ValueError("comparison_report_binding_or_accounting_mismatch")
    provenance = report.get("execution_provenance")
    if (
        not isinstance(provenance, dict)
        or provenance.get("execution_artifact_binding_verified") is not True
        or provenance.get("execution_completed") is not True
    ):
        raise ValueError("receipt_bound_execution_report_required")
    phase = (report.get("client_metrics") or {}).get(f"{row['condition']}_measured")
    if (
        not isinstance(phase, dict)
        or phase.get("accounting_complete") is not True
        or phase.get("delivery_complete") is not True
        or phase.get("dropped_iterations") != 0
    ):
        raise ValueError("complete_measured_phase_required")
    issued, correct = phase.get("issued"), phase.get("correct")
    quantiles = phase.get("correct_latency_ms") or {}
    if (
        type(issued) is not int
        or issued < 1
        or type(correct) is not int
        or not 0 <= correct <= issued
        or any(
            isinstance(quantiles.get(key), bool)
            or not isinstance(quantiles.get(key), (int, float))
            or not math.isfinite(quantiles[key])
            or quantiles[key] < 0
            for key in ("p50_ms", "p95_ms", "p99_ms")
        )
    ):
        raise ValueError("invalid_comparison_phase_metrics")
    return report, phase


def _cost_record(row: dict[str, Any]) -> float:
    _, raw = _repo_file(row["cost_path"], 10_000)
    if _canonical_hash(raw) != row["cost_sha256"]:
        raise ValueError("cost_input_hash_mismatch")
    cost = json.loads(raw)
    if not isinstance(cost, dict) or set(cost) != {
        "run_id",
        "condition",
        "cost_usd",
        "cost_basis",
        "cost_source_reference",
    }:
        raise ValueError("reviewed_cost_input_required")
    if (
        cost["run_id"] != row["run_id"]
        or cost["condition"] != row["condition"]
        or cost["cost_basis"] not in {"estimated", "billing"}
        or not isinstance(cost["cost_source_reference"], str)
        or not cost["cost_source_reference"].strip()
    ):
        raise ValueError("cost_input_binding_mismatch")
    amount = cost["cost_usd"]
    if not isinstance(amount, str) or not re.fullmatch(
        r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?", amount
    ):
        raise ValueError("invalid_cost_amount")
    try:
        amount_value = Decimal(amount)
    except InvalidOperation:
        raise ValueError("invalid_cost_amount") from None
    report, phase = _report_record(row)
    correct = phase["correct"]
    if correct == 0:
        raise ValueError("cost_per_1000_correct_unavailable")
    return float(amount_value * 1000 / correct)


def analyze(value: Any) -> dict[str, Any]:
    """Apply frozen scoring and uncertainty rules to exact, reviewed inputs."""
    if (
        not isinstance(value, dict)
        or set(value) != INPUT_KEYS
        or value["format_version"] != 1
        or value["purpose"] != "exp07-offline-analysis-input"
    ):
        raise ValueError("invalid_analysis_input")
    spec = _validate_spec(value["score_spec"])
    eligibility = value["eligibility"]
    if not isinstance(eligibility, dict) or set(eligibility) != {"A", "B"}:
        raise ValueError("reviewed_architecture_eligibility_required")
    for config in ("A", "B"):
        decision = eligibility[config]
        if (
            not isinstance(decision, dict)
            or set(decision) != {"status", "review_record"}
            or decision["status"] not in {"eligible", "ineligible", "unknown"}
            or not isinstance(decision["review_record"], str)
            or not decision["review_record"].strip()
        ):
            raise ValueError("invalid_eligibility_review")
    runs = value["runs"]
    if not isinstance(runs, list) or len(runs) != 18:
        raise ValueError("all_18_comparison_runs_required")
    found: dict[tuple[str, str, int], dict[str, Any]] = {}
    run_ids: set[str] = set()
    exclusions = []
    all_rows = []
    for row in runs:
        if (
            not isinstance(row, dict)
            or set(row) != RUN_KEYS
            or not isinstance(row["run_id"], str)
            or not RUN_ID.fullmatch(row["run_id"])
        ):
            raise ValueError("invalid_run_record")
        key = (row["configuration"], row["condition"], row["repetition"])
        if (
            row["configuration"] not in {"A", "B"}
            or row["condition"] not in CONDITIONS
            or type(row["repetition"]) is not int
            or row["repetition"] not in REPETITIONS
            or key in found
            or row["run_id"] in run_ids
        ):
            raise ValueError("duplicate_or_invalid_run_slot")
        if (
            row["validity"] not in {"valid", "invalid", "incomplete"}
            or not isinstance(row["validity_review"], str)
            or not row["validity_review"].strip()
        ):
            raise ValueError("run_validity_review_required")
        if not SHA256.fullmatch(row["report_sha256"]) or not SHA256.fullmatch(
            row["cost_sha256"]
        ):
            raise ValueError("run_artifact_hash_required")
        found[key] = row
        run_ids.add(row["run_id"])
        if row["validity"] != "valid":
            exclusions.append(
                {
                    "run_id": row["run_id"],
                    "configuration": row["configuration"],
                    "condition": row["condition"],
                    "repetition": row["repetition"],
                    "validity": row["validity"],
                    "reason": row["validity_review"],
                    "preserved": True,
                }
            )
        all_rows.append(row)
    expected = {
        (config, condition, repetition)
        for config in ("A", "B")
        for condition in CONDITIONS
        for repetition in REPETITIONS
    }
    if set(found) != expected:
        raise ValueError(
            "comparison_matrix_must_cover_A_B_three_conditions_three_repetitions"
        )

    metrics: dict[str, dict[str, dict[str, list[float]]]] = {
        config: {
            condition: {
                "p50_ms": [],
                "p95_ms": [],
                "p99_ms": [],
                "cost_per_1000": [],
                "failure_percent": [],
            }
            for condition in CONDITIONS
        }
        for config in ("A", "B")
    }
    normal_route_values: dict[str, dict[str, dict[str, list[float]]]] = {
        config: {
            route: {"p95_ms": [], "failure_percent": []}
            for route in ("browse", "search", "detail")
        }
        for config in ("A", "B")
    }
    correctness_floor_passed = {"A": True, "B": True}
    for row in all_rows:
        if row["validity"] != "valid":
            continue
        report, phase = _report_record(row)
        for percentile in ("p50_ms", "p95_ms", "p99_ms"):
            metrics[row["configuration"]][row["condition"]][percentile].append(
                float(phase["correct_latency_ms"][percentile])
            )
        metrics[row["configuration"]][row["condition"]]["cost_per_1000"].append(
            _cost_record(row)
        )
        metrics[row["configuration"]][row["condition"]]["failure_percent"].append(
            100 * (phase["issued"] - phase["correct"]) / phase["issued"]
        )
        correctness_floor_passed[row["configuration"]] = (
            correctness_floor_passed[row["configuration"]]
            and phase["correct"] / phase["issued"] >= 0.95
        )
        if row["condition"] == "normal":
            for route, route_row in (phase.get("routes") or {}).items():
                if route not in normal_route_values[row["configuration"]]:
                    continue
                route_issued = route_row.get("issued")
                route_correct = route_row.get("outcomes", {}).get("correct", 0)
                route_p95 = (route_row.get("correct_latency_ms") or {}).get("p95_ms")
                if (
                    type(route_issued) is int
                    and route_issued > 0
                    and type(route_correct) is int
                    and 0 <= route_correct <= route_issued
                    and isinstance(route_p95, (int, float))
                    and not isinstance(route_p95, bool)
                    and math.isfinite(route_p95)
                ):
                    normal_route_values[row["configuration"]][route]["p95_ms"].append(
                        float(route_p95)
                    )
                    normal_route_values[row["configuration"]][route][
                        "failure_percent"
                    ].append(100 * (route_issued - route_correct) / route_issued)

    normal_class_guard: dict[str, Any] = {}
    for route in ("browse", "search", "detail"):
        a = normal_route_values["A"][route]
        b = normal_route_values["B"][route]
        complete = (
            len(a["p95_ms"])
            == len(a["failure_percent"])
            == len(b["p95_ms"])
            == len(b["failure_percent"])
            == 3
        )
        if complete:
            a_p95, b_p95 = _median(a["p95_ms"]), _median(b["p95_ms"])
            a_failure, b_failure = _median(a["failure_percent"]), _median(
                b["failure_percent"]
            )
            max_p95 = a_p95 + max(50.0, 0.10 * a_p95)
            normal_class_guard[route] = {
                "A_median_p95_ms": a_p95,
                "B_median_p95_ms": b_p95,
                "B_p95_limit_ms": max_p95,
                "A_median_failure_percent": a_failure,
                "B_median_failure_percent": b_failure,
                "B_failure_limit_percent": a_failure + 1.0,
                "complete": True,
                "passed": b_p95 <= max_p95 and b_failure <= a_failure + 1.0,
            }
        else:
            normal_class_guard[route] = {
                "complete": False,
                "passed": False,
                "failure_reason": "three valid route-level reports required for both configurations",
            }
    normal_class_guard_passed = all(
        row["passed"] for row in normal_class_guard.values()
    )
    effective_eligible = {
        "A": eligibility["A"]["status"] == "eligible" and correctness_floor_passed["A"],
        "B": eligibility["B"]["status"] == "eligible"
        and correctness_floor_passed["B"]
        and normal_class_guard_passed,
    }

    summaries: dict[str, Any] = {}
    scores: dict[str, dict[str, Any]] = {}
    all_valid = not exclusions
    for config in ("A", "B"):
        summaries[config] = {}
        p95_values: dict[str, float] = {}
        cost_values: dict[str, float] = {}
        failure_values: dict[str, float] = {}
        for condition in CONDITIONS:
            current = metrics[config][condition]
            complete = all(len(current[field]) == 3 for field in current)
            all_valid = all_valid and complete
            row = {
                field: {
                    "per_run": values,
                    "median": _median(values) if len(values) == 3 else None,
                    "minimum": min(values) if values else None,
                    "maximum": max(values) if values else None,
                }
                for field, values in current.items()
            }
            summaries[config][condition] = row
            if complete:
                p95_values[condition] = row["p95_ms"]["median"]
                cost_values[condition] = row["cost_per_1000"]["median"]
                failure_values[condition] = row["failure_percent"]["median"]
        if (
            all(condition in p95_values for condition in CONDITIONS)
            and effective_eligible[config]
        ):
            reliability = max(failure_values["normal"], failure_values["burst"])
            inputs = {
                "burst": p95_values["burst"],
                "cost": cost_values["normal"],
                "normal": p95_values["normal"],
                "reliability": reliability,
            }
            points = {
                "burst": _score(inputs["burst"], 500, 3000),
                "cost": _score(
                    inputs["cost"],
                    float(spec["cost_good_usd_per_1000"]),
                    float(spec["cost_poor_usd_per_1000"]),
                ),
                "normal": _score(inputs["normal"], 250, 1000),
                "reliability": _score(inputs["reliability"], 0, 5),
            }
            scores[config] = {
                "inputs": inputs,
                "metric_points": points,
                "weighted_contributions": {
                    key: points[key] * WEIGHTS[key] for key in WEIGHTS
                },
                "total_points": sum(points[key] * WEIGHTS[key] for key in WEIGHTS),
                "sensitivity_totals": [
                    sum(points[key] * weights[key] for key in weights)
                    for weights in SENSITIVITY
                ],
            }
    paired_differences: list[dict[str, Any]] = []
    for repetition in REPETITIONS:
        if not effective_eligible["A"] or not effective_eligible["B"]:
            paired_differences.append(
                {"repetition": repetition, "difference_B_minus_A": None}
            )
            continue
        pair_complete = all(
            len(metrics[config][condition]["p95_ms"]) == 3
            for config in ("A", "B")
            for condition in CONDITIONS
        )
        if not pair_complete:
            paired_differences.append(
                {"repetition": repetition, "difference_B_minus_A": None}
            )
            continue
        per_config: dict[str, dict[str, dict[str, float] | None]] = {}
        for config in ("A", "B"):
            values: dict[str, dict[str, float] | None] = {
                condition: None for condition in CONDITIONS
            }
            for condition in CONDITIONS:
                row = found[(config, condition, repetition)]
                if row["validity"] != "valid":
                    values[condition] = None
                    break
                _, phase = _report_record(row)
                values[condition] = {
                    "p95_ms": float(phase["correct_latency_ms"]["p95_ms"]),
                    "cost_per_1000": _cost_record(row),
                    "failure_percent": 100
                    * (phase["issued"] - phase["correct"])
                    / phase["issued"],
                }
            per_config[config] = values
        if any(
            any(per_config[c][condition] is None for condition in CONDITIONS)
            for c in ("A", "B")
        ):
            difference = None
        else:
            for config in ("A", "B"):
                for condition in CONDITIONS:
                    assert per_config[config][condition] is not None
            total: dict[str, float] = {}
            for config in ("A", "B"):
                a_normal = per_config[config]["normal"]
                a_burst = per_config[config]["burst"]
                assert a_normal is not None and a_burst is not None
                inp = {
                    "burst": a_burst["p95_ms"],
                    "cost": a_normal["cost_per_1000"],
                    "normal": a_normal["p95_ms"],
                    "reliability": max(
                        a_normal["failure_percent"], a_burst["failure_percent"]
                    ),
                }
                pts = {
                    "burst": _score(inp["burst"], 500, 3000),
                    "cost": _score(
                        inp["cost"],
                        float(spec["cost_good_usd_per_1000"]),
                        float(spec["cost_poor_usd_per_1000"]),
                    ),
                    "normal": _score(inp["normal"], 250, 1000),
                    "reliability": _score(inp["reliability"], 0, 5),
                }
                total[config] = sum(pts[key] * WEIGHTS[key] for key in WEIGHTS)
            difference = total["B"] - total["A"]
        paired_differences.append(
            {"repetition": repetition, "difference_B_minus_A": difference}
        )

    if not all_valid:
        selection = "inconclusive_missing_or_invalid_run"
    elif (
        effective_eligible["A"]
        and not effective_eligible["B"]
        and eligibility["B"]["status"] != "unknown"
    ):
        selection = "A_only_eligible"
    elif (
        effective_eligible["B"]
        and not effective_eligible["A"]
        and eligibility["A"]["status"] == "ineligible"
    ):
        selection = "B_only_eligible"
    elif "unknown" in {eligibility["A"]["status"], eligibility["B"]["status"]}:
        selection = "inconclusive_eligibility_unknown"
    elif not scores:
        selection = "neither_alternative_eligible"
    elif not effective_eligible["A"] or not effective_eligible["B"]:
        selection = "no_eligible_alternative"
    elif abs(scores["A"]["total_points"] - scores["B"]["total_points"]) <= 3:
        selection = "practical_tie"
    elif any(row["difference_B_minus_A"] is None for row in paired_differences) or min(
        row["difference_B_minus_A"]
        for row in paired_differences
        if row["difference_B_minus_A"] is not None
    ) <= 0 <= max(
        row["difference_B_minus_A"]
        for row in paired_differences
        if row["difference_B_minus_A"] is not None
    ):
        selection = "inconclusive_paired_differences_cross_zero"
    elif scores["B"]["total_points"] > scores["A"]["total_points"]:
        selection = "B_higher_score"
    else:
        selection = "A_higher_score"
    return {
        "format_version": 1,
        "purpose": "exp07-analysis-preview",
        "analysis_complete": all_valid,
        "eligibility_reviews": eligibility,
        "effective_eligibility_for_scoring": effective_eligible,
        "all_runs_meet_95_percent_correctness_floor": correctness_floor_passed,
        "normal_per_class_no_degradation_guard": normal_class_guard,
        "run_exclusions": exclusions,
        "run_summaries": summaries,
        "frozen_score_spec_sha256": _canonical_hash(
            json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()
        ),
        "frozen_cost_model_reference": spec["cost_model_reference"],
        "primary_weights": WEIGHTS,
        "scores": scores,
        "paired_total_score_differences_B_minus_A": paired_differences,
        "sensitivity_weights": list(SENSITIVITY),
        "selection_status": selection,
        "nfr_accepted": False,
        "product_eligibility_accepted": False,
        "raw_data_modified": False,
        "human_calculation_and_validity_review_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > 20_000_000:
            raise ValueError("analysis_input_too_large")
        value = json.loads(args.input.read_text(encoding="utf-8"))
        report = analyze(value)
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(report, output, sort_keys=True, indent=2, allow_nan=False)
            output.write("\n")
        return 0 if report["analysis_complete"] else 1
    except OSError, ValueError, TypeError, KeyError, json.JSONDecodeError:
        parser.exit(2, "EXP-07 analysis refused; raw evidence was not changed\n")


if __name__ == "__main__":
    raise SystemExit(main())
