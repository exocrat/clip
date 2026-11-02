"""Synthetic tests for the offline comparison input gate."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, cast

import pytest

from scripts.evaluation.k6.comparison_ordered_results import bind_ordered_results
from scripts.evaluation.k6.comparison_pair_plan import TEMPLATE as PAIR_TEMPLATE
from scripts.evaluation.k6.comparison_run_preflight import validate_run_inputs
from scripts.evaluation.k6.prepare_comparison_corpus import (
    FINGERPRINT,
    FROZEN,
    LABELS,
    build_corpus,
)


@pytest.fixture(scope="module")
def prepared_inputs() -> tuple[dict[str, Any], bytes, dict[str, Any], dict[str, Any]]:
    """Build entirely synthetic ordered results and a matching nine-pair plan."""
    draft = build_corpus()
    frozen = json.loads(FROZEN.read_text())
    labels = json.loads(LABELS.read_text())
    case_ids = [row["listing_id"] for row in draft["cases"][0]["expected"]["items"]]
    revision = "a" * 40
    reference = {
        "format_version": 1,
        "dataset_fingerprint": FINGERPRINT,
        "schema_version": draft["dataset"]["schema_version"],
        "search_contract_revision": labels["search_contract_revision"],
        "search_implementation_revision": revision,
        "model_revision": frozen["model"]["revision"],
        "review_record_reference": "synthetic-test-only/review",
        "queries": [
            {
                "query_id": case["relevance_reference"]["query_id"],
                "query_text": case["request"]["query"]["q"],
                "ordered_listing_ids": list(reversed(case_ids)),
                "has_next": True,
            }
            for case in draft["cases"]
            if case["request"]["kind"] == "search"
        ],
    }
    corpus = bind_ordered_results(reference, revision)
    corpus_bytes = json.dumps(corpus, sort_keys=True).encode()
    binding_plan = {
        "format_version": 1,
        "purpose": "offline-binding-check-not-authorization",
        "application_revision": revision,
        "dataset_fingerprint": FINGERPRINT,
        "case_corpus_sha256": hashlib.sha256(corpus_bytes).hexdigest(),
    }

    paired_plan = cast(dict[str, Any], json.loads(PAIR_TEMPLATE.read_text()))
    paired_plan["plan_state"] = "planned"
    paired_plan["shared_inputs"] = {
        "dataset_fingerprint": FINGERPRINT,
        "index_fingerprint": "synthetic-index-v1",
        "database_settings_sha256": "b" * 64,
        "schedule_sha256": "c" * 64,
        "case_corpus_sha256": binding_plan["case_corpus_sha256"],
        "load_script_sha256": "d" * 64,
        "generator_version": "synthetic-k6-version",
    }
    for cycle in paired_plan["cycles"]:
        for pair_index, pair in enumerate(cycle["pairs"]):
            pair["sequence_start"] = (pair_index + cycle["cycle"] - 1) % 10
            pair["A_run_id"] = f"synthetic-c{cycle['cycle']}-p{pair_index}-A"
            pair["B_run_id"] = f"synthetic-c{cycle['cycle']}-p{pair_index}-B"
    return binding_plan, corpus_bytes, reference, paired_plan


def test_matching_inputs_pass_but_never_authorize(prepared_inputs: Any) -> None:
    result = validate_run_inputs(*prepared_inputs)
    assert result == {
        "valid": True,
        "source_dataset_corpus_bindings_match": True,
        "paired_plan_valid": True,
        "planned_pair_count": 9,
        "planned_run_count": 18,
        "workload_profile_checked": False,
        "measurement_authorized": False,
    }


@pytest.mark.parametrize("cycle", [1, 2, 3])
def test_profile_starts_and_cases_match_the_selected_cycle(
    prepared_inputs: Any, cycle: int
) -> None:
    binding_plan, corpus_bytes, reference, paired_plan = prepared_inputs
    starts = {
        pair["condition"]: pair["sequence_start"]
        for pair in paired_plan["cycles"][cycle - 1]["pairs"]
    }
    profile = {"cases": json.loads(corpus_bytes)["cases"], "sequence_starts": starts}
    result = validate_run_inputs(
        binding_plan, corpus_bytes, reference, paired_plan, profile, cycle
    )
    assert result["workload_profile_checked"] is True
    assert result["measurement_authorized"] is False


@pytest.mark.parametrize(
    ("change", "cycle", "error"),
    [
        (
            lambda profile: profile["sequence_starts"].update(low=9),
            1,
            "profile_sequence_starts_mismatch",
        ),
        (
            lambda profile: profile["sequence_starts"].update(low=True),
            1,
            "invalid_profile_sequence_starts",
        ),
        (
            lambda profile: profile["sequence_starts"].pop("burst"),
            1,
            "invalid_profile_sequence_starts",
        ),
        (lambda profile: profile["cases"].pop(), 1, "profile_cases_mismatch"),
        (lambda profile: None, 4, "workload_profile_and_cycle_required"),
    ],
)
def test_bad_workload_profile_is_refused(
    prepared_inputs: Any, change: Any, cycle: int, error: str
) -> None:
    binding_plan, corpus_bytes, reference, paired_plan = prepared_inputs
    profile = {
        "cases": json.loads(corpus_bytes)["cases"],
        "sequence_starts": {"low": 0, "normal": 1, "burst": 2},
    }
    change(profile)
    with pytest.raises(ValueError, match=error):
        validate_run_inputs(
            binding_plan, corpus_bytes, reference, paired_plan, profile, cycle
        )


def test_profile_and_cycle_must_be_supplied_together(prepared_inputs: Any) -> None:
    binding_plan, corpus_bytes, reference, paired_plan = prepared_inputs
    with pytest.raises(ValueError, match="workload_profile_and_cycle_required"):
        validate_run_inputs(binding_plan, corpus_bytes, reference, paired_plan, None, 1)
    with pytest.raises(ValueError, match="workload_profile_and_cycle_required"):
        validate_run_inputs(
            binding_plan, corpus_bytes, reference, paired_plan, {}, None
        )


@pytest.mark.parametrize(
    ("section", "key", "value", "error"),
    [
        (
            "shared_inputs",
            "dataset_fingerprint",
            "sha256:" + "0" * 64,
            "paired_dataset_binding_mismatch",
        ),
        (
            "shared_inputs",
            "case_corpus_sha256",
            "e" * 64,
            "paired_corpus_binding_mismatch",
        ),
    ],
)
def test_pair_plan_binding_mismatches_are_refused(
    prepared_inputs: Any, section: str, key: str, value: str, error: str
) -> None:
    binding_plan, corpus_bytes, reference, paired_plan = prepared_inputs
    changed = deepcopy(paired_plan)
    changed[section][key] = value
    with pytest.raises(ValueError, match=error):
        validate_run_inputs(binding_plan, corpus_bytes, reference, changed)


def test_unfilled_pair_template_is_refused(prepared_inputs: Any) -> None:
    binding_plan, corpus_bytes, reference, _ = prepared_inputs
    template = cast(dict[str, Any], json.loads(PAIR_TEMPLATE.read_text()))
    with pytest.raises(ValueError, match="complete_paired_plan_required"):
        validate_run_inputs(binding_plan, corpus_bytes, reference, template)


def test_cli_outputs_only_aggregate_and_fails_closed(
    tmp_path: Path, prepared_inputs: Any
) -> None:
    binding_plan, corpus_bytes, reference, paired_plan = prepared_inputs
    paired_plan = deepcopy(paired_plan)
    paths = [
        tmp_path / name
        for name in ("binding.json", "corpus.json", "ordered.json", "paired.json")
    ]
    paths[0].write_text(json.dumps(binding_plan))
    paths[1].write_bytes(corpus_bytes)
    paths[2].write_text(json.dumps(reference))
    paths[3].write_text(json.dumps(paired_plan))
    command = [
        sys.executable,
        "-m",
        "scripts.evaluation.k6.comparison_run_preflight",
        *map(str, paths),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert json.loads(result.stdout)["measurement_authorized"] is False
    assert reference["queries"][0]["query_text"] not in result.stdout

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "cases": json.loads(corpus_bytes)["cases"],
                "sequence_starts": {"low": 0, "normal": 1, "burst": 2},
            }
        )
    )
    checked = subprocess.run(
        [*command, "--workload-profile", str(profile_path), "--cycle", "1"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0
    assert json.loads(checked.stdout)["workload_profile_checked"] is True
    bad_profile = json.loads(profile_path.read_text())
    bad_profile["sequence_starts"]["burst"] = 9
    profile_path.write_text(json.dumps(bad_profile))
    mismatch = subprocess.run(
        [*command, "--workload-profile", str(profile_path), "--cycle", "1"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert mismatch.returncode == 2
    assert (
        reference["queries"][0]["query_text"] not in mismatch.stdout + mismatch.stderr
    )
    incomplete = subprocess.run(
        [*command, "--workload-profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert incomplete.returncode == 2

    paired_plan["shared_inputs"]["case_corpus_sha256"] = "e" * 64
    paths[3].write_text(json.dumps(paired_plan))
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "Comparison input preflight failed" in result.stderr
    assert reference["queries"][0]["query_text"] not in result.stdout + result.stderr
