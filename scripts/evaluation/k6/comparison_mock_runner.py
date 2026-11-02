"""Exercise preparation ordering using fixed in-memory doubles, never a workload."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from scripts.evaluation.k6.comparison_offline_prepare import _read_local, prepare_inputs
from scripts.evaluation.k6.comparison_parity_preparation import check_draft_parity
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
    *,
    parity_response_pairs: Any = None,
) -> dict[str, Any]:
    """Read local inputs, then produce simulated events only after preflight."""
    events = ["preflight_started"]
    parity_draft = parity_response_pairs is not None
    preparation = prepare_inputs(
        paths, cycle, run_id, expected_hash, allow_parity_draft=parity_draft
    )
    if not preparation["local_inputs_checked"]:
        events.append("preflight_refused")
    else:
        events.append("preflight_passed")
        if parity_draft:
            try:
                if cycle is None or expected_hash is None:
                    raise ValueError("incomplete_parity_inputs")

                def read(name: str) -> bytes:
                    path = paths.get(name)
                    if path is None:
                        raise ValueError("missing_parity_input")
                    return _read_local(path)

                result = check_draft_parity(
                    json.loads(read("binding_plan")),
                    read("corpus"),
                    json.loads(read("ordered_reference")),
                    json.loads(read("paired_plan")),
                    read("workload_profile"),
                    cycle,
                    expected_hash,
                    parity_response_pairs,
                )
                if not result["all_equal_and_valid"]:
                    raise ValueError("parity_mismatch")
                events.append("simulated_parity_passed")
            except OSError, ValueError, TypeError, KeyError:
                events.append("simulated_parity_refused")
                return {
                    "events": events,
                    "preparation": preparation,
                    "simulation_only": True,
                    "measurement_authorized": False,
                    "requests_sent": False,
                }
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
