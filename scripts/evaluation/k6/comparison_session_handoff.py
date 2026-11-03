"""Prepare an in-memory comparison session handoff; never start a process."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

SESSION_VARIABLE = "CLIP_COMPARISON_SESSION_COOKIE"
COOKIE_PATTERN = re.compile(r"__Host-clip_session=[A-Za-z0-9._~+/=-]{1,2048}\Z")


def prepare_session_environment(
    preparation: Mapping[str, Any], source_environment: Mapping[str, str]
) -> dict[str, str]:
    """Copy one session only after local checks; return no other environment values.

    The caller must keep the returned mapping private and clear it after use.
    This function does not establish session validity, approval or run readiness.
    """
    if preparation.get("local_inputs_checked") is not True:
        raise ValueError("comparison_preflight_required")
    session = source_environment.get(SESSION_VARIABLE)
    if not isinstance(session, str) or not COOKIE_PATTERN.fullmatch(session):
        raise ValueError("comparison_session_missing_or_invalid")
    return {SESSION_VARIABLE: session}
