"""Offline safety tests for the host launcher, never a cloud/database caller."""

import ast
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest

from scripts import identity_retention_job as job

IMAGE = (
    "335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:"
    + "a" * 64
)
DEADLINE = datetime.now(timezone.utc) + timedelta(hours=1)
COUNTS = dict.fromkeys(job.CATEGORIES, 0)


def test_host_python39_and_child_payload_compile(monkeypatch):
    """Host grammar stays3.9; child compiles and defaults to read-only cleanup."""
    ast.parse(Path(job.__file__).read_text(), feature_version=(3, 9))
    captured = []

    def command(args, payload=None):
        if args[0] == "ps":
            return "a" * 12
        if args[0] == "inspect":
            return IMAGE
        compile(payload, "<container-payload>", "exec")
        captured.append(payload)
        return json.dumps({"dry_run": True, "counts": COUNTS})

    monkeypatch.setattr(job, "command", command)
    assert job.run_job(IMAGE, 6, DEADLINE, apply=False)["dry_run"]
    assert len(captured) == 1 and "'--apply'" not in captured[0]
    assert "signal.alarm(90)" in captured[0]


def test_expired_scope_refuses_before_client(monkeypatch):
    monkeypatch.setattr(job, "command", lambda *args: pytest.fail("Client called"))
    with pytest.raises(ValueError):
        job.run_job(
            IMAGE, 6, datetime.now(timezone.utc) - timedelta(seconds=1), apply=True
        )


def test_unreviewed_image_refuses_before_exec(monkeypatch):
    def command(args, payload=None):
        assert args[0] in ("ps", "inspect")
        return "a" * 12 if args[0] == "ps" else IMAGE + "drift"

    monkeypatch.setattr(job, "command", command)
    with pytest.raises(ValueError):
        job.run_job(IMAGE, 6, DEADLINE, apply=True)


def test_unexpected_child_output_is_redacted(monkeypatch, capsys):
    def command(args, payload=None):
        if args[0] == "ps":
            return "a" * 12
        if args[0] == "inspect":
            return IMAGE
        return "private-child-output-must-not-escape"

    monkeypatch.setattr(job, "command", command)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "identity_retention_job.py",
            "--image",
            IMAGE,
            "--revision",
            "6",
            "--deadline-utc",
            DEADLINE.isoformat(),
            "--apply",
        ],
    )
    assert job.main() == 1
    output = capsys.readouterr()
    assert "private-child-output" not in output.out + output.err
    assert "failed; inspect target" in output.out
