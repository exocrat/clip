"""Create bounded, separate local evidence files without running an experiment.

Callers must supply privacy-reviewed bytes; this module does not scan content.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

MAX_RAW_BYTES = 100_000_000
MAX_REPORT_BYTES = 2_000_000
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}\Z")


def _write_new(directory: int, name: str, data: bytes) -> None:
    """Create one private file exclusively; keep partial files on failure."""
    fd = os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory,
    )
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("evidence_write_failed")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def capture_local_evidence(
    root: Path, run_id: str, raw: bytes, report: bytes
) -> dict[str, Any]:
    """Write distinct raw/report files and a final fingerprint record in a new folder.

    A missing final fingerprint record indicates incomplete capture. This helper
    does not establish privacy, authenticity, validity, or durable immutability.
    """
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("invalid_run_id")
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RAW_BYTES:
        raise ValueError("invalid_raw_output")
    if not isinstance(report, bytes) or not 0 < len(report) <= MAX_REPORT_BYTES:
        raise ValueError("invalid_report")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ValueError("safe_file_access_unavailable")
    root = root.absolute()
    if root.resolve(strict=True) != root:
        raise ValueError("symlink_evidence_root")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.mkdir(run_id, 0o700, dir_fd=root_fd)
        run_fd = os.open(
            run_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd
        )
        try:
            _write_new(run_fd, "raw.jsonl", raw)
            _write_new(run_fd, "report.json", report)
            record = {
                "run_id": run_id,
                "raw_reference": f"{run_id}/raw.jsonl",
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "report_reference": f"{run_id}/report.json",
                "report_sha256": hashlib.sha256(report).hexdigest(),
                "privacy_reviewed": False,
                "run_validity_verified": False,
            }
            _write_new(
                run_fd,
                "fingerprints.json",
                (json.dumps(record, sort_keys=True, indent=2) + "\n").encode(),
            )
            os.fsync(run_fd)
            return record
        finally:
            os.close(run_fd)
    finally:
        os.close(root_fd)
