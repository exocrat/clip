"""Experiment inputs stay bound to accepted bytes after implementation changes."""

from pathlib import Path
import pytest
from data.generators import reference
from scripts.evaluation.frozen_reference import LABELS, ROOT, load_frozen_reference


def test_frozen_reference_reads_accepted_archive_without_regenerating(monkeypatch):
    def refuse_regeneration(*args, **kwargs):
        raise AssertionError("An experiment must not regenerate its frozen dataset")

    monkeypatch.setattr(reference, "build_reference", refuse_regeneration)
    bundle, labels, binding = load_frozen_reference()
    assert len(bundle["users"]) == 5000
    assert len(bundle["listings"]) == 1000
    assert len(labels["queries"]) == 22
    assert not binding.preview_only
    assert all(len(ids) == 800 for ids in binding.eligible_ids.values())


def test_frozen_reference_rejects_changed_judgments_before_archive_use(monkeypatch):
    original = Path.read_bytes

    def changed(path):
        raw = original(path)
        return raw + b" " if path == ROOT / LABELS else raw

    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(ValueError, match="frozen_reference_input_changed"):
        load_frozen_reference()
