from pathlib import Path
import pytest
from scripts.evaluation.observer_journal import record


def test_observer_keeps_prior_bytes_and_refuses_private_fields(tmp_path: Path) -> None:
    p = tmp_path / "events.ndjson"
    plan = {"observation_path": str(p)}
    record(plan, {"event": "baseline", "status": 200})
    before = p.read_bytes()
    record(plan, {"event": "capacity", "state": {"running": 2}})
    assert p.read_bytes().startswith(before) and len(p.read_text().splitlines()) == 2
    with pytest.raises(ValueError, match="private_observer_field_refused"):
        record(plan, {"nested": {"password": "synthetic"}})
    assert len(p.read_text().splitlines()) == 2
    link = tmp_path / "link"
    link.symlink_to(p)
    with pytest.raises(OSError):
        record({"observation_path": str(link)}, {"event": "no"})
