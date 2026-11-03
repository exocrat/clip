"""Preview the median of three independently declared comparison run costs."""

import argparse
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from scripts.evaluation.k6.comparison_cost_binding import _read, check_cost_binding
from scripts.evaluation.k6.comparison_cost_preview import calculate_cost


def cost_median(runs: Any) -> dict[str, Any]:
    """Check three distinct cycles, then take the median of their unit costs."""
    if not isinstance(runs, list) or len(runs) != 3:
        raise ValueError("three_runs_required")
    configs: set[str] = set()
    conditions: set[str] = set()
    repetitions: set[int] = set()
    run_ids: set[str] = set()
    values: list[tuple[Decimal, str]] = []
    for cost, manifest, report in runs:
        check_cost_binding(cost, manifest, report)
        run = manifest["run"]
        configs.add(run["configuration"])
        conditions.add(run["condition"])
        repetitions.add(run["repetition"])
        run_ids.add(run["run_id"])
        result = calculate_cost(cost)
        unit = result["usd_per_1000_correct_operations"]
        if unit is None:
            raise ValueError("unit_cost_unavailable")
        values.append((Decimal(unit), run["run_id"]))
    if len(configs) != 1 or len(conditions) != 1:
        raise ValueError("configuration_or_condition_mismatch")
    if repetitions != {1, 2, 3} or len(run_ids) != 3:
        raise ValueError("distinct_cycles_required")
    values.sort()
    condition = next(iter(conditions))
    return {
        "configuration": next(iter(configs)),
        "condition": condition,
        "run_values_usd_per_1000": [
            {"run_id": run_id, "value": str(value)} for value, run_id in values
        ],
        "median_usd_per_1000": str(values[1][0]),
        "normal_score_input_candidate": condition == "normal",
        "cost_allocation_verified": False,
        "run_validity_verified": False,
        "score_calculated": False,
    }


def main() -> None:
    """Read three sets of local inputs and write a new standalone preview."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--run",
        nargs=3,
        action="append",
        required=True,
        metavar=("COST", "MANIFEST", "REPORT"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if len(args.run) != 3:
            raise ValueError("three_runs_required")
        runs = [
            (
                json.loads(_read(Path(cost))),
                json.loads(_read(Path(manifest))),
                _read(Path(report)),
            )
            for cost, manifest, report in args.run
        ]
        result = cost_median(runs)
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write("\n")
    except OSError, ValueError, TypeError, KeyError:
        parser.exit(2, "Could not produce cost median preview\n")


if __name__ == "__main__":
    main()
