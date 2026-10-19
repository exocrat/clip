# DEC-08 — Explicit Terraform deployment phase

**Date:** 2026-10-19

**Origin:** PD-16 audit R03; approval of decision bundle C.

## Question
How should omission of the deployment phase avoid silently requesting deletion?

## Options considered

- Keep a default disabled phase and rely solely on plan inspection.
- Require explicit phase input and retain exact change review.

## Selected choice
Remove the default from `deployment_phase`; retain `disabled`, `base` and `service` and the current resource logic. Cloud planning uses `-input=false` and reviewed phase-specific inputs, so missing input fails rather than silently selecting disabled. Use `base` for initial base provisioning and keep `service` for service deployment and subsequent desired-count toggles. Preserve all other approved non-secret inputs.

## Rationale
Disabled means desired absence of phase-managed resources. It is empty only against empty state; with deployed resources it can propose deletion. A missing phase previously generated a rejected destructive plan.

## Implications
Deliberately selecting disabled can still plan destruction; service-to-base removes service resources. This change is not a destructive-operation safeguard against intentional selection. Inspect every plan's changes and obtain exact checksum approval. Backend-free schema validation needs no actual variable values. No wrapper, remote inspection or AWS action is introduced. Configuration changes require a fresh plan/review; prior approvals do not authorize reusing saved plans after these changes.

## Approver
User in the current session; personal name not recorded.

## Supersedes
The implicit disabled default, not resource ownership, phase values, saved-plan review or separate cloud action approvals.
