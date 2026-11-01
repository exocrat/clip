"""Local preparation refuses unsafe inputs and never returns synthetic sessions."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.evaluation.k6 import comparison_runner


def test_runner_returns_only_sanitized_statuses(monkeypatch):
    """The session reaches only the child environment, never the result."""
    monkeypatch.setattr(
        comparison_runner,
        "inspection_session",
        lambda port: "clip_session_dev=synthetic",
    )

    def run_child(command, **kwargs):
        if command[1] == "inspect":
            assert (
                kwargs["env"]["CLIP_COMPARISON_LOCAL_COOKIE"]
                == "inspection-preflight-placeholder"
            )
            return SimpleNamespace(returncode=0)
        assert (
            kwargs["env"]["CLIP_COMPARISON_LOCAL_COOKIE"]
            == "clip_session_dev=synthetic"
        )
        output = next(
            arg.removeprefix("json=") for arg in command if arg.startswith("json=")
        )
        point = {
            "type": "Point",
            "metric": "http_reqs",
            "data": {"tags": {"kind": "browse", "status": "200", "case_index": "0"}},
        }
        outcome = {
            "type": "Point",
            "metric": "clip_comparison_preparation_response",
            "data": {
                "tags": {"kind": "browse", "case_index": "0", "outcome": "correct"}
            },
        }
        Path(output).write_text(json.dumps(point) + "\n" + json.dumps(outcome) + "\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(comparison_runner.subprocess, "run", run_child)
    result = comparison_runner.run(
        5175, [{"kind": "browse", "query": {}}], Path("/usr/bin/true")
    )
    assert result == {
        "measurement": False,
        "correct": True,
        "requests": [{"kind": "browse", "status": "200", "outcome": "correct"}],
    }
    assert "synthetic" not in json.dumps(result)


def test_invalid_k6_preflight_refuses_before_login(monkeypatch):
    """An invalid full case batch is rejected before the synthetic login."""
    monkeypatch.setattr(
        comparison_runner.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=1),
    )
    monkeypatch.setattr(
        comparison_runner,
        "inspection_session",
        lambda port: pytest.fail("must not request a session"),
    )
    with pytest.raises(ValueError, match="Invalid scenario"):
        comparison_runner.run(
            5175, [{"kind": "search", "query": {"q": "desk"}}], Path("/usr/bin/true")
        )


def test_unsafe_inputs_rejected_before_login(monkeypatch):
    """Invalid ports, case counts and tool paths never trigger a session request."""

    def fail_login(port):
        pytest.fail("must not request a session")

    monkeypatch.setattr(comparison_runner, "inspection_session", fail_login)
    for port, cases, binary in [
        (443, [{}], Path("/usr/bin/true")),
        (5175, [], Path("/usr/bin/true")),
        (5175, [{}] * 11, Path("/usr/bin/true")),
        (5175, [{}], Path("relative")),
    ]:
        with pytest.raises(ValueError):
            comparison_runner.run(port, cases, binary)
