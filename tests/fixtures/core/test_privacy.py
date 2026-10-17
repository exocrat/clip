"""Actual failure-report and snapshot checks using synthetic sentinel values only."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.core.config import load_settings
from clip_test_fixtures import (
    Fail,
    Return,
    make_provider_scenarios,
    make_test_provider,
    redact_snapshot,
)

SENTINEL = "synthetic-private-fixture-sentinel"


@pytest.mark.parametrize(
    "field",
    [
        "email",
        "phone",
        "upi_id",
        "contacts",
        "Authorization",
        "OTP",
        "private-key",
        "message_plaintext",
        "message_ciphertext",
        "headers",
    ],
)
def test_sensitive_fields_are_explicitly_masked(field):
    """Known sensitive field labels survive only with a fixed redaction marker."""
    snapshot = redact_snapshot({"data": {field: SENTINEL}})
    assert SENTINEL not in json.dumps(snapshot)
    assert "[REDACTED]" in json.dumps(snapshot)


def test_unknown_values_keys_and_objects_are_not_rendered():
    """Unknown metadata and private map keys cannot bypass the allowlist."""

    class Unrenderable:
        """Represent a private object that must not be inspected."""

        def __repr__(self):
            """Fail if diagnostic code tries to inspect the payload."""
            raise AssertionError("Private object must not be rendered")

    snapshot = redact_snapshot(
        {
            SENTINEL: SENTINEL,
            "data": [SENTINEL, 9876543210, b"synthetic-bytes", Unrenderable()],
            "status": SENTINEL,
            "code": SENTINEL,
        }
    )
    assert SENTINEL not in json.dumps(snapshot)
    assert "9876543210" not in json.dumps(snapshot)
    assert "synthetic-bytes" not in json.dumps(snapshot)
    assert snapshot["status"] == snapshot["code"] == "[REDACTED]"


def test_safe_status_error_and_count_metadata_remain_useful():
    """Diagnostic redaction does not discard approved failure/status information."""
    assert redact_snapshot(
        {
            "status": 503,
            "error": {"code": "dependency_unavailable", "message": SENTINEL},
            "call_count": 2,
        }
    ) == {
        "status": 503,
        "error": {"code": "dependency_unavailable", "message": "[REDACTED]"},
        "call_count": 2,
    }


def test_outcome_and_provider_snapshots_hide_values(monkeypatch):
    """Provider/scenario representations never reveal queued or returned payloads."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    monkeypatch.setenv("CLIP_EMAIL_PROVIDER", "fake")
    payload = {"email": SENTINEL, "message_plaintext": SENTINEL}
    outcome = Return(payload)
    provider = make_test_provider(load_settings(), "email", [outcome])
    snapshots = [
        redact_snapshot(outcome),
        redact_snapshot(provider),
        redact_snapshot(Fail("unavailable")),
    ]
    assert SENTINEL not in json.dumps(snapshots)
    assert SENTINEL not in repr(make_provider_scenarios(payload, payload))
    assert snapshots[1]["remaining"] == 1


def test_recursive_and_large_snapshots_are_bounded():
    """Cyclic or oversized test payloads cannot create unbounded failure output."""
    recursive = {}
    recursive["data"] = recursive
    assert "[REDACTED]" in json.dumps(redact_snapshot(recursive))
    assert len(redact_snapshot(list(range(100)))) == 33
    assert len(redact_snapshot({str(i): SENTINEL for i in range(100)})) <= 33


def test_intentional_pytest_failure_report_contains_only_safe_snapshot(tmp_path):
    """Run an expected child failure and inspect its real stdout/stderr report."""
    test_file = tmp_path / "test_snapshot_failure.py"
    test_file.write_text(
        "import json, os, pytest\n"
        "from clip_test_fixtures import redact_snapshot\n"
        "def test_expected_snapshot_failure():\n"
        "    payload = json.loads(os.environ['SYNTHETIC_PRIVACY_PAYLOAD'])\n"
        "    pytest.fail(json.dumps(redact_snapshot(payload)), pytrace=False)\n"
    )
    root = Path(__file__).resolve().parents[3]
    payload = {
        "status": 503,
        "error": {"code": "dependency_unavailable"},
        "contacts": {"email": SENTINEL, "phone": SENTINEL, "upi_id": SENTINEL},
        "token": SENTINEL,
        "message_ciphertext": SENTINEL,
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(root / "pyproject.toml"),
            "--noconftest",
            "-q",
            "-W",
            "error",
            str(test_file),
        ],
        cwd=root,
        env={
            "PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "SYNTHETIC_PRIVACY_PAYLOAD": json.dumps(payload),
        },
        capture_output=True,
        text=True,
        timeout=15,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert "1 failed" in output
    assert "[REDACTED]" in output
    assert "dependency_unavailable" in output and "503" in output
    assert SENTINEL not in output
