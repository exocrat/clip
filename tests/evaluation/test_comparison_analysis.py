from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

import pytest

from scripts.evaluation.k6.comparison_analysis import ROOT, analyze


def _write(path: Path, value: dict) -> tuple[str, str]:
    data = (json.dumps(value, sort_keys=True) + "\n").encode()
    path.write_bytes(data)
    return str(path.relative_to(ROOT)), hashlib.sha256(data).hexdigest()


def _report(run_id: str, config: str, condition: str, p95: float) -> dict:
    phase = {
        "issued": 100,
        "correct": 98,
        "accounting_complete": True,
        "delivery_complete": True,
        "dropped_iterations": 0,
        "correct_latency_ms": {"p50_ms": p95 / 2, "p95_ms": p95, "p99_ms": p95 * 1.2},
        "routes": {
            route: {
                "issued": 30,
                "outcomes": {"correct": 30},
                "correct_latency_ms": {"p95_ms": p95},
            }
            for route in ("browse", "search", "detail")
        },
    }
    return {
        "run_id": run_id,
        "configuration": config,
        "selected_condition": condition,
        "nfr_accepted": False,
        "accounting_complete": True,
        "delivery_complete": True,
        "execution_provenance": {
            "execution_artifact_binding_verified": True,
            "execution_completed": True,
        },
        "client_metrics": {f"{condition}_measured": phase},
    }


def _input(
    folder: Path, *, b_normal_p95: float = 400, invalid_run: str | None = None
) -> dict:
    rows = []
    for config in ("A", "B"):
        for condition in ("low", "normal", "burst"):
            for repetition in (1, 2, 3):
                run_id = f"{config}-{condition}-r{repetition}"
                p95 = b_normal_p95 if config == "B" and condition == "normal" else 400
                report_path, report_sha = _write(
                    folder / f"{run_id}-report.json",
                    _report(run_id, config, condition, p95),
                )
                cost_path, cost_sha = _write(
                    folder / f"{run_id}-cost.json",
                    {
                        "run_id": run_id,
                        "condition": condition,
                        "cost_usd": "0.01000000",
                        "cost_basis": "estimated",
                        "cost_source_reference": "reviewed-test-price-source",
                    },
                )
                rows.append(
                    {
                        "run_id": run_id,
                        "configuration": config,
                        "condition": condition,
                        "repetition": repetition,
                        "validity": "invalid" if run_id == invalid_run else "valid",
                        "validity_review": (
                            "test reviewer accepted"
                            if run_id != invalid_run
                            else "synthetic invalidation reason"
                        ),
                        "report_path": report_path,
                        "report_sha256": report_sha,
                        "cost_path": cost_path,
                        "cost_sha256": cost_sha,
                    }
                )
    return {
        "format_version": 1,
        "purpose": "exp07-offline-analysis-input",
        "score_spec": {
            "state": "frozen",
            "frozen_before_results": True,
            "frozen_at_utc": "2026-11-01T12:00:00Z",
            "review_record": "score-review-record",
            "cost_good_usd_per_1000": 0.01,
            "cost_poor_usd_per_1000": 1.0,
            "cost_model_reference": "pre-run-cost-model",
        },
        "eligibility": {
            "A": {"status": "eligible", "review_record": "A-review"},
            "B": {"status": "eligible", "review_record": "B-review"},
        },
        "runs": rows,
    }


def test_analysis_uses_frozen_rules_and_reports_practical_tie() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT / "tests/evaluation") as temp:
        result = analyze(_input(Path(temp)))
    assert result["analysis_complete"] is True
    assert result["selection_status"] == "practical_tie"
    assert result["scores"]["A"]["total_points"] == pytest.approx(
        result["scores"]["B"]["total_points"]
    )
    assert result["normal_per_class_no_degradation_guard"]["browse"]["passed"] is True
    assert result["nfr_accepted"] is False
    assert result["product_eligibility_accepted"] is False


def test_analysis_downgrades_b_when_normal_route_guard_fails() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT / "tests/evaluation") as temp:
        result = analyze(_input(Path(temp), b_normal_p95=700))
    assert result["normal_per_class_no_degradation_guard"]["browse"]["passed"] is False
    assert result["effective_eligibility_for_scoring"]["B"] is False
    assert "B" not in result["scores"]
    assert result["selection_status"] == "A_only_eligible"


def test_analysis_preserves_invalid_run_and_refuses_to_score_incomplete_matrix() -> (
    None
):
    with tempfile.TemporaryDirectory(dir=ROOT / "tests/evaluation") as temp:
        result = analyze(_input(Path(temp), invalid_run="A-low-r2"))
    assert result["analysis_complete"] is False
    assert result["run_exclusions"][0]["preserved"] is True
    assert result["selection_status"] == "inconclusive_missing_or_invalid_run"
    assert "A" not in result["scores"]
    assert "B" in result["scores"]


def test_analysis_rejects_changed_report_bytes() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT / "tests/evaluation") as temp:
        folder = Path(temp)
        value = _input(folder)
        report = ROOT / value["runs"][0]["report_path"]
        report.write_text("{}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="derived_report_hash_mismatch"):
            analyze(value)
