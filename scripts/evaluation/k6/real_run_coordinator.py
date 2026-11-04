"""Bounded coordinator for one approved comparison, EXP-05 pilot or NFR-01/02/03 k6 run.

The command validates checked local inputs and a separate human action record
before live target inspection. It obtains a session only after the target check,
does one run without retries, and preserves raw output plus a separate receipt.
It never changes AWS resources and cannot accept an NFR or approve a result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import time
from typing import Any, cast

from scripts.evaluation.k6.comparison_stage_run import (
    MODULES as COMPARISON_MODULES,
    stage_run,
)
from scripts.evaluation.k6.nfr_profile_builder import build_profile as build_nfr_profile
from scripts.evaluation.k6.nfr03_profile_builder import (
    build_profile as build_nfr03_profile,
)
from scripts.evaluation.k6.real_target_preflight import (
    check_session_identity,
    inspect_target,
    validate_plan as validate_target_plan,
)

ROOT = Path(__file__).resolve().parents[3]
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
KINDS = {"comparison", "nfr-01", "nfr-02", "nfr-03", "exp05-pilot"}
NFR_MODULES = {
    "nfr-01": (
        "nfr_load.js",
        "nfr_workload.js",
        "comparison_cases.js",
        "comparison_checks.js",
        "comparison_outcomes.js",
        "core.js",
    ),
    "nfr-02": (
        "nfr_load.js",
        "nfr_workload.js",
        "comparison_cases.js",
        "comparison_checks.js",
        "comparison_outcomes.js",
        "core.js",
    ),
    "nfr-03": (
        "nfr03_load.js",
        "nfr03_schedule.js",
        "nfr03_checks.js",
        "comparison_cases.js",
        "comparison_checks.js",
        "comparison_outcomes.js",
        "core.js",
    ),
    "exp05-pilot": (
        "exp05_pilot_load.js",
        "comparison_cases.js",
        "comparison_checks.js",
        "comparison_outcomes.js",
        "core.js",
    ),
}
# Included even in deployed bundles so import closure is complete; the helper
# rejects its short-window opt-in whenever a real runner is selected.
NFR_MODULES = {
    kind: (*modules, "local_capacity_window.js")
    for kind, modules in NFR_MODULES.items()
}
PLAN_KEYS = {
    "format_version",
    "purpose",
    "run_id",
    "workload_kind",
    "configuration",
    "target_plan_path",
    "target_plan_sha256",
    "profile_path",
    "profile_sha256",
    "fixture_path",
    "fixture_sha256",
    "condition",
    "cycle",
    "comparison_inputs",
    "pilot_inputs",
    "pilot_input_hashes",
    "module_hashes",
    "k6_binary_path",
    "k6_binary_sha256",
    "expected_user_id",
    "maximum_duration_seconds",
    "maximum_raw_bytes",
    "evidence_directory",
    "execution_permitted",
    "nfr_accepted",
}
COMPARISON_INPUT_KEYS = {
    "binding_plan",
    "corpus",
    "ordered_reference",
    "paired_plan",
    "workload_profile",
    "parity",
    "parity_evidence_root",
    "source_dir",
    "schedule",
}
PILOT_INPUT_KEYS = {
    "binding_plan",
    "corpus",
    "ordered_reference",
    "paired_plan",
    "comparison_profile",
    "parity",
    "parity_evidence_root",
    "source_dir",
    "schedule",
}
PILOT_INPUT_HASH_KEYS = {
    "binding_plan",
    "corpus",
    "ordered_reference",
    "paired_plan",
    "comparison_profile",
    "parity",
    "schedule",
}
APPROVAL_KEYS = {
    "format_version",
    "action",
    "run_id",
    "workload_kind",
    "configuration",
    "run_plan_sha256",
    "target_plan_sha256",
    "authorized_at",
    "expires_at",
    "review_record",
}


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _repo_path(value: Any, name: str) -> Path:
    """Resolve one repository-relative file/directory and reject symlink components."""
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError(f"invalid_{name}_path")
    relative = Path(value)
    if ".." in relative.parts or "." in relative.parts:
        raise ValueError(f"unsafe_{name}_path")
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink_{name}_path")
    resolved = current.resolve(strict=True)
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"outside_repository_{name}_path")
    return resolved


def _new_evidence_path(value: Any) -> Path:
    """Resolve a not-yet-created run directory beneath the repository.

    Its parent must already exist so the command cannot create an unreviewed
    tree, and every existing component is checked without following symlinks.
    """
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError("invalid_evidence_directory")
    relative = Path(value)
    if ".." in relative.parts or "." in relative.parts or len(relative.parts) < 2:
        raise ValueError("unsafe_evidence_directory")
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlink_evidence_directory")
    parent = current.parent.resolve(strict=True)
    if not parent.is_relative_to(ROOT) or current.exists():
        raise ValueError("evidence_directory_unavailable")
    return parent / current.name


def _input_path(path: Path, name: str) -> Path:
    """Require a symlink-free plan or approval file within the repository."""
    candidate = path if path.is_absolute() else ROOT / path
    try:
        relative = candidate.relative_to(ROOT)
    except ValueError:
        raise ValueError(f"{name}_outside_repository") from None
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink_{name}")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"{name}_outside_repository")
    return resolved


def _read_bounded(path: Path, maximum: int = 10_000_000) -> bytes:
    """Read a regular file without following its final symlink."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError("input_not_bounded_regular_file")
        chunks: list[bytes] = []
        count = 0
        while True:
            piece = os.read(fd, min(1_048_576, maximum + 1 - count))
            if not piece:
                break
            chunks.append(piece)
            count += len(piece)
            if count > maximum:
                raise ValueError("input_too_large")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha(path: Path, maximum: int = 100_000_000) -> str:
    return _sha(_read_bounded(path, maximum))


def _hash_output(path: Path, maximum: int) -> tuple[str, int, bool]:
    """Hash a regular k6 output incrementally, including oversized failures."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("raw_output_not_regular_file")
        digest = hashlib.sha256()
        size = 0
        while True:
            block = os.read(descriptor, 1_048_576)
            if not block:
                break
            digest.update(block)
            size += len(block)
        return digest.hexdigest(), size, size > maximum
    finally:
        os.close(descriptor)


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"invalid_{field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"invalid_{field}") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"invalid_{field}")
    return parsed.astimezone(timezone.utc)


def validate_approval(plan: dict[str, Any], plan_bytes: bytes, approval: Any) -> None:
    """Bind an expiring separate approval to the exact run and target plans."""
    if not isinstance(approval, dict) or set(approval) != APPROVAL_KEYS:
        raise ValueError("invalid_action_approval")
    if (
        type(approval["format_version"]) is not int
        or approval["format_version"] != 1
        or approval["action"] != "execute_k6_run"
        or approval["run_id"] != plan["run_id"]
        or approval["workload_kind"] != plan["workload_kind"]
        or approval["configuration"] != plan["configuration"]
        or approval["run_plan_sha256"] != _sha(plan_bytes)
        or approval["target_plan_sha256"] != plan["target_plan_sha256"]
        or not isinstance(approval["review_record"], str)
        or not approval["review_record"].strip()
    ):
        raise ValueError("action_approval_binding_mismatch")
    start = _utc(approval["authorized_at"], "approval_time")
    end = _utc(approval["expires_at"], "approval_expiry")
    now = datetime.now(timezone.utc)
    if start > now or end <= now or end <= start:
        raise ValueError("action_approval_expired_or_misordered")


def validate_run_plan(plan: Any, *, completed_evidence: bool = False) -> dict[str, Any]:
    """Reject incomplete, unbounded, or locally inconsistent run declarations."""
    if not isinstance(plan, dict) or set(plan) != PLAN_KEYS:
        raise ValueError("invalid_run_plan_shape")
    if (
        type(plan["format_version"]) is not int
        or plan["format_version"] != 1
        or plan["purpose"] != "clip-approved-k6-run"
        or plan["execution_permitted"] is not False
        or plan["nfr_accepted"] is not False
        or not isinstance(plan["run_id"], str)
        or not RUN_ID.fullmatch(plan["run_id"])
        or plan["workload_kind"] not in KINDS
        or plan["configuration"] not in {"A", "B"}
        or not isinstance(plan["expected_user_id"], str)
        or not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            plan["expected_user_id"],
        )
    ):
        raise ValueError("invalid_run_plan_values")
    for key in ("target_plan_sha256", "profile_sha256", "k6_binary_sha256"):
        if not isinstance(plan[key], str) or not HEX64.fullmatch(plan[key]):
            raise ValueError("invalid_run_plan_fingerprint")
    if (
        type(plan["maximum_duration_seconds"]) is not int
        or not 300 <= plan["maximum_duration_seconds"] <= 900
    ):
        raise ValueError("invalid_run_duration_limit")
    if (
        type(plan["maximum_raw_bytes"]) is not int
        or not 1_000_000 <= plan["maximum_raw_bytes"] <= 2_000_000_000
    ):
        raise ValueError("invalid_raw_output_limit")
    if plan["configuration"] not in {"A", "B"}:
        raise ValueError("invalid_configuration")
    target = _repo_path(plan["target_plan_path"], "target_plan")
    profile = _repo_path(plan["profile_path"], "profile")
    binary = _repo_path(plan["k6_binary_path"], "k6_binary")
    if completed_evidence:
        # Reporting validates an existing run. Execution retains the default
        # requirement for a new directory so it cannot overwrite earlier raw data.
        if not _repo_path(plan["evidence_directory"], "evidence_directory").is_dir():
            raise ValueError("completed_evidence_directory_required")
    else:
        _new_evidence_path(plan["evidence_directory"])
    _repo_path("scripts/evaluation/k6", "module_root")
    modules = (
        COMPARISON_MODULES
        if plan["workload_kind"] == "comparison"
        else NFR_MODULES[plan["workload_kind"]]
    )
    if not isinstance(plan["module_hashes"], dict) or set(plan["module_hashes"]) != set(
        modules
    ):
        raise ValueError("module_hash_list_mismatch")
    for digest in plan["module_hashes"].values():
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise ValueError("invalid_module_hash")
    comparison = plan["comparison_inputs"]
    pilot_inputs, pilot_hashes = plan["pilot_inputs"], plan["pilot_input_hashes"]
    if plan["workload_kind"] == "comparison":
        if pilot_inputs is not None or pilot_hashes is not None:
            raise ValueError("unexpected_pilot_inputs")
        if not isinstance(comparison, dict) or set(comparison) != COMPARISON_INPUT_KEYS:
            raise ValueError("comparison_inputs_required")
        if (
            type(plan["cycle"]) is not int
            or plan["cycle"] not in (1, 2, 3)
            or plan["condition"] not in {"low", "normal", "burst"}
        ):
            raise ValueError("comparison_pair_selection_required")
    else:
        if comparison is not None:
            raise ValueError("unexpected_profile_specific_inputs")
        if plan["workload_kind"] == "exp05-pilot":
            if (
                plan["condition"] != "burst"
                or type(plan["cycle"]) is not int
                or plan["cycle"] not in (1, 2, 3)
            ):
                raise ValueError("pilot_cycle_and_condition_required")
            if (
                not isinstance(pilot_inputs, dict)
                or set(pilot_inputs) != PILOT_INPUT_KEYS
                or not isinstance(pilot_hashes, dict)
                or set(pilot_hashes) != PILOT_INPUT_HASH_KEYS
            ):
                raise ValueError("pilot_source_inputs_required")
            for key in PILOT_INPUT_KEYS:
                _repo_path(pilot_inputs[key], f"pilot_{key}")
            if any(
                not isinstance(value, str) or not HEX64.fullmatch(value)
                for value in pilot_hashes.values()
            ):
                raise ValueError("pilot_source_fingerprints_required")
        else:
            if plan["condition"] is not None or plan["cycle"] is not None:
                raise ValueError("unexpected_profile_specific_inputs")
            if pilot_inputs is not None or pilot_hashes is not None:
                raise ValueError("unexpected_pilot_inputs")
        if plan["workload_kind"] == "nfr-03":
            if (
                not isinstance(plan["fixture_path"], str)
                or not isinstance(plan["fixture_sha256"], str)
                or not HEX64.fullmatch(plan["fixture_sha256"])
            ):
                raise ValueError("nfr03_fixture_binding_required")
        elif plan["fixture_path"] is not None or plan["fixture_sha256"] is not None:
            raise ValueError("unexpected_fixture_binding")
    if plan["workload_kind"] == "comparison" and (
        plan["fixture_path"] is not None or plan["fixture_sha256"] is not None
    ):
        raise ValueError("unexpected_fixture_binding")
    if (
        plan["workload_kind"] != "nfr-03"
        and plan["workload_kind"] != "comparison"
        and (plan["fixture_path"] is not None or plan["fixture_sha256"] is not None)
    ):
        raise ValueError("unexpected_fixture_binding")
    return plan


def _validate_profile(plan: dict[str, Any], profile_bytes: bytes) -> dict[str, Any]:
    """Rebuild NFR profiles from reviewed repository inputs before session access."""
    profile = json.loads(profile_bytes)
    kind = plan["workload_kind"]
    if kind in {"nfr-01", "nfr-02"}:
        capacity = profile.get("capacity", {})
        expected = build_nfr_profile(
            kind,
            plan["configuration"],
            plan["run_id"],
            capacity.get("preAllocatedVUs"),
            capacity.get("maxVUs"),
        )
    elif kind == "nfr-03":
        fixture_path = _repo_path(plan["fixture_path"], "fixture")
        fixture_bytes = _read_bounded(fixture_path, 65_536)
        if _sha(fixture_bytes) != plan["fixture_sha256"]:
            raise ValueError("nfr03_fixture_hash_mismatch")
        fixture = json.loads(fixture_bytes)
        capacity = profile.get("capacity", {})
        expected = build_nfr03_profile(
            plan["run_id"],
            plan["configuration"],
            fixture,
            capacity.get("preAllocatedVUs"),
            capacity.get("maxVUs"),
        )
    elif kind == "exp05-pilot":
        if set(profile) != {
            "version",
            "purpose",
            "run_id",
            "configuration",
            "dataset_fingerprint",
            "case_bundle_sha256",
            "workload_sha256",
            "condition",
            "rate_rps",
            "warmup_rate_rps",
            "warmup_seconds",
            "measured_seconds",
            "drain_seconds",
            "timeout_seconds",
            "retries",
            "sequence_start",
            "capacity",
            "conditions",
            "cases",
            "execution_permitted",
            "nfr_accepted",
        }:
            raise ValueError("invalid_exp05_pilot_profile")
        workload = {
            "dataset_fingerprint": profile["dataset_fingerprint"],
            "cases": profile["cases"],
            "sequence_start": profile["sequence_start"],
            "rate_rps": 50,
            "warmup_rate_rps": 10,
            "warmup_seconds": 60,
            "measured_seconds": 120,
            "timeout_seconds": 5,
            "retries": 0,
            "capacity": profile["capacity"],
        }
        if (
            profile["purpose"] != "exp05-pilot-workload"
            or profile["run_id"] != plan["run_id"]
            or profile["configuration"] != plan["configuration"]
            or profile["dataset_fingerprint"].removeprefix("sha256:")
            != plan_target_dataset(plan)
            or profile["condition"] != "burst"
            or profile["rate_rps"] != 50
            or profile["warmup_rate_rps"] != 10
            or profile["warmup_seconds"] != 60
            or profile["measured_seconds"] != 120
            or profile["drain_seconds"] != 5
            or profile["timeout_seconds"] != 5
            or profile["retries"] != 0
            or type(profile["sequence_start"]) is not int
            or profile["sequence_start"] not in range(10)
            or not isinstance(profile["capacity"], dict)
            or not isinstance(profile["cases"], list)
            or len(profile["cases"]) != 10
            or hashlib.sha256(_canonical(profile["cases"]).encode()).hexdigest()
            != profile["case_bundle_sha256"]
            or hashlib.sha256(_canonical(workload).encode()).hexdigest()
            != profile["workload_sha256"]
            or profile["execution_permitted"] is not False
            or profile["nfr_accepted"] is not False
        ):
            raise ValueError("exp05_pilot_profile_binding_mismatch")
        expected = profile
    else:
        return cast(dict[str, Any], profile)
    if kind != "exp05-pilot" and _canonical(profile) != _canonical(expected):
        raise ValueError("profile_does_not_match_reviewed_builder")
    return cast(dict[str, Any], profile)


def plan_target_dataset(plan: dict[str, Any]) -> str:
    """Read only the frozen dataset digest already bound by the target plan."""
    target_path = _repo_path(plan["target_plan_path"], "target_plan")
    target = json.loads(_read_bounded(target_path, 100_000))
    fingerprint = target["revisions"]["dataset_fingerprint"]
    if not isinstance(fingerprint, str):
        raise ValueError("target_dataset_fingerprint_missing")
    return fingerprint.removeprefix("sha256:")


def _verify_modules(plan: dict[str, Any]) -> dict[str, bytes]:
    module_root = ROOT / "scripts/evaluation/k6"
    result = {}
    for name, expected_hash in plan["module_hashes"].items():
        data = _read_bounded(module_root / name, 2_000_000)
        if _sha(data) != expected_hash:
            raise ValueError("load_module_hash_mismatch")
        result[name] = data
    script_name = {
        "comparison": "comparison_load.js",
        "nfr-01": "nfr_load.js",
        "nfr-02": "nfr_load.js",
        "nfr-03": "nfr03_load.js",
        "exp05-pilot": "exp05_pilot_load.js",
    }[plan["workload_kind"]]
    if script_name not in result:
        raise ValueError("load_script_missing_from_module_bundle")
    verify_import_closure(result)
    return result


def verify_import_closure(modules: dict[str, bytes]) -> None:
    """Reject a staged workload missing a static relative JavaScript dependency.

    The source directory can hide missing bundle files during local execution;
    check the hash-bound staged module set itself before opening a session.
    All reviewed workload imports use one-line static named imports.
    """
    pattern = re.compile(rb"(?m)^\s*import[^\n]*\bfrom\s*['\"]\./([^'\"]+)['\"]")
    for content in modules.values():
        for dependency in pattern.findall(content):
            if dependency.decode("utf-8") not in modules:
                raise ValueError("load_module_dependency_missing")


def _write_new(path: Path, payload: bytes, mode: int = 0o600) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("write_failed")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _stage_nfr(
    plan: dict[str, Any], profile_bytes: bytes, modules: dict[str, bytes], run_dir: Path
) -> Path:
    stage = run_dir / "stage"
    os.mkdir(stage, 0o700)
    for name, data in modules.items():
        _write_new(stage / name, data, 0o400)
    _write_new(stage / "profile.json", profile_bytes, 0o400)
    os.chmod(stage, 0o500)
    return stage


def _comparison_stage(plan: dict[str, Any], run_dir: Path) -> Path:
    inputs = plan["comparison_inputs"]

    def get(key: str) -> Path:
        return _repo_path(inputs[key], key)

    paths = {
        key: get(key)
        for key in (
            "binding_plan",
            "corpus",
            "ordered_reference",
            "paired_plan",
            "workload_profile",
        )
    }
    source_dir = get("source_dir")
    schedule = get("schedule")
    module_hashes = plan["module_hashes"]
    parity = get("parity")
    parity_root = get("parity_evidence_root")
    staging_root = run_dir / "stage-root"
    os.mkdir(staging_root, 0o700)
    stage_run(
        paths,
        plan["cycle"],
        plan["run_id"],
        plan["profile_sha256"],
        source_dir,
        schedule,
        module_hashes,
        staging_root,
        parity_path=parity,
        parity_evidence_root=parity_root,
    )
    stage = staging_root / plan["run_id"]
    for path in stage.iterdir():
        if path.is_file():
            os.chmod(path, 0o400)
    os.chmod(stage, 0o500)
    return cast(Path, stage)


def _validate_pilot_sources(plan: dict[str, Any], profile: dict[str, Any]) -> None:
    """Revalidate the pilot's cases, sequence and parity against comparison inputs."""
    from scripts.evaluation.k6.comparison_declared_parity import (
        validate_declared_parity,
    )
    from scripts.evaluation.k6.comparison_run_preflight import validate_run_inputs

    paths = {
        key: _repo_path(plan["pilot_inputs"][key], f"pilot_{key}")
        for key in PILOT_INPUT_KEYS
    }
    source_bytes = {
        key: _read_bounded(paths[key], 10_000_000) for key in PILOT_INPUT_HASH_KEYS
    }
    if any(
        _sha(source_bytes[key]) != plan["pilot_input_hashes"][key]
        for key in PILOT_INPUT_HASH_KEYS
    ):
        raise ValueError("pilot_source_hash_mismatch")
    binding = json.loads(source_bytes["binding_plan"])
    reference = json.loads(source_bytes["ordered_reference"])
    paired = json.loads(source_bytes["paired_plan"])
    base_profile = json.loads(source_bytes["comparison_profile"])
    if hashlib.sha256(source_bytes["schedule"]).hexdigest() != paired["shared_inputs"][
        "schedule_sha256"
    ].removeprefix("sha256:"):
        raise ValueError("pilot_schedule_binding_mismatch")
    checked = validate_run_inputs(
        binding,
        source_bytes["corpus"],
        reference,
        paired,
        base_profile,
        plan["cycle"],
        profile_bytes=source_bytes["comparison_profile"],
        expected_profile_sha256=_sha(source_bytes["comparison_profile"]),
    )
    if (
        not checked.get("profile_hash_checked")
        or profile["cases"] != base_profile["cases"]
        or profile["sequence_start"] != base_profile["sequence_starts"]["burst"]
    ):
        raise ValueError("pilot_case_or_rotation_mismatch")
    if profile["dataset_fingerprint"].removeprefix("sha256:") != binding[
        "dataset_fingerprint"
    ].removeprefix("sha256:"):
        raise ValueError("pilot_dataset_binding_mismatch")
    parity = json.loads(source_bytes["parity"])
    validate_declared_parity(
        parity,
        binding,
        source_bytes["corpus"],
        reference,
        paired,
        evidence_root=paths["parity_evidence_root"],
    )


def _pilot_stage(
    plan: dict[str, Any], profile_bytes: bytes, modules: dict[str, bytes], run_dir: Path
) -> Path:
    """Validate reviewed source/parity inputs, then stage pilot bytes read-only."""
    profile = json.loads(profile_bytes)
    _validate_pilot_sources(plan, profile)
    stage = run_dir / "stage"
    os.mkdir(stage, 0o700)
    for name, data in modules.items():
        _write_new(stage / name, data, 0o400)
    _write_new(stage / "profile.json", profile_bytes, 0o400)
    os.chmod(stage, 0o500)
    return stage


def _prepare_child_env(
    plan: dict[str, Any],
    profile_path: Path,
    target: dict[str, Any],
    cookie: str,
    csrf: str | None,
) -> dict[str, str]:
    api_target = target["api_origin"] + "/api"
    env = {"PATH": os.environ.get("PATH", ""), "TMPDIR": str(profile_path.parent)}
    kind = plan["workload_kind"]
    if kind == "comparison":
        env.update(
            {
                "CLIP_REAL_RUN_MODE": "approved-runner",
                "CLIP_REAL_RUN_TARGET": api_target,
                "CLIP_REAL_RUN_ORIGIN": target["api_origin"],
                "CLIP_REAL_RUN_PROFILE": str(profile_path),
                "CLIP_REAL_RUN_ID": plan["run_id"],
                "CLIP_REAL_RUN_CONFIGURATION": plan["configuration"],
                "CLIP_REAL_RUN_CONDITION": plan["condition"],
                "CLIP_REAL_RUN_SESSION_COOKIE": cookie,
                "CLIP_COMPARISON_LOCAL_LOAD": "false",
            }
        )
    elif kind in {"nfr-01", "nfr-02"}:
        env.update(
            {
                "CLIP_NFR_REAL_RUN_MODE": "approved-runner",
                "CLIP_NFR_REAL_TARGET": api_target,
                "CLIP_NFR_REAL_ORIGIN": target["api_origin"],
                "CLIP_NFR_REAL_PROFILE": str(profile_path),
                "CLIP_NFR_REAL_RUN_ID": plan["run_id"],
                "CLIP_NFR_REAL_CONFIGURATION": plan["configuration"],
                "CLIP_REAL_RUN_SESSION_COOKIE": cookie,
                "CLIP_NFR_LOCAL_LOAD": "false",
            }
        )
    elif kind == "nfr-03":
        if not csrf:
            raise ValueError("nfr03_csrf_required")
        env.update(
            {
                "CLIP_NFR03_REAL_RUN_MODE": "approved-runner",
                "CLIP_NFR03_REAL_TARGET": api_target,
                "CLIP_NFR03_REAL_ORIGIN": target["api_origin"],
                "CLIP_NFR03_REAL_PROFILE": str(profile_path),
                "CLIP_NFR03_REAL_RUN_ID": plan["run_id"],
                "CLIP_NFR03_REAL_CONFIGURATION": plan["configuration"],
                "CLIP_REAL_RUN_SESSION_COOKIE": cookie,
                "CLIP_REAL_RUN_CSRF": csrf,
                "CLIP_NFR03_LOCAL_LOAD": "false",
            }
        )
    elif kind == "exp05-pilot":
        env.update(
            {
                "CLIP_EXP05_REAL_RUN_MODE": "approved-runner",
                "CLIP_EXP05_REAL_TARGET": api_target,
                "CLIP_EXP05_REAL_ORIGIN": target["api_origin"],
                "CLIP_EXP05_REAL_PROFILE": str(profile_path),
                "CLIP_EXP05_REAL_RUN_ID": plan["run_id"],
                "CLIP_EXP05_REAL_CONFIGURATION": plan["configuration"],
                "CLIP_REAL_RUN_SESSION_COOKIE": cookie,
                "CLIP_EXP05_LOCAL_LOAD": "false",
            }
        )
    return env


def execute(plan_path: Path, approval_path: Path) -> dict[str, Any]:
    """Validate, inspect, authenticate, then execute and retain one raw k6 run."""
    plan_path = _input_path(plan_path, "run_plan")
    approval_path = _input_path(approval_path, "action_approval")
    plan_bytes = _read_bounded(plan_path, 200_000)
    plan = validate_run_plan(json.loads(plan_bytes))
    approval_bytes = _read_bounded(approval_path, 30_000)
    validate_approval(plan, plan_bytes, json.loads(approval_bytes))
    target_path = _repo_path(plan["target_plan_path"], "target_plan")
    target_bytes = _read_bounded(target_path, 100_000)
    if _sha(target_bytes) != plan["target_plan_sha256"]:
        raise ValueError("target_plan_hash_mismatch")
    target = validate_target_plan(json.loads(target_bytes))
    if (
        target["run_id"] != plan["run_id"]
        or target["configuration"] != plan["configuration"]
        or target["expected_user_id"] != plan["expected_user_id"]
    ):
        raise ValueError("target_run_binding_mismatch")
    profile_path = _repo_path(plan["profile_path"], "profile")
    profile_bytes = _read_bounded(profile_path, 5_000_000)
    if _sha(profile_bytes) != plan["profile_sha256"]:
        raise ValueError("profile_hash_mismatch")
    profile = _validate_profile(plan, profile_bytes)
    modules = _verify_modules(plan)
    binary_path = _repo_path(plan["k6_binary_path"], "k6_binary")
    if _file_sha(binary_path, 2_000_000_000) != plan[
        "k6_binary_sha256"
    ] or not os.access(binary_path, os.X_OK):
        raise ValueError("k6_binary_hash_or_mode_mismatch")
    run_dir = _new_evidence_path(plan["evidence_directory"])
    validate_target_plan(target)
    os.mkdir(run_dir, 0o700)
    try:
        # Stage and validate every selected case, parity artifact and checked
        # module before inspecting a live target or accepting a session.
        if plan["workload_kind"] == "comparison":
            stage = _comparison_stage(plan, run_dir)
        elif plan["workload_kind"] == "exp05-pilot":
            stage = _pilot_stage(plan, profile_bytes, modules, run_dir)
        else:
            stage = _stage_nfr(plan, profile_bytes, modules, run_dir)
        script_name = {
            "comparison": "comparison_load.js",
            "nfr-01": "nfr_load.js",
            "nfr-02": "nfr_load.js",
            "nfr-03": "nfr03_load.js",
            "exp05-pilot": "exp05_pilot_load.js",
        }[plan["workload_kind"]]
        staged_profile = stage / (
            "profile.json" if plan["workload_kind"] != "comparison" else "profile.json"
        )
        if not staged_profile.exists():
            raise ValueError("staged_profile_missing")
        inspect_target(target)
        from scripts.evaluation.k6.lambda_concurrency import run_guard

        concurrency_guard = run_guard(target)
        if concurrency_guard:
            concurrency_guard()
        needs_csrf = plan["workload_kind"] == "nfr-03"
        session_value = os.environ.get("CLIP_REAL_RUN_SESSION_COOKIE", "")
        session = check_session_identity(target, session_value, needs_csrf=needs_csrf)
        csrf_token = session.pop("csrf_token", None)
        raw_path = run_dir / "raw.ndjson"
        _write_new(raw_path, b"")
        os.chmod(raw_path, 0o600)
        child_env = _prepare_child_env(
            plan, staged_profile, target, session_value, csrf_token
        )
        start = _utc_now()
        begin = time.monotonic()
        process = subprocess.Popen(
            [
                str(binary_path),
                "run",
                "--quiet",
                f"--out=json={raw_path}",
                str(stage / script_name),
            ],
            cwd=stage,
            env=child_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        timed_out = False
        oversized = False
        concurrency_guard_failed = False
        next_concurrency_check = time.monotonic() + 5
        while process.poll() is None:
            if time.monotonic() - begin > plan["maximum_duration_seconds"]:
                timed_out = True
            try:
                oversized = raw_path.stat().st_size > plan["maximum_raw_bytes"]
            except FileNotFoundError:
                oversized = True
            if concurrency_guard and time.monotonic() >= next_concurrency_check:
                try:
                    concurrency_guard()
                except Exception:
                    concurrency_guard_failed = True
                next_concurrency_check = time.monotonic() + 5
            if timed_out or oversized or concurrency_guard_failed:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                break
            time.sleep(0.2)
        return_code = process.wait()
        elapsed_seconds = time.monotonic() - begin
        if concurrency_guard:
            try:
                concurrency_guard()
            except Exception:
                concurrency_guard_failed = True
        child_env.clear()
        del session_value
        raw_hash, raw_size, output_exceeded = _hash_output(
            raw_path, plan["maximum_raw_bytes"]
        )
        oversized = oversized or output_exceeded
        os.chmod(raw_path, 0o400)
        receipt = {
            "format_version": 1,
            "run_id": plan["run_id"],
            "workload_kind": plan["workload_kind"],
            "configuration": plan["configuration"],
            "target_plan_sha256": _sha(target_bytes),
            "routing": target["routing"],
            "revisions": target["revisions"],
            "run_plan_sha256": _sha(plan_bytes),
            "profile_sha256": _sha(profile_bytes),
            "k6_binary_sha256": plan["k6_binary_sha256"],
            "raw_sha256": raw_hash,
            "raw_bytes": raw_size,
            "started_at_utc": start,
            "ended_at_utc": _utc_now(),
            "elapsed_seconds": elapsed_seconds,
            "process_exit_code": return_code,
            "timed_out": timed_out,
            "raw_limit_exceeded": oversized,
            "concurrency_guard_failed": concurrency_guard_failed,
            "execution_state": (
                "completed"
                if return_code == 0
                and not timed_out
                and not oversized
                and not concurrency_guard_failed
                else "failed_or_incomplete"
            ),
            "nfr_accepted": False,
            "measurement_validity_reviewed": False,
        }
        receipt_path = run_dir / "execution-receipt.json"
        _write_new(
            receipt_path,
            (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode(),
        )
        os.chmod(receipt_path, 0o400)
        directory_fd = os.open(run_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return {
            key: receipt[key]
            for key in (
                "run_id",
                "workload_kind",
                "configuration",
                "execution_state",
                "raw_sha256",
                "nfr_accepted",
            )
        }
    finally:
        csrf_token = None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument(
        "--execute", action="store_true", help="execute the explicitly approved run"
    )
    args = parser.parse_args()
    try:
        if not args.execute:
            raise ValueError("explicit_execute_flag_required")
        result = execute(args.plan, args.approval)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        code = (
            str(error)
            if isinstance(error, ValueError)
            and re.fullmatch(r"[a-z_]{1,80}", str(error))
            else "real_run_failed"
        )
        parser.exit(
            2,
            f"Real run refused or incomplete: {code}; inspect the private evidence directory if it was created\n",
        )


if __name__ == "__main__":
    raise SystemExit(main())
