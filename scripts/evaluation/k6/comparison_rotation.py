"""Generate the approved nine-pair case rotation offline from a supplied seed."""

from __future__ import annotations

import argparse
import json

ROTATION_RULE = "increment-one-per-pair-v1"
CONDITIONS = ("low", "normal", "burst")


def rotation_starts(seed: object) -> tuple[int, ...]:
    """Return nine starts, advancing one position per pair and wrapping at ten."""
    if type(seed) is not int or not 0 <= seed <= 9:
        raise ValueError("rotation_seed_must_be_integer_zero_to_nine")
    return tuple((seed + pair_index) % 10 for pair_index in range(9))


def rotation_start(seed: object, cycle: object, condition: object) -> int:
    """Find the planned start for one cycle/condition; A and B share it."""
    starts = rotation_starts(seed)
    if type(cycle) is not int or cycle not in (1, 2, 3):
        raise ValueError("rotation_cycle_invalid")
    if not isinstance(condition, str) or condition not in CONDITIONS:
        raise ValueError("rotation_condition_invalid")
    return starts[(cycle - 1) * len(CONDITIONS) + CONDITIONS.index(condition)]


def main() -> None:
    """Print the nine deterministic starts; this does not authorize a run."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--seed", required=True, type=int)
    args = parser.parse_args()
    try:
        starts = rotation_starts(args.seed)
    except ValueError:
        parser.exit(2, "Rotation seed must be an integer from 0 through 9\n")
    pairs = [
        {"cycle": cycle, "condition": condition, "sequence_start": starts[index]}
        for index, (cycle, condition) in enumerate(
            (cycle, condition) for cycle in (1, 2, 3) for condition in CONDITIONS
        )
    ]
    print(
        json.dumps(
            {
                "rule": ROTATION_RULE,
                "seed": args.seed,
                "pairs": pairs,
                "measurement_authorized": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
