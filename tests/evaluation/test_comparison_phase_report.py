"""Offline fixtures verify phase pairing, accounting and immutable inputs."""

import json
import subprocess
import sys

from scripts.evaluation.k6.comparison_phase_report import preview


def record(outcome, blocked=0, duration=0, connecting=0, tls=0):
    return {
        "outcome": outcome,
        "timings": {
            "blocked": blocked,
            "duration": duration,
            "connecting": connecting,
            "tls_handshaking": tls,
        },
    }


def test_same_response_sums_and_failures_remain_visible():
    report = preview(
        [
            record("correct", 100, 1, 40, 30),
            record("correct", 1, 100),
            record("timeout"),
            record("transport_error"),
        ]
    )
    assert report["correct_approximate_span_ms"]["p95_ms"] == 101
    assert report["correct_phase_ms"]["duration"]["p95_ms"] != 101
    assert report["correct_phase_ms"]["connecting"]["samples"] == 2
    assert report["failure_outcomes"] == {"timeout": 1, "transport_error": 1}
    assert report["timing_verified"] is False
    assert report["nfr_accepted"] is False


def test_suspicious_correct_observation_suppresses_all_percentiles():
    report = preview([record("correct", 1, 2), record("correct", 1, 5000)])
    assert report["anomalies"] == {"over_timeout_warning": 1}
    assert report["correct_records"] == 2
    assert report["correct_approximate_span_ms"] is None
    assert report["correct_phase_ms"] is None
    assert not report["percentiles_available"]


def test_missing_and_negative_phases_are_visible():
    missing = record("correct")
    del missing["timings"]["connecting"]
    report = preview([missing, record("correct", -1, 20), record("incorrect")])
    assert report["anomalies"] == {"missing_or_unknown_phase": 1, "invalid_phase": 1}
    assert report["failure_outcomes"] == {"incorrect": 1}
    assert report["correct_approximate_span_ms"] is None


def test_cli_keeps_fixture_and_existing_report_unchanged(tmp_path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps([record("correct", 10, 30)]))
    before = fixture.read_bytes()
    output = tmp_path / "report-v1.json"
    cmd = [
        sys.executable,
        "-m",
        "scripts.evaluation.k6.comparison_phase_report",
        str(fixture),
        "--output",
        str(output),
    ]
    assert subprocess.run(cmd, capture_output=True, check=False).returncode == 0
    original = output.read_bytes()
    assert subprocess.run(cmd, capture_output=True, check=False).returncode == 2
    assert fixture.read_bytes() == before
    assert output.read_bytes() == original
