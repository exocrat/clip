"""Campaign orchestration must retain failures and never repeat measured work."""

from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path

import pytest

from scripts.evaluation.campaign_runner import (
    Journal,
    UnsafeStop,
    run_campaign,
    verify_bundle,
)
from scripts.evaluation.k6.lambda_concurrency import BoundedGuard, failure_code
from scripts.evaluation.performance_campaign import build_campaign
from scripts.evaluation.k6.cloudwatch_capture import build_queries
from tests.evaluation.test_cloudwatch_capture import _plan


def plan():
    return {
        "batch_id": "synthetic-campaign",
        "maximum_seconds": 1000,
        "entries": [
            {"run_id": f"synthetic-{i}", "kind": "comparison", "configuration": "A"}
            for i in range(3)
        ],
    }


class Fake:
    def __init__(self, fail=False, unsafe=False):
        self.calls = []
        self.cleaned = 0
        self.fail = fail
        self.unsafe = unsafe

    def run(self, entry, progress):
        self.calls.append(("run", entry["run_id"]))
        progress("prepared")
        if self.unsafe:
            raise UnsafeStop("database_connection_safety_limit")
        return {"state": "failed" if self.fail else "completed", "raw_retained": True}

    def recover(self, entry, progress):
        self.calls.append(("recover", entry["run_id"]))
        return {"state": "interrupted", "raw_retained": True}

    def cleanup(self):
        self.cleaned += 1
        return {"complete": True}


def test_bad_results_continue_and_completed_entries_do_not_run_again(tmp_path):
    fake = Fake(fail=True)
    run_campaign(plan(), fake, tmp_path)
    assert len(fake.calls) == 3 and fake.cleaned == 1
    before = (tmp_path / "journal.ndjson").read_bytes()
    run_campaign(plan(), fake, tmp_path)
    assert len(fake.calls) == 3
    assert (tmp_path / "journal.ndjson").read_bytes() == before
    status = json.loads((tmp_path / "status.json").read_text())
    assert status["terminal_count"] == 3
    assert all(r["state"] == "failed" for r in status["entries"])


def test_resume_recovers_instead_of_reissuing_workload_and_unsafe_stop_cleans(tmp_path):
    p = plan()
    journal = Journal(tmp_path, p)
    journal.append("synthetic-0", "running", stage="workload_started")
    fake = Fake()
    run_campaign(p, fake, tmp_path)
    assert fake.calls[0] == ("recover", "synthetic-0")
    assert len(fake.calls) == 3
    second = tmp_path / "unsafe"
    unsafe = Fake(unsafe=True)
    result = run_campaign(p, unsafe, second)
    assert result["campaign_state"] == "safety_stopped"
    assert len(unsafe.calls) == 1 and unsafe.cleaned == 1


def test_campaign_sources_and_expiry_are_exact(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("synthetic")
    p = {
        **plan(),
        "bound_files": {str(source): hashlib.sha256(source.read_bytes()).hexdigest()},
    }
    raw = json.dumps(p).encode()
    approval = {
        "approved": True,
        "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "expires_at_utc": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    }
    verify_bundle(p, approval, raw)
    source.write_text("changed")
    with pytest.raises(ValueError, match="source_changed"):
        verify_bundle(p, approval, raw)


def test_main_first_single_nfr_round_preserves_all_18_formal_runs():
    campaign = build_campaign("night-fixture", nfr_repetitions=1, main_first=True)
    entries = campaign["entries"]
    assert len(entries) == 31
    main = entries[:18]
    assert all(e["kind"] == "comparison" for e in main)
    assert [(e["configuration"], e["condition"]) for e in main[:6]] == [
        (c, condition) for c in ("A", "B") for condition in ("low", "normal", "burst")
    ]
    assert [e["configuration"] for e in main[6:12]] == ["B"] * 3 + ["A"] * 3
    assert all(e["repetition"] == 1 for e in entries[18:])


def test_transient_monitor_failure_recovers_but_drift_does_not_retry():
    calls = []
    clock = [0.0]

    def check():
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError("SECRET provider prose")

    guard = BoundedGuard(
        check,
        monotonic=lambda: clock[0],
        sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
    )
    guard()
    assert len(calls) == 3 and guard.diagnostics()["recovered_checks"] == 1
    assert "SECRET" not in json.dumps(guard.diagnostics())

    def drift():
        raise ValueError("lambda_unreserved_quota_drift")

    guard = BoundedGuard(drift, sleep=lambda _: pytest.fail("drift must not retry"))
    with pytest.raises(ValueError, match="quota_drift"):
        guard()
    assert guard.diagnostics()["failure_count"] == 1
    assert failure_code(ValueError("PRIVATE")) == "guard_observation_failed"


def test_observer_failure_retry_count_is_bounded():
    calls = []

    def check():
        calls.append(1)
        raise ConnectionError("SECRET")

    guard = BoundedGuard(check, sleep=lambda _: None)
    with pytest.raises(ConnectionError):
        guard()
    assert len(calls) == 4
    assert "SECRET" not in json.dumps(guard.diagnostics())


def test_alb_dimensions_keep_full_targetgroup_resource_suffix():
    p = _plan()
    expected = {
        p["resources"][name].split(":", 5)[5]
        for name in ("ecs_target_group_arn", "lambda_target_group_arn")
    }
    groups = build_queries(p)
    for queries in groups.values():
        for query in queries:
            for dimension in query["MetricStat"]["Metric"]["Dimensions"]:
                if dimension["Name"] == "TargetGroup":
                    assert dimension["Value"] in expected


def test_formal_comparison_uses_hash_checked_staged_schedule(tmp_path):
    from scripts.evaluation.k6.comparison_report import bound_schedule

    schedule = b'{"conditions": []}'
    stage = tmp_path / "stage-root/formal-run"
    stage.mkdir(parents=True)
    (stage / "schedule.json").write_bytes(schedule)
    (stage / "staged-files.json").write_text(
        json.dumps(
            {
                "run_id": "formal-run",
                "condition": "low",
                "files": {"schedule.json": hashlib.sha256(schedule).hexdigest()},
            }
        )
    )
    plan = {"run_id": "formal-run", "condition": "low"}
    assert bound_schedule(plan, tmp_path) == stage / "schedule.json"
    (stage / "schedule.json").write_text("{}")
    with pytest.raises(ValueError, match="staged_schedule_binding_mismatch"):
        bound_schedule(plan, tmp_path)


def test_supervised_invalid_preparation_holds_remaining_entries(tmp_path):
    class Invalid(Fake):
        def run(self, entry, progress):
            self.calls.append(entry["run_id"])
            return {"state": "invalid", "reason": "preparation_failed"}

    fake = Invalid()
    result = run_campaign({**plan(), "stop_on_invalid": True}, fake, tmp_path)
    assert result["campaign_state"] == "operator_attention_required"
    assert len(fake.calls) == 1 and fake.cleaned == 1
    state = json.loads((tmp_path / "status.json").read_text())
    assert state["entries"][1]["state"] == "pending"
