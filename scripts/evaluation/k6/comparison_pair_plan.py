"""Check the declared EXP-02 paired run order and shared workload inputs offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "data/evaluation/workloads/ecs-lambda-paired-plan.template.json"
MAX_INPUT_BYTES = 2_000_000
CONDITIONS = ("low", "normal", "burst")
CONFIGURATION_ORDERS = (("A", "B"), ("B", "A"), ("A", "B"))
TOP_KEYS = {"schema_version", "purpose", "plan_state", "shared_inputs", "cycles"}
SHARED_KEYS = {
    "dataset_fingerprint",
    "index_fingerprint",
    "database_settings_sha256",
    "schedule_sha256",
    "case_corpus_sha256",
    "load_script_sha256",
    "generator_version",
}
CYCLE_KEYS = {"cycle", "configuration_order", "pairs"}
PAIR_KEYS = {"condition", "sequence_start", "A_run_id", "B_run_id"}
SHA256 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


def _object(value: object, keys: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(code)
    return value


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_pair_plan(value: Any) -> dict[str, Any]:
    """Validate one template or complete plan; never authorize a measurement."""
    plan = _object(value, TOP_KEYS, "invalid_plan_shape")
    if type(plan["schema_version"]) is not int or plan["schema_version"] != 1:
        raise ValueError("unsupported_plan_version")
    if plan["purpose"] != "offline-paired-run-plan-not-authorization":
        raise ValueError("invalid_plan_purpose")
    state = plan["plan_state"]
    if not isinstance(state, str) or state not in {"template", "planned"}:
        raise ValueError("invalid_plan_state")

    shared = _object(plan["shared_inputs"], SHARED_KEYS, "invalid_shared_inputs")
    if not isinstance(plan["cycles"], list) or len(plan["cycles"]) != 3:
        raise ValueError("three_cycles_required")

    run_ids: set[str] = set()
    for index, (cycle_value, expected_order) in enumerate(
        zip(plan["cycles"], CONFIGURATION_ORDERS, strict=True), start=1
    ):
        cycle = _object(cycle_value, CYCLE_KEYS, "invalid_cycle")
        if type(cycle["cycle"]) is not int or cycle["cycle"] != index:
            raise ValueError("cycle_order_mismatch")
        if cycle["configuration_order"] != list(expected_order):
            raise ValueError("configuration_order_mismatch")
        pairs = cycle["pairs"]
        if not isinstance(pairs, list) or len(pairs) != len(CONDITIONS):
            raise ValueError("three_condition_pairs_required")
        for pair, expected_condition in zip(pairs, CONDITIONS, strict=True):
            pair = _object(pair, PAIR_KEYS, "invalid_pair")
            if pair["condition"] != expected_condition:
                raise ValueError("condition_order_mismatch")
            if state == "template":
                if any(
                    pair[key] is not None
                    for key in ("sequence_start", "A_run_id", "B_run_id")
                ):
                    raise ValueError("template_contains_run_values")
                continue
            sequence_start = pair["sequence_start"]
            if type(sequence_start) is not int or not 0 <= sequence_start < 10:
                raise ValueError("invalid_sequence_start")
            for config in ("A", "B"):
                run_id = pair[f"{config}_run_id"]
                if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
                    raise ValueError("invalid_run_id")
                if run_id in run_ids:
                    raise ValueError("duplicate_run_id")
                run_ids.add(run_id)

    if state == "template":
        if any(value is not None for value in shared.values()):
            raise ValueError("template_contains_shared_inputs")
        return {
            "valid": True,
            "state": "template",
            "pair_count": 9,
            "planned_run_count": 18,
            "measurement_authorized": False,
        }

    for key, item in shared.items():
        if not _nonempty(item):
            raise ValueError("missing_shared_input")
        if key in {
            "dataset_fingerprint",
            "database_settings_sha256",
            "schedule_sha256",
            "case_corpus_sha256",
            "load_script_sha256",
        } and not SHA256.fullmatch(item):
            raise ValueError("invalid_shared_fingerprint")
    if len(run_ids) != 18:
        raise ValueError("eighteen_unique_run_ids_required")
    return {
        "valid": True,
        "state": "planned",
        "cycle_configuration_order": [list(order) for order in CONFIGURATION_ORDERS],
        "pair_count": 9,
        "planned_run_count": len(run_ids),
        "shared_inputs_bound": True,
        "measurement_authorized": False,
    }


def _read(path: Path) -> Any:
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("plan_too_large")
    data = path.read_bytes()
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("plan_too_large")
    return json.loads(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "plan", nargs="?", type=Path, default=TEMPLATE, help="local paired plan JSON"
    )
    args = parser.parse_args()
    try:
        result = validate_pair_plan(_read(args.plan))
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError):
        parser.exit(2, "Paired run plan check failed; no workload was started\n")


if __name__ == "__main__":
    main()
