# DEC-06 — Temporary Terraform planning identity exception

**Date:** 2026-10-19

**Origin:** PD-16 Step 5.

## Question
Can the PD-16 base plan proceed with the currently configured AWS root identity while a separate planning identity is unavailable?

## Options considered
- Pause until a scoped non-root planning identity is available.
- Use the root identity temporarily, with a narrow task and action boundary.

## Selected choice
For PD-16 Step 5 only, the user approved the configured `default` profile, which STS identifies as the account root principal, for preparing and reviewing the non-applying base-infrastructure plan.

This exception does not authorize applying the plan, provisioning or changing resources, bootstrapping or migrating Terraform state, publishing an image, or preparing later service-phase cloud changes. Those actions retain their separate approval gates; a non-root identity is required before apply/provisioning.

## Rationale
The user chose to continue with the available identity because there is not time to configure another identity now. This removes the planning-identity blocker for the narrowly scoped non-applying plan while recording that root has broader account access and raises the impact of an operational mistake.

## Implications
The exact plan remains gated on PD-15 backend creation and state migration, complete per-run cost/lifecycle and reserve inputs, and explicit authorization to create the non-applying plan. The plan must target account `335523638354`, Region `ap-south-1`, and the reviewed shared/test state. Before any apply or provisioning, configure and verify an approved non-root identity and obtain the separate exact-plan authorization.

## Approver
User in the current session; name not recorded.

## Supersedes
None. This is a temporary, task-scoped exception to the non-root planning-identity requirement recorded in the PD-16 proposal.
