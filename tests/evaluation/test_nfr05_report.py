"""Synthetic NFR-05 arithmetic and strict-input checks; no messages are sent."""

from copy import deepcopy
import json
import subprocess
import sys

import pytest

from scripts.evaluation.nfr05_report import DEADLINE_NS, summarize


def samples():
    return [
        {
            "index": i,
            "outcome": "displayed",
            "submitted_ns": 10,
            "displayed_ns": 10 + DEADLINE_NS,
        }
        for i in range(60)
    ]


def test_boundary_failures_and_missing_outcomes_stay_in_denominator():
    data = samples()
    data[0]["displayed_ns"] += 1
    data[1].update(outcome="failed", submitted_ns=None, displayed_ns=None)
    data[2].update(outcome="undisplayed", displayed_ns=None)
    result = summarize({"samples": data})
    assert result["visible_on_time"] == 57
    assert result["threshold_met_if_valid"] is True
    assert result["nfr_accepted"] is False
    assert summarize({"samples": data[:-1]})["threshold_met_if_valid"] is False
    data[3].update(outcome="undisplayed", displayed_ns=None)
    assert summarize({"samples": data})["threshold_met_if_valid"] is False


def test_refuses_duplicates_invalid_clock_and_private_fields():
    good = samples()
    for mutation in ("duplicate", "clock", "private", "boolean"):
        data = deepcopy(good)
        if mutation == "duplicate":
            data[1]["index"] = 0
        elif mutation == "clock":
            data[0]["displayed_ns"] = 9
        elif mutation == "private":
            data[0]["message"] = "synthetic"
        else:
            data[0]["submitted_ns"] = True
        with pytest.raises(ValueError):
            summarize({"samples": data})


def test_cli_reports_only_aggregate_and_rejects_unsafe_input(tmp_path):
    path = tmp_path / "samples.json"
    path.write_text(json.dumps({"samples": samples()}))
    command = [sys.executable, "-m", "scripts.evaluation.nfr05_report", str(path)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert json.loads(result.stdout)["threshold_met_if_valid"] is True
    assert "submitted_ns" not in result.stdout
    path.write_text('{"samples":[],"message":"private"}')
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "private" not in result.stderr
