"""Connect draft profile validation and supplied response comparison offline.

No requests, sessions or deployment checks are performed. This is not a run gate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from scripts.evaluation.k6.comparison_run_preflight import validate_run_inputs

ROOT = Path(__file__).resolve().parents[3]
MAX_INPUT_BYTES = 5_000_000


def check_draft_parity(
    binding: Any,
    corpus_bytes: bytes,
    reference: Any,
    plan: Any,
    profile_bytes: bytes,
    cycle: int,
    profile_sha256: str,
    cases: Any,
) -> dict[str, Any]:
    """Validate draft inputs first, then compare supplied responses without logging them."""
    if not isinstance(profile_bytes, bytes) or len(profile_bytes) > MAX_INPUT_BYTES:
        raise ValueError("invalid_profile_bytes")
    profile = json.loads(profile_bytes)
    checked = validate_run_inputs(
        binding,
        corpus_bytes,
        reference,
        plan,
        profile,
        cycle,
        profile_bytes=profile_bytes,
        expected_profile_sha256=profile_sha256,
        allow_parity_draft=True,
    )
    if checked.get("parity_draft_checked") is not True:
        raise ValueError("parity_draft_required")
    payload = json.dumps(
        {"corpus": json.loads(corpus_bytes), "cases": cases},
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError("parity_input_too_large")
    try:
        process = subprocess.run(
            ["node", "scripts/evaluation/k6/comparison_search_parity_cli.mjs", "--all"],
            cwd=ROOT,
            input=payload,
            capture_output=True,
            check=False,
            timeout=15,
        )
        result = json.loads(process.stdout)
        if (
            process.returncode not in (0, 2)
            or not isinstance(result, dict)
            or set(result)
            != {
                "cases_checked",
                "cases_equal_and_valid",
                "all_equal_and_valid",
                "corpus_authenticity_verified",
                "independent_correctness_verified",
                "deployment_verified",
                "measurement_authorized",
            }
            or type(result["cases_equal_and_valid"]) is not int
            or not 0 <= result["cases_equal_and_valid"] <= 10
            or result["cases_checked"] != 10
            or type(result["all_equal_and_valid"]) is not bool
            or result["all_equal_and_valid"] != (result["cases_equal_and_valid"] == 10)
            or process.returncode != (0 if result["all_equal_and_valid"] else 2)
            or any(
                result[key] is not False
                for key in (
                    "corpus_authenticity_verified",
                    "independent_correctness_verified",
                    "deployment_verified",
                    "measurement_authorized",
                )
            )
        ):
            raise ValueError("comparison_output_invalid")
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        raise ValueError("offline_comparison_failed") from None
    return {
        "draft_inputs_checked": True,
        "corpus_sha256": hashlib.sha256(corpus_bytes).hexdigest(),
        "profile_sha256": profile_sha256,
        "cases_equal_and_valid": result["cases_equal_and_valid"],
        "all_equal_and_valid": result["all_equal_and_valid"],
        "deployment_verified": False,
        "independent_correctness_verified": False,
        "measurement_authorized": False,
    }
