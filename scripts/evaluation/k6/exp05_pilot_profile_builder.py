"""Build one 60-second warm-up / two-minute EXP-05 pilot profile offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}\Z")


def build_profile(
    base_profile: Any,
    run_id: str,
    configuration: str,
    pre_allocated_vus: int,
    max_vus: int,
    dataset_fingerprint: str,
) -> dict[str, Any]:
    """Reuse the reviewed ten-case comparison mix with the fixed pilot window."""
    if not isinstance(base_profile, dict) or set(base_profile) != {
        "cases",
        "sequence_starts",
        "capacity",
        "timeout_seconds",
    }:
        raise ValueError("reviewed_comparison_profile_required")
    cases = base_profile["cases"]
    starts = base_profile["sequence_starts"]
    if (
        not isinstance(cases, list)
        or len(cases) != 10
        or not isinstance(starts, dict)
        or set(starts) != {"low", "normal", "burst"}
        or type(starts["burst"]) is not int
        or starts["burst"] not in range(10)
        or not isinstance(base_profile["capacity"], dict)
        or type(base_profile["timeout_seconds"]) is not int
        or base_profile["timeout_seconds"] != 5
    ):
        raise ValueError("invalid_reviewed_comparison_profile")
    counts = {kind: 0 for kind in ("browse", "search", "detail")}
    for case in cases:
        if (
            not isinstance(case, dict)
            or not isinstance(case.get("request"), dict)
            or case["request"].get("kind") not in counts
        ):
            raise ValueError("invalid_pilot_case")
        counts[case["request"]["kind"]] += 1
    if counts != {"browse": 5, "search": 3, "detail": 2}:
        raise ValueError("invalid_pilot_case_mix")
    if not RUN_ID.fullmatch(run_id) or configuration not in {"A", "B"}:
        raise ValueError("invalid_pilot_run_binding")
    dataset_fingerprint = (
        dataset_fingerprint.removeprefix("sha256:")
        if isinstance(dataset_fingerprint, str)
        else ""
    )
    if not re.fullmatch(r"[0-9a-f]{64}", dataset_fingerprint):
        raise ValueError("invalid_pilot_dataset_fingerprint")
    if (
        type(pre_allocated_vus) is not int
        or type(max_vus) is not int
        or pre_allocated_vus < 1
        or max_vus < pre_allocated_vus
    ):
        raise ValueError("invalid_pilot_capacity")
    workload = {
        "dataset_fingerprint": dataset_fingerprint,
        "cases": cases,
        "sequence_start": starts["burst"],
        "rate_rps": 50,
        "warmup_rate_rps": 10,
        "warmup_seconds": 60,
        "measured_seconds": 120,
        "timeout_seconds": 5,
        "retries": 0,
        "capacity": {"preAllocatedVUs": pre_allocated_vus, "maxVUs": max_vus},
    }
    return {
        "version": 1,
        "purpose": "exp05-pilot-workload",
        "run_id": run_id,
        "configuration": configuration,
        "dataset_fingerprint": dataset_fingerprint,
        "case_bundle_sha256": hashlib.sha256(_canonical(cases)).hexdigest(),
        "workload_sha256": hashlib.sha256(_canonical(workload)).hexdigest(),
        "condition": "burst",
        "rate_rps": 50,
        "warmup_rate_rps": 10,
        "warmup_seconds": 60,
        "measured_seconds": 120,
        "drain_seconds": 5,
        "timeout_seconds": 5,
        "retries": 0,
        "sequence_start": starts["burst"],
        "capacity": {"preAllocatedVUs": pre_allocated_vus, "maxVUs": max_vus},
        "conditions": [{"name": "burst", "warmup_rate": 10, "measured_rate": 50}],
        "cases": cases,
        "execution_permitted": False,
        "nfr_accepted": False,
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def main() -> None:
    """Write one new profile for the named pilot run; never starts k6."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("base_profile", type=Path)
    parser.add_argument("run_id")
    parser.add_argument("configuration", choices=("A", "B"))
    parser.add_argument("--pre-allocated-vus", required=True, type=int)
    parser.add_argument("--max-vus", required=True, type=int)
    parser.add_argument("--dataset-fingerprint", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.base_profile.stat().st_size > 10_000_000:
            raise ValueError("base_profile_too_large")
        base = json.loads(args.base_profile.read_text(encoding="utf-8"))
        profile = build_profile(
            base,
            args.run_id,
            args.configuration,
            args.pre_allocated_vus,
            args.max_vus,
            args.dataset_fingerprint,
        )
        raw = (
            json.dumps(
                profile, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False
            ).encode()
            + b"\n"
        )
        with args.output.open("xb") as output:
            output.write(raw)
        print(
            json.dumps(
                {
                    "run_id": args.run_id,
                    "configuration": args.configuration,
                    "workload_sha256": profile["workload_sha256"],
                    "profile_sha256": hashlib.sha256(raw).hexdigest(),
                    "execution_permitted": False,
                },
                sort_keys=True,
            )
        )
    except OSError, ValueError, TypeError, KeyError, json.JSONDecodeError:
        parser.exit(
            2, "EXP-05 pilot profile preparation failed; no workload was started\n"
        )


if __name__ == "__main__":
    main()
