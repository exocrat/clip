# Domain public boundaries

**Date:** 2026-10-18

**Origin:** PD-11 step 2.

## Question

Which Python and database boundaries must future domain consumers respect?

## Options considered

- Package/private imports and shared-table access: conflict with existing ownership rules.
- Declared public modules with explicit composition exceptions: make the existing ownership boundary checkable.

## Selected choice

Use each domain's generated `public.py` as its cross-domain entry point.
The [shared convention](../conventions/shared-conventions-and-cross-domain-contract-rules.md#python-boundary-convention-pd-11-step-2)
defines permitted dependencies, composition/test scope and the ban on private-table access.
Core remains technical; public declarations do not expose implementations.

## Rationale

Consumers can depend on reviewed contracts before provider implementations exist.
One database and one deployable application do not remove domain ownership.

## Implications

PD-11 step 3 checks representative import/table violations and reports analysis
limits. DL-00 generates actual public declarations; domain tasks implement them.
No business contract, composition exception or human ownership is invented here.

## Approver

Existing canonical ownership rules; integration contributor authorized step 2.
Recorded output verification and affected-owner/independent review remain pending.

## Supersedes

None; makes the existing domain boundary concrete without changing ownership.
