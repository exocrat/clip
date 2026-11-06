# CI integration sequencing

**Date:** 2026-10-19

**Origin:** PD-12 task-definition audit before Step 1.

## Question
How can CI and its local parity check be implemented without circular sequencing?

## Options considered
- Wait for final upstream acceptance and the PD-13 aggregate, leaving circular gates.
- Permit bounded integration preparation and create the minimal shared check runner in PD-12.

## Selected choice
PD-12 may implement and check CI against merged PD-08/09 source (main
`e4d7551`) and locally verified PD-11 (`bbf6358`) on
`task/pre-domain-integration`. Step 6 creates a minimal shared local check
runner/command list used by CI; PD-13 reuses it for the full lifecycle front door.

## Rationale
PD-08 needs actual PD-12 CI/version evidence, and PD-12 needs a local aggregate
before PD-13. Explicit preparation scope resolves these ordering gaps.

## Implications
No test doubles or domain contracts are introduced. At the time of this decision,
the original PD-08 platform/affected-owner/CI checks, PD-09 upstream/command gates,
and PD-11 peer/affected-owner review and main acceptance were pending. Later task
status is recorded in the [work log](../status/work-log.md#current-task-state).
Final acceptance dependencies remain unchanged. PD-19/PRE-00 cannot pass until
required gates are satisfied.
Hosting changes, publication and exact-revision merge retain separate approvals.

## Approver
Current integration contributor, explicit approval of both corrections and the
PD-12 plan before Step 1. No person inferred from a stream label.

## Supersedes
None.

## Scope addition — 2026-10-19
The contributor added Black pre-commit hooks as PD-12 Step 8, after the existing
seven steps. Hooks supplement the independent CI formatting gate.

## Failure evidence acceptance — 2026-10-19
The contributor explicitly accepted the existing intentional local failure
controls plus actual hosted failure (run 39164677937) and successful recovery
(run 39164957563, head `05e4cb8`). No additional hosted probe commits are needed.
Independent human/affected-owner review, exact merge authorization and original
upstream/foundation gates remain required. This accepts the combined evidence;
it does not claim an intentional hosted failure was performed.

## PR-only CI and superseded runs — 2026-10-19
The contributor explicitly selected PR-only CI and cancellation of superseded
runs to conserve Actions minutes. Remove the main push trigger; use a workflow/PR
concurrency key with `cancel-in-progress: true`. Different PRs remain independent.
Before each merge, incorporate latest main and require successful CI for that
integration; if main advances again, refresh/rerun before merging. Record tested
head/base SHAs. This revises PD-12 Step 1 and the manual merge gate; it does not
waive review or permit direct main pushes. A cancelled run never counts as success.
No hosted cancellation behavior is claimed until published/observed.

## Acceptance status reconciliation — 2026-10-19

The user confirmed the previously pending PD-08/09/12/13/15 platform, owner,
upstream, hosted and independent-acceptance gates complete; see the [work-log
reconciliation](../status/work-log.md#resolved-integration-evidence). PD-17–19
and PRE-00 were later accepted; current milestone status is in the work log.
