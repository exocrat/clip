"""Synthetic offline paired-plan checks; no generator or target is started."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, cast

import pytest

from scripts.evaluation.k6.comparison_pair_plan import TEMPLATE, validate_pair_plan
from scripts.evaluation.k6.comparison_manifest import TEMPLATE as MANIFEST_TEMPLATE


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


def captured_manifests(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Build valid, entirely synthetic captured records for every planned run."""
    manifests = []
    for cycle in plan["cycles"]:
        for pair in cycle["pairs"]:
            for config in cycle["configuration_order"]:
                slot = (
                    (cycle["cycle"] - 1) * 6
                    + cycle["configuration_order"].index(config) * 3
                    + ("low", "normal", "burst").index(pair["condition"])
                )
                start = datetime(2026, 11, 1, 10, tzinfo=timezone.utc) + timedelta(
                    minutes=7 * slot
                )
                end = start + timedelta(minutes=6)

                def utc(value: datetime) -> str:
                    return value.isoformat().replace("+00:00", "Z")

                manifest = cast(
                    dict[str, Any], json.loads(MANIFEST_TEMPLATE.read_text())
                )
                manifest["manifest_state"] = "captured"
                manifest["run"] = {
                    "run_id": pair[f"{config}_run_id"],
                    "configuration": config,
                    "condition": pair["condition"],
                    "repetition": cycle["cycle"],
                    "owner_role": "synthetic operator",
                    "planned_start_utc": utc(start),
                    "actual_start_utc": utc(start),
                    "actual_end_utc": utc(end),
                }
                manifest["target"].update(
                    {
                        "account_id": "123456789012",
                        "role_arn": "arn:aws:iam::123456789012:role/synthetic",
                        "region": "synthetic-region",
                        "environment_id": "synthetic-env",
                        "entrypoint_reference": "synthetic-target-record",
                        "resource_ids": ["synthetic-resource"],
                        "resource_configuration_sha256": "f" * 64,
                    }
                )
                manifest["revisions"].update(
                    {
                        "application_revision": "1" * 40,
                        "image_digest": "sha256:" + "2" * 64,
                        "frontend_revision": "3" * 40,
                        "migration_head": "20261101010000",
                        "api_contract_sha256": "4" * 64,
                    }
                )
                shared = plan["shared_inputs"]
                manifest["dataset"].update(
                    {
                        "seed": 42,
                        "user_count": 5000,
                        "listing_count": 1000,
                        "logical_fingerprint": shared["dataset_fingerprint"],
                        "index_fingerprint": shared["index_fingerprint"],
                        "database_settings_sha256": shared["database_settings_sha256"],
                    }
                )
                manifest["workload"].update(
                    {
                        "profile_sha256": shared["schedule_sha256"],
                        "case_corpus_path": "synthetic-cases.json",
                        "case_corpus_sha256": shared["case_corpus_sha256"],
                        "generator_version": shared["generator_version"],
                        "load_script_sha256": shared["load_script_sha256"],
                        "run_command_reference": "synthetic-command.md",
                        "sequence_start": pair["sequence_start"],
                    }
                )
                for name in ("ecs", "lambda", "postgres", "generator"):
                    manifest["resource_telemetry"].update(
                        {
                            f"{name}_artifact_reference": f"{name}.json",
                            f"{name}_artifact_sha256": "5" * 64,
                        }
                    )
                manifest["cost_inputs"].update(
                    {
                        "source_reference": "synthetic-cost.json",
                        "source_sha256": "6" * 64,
                        "interval_start_utc": utc(start - timedelta(minutes=1)),
                        "interval_end_utc": utc(end + timedelta(minutes=1)),
                        "amount_before_credits": 0.0,
                        "billing_delay_note": "synthetic fixture",
                    }
                )
                manifest["evidence"].update(
                    {
                        "raw_output_reference": "raw.ndjson",
                        "raw_output_sha256": "7" * 64,
                        "derived_report_reference": "report-v1.json",
                        "derived_report_sha256": "8" * 64,
                        "approval_record_reference": "synthetic-approval.md",
                        "cleanup_record_reference": "synthetic-cleanup.md",
                    }
                )
                manifests.append(manifest)
    return manifests


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


def test_all_synthetic_captured_manifests_match_the_plan() -> None:
    plan = planned_plan()
    # Input file order need not be chronological; recorded timestamps decide.
    result = validate_pair_plan(plan, list(reversed(captured_manifests(plan))))
    assert result["captured_manifests_checked"] is True
    assert result["captured_manifest_count"] == 18
    assert result["recorded_order_checked"] is True
    assert result["measurement_authorized"] is False


@pytest.mark.parametrize("pair_index", [0, 3, 6])
def test_reversed_configuration_order_is_refused_in_each_cycle(pair_index: int) -> None:
    plan = planned_plan()
    manifests = captured_manifests(plan)
    left, right = manifests[pair_index * 2 : pair_index * 2 + 2]
    for key in ("actual_start_utc", "actual_end_utc"):
        left["run"][key], right["run"][key] = right["run"][key], left["run"][key]
    with pytest.raises(ValueError, match="captured_run_order_or_overlap"):
        validate_pair_plan(plan, manifests)


def test_overlapping_recorded_runs_are_refused() -> None:
    plan = planned_plan()
    manifests = captured_manifests(plan)
    # A normal starts one second before A low's recorded end.
    manifests[2]["run"]["actual_start_utc"] = "2026-11-01T10:05:59Z"
    with pytest.raises(ValueError, match="captured_run_order_or_overlap"):
        validate_pair_plan(plan, manifests)


def test_reversed_condition_order_is_refused() -> None:
    plan = planned_plan()
    manifests = captured_manifests(plan)
    for key in ("actual_start_utc", "actual_end_utc"):
        manifests[0]["run"][key], manifests[2]["run"][key] = (
            manifests[2]["run"][key],
            manifests[0]["run"][key],
        )
    with pytest.raises(ValueError, match="captured_run_order_or_overlap"):
        validate_pair_plan(plan, manifests)


def test_touching_recorded_boundaries_are_allowed() -> None:
    plan = planned_plan()
    manifests = captured_manifests(plan)
    manifests[2]["run"]["actual_start_utc"] = manifests[0]["run"]["actual_end_utc"]
    assert validate_pair_plan(plan, manifests)["recorded_order_checked"] is True


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            lambda manifest: manifest["workload"].update(sequence_start=9),
            "captured_run_binding_mismatch",
        ),
        (
            lambda manifest: manifest["run"].update(configuration="B"),
            "captured_run_binding_mismatch",
        ),
        (
            lambda manifest: manifest["workload"].update(case_corpus_sha256="9" * 64),
            "captured_shared_input_mismatch",
        ),
    ],
)
def test_mismatched_captured_manifest_is_refused(
    change: Callable[[dict[str, Any]], None], message: str
) -> None:
    plan = planned_plan()
    manifests = captured_manifests(plan)
    change(manifests[0])
    with pytest.raises(ValueError, match=message):
        validate_pair_plan(plan, manifests)


def test_incomplete_capture_set_and_template_capture_are_refused() -> None:
    plan = planned_plan()
    with pytest.raises(ValueError, match="eighteen_captured_manifests_required"):
        validate_pair_plan(plan, captured_manifests(plan)[:-1])
    with pytest.raises(ValueError, match="captured_manifests_require_planned_plan"):
        validate_pair_plan(json.loads(TEMPLATE.read_text()), [])


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
