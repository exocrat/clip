"""Durable, single-operator campaign orchestration with injected reviewed actions.

The engine knows no AWS credentials or commands. An exact reviewed adapter owns
target checks, routing, bounded workload execution and cleanup. Test failures are
results; unsafe conditions stop the campaign. Journals and raw results are never
replaced when the operator resumes after a process interruption.
"""

from __future__ import annotations

from datetime import UTC, datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Protocol

TERMINAL = {"completed", "failed", "invalid", "blocked", "interrupted"}


class UnsafeStop(RuntimeError):
    """A real safety condition, unlike an ordinary unsuccessful measurement."""


class Adapter(Protocol):
    """Concrete, separately reviewed actions; recovery must not repeat traffic."""

    def run(self, entry: dict[str, Any], progress: Any) -> dict[str, Any]: ...
    def recover(self, entry: dict[str, Any], progress: Any) -> dict[str, Any]: ...
    def cleanup(self) -> dict[str, Any]: ...


class Journal:
    """Append/fsync transitions and atomically publish a small current status."""

    def __init__(self, root: Path, plan: dict[str, Any]):
        self.root, self.plan = root, plan
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if root.is_symlink():
            raise ValueError("campaign_root_symlink")
        self.path = root / "journal.ndjson"
        if self.path.is_symlink():
            raise ValueError("campaign_journal_symlink")
        self.latest: dict[str, dict[str, Any]] = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                row = json.loads(line)
                if row.get("run_id"):
                    self.latest[row["run_id"]] = row

    def append(self, run_id: str, state: str, **detail: Any) -> None:
        """Store only adapter-sanitized state; secrets never belong in progress."""
        row = {
            "at_utc": datetime.now(UTC).isoformat(),
            "run_id": run_id,
            "state": state,
            **detail,
        }
        fd = os.open(
            self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(fd, "a") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.latest[run_id] = row
        self.publish()

    def publish(self, **extra: Any) -> None:
        """Atomic snapshots let humans inspect progress while the runner writes."""
        rows = [
            {
                "run_id": e["run_id"],
                "kind": e["kind"],
                "configuration": e["configuration"],
                **self.latest.get(e["run_id"], {"state": "pending"}),
            }
            for e in self.plan["entries"]
        ]
        payload = {
            "format_version": 1,
            "updated_at_utc": datetime.now(UTC).isoformat(),
            "batch_id": self.plan["batch_id"],
            "entries": rows,
            "terminal_count": sum(r["state"] in TERMINAL for r in rows),
            "planned_count": len(rows),
            "nfr_accepted": False,
            **extra,
        }
        temporary = self.root / "status.json.tmp"
        temporary.write_text(json.dumps(payload, indent=2) + "\n")
        temporary.chmod(0o600)
        os.replace(temporary, self.root / "status.json")
        text = [
            f"# {self.plan['batch_id']}",
            "",
            f"Updated UTC: {payload['updated_at_utc']}",
            "",
            "| Run | State |",
            "|---|---|",
        ]
        text.extend(f"| {r['run_id']} | {r['state']} |" for r in rows)
        text.extend(
            [
                "",
                "Every attempt is retained. A completed run is not human NFR acceptance.",
                "Detailed status and evidence locations: status.json and per-run results.",
            ]
        )
        (self.root / "STATUS.md").write_text("\n".join(text) + "\n")


def verify_bundle(plan: dict[str, Any], approval: dict[str, Any], raw: bytes) -> None:
    """Require exact authorization and unchanged source before any action."""
    if (
        approval.get("approved") is not True
        or approval.get("plan_sha256") != hashlib.sha256(raw).hexdigest()
    ):
        raise ValueError("exact_campaign_approval_required")
    expires = datetime.fromisoformat(approval["expires_at_utc"].replace("Z", "+00:00"))
    if expires.tzinfo is None or datetime.now(UTC) >= expires:
        raise ValueError("campaign_approval_expired")
    ids = [entry["run_id"] for entry in plan["entries"]]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("unique_campaign_runs_required")
    for source, digest in plan["bound_files"].items():
        p = Path(source)
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ValueError("campaign_source_changed")


def run_campaign(
    plan: dict[str, Any],
    adapter: Adapter,
    root: Path,
    *,
    monotonic: Any = time.monotonic,
) -> dict[str, Any]:
    """Continue independent entries after bad results, never after unsafe state.

    Supervised plans can stop on invalid preparation for immediate operator
    repair instead of consuming the remaining queue. Ordinary measured failures
    remain results. The adapter handles bounded monitoring retries and exact action
    approvals. A resumed in-progress entry uses observation/evidence recovery;
    it must not quietly rerun a completed or interrupted workload.
    """
    journal = Journal(root, plan)
    lock = os.open(
        root / "operator.lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600
    )
    started = monotonic()
    stopped = False
    acquired = False
    attention_required = False
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquired = True
        journal.publish(campaign_state="running")
        for entry in plan["entries"]:
            run = entry["run_id"]
            if journal.latest.get(run, {}).get("state") in TERMINAL:
                continue
            if monotonic() - started > plan["maximum_seconds"]:
                journal.append(run, "blocked", reason="campaign_time_cap")
                stopped = True
                break
            previous = journal.latest.get(run)

            def progress(stage: str, **detail: Any) -> None:
                journal.append(run, "running", stage=stage, **detail)

            try:
                if previous:
                    result = adapter.recover(entry, progress)
                else:
                    progress("starting")
                    result = adapter.run(entry, progress)
                if result.get("state") not in TERMINAL:
                    raise ValueError("terminal_result_required")
                journal.append(run, **result)
                if result["state"] == "invalid" and plan.get("stop_on_invalid", False):
                    attention_required = True
                    break
            except UnsafeStop as error:
                journal.append(run, "interrupted", reason=str(error))
                stopped = True
                break
            except Exception as error:
                # Adapter exceptions carry no provider prose into the journal.
                journal.append(run, "invalid", failure_type=type(error).__name__)
                if plan.get("stop_on_invalid", False):
                    attention_required = True
                    break
        return {
            "campaign_state": (
                "safety_stopped"
                if stopped
                else "operator_attention_required" if attention_required else "finished"
            ),
            "planned": len(plan["entries"]),
            "recorded": len(journal.latest),
        }
    finally:
        if acquired:
            try:
                cleanup = adapter.cleanup()
            except Exception as error:
                cleanup = {"complete": False, "failure_type": type(error).__name__}
            journal.publish(
                campaign_state=(
                    "safety_stopped"
                    if stopped
                    else (
                        "operator_attention_required"
                        if attention_required
                        else "finished"
                    )
                ),
                cleanup=cleanup,
            )
        os.close(lock)
