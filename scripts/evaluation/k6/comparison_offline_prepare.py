"""Check local inputs for one planned comparison run without executing it."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

from scripts.evaluation.k6.comparison_binding_preflight import MAX_INPUT_BYTES
from scripts.evaluation.k6.comparison_run_preflight import validate_run_inputs

FILE_FIELDS = (
    "binding_plan",
    "corpus",
    "ordered_reference",
    "paired_plan",
    "workload_profile",
)
REMAINING_GATES = (
    "independent_reference_and_owner_review",
    "deployed_target_and_dataset_parity",
    "timing_protocol_and_generator_capacity",
    "authentication_and_runner_integration",
    "run_approval_telemetry_cost_and_cleanup",
)


def _read_local(path: Path) -> bytes:
    """Read a bounded regular local file without following its final symlink."""
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("safe_read_unavailable")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("regular_file_required")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
        if len(data) > MAX_INPUT_BYTES:
            raise ValueError("input_too_large")
        return data
    finally:
        os.close(fd)


def prepare_inputs(
    paths: Mapping[str, Path | None],
    cycle: int | None,
    run_id: str | None,
    expected_hash: str | None,
    *,
    allow_parity_draft: bool = False,
) -> dict[str, Any]:
    """Validate supplied files and a planned run; return only safe status labels."""
    missing = [name for name in FILE_FIELDS if paths.get(name) is None]
    if cycle is None:
        missing.append("cycle")
    if not run_id:
        missing.append("run_id")
    if not expected_hash:
        missing.append("expected_profile_sha256")
    invalid: list[str] = []
    contents: dict[str, bytes] = {}
    parsed: dict[str, Any] = {}
    for name in FILE_FIELDS:
        path = paths.get(name)
        if path is None:
            continue
        try:
            data = _read_local(path)
            contents[name] = data
            parsed[name] = json.loads(data)
        except OSError, ValueError, TypeError:
            invalid.append(name)
    if cycle is not None and (type(cycle) is not int or cycle not in (1, 2, 3)):
        invalid.append("cycle")
    if run_id and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}", run_id):
        invalid.append("run_id")
    if expected_hash and not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        invalid.append("expected_profile_sha256")
    checked = False
    if not missing and not invalid:
        try:
            result = validate_run_inputs(
                parsed["binding_plan"],
                contents["corpus"],
                parsed["ordered_reference"],
                parsed["paired_plan"],
                parsed["workload_profile"],
                cycle,
                profile_bytes=contents["workload_profile"],
                expected_profile_sha256=expected_hash,
                allow_parity_draft=allow_parity_draft,
            )
            if (
                not result["workload_profile_checked"]
                or not result["profile_hash_checked"]
            ):
                raise ValueError("incomplete_profile_check")
            if cycle is None:
                raise ValueError("cycle_required")
            pairs = parsed["paired_plan"]["cycles"][cycle - 1]["pairs"]
            if (
                sum(
                    run_id == pair[f"{side}_run_id"]
                    for pair in pairs
                    for side in ("A", "B")
                )
                != 1
            ):
                raise ValueError("run_not_in_selected_cycle")
            checked = True
        except OSError, ValueError, TypeError, KeyError, IndexError:
            invalid.append("input_bindings_or_planned_run")
    return {
        "local_inputs_checked": checked,
        "missing_inputs": missing,
        "invalid_inputs": invalid,
        "remaining_run_gates": list(REMAINING_GATES),
        "measurement_authorized": False,
        "requests_sent": False,
    }


def main() -> None:
    """Accept optional paths and print an aggregate offline readiness report."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for field in FILE_FIELDS:
        parser.add_argument("--" + field.replace("_", "-"), type=Path)
    parser.add_argument("--cycle", type=int)
    parser.add_argument("--run-id")
    parser.add_argument("--expected-profile-sha256")
    args = parser.parse_args()
    result = prepare_inputs(
        {name: getattr(args, name) for name in FILE_FIELDS},
        args.cycle,
        args.run_id,
        args.expected_profile_sha256,
    )
    print(json.dumps(result, sort_keys=True))
    if not result["local_inputs_checked"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
