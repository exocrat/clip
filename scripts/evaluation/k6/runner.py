"""SE-01 local-only k6 execution/reporting; never NFR acceptance or cloud traffic.

Profiles for future NFR runs can be inspected, but this entry point only executes
bounded loopback pilots. Auth/final-dataset/deployment manifests remain real gates.
"""

import argparse
from collections import Counter
from datetime import datetime, UTC
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

from scripts.evaluation.k6.install import BINARY, ROOT, VERSION


def quantile(values: list[float], probability: float) -> float | None:
    """R7 linear interpolation over actual samples; never average per-run quantiles."""
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    low = math.floor(index)
    high = math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def cohort(points: list[dict], phase: str, expected: int, duration: float) -> dict:
    """Preserve issued, completed, actual HTTP, drops/failures and both denominators."""
    issued = 0
    http = 0
    drops = 0
    bad_clock = 0
    outside_cohort = 0
    samples = []
    for point in points:
        if point.get("type") != "Point":
            continue
        data = point["data"]
        tags = data.get("tags") or {}
        if tags.get("phase", tags.get("scenario")) != phase:
            continue
        metric = point["metric"]
        value = data["value"]
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError("Invalid metric value")
        if metric == "clip_outside_cohort":
            outside_cohort += int(value)
        elif metric == "clip_issued":
            issued += int(value)
        elif metric == "http_reqs":
            http += int(value)
        elif metric == "dropped_iterations":
            drops += int(value)
        elif metric == "clip_clock_invalid":
            bad_clock += int(value)
        elif metric == "clip_elapsed_ms":
            samples.append((float(value), tags.get("outcome"), tags.get("case_id")))
    outcomes = Counter(outcome for _, outcome, _ in samples)
    success = [value for value, outcome, _ in samples if outcome == "ok"]
    timed_success = sum(1 for value in success if value <= 1000)

    def stats(values):
        return {
            "samples": len(values),
            "p50_ms": quantile(values, 0.5),
            "p95_ms": quantile(values, 0.95),
            "p99_ms": quantile(values, 0.99),
        }

    return {
        "scheduled": expected,
        "issued": issued,
        "actual_http_requests": http,
        "completed_samples": len(samples),
        "uncompleted": max(0, issued - len(samples)),
        "generator_drops": drops,
        "boundary_iterations_without_http": outside_cohort,
        "generator_shortfall": max(0, expected - issued),
        "outcomes": dict(outcomes),
        "clock_invalid": bad_clock,
        "offered_rps": expected / duration if duration else 0,
        "issued_rps": issued / duration if duration else 0,
        "successful_rps": len(success) / duration if duration else 0,
        "all_completed_latency": stats([value for value, _, _ in samples]),
        "successful_latency": stats(success),
        "expected_result_within_1s": timed_success,
        "within_1s_fraction_of_correct": (
            timed_success / len(success) if success else None
        ),
        "within_1s_fraction_of_issued": timed_success / issued if issued else None,
        "case_outcomes": {
            case: dict(Counter(outcome for _, outcome, name in samples if name == case))
            for case in sorted({name for _, _, name in samples})
        },
        "valid": issued == expected == http == len(samples)
        and drops == 0
        and bad_clock == 0
        and len(success) == issued
        and issued > 0,
    }


def summarize(raw: Path, profile: dict, finished: bool, exit_code: int) -> dict:
    """Local preparation result is valid only with a complete, correctly delivered workload."""
    if raw.exists() and raw.stat().st_size > 5_000_000:
        raise ValueError("Pilot metric file exceeds cap")
    points = (
        [json.loads(line) for line in raw.read_text().splitlines()]
        if raw.exists()
        else []
    )
    measured = cohort(
        points,
        "measured",
        profile["rate"] * profile["measured_seconds"],
        profile["measured_seconds"],
    )
    warmup = cohort(
        points,
        "warmup",
        profile["rate"] * profile["warmup_seconds"],
        profile["warmup_seconds"],
    )
    return {
        "preview_only": True,
        "nfr_accepted": False,
        "latency_timing_verified": False,
        "finished": finished,
        "k6_exit": exit_code,
        "profile_id": profile["id"],
        "measured": measured,
        "warmup": warmup,
        "valid_preparation_run": finished
        and exit_code == 0
        and measured["valid"]
        and (not profile["warmup_seconds"] or warmup["valid"]),
        "latency_boundary": "Date.now around one synchronous HTTP call through full response body; negative elapsed clock samples invalidate run",
        "quantile_method": "R7 linear interpolation",
        "throughput_boundary": "arrival cohort completions / scheduled cohort seconds; bounded completion drain retained",
        "acceptance": "No local/stub result accepts SE-CORE, DATA-READY or NFRs",
    }


def execute(
    profile_path: Path, port: int, destination: Path, *, target_kind: str
) -> dict:
    """Execute one fresh loopback pilot with a clean child environment and raw metrics.

    Caller supplies only an unused ignored evidence directory. Future full-rate
    profiles are refused. Normal external targets/auth/config are never inferred.
    """
    if profile_path.stat().st_size > 65536:
        raise ValueError("Profile exceeds cap")
    profile = json.loads(profile_path.read_text())
    if (
        profile.get("purpose") != "local-pilot"
        or not 1 <= profile.get("rate", 0) <= 2
        or not 0 <= profile.get("warmup_seconds", -1) <= 5
        or not 1 <= profile.get("measured_seconds", 0) <= 10
        or not 1 <= profile.get("max_vus", 0) <= 2
        or not 0 < profile.get("timeout_seconds", 0) <= 3
    ):
        raise ValueError("Only capped local pilot profiles can run")
    if (
        type(port) is not int
        or not 1024 <= port <= 65535
        or target_kind not in {"native", "fault-fixtures"}
    ):
        raise ValueError("Invalid local target")
    local = ROOT / ".tools"
    if any(
        path.is_symlink() for path in [destination, *destination.absolute().parents]
    ):
        raise ValueError("Symlink output forbidden")
    destination = destination.resolve()
    if not destination.is_relative_to(local) or any(
        path.is_symlink() for path in [destination, *destination.parents]
    ):
        raise ValueError("Use a new repository-local ignored run directory")
    destination.mkdir(parents=True, exist_ok=False)
    report = json.loads((ROOT / ".tools/k6/install.json").read_text())
    if (
        hashlib.sha256(BINARY.read_bytes()).hexdigest() != report["binary_sha256"]
        or report["version"] != VERSION
    ):
        raise ValueError("Pinned binary mismatch")
    frozen = destination / "profile.json"
    frozen.write_text(json.dumps(profile, indent=2) + "\n")
    (destination / "config.json").write_text("{}\n")
    manifest = {
        "utc": datetime.now(UTC).isoformat(),
        "profile": profile,
        "profile_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in [
                "scripts/evaluation/k6/load.js",
                "scripts/evaluation/k6/core.js",
                "scripts/evaluation/k6/runner.py",
            ]
        },
        "tool": report,
        "target": f"http://127.0.0.1:{port}",
        "target_kind": target_kind,
        "preview_only": True,
        "nfr_accepted": False,
        "approval_scope": "Mohit verified bounded local-only Step10 preparation; no cloud/final NFR approval",
        "auth": "explicit isolated synthetic caller/header only; real Identity pending",
        "request_cap": profile["rate"]
        * (profile["warmup_seconds"] + profile["measured_seconds"]),
        "max_simultaneous_requests": profile["max_vus"],
        "warmup_and_measure_overlap": False,
        "drain_seconds_each": profile["timeout_seconds"],
        "spend": "local only, no cloud/provider calls",
        "remaining": "real auth/data/images/labels/deployed target/telemetry/resource/cost/repetition/final acceptance manifests",
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    environment = {
        "PATH": "/usr/bin:/bin",
        "K6_NO_USAGE_REPORT": "true",
        "CLIP_LOAD_ISOLATED": "true",
        "CLIP_LOAD_TARGET_KIND": target_kind,
        "CLIP_LOAD_PROFILE": str(frozen),
        "CLIP_LOAD_TARGET": manifest["target"],
        "CLIP_LOAD_FINISHED": str(destination / "finished.json"),
    }
    command = [
        str(BINARY),
        "run",
        "--quiet",
        "--no-color",
        "--no-usage-report",
        "--address",
        "",
        "--config",
        str(destination / "config.json"),
        "--out",
        f"json={destination/'raw.ndjson'}",
        str(ROOT / "scripts/evaluation/k6/load.js"),
    ]
    with (destination / "k6.log").open("wb") as log:
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                stdout=log,
                stderr=log,
                timeout=profile["warmup_seconds"]
                + profile["measured_seconds"]
                + 2 * profile["timeout_seconds"]
                + 10,
            )
            code = completed.returncode
        except subprocess.TimeoutExpired:
            code = 124
    result = summarize(
        destination / "raw.ndjson",
        profile,
        (destination / "finished.json").exists(),
        code,
    )
    result["target_kind"] = target_kind
    (destination / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    """Accept only one fixed loopback target and local output/profile files."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--isolated-local-pilot", action="store_true")
    args = parser.parse_args()
    if not args.isolated_local_pilot:
        parser.error("Explicit isolated local pilot opt-in required")
    try:
        result = execute(args.profile, args.port, args.output, target_kind="native")
    except OSError, ValueError, KeyError:
        parser.exit(2, "Local load preparation refused\n")
    print(json.dumps(result))
    raise SystemExit(0 if result["valid_preparation_run"] else 2)


if __name__ == "__main__":
    main()
