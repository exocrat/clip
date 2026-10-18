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
No test doubles or domain contracts are introduced. Original PD-08 platform,
affected-owner and CI checks, PD-09 upstream/command gates, PD-11 peer/affected-owner
review and main acceptance remain pending. Final acceptance dependencies remain
unchanged. PD-19/PRE-00 cannot pass until required gates are satisfied.
Hosting changes, publication and exact-revision merge retain separate approvals.

## Approver
Current integration contributor, explicit approval of both corrections and the
PD-12 plan before Step 1. No person inferred from a stream label.

## Supersedes
None.

## Scope addition — 2026-10-19
The contributor added Black pre-commit hooks as PD-12 Step 8, after the existing
seven steps. Hooks supplement the independent CI formatting gate.
