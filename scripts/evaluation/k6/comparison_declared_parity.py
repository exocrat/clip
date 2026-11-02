"""Compare declared paired-run dataset and search bindings without network access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.evaluation.k6.comparison_manifest import HEX64, _utc
from scripts.evaluation.k6.comparison_run_preflight import (
    MAX_INPUT_BYTES,
    validate_run_inputs,
)
from scripts.evaluation.k6.comparison_telemetry import _reference

TOP_FIELDS = {"format_version", "purpose", "cycle", "condition", "configurations"}
SNAPSHOT_FIELDS = {
    "run_id",
    "observed_at_utc",
    "dataset_fingerprint",
    "schema_version",
    "index_fingerprint",
    "database_settings_sha256",
    "search_contract_revision",
    "search_implementation_revision",
    "model_revision",
    "evidence_reference",
    "evidence_sha256",
}


def validate_declared_parity(
    record: Any, binding: Any, corpus: bytes, reference: Any, plan: Any
) -> dict[str, Any]:
    """Compare two supplied declarations to the independently supplied plan/reference."""
    validate_run_inputs(binding, corpus, reference, plan)
    if not isinstance(record, dict) or set(record) != TOP_FIELDS:
        raise ValueError("invalid_parity_shape")
    if (
        type(record["format_version"]) is not int
        or record["format_version"] != 1
        or record["purpose"] != "declared-pair-parity-not-authorization"
    ):
        raise ValueError("invalid_parity_kind")
    cycle, condition = record["cycle"], record["condition"]
    if (
        type(cycle) is not int
        or cycle not in (1, 2, 3)
        or condition not in ("low", "normal", "burst")
    ):
        raise ValueError("invalid_pair_selection")
    configs = record["configurations"]
    if not isinstance(configs, dict) or set(configs) != {"A", "B"}:
        raise ValueError("invalid_configurations")
    pair = next(
        item
        for item in plan["cycles"][cycle - 1]["pairs"]
        if item["condition"] == condition
    )
    expected = {
        "dataset_fingerprint": plan["shared_inputs"]["dataset_fingerprint"],
        "schema_version": reference["schema_version"],
        "index_fingerprint": plan["shared_inputs"]["index_fingerprint"],
        "database_settings_sha256": plan["shared_inputs"]["database_settings_sha256"],
        "search_contract_revision": reference["search_contract_revision"],
        "search_implementation_revision": binding["application_revision"],
        "model_revision": reference["model_revision"],
    }
    for name in ("A", "B"):
        item = configs[name]
        if not isinstance(item, dict) or set(item) != SNAPSHOT_FIELDS:
            raise ValueError("invalid_snapshot_shape")
        if item["run_id"] != pair[f"{name}_run_id"]:
            raise ValueError("snapshot_run_id_mismatch")
        _utc(item["observed_at_utc"], "observation")
        if (
            not _reference(item["evidence_reference"])
            or not isinstance(item["evidence_sha256"], str)
            or not HEX64.fullmatch(item["evidence_sha256"])
        ):
            raise ValueError("invalid_evidence_reference")
        for field, expected_value in expected.items():
            actual = item[field]
            if not isinstance(actual, str):
                raise ValueError("missing_parity_value")
            if field in {"dataset_fingerprint", "database_settings_sha256"}:
                actual, expected_value = actual.removeprefix(
                    "sha256:"
                ), expected_value.removeprefix("sha256:")
            if actual != expected_value:
                raise ValueError("declared_parity_mismatch")
    return {
        "declared_pair_matches_plan_and_reference": True,
        "evidence_files_inspected": False,
        "deployed_parity_verified": False,
        "observation_freshness_verified": False,
        "human_review_verified": False,
        "measurement_authorized": False,
    }


def _read(path: Path) -> bytes:
    """Read bounded local input and do not expose its contents."""
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("input_too_large")
    data = path.read_bytes()
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("input_too_large")
    return data


def main() -> None:
    """Print aggregate consistency status; never access a deployment."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("parity", "binding", "corpus", "reference", "plan"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    try:
        result = validate_declared_parity(
            json.loads(_read(args.parity)),
            json.loads(_read(args.binding)),
            _read(args.corpus),
            json.loads(_read(args.reference)),
            json.loads(_read(args.plan)),
        )
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError, StopIteration):
        parser.exit(2, "Declared parity check failed; no workload was started\n")


if __name__ == "__main__":
    main()
