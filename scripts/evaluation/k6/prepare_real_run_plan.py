"""Build one offline, hash-bound plan for the shared real-run coordinator.

This command reads local reviewed inputs only. It never contacts AWS, obtains a
session, sends workload traffic, creates the evidence directory, or authorizes
execution. A separate short-lived approval must bind the resulting exact bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from scripts.evaluation.k6.comparison_stage_run import MODULES as COMPARISON_MODULES
from scripts.evaluation.k6.real_run_coordinator import (
    NFR_MODULES,
    ROOT,
    _file_sha,
    _new_evidence_path,
    _repo_path,
    _validate_profile,
    _verify_modules,
    _write_new,
)
from scripts.evaluation.k6.real_target_preflight import (
    validate_plan as validate_target_plan,
)


def _read_json(path: Path, field: str) -> tuple[dict[str, Any], bytes]:
    """Read a small repository JSON input through the coordinator's safe reader."""
    from scripts.evaluation.k6.real_run_coordinator import _read_bounded

    raw = _read_bounded(path, 10_000_000)
    document = json.loads(raw)
    if not isinstance(document, dict):
        raise ValueError(f"invalid_{field}")
    return document, raw


def _new_output(value: str) -> Path:
    """Resolve a new repository file while requiring an existing safe parent."""
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts or "." in candidate.parts:
        raise ValueError("unsafe_output_path")
    output = ROOT / candidate
    parent = output.parent.resolve(strict=True)
    if not parent.is_relative_to(ROOT) or output.exists() or output.is_symlink():
        raise ValueError("output_path_unavailable")
    current = ROOT
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("output_path_symlink")
    return output


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Bind selected target, profile, binary and exact workload modules offline."""
    kind = args.workload_kind
    if kind not in {"comparison", *NFR_MODULES}:
        raise ValueError("unsupported_workload_kind")
    target_path = _repo_path(args.target_plan, "target_plan")
    target, target_bytes = _read_json(target_path, "target_plan")
    validate_target_plan(target)
    if target["run_id"] != args.run_id or target["configuration"] != args.configuration:
        raise ValueError("target_run_binding_mismatch")
    report_cap = 190_000_000 if kind == "nfr-03" else 90_000_000
    raw_limit = (
        args.maximum_raw_bytes if args.maximum_raw_bytes is not None else report_cap
    )
    if raw_limit > report_cap:
        raise ValueError("raw_limit_exceeds_reporter_capacity")
    profile_path = _repo_path(args.profile, "profile")
    from scripts.evaluation.k6.real_run_coordinator import _read_bounded

    profile_bytes = _read_bounded(profile_path, 5_000_000)
    modules = COMPARISON_MODULES if kind == "comparison" else NFR_MODULES[kind]
    module_root = _repo_path("scripts/evaluation/k6", "module_root")
    module_hashes = {
        name: hashlib.sha256(_read_bounded(module_root / name, 2_000_000)).hexdigest()
        for name in modules
    }
    binary_path = _repo_path(args.k6_binary, "k6_binary")
    if not os.access(binary_path, os.X_OK):
        raise ValueError("k6_binary_not_executable")
    profile_doc = json.loads(profile_bytes)
    capacity = profile_doc.get("capacity", {})
    fixture_path: str | None
    fixture_hash: str | None
    condition: str | None
    cycle: int | None
    comparison_inputs: dict[str, Any] | None
    pilot_inputs: dict[str, Any] | None
    pilot_input_hashes: dict[str, str] | None
    if kind in {"nfr-01", "nfr-02", "exp05-pilot"}:
        fixture_path = fixture_hash = None
        comparison_inputs = None
        if kind == "exp05-pilot":
            if args.cycle not in (1, 2, 3):
                raise ValueError("pilot_source_cycle_required")
            condition, cycle = "burst", args.cycle
            raw_pilot_inputs = {
                "binding_plan": args.binding_plan,
                "corpus": args.corpus,
                "ordered_reference": args.ordered_reference,
                "paired_plan": args.paired_plan,
                "comparison_profile": args.comparison_profile,
                "parity": args.parity,
                "parity_evidence_root": args.parity_evidence_root,
                "source_dir": "scripts/evaluation/k6",
                "schedule": args.schedule,
            }
            if any(value is None for value in raw_pilot_inputs.values()):
                raise ValueError("pilot_source_inputs_required")
            pilot_inputs = raw_pilot_inputs
            pilot_input_hashes = {
                key: hashlib.sha256(
                    _read_bounded(_repo_path(value, f"pilot_{key}"), 10_000_000)
                ).hexdigest()
                for key, value in raw_pilot_inputs.items()
                if key not in {"parity_evidence_root", "source_dir"}
            }
            if set(pilot_input_hashes) != {
                "binding_plan",
                "corpus",
                "ordered_reference",
                "paired_plan",
                "comparison_profile",
                "parity",
                "schedule",
            }:
                raise ValueError("pilot_source_hashes_incomplete")
        else:
            condition = cycle = None
            pilot_inputs = pilot_input_hashes = None
    elif kind == "nfr-03":
        fixture_path = args.fixture
        if not fixture_path:
            raise ValueError("nfr03_fixture_required")
        fixture_file = _repo_path(fixture_path, "fixture")
        fixture_bytes = _read_bounded(fixture_file, 65_536)
        fixture_hash = hashlib.sha256(fixture_bytes).hexdigest()
        condition = cycle = comparison_inputs = None
        pilot_inputs = pilot_input_hashes = None
    else:
        if args.cycle not in (1, 2, 3) or args.condition not in {
            "low",
            "normal",
            "burst",
        }:
            raise ValueError("comparison_pair_selection_required")
        fixture_path = fixture_hash = None
        condition, cycle = args.condition, args.cycle
        pilot_inputs = pilot_input_hashes = None
        required = {
            "binding_plan": args.binding_plan,
            "corpus": args.corpus,
            "ordered_reference": args.ordered_reference,
            "paired_plan": args.paired_plan,
            "workload_profile": args.profile,
            "parity": args.parity,
            "parity_evidence_root": args.parity_evidence_root,
            "source_dir": "scripts/evaluation/k6",
            "schedule": args.schedule,
        }
        if any(value is None for value in required.values()):
            raise ValueError("comparison_inputs_required")
        for name, value in required.items():
            if name == "parity_evidence_root":
                _repo_path(value, name)
            elif name == "source_dir":
                _repo_path(value, name)
            else:
                _repo_path(value, name)
        comparison_inputs = required
    plan = {
        "format_version": 1,
        "purpose": "clip-approved-k6-run",
        "run_id": args.run_id,
        "workload_kind": kind,
        "configuration": args.configuration,
        "target_plan_path": args.target_plan,
        "target_plan_sha256": hashlib.sha256(target_bytes).hexdigest(),
        "profile_path": args.profile,
        "profile_sha256": hashlib.sha256(profile_bytes).hexdigest(),
        "fixture_path": fixture_path,
        "fixture_sha256": fixture_hash,
        "condition": condition,
        "cycle": cycle,
        "comparison_inputs": comparison_inputs,
        "pilot_inputs": pilot_inputs,
        "pilot_input_hashes": pilot_input_hashes,
        "module_hashes": module_hashes,
        "k6_binary_path": args.k6_binary,
        "k6_binary_sha256": _file_sha(binary_path, 2_000_000_000),
        "expected_user_id": target["expected_user_id"],
        "maximum_duration_seconds": args.maximum_duration_seconds,
        "maximum_raw_bytes": raw_limit,
        "evidence_directory": args.evidence_directory,
        "execution_permitted": False,
        "nfr_accepted": False,
    }
    from scripts.evaluation.k6.real_run_coordinator import validate_run_plan

    validate_run_plan(plan)
    _validate_profile(plan, profile_bytes)
    _verify_modules(plan)
    if kind == "exp05-pilot":
        from scripts.evaluation.k6.real_run_coordinator import _validate_pilot_sources

        _validate_pilot_sources(plan, json.loads(profile_bytes))
    _new_evidence_path(args.evidence_directory)
    return plan


def main() -> int:
    """Parse one bounded local plan request and write a new private JSON file."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--workload-kind", required=True, choices=["comparison", *NFR_MODULES]
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--configuration", required=True, choices=["A", "B"])
    parser.add_argument("--target-plan", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--k6-binary", required=True)
    parser.add_argument("--evidence-directory", required=True)
    parser.add_argument("--maximum-duration-seconds", type=int, default=400)
    parser.add_argument("--maximum-raw-bytes", type=int)
    parser.add_argument("--fixture")
    parser.add_argument("--condition", choices=["low", "normal", "burst"])
    parser.add_argument("--cycle", type=int, choices=[1, 2, 3])
    parser.add_argument("--binding-plan")
    parser.add_argument("--corpus")
    parser.add_argument("--ordered-reference")
    parser.add_argument("--paired-plan")
    parser.add_argument("--parity")
    parser.add_argument("--parity-evidence-root")
    parser.add_argument("--schedule")
    parser.add_argument("--comparison-profile")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        output = _new_output(args.output)
        plan = build_plan(args)
        _write_new(output, (json.dumps(plan, sort_keys=True, indent=2) + "\n").encode())
        os.chmod(output, 0o400)
        plan_bytes = (json.dumps(plan, sort_keys=True, indent=2) + "\n").encode()
        print(
            json.dumps(
                {
                    "run_id": plan["run_id"],
                    "workload_kind": plan["workload_kind"],
                    "configuration": plan["configuration"],
                    "execution_permitted": False,
                    "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
                    "output": str(output.relative_to(ROOT)),
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as error:
        code = (
            str(error)
            if isinstance(error, ValueError)
            and error.args
            and str(error).replace("_", "").isalnum()
            else "invalid_run_plan_input"
        )
        parser.exit(
            2, f"Real-run plan refused: {code}; no AWS or workload request was made\n"
        )


if __name__ == "__main__":
    raise SystemExit(main())
