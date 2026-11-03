"""Create a new loopback-only NFR-01/02 profile from repository-bound cases.

This builder fills synthetic preparation inputs only. Its output explicitly
disallows deployed execution and NFR acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from scripts.evaluation.k6.prepare_nfr_cases import build_nfr_drafts
from scripts.evaluation.k6.prepare_comparison_corpus import FINGERPRINT


def build_profile(
    nfr_id: str,
    configuration: str,
    run_id: str,
    pre_allocated_vus: int,
    max_vus: int,
) -> dict[str, Any]:
    """Build a case-complete profile without changing execution authority."""
    if nfr_id not in {"nfr-01", "nfr-02"} or configuration not in {"A", "B"}:
        raise ValueError("invalid_nfr_or_configuration")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}", run_id):
        raise ValueError("invalid_run_id")
    if (
        type(pre_allocated_vus) is not int
        or type(max_vus) is not int
        or not 1 <= pre_allocated_vus <= max_vus <= 500
    ):
        raise ValueError("invalid_vu_capacity")
    drafts = build_nfr_drafts()
    raw_cases = drafts["nfr_01" if nfr_id == "nfr-01" else "nfr_02"]
    cases = []
    for item in raw_cases:
        cases.append(
            {
                "case_id": item["case_id"],
                "request": item["request"],
                "expected_status": 200,
                "expected": item["expected"] if nfr_id == "nfr-01" else None,
                "query_class": (
                    item["relevance_reference"]["query_class"]
                    if nfr_id == "nfr-02"
                    else None
                ),
            }
        )
    bundle_hash = hashlib.sha256(
        json.dumps(
            cases, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    return {
        "version": 1,
        "purpose": "nfr-local-preparation",
        "nfr_id": nfr_id,
        "configuration": configuration,
        "run_id": run_id,
        "dataset_fingerprint": FINGERPRINT,
        "case_bundle_sha256": bundle_hash,
        "rate_rps": 20 if nfr_id == "nfr-01" else 10,
        "warmup_seconds": 60,
        "measured_seconds": 300,
        "drain_seconds": 5,
        "timeout_seconds": 5,
        "retries": 0,
        "capacity": {"preAllocatedVUs": pre_allocated_vus, "maxVUs": max_vus},
        "cases": cases,
        "execution_permitted": False,
        "nfr_accepted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("nfr_id", choices=("nfr-01", "nfr-02"))
    parser.add_argument("configuration", choices=("A", "B"))
    parser.add_argument("run_id")
    parser.add_argument("--pre-allocated-vus", type=int, required=True)
    parser.add_argument("--max-vus", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        profile = build_profile(
            args.nfr_id,
            args.configuration,
            args.run_id,
            args.pre_allocated_vus,
            args.max_vus,
        )
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(profile, output, sort_keys=True, indent=2, ensure_ascii=False)
            output.write("\n")
    except OSError, ValueError, KeyError, TypeError:
        parser.exit(2, "NFR local profile build failed; no workload was started\n")


if __name__ == "__main__":
    main()
