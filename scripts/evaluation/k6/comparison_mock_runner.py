"""Exercise preparation ordering using fixed in-memory doubles, never a workload."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.evaluation.k6.comparison_offline_prepare import prepare_inputs


def simulate_run(
    paths: Mapping[str, Path | None],
    cycle: int | None,
    run_id: str | None,
    expected_hash: str | None,
) -> dict[str, Any]:
    """Read local inputs, then produce simulated events only after preflight."""
    events = ["preflight_started"]
    preparation = prepare_inputs(paths, cycle, run_id, expected_hash)
    if not preparation["local_inputs_checked"]:
        events.append("preflight_refused")
    else:
        events.extend(("preflight_passed", "simulated_session", "simulated_workload"))
    return {
        "events": events,
        "preparation": preparation,
        "simulation_only": True,
        "measurement_authorized": False,
        "requests_sent": False,
    }
