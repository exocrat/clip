"""Validate and summarize the append-only project cost ledger; no cloud calls."""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
from typing import Any

PROJECT_LIMIT_USD = Decimal("200")
AMOUNT = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]{1,6})?$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
LEDGER_KEYS = {
    "format_version",
    "ledger_id",
    "final_reconciliation",
    "project_scope_complete",
    "billing_checked_through",
    "entries",
}
ENTRY_KEYS = {
    "entry_id",
    "provider",
    "kind",
    "category",
    "resource_scope",
    "period_start",
    "period_end",
    "amount_usd",
    "credits_usd",
    "source_reference",
    "source_sha256",
    "price_date",
    "estimate_basis",
    "replaces_estimate_id",
}


def _date(value: Any, *, nullable: bool = False) -> date | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid_ledger_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("invalid_ledger_date") from None
    if parsed.isoformat() != value:
        raise ValueError("invalid_ledger_date")
    return parsed


def _amount(value: Any) -> Decimal:
    if not isinstance(value, str) or not AMOUNT.fullmatch(value):
        raise ValueError("invalid_ledger_amount")
    try:
        return Decimal(value)
    except InvalidOperation:
        raise ValueError("invalid_ledger_amount") from None


def validate_ledger(ledger: Any) -> dict[str, Any]:
    """Validate entries, deduplicate source lines, and settle estimates once."""
    if not isinstance(ledger, dict) or set(ledger) != LEDGER_KEYS:
        raise ValueError("invalid_ledger_shape")
    if (
        type(ledger["format_version"]) is not int
        or ledger["format_version"] != 1
        or not isinstance(ledger["ledger_id"], str)
        or not IDENTIFIER.fullmatch(ledger["ledger_id"])
        or type(ledger["final_reconciliation"]) is not bool
        or type(ledger["project_scope_complete"]) is not bool
        or not isinstance(ledger["entries"], list)
    ):
        raise ValueError("invalid_ledger_metadata")
    checked_through = _date(ledger["billing_checked_through"], nullable=True)
    entries: dict[str, dict[str, Any]] = {}
    sources: set[tuple[str, str]] = set()
    estimate_keys: set[tuple[str, str, str, str]] = set()
    coverage: dict[tuple[str, str, str], list[tuple[str, date, date]]] = {}
    for row in ledger["entries"]:
        if not isinstance(row, dict) or set(row) != ENTRY_KEYS:
            raise ValueError("invalid_cost_entry_shape")
        entry_id = row["entry_id"]
        if (
            not isinstance(entry_id, str)
            or not IDENTIFIER.fullmatch(entry_id)
            or entry_id in entries
        ):
            raise ValueError("duplicate_or_invalid_entry_id")
        if row["provider"] not in {"aws", "other"} or row["kind"] not in {
            "actual",
            "unbilled_estimate",
            "retained_resource_estimate",
        }:
            raise ValueError("invalid_cost_entry_kind")
        if not all(
            isinstance(row[key], str) and row[key].strip()
            for key in ("category", "resource_scope", "source_reference")
        ):
            raise ValueError("invalid_cost_entry_reference")
        start, end = _date(row["period_start"]), _date(row["period_end"])
        if start is None or end is None:
            raise ValueError("invalid_cost_period")
        if start > end:
            raise ValueError("invalid_cost_period")
        coverage_key = (row["provider"], row["category"], row["resource_scope"])
        coverage.setdefault(coverage_key, []).append((entry_id, start, end))
        amount = _amount(row["amount_usd"])
        credits = _amount(row["credits_usd"])
        if credits > amount or (row["provider"] != "aws" and credits != 0):
            raise ValueError("invalid_credit_amount")
        source_hash = row["source_sha256"]
        if not isinstance(source_hash, str) or not SHA256.fullmatch(source_hash):
            raise ValueError("source_fingerprint_required")
        source_key = (source_hash, row["source_reference"])
        if source_key in sources:
            raise ValueError("duplicate_source_line")
        sources.add(source_key)
        price_date = _date(row["price_date"], nullable=True)
        basis = row["estimate_basis"]
        replaced = row["replaces_estimate_id"]
        if row["kind"] == "actual":
            if price_date is not None or basis is not None:
                raise ValueError("actual_entry_has_estimate_fields")
            if replaced is not None and (
                not isinstance(replaced, str) or not IDENTIFIER.fullmatch(replaced)
            ):
                raise ValueError("invalid_replaced_estimate_id")
        else:
            if (
                credits != 0
                or price_date is None
                or not isinstance(basis, str)
                or not basis.strip()
                or replaced is not None
            ):
                raise ValueError("incomplete_estimate_basis")
            estimate_key = (
                row["kind"],
                row["resource_scope"],
                start.isoformat(),
                end.isoformat(),
            )
            if estimate_key in estimate_keys:
                raise ValueError("duplicate_period_estimate")
            estimate_keys.add(estimate_key)
        entries[entry_id] = {
            **row,
            "_start": start,
            "_end": end,
            "_amount": amount,
            "_credits": credits,
            "_price_date": price_date,
        }

    for entry_id, period_rows in coverage.items():
        periods = sorted(period_rows, key=lambda row: (row[1], row[2], row[0]))
        for index, (left_id, left_start, left_end) in enumerate(periods):
            for right_id, right_start, right_end in periods[index + 1 :]:
                if right_start > left_end:
                    break
                linked_pair = (
                    entries[left_id]["replaces_estimate_id"] == right_id
                    or entries[right_id]["replaces_estimate_id"] == left_id
                )
                if (
                    not linked_pair
                    or left_start != right_start
                    or left_end != right_end
                ):
                    raise ValueError("overlapping_cost_periods")

    settled: dict[str, str] = {}
    for entry_id, row in entries.items():
        replaced = row["replaces_estimate_id"]
        if replaced is None:
            continue
        estimate = entries.get(replaced)
        if (
            estimate is None
            or row["kind"] != "actual"
            or estimate["kind"]
            not in {"unbilled_estimate", "retained_resource_estimate"}
            or estimate["provider"] != row["provider"]
            or estimate["category"] != row["category"]
            or estimate["resource_scope"] != row["resource_scope"]
            or estimate["period_start"] != row["period_start"]
            or estimate["period_end"] != row["period_end"]
            or replaced in settled
        ):
            raise ValueError("invalid_estimate_replacement")
        settled[replaced] = entry_id

    actual_total = sum(
        (row["_amount"] for row in entries.values() if row["kind"] == "actual"),
        Decimal(0),
    )
    outstanding_estimates = sum(
        (
            row["_amount"]
            for key, row in entries.items()
            if row["kind"] != "actual" and key not in settled
        ),
        Decimal(0),
    )
    aws_credits = sum(
        (
            row["_credits"]
            for row in entries.values()
            if row["provider"] == "aws" and row["kind"] == "actual"
        ),
        Decimal(0),
    )
    exposure = actual_total + outstanding_estimates
    evidence_complete = bool(entries) and all(
        row["source_reference"] and SHA256.fullmatch(row["source_sha256"])
        for row in entries.values()
    )
    budget_headroom = PROJECT_LIMIT_USD - exposure
    final = ledger["final_reconciliation"]
    if final and checked_through is None:
        raise ValueError("final_billing_period_required")
    if final and not ledger["project_scope_complete"]:
        raise ValueError("final_project_scope_incomplete")
    return {
        "ledger_id": ledger["ledger_id"],
        "entry_count": len(entries),
        "actual_gross_usd": str(actual_total),
        "outstanding_unbilled_and_retained_estimates_usd": str(outstanding_estimates),
        "project_cost_exposure_usd": str(exposure),
        "aws_credits_used_usd": str(aws_credits),
        "project_budget_limit_usd": str(PROJECT_LIMIT_USD),
        "project_budget_headroom_usd": str(budget_headroom),
        "evidence_complete": evidence_complete,
        "below_project_budget_preview": exposure < PROJECT_LIMIT_USD,
        "final_reconciliation_requested": final,
        "project_scope_complete": ledger["project_scope_complete"],
        "billing_checked_through": (
            checked_through.isoformat() if checked_through else None
        ),
        "nfr08_ready_for_human_review": bool(
            final
            and ledger["project_scope_complete"]
            and evidence_complete
            and exposure < PROJECT_LIMIT_USD
        ),
        "nfr08_accepted": False,
        "credits_are_not_subtracted_from_project_cost": True,
    }


def _read(path: Path) -> Any:
    if path.stat().st_size > 10_000_000:
        raise ValueError("ledger_too_large")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("ledger", type=Path)
    parser.add_argument(
        "--entry", type=Path, help="append one validated entry into a new ledger file"
    )
    parser.add_argument(
        "--output", type=Path, help="new ledger path, required with --entry"
    )
    args = parser.parse_args()
    try:
        ledger = _read(args.ledger)
        if args.entry or args.output:
            if not args.entry or not args.output:
                raise ValueError("entry_and_output_required_together")
            entry = _read(args.entry)
            if isinstance(entry, dict) and set(entry) == {"entry"}:
                entry = entry["entry"]
            candidate = {**ledger, "entries": [*ledger["entries"], entry]}
            validate_ledger(candidate)
            with args.output.open("x", encoding="utf-8") as output:
                output.write(json.dumps(candidate, indent=2, sort_keys=True) + "\n")
            ledger = candidate
        report = validate_ledger(ledger)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["evidence_complete"] else 1
    except OSError, ValueError, TypeError, json.JSONDecodeError:
        parser.exit(2, "Cost ledger refused; no files were changed\n")


if __name__ == "__main__":
    raise SystemExit(main())
