"""Check a completed EXP-08 resource disposition record without cloud calls.

The checker validates evidence completeness and retained-cost links. It does
not inspect AWS or approve deletion, so its output never proves live cleanup.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}\Z")
AMOUNT = re.compile(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?\Z")
TOP_KEYS = {
    "format_version",
    "purpose",
    "run_id",
    "approved_plan_sha256",
    "inventory_source_reference",
    "inventory_source_sha256",
    "observed_at_utc",
    "expected_resource_ids",
    "unplanned_resource_ids",
    "resources",
}
RESOURCE_KEYS = {
    "resource_id",
    "service",
    "disposition",
    "observed_state",
    "verified",
    "evidence_reference",
    "evidence_sha256",
    "owner",
    "expiry_utc",
    "estimated_remaining_cost_usd",
    "cost_ledger_entry_id",
}


def _time(value: Any, *, nullable: bool = False) -> datetime | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid_cleanup_timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("invalid_cleanup_timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("cleanup_timestamp_must_be_utc")
    return parsed


def validate_record(value: Any) -> dict[str, Any]:
    """Require exact inventory coverage and documented resource disposition."""
    if not isinstance(value, dict) or set(value) != TOP_KEYS:
        raise ValueError("invalid_cleanup_record_shape")
    if (
        type(value["format_version"]) is not int
        or value["format_version"] != 1
        or value["purpose"] != "exp08-cleanup-accounting"
        or not isinstance(value["run_id"], str)
        or not IDENTIFIER.fullmatch(value["run_id"])
        or not isinstance(value["approved_plan_sha256"], str)
        or not SHA256.fullmatch(value["approved_plan_sha256"])
        or not isinstance(value["inventory_source_reference"], str)
        or not value["inventory_source_reference"].strip()
        or not isinstance(value["inventory_source_sha256"], str)
        or not SHA256.fullmatch(value["inventory_source_sha256"])
    ):
        raise ValueError("invalid_cleanup_record_binding")
    observed = _time(value["observed_at_utc"])
    expected = value["expected_resource_ids"]
    unplanned = value["unplanned_resource_ids"]
    rows = value["resources"]
    if (
        not isinstance(expected, list)
        or not expected
        or any(
            not isinstance(item, str) or not IDENTIFIER.fullmatch(item)
            for item in expected
        )
        or len(set(expected)) != len(expected)
    ):
        raise ValueError("approved_resource_inventory_required")
    if not isinstance(unplanned, list) or any(
        not isinstance(item, str) or not IDENTIFIER.fullmatch(item)
        for item in unplanned
    ):
        raise ValueError("invalid_unplanned_resource_inventory")
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise ValueError("cleanup_resource_coverage_mismatch")
    found: set[str] = set()
    complete = not unplanned
    retained_costs: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != RESOURCE_KEYS:
            raise ValueError("invalid_resource_disposition_shape")
        resource_id = row["resource_id"]
        if (
            not isinstance(resource_id, str)
            or resource_id not in expected
            or resource_id in found
        ):
            raise ValueError("unknown_or_duplicate_resource")
        found.add(resource_id)
        if (
            not isinstance(row["service"], str)
            or not row["service"].strip()
            or row["disposition"] not in {"removed", "retained", "shared"}
        ):
            raise ValueError("invalid_resource_disposition")
        if not isinstance(row["observed_state"], str) or row["observed_state"] not in {
            "absent",
            "present",
            "shared",
        }:
            raise ValueError("invalid_observed_resource_state")
        if type(row["verified"]) is not bool:
            raise ValueError("resource_verification_flag_required")
        if (
            not isinstance(row["evidence_reference"], str)
            or not row["evidence_reference"].strip()
            or not isinstance(row["evidence_sha256"], str)
            or not SHA256.fullmatch(row["evidence_sha256"])
        ):
            raise ValueError("cleanup_observation_evidence_required")
        if row["disposition"] == "removed" and row["observed_state"] != "absent":
            raise ValueError("removed_resource_still_present")
        if row["disposition"] == "retained" and row["observed_state"] != "present":
            raise ValueError("retained_resource_not_confirmed_present")
        if row["disposition"] == "shared" and row["observed_state"] != "shared":
            raise ValueError("shared_resource_not_confirmed")
        cost = row["estimated_remaining_cost_usd"]
        ledger_id = row["cost_ledger_entry_id"]
        if not isinstance(cost, str) or not AMOUNT.fullmatch(cost):
            raise ValueError("retained_cost_estimate_required")
        if row["disposition"] in {"retained", "shared"}:
            _time(row["expiry_utc"])
            if (
                not isinstance(row["owner"], str)
                or not row["owner"].strip()
                or not isinstance(ledger_id, str)
                or not IDENTIFIER.fullmatch(ledger_id)
            ):
                raise ValueError(
                    "retained_resource_owner_expiry_and_cost_link_required"
                )
            retained_costs.append(
                {
                    "resource_id": resource_id,
                    "cost_ledger_entry_id": ledger_id,
                    "estimated_remaining_cost_usd": cost,
                }
            )
        elif (
            row["owner"] is not None
            or row["expiry_utc"] is not None
            or ledger_id is not None
            or cost != "0"
        ):
            raise ValueError("removed_resource_cannot_have_retained_liability")
        complete = complete and row["verified"] is True
    if found != set(expected):
        raise ValueError("cleanup_resource_coverage_mismatch")
    if observed is None:
        raise ValueError("invalid_cleanup_timestamp")
    return {
        "format_version": 1,
        "purpose": "exp08-cleanup-accounting-preview",
        "run_id": value["run_id"],
        "approved_plan_sha256": value["approved_plan_sha256"],
        "inventory_source_sha256": value["inventory_source_sha256"],
        "observed_at_utc": observed.isoformat().replace("+00:00", "Z"),
        "expected_resource_count": len(expected),
        "verified_resource_count": sum(row["verified"] is True for row in rows),
        "unplanned_resources": unplanned,
        "retained_resource_liabilities": retained_costs,
        "cleanup_evidence_complete_preview": complete,
        "live_inventory_independently_verified": False,
        "cleanup_authorized": False,
        "nfr_accepted": False,
        "human_review_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("record", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.record.stat().st_size > 5_000_000:
            raise ValueError("cleanup_record_too_large")
        record = json.loads(args.record.read_text(encoding="utf-8"))
        report = validate_record(record)
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(report, output, sort_keys=True, indent=2)
            output.write("\n")
        return 0 if report["cleanup_evidence_complete_preview"] else 1
    except OSError, ValueError, TypeError, json.JSONDecodeError:
        parser.exit(2, "Cleanup record refused; no cloud action was performed\n")


if __name__ == "__main__":
    raise SystemExit(main())
