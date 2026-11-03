"""Verify bounded local profile, telemetry and evidence hashes for a captured run.

No cloud access or provider calls are made. Hash equality does not attest source,
artifact content, telemetry health, clock quality or measurement validity.
"""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

from scripts.evaluation.k6.comparison_manifest import TEMPLATE, _utc, validate_manifest
from scripts.evaluation.k6.comparison_telemetry import (
    ARTIFACT_NAMES,
    _reference,
    validate_telemetry,
)

MAX_METADATA_BYTES = 2_000_000
MAX_ARTIFACT_BYTES = 100_000_000


def _hash_artifact(root: Path, reference: object) -> tuple[str, tuple[int, int]]:
    """Hash one regular file and return its device/inode without following links."""
    if not _reference(reference) or not isinstance(reference, str):
        raise ValueError("unsafe_artifact_reference")
    parts = reference.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("unsafe_artifact_reference")
    root = root.absolute()
    if root.resolve(strict=True) != root:
        raise ValueError("symlink_evidence_root")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ValueError("safe_file_access_unavailable")
    with ExitStack() as stack:
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stack.callback(os.close, directory)
        for part in parts[:-1]:
            directory = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
            )
            stack.callback(os.close, directory)
        fd = os.open(
            parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
        )
        stack.callback(os.close, fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_ARTIFACT_BYTES:
            raise ValueError("artifact_not_bounded_regular_file")
        digest = hashlib.sha256()
        count = 0
        while True:
            chunk = os.read(fd, 1_048_576)
            if not chunk:
                break
            count += len(chunk)
            if count > MAX_ARTIFACT_BYTES:
                raise ValueError("artifact_too_large")
            digest.update(chunk)
        after = os.fstat(fd)
        if (
            count != before.st_size
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ctime_ns != after.st_ctime_ns
        ):
            raise ValueError("artifact_changed_during_hash")
        return digest.hexdigest(), (after.st_dev, after.st_ino)


def validate_artifacts(
    manifest: dict[str, Any], telemetry: object, evidence_root: Path
) -> dict[str, Any]:
    """Validate captured metadata, coverage and local file hashes, not contents."""
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    if validate_manifest(manifest, template)["state"] != "captured":
        raise ValueError("captured_manifest_required")
    metadata = validate_telemetry(telemetry, manifest)
    cost = manifest["cost_inputs"]
    if _utc(cost["interval_start_utc"], "cost start") > _utc(
        manifest["run"]["actual_start_utc"], "run start"
    ) or _utc(cost["interval_end_utc"], "cost end") < _utc(
        manifest["run"]["actual_end_utc"], "run end"
    ):
        raise ValueError("cost_interval_does_not_cover_run")
    references = [
        (
            manifest["resource_telemetry"][f"{name}_artifact_reference"],
            manifest["resource_telemetry"][f"{name}_artifact_sha256"],
        )
        for name in ARTIFACT_NAMES
    ] + [
        (cost["source_reference"], cost["source_sha256"]),
        (
            manifest["workload"]["execution_profile_reference"],
            manifest["workload"]["execution_profile_sha256"],
        ),
    ]
    hashed: dict[str, tuple[str, tuple[int, int]]] = {}
    for reference, expected in references:
        hashed[reference] = _hash_artifact(evidence_root, reference)
        if hashed[reference][0] != expected.removeprefix("sha256:"):
            raise ValueError("artifact_hash_mismatch")
    raw = manifest["evidence"]["raw_output_reference"]
    report = manifest["evidence"]["derived_report_reference"]
    hashed[raw] = _hash_artifact(evidence_root, raw)
    hashed[report] = _hash_artifact(evidence_root, report)
    if hashed[raw][0] != manifest["evidence"]["raw_output_sha256"].removeprefix(
        "sha256:"
    ) or hashed[report][0] != manifest["evidence"][
        "derived_report_sha256"
    ].removeprefix(
        "sha256:"
    ):
        raise ValueError("artifact_hash_mismatch")
    if hashed[raw][1] == hashed[report][1]:
        raise ValueError("raw_and_derived_report_must_be_distinct_files")
    return {
        "artifact_hashes_match": True,
        "execution_profile_hash_matches": True,
        "raw_output_hash_matches": True,
        "derived_report_hash_matches": True,
        "raw_and_derived_report_are_distinct_files": True,
        "telemetry_metadata_valid": True,
        "generator_checks": metadata["generator_checks"],
        "artifact_contents_verified": False,
        "clock_independently_verified": False,
        "measurement_authorized": False,
        "nfr_accepted": False,
    }


def _read_metadata(path: Path) -> Any:
    """Read bounded input metadata; never print its content or raw errors."""
    if path.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError("metadata_too_large")
    data = path.read_bytes()
    if len(data) > MAX_METADATA_BYTES:
        raise ValueError("metadata_too_large")
    return json.loads(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("telemetry", type=Path)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate_artifacts(
            _read_metadata(args.manifest),
            _read_metadata(args.telemetry),
            args.evidence_root,
        )
        print(json.dumps(result, sort_keys=True))
    except OSError, ValueError, KeyError, TypeError:
        parser.exit(2, "Artifact verification failed; no workload was started\n")


if __name__ == "__main__":
    main()
