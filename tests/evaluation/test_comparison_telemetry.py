"""Validate telemetry bindings and explicit saturation/clock limitations."""

from copy import deepcopy
import subprocess
import sys

import pytest

from scripts.evaluation.k6.comparison_telemetry import validate_telemetry
from scripts.evaluation.k6.comparison_manifest import TEMPLATE


@pytest.fixture
def records():
    """Supply local synthetic metadata; no telemetry or provider data is read."""
    names = ("ecs", "lambda", "postgres", "generator")
    manifest = {
        "manifest_state": "captured",
        "run": {
            "run_id": "synthetic-A-1",
            "actual_start_utc": "2026-11-01T10:00:00Z",
            "actual_end_utc": "2026-11-01T10:06:00Z",
        },
        "resource_telemetry": {
            f"{name}_artifact_{field}": (
                f"evidence/{name}.json" if field == "reference" else "a" * 64
            )
            for name in names
            for field in ("reference", "sha256")
        },
    }
    evidence = {
        "format_version": 1,
        "run_id": "synthetic-A-1",
        "clock": {
            "source": "synthetic monotonic fixture",
            "monotonic_verified": False,
            "evidence_reference": "evidence/clock.json",
        },
        "generator": {
            "peak_cpu_percent": 65,
            "approved_cpu_limit_percent": 80,
            "peak_rss_bytes": 1000,
            "approved_rss_limit_bytes": 2000,
            "peak_vus": 3,
            "approved_max_vus": 5,
            "dropped_iterations": 0,
        },
        "artifacts": {
            name: {
                "reference": f"evidence/{name}.json",
                "sha256": "a" * 64,
                "window_start_utc": "2026-11-01T09:59:00Z",
                "window_end_utc": "2026-11-01T10:07:00Z",
            }
            for name in names
        },
    }
    return manifest, evidence


def test_valid_metadata_never_claims_clock_or_artifacts_are_verified(records):
    manifest, evidence = records
    result = validate_telemetry(evidence, manifest)
    assert result["metadata_valid"] is True
    assert result["measurement_authorized"] is False
    assert result["artifact_contents_or_hashes_verified"] is False
    assert result["monotonic_clock_independently_verified"] is False
    assert result["monotonic_clock_declared_verified"] is False
    assert all(result["generator_checks"].values())


def test_generator_saturation_and_drops_are_visible(records):
    manifest, evidence = records
    evidence["generator"].update(
        peak_cpu_percent=95,
        peak_rss_bytes=2001,
        peak_vus=5,
        dropped_iterations=1,
    )
    checks = validate_telemetry(evidence, manifest)["generator_checks"]
    assert checks == {
        "cpu_within_supplied_limit": False,
        "rss_within_supplied_limit": False,
        "vus_within_supplied_limit": True,
        "vu_headroom_observed": False,
        "no_dropped_iterations": False,
    }


def test_clock_declaration_never_substitutes_for_independent_verification(records):
    manifest, evidence = records
    evidence["clock"]["monotonic_verified"] = True
    result = validate_telemetry(evidence, manifest)
    assert result["monotonic_clock_declared_verified"] is True
    assert result["monotonic_clock_independently_verified"] is False
    assert result["measurement_authorized"] is False


def test_cli_refuses_unfilled_manifest_and_telemetry_templates():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.evaluation.k6.comparison_telemetry",
            str(TEMPLATE),
            "data/evaluation/workloads/ecs-lambda-telemetry.template.json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (lambda e: e.update(run_id="other"), "run binding mismatch"),
        (lambda e: e["artifacts"].pop("lambda"), "Invalid artifacts shape"),
        (
            lambda e: e["artifacts"]["ecs"].update(sha256="b" * 64),
            "artifact binding mismatch",
        ),
        (
            lambda e: e["artifacts"]["postgres"].update(
                window_end_utc="2026-11-01T10:05:59Z"
            ),
            "window does not cover run",
        ),
        (
            lambda e: e["clock"].update(evidence_reference="../secret"),
            "Invalid clock declaration",
        ),
        (
            lambda e: e["clock"].update(source="Bearer private-value"),
            "Invalid clock declaration",
        ),
        (
            lambda e: e["generator"].update(approved_cpu_limit_percent=0),
            "limit must be positive",
        ),
        (lambda e: e["generator"].update(peak_vus=True), "Invalid generator peak_vus"),
    ],
)
def test_rejects_missing_mismatched_or_unsafe_metadata(records, mutate, error):
    manifest, evidence = records
    evidence = deepcopy(evidence)
    mutate(evidence)
    with pytest.raises(ValueError, match=error):
        validate_telemetry(evidence, manifest)
