"""Prepare one checked comparison workload profile offline, without running it."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
from typing import Any

from scripts.evaluation.k6.comparison_binding_preflight import MAX_INPUT_BYTES
from scripts.evaluation.k6.comparison_pair_plan import (
    MAX_INPUT_BYTES as PAIR_MAX_INPUT_BYTES,
    validate_pair_plan,
)
from scripts.evaluation.k6.comparison_run_preflight import (
    validate_generator_capacity,
    validate_run_inputs,
)


def build_profile(
    binding_plan: Any,
    corpus_bytes: bytes,
    ordered_reference: Any,
    paired_plan: Any,
    cycle: int,
    pre_allocated_vus: int,
    max_vus: int,
    *,
    parity_draft: bool = False,
) -> bytes:
    """Build deterministic profile bytes only after the existing checks pass."""
    if type(cycle) is not int or cycle not in (1, 2, 3):
        raise ValueError("invalid_cycle")
    validate_generator_capacity(
        {"preAllocatedVUs": pre_allocated_vus, "maxVUs": max_vus}
    )
    if len(corpus_bytes) > MAX_INPUT_BYTES:
        raise ValueError("corpus_too_large")
    if validate_pair_plan(paired_plan)["state"] != "planned":
        raise ValueError("complete_paired_plan_required")
    corpus = json.loads(corpus_bytes)
    if not isinstance(corpus, dict) or not isinstance(corpus.get("cases"), list):
        raise ValueError("invalid_case_corpus")
    starts = {
        pair["condition"]: pair["sequence_start"]
        for pair in paired_plan["cycles"][cycle - 1]["pairs"]
    }
    profile = {
        "cases": corpus["cases"],
        "sequence_starts": starts,
        "capacity": {"preAllocatedVUs": pre_allocated_vus, "maxVUs": max_vus},
        "timeout_seconds": 5,
    }
    # The existing preflight verifies the archive, reference, source, corpus,
    # paired plan, and this profile before any output file is created.
    validate_run_inputs(
        binding_plan,
        corpus_bytes,
        ordered_reference,
        paired_plan,
        profile,
        cycle,
        allow_parity_draft=parity_draft,
    )
    content = (
        json.dumps(profile, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")
    if len(content) > MAX_INPUT_BYTES:
        raise ValueError("profile_too_large")
    return content


def _read_bounded(path: Path, limit: int) -> bytes:
    """Read at most the allowed bytes from a regular local file."""
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("input_must_be_regular_file")
    with path.open("rb") as source:
        content = source.read(limit + 1)
    if len(content) > limit:
        raise ValueError("input_too_large")
    return content


def main() -> None:
    """Create one new profile; repeat for the three cycles with reviewed inputs."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("binding_plan", type=Path)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("ordered_reference", type=Path)
    parser.add_argument("paired_plan", type=Path)
    parser.add_argument("--cycle", required=True, type=int)
    parser.add_argument("--pre-allocated-vus", required=True, type=int)
    parser.add_argument("--max-vus", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--parity-draft", action="store_true")
    args = parser.parse_args()
    try:
        binding_plan = json.loads(_read_bounded(args.binding_plan, MAX_INPUT_BYTES))
        corpus_bytes = _read_bounded(args.corpus, MAX_INPUT_BYTES)
        reference = json.loads(_read_bounded(args.ordered_reference, MAX_INPUT_BYTES))
        paired_plan = json.loads(_read_bounded(args.paired_plan, PAIR_MAX_INPUT_BYTES))
        content = build_profile(
            binding_plan,
            corpus_bytes,
            reference,
            paired_plan,
            args.cycle,
            args.pre_allocated_vus,
            args.max_vus,
            parity_draft=args.parity_draft,
        )
        # Exclusive creation preserves any existing user file, including symlinks.
        with args.output.open("xb") as output:
            output.write(content)
        print(
            json.dumps(
                {
                    "profile_created": True,
                    "cycle": args.cycle,
                    "profile_sha256": hashlib.sha256(content).hexdigest(),
                    "measurement_authorized": False,
                    "parity_draft": args.parity_draft,
                },
                sort_keys=True,
            )
        )
    except OSError, ValueError, TypeError, KeyError, RecursionError:
        parser.exit(
            2, "Comparison profile preparation failed; no workload was started\n"
        )


if __name__ == "__main__":
    main()
