"""Create bounded, separate local evidence files without running an experiment.

Known unsafe fields and values are rejected, but privacy review remains required.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any

from scripts.evaluation.k6.comparison_manifest import SENSITIVE_KEY, SENSITIVE_VALUE

MAX_RAW_BYTES = 100_000_000
MAX_REPORT_BYTES = 2_000_000
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}\Z")


EXTRA_SENSITIVE_KEY = re.compile(
    r"^(?:body|response_body|request_body|response_headers|request_headers|"
    r"headers|embedding|embeddings|query_embedding|message_plaintext|"
    r"provider_error|error_message|error|response|request|content|plaintext|"
    r"message|query|query_text|q|url|uri|stack|traceback)$",
    re.IGNORECASE,
)
COOKIE_VALUE = re.compile(
    r"(?:__Host-clip_session|clip_session_dev)\s*=", re.IGNORECASE
)


def _reject_constant(value: str) -> None:
    """Reject JSON constants that are not finite JSON numbers."""
    raise ValueError("invalid_json_constant")


def _check_json_value(value: Any) -> None:
    """Reject known sensitive keys and values without reporting their contents."""
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            for key, child in item.items():
                if (
                    not isinstance(key, str)
                    or SENSITIVE_KEY.search(key)
                    or EXTRA_SENSITIVE_KEY.fullmatch(key)
                ):
                    raise ValueError("unsafe_evidence_content")
                pending.append(child)
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, str):
            if SENSITIVE_VALUE.search(item) or COOKIE_VALUE.search(item):
                raise ValueError("unsafe_evidence_content")
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("invalid_evidence_number")


def _check_evidence(raw: bytes, report: bytes) -> None:
    """Inspect complete JSONL/raw and JSON/report before creating any files."""
    try:
        lines = raw.decode("utf-8").splitlines()
        if not lines or any(not line.strip() for line in lines):
            raise ValueError("invalid_raw_jsonl")
        for line in lines:
            _check_json_value(json.loads(line, parse_constant=_reject_constant))
        _check_json_value(json.loads(report, parse_constant=_reject_constant))
    except ValueError, UnicodeError, RecursionError:
        raise ValueError("invalid_or_unsafe_evidence") from None


def _verify_file(directory: int, name: str, expected: bytes) -> None:
    """Read back one regular file and compare its exact SHA-256 fingerprint."""
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size != len(expected):
            raise ValueError("captured_file_mismatch")
        digest = hashlib.sha256()
        count = 0
        while True:
            chunk = os.read(fd, 1_048_576)
            if not chunk:
                break
            count += len(chunk)
            if count > len(expected):
                raise ValueError("captured_file_mismatch")
            digest.update(chunk)
        after = os.fstat(fd)
        if (
            count != len(expected)
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ctime_ns != after.st_ctime_ns
            or digest.digest() != hashlib.sha256(expected).digest()
        ):
            raise ValueError("captured_file_mismatch")
    finally:
        os.close(fd)


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
    _check_evidence(raw, report)
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
            _verify_file(run_fd, "raw.jsonl", raw)
            _verify_file(run_fd, "report.json", report)
            record = {
                "run_id": run_id,
                "raw_reference": f"{run_id}/raw.jsonl",
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "report_reference": f"{run_id}/report.json",
                "report_sha256": hashlib.sha256(report).hexdigest(),
                "privacy_reviewed": False,
                "run_validity_verified": False,
            }
            fingerprint_bytes = (
                json.dumps(record, sort_keys=True, indent=2) + "\n"
            ).encode()
            _write_new(run_fd, "fingerprints.json", fingerprint_bytes)
            _verify_file(run_fd, "fingerprints.json", fingerprint_bytes)
            os.fsync(run_fd)
            return record
        finally:
            os.close(run_fd)
    finally:
        os.close(root_fd)
