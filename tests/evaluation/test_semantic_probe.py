"""Portable chunk/integrity checks; no isolated ML dependencies or fake inference."""

import hashlib

import pytest

from scripts.evaluation.semantic.probe import chunk_ranges, long_description_fixture
from scripts.evaluation.semantic.fetch import checked_digest


@pytest.mark.parametrize("length", [0, 1, 253, 254, 255, 476, 5000, 21344])
def test_chunk_coverage_and_overlap(length):
    ranges = chunk_ranges(length)
    assert ranges[0][0] == 0 and ranges[-1][1] == length
    assert all(0 <= end - start <= 254 for start, end in ranges)
    assert len(ranges) <= 96
    covered = {index for start, end in ranges for index in range(start, end)}
    assert covered == set(range(length))
    for previous, following in zip(ranges, ranges[1:]):
        assert previous[1] - following[0] == 32


@pytest.mark.parametrize("length", [-1, True, 21345])
def test_invalid_or_over_budget_chunking_fails_without_truncation(length):
    with pytest.raises(ValueError):
        chunk_ranges(length)


def test_long_probe_fixture_meets_real_description_contract():
    text = long_description_fixture()
    assert len(text) <= 5000
    assert text.endswith("collectible telescope")


def test_artifact_integrity_checks(tmp_path):
    path = tmp_path / "model.bin"
    path.write_bytes(b"controlled artifact")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert (
        checked_digest(path, {"bytes": path.stat().st_size, "sha256": digest}) == digest
    )
    with pytest.raises(ValueError, match="size mismatch"):
        checked_digest(path, {"bytes": 0, "sha256": digest})
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        checked_digest(path, {"bytes": path.stat().st_size, "sha256": "0" * 64})
    blob = hashlib.sha1(
        b"blob " + str(path.stat().st_size).encode() + b"\0" + path.read_bytes()
    ).hexdigest()
    assert (
        checked_digest(
            path, {"bytes": path.stat().st_size, "sha256": None, "git_blob": blob}
        )
        == digest
    )
    with pytest.raises(ValueError, match="identity mismatch"):
        checked_digest(
            path, {"bytes": path.stat().st_size, "sha256": None, "git_blob": "0" * 40}
        )
