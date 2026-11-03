"""Cross-check prepared comparison inputs offline; never authorize a run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
MAX_SAFE_INTEGER = 2**53 - 1


def validate_generator_capacity(capacity: Any) -> None:
    """Check JavaScript-representable worker settings without setting a cap."""
    if not isinstance(capacity, dict) or set(capacity) != {"preAllocatedVUs", "maxVUs"}:
        raise ValueError("invalid_generator_capacity")
    pre, maximum = capacity["preAllocatedVUs"], capacity["maxVUs"]
    if (
        type(pre) is not int
        or type(maximum) is not int
        or not 1 <= pre <= maximum <= MAX_SAFE_INTEGER
    ):
        raise ValueError("invalid_generator_capacity")


def _same_fingerprint(left: str, right: str) -> bool:
    """Compare SHA-256 values whether or not they carry the sha256 prefix."""
    return left.removeprefix("sha256:") == right.removeprefix("sha256:")


def _canonical_json(value: Any) -> str:
    """Compare JSON values without treating booleans as integers."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate_run_inputs(
    binding_plan: Any,
    corpus_bytes: bytes,
    ordered_reference: Any,
    paired_plan: Any,
    workload_profile: Any = None,
    cycle: int | None = None,
    *,
    profile_bytes: bytes | None = None,
    expected_profile_sha256: str | None = None,
    allow_parity_draft: bool = False,
) -> dict[str, Any]:
    """Check bindings, the paired plan, and optionally one cycle's profile."""
    binding_result = validate_bindings(
        binding_plan,
        corpus_bytes,
        ordered_reference,
        allow_parity_draft=allow_parity_draft,
    )
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

    profile_checked = workload_profile is not None or cycle is not None
    if profile_checked:
        if (
            not isinstance(workload_profile, dict)
            or type(cycle) is not int
            or cycle not in (1, 2, 3)
        ):
            raise ValueError("workload_profile_and_cycle_required")
        if set(workload_profile) != {
            "cases",
            "sequence_starts",
            "capacity",
            "timeout_seconds",
        }:
            raise ValueError("invalid_workload_profile_shape")
        if (
            type(workload_profile["timeout_seconds"]) is not int
            or workload_profile["timeout_seconds"] != 5
        ):
            raise ValueError("invalid_profile_timeout")
        validate_generator_capacity(workload_profile["capacity"])
        starts = workload_profile.get("sequence_starts")
        if (
            not isinstance(starts, dict)
            or set(starts) != {"low", "normal", "burst"}
            or any(
                type(value) is not int or not 0 <= value < 10
                for value in starts.values()
            )
        ):
            raise ValueError("invalid_profile_sequence_starts")
        expected_starts = {
            pair["condition"]: pair["sequence_start"]
            for pair in paired_plan["cycles"][cycle - 1]["pairs"]
        }
        if starts != expected_starts:
            raise ValueError("profile_sequence_starts_mismatch")
        if _canonical_json(workload_profile.get("cases")) != _canonical_json(
            json.loads(corpus_bytes)["cases"]
        ):
            raise ValueError("profile_cases_mismatch")

    hash_checked = profile_bytes is not None or expected_profile_sha256 is not None
    if hash_checked:
        if (
            not profile_checked
            or not isinstance(profile_bytes, bytes)
            or not isinstance(expected_profile_sha256, str)
        ):
            raise ValueError("profile_bytes_and_hash_required")
        if len(profile_bytes) > BINDING_MAX_INPUT_BYTES or not re.fullmatch(
            r"[0-9a-f]{64}", expected_profile_sha256
        ):
            raise ValueError("invalid_profile_bytes_or_hash")
        if hashlib.sha256(profile_bytes).hexdigest() != expected_profile_sha256:
            raise ValueError("profile_hash_mismatch")
        if _canonical_json(json.loads(profile_bytes)) != _canonical_json(
            workload_profile
        ):
            raise ValueError("profile_bytes_mismatch")

    return {
        "valid": True,
        "source_dataset_corpus_bindings_match": binding_result["bindings_match"],
        "paired_plan_valid": pair_result["valid"],
        "planned_pair_count": pair_result["pair_count"],
        "planned_run_count": pair_result["planned_run_count"],
        "workload_profile_checked": profile_checked,
        "profile_hash_checked": hash_checked,
        "measurement_authorized": False,
        **(
            {"parity_draft_checked": True}
            if binding_result["parity_draft_checked"]
            else {}
        ),
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
    parser.add_argument("--workload-profile", type=Path)
    parser.add_argument("--cycle", type=int)
    parser.add_argument("--expected-profile-sha256")
    args = parser.parse_args()
    try:
        if any(
            value is not None
            for value in (
                args.workload_profile,
                args.cycle,
                args.expected_profile_sha256,
            )
        ) and any(
            value is None
            for value in (
                args.workload_profile,
                args.cycle,
                args.expected_profile_sha256,
            )
        ):
            raise ValueError("workload_profile_cycle_and_hash_required")
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
        workload_profile, profile_bytes = (
            _read_json(args.workload_profile, BINDING_MAX_INPUT_BYTES)
            if args.workload_profile is not None
            else (None, None)
        )
        print(
            json.dumps(
                validate_run_inputs(
                    binding_plan,
                    corpus_bytes,
                    ordered_reference,
                    paired_plan,
                    workload_profile,
                    args.cycle,
                    profile_bytes=profile_bytes,
                    expected_profile_sha256=args.expected_profile_sha256,
                ),
                sort_keys=True,
            )
        )
    except OSError, ValueError, TypeError, KeyError:
        parser.exit(2, "Comparison input preflight failed; no workload was started\n")


if __name__ == "__main__":
    main()
