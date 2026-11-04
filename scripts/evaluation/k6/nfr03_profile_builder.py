"""Build an isolated NFR-03 mixed read/write profile from frozen cases.

The fixture binding only supplies existing IDs for read checks; it cannot
authorize execution, account creation, deletion or a live target.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from uuid import UUID

from scripts.evaluation.k6.prepare_comparison_corpus import FINGERPRINT, build_corpus


def build_profile(
    run_id: str, configuration: str, fixture: Any, pre_allocated_vus: int, max_vus: int
) -> dict[str, Any]:
    """Bind deterministic cases/fixtures; staged schedule code fixes smooth ordering.

    nfr03_schedule.js preserves the reviewed counts and is hash-bound by the
    real coordinator. No outcome-dependent ordering or weakened load is allowed.
    """
    if configuration not in {"A", "B"} or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}", run_id
    ):
        raise ValueError("invalid_run_identity")
    if (
        type(pre_allocated_vus) is not int
        or type(max_vus) is not int
        or not 1 <= pre_allocated_vus <= max_vus <= 500
    ):
        raise ValueError("invalid_vu_capacity")
    if (
        not isinstance(fixture, dict)
        or set(fixture)
        != {
            "dataset_fingerprint",
            "wanted_request_id",
            "conversation_id",
            "saved_listing_ids",
            "category_code",
        }
        or fixture["dataset_fingerprint"] != FINGERPRINT
    ):
        raise ValueError("invalid_fixture_binding")
    try:
        UUID(fixture["wanted_request_id"])
        UUID(fixture["conversation_id"])
        saved = fixture["saved_listing_ids"]
        if (
            not isinstance(saved, list)
            or len(saved) < 5
            or len(set(saved)) != len(saved)
        ):
            raise ValueError
        for item in saved:
            UUID(item)
    except ValueError, TypeError, AttributeError:
        raise ValueError("invalid_fixture_binding") from None
    if not isinstance(fixture["category_code"], str) or not re.fullmatch(
        r"[a-z][a-z0-9_]{1,39}", fixture["category_code"]
    ):
        raise ValueError("invalid_fixture_binding")
    corpus = build_corpus()
    browse = [case for case in corpus["cases"] if case["request"]["kind"] == "browse"]
    search = [case for case in corpus["cases"] if case["request"]["kind"] == "search"]
    details = [case for case in corpus["cases"] if case["request"]["kind"] == "detail"]
    if len(browse) != 5 or len(search) != 3 or len(details) != 2:
        raise ValueError("frozen_case_mix_changed")
    cases = {
        "browse": [
            {"request": row["request"], "expected": row["expected"]} for row in browse
        ],
        "search": [{"request": row["request"]} for row in search],
        "detail": [
            {"request": row["request"], "expected": row["expected"]} for row in details
        ],
        "wanted_request_id": fixture["wanted_request_id"],
        "conversation_id": fixture["conversation_id"],
        "saved_listing_ids": fixture["saved_listing_ids"],
        "category_code": fixture["category_code"],
    }
    digest = hashlib.sha256(
        json.dumps(
            cases, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    return {
        "version": 1,
        "purpose": "nfr-local-preparation",
        "nfr_id": "nfr-03",
        "configuration": configuration,
        "run_id": run_id,
        "dataset_fingerprint": FINGERPRINT,
        "fixture_binding_sha256": hashlib.sha256(
            json.dumps(fixture, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "case_bundle_sha256": digest,
        "rate_rps": 50,
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
    parser.add_argument("configuration", choices=("A", "B"))
    parser.add_argument("run_id")
    parser.add_argument("fixture_binding", type=Path)
    parser.add_argument("--pre-allocated-vus", type=int, required=True)
    parser.add_argument("--max-vus", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.fixture_binding.stat().st_size > 65_536:
            raise ValueError("fixture_binding_too_large")
        fixture = json.loads(args.fixture_binding.read_text(encoding="utf-8"))
        profile = build_profile(
            args.run_id,
            args.configuration,
            fixture,
            args.pre_allocated_vus,
            args.max_vus,
        )
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(profile, output, ensure_ascii=False, sort_keys=True, indent=2)
            output.write("\n")
    except OSError, ValueError, KeyError, TypeError:
        parser.exit(2, "NFR-03 profile build failed; no workload was started\n")


if __name__ == "__main__":
    main()
