# PD-16 Step 13 — lifecycle and retention closeout

**Status:** Operational evidence reviewed; user explicitly named Aditya as current operator. User accepted the exact 96-hour idle deadline below. No new cloud action authorized here.

## Audit and established evidence

Step 13 is coherent with DEC-03/DEC-10/DEC-11, the shared-test runbook and cleanup policy. Preserve phase `service`, unchanged ephemeral credential versions, managed scaling and separate exact-action approvals. User explicitly selected shutdown before Step 12; the budget review subsequently ran and is committed in `dfb61ec`, with approximate recent-run cost review subsequently accepted under [DEC-12](../../../decisions/foundation-cost-review-precision.md).

- Approved run: 2026-10-19 17:17:08–19:17:08 UTC; Aditya is now explicitly named current operator; broad human access and `Owner=shared-team` explicitly accepted.
- Initial zero-host foundation scaled to one host for the API; approved shutdown returned tasks/ASG desired/hosts to zero, original host terminated. [Capacity/lifecycle evidence](compute-stop-result.json).
- Original RDS was stopped, restarted with approval, used by successful fixed setup/probe, then stopped again at **2026-10-19 18:23:35 UTC**, same resource ID. [SQL evidence](database-retry-result.json). No further restart is proposed to reproduce these results. A later same-service re-enable plan has not been executed and is not claimed as tested.
- Applied state snapshot: one-day RDS backup retention, deletion protection on, no final snapshot selected for disposable teardown; seven-day API log retention; immutable ECR tags. Existing images, credentials, DB storage and task definitions retained; NAT/storage/logs/backend remain billable. This reads the applied snapshot, not a fresh independent cloud inventory.
- Resume: separately approve RDS start, then prepare/review/apply a new exact desired-count-one service plan with unchanged credentials/images and a new budget/window. Stop path already verified. [Operator runbook](../../../environment/shared-test-rds-operations.md).
- Full teardown: separately approved protection-disable plan/apply, explicitly approved manual ECR-image cleanup, then fresh destroy plan/apply; preserve PD-15 backend and versions. Do not automate/execute teardown from this document.

## Accepted closeout inputs

1. **Accountable operator — resolved:** user explicitly named **Aditya** as operator for now; use the existing team roster/contact references for handoff, and update the assignment if responsibility changes. No identity was inferred from a stream/IAM label; `Owner=shared-team` remains unchanged.
2. **Exact idle-clock anchor/deadline — resolved:** user accepted **2026-10-19 18:23:35 UTC → 2026-10-23 18:23:35 UTC** (96 hours; **23:53:35 IST on October 23**). This supersedes the earlier unaccepted first-apply-based proposal. Aditya initiates the separately reviewed cleanup process by this deadline if no new approved run occurs; there is no automatic destructive action or standing apply approval. A later approved run must update the idle clock. Existing date-only review/tag October 23 is consistent and needs no retagging.

RDS may auto-restart after seven stopped days; no automation suppresses that. Operational lifecycle and Step 11/14 handoff are human-verified; exact recent-run billing reconciliation is no longer required under DEC-12; upstream/owner/platform/peer acceptance remains separate. PD-16 operational scope is closed by explicit user direction; PD-17 documentation is authorized under DEC-07, while PRE-00/domain work remains unaccepted.
