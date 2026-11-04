"""Completed-run reports must verify real artifacts without reopening raw output."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts.evaluation.k6 import real_run_coordinator as coordinator
from scripts.evaluation.k6 import real_run_evidence as evidence
from scripts.evaluation.k6.real_run_evidence import verify_execution


def test_completed_receipt_verifies_but_reexecution_and_tampering_are_rejected(
    tmp_path, monkeypatch
):
    """Exercise the launch/report distinction using a completed immutable fixture."""
    monkeypatch.setattr(coordinator, "ROOT", tmp_path)
    monkeypatch.setattr(
        evidence,
        "__file__",
        str(tmp_path / "scripts/evaluation/k6/real_run_evidence.py"),
    )
    (tmp_path / "scripts/evaluation/k6").mkdir(parents=True)
    run_dir = tmp_path / "runs/completed"
    run_dir.mkdir(parents=True)
    raw = run_dir / "raw.ndjson"
    raw.write_bytes(b'{"synthetic":"raw"}\n')
    profile = tmp_path / "profile.json"
    profile.write_text("{}")
    target = tmp_path / "target.json"
    target.write_text('{"revisions":{}}')
    binary = tmp_path / "k6"
    binary.write_bytes(b"synthetic binary")

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    plan = dict.fromkeys(coordinator.PLAN_KEYS)
    plan.update(
        format_version=1,
        purpose="clip-approved-k6-run",
        run_id="completed-run",
        workload_kind="nfr-01",
        configuration="A",
        target_plan_path="target.json",
        target_plan_sha256=digest(target),
        profile_path="profile.json",
        profile_sha256=digest(profile),
        module_hashes={name: "0" * 64 for name in coordinator.NFR_MODULES["nfr-01"]},
        k6_binary_path="k6",
        k6_binary_sha256=digest(binary),
        expected_user_id="11111111-1111-4111-8111-111111111111",
        maximum_duration_seconds=400,
        maximum_raw_bytes=1_000_000,
        evidence_directory="runs/completed",
        execution_permitted=False,
        nfr_accepted=False,
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    receipt = {
        "run_id": plan["run_id"],
        "configuration": "A",
        "workload_kind": "nfr-01",
        "run_plan_sha256": digest(plan_path),
        "target_plan_sha256": digest(target),
        "profile_sha256": digest(profile),
        "k6_binary_sha256": digest(binary),
        "raw_sha256": digest(raw),
        "raw_bytes": raw.stat().st_size,
        "execution_state": "completed",
        "process_exit_code": 0,
        "timed_out": False,
        "raw_limit_exceeded": False,
        "nfr_accepted": False,
    }
    receipt_path = run_dir / "receipt.json"
    receipt_path.write_text(json.dumps(receipt))

    def verify():
        return verify_execution(
            receipt_path,
            plan_path,
            raw,
            profile,
            workload_kind="nfr-01",
            configuration="A",
            run_id="completed-run",
        )

    assert verify()["latency_timing_binary_hash_bound"]
    assert verify()["execution_artifact_binding_verified"]
    with pytest.raises(ValueError, match="evidence_directory_unavailable"):
        coordinator.validate_run_plan(plan)
    raw.write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="execution_artifact_binding_mismatch"):
        verify()
