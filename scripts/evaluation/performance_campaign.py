"""Freeze coverage-first run order and validate fresh-runtime receipts offline.

This module schedules evidence obligations, not AWS actions or workload approval.
Each entry still needs the canonical run plan, exact target and action approval.
Shared checks cannot be represented as additional performance repetitions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def build_campaign(
    prefix: str, *, nfr_repetitions: int = 3, main_first: bool = False
) -> dict[str, Any]:
    """Cover every applicable NFR before extra repetitions and the main comparison."""
    from scripts.evaluation.k6.real_target_preflight import RUN_ID

    if not isinstance(prefix, str) or not RUN_ID.fullmatch(prefix) or len(prefix) > 30:
        raise ValueError("invalid_campaign_prefix")
    if (
        type(nfr_repetitions) is not int
        or nfr_repetitions not in (1, 2, 3)
        or type(main_first) is not bool
    ):
        raise ValueError("invalid_campaign_repetition_policy")
    entries = []

    def entry(kind: str, config: str, repetition: int, **extra: Any) -> None:
        suffix = extra.get("condition", "check")
        entries.append(
            {
                "run_id": f"{prefix}-{kind}-{config.lower()}-r{repetition}-{suffix}",
                "kind": kind,
                "configuration": config,
                "repetition": repetition,
                **extra,
            }
        )

    for repetition in range(1, nfr_repetitions + 1):
        for kind in ("nfr-01", "nfr-02", "nfr-03", "nfr-05"):
            for config in (("A", "B") if repetition != 2 else ("B", "A")):
                entry(
                    kind,
                    config,
                    repetition,
                    stage="coverage" if repetition == 1 else "repeat",
                    fresh_runtime=kind != "nfr-05",
                    warmup_seconds=60,
                    measured_seconds=300,
                )
        if repetition == 1:
            for kind in ("nfr-04", "nfr-06"):
                for config in ("A", "B"):
                    entry(
                        kind,
                        config,
                        1,
                        stage="coverage",
                        fresh_runtime=False,
                        separate_action_approval=kind == "nfr-06",
                    )
            entry(
                "nfr-07",
                "shared",
                1,
                stage="coverage",
                fresh_runtime=False,
                separate_action_approval=True,
            )
    for cycle in (1, 2, 3):
        # Match comparison_pair_plan: finish low/normal/burst on the first
        # configuration, then the second; reverse the configuration order in c2.
        for config in (("A", "B") if cycle != 2 else ("B", "A")):
            for condition in ("low", "normal", "burst"):
                entry(
                    "comparison",
                    config,
                    cycle,
                    condition=condition,
                    stage="comparison",
                    fresh_runtime=True,
                    warmup_seconds=60,
                    measured_seconds=300,
                )
    if main_first:
        entries = [row for row in entries if row["kind"] == "comparison"] + [
            row for row in entries if row["kind"] != "comparison"
        ]
    return {
        "format_version": 1,
        "entries": entries,
        "nfr_repetitions": nfr_repetitions,
        "main_first": main_first,
        "nfr08_continuous_ledger": True,
        "database_and_pool_caches_reset": False,
        "pilot_policy": "three_lambda_only_repetitions_observe_reuse_no_forced_reset",
        "execution_authorized": False,
        "hold_after_lambda_pilots": True,
    }


def verify_fresh_receipt(receipt: Any, target: dict[str, Any], now: datetime) -> None:
    """Reject reused/partial/wrong-target preparation before formal traffic.

    Readiness is preparation evidence. Cold observations are collected afterward;
    their absence must prevent a claimed cold-start conclusion, not erase runs.
    """
    if not isinstance(receipt, dict) or (
        receipt.get("run_id") != target["run_id"]
        or receipt.get("configuration") != target["configuration"]
        or receipt.get("state") != "prepared_requires_log_confirmation"
        or receipt.get("target_plan_sha256") is None
    ):
        raise ValueError("fresh_runtime_receipt_required")
    old = receipt.get("old_ecs_tasks", [])
    rows = receipt.get("new_ecs_tasks", [])
    new = [row.get("task_arn") for row in rows if isinstance(row, dict)]
    if (
        len(old) != 2
        or len(set(old)) != 2
        or len(new) != 2
        or len(set(new)) != 2
        or not all(isinstance(x, str) and x for x in new)
        or set(old) & set(new)
    ):
        raise ValueError("fresh_tasks_not_proven")
    ended = datetime.fromisoformat(receipt["ended_at_utc"].replace("Z", "+00:00"))
    if ended.tzinfo is None or not 0 <= (now - ended).total_seconds() <= 900:
        raise ValueError("fresh_runtime_receipt_expired")
    if target["configuration"] == "B" and (
        receipt.get("lambda_reset_marker") != target["run_id"]
        or not receipt.get("lambda_revision")
    ):
        raise ValueError("fresh_lambda_not_prepared")
