"""Verify a completed coordinator receipt against its untouched run artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

from scripts.evaluation.k6.real_run_coordinator import _read_bounded, validate_run_plan


def _digest_file(path: Path, maximum: int) -> tuple[str, int]:
    """Stream-hash one regular evidence file without following a final symlink."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError("evidence_file_not_bounded_regular")
        digest = hashlib.sha256()
        size = 0
        while True:
            data = os.read(descriptor, 1_048_576)
            if not data:
                break
            digest.update(data)
            size += len(data)
        return digest.hexdigest(), size
    finally:
        os.close(descriptor)


def verify_execution(
    receipt_path: Path,
    run_plan_path: Path,
    raw_path: Path,
    profile_path: Path,
    *,
    workload_kind: str,
    configuration: str,
    run_id: str,
) -> dict[str, Any]:
    """Prove raw/profile bytes belong to one completed, bound coordinator run.

    The returned flags establish artifact consistency and execution provenance,
    not measurement validity, infrastructure telemetry, or NFR acceptance.
    """
    receipt_bytes = _read_bounded(receipt_path, 100_000)
    receipt = json.loads(receipt_bytes)
    plan_bytes = _read_bounded(run_plan_path, 200_000)
    plan = validate_run_plan(json.loads(plan_bytes), completed_evidence=True)
    raw_hash, raw_size = _digest_file(raw_path, plan["maximum_raw_bytes"])
    profile_hash, _ = _digest_file(profile_path, 5_000_000)
    if (
        not isinstance(receipt, dict)
        or receipt.get("run_id") != run_id
        or receipt.get("configuration") != configuration
        or receipt.get("workload_kind") != workload_kind
        or receipt.get("run_plan_sha256") != hashlib.sha256(plan_bytes).hexdigest()
        or receipt.get("target_plan_sha256") != plan["target_plan_sha256"]
        or receipt.get("profile_sha256") != profile_hash
        or profile_hash != plan["profile_sha256"]
        or receipt.get("raw_sha256") != raw_hash
        or receipt.get("raw_bytes") != raw_size
        or plan["run_id"] != run_id
        or plan["configuration"] != configuration
        or plan["workload_kind"] != workload_kind
    ):
        raise ValueError("execution_artifact_binding_mismatch")
    completed = (
        receipt.get("execution_state") == "completed"
        and receipt.get("process_exit_code") == 0
        and receipt.get("timed_out") is False
        and receipt.get("raw_limit_exceeded") is False
        and receipt.get("nfr_accepted") is False
    )
    if not completed:
        raise ValueError("execution_incomplete_or_failed")
    target_plan_bytes = _read_bounded(
        Path(__file__).resolve().parents[3] / plan["target_plan_path"], 100_000
    )
    target_plan = json.loads(target_plan_bytes)
    revisions = target_plan.get("revisions", {})
    return {
        "execution_artifact_binding_verified": True,
        "execution_completed": True,
        "latency_timing_binary_hash_bound": receipt.get("k6_binary_sha256")
        == plan["k6_binary_sha256"],
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "run_plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "target_plan_sha256": plan["target_plan_sha256"],
        "profile_sha256": profile_hash,
        "raw_sha256": raw_hash,
        "application_revision": revisions.get("application_revision"),
        "dataset_fingerprint": revisions.get("dataset_fingerprint"),
        "model_revision": revisions.get("model_revision"),
        "measurement_validity_reviewed": False,
        "nfr_accepted": False,
    }
