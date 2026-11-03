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
        capture.capture_local_evidence(tmp_path, "synthetic-A-1", b"{}", b"{}")
    assert raw_path.read_bytes() == raw
    assert report_path.read_bytes() == report


@pytest.mark.parametrize("run_id", ["../escape", ".", "two words", "x", "a/b"])
def test_invalid_ids_fail_before_creating_files(tmp_path: Path, run_id: str) -> None:
    with pytest.raises(ValueError):
        capture.capture_local_evidence(tmp_path, run_id, b"{}", b"{}")
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
        capture.capture_local_evidence(tmp_path, "synthetic-A-1", b"{}", b"{}")
    folder = tmp_path / "synthetic-A-1"
    assert (folder / "raw.jsonl").read_bytes() == b"{}"
    assert not (folder / "fingerprints.json").exists()
    with pytest.raises(FileExistsError):
        capture.capture_local_evidence(tmp_path, "synthetic-A-1", b"{}", b"{}")


def test_rejects_empty_inputs_and_symlink_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        capture.capture_local_evidence(tmp_path, "synthetic-A-1", b"", b"{}")
    link = tmp_path / "alias"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        capture.capture_local_evidence(link, "synthetic-A-1", b"{}", b"{}")


@pytest.mark.parametrize(
    "bad",
    [
        b'{"cookie":"synthetic-private"}\n',
        b'{"response_body":{"value":"synthetic"}}\n',
        b'{"embedding":[1,2]}\n',
        b'{"response":{"content":"synthetic"}}\n',
        b'{"query_text":"synthetic"}\n',
        b'{"metric":"Bearer synthetic-secret"}\n',
        b'{"metric":"__Host-clip_session=synthetic"}\n',
        b'{"\\u0063ookie":"synthetic"}\n',
        b'{"value":NaN}\n',
        b"not-json\n",
    ],
)
def test_unsafe_or_invalid_raw_refused_before_directory(
    tmp_path: Path, bad: bytes
) -> None:
    with pytest.raises(ValueError, match="invalid_or_unsafe_evidence") as error:
        capture.capture_local_evidence(tmp_path, "synthetic-A-1", bad, b"{}")
    assert "synthetic-private" not in str(error.value)
    assert list(tmp_path.iterdir()) == []


def test_unsafe_report_refused_before_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid_or_unsafe_evidence"):
        capture.capture_local_evidence(
            tmp_path, "synthetic-A-1", b"{}\n", b'{"provider_error":"synthetic"}'
        )
    assert list(tmp_path.iterdir()) == []


def test_changed_written_file_prevents_fingerprint_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = capture._write_new

    def write_corrupted(directory: int, name: str, data: bytes) -> None:
        original(directory, name, b"[]" if name == "report.json" else data)

    monkeypatch.setattr(capture, "_write_new", write_corrupted)
    with pytest.raises(ValueError, match="captured_file_mismatch"):
        capture.capture_local_evidence(tmp_path, "synthetic-A-1", b"{}\n", b"{}")
    assert not (tmp_path / "synthetic-A-1" / "fingerprints.json").exists()


def test_accepts_synthetic_k6_points_and_existing_report(tmp_path: Path) -> None:
    from scripts.evaluation.k6.comparison_report import summarize_points

    point = {
        "type": "Point",
        "metric": "clip_comparison_outcomes",
        "data": {
            "time": "2026-11-02T00:00:00Z",
            "value": 1,
            "tags": {"phase": "low_measured", "kind": "browse", "outcome": "correct"},
        },
    }
    profile = {
        "conditions": [
            {"name": name, "warmup_rate": 1, "measured_rate": 1}
            for name in ("low", "normal", "burst")
        ],
        "warmup_seconds": 1,
        "measured_seconds": 1,
    }
    raw = (json.dumps(point) + "\n").encode()
    report = json.dumps(summarize_points([point], profile)).encode()
    record = capture.capture_local_evidence(tmp_path, "synthetic-A-1", raw, report)
    assert (tmp_path / record["raw_reference"]).read_bytes() == raw
    assert record["privacy_reviewed"] is False
