"""Synthetic offline paired-plan checks; no generator or target is started."""

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, cast

import pytest

from scripts.evaluation.k6.comparison_pair_plan import TEMPLATE, validate_pair_plan


def planned_plan() -> dict[str, Any]:
    plan = cast(dict[str, Any], json.loads(TEMPLATE.read_text()))
    plan["plan_state"] = "planned"
    plan["shared_inputs"] = {
        "dataset_fingerprint": "sha256:" + "a" * 64,
        "index_fingerprint": "synthetic-index-v1",
        "database_settings_sha256": "b" * 64,
        "schedule_sha256": "c" * 64,
        "case_corpus_sha256": "d" * 64,
        "load_script_sha256": "e" * 64,
        "generator_version": "k6 v2.3.0",
    }
    counter = 1
    for cycle in plan["cycles"]:
        for pair in cycle["pairs"]:
            pair["sequence_start"] = (cycle["cycle"] - 1) % 10
            pair["A_run_id"] = f"synthetic-{counter:02d}-A"
            pair["B_run_id"] = f"synthetic-{counter:02d}-B"
            counter += 1
    return plan


def test_template_is_valid_but_never_authorizes_measurement() -> None:
    result = validate_pair_plan(json.loads(TEMPLATE.read_text()))
    assert result == {
        "valid": True,
        "state": "template",
        "pair_count": 9,
        "planned_run_count": 18,
        "measurement_authorized": False,
    }


def test_complete_plan_checks_three_cycles_nine_pairs_and_order() -> None:
    result = validate_pair_plan(planned_plan())
    assert result["state"] == "planned"
    assert result["pair_count"] == 9
    assert result["planned_run_count"] == 18
    assert result["cycle_configuration_order"] == [["A", "B"], ["B", "A"], ["A", "B"]]
    assert result["shared_inputs_bound"] is True
    assert result["measurement_authorized"] is False


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            lambda plan: plan["cycles"][0].update(configuration_order=["B", "A"]),
            "configuration_order_mismatch",
        ),
        (lambda plan: plan["cycles"][1]["pairs"].reverse(), "condition_order_mismatch"),
        (
            lambda plan: plan["cycles"][2]["pairs"][0].update(sequence_start=10),
            "invalid_sequence_start",
        ),
        (
            lambda plan: plan["shared_inputs"].update(case_corpus_sha256="wrong"),
            "invalid_shared_fingerprint",
        ),
    ],
)
def test_invalid_plan_inputs_are_refused(
    change: Callable[[dict[str, Any]], None], message: str
) -> None:
    plan = planned_plan()
    change(plan)
    with pytest.raises(ValueError, match=message):
        validate_pair_plan(plan)


def test_duplicate_run_ids_are_refused() -> None:
    plan = planned_plan()
    plan["cycles"][1]["pairs"][0]["A_run_id"] = plan["cycles"][0]["pairs"][0][
        "A_run_id"
    ]
    with pytest.raises(ValueError, match="duplicate_run_id"):
        validate_pair_plan(plan)


def test_cli_checks_template_offline_without_starting_workload(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.evaluation.k6.comparison_pair_plan",
            str(TEMPLATE),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["measurement_authorized"] is False
    assert result.stderr == ""
