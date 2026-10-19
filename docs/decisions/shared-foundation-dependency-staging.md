# DEC-07 — Bounded shared-foundation dependency staging

**Date:** 2026-10-19

**Origin:** PD-16 audit R02; approval of decision bundle B.

## Question
Can the named health-only foundation increments proceed while upstream acceptance remains pending?

## Options considered

- Wait for all upstream acceptance before any further PD-16 work.
- Permit only locally supported foundation increments, preserving all real acceptance and cloud gates.

## Selected choice
The user approved the bounded second option. PD-16 may prepare foundation artifacts and, only after separate exact action approval, provision the reviewed base and perform API process-liveness/private SQL checks against locally verified interfaces/configuration: PD-05 health skeleton, PD-06 core conventions, PD-08 PostgreSQL 18.6/local lifecycle, PD-12/13 local shared checks, and PD-15 exact backend/locking handoff. SQL setup is limited to the dedicated probe role and test-database grants; it does not validate domain schemas/migrations/contracts.

The already recorded base apply is historical evidence, not retrospectively authorized by this decision. No domain implementation, NFR result, upstream task completion, PRE-00 or blanket dependency waiver is granted. The hard task acceptance dependencies remain unchanged.

## Rationale
These increments use the existing health skeleton and managed database primitives; native teammate platform runs and domain-owner acceptance do not become successful merely because those primitives are deployed.

## Implications
Preserve these original obligations in the work log:

- PD-08: native Linux AMD64/macOS container/platform checks, affected-owner schema/transaction/security acceptance and current hosted CI acceptance.
- PD-09: accepted PD-08 upstream and current independent/hosted acceptance; command/data-test wiring is implemented locally. Final data/adapters/labels remain SE-01/DATA-READY.
- PD-12: published revised policy, passing current head/base hosted CI and independent review; no historical run accepts this revision.
- PD-13: native teammate platform verification, upstream/peer/main acceptance and current hosted checks.
- PD-15: independent peer review and accepted main handoff of backend/migration outputs.

Each deployment, upload, state action and cleanup still requires its own exact approval. Stop if a staged increment depends on an unreviewed interface or an unavailable real prerequisite. Record failures and return to the original checks when their prerequisites arrive. PD-19/PRE-00 cannot pass with any required gate unresolved.

## Approver
User in the current session; personal name not recorded.

## Supersedes
Only the requirement to await full upstream acceptance before these specifically named PD-16 increments; no upstream requirement or acceptance check is removed. Complements [the PD-08 integration handoff](database-integration-handoff.md).
