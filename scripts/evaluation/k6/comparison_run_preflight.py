"""Cross-check prepared comparison inputs offline; never authorize a run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.evaluation.k6.comparison_binding_preflight import (
    MAX_INPUT_BYTES as BINDING_MAX_INPUT_BYTES,
    validate_bindings,
)
from scripts.evaluation.k6.comparison_pair_plan import (
    MAX_INPUT_BYTES as PAIR_MAX_INPUT_BYTES,
    validate_pair_plan,
)

MAX_INPUT_BYTES = max(BINDING_MAX_INPUT_BYTES, PAIR_MAX_INPUT_BYTES)


def _same_fingerprint(left: str, right: str) -> bool:
    """Compare SHA-256 values whether or not they carry the sha256 prefix."""
    return left.removeprefix("sha256:") == right.removeprefix("sha256:")


def validate_run_inputs(
    binding_plan: Any,
    corpus_bytes: bytes,
    ordered_reference: Any,
    paired_plan: Any,
) -> dict[str, Any]:
    """Check source/data/corpus bindings and the complete paired-run plan."""
    binding_result = validate_bindings(binding_plan, corpus_bytes, ordered_reference)
    pair_result = validate_pair_plan(paired_plan)
    if pair_result["state"] != "planned":
        raise ValueError("complete_paired_plan_required")

    shared = paired_plan["shared_inputs"]
    if not _same_fingerprint(
        shared["dataset_fingerprint"], binding_plan["dataset_fingerprint"]
    ):
        raise ValueError("paired_dataset_binding_mismatch")
    if not _same_fingerprint(
        shared["case_corpus_sha256"], binding_plan["case_corpus_sha256"]
    ):
        raise ValueError("paired_corpus_binding_mismatch")

    return {
        "valid": True,
        "source_dataset_corpus_bindings_match": binding_result["bindings_match"],
        "paired_plan_valid": pair_result["valid"],
        "planned_pair_count": pair_result["pair_count"],
        "planned_run_count": pair_result["planned_run_count"],
        "measurement_authorized": False,
    }


def _read_json(path: Path, limit: int) -> tuple[Any, bytes]:
    """Read one bounded local JSON input without following remote references."""
    if path.stat().st_size > limit:
        raise ValueError("input_too_large")
    data = path.read_bytes()
    if len(data) > limit:
        raise ValueError("input_too_large")
    return json.loads(data), data


def main() -> None:
    """Validate four local inputs and print only an aggregate result."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("binding_plan", type=Path)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("ordered_reference", type=Path)
    parser.add_argument("paired_plan", type=Path)
    args = parser.parse_args()
    try:
        binding_plan, _ = _read_json(args.binding_plan, BINDING_MAX_INPUT_BYTES)
        if args.corpus.stat().st_size > BINDING_MAX_INPUT_BYTES:
            raise ValueError("input_too_large")
        corpus_bytes = args.corpus.read_bytes()
        if len(corpus_bytes) > BINDING_MAX_INPUT_BYTES:
            raise ValueError("input_too_large")
        ordered_reference, _ = _read_json(
            args.ordered_reference, BINDING_MAX_INPUT_BYTES
        )
        paired_plan, _ = _read_json(args.paired_plan, PAIR_MAX_INPUT_BYTES)
        print(
            json.dumps(
                validate_run_inputs(
                    binding_plan, corpus_bytes, ordered_reference, paired_plan
                ),
                sort_keys=True,
            )
        )
    except (OSError, ValueError, TypeError, KeyError):
        parser.exit(2, "Comparison input preflight failed; no workload was started\n")


if __name__ == "__main__":
    main()
