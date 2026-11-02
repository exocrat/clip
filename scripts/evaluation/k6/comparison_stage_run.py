"""Stage checked local comparison inputs without launching a process or workload."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from scripts.evaluation.k6.comparison_declared_parity import validate_declared_parity
from scripts.evaluation.k6.comparison_evidence_capture import _verify_file, _write_new
from scripts.evaluation.k6.comparison_offline_prepare import FILE_FIELDS, _read_local
from scripts.evaluation.k6.comparison_run_preflight import validate_run_inputs

MODULES = (
    "comparison_load.js",
    "comparison_cases.js",
    "comparison_checks.js",
    "comparison_schedule.js",
    "comparison_outcomes.js",
    "comparison_all_parity.js",
    "comparison_search_parity.js",
    "core.js",
)


def stage_run(
    paths: Mapping[str, Path],
    cycle: int,
    run_id: str,
    expected_profile_sha256: str,
    source_dir: Path,
    schedule_path: Path,
    expected_module_hashes: Any,
    staging_root: Path,
    *,
    parity_path: Path,
    parity_evidence_root: Path,
) -> dict[str, Any]:
    """Validate one planned run and stage exact bounded bytes in a new folder.

    Supplied fingerprints establish consistency, not independent approval or use.
    """
    if set(paths) != set(FILE_FIELDS):
        raise ValueError("all_input_paths_required")
    if type(cycle) is not int or cycle not in (1, 2, 3):
        raise ValueError("invalid_cycle")
    if not isinstance(run_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}", run_id
    ):
        raise ValueError("invalid_run_id")
    if not isinstance(expected_module_hashes, dict) or set(
        expected_module_hashes
    ) != set(MODULES):
        raise ValueError("all_module_fingerprints_required")
    data = {name: _read_local(paths[name]) for name in FILE_FIELDS}
    binding = json.loads(data["binding_plan"])
    reference = json.loads(data["ordered_reference"])
    plan = json.loads(data["paired_plan"])
    profile = json.loads(data["workload_profile"])
    checked = validate_run_inputs(
        binding,
        data["corpus"],
        reference,
        plan,
        profile,
        cycle,
        profile_bytes=data["workload_profile"],
        expected_profile_sha256=expected_profile_sha256,
    )
    if not checked["profile_hash_checked"]:
        raise ValueError("profile_hash_required")
    pairs = plan["cycles"][cycle - 1]["pairs"]
    matches = [
        pair
        for pair in pairs
        for side in ("A", "B")
        if run_id == pair[f"{side}_run_id"]
    ]
    if len(matches) != 1:
        raise ValueError("run_not_in_selected_cycle")
    parity_bytes = _read_local(parity_path)
    parity = json.loads(parity_bytes)
    parity_result = validate_declared_parity(
        parity,
        binding,
        data["corpus"],
        reference,
        plan,
        evidence_root=parity_evidence_root,
    )
    if (
        parity["cycle"] != cycle
        or parity["condition"] != matches[0]["condition"]
        or not parity_result["evidence_hashes_match"]
    ):
        raise ValueError("selected_run_parity_mismatch")
    module_bytes = {name: _read_local(source_dir / name) for name in MODULES}
    for name, content in module_bytes.items():
        expected = expected_module_hashes[name]
        if (
            not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
            or hashlib.sha256(content).hexdigest() != expected
        ):
            raise ValueError("module_fingerprint_mismatch")
    if expected_module_hashes["comparison_load.js"] != plan["shared_inputs"][
        "load_script_sha256"
    ].removeprefix("sha256:"):
        raise ValueError("load_script_plan_mismatch")
    schedule = _read_local(schedule_path)
    if hashlib.sha256(schedule).hexdigest() != plan["shared_inputs"][
        "schedule_sha256"
    ].removeprefix("sha256:"):
        raise ValueError("schedule_plan_mismatch")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ValueError("safe_file_access_unavailable")
    staging_root = staging_root.absolute()
    if staging_root.resolve(strict=True) != staging_root:
        raise ValueError("symlink_staging_root")
    files = {
        "profile.json": data["workload_profile"],
        "schedule.json": schedule,
        **module_bytes,
    }
    record: dict[str, Any] = {
        "run_id": run_id,
        "cycle": cycle,
        "condition": matches[0]["condition"],
        "parity_record_sha256": hashlib.sha256(parity_bytes).hexdigest(),
        "parity_evidence_hashes_checked": True,
        "deployed_parity_verified": False,
        "files": {
            name: hashlib.sha256(content).hexdigest()
            for name, content in sorted(files.items())
        },
        "independent_approval_verified": False,
        "actual_use_verified": False,
        "measurement_authorized": False,
    }
    root_fd = os.open(staging_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.mkdir(run_id, 0o700, dir_fd=root_fd)
        run_fd = os.open(
            run_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd
        )
        try:
            for name, content in files.items():
                _write_new(run_fd, name, content)
                _verify_file(run_fd, name, content)
            metadata = (json.dumps(record, sort_keys=True, indent=2) + "\n").encode()
            _write_new(run_fd, "staged-files.json", metadata)
            _verify_file(run_fd, "staged-files.json", metadata)
            os.fsync(run_fd)
        finally:
            os.close(run_fd)
    finally:
        os.close(root_fd)
    return record


def main() -> None:
    """Accept local inputs and print only aggregate staging status."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in FILE_FIELDS:
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-profile-sha256", required=True)
    parser.add_argument("--module-hashes", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--parity", type=Path, required=True)
    parser.add_argument("--parity-evidence-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        stage_run(
            {name: getattr(args, name) for name in FILE_FIELDS},
            args.cycle,
            args.run_id,
            args.expected_profile_sha256,
            args.source_dir,
            args.schedule,
            json.loads(_read_local(args.module_hashes)),
            args.staging_root,
            parity_path=args.parity,
            parity_evidence_root=args.parity_evidence_root,
        )
        print(
            json.dumps(
                {"staged": True, "measurement_authorized": False}, sort_keys=True
            )
        )
    except (OSError, ValueError, TypeError, KeyError):
        parser.exit(2, "Comparison staging failed; no workload was started\n")


if __name__ == "__main__":
    main()
