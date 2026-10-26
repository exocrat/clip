# DEC-ID-01 — Explicit hosted test Identity activation

**Date:** 2026-10-25

**Origin:** ID-01 Step12, local runtime-readiness implementation.

## Question

How can the shared test API use the implemented real Identity services while the
default and production API remain safely unbound?

## Options considered

- Keep Identity available only through the operator-local loopback command; this
  does not support the hosted account checks.
- Bind Identity automatically whenever Microsoft settings are present; partial
  or accidental configuration could expose a real sign-in path.
- Add one explicit test-only startup flag with complete settings validation and
  retain the default-disabled/production-refusing behavior.

## Selected choice

Use `CLIP_IDENTITY_RUNTIME_ENABLED=true` only with `CLIP_ENVIRONMENT=test`, real
Microsoft and dual-email selectors, debug/development auth off, a separate
Listings database URL, and exactly the registered HTTPS origin
`https://clip-iisc.site`. `app.main` then loads the fixed Identity SSM references,
checks the dedicated Identity DB role and email route, and installs the existing
Identity handlers. Any missing or invalid dependency fails startup without
falling back. No migration, provisioning or initial email send occurs at startup.

When the same API process serves the bundled UI, Identity endpoints use `/api`
like Listings/Search. With a separately hosted UI, an approved same-origin proxy
must route `/api` to the unprefixed API paths. The browser middleware continues
to require HTTPS and exact Origins; proxy trust must be configured only after its
actual network hop is verified.

## Rationale

The shared environment and approved secret references are explicitly `test`, so
the opt-in is limited to that mode. It avoids changing production guards and
preserves credential-free startup by default. Requiring both database URLs keeps
Identity's restricted DB login separate from the Listings application pool.

## Implications

The settings, ASGI composition and Identity route installer now support this
explicit mode. The shared ECS task definition, Identity SSM/IAM access, both DB
URLs/roles, shared HTTPS ingress, trusted proxy and actual account checks remain
unconfigured or unverified; this decision authorizes none of those cloud actions.
The feature flag must remain false until the exact runtime and ingress plan is
reviewed and approved.

## Approver

Aditya (A) delegated local implementation and routine design choices for overnight
preparation. Cloud configuration, secrets, migration, deployment and live sends
retain their separate approvals.

## Supersedes

None.
