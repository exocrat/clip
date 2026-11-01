"""Validate sanitized EXP-02 per-run evidence manifests without executing runs."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "data/evaluation/workloads/ecs-lambda-run-manifest.template.json"
SENSITIVE_KEY = re.compile(
    r"password|token|secret|private.?key|credential|cookie|authorization|"
    r"message.?content|contact|email|phone|dsn|api.?key",
    re.IGNORECASE,
)
SENSITIVE_VALUE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"\bAKIA[0-9A-Z]{16}\b|\bBearer\s+\S+|"
    r"[a-zA-Z][a-zA-Z0-9+.-]*://[^/@\s:]+:[^/@\s]+@|"
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b|"
    r"[?&](?:token|password|secret|access_key|signature|x-amz-signature|x-amz-credential)=",
    re.IGNORECASE,
)
HEX64 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")


def _shape(expected: Any, value: Any, path: str = "manifest") -> None:
    if isinstance(expected, dict):
        if not isinstance(value, dict) or set(value) != set(expected):
            raise ValueError(f"Unexpected object shape at {path}")
        for key, child in expected.items():
            if SENSITIVE_KEY.search(key) and not key.endswith("_excluded"):
                raise ValueError(f"Sensitive field name is forbidden at {path}.{key}")
            _shape(child, value[key], f"{path}.{key}")
    elif isinstance(expected, list):
        if not isinstance(value, list):
            raise ValueError(f"Expected an array at {path}")
        for index, child in enumerate(value):
            if not isinstance(child, str) or SENSITIVE_VALUE.search(child):
                raise ValueError(f"Unsafe array item at {path}[{index}]")
    elif expected is None:
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise ValueError(f"Unexpected value type at {path}")
        if isinstance(value, str) and SENSITIVE_VALUE.search(value):
            raise ValueError(f"Sensitive value pattern at {path}")
    elif type(value) is not type(expected):
        raise ValueError(f"Unexpected value type at {path}")
    elif isinstance(value, str) and SENSITIVE_VALUE.search(value):
        raise ValueError(f"Sensitive value pattern at {path}")


def _utc(value: object, name: str) -> datetime:
    if not isinstance(value, str) or not UTC.fullmatch(value):
        raise ValueError(f"{name} must be an ISO-8601 UTC timestamp ending in Z")
    return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")


def _no_nulls(value: Any, path: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _no_nulls(item, f"{path}.{key}")
    elif isinstance(value, list):
        if not value:
            raise ValueError(f"Captured manifest has an empty list at {path}")
        for index, item in enumerate(value):
            _no_nulls(item, f"{path}[{index}]")
    elif value is None or value == "":
        raise ValueError(f"Captured manifest has an empty value at {path}")


def validate_manifest(
    value: dict[str, Any], template: dict[str, Any]
) -> dict[str, Any]:
    """Check exact schema, frozen workload constants, and safe capture values."""
    _shape(template, value)
    if (
        value["schema_version"] != 1
        or value["manifest_kind"] != "ecs-lambda-run-capture"
    ):
        raise ValueError("Unsupported manifest schema")
    if value["measurement_state"] != "record_only_not_authorization":
        raise ValueError("Manifest cannot grant measurement authorization")
    if (
        value["workload"]["profile_path"]
        != "data/evaluation/workloads/ecs-lambda-comparison-schedule-v1.json"
    ):
        raise ValueError("Unexpected workload profile")
    if value["workload"]["request_mix_per_ten"] != {
        "browse": 5,
        "search": 3,
        "detail": 2,
    }:
        raise ValueError("Workload mix differs from the approved design")
    if [
        value["workload"][field]
        for field in (
            "warmup_seconds",
            "measured_seconds",
            "maximum_drain_seconds",
            "timeout_seconds",
            "retries",
        )
    ] != [60, 300, 5, 5, 0]:
        raise ValueError(
            "Workload timing/retry policy differs from the approved design"
        )

    state = value["manifest_state"]
    if state == "template":
        sections = ("run", "revisions", "dataset", "resource_telemetry", "evidence")
        if any(
            any(item is not None for item in value[section].values())
            for section in sections
        ):
            raise ValueError("Template must not contain run-specific values")
        if (
            any(
                item is not None
                for key, item in value["target"].items()
                if key != "resource_ids"
            )
            or value["target"]["resource_ids"]
        ):
            raise ValueError("Template must not contain target-specific values")
        if any(
            item is not None
            for key, item in value["cost_inputs"].items()
            if key != "currency"
        ):
            raise ValueError("Template must not contain run-specific cost values")
        placeholders = (
            "profile_sha256",
            "case_corpus_path",
            "case_corpus_sha256",
            "generator_version",
            "load_script_sha256",
            "run_command_reference",
            "sequence_start",
        )
        if any(value["workload"][key] is not None for key in placeholders):
            raise ValueError("Template must not contain run-specific workload values")
        return {"valid": True, "state": "template", "measurement_authorized": False}
    if state != "captured":
        raise ValueError("manifest_state must be template or captured")
    _no_nulls(value)

    run = value["run"]
    if not isinstance(run["run_id"], str) or not RUN_ID.fullmatch(run["run_id"]):
        raise ValueError("Invalid run ID")
    if run["configuration"] not in {"A", "B"} or run["condition"] not in {
        "low",
        "normal",
        "burst",
    }:
        raise ValueError("Invalid configuration or traffic condition")
    if type(run["repetition"]) is not int or not 1 <= run["repetition"] <= 3:
        raise ValueError("Invalid repetition number")
    _utc(run["planned_start_utc"], "run.planned_start_utc")
    actual_start = _utc(run["actual_start_utc"], "run.actual_start_utc")
    actual_end = _utc(run["actual_end_utc"], "run.actual_end_utc")
    if actual_end <= actual_start:
        raise ValueError("Run end must follow run start")

    required_nonempty = [
        value["run"]["owner_role"],
        value["target"]["account_id"],
        value["target"]["role_arn"],
        value["target"]["region"],
        value["target"]["environment_id"],
        value["target"]["entrypoint_reference"],
        value["target"]["resource_configuration_sha256"],
        value["revisions"]["application_revision"],
        value["revisions"]["image_digest"],
        value["revisions"]["frontend_revision"],
        value["revisions"]["migration_head"],
        value["revisions"]["api_contract_sha256"],
        value["dataset"]["logical_fingerprint"],
        value["dataset"]["index_fingerprint"],
        value["dataset"]["database_settings_sha256"],
        value["workload"]["profile_sha256"],
        value["workload"]["case_corpus_path"],
        value["workload"]["case_corpus_sha256"],
        value["workload"]["generator_version"],
        value["workload"]["load_script_sha256"],
        value["workload"]["run_command_reference"],
        value["resource_telemetry"]["ecs_artifact_reference"],
        value["resource_telemetry"]["ecs_artifact_sha256"],
        value["resource_telemetry"]["lambda_artifact_reference"],
        value["resource_telemetry"]["lambda_artifact_sha256"],
        value["resource_telemetry"]["postgres_artifact_reference"],
        value["resource_telemetry"]["postgres_artifact_sha256"],
        value["resource_telemetry"]["generator_artifact_reference"],
        value["resource_telemetry"]["generator_artifact_sha256"],
        value["cost_inputs"]["source_reference"],
        value["cost_inputs"]["source_sha256"],
        value["cost_inputs"]["interval_start_utc"],
        value["cost_inputs"]["interval_end_utc"],
        value["evidence"]["raw_output_reference"],
        value["evidence"]["raw_output_sha256"],
        value["evidence"]["derived_report_reference"],
        value["evidence"]["derived_report_sha256"],
        value["evidence"]["approval_record_reference"],
        value["evidence"]["cleanup_record_reference"],
        value["cost_inputs"]["billing_delay_note"],
    ]
    if any(not isinstance(item, str) or not item.strip() for item in required_nonempty):
        raise ValueError(
            "Captured manifest is missing a required run value or evidence reference"
        )
    evidence = value["evidence"]
    if (
        evidence["raw_output_reference"].strip()
        == evidence["derived_report_reference"].strip()
    ):
        raise ValueError("Raw output and derived report must use separate references")
    if not value["target"]["resource_ids"]:
        raise ValueError("Captured manifest must identify measured resources")
    if any(
        not HEX64.fullmatch(value["revisions"][field])
        for field in ("api_contract_sha256",)
    ):
        raise ValueError("Invalid SHA-256 fingerprint")
    for path in (
        "target.resource_configuration_sha256",
        "dataset.database_settings_sha256",
        "workload.profile_sha256",
        "workload.case_corpus_sha256",
        "workload.load_script_sha256",
        "resource_telemetry.ecs_artifact_sha256",
        "resource_telemetry.lambda_artifact_sha256",
        "resource_telemetry.postgres_artifact_sha256",
        "resource_telemetry.generator_artifact_sha256",
        "cost_inputs.source_sha256",
        "evidence.raw_output_sha256",
        "evidence.derived_report_sha256",
    ):
        section, field = path.split(".")
        if not HEX64.fullmatch(value[section][field]):
            raise ValueError(f"Invalid SHA-256 fingerprint at {path}")
    if not isinstance(
        value["dataset"]["logical_fingerprint"], str
    ) or not HEX64.fullmatch(
        value["dataset"]["logical_fingerprint"].removeprefix("sha256:")
    ):
        raise ValueError("Invalid logical dataset fingerprint")
    if (
        not isinstance(value["revisions"]["image_digest"], str)
        or not value["revisions"]["image_digest"].startswith("sha256:")
        or not HEX64.fullmatch(value["revisions"]["image_digest"])
    ):
        raise ValueError("Invalid image digest")
    if any(
        type(value["dataset"][key]) is not int
        for key in ("seed", "user_count", "listing_count")
    ):
        raise ValueError("Captured dataset seed and counts must be integers")
    if (
        value["dataset"]["user_count"] < 5000
        or value["dataset"]["listing_count"] < 1000
    ):
        raise ValueError("Dataset does not meet the approved reference workload size")
    if (
        type(value["workload"]["sequence_start"]) is not int
        or not 0 <= value["workload"]["sequence_start"] < 10
    ):
        raise ValueError("Invalid sequence start")
    cost_start = _utc(
        value["cost_inputs"]["interval_start_utc"], "cost_inputs.interval_start_utc"
    )
    cost_end = _utc(
        value["cost_inputs"]["interval_end_utc"], "cost_inputs.interval_end_utc"
    )
    if cost_end <= cost_start:
        raise ValueError("Cost interval end must follow its start")
    if (
        isinstance(value["cost_inputs"]["amount_before_credits"], bool)
        or not isinstance(value["cost_inputs"]["amount_before_credits"], (int, float))
        or value["cost_inputs"]["amount_before_credits"] < 0
    ):
        raise ValueError("Invalid measured cost input")
    if value["cost_inputs"]["currency"] != "USD":
        raise ValueError("Comparison cost currency must be USD")
    if not all(value["privacy"].values()):
        raise ValueError("Privacy exclusions must remain enabled")
    return {"valid": True, "state": "captured", "measurement_authorized": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        template = json.loads(TEMPLATE.read_text())
        value = json.loads(args.manifest.read_text())
        result = validate_manifest(value, template)
    except OSError, ValueError, KeyError, TypeError, json.JSONDecodeError:
        parser.exit(2, "Manifest validation failed; no run was started\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
