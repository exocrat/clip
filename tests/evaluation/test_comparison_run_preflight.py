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
from scripts.evaluation.k6.comparison_profile_builder import build_profile
from scripts.evaluation.k6.comparison_run_preflight import (
    MAX_SAFE_INTEGER,
    validate_run_inputs,
)
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
    paired_plan["rotation"]["seed"] = 0
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
            pair["sequence_start"] = (cycle["cycle"] - 1) * 3 + pair_index
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
        "profile_hash_checked": False,
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
    profile = {
        "cases": json.loads(corpus_bytes)["cases"],
        "sequence_starts": starts,
        "capacity": {"preAllocatedVUs": 2, "maxVUs": 301},
        "timeout_seconds": 5,
    }
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
        "capacity": {"preAllocatedVUs": 2, "maxVUs": 301},
        "timeout_seconds": 5,
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


@pytest.mark.parametrize("cycle", [1, 2, 3])
def test_profile_builder_reuses_bound_cases_and_planned_starts_deterministically(
    prepared_inputs: Any, cycle: int
) -> None:
    binding_plan, corpus_bytes, reference, paired_plan = prepared_inputs
    first = build_profile(
        binding_plan, corpus_bytes, reference, paired_plan, cycle, 2, 301
    )
    second = build_profile(
        binding_plan, corpus_bytes, reference, paired_plan, cycle, 2, 301
    )
    assert first == second
    profile = json.loads(first)
    assert profile["cases"] == json.loads(corpus_bytes)["cases"]
    assert profile["sequence_starts"] == {
        pair["condition"]: pair["sequence_start"]
        for pair in paired_plan["cycles"][cycle - 1]["pairs"]
    }
    assert profile["capacity"] == {"preAllocatedVUs": 2, "maxVUs": 301}
    assert profile["timeout_seconds"] == 5
    assert (
        validate_run_inputs(
            binding_plan, corpus_bytes, reference, paired_plan, profile, cycle
        )["workload_profile_checked"]
        is True
    )


@pytest.mark.parametrize(
    ("cycle", "pre_allocated", "maximum"),
    [
        (0, 1, 1),
        (True, 1, 1),
        (1, 0, 1),
        (1, 2, 1),
        (1, True, 1),
        (1, 1, MAX_SAFE_INTEGER + 1),
    ],
)
def test_profile_builder_refuses_bad_cycle_or_unrepresentable_capacity(
    prepared_inputs: Any, cycle: Any, pre_allocated: Any, maximum: Any
) -> None:
    binding_plan, corpus_bytes, reference, paired_plan = prepared_inputs
    with pytest.raises(ValueError):
        build_profile(
            binding_plan,
            corpus_bytes,
            reference,
            paired_plan,
            cycle,
            pre_allocated,
            maximum,
        )


def test_profile_builder_rejects_missing_or_mismatched_references(
    prepared_inputs: Any,
) -> None:
    binding_plan, corpus_bytes, reference, paired_plan = prepared_inputs
    missing = deepcopy(reference)
    missing["queries"][0]["ordered_listing_ids"] = None
    with pytest.raises(ValueError):
        build_profile(binding_plan, corpus_bytes, missing, paired_plan, 1, 1, 2)
    wrong_plan = deepcopy(paired_plan)
    wrong_plan["rotation"]["seed"] = 1
    with pytest.raises(ValueError, match="sequence_start_rotation_mismatch"):
        build_profile(binding_plan, corpus_bytes, reference, wrong_plan, 1, 1, 2)


def test_profile_builder_cli_is_exclusive_and_fails_before_output(
    tmp_path: Path, prepared_inputs: Any
) -> None:
    binding_plan, corpus_bytes, reference, paired_plan = prepared_inputs
    binding_path, corpus_path, reference_path, plan_path = [
        tmp_path / name
        for name in ("binding.json", "corpus.json", "reference.json", "paired.json")
    ]
    binding_path.write_text(json.dumps(binding_plan))
    corpus_path.write_bytes(corpus_bytes)
    reference_path.write_text(json.dumps(reference))
    plan_path.write_text(json.dumps(paired_plan))
    output = tmp_path / "profile.json"
    command = [
        sys.executable,
        "-m",
        "scripts.evaluation.k6.comparison_profile_builder",
        str(binding_path),
        str(corpus_path),
        str(reference_path),
        str(plan_path),
        "--cycle",
        "1",
        "--pre-allocated-vus",
        "2",
        "--max-vus",
        "301",
        "--output",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    report = json.loads(result.stdout)
    original = output.read_bytes()
    assert report["profile_sha256"] == hashlib.sha256(original).hexdigest()
    assert report["measurement_authorized"] is False
    assert reference["queries"][0]["query_text"] not in result.stdout + result.stderr
    assert (
        subprocess.run(command, capture_output=True, text=True, check=False).returncode
        == 2
    )
    assert output.read_bytes() == original

    untouched = tmp_path / "untouched.json"
    untouched.write_text("existing user file")
    alias = tmp_path / "profile-alias.json"
    alias.symlink_to(untouched)
    assert (
        subprocess.run(
            command[:-1] + [str(alias)], capture_output=True, text=True, check=False
        ).returncode
        == 2
    )
    assert untouched.read_text() == "existing user file"

    missing_output = tmp_path / "not-created.json"
    reference_path.unlink()
    missing_command = command[:-1] + [str(missing_output)]
    failed = subprocess.run(
        missing_command, capture_output=True, text=True, check=False
    )
    assert failed.returncode == 2
    assert not missing_output.exists()
    assert reference["queries"][0]["query_text"] not in failed.stdout + failed.stderr
    incomplete_reference = deepcopy(reference)
    incomplete_reference["queries"][0]["ordered_listing_ids"] = None
    reference_path.write_text(json.dumps(incomplete_reference))
    failed = subprocess.run(
        missing_command, capture_output=True, text=True, check=False
    )
    assert failed.returncode == 2
    assert not missing_output.exists()


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
                "capacity": {"preAllocatedVUs": 2, "maxVUs": 301},
                "timeout_seconds": 5,
            }
        )
    )
    checked = subprocess.run(
        [
            *command,
            "--workload-profile",
            str(profile_path),
            "--cycle",
            "1",
            "--expected-profile-sha256",
            hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0
    assert json.loads(checked.stdout)["workload_profile_checked"] is True
    assert json.loads(checked.stdout)["profile_hash_checked"] is True
    bad_profile = json.loads(profile_path.read_text())
    bad_profile["sequence_starts"]["burst"] = 9
    profile_path.write_text(json.dumps(bad_profile))
    mismatch = subprocess.run(
        [
            *command,
            "--workload-profile",
            str(profile_path),
            "--cycle",
            "1",
            "--expected-profile-sha256",
            hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        ],
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


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.pop("timeout_seconds"),
        lambda p: p.update(extra=True),
        lambda p: p.update(timeout_seconds=True),
        lambda p: p.update(timeout_seconds=3),
        lambda p: p["capacity"].update(preAllocatedVUs=0),
        lambda p: p["capacity"].update(preAllocatedVUs=True),
        lambda p: p["capacity"].update(preAllocatedVUs=302),
        lambda p: p["capacity"].update(maxVUs=MAX_SAFE_INTEGER + 1),
        lambda p: p["capacity"].update(extra=1),
    ],
)
def test_profile_rejects_invalid_shape_timeout_or_workers(
    prepared_inputs: Any, change: Any
) -> None:
    binding, corpus, reference, plan = prepared_inputs
    profile = json.loads(build_profile(binding, corpus, reference, plan, 1, 2, 301))
    change(profile)
    with pytest.raises(ValueError):
        validate_run_inputs(binding, corpus, reference, plan, profile, 1)


def test_profile_hash_checks_exact_bytes_and_object(prepared_inputs: Any) -> None:
    binding, corpus, reference, plan = prepared_inputs
    content = build_profile(binding, corpus, reference, plan, 1, 2, 301)
    profile = json.loads(content)
    digest = hashlib.sha256(content).hexdigest()
    result = validate_run_inputs(
        binding,
        corpus,
        reference,
        plan,
        profile,
        1,
        profile_bytes=content,
        expected_profile_sha256=digest,
    )
    assert result["profile_hash_checked"] is True
    assert result["measurement_authorized"] is False
    for data, expected in [
        (content, None),
        (None, digest),
        (content, "bad"),
        (content + b" ", digest),
        (content, "0" * 64),
    ]:
        with pytest.raises(ValueError):
            validate_run_inputs(
                binding,
                corpus,
                reference,
                plan,
                profile,
                1,
                profile_bytes=data,
                expected_profile_sha256=expected,
            )
    other = deepcopy(profile)
    other["capacity"]["maxVUs"] = 302
    with pytest.raises(ValueError, match="profile_bytes_mismatch"):
        validate_run_inputs(
            binding,
            corpus,
            reference,
            plan,
            other,
            1,
            profile_bytes=content,
            expected_profile_sha256=digest,
        )


def test_offline_preparation_checks_all_inputs_and_planned_run(
    tmp_path: Path, prepared_inputs: Any
) -> None:
    from scripts.evaluation.k6.comparison_offline_prepare import (
        FILE_FIELDS,
        prepare_inputs,
    )

    binding, corpus, reference, plan = prepared_inputs
    profile = build_profile(binding, corpus, reference, plan, 1, 2, 301)
    values = (
        json.dumps(binding).encode(),
        corpus,
        json.dumps(reference).encode(),
        json.dumps(plan).encode(),
        profile,
    )
    paths = {name: tmp_path / f"{name}.json" for name in FILE_FIELDS}
    for name, value in zip(FILE_FIELDS, values):
        paths[name].write_bytes(value)
    digest = hashlib.sha256(profile).hexdigest()
    result = prepare_inputs(paths, 1, "synthetic-c1-p0-A", digest)
    assert result["local_inputs_checked"] is True
    assert result["measurement_authorized"] is False
    assert result["remaining_run_gates"]
    assert prepare_inputs(paths, 1, "synthetic-c2-p0-A", digest)["invalid_inputs"] == [
        "input_bindings_or_planned_run"
    ]
    assert (
        prepare_inputs(paths, 1, "synthetic-c1-p0-A", "0" * 64)["local_inputs_checked"]
        is False
    )
    paths["workload_profile"].write_bytes(profile + b" ")
    assert (
        prepare_inputs(paths, 1, "synthetic-c1-p0-A", digest)["local_inputs_checked"]
        is False
    )
    missing = prepare_inputs({}, None, None, None)
    assert len(missing["missing_inputs"]) == 8
    assert missing["requests_sent"] is False
    paths["corpus"].unlink()
    paths["corpus"].symlink_to(paths["binding_plan"])
    assert (
        "corpus"
        in prepare_inputs(paths, 1, "synthetic-c1-p0-A", digest)["invalid_inputs"]
    )


def test_offline_preparation_cli_lists_missing_inputs_without_echoing_paths() -> None:
    command = [
        sys.executable,
        "-m",
        "scripts.evaluation.k6.comparison_offline_prepare",
        "--binding-plan",
        "/nonexistent/private-location",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert "binding_plan" in report["invalid_inputs"]
    assert "ordered_reference" in report["missing_inputs"]
    assert "/nonexistent/private-location" not in result.stdout + result.stderr


def test_mock_runner_stops_before_simulated_session_and_workload(
    tmp_path: Path, prepared_inputs: Any
) -> None:
    from scripts.evaluation.k6.comparison_mock_runner import FAKE_SESSION, simulate_run
    from scripts.evaluation.k6.comparison_offline_prepare import FILE_FIELDS
    from scripts.evaluation.k6.comparison_session_handoff import SESSION_VARIABLE

    class UnreadableEnvironment(dict[str, str]):
        def get(self, key: str, default: Any = None) -> Any:
            raise AssertionError("session accessed before preflight")

    refused = simulate_run({}, None, None, None, UnreadableEnvironment())
    assert refused["events"] == ["preflight_started", "preflight_refused"]
    assert refused["requests_sent"] is False
    binding, corpus, reference, plan = prepared_inputs
    profile = build_profile(binding, corpus, reference, plan, 1, 2, 301)
    values = (
        json.dumps(binding).encode(),
        corpus,
        json.dumps(reference).encode(),
        json.dumps(plan).encode(),
        profile,
    )
    paths = {name: tmp_path / f"{name}.json" for name in FILE_FIELDS}
    for name, value in zip(FILE_FIELDS, values):
        paths[name].write_bytes(value)
    digest = hashlib.sha256(profile).hexdigest()
    result = simulate_run(
        paths, 1, "synthetic-c1-p0-A", digest, {SESSION_VARIABLE: FAKE_SESSION}
    )
    assert result["events"] == [
        "preflight_started",
        "preflight_passed",
        "simulated_session",
        "simulated_workload",
    ]
    assert result["measurement_authorized"] is False
    assert result["simulation_only"] is True
    assert FAKE_SESSION not in json.dumps(result)
    for source in (
        {},
        {SESSION_VARIABLE: "__Host-clip_session=other"},
        {SESSION_VARIABLE: "synthetic-private-invalid-cookie"},
    ):
        bad = simulate_run(paths, 1, "synthetic-c1-p0-A", digest, source)
        assert bad["events"] == [
            "preflight_started",
            "preflight_passed",
            "session_refused",
        ]
        assert "simulated_workload" not in bad["events"]
        assert all(value not in json.dumps(bad) for value in source.values())
    paths["workload_profile"].write_bytes(profile + b" ")
    refused = simulate_run(
        paths, 1, "synthetic-c1-p0-A", digest, UnreadableEnvironment()
    )
    assert refused["events"] == ["preflight_started", "preflight_refused"]
    assert refused["requests_sent"] is False
