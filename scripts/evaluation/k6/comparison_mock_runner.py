"""Exercise preparation ordering using fixed in-memory doubles, never a workload."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.evaluation.k6.comparison_offline_prepare import prepare_inputs
from scripts.evaluation.k6.comparison_session_handoff import (
    SESSION_VARIABLE,
    prepare_session_environment,
)

FAKE_SESSION = "__Host-clip_session=synthetic-test-value"


def simulate_run(
    paths: Mapping[str, Path | None],
    cycle: int | None,
    run_id: str | None,
    expected_hash: str | None,
    source_environment: Mapping[str, str],
) -> dict[str, Any]:
    """Read local inputs, then produce simulated events only after preflight."""
    events = ["preflight_started"]
    preparation = prepare_inputs(paths, cycle, run_id, expected_hash)
    if not preparation["local_inputs_checked"]:
        events.append("preflight_refused")
    else:
        events.append("preflight_passed")
        session_environment: dict[str, str] = {}
        try:
            session_environment = prepare_session_environment(
                preparation, source_environment
            )
            if session_environment[SESSION_VARIABLE] != FAKE_SESSION:
                raise ValueError("synthetic_session_required")
            events.extend(("simulated_session", "simulated_workload"))
        except KeyError, ValueError:
            events.append("session_refused")
        finally:
            session_environment.clear()
    return {
        "events": events,
        "preparation": preparation,
        "simulation_only": True,
        "measurement_authorized": False,
        "requests_sent": False,
    }
