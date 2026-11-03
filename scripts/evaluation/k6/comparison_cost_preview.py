"""Calculate a supplied run's cost per correct operation without billing access.

Inputs are declarations, not evidence of complete allocation or run validity.
"""

import argparse
from decimal import Decimal, InvalidOperation, localcontext
import json
from pathlib import Path
import re
from typing import Any

MAX_BYTES = 4096


def calculate_cost(record: Any) -> dict[str, Any]:
    """Check one bounded declared interval and compute its pre-credit unit cost."""
    fields = {"run_id", "condition", "cost_usd", "cost_basis", "correct_operations"}
    if not isinstance(record, dict) or set(record) != fields:
        raise ValueError("invalid_cost_record")
    run_id = record["run_id"]
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id):
        raise ValueError("invalid_run_id")
    if record["condition"] not in ("low", "normal", "burst"):
        raise ValueError("invalid_condition")
    if record["cost_basis"] not in ("estimated", "billing"):
        raise ValueError("invalid_cost_basis")
    cost = record["cost_usd"]
    if not isinstance(cost, str) or not re.fullmatch(
        r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?", cost
    ):
        raise ValueError("invalid_cost")
    count = record["correct_operations"]
    if type(count) is not int or not 0 <= count <= 2**53 - 1:
        raise ValueError("invalid_correct_operations")
    with localcontext() as context:
        context.prec = 50
        amount = Decimal(cost)
        unit_cost = str(amount * 1000 / count) if count else None
    return {
        "run_id": run_id,
        "condition": record["condition"],
        "cost_usd_before_credits": cost,
        "cost_basis": record["cost_basis"],
        "correct_operations": count,
        "usd_per_1000_correct_operations": unit_cost,
        "unit_cost_unavailable_reason": "no_correct_operations" if not count else None,
        "inputs_independently_verified": False,
        "run_validity_verified": False,
    }


def main() -> None:
    """Read a bounded local declaration and write a new, separate report."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > MAX_BYTES:
            raise ValueError("input_too_large")
        data = args.input.read_bytes()
        if len(data) > MAX_BYTES:
            raise ValueError("input_too_large")
        report = calculate_cost(json.loads(data))
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(report, output, sort_keys=True, indent=2)
            output.write("\n")
    except OSError, ValueError, TypeError, InvalidOperation:
        parser.exit(2, "Could not produce cost preview; no output was authorized\n")


if __name__ == "__main__":
    main()
