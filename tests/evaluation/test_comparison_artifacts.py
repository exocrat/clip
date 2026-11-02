"""Synthetic-only local evidence fixtures; no provider services are contacted."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.evaluation.k6.comparison_artifacts import validate_artifacts
from scripts.evaluation.k6.comparison_manifest import TEMPLATE


@pytest.fixture
def evidence(tmp_path):
    root = tmp_path / "evidence"
    root.mkdir()
    manifest = json.loads(TEMPLATE.read_text())
    manifest["manifest_state"] = "captured"
    manifest["run"] = {
        "run_id": "synthetic-A-1",
        "configuration": "A",
        "condition": "low",
        "repetition": 1,
        "owner_role": "operator",
        "planned_start_utc": "2026-11-01T10:00:00Z",
        "actual_start_utc": "2026-11-01T10:00:01Z",
        "actual_end_utc": "2026-11-01T10:06:00Z",
    }
    manifest["target"] = {
        "account_id": "123456789012",
        "role_arn": "arn:aws:iam::123456789012:role/test",
        "region": "test-region",
        "environment_id": "synthetic",
        "entrypoint_reference": "target-record",
        "resource_ids": ["test-resource"],
        "resource_configuration_sha256": "a" * 64,
    }
    manifest["revisions"] = {
        "application_revision": "b" * 40,
        "image_digest": "sha256:" + "c" * 64,
        "frontend_revision": "d" * 40,
        "migration_head": "20261101010000",
        "api_contract_sha256": "e" * 64,
    }
    manifest["dataset"] = {
        "seed": 42,
        "user_count": 5000,
        "listing_count": 1000,
        "logical_fingerprint": "sha256:" + "f" * 64,
        "index_fingerprint": "synthetic-index",
        "database_settings_sha256": "1" * 64,
    }
    profile = root / "cycle-profile.json"
    profile.write_bytes(b"synthetic workload profile")
    manifest["workload"].update(
        {
            "profile_sha256": "2" * 64,
            "execution_profile_reference": profile.name,
            "execution_profile_sha256": hashlib.sha256(
                profile.read_bytes()
            ).hexdigest(),
            "case_corpus_path": "cases.json",
            "case_corpus_sha256": "3" * 64,
            "generator_version": "k6 v2.3.0",
            "load_script_sha256": "4" * 64,
            "run_command_reference": "command.md",
            "rotation_seed": 0,
            "sequence_start": 0,
        }
    )
    artifacts = {}
    for name in ("ecs", "lambda", "postgres", "generator"):
        path = root / f"{name}.json"
        content = f"synthetic {name}".encode()
        path.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        manifest["resource_telemetry"][f"{name}_artifact_reference"] = path.name
        manifest["resource_telemetry"][f"{name}_artifact_sha256"] = digest
        artifacts[name] = {
            "reference": path.name,
            "sha256": digest,
            "window_start_utc": "2026-11-01T09:59:00Z",
            "window_end_utc": "2026-11-01T10:07:00Z",
        }
    raw = root / "raw/data.jsonl"
    raw.parent.mkdir()
    raw.write_bytes(b"synthetic immutable raw output")
    report = root / "reports/report.json"
    report.parent.mkdir()
    report.write_bytes(b"synthetic derived report v1")
    cost = root / "cost.json"
    cost.write_bytes(b"synthetic cost")
    manifest["cost_inputs"].update(
        {
            "source_reference": cost.name,
            "source_sha256": hashlib.sha256(cost.read_bytes()).hexdigest(),
            "interval_start_utc": "2026-11-01T09:59:00Z",
            "interval_end_utc": "2026-11-01T10:07:00Z",
            "amount_before_credits": 1.25,
            "billing_delay_note": "synthetic only",
        }
    )
    manifest["evidence"] = {
        "raw_output_reference": "raw/data.jsonl",
        "raw_output_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "derived_report_reference": "reports/report.json",
        "derived_report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "approval_record_reference": "approval/record.md",
        "cleanup_record_reference": "cleanup/record.md",
    }
    telemetry = {
        "format_version": 1,
        "run_id": "synthetic-A-1",
        "clock": {
            "source": "synthetic",
            "monotonic_verified": False,
            "evidence_reference": "clock.json",
        },
        "generator": {
            "peak_cpu_percent": 10,
            "approved_cpu_limit_percent": 80,
            "peak_rss_bytes": 10,
            "approved_rss_limit_bytes": 20,
            "peak_vus": 1,
            "approved_max_vus": 2,
            "dropped_iterations": 0,
        },
        "artifacts": artifacts,
    }
    return root, manifest, telemetry


def test_hashes_and_windows_without_claiming_content_or_measurement(evidence):
    root, manifest, telemetry = evidence
    before = {
        p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }
    report = validate_artifacts(manifest, telemetry, root)
    assert report["artifact_hashes_match"] is True
    assert report["execution_profile_hash_matches"] is True
    assert report["raw_output_hash_matches"] is True
    assert report["derived_report_hash_matches"] is True
    assert report["raw_and_derived_report_are_distinct_files"] is True
    assert report["telemetry_metadata_valid"] is True
    assert report["artifact_contents_verified"] is False
    assert report["clock_independently_verified"] is False
    assert report["measurement_authorized"] is False
    assert report["nfr_accepted"] is False
    assert {
        p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
    } == before


def test_missing_modified_and_symlinked_artifacts_refused(evidence, tmp_path):
    root, manifest, telemetry = evidence
    path = root / "ecs.json"
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="artifact_hash_mismatch"):
        validate_artifacts(manifest, telemetry, root)
    path.unlink()
    with pytest.raises(OSError):
        validate_artifacts(manifest, telemetry, root)
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"synthetic ecs")
    path.symlink_to(outside)
    with pytest.raises(OSError):
        validate_artifacts(manifest, telemetry, root)


def test_missing_modified_and_symlinked_execution_profile_refused(evidence, tmp_path):
    root, manifest, telemetry = evidence
    profile = root / "cycle-profile.json"
    profile.write_bytes(b"modified synthetic profile")
    with pytest.raises(ValueError, match="artifact_hash_mismatch"):
        validate_artifacts(manifest, telemetry, root)
    profile.unlink()
    with pytest.raises(OSError):
        validate_artifacts(manifest, telemetry, root)
    outside = tmp_path / "profile.json"
    outside.write_bytes(b"synthetic workload profile")
    profile.symlink_to(outside)
    with pytest.raises(OSError):
        validate_artifacts(manifest, telemetry, root)


def test_execution_profile_reference_cannot_escape_evidence_root(evidence):
    root, manifest, telemetry = evidence
    manifest["workload"]["execution_profile_reference"] = "../profile.json"
    with pytest.raises(ValueError, match="unsafe_artifact_reference"):
        validate_artifacts(manifest, telemetry, root)


def test_symlinked_root_and_parent_directory_are_refused(evidence, tmp_path):
    root, manifest, telemetry = evidence
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink_evidence_root"):
        validate_artifacts(manifest, telemetry, alias)
    external = tmp_path / "external"
    external.mkdir()
    (external / "cost.json").write_bytes(b"synthetic cost")
    (root / "linked").symlink_to(external, target_is_directory=True)
    changed = deepcopy(manifest)
    changed["cost_inputs"]["source_reference"] = "linked/cost.json"
    with pytest.raises(OSError):
        validate_artifacts(changed, telemetry, root)


def test_modified_cost_and_generator_limit_flags(evidence):
    root, manifest, telemetry = evidence
    telemetry["generator"]["peak_cpu_percent"] = 90
    report = validate_artifacts(manifest, telemetry, root)
    assert report["generator_checks"]["cpu_within_supplied_limit"] is False
    assert report["measurement_authorized"] is False
    (root / "cost.json").write_bytes(b"different synthetic cost")
    with pytest.raises(ValueError, match="artifact_hash_mismatch"):
        validate_artifacts(manifest, telemetry, root)


def test_raw_and_derived_report_hashes_and_distinct_files(evidence):
    root, manifest, telemetry = evidence
    report = root / "reports/report.json"
    report.write_bytes(b"corrected derived report v2")
    with pytest.raises(ValueError, match="artifact_hash_mismatch"):
        validate_artifacts(manifest, telemetry, root)

    manifest["evidence"]["derived_report_sha256"] = hashlib.sha256(
        report.read_bytes()
    ).hexdigest()
    raw = root / "raw/data.jsonl"
    raw.unlink()
    raw.hardlink_to(report)
    manifest["evidence"]["raw_output_sha256"] = hashlib.sha256(
        raw.read_bytes()
    ).hexdigest()
    with pytest.raises(
        ValueError, match="raw_and_derived_report_must_be_distinct_files"
    ):
        validate_artifacts(manifest, telemetry, root)


def test_modified_raw_output_is_refused(evidence):
    root, manifest, telemetry = evidence
    (root / "raw/data.jsonl").write_bytes(b"changed raw output")
    with pytest.raises(ValueError, match="artifact_hash_mismatch"):
        validate_artifacts(manifest, telemetry, root)


def test_traversal_windows_and_limits_are_refused(evidence, monkeypatch):
    root, manifest, telemetry = evidence
    changed = deepcopy(manifest)
    changed["cost_inputs"]["source_reference"] = "../outside.json"
    with pytest.raises(ValueError, match="unsafe_artifact_reference"):
        validate_artifacts(changed, telemetry, root)
    changed = deepcopy(telemetry)
    changed["artifacts"]["ecs"]["window_end_utc"] = "2026-11-01T10:05:00Z"
    with pytest.raises(ValueError, match="does not cover"):
        validate_artifacts(manifest, changed, root)
    changed_manifest = deepcopy(manifest)
    changed_manifest["cost_inputs"]["interval_end_utc"] = "2026-11-01T10:05:00Z"
    with pytest.raises(ValueError, match="cost_interval_does_not_cover_run"):
        validate_artifacts(changed_manifest, telemetry, root)
    monkeypatch.setattr(
        "scripts.evaluation.k6.comparison_artifacts.MAX_ARTIFACT_BYTES", 3
    )
    with pytest.raises(ValueError, match="artifact_not_bounded_regular_file"):
        validate_artifacts(manifest, telemetry, root)


def test_cli_refuses_template_without_disclosing_contents(evidence, tmp_path):
    root, _, telemetry = evidence
    telemetry_file = tmp_path / "telemetry.json"
    telemetry_file.write_text(json.dumps(telemetry))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.evaluation.k6.comparison_artifacts",
            str(TEMPLATE),
            str(telemetry_file),
            "--evidence-root",
            str(root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "synthetic cost" not in result.stderr
