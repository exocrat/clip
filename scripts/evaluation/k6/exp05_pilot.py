"""Prepare EXP-05 weight candidates and score retained pilot summaries offline.

This module creates no AWS resources, starts no workload, and never accepts an
experiment. Its output plan is a draft that still needs exact human review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
LEGACY_WEIGHTS = (100, 75, 50, 25)
WEIGHTS = (100,)
REPETITIONS = 3


def build_plan(
    run_prefix: str,
    workload_sha256: str,
    target_binding_sha256: dict[str, str],
    *,
    max_successful_failure_share: float = 0.05,
) -> dict[str, Any]:
    """Create three ECS baseline and three full-offload candidate declarations."""
    if not RUN_ID.fullmatch(run_prefix) or len(run_prefix) > 40:
        raise ValueError("invalid_run_prefix")
    if not SHA256.fullmatch(workload_sha256) or not isinstance(
        target_binding_sha256, dict
    ):
        raise ValueError("pilot_fingerprints_required")
    if (
        isinstance(max_successful_failure_share, bool)
        or not isinstance(max_successful_failure_share, (int, float))
        or not 0 <= max_successful_failure_share <= 0.05
    ):
        raise ValueError("pilot_success_floor_must_be_at_least_95_percent")

    runs: list[dict[str, Any]] = []
    for repetition in range(1, REPETITIONS + 1):
        runs.append(
            {
                "run_id": f"{run_prefix}-base-r{repetition}",
                "configuration": "A",
                "lambda_weight_percent": 0,
                "ecs_weight_percent": 100,
                "repetition": repetition,
            }
        )
    for weight in WEIGHTS:
        for repetition in range(1, REPETITIONS + 1):
            runs.append(
                {
                    "run_id": f"{run_prefix}-l{weight}-r{repetition}",
                    "configuration": "B",
                    "lambda_weight_percent": weight,
                    "ecs_weight_percent": 100 - weight,
                    "repetition": repetition,
                }
            )
    if set(target_binding_sha256) != {row["run_id"] for row in runs} or any(
        not isinstance(value, str) or not SHA256.fullmatch(value)
        for value in target_binding_sha256.values()
    ):
        raise ValueError("all_pilot_target_plans_required")
    for row in runs:
        row["target_plan_sha256"] = target_binding_sha256[row["run_id"]]
    target_matrix_sha256 = hashlib.sha256(
        json.dumps(
            target_binding_sha256, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return {
        "schema_version": 2,
        "purpose": "exp05-pilot-candidates-not-authorization",
        "state": "draft",
        "execution_permitted": False,
        "pilot_result": False,
        "run_order": [
            "ecs_baseline",
            *[f"lambda_ecs_{weight}_{100-weight}" for weight in WEIGHTS],
        ],
        "workload": {
            "sha256": workload_sha256,
            "condition": "burst",
            "rate_rps": 50,
            "mix": {"browse": 50, "search": 30, "detail": 20},
            "warmup_seconds": 60,
            "measured_seconds": 120,
            "drain_seconds": 5,
            "timeout_seconds": 5,
            "retries": 0,
        },
        "candidate_weights_lambda_ecs_percent": [[100, 0]],
        "repetitions_per_weight": REPETITIONS,
        "baseline_repetitions": REPETITIONS,
        "selection_rule": "highest_lambda_weight_meeting_all_frozen_pilot_gates",
        "gates": {
            "minimum_correct_share": 1 - max_successful_failure_share,
            "zero_generator_drops": True,
            "complete_request_accounting": True,
            "resource_and_database_headroom_verified": True,
            "all_required_telemetry_present": True,
            "under_approved_run_cost_cap": True,
        },
        "target_binding_sha256": target_matrix_sha256,
        "runs": runs,
        "human_review": None,
        "approval_reference": None,
    }


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value >= 0
        and value < float("inf")
    )


def _phase(summary: Any) -> dict[str, Any]:
    """Read a measured phase from the common comparison report shape."""
    if not isinstance(summary, dict) or summary.get("preview_only") is not True:
        raise ValueError("comparison_preview_required")
    client = summary.get("client_metrics")
    if not isinstance(client, dict):
        raise ValueError("pilot_client_report_required")
    measured = client.get("burst_measured")
    if not isinstance(measured, dict):
        raise ValueError("pilot_burst_measured_summary_required")
    return measured


def _validate_plan(plan: Any) -> dict[str, Any]:
    """Enforce the fixed candidate matrix and refuse weakened pilot gates."""
    if (
        not isinstance(plan, dict)
        or plan.get("purpose") != "exp05-pilot-candidates-not-authorization"
        or type(plan.get("schema_version")) is not int
        or plan["schema_version"] not in (1, 2)
        or plan.get("state") != "draft"
        or plan.get("pilot_result") is not False
        or plan.get("execution_permitted") is not False
    ):
        raise ValueError("exp05_draft_plan_required")
    weights = LEGACY_WEIGHTS if plan["schema_version"] == 1 else WEIGHTS
    workload = plan.get("workload")
    if not isinstance(workload, dict) or (
        workload.get("condition") != "burst"
        or workload.get("rate_rps") != 50
        or workload.get("mix") != {"browse": 50, "search": 30, "detail": 20}
        or workload.get("warmup_seconds") != 60
        or workload.get("measured_seconds") != 120
        or workload.get("drain_seconds") != 5
        or workload.get("timeout_seconds") != 5
        or workload.get("retries") != 0
        or not isinstance(workload.get("sha256"), str)
        or not SHA256.fullmatch(workload["sha256"])
    ):
        raise ValueError("exp05_workload_binding_mismatch")
    if (
        plan.get("candidate_weights_lambda_ecs_percent")
        != [[weight, 100 - weight] for weight in weights]
        or plan.get("run_order")
        != [
            "ecs_baseline",
            *[f"lambda_ecs_{weight}_{100-weight}" for weight in weights],
        ]
        or plan.get("repetitions_per_weight") != 3
        or plan.get("baseline_repetitions") != 3
    ):
        raise ValueError("exp05_candidate_matrix_mismatch")
    if (
        plan.get("selection_rule")
        != "highest_lambda_weight_meeting_all_frozen_pilot_gates"
    ):
        raise ValueError("exp05_selection_rule_mismatch")
    gates = plan.get("gates")
    if (
        not isinstance(gates, dict)
        or set(gates)
        != {
            "minimum_correct_share",
            "zero_generator_drops",
            "complete_request_accounting",
            "resource_and_database_headroom_verified",
            "all_required_telemetry_present",
            "under_approved_run_cost_cap",
        }
        or isinstance(gates["minimum_correct_share"], bool)
        or not isinstance(gates["minimum_correct_share"], (int, float))
        or not 0.95 <= gates["minimum_correct_share"] <= 1
        or any(gates[key] is not True for key in set(gates) - {"minimum_correct_share"})
    ):
        raise ValueError("exp05_gates_weakened_or_incomplete")
    if not isinstance(plan.get("target_binding_sha256"), str) or not SHA256.fullmatch(
        plan["target_binding_sha256"]
    ):
        raise ValueError("exp05_target_binding_required")
    runs = plan.get("runs")
    if not isinstance(runs, list) or len(runs) != 3 * (1 + len(weights)):
        raise ValueError("exp05_complete_run_matrix_required")
    expected = []
    prefix = runs[0].get("run_id", "").rsplit("-base-r1", 1)[0]
    if not RUN_ID.fullmatch(prefix) or len(prefix) > 40:
        raise ValueError("invalid_pilot_run_prefix")
    for repetition in range(1, 4):
        expected.append(
            {
                "run_id": f"{prefix}-base-r{repetition}",
                "configuration": "A",
                "lambda_weight_percent": 0,
                "ecs_weight_percent": 100,
                "repetition": repetition,
            }
        )
    for weight in weights:
        for repetition in range(1, 4):
            expected.append(
                {
                    "run_id": f"{prefix}-l{weight}-r{repetition}",
                    "configuration": "B",
                    "lambda_weight_percent": weight,
                    "ecs_weight_percent": 100 - weight,
                    "repetition": repetition,
                }
            )
    if (
        not isinstance(runs, list)
        or len(runs) != 3 * (1 + len(weights))
        or any(not isinstance(row, dict) for row in runs)
    ):
        raise ValueError("exp05_run_matrix_mismatch")
    target_bindings = {}
    for actual, base in zip(runs, expected, strict=True):
        if (
            set(actual) != set(base) | {"target_plan_sha256"}
            or any(actual[key] != value for key, value in base.items())
            or not isinstance(actual["target_plan_sha256"], str)
            or not SHA256.fullmatch(actual["target_plan_sha256"])
        ):
            raise ValueError("exp05_run_matrix_mismatch")
        target_bindings[actual["run_id"]] = actual["target_plan_sha256"]
    target_matrix_sha256 = hashlib.sha256(
        json.dumps(target_bindings, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if plan["target_binding_sha256"] != target_matrix_sha256:
        raise ValueError("exp05_run_matrix_mismatch")
    return plan


def summarize_pilot(plan: Any, records: Any) -> dict[str, Any]:
    """Apply frozen pilot gates; never invent a winner when evidence is missing."""
    plan = _validate_plan(plan)
    expected_runs = plan.get("runs")
    if (
        not isinstance(expected_runs, list)
        or not isinstance(records, list)
        or len(records) != len(expected_runs)
    ):
        raise ValueError("all_declared_pilot_run_records_required")
    expected = {row["run_id"]: row for row in expected_runs}
    found: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {
            "run_id",
            "configuration",
            "lambda_weight_percent",
            "ecs_weight_percent",
            "repetition",
            "workload_sha256",
            "target_plan_sha256",
            "report",
            "resource_checks",
        }:
            raise ValueError("invalid_pilot_record")
        binding = expected.get(record["run_id"])
        if binding is None or record["run_id"] in found:
            raise ValueError("unknown_or_duplicate_pilot_run")
        for key in (
            "configuration",
            "lambda_weight_percent",
            "ecs_weight_percent",
            "repetition",
        ):
            if record[key] != binding[key]:
                raise ValueError("pilot_run_binding_mismatch")
        if record["workload_sha256"] != plan["workload"]["sha256"]:
            raise ValueError("pilot_workload_mismatch")
        if record["target_plan_sha256"] != binding["target_plan_sha256"]:
            raise ValueError("pilot_target_plan_mismatch")
        provenance = (
            record["report"].get("execution_provenance")
            if isinstance(record["report"], dict)
            else None
        )
        if (
            not isinstance(provenance, dict)
            or provenance.get("execution_artifact_binding_verified") is not True
            or provenance.get("target_plan_sha256") != binding["target_plan_sha256"]
        ):
            raise ValueError("pilot_execution_receipt_binding_required")
        checks = record["resource_checks"]
        if (
            not isinstance(checks, dict)
            or set(checks)
            != {
                "database_headroom",
                "generator_headroom",
                "telemetry_complete",
                "cost_under_cap",
                "routing_weight_verified",
            }
            or any(type(value) is not bool for value in checks.values())
        ):
            raise ValueError("explicit_resource_checks_required")
        found[record["run_id"]] = record

    candidate_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    for repetition in range(1, REPETITIONS + 1):
        run_id = next(
            row["run_id"]
            for row in expected_runs
            if row["configuration"] == "A" and row["repetition"] == repetition
        )
        record = found[run_id]
        phase = _phase(record["report"])
        checks = record["resource_checks"]
        baseline_ok = (
            record["report"].get("accounting_complete") is True
            and record["report"].get("delivery_complete") is True
            and phase.get("accounting_complete") is True
            and phase.get("delivery_complete") is True
            and phase.get("dropped_iterations") == 0
            and type(phase.get("issued")) is int
            and phase["issued"] > 0
            and type(phase.get("correct")) is int
            and 0 <= phase["correct"] <= phase["issued"]
            and phase["correct"] / phase["issued"]
            >= plan["gates"]["minimum_correct_share"]
            and all(checks.values())
        )
        baseline_rows.append(
            {"run_id": run_id, "eligible": baseline_ok, "resource_checks": checks}
        )
    for weight in (pair[0] for pair in plan["candidate_weights_lambda_ecs_percent"]):
        repetitions = []
        eligible = True
        for repetition in range(1, REPETITIONS + 1):
            run_id = next(
                row["run_id"]
                for row in expected_runs
                if row["lambda_weight_percent"] == weight
                and row["repetition"] == repetition
            )
            record = found[run_id]
            report = record["report"]
            phase = _phase(report)
            issued = phase.get("issued")
            correct = phase.get("correct")
            p95 = (phase.get("correct_latency_ms") or {}).get("p95_ms")
            success_share = (
                correct / issued
                if type(issued) is int and issued > 0 and type(correct) is int
                else None
            )
            checks = record["resource_checks"]
            run_ok = (
                report.get("accounting_complete") is True
                and report.get("delivery_complete") is True
                and phase.get("accounting_complete") is True
                and phase.get("delivery_complete") is True
                and phase.get("dropped_iterations") == 0
                and success_share is not None
                and success_share <= 1
                and success_share >= plan["gates"]["minimum_correct_share"]
                and _finite(p95)
                and all(checks.values())
            )
            eligible = eligible and run_ok
            repetitions.append(
                {
                    "run_id": run_id,
                    "issued": issued,
                    "correct": correct,
                    "success_share": success_share,
                    "p95_correct_ms": p95,
                    "failed": phase.get("failed"),
                    "throttled": (phase.get("outcomes") or {}).get("throttled", 0),
                    "generator_drops": phase.get("dropped_iterations"),
                    "accounting_complete": phase.get("accounting_complete") is True,
                    "delivery_complete": phase.get("delivery_complete") is True,
                    "resource_checks": checks,
                    "eligible": run_ok,
                }
            )
        candidate_rows.append(
            {
                "lambda_weight_percent": weight,
                "ecs_weight_percent": 100 - weight,
                "repetitions": repetitions,
                "eligible": eligible,
            }
        )
    eligible_weights: list[int] = [
        row["lambda_weight_percent"] for row in candidate_rows if row["eligible"]
    ]
    baseline_ok = all(row["eligible"] for row in baseline_rows)
    selected = max(eligible_weights) if eligible_weights and baseline_ok else None
    return {
        "schema_version": 1,
        "purpose": "exp05-pilot-review-summary",
        "pilot_result": True,
        "selected_lambda_weight_percent": selected,
        "selected_ecs_weight_percent": 100 - selected if selected is not None else None,
        "selection_rule": plan["selection_rule"],
        "baseline_runs": baseline_rows,
        "baseline_eligible": baseline_ok,
        "candidate_results": candidate_rows,
        "selection_status": (
            "candidate_selected_for_human_review"
            if selected is not None and all(row["eligible"] for row in baseline_rows)
            else "no_candidate_passed_or_evidence_incomplete"
        ),
        "main_experiment_weight_frozen": False,
        "nfr_accepted": False,
        "raw_runs_preserved": True,
    }


def _read(path: Path, maximum: int = 10_000_000) -> Any:
    if path.stat().st_size > maximum:
        raise ValueError("input_too_large")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("plan")
    build.add_argument("--run-prefix", required=True)
    build.add_argument("--workload-sha256", required=True)
    build.add_argument(
        "--target-bindings",
        type=Path,
        required=True,
        help="JSON object mapping every declared run ID to its exact target-plan SHA-256",
    )
    build.add_argument("--output", type=Path, required=True)
    report = sub.add_parser("report")
    report.add_argument("--plan", type=Path, required=True)
    report.add_argument("--records", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "plan":
            value = build_plan(
                args.run_prefix, args.workload_sha256, _read(args.target_bindings)
            )
        else:
            value = summarize_pilot(_read(args.plan), _read(args.records))
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        print(
            json.dumps(
                {
                    "command": args.command,
                    "output": str(args.output),
                    "execution_permitted": False,
                    "nfr_accepted": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except OSError, ValueError, TypeError, KeyError, json.JSONDecodeError:
        parser.exit(
            2, "EXP-05 pilot preparation/report refused; no workload was started\n"
        )


if __name__ == "__main__":
    raise SystemExit(main())
