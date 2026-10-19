# PD-08 unfinished work moves to pre-domain integration

**Date:** 2026-10-18

**Origin:** PD-09 local closeout; Mohit's explicit phase-transfer instruction.

## Question
Where will PD-08's remaining checks/reviews be completed after the verified
Stream 3 implementation and native macOS checkpoint?

## Options considered
- Keep the remaining work with Stream 3 before the integration phase.
- Hand the unfinished checkpoints to pre-domain integration while preserving
  their technical dependencies, exact checks, review and acceptance gates.

## Selected choice
Mohit explicitly shifted **all unfinished PD-08 work to the pre-domain
integration phase**. Stream 3's local delivery is a handoff, not a claim that
PD-08 is fully accepted. Published PD-08 source is `b6bade4` on
`predomain-database`; native PostgreSQL 18.6/dbmate 2.36.0 apply/head/repeat/
smoke/down-up/inventory checks and Step 7 documentation are human-verified.

| Original obligation | Integration-phase action / responsibility |
|---|---|
| PD-08 Step 2 affected-owner review | Integration owner coordinates Aditya (A), Suraj (B) and Rahul (D) on schema/constraints, public transaction/crypto/storage/cleanup compatibility. Resolve findings through reviewed changes; do not claim these owners have already approved. Mohit supports the database handoff. |
| PD-08 Step 4 container/platform verification | Integration owner uses an approved container-capable contributor environment to inspect actual PostgreSQL 18.6/dbmate 2.36.0 images/tools and platform/locale compatibility. No requirement to install a VM on Mohit's Mac is introduced. |
| PD-08 Steps 5–6 real local lifecycle | Run quiet Compose validation, startup, authenticated loopback TCP/SCRAM connectivity, stop/start named-volume persistence, and explicitly approved reset/recreate. Verify refusal of non-local/wrong targets. Synthetic CLI tests/native SQL tests do not substitute. |
| PD-08 Step 6 remaining SQL checks | Add/run multi-connection cases for final-image deletion/count, origin closure/create, sequence allocation, offer revision/retention and read/reminder/cleanup races, plus scoped query-plan checks. Re-run clean apply/head/repeat/down-up/smoke/inventory checks when code/schema/runtime changes require revalidation. |
| PD-08 Step 4 CI version agreement | PD-12/integration verifies the same PostgreSQL version in actual CI or records a reviewed compatibility reason; runs the applicable real gates. Planned configuration alone is not CI evidence. |
| Command/combined verification | PD-13 integrates the actual database commands and explicit PD-09 data tests into the common front door; PD-19 verifies clean-environment end-to-end foundation setup/checks. |
| Final PD-08 review/acceptance | Integration coordinates independent peer review, affected-owner acceptance, refreshed-main checks, human closeout and exact-revision merge approval. Preserve evidence and accepted main SHA before treating a dependency as accepted. |

The named integration contributor/operator and any bounded shared-path writer
must be recorded before implementation or environment actions. Until then,
responsibility is assigned to the **integration-owner role**, not an invented
person. Mohit remains the Stream 3 handoff contact. No external review request
has been sent by the agent.

## Rationale
Native checks and implemented source are available for integration, while real
container/CI/cross-owner acceptance work is unfinished. Recording the transfer
makes phase ownership explicit without losing or relabeling required checks.

## Implications
Carry these obligations in the canonical task/work log under their original
PD-08 step IDs. Integration intake must sequence the remaining PD-08 continuation
and consumer prerequisites before dependent technical actions; this transfer is
not blanket authorization to start blocked tasks or silently waive a dependency.
CI/common-command outputs remain PD-12/13 work. If the required ordering cannot
be satisfied, obtain a concrete bounded dependency/contract decision before
execution rather than claiming PD-08 complete.

**PD-19/PRE-00 cannot pass while any required transferred obligation remains
unresolved.** PD-09's local tooling can be verified under its already approved
schema-independent preparation exception; final review/upstream/main gates still
apply. DATA-READY/final adapters/loading/human labels remain SE-01 obligations.

The future backup/restore handoff from completed PD-08 Step 7 is unchanged:
PD-16's approved foundation capabilities and INT-01's actual managed-backup
restore/NFR-07 retain their own timing, privacy, cost and action approvals.
No cloud operation, tool installation, destructive reset/cleanup, commit,
publication, peer approval or merge is authorized merely by this phase transfer.

## Approver
Mohit (C), explicit instruction to move unfinished PD-08 tasks to pre-domain
integration. Integration execution, affected-owner approval and final acceptance
remain pending.

## Supersedes
Replaces the earlier scheduling assumption that Mohit would resume all deferred
PD-08 checks in Stream 3. Does not supersede technical requirements or tests.

## PD-16 bounded staging clarification — 2026-10-19

The user approved a [specific PD-16 foundation staging exception](shared-foundation-dependency-staging.md). It permits only the named health/private-SQL foundation increments, not domain integration, accepted database contracts, upstream completion or PRE-00. All original affected-owner/platform/hosted acceptance obligations above remain. This is a new bounded scheduling decision, not retrospective approval of earlier cloud actions.

## Integration test scope clarification — 2026-10-18

The integration contributor approved testing existing database integrity
constraints and query-plan/index diagnostics without inventing missing service
locking contracts. PD-08's storage checks cover image limits, conversation-pair
uniqueness, sequence allocation and offer consistency. Application races for
closure/create, offer cleanup and notification read/lease/replay require reviewed
DL-00/domain contracts and their owning implementation tasks. Keep these
obligations visible; storage-only passes do not accept application workflows.
Representative workload/query performance remains with domain verification;
forced index eligibility is diagnostic only. Other platform matrix rows and
PD-08 affected-owner/CI acceptance remain unchanged.
