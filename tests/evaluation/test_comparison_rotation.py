"""Deterministic synthetic checks for the approved nine-pair rotation."""

import json
import subprocess
import sys

import pytest

from scripts.evaluation.k6.comparison_rotation import (
    ROTATION_RULE,
    rotation_start,
    rotation_starts,
)


def test_seed_three_wraps_and_assigns_nine_distinct_pair_starts() -> None:
    assert rotation_starts(3) == (3, 4, 5, 6, 7, 8, 9, 0, 1)
    assert rotation_starts(3) == rotation_starts(3)
    assert rotation_start(3, 1, "low") == 3
    assert rotation_start(3, 2, "low") == 6
    assert rotation_start(3, 3, "burst") == 1


@pytest.mark.parametrize("seed", [None, True, -1, 10, 1.0, "3"])
def test_invalid_seed_is_rejected(seed: object) -> None:
    with pytest.raises(ValueError, match="rotation_seed"):
        rotation_starts(seed)


def test_invalid_cycle_and_condition_are_rejected() -> None:
    with pytest.raises(ValueError, match="rotation_cycle_invalid"):
        rotation_start(0, True, "low")
    with pytest.raises(ValueError, match="rotation_condition_invalid"):
        rotation_start(0, 1, "other")


def test_cli_prints_deterministic_synthetic_plan_without_authorizing() -> None:
    command = [
        sys.executable,
        "-m",
        "scripts.evaluation.k6.comparison_rotation",
        "--seed",
        "3",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["rule"] == ROTATION_RULE
    assert output["measurement_authorized"] is False
    assert [pair["sequence_start"] for pair in output["pairs"]] == [
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        0,
        1,
    ]
    assert output["pairs"][3] == {"cycle": 2, "condition": "low", "sequence_start": 6}
    bad = subprocess.run(
        command[:-1] + ["10"], capture_output=True, text=True, check=False
    )
    assert bad.returncode == 2
