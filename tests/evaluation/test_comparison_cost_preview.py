"""Cost arithmetic uses synthetic declarations and no external services."""

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from scripts.evaluation.k6.comparison_cost_preview import calculate_cost


@pytest.fixture
def record() -> dict[str, Any]:
    return {
        "run_id": "synthetic-A-1",
        "condition": "normal",
        "cost_usd": "0.25",
        "cost_basis": "estimated",
        "correct_operations": 500,
    }


def test_cost_uses_correct_operations_and_precise_decimal(
    record: dict[str, Any],
) -> None:
    report = calculate_cost(record)
    assert Decimal(report["usd_per_1000_correct_operations"]) == Decimal("0.5")
    assert report["inputs_independently_verified"] is False
    assert report["run_validity_verified"] is False
    record["correct_operations"] = 0
    report = calculate_cost(record)
    assert report["usd_per_1000_correct_operations"] is None
    assert report["unit_cost_unavailable_reason"] == "no_correct_operations"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("cost_usd", "-1"),
        ("cost_usd", "NaN"),
        ("cost_usd", 1),
        ("cost_usd", "1e3"),
        ("correct_operations", True),
        ("correct_operations", -1),
        ("condition", "combined"),
        ("cost_basis", "actual"),
        ("run_id", "private data"),
    ],
)
def test_bad_inputs_rejected(record: dict[str, Any], key: str, value: object) -> None:
    changed = deepcopy(record)
    changed[key] = value
    with pytest.raises(ValueError):
        calculate_cost(changed)


def test_cli_preserves_inputs_and_existing_outputs(
    tmp_path: Path, record: dict[str, Any]
) -> None:
    source = tmp_path / "input.json"
    destination = tmp_path / "report.json"
    source.write_text(json.dumps(record))
    command = [
        sys.executable,
        "-m",
        "scripts.evaluation.k6.comparison_cost_preview",
        str(source),
        "--output",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    assert result.returncode == 0
    original = destination.read_bytes()
    assert subprocess.run(command, capture_output=True, check=False).returncode == 2
    assert destination.read_bytes() == original
    assert json.loads(source.read_text()) == record
    assert (
        subprocess.run(
            command[:-1] + [str(source)], capture_output=True, check=False
        ).returncode
        == 2
    )
    assert json.loads(source.read_text()) == record
