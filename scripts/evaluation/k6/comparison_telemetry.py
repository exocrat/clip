"""Validate offline telemetry metadata against a captured comparison manifest.

This reads two local JSON files only. It checks declared coverage and operator
limits; it does not read provider data, attest artifact hashes, prove a clock is
monotonic, or authorize a measurement.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

from scripts.evaluation.k6.comparison_manifest import (
    SENSITIVE_VALUE,
    TEMPLATE,
    _utc,
    validate_manifest,
)

SHA256 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
ARTIFACT_NAMES = ("ecs", "lambda", "postgres", "generator")


def _keys(value: object, expected: set[str], name: str) -> None:
    """Reject unknown or missing fields before interpreting an evidence record."""
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"Invalid {name} shape")


def _reference(value: object) -> bool:
    """Allow only bounded local evidence references without URL/query contents."""
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value) <= 240
        and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", value))
        and ".." not in Path(value).parts
        and not SENSITIVE_VALUE.search(value)
    )


def _number(value: object, name: str, *, maximum: float | None = None) -> float:
    """Accept finite nonnegative measurements, never bools or implied limits."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or maximum is not None
        and value > maximum
    ):
        raise ValueError(f"Invalid {name}")
    return float(value)


def validate_telemetry(evidence: object, manifest: dict) -> dict:
    """Check run binding, capture windows, and supplied generator limits.

    The caller must separately validate the full captured manifest. A success
    result is metadata validation only, not an evidence audit or NFR result.
    """
    _keys(
        evidence,
        {"format_version", "run_id", "clock", "generator", "artifacts"},
        "telemetry",
    )
    if type(evidence["format_version"]) is not int or evidence["format_version"] != 1:
        raise ValueError("Unsupported telemetry format")
    if (
        manifest.get("manifest_state") != "captured"
        or evidence["run_id"] != manifest["run"]["run_id"]
    ):
        raise ValueError("Telemetry run binding mismatch")
    start = _utc(manifest["run"]["actual_start_utc"], "run start")
    end = _utc(manifest["run"]["actual_end_utc"], "run end")
    if end <= start:
        raise ValueError("Invalid run interval")

    clock = evidence["clock"]
    _keys(clock, {"source", "monotonic_verified", "evidence_reference"}, "clock")
    if (
        not isinstance(clock["source"], str)
        or not clock["source"].strip()
        or len(clock["source"]) > 120
        or any(ord(char) < 32 for char in clock["source"])
        or SENSITIVE_VALUE.search(clock["source"])
        or type(clock["monotonic_verified"]) is not bool
        or not _reference(clock["evidence_reference"])
    ):
        raise ValueError("Invalid clock declaration")

    generator = evidence["generator"]
    _keys(
        generator,
        {
            "peak_cpu_percent",
            "approved_cpu_limit_percent",
            "peak_rss_bytes",
            "approved_rss_limit_bytes",
            "peak_vus",
            "approved_max_vus",
            "dropped_iterations",
        },
        "generator",
    )
    cpu = _number(generator["peak_cpu_percent"], "peak CPU", maximum=100)
    cpu_limit = _number(
        generator["approved_cpu_limit_percent"], "approved CPU limit", maximum=100
    )
    if cpu_limit <= 0:
        raise ValueError("Approved CPU limit must be positive")
    for key in (
        "peak_rss_bytes",
        "approved_rss_limit_bytes",
        "peak_vus",
        "approved_max_vus",
        "dropped_iterations",
    ):
        if type(generator[key]) is not int or generator[key] < 0:
            raise ValueError(f"Invalid generator {key}")
    if generator["approved_rss_limit_bytes"] < 1 or generator["approved_max_vus"] < 1:
        raise ValueError("Approved generator limits must be positive")

    artifacts = evidence["artifacts"]
    _keys(artifacts, set(ARTIFACT_NAMES), "artifacts")
    manifest_artifacts = manifest["resource_telemetry"]
    for name in ARTIFACT_NAMES:
        artifact = artifacts[name]
        _keys(
            artifact,
            {"reference", "sha256", "window_start_utc", "window_end_utc"},
            name,
        )
        if (
            not _reference(artifact["reference"])
            or not isinstance(artifact["sha256"], str)
            or not SHA256.fullmatch(artifact["sha256"])
            or artifact["reference"] != manifest_artifacts[f"{name}_artifact_reference"]
            or artifact["sha256"].removeprefix("sha256:")
            != manifest_artifacts[f"{name}_artifact_sha256"].removeprefix("sha256:")
        ):
            raise ValueError(f"{name} artifact binding mismatch")
        window_start = _utc(artifact["window_start_utc"], f"{name} window start")
        window_end = _utc(artifact["window_end_utc"], f"{name} window end")
        if window_start > start or window_end < end or window_end <= window_start:
            raise ValueError(f"{name} window does not cover run")

    return {
        "metadata_valid": True,
        "measurement_authorized": False,
        "artifact_contents_or_hashes_verified": False,
        "monotonic_clock_independently_verified": False,
        "monotonic_clock_declared_verified": clock["monotonic_verified"],
        "generator_checks": {
            "cpu_within_supplied_limit": cpu <= cpu_limit,
            "rss_within_supplied_limit": generator["peak_rss_bytes"]
            <= generator["approved_rss_limit_bytes"],
            "vus_within_supplied_limit": generator["peak_vus"]
            <= generator["approved_max_vus"],
            "vu_headroom_observed": generator["peak_vus"]
            < generator["approved_max_vus"],
            "no_dropped_iterations": generator["dropped_iterations"] == 0,
        },
    }


def main() -> int:
    """Validate local captured-manifest and telemetry metadata JSON files."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("telemetry", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        if validate_manifest(manifest, template)["state"] != "captured":
            raise ValueError("Captured manifest required")
        evidence = json.loads(args.telemetry.read_text(encoding="utf-8"))
        result = validate_telemetry(evidence, manifest)
    except OSError, ValueError, KeyError, TypeError:
        parser.exit(2, "Telemetry validation failed; no run was started\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
