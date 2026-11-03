from __future__ import annotations

import copy
import hashlib

import pytest

from scripts.evaluation.exp08_cleanup import validate_record


def _record() -> dict:
    return {
        "format_version": 1,
        "purpose": "exp08-cleanup-accounting",
        "run_id": "exp08-run-001",
        "approved_plan_sha256": "a" * 64,
        "inventory_source_reference": "reviewed-inventory.json",
        "inventory_source_sha256": hashlib.sha256(b"inventory").hexdigest(),
        "observed_at_utc": "2026-11-03T10:00:00Z",
        "expected_resource_ids": [
            "arn:aws:ecs:region:account:service/cluster/service",
            "db-copy-001",
        ],
        "unplanned_resource_ids": [],
        "resources": [
            {
                "resource_id": "arn:aws:ecs:region:account:service/cluster/service",
                "service": "ecs",
                "disposition": "removed",
                "observed_state": "absent",
                "verified": True,
                "evidence_reference": "post-cleanup-service-list.json",
                "evidence_sha256": "b" * 64,
                "owner": None,
                "expiry_utc": None,
                "estimated_remaining_cost_usd": "0",
                "cost_ledger_entry_id": None,
            },
            {
                "resource_id": "db-copy-001",
                "service": "rds",
                "disposition": "retained",
                "observed_state": "present",
                "verified": True,
                "evidence_reference": "post-cleanup-rds-list.json",
                "evidence_sha256": "c" * 64,
                "owner": "Suraj",
                "expiry_utc": "2026-11-10T00:00:00Z",
                "estimated_remaining_cost_usd": "1.25",
                "cost_ledger_entry_id": "cost-retained-db-001",
            },
        ],
    }


def test_cleanup_preview_covers_resources_and_retained_costs() -> None:
    result = validate_record(_record())
    assert result["cleanup_evidence_complete_preview"] is True
    assert result["expected_resource_count"] == 2
    assert result["retained_resource_liabilities"] == [
        {
            "resource_id": "db-copy-001",
            "cost_ledger_entry_id": "cost-retained-db-001",
            "estimated_remaining_cost_usd": "1.25",
        }
    ]
    assert result["live_inventory_independently_verified"] is False
    assert result["cleanup_authorized"] is False


def test_cleanup_refuses_missing_planned_resource() -> None:
    record = _record()
    record["resources"].pop()
    with pytest.raises(ValueError, match="cleanup_resource_coverage_mismatch"):
        validate_record(record)


def test_cleanup_refuses_resource_marked_removed_but_present() -> None:
    record = copy.deepcopy(_record())
    record["resources"][0]["observed_state"] = "present"
    with pytest.raises(ValueError, match="removed_resource_still_present"):
        validate_record(record)


def test_cleanup_requires_cost_link_for_retained_resource() -> None:
    record = copy.deepcopy(_record())
    record["resources"][1]["cost_ledger_entry_id"] = None
    with pytest.raises(
        ValueError, match="retained_resource_owner_expiry_and_cost_link_required"
    ):
        validate_record(record)
