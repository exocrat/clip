"""Exercise exclusive local evidence capture with synthetic bytes only."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts.evaluation.k6 import comparison_evidence_capture as capture
from scripts.evaluation.k6.comparison_artifacts import _hash_artifact


def test_capture_writes_distinct_files_and_preserves_existing_run(
    tmp_path: Path,
) -> None:
    raw = b'{"synthetic_metric":1}\n'
    report = b'{"synthetic_report":true}\n'
    record = capture.capture_local_evidence(tmp_path, "synthetic-A-1", raw, report)
    raw_path = tmp_path / record["raw_reference"]
    report_path = tmp_path / record["report_reference"]
    assert raw_path.read_bytes() == raw
    assert report_path.read_bytes() == report
    assert record["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert record["report_sha256"] == hashlib.sha256(report).hexdigest()
    assert _hash_artifact(tmp_path, record["raw_reference"])[0] == record["raw_sha256"]
    assert json.loads((raw_path.parent / "fingerprints.json").read_text()) == record
    assert record["privacy_reviewed"] is False
    with pytest.raises(FileExistsError):
        capture.capture_local_evidence(
            tmp_path, "synthetic-A-1", b"changed", b"changed"
        )
    assert raw_path.read_bytes() == raw
    assert report_path.read_bytes() == report


@pytest.mark.parametrize("run_id", ["../escape", ".", "two words", "x", "a/b"])
def test_invalid_ids_fail_before_creating_files(tmp_path: Path, run_id: str) -> None:
    with pytest.raises(ValueError):
        capture.capture_local_evidence(tmp_path, run_id, b"x", b"y")
    assert list(tmp_path.iterdir()) == []


def test_incomplete_capture_is_retained_without_completion_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = capture._write_new

    def fail_report(directory: int, name: str, data: bytes) -> None:
        if name == "report.json":
            raise OSError("synthetic failure")
        original(directory, name, data)

    monkeypatch.setattr(capture, "_write_new", fail_report)
    with pytest.raises(OSError):
        capture.capture_local_evidence(tmp_path, "synthetic-A-1", b"raw", b"report")
    folder = tmp_path / "synthetic-A-1"
    assert (folder / "raw.jsonl").read_bytes() == b"raw"
    assert not (folder / "fingerprints.json").exists()
    with pytest.raises(FileExistsError):
        capture.capture_local_evidence(tmp_path, "synthetic-A-1", b"raw", b"report")


def test_rejects_empty_inputs_and_symlink_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        capture.capture_local_evidence(tmp_path, "synthetic-A-1", b"", b"report")
    link = tmp_path / "alias"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        capture.capture_local_evidence(link, "synthetic-A-1", b"raw", b"report")
