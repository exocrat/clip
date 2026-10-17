# DEC-01 — Terraform state ownership boundaries

**Date:** 2026-10-17

## Question
How should Terraform ownership be divided so shared infrastructure and future domain resources are not managed by overlapping states or contributors?

## Options considered
- Put bootstrap, shared-environment, and domain resources in one state. This is simpler initially but couples changes and ownership across the project.
- Separate ownership by resource category, keeping shared resources in one state and domain-exclusive resources in their owner's state. This adds state boundaries but makes ownership and change scope clearer.

## Selected choice
- PD-15 / Stream 4 (Rahul) owns the Terraform bootstrap/state infrastructure and its configuration.
- The PD-16 integration owner owns shared test-environment infrastructure.
- Each domain task owner owns only resources exclusive to that domain. Domain modules consume shared resource identifiers rather than recreating shared resources.

These are ownership boundaries, not a selection of backend technology, bucket, exact state keys, workspaces, or AWS resources. Those remain for later PD-15 steps and their approval gates.

## Rationale
Separate ownership by resource category reduces accidental overlap, gives shared infrastructure a single accountable owner, and lets domain work consume common infrastructure without duplicating it.

## Implications
PD-15 Step 3 must select the backend, locking, encryption, recovery, and environment-separation design. PD-15 Step 5 must record exact state keys/workspaces and module ownership in `docs/architecture/terraform-ownership.md`. No AWS resource creation, permission grant, backend provisioning, or state migration is authorized by this decision. The user's deferral of least-privilege checks remains in effect and is not treated as a passed PD-14 check.

## Approver
Rahul (D), who verified the Step 2 ownership-boundary understanding on 2026-10-17.

## Supersedes
None
