# Explicit test providers and production rejection

**Date:** 2026-10-17

**Origin:** Decision taken in PD-06 step 2.

**Updated:** 2026-10-17, PD-10 step 2: approved generic test-adapter boundary and storage selector.

## Question

Which shared explicit test providers and production rejection convention should domain consumers use?

## Options considered

- A global test-mode switch controlling several providers.
- Independent explicit provider selection with disabled defaults and production rejection of fakes.

## Selected choice

Default providers to disabled; explicitly select fakes only locally/in tests; reject fakes/development auth in production and never fall back to fake success from real-provider failure. The
[2026-10-24 Identity email decision](identity-email-routing.md) explicitly permits
one alternate real-email-provider attempt, including after uncertainty; it does
not relax fake rejection or enable a provider.

PD-10 extends explicit selectors to storage and approves a generic scripted test helper with safe outcomes/counts/exhaustion. This supports controlled tests before domain-specific provider operation contracts exist; those contracts remain with their owners. The current Stream 1 contributor approved this extension.

The authoritative details and examples are in [shared conventions section 8](../conventions/shared-conventions-and-cross-domain-contract-rules.md).

## Rationale

Testing substitutes must not accidentally authenticate users or claim delivery in production.

## Implications

PD-06 steps 3–6 implement and verify the applicable shared boundary. PD-08/10/11 and later domain owners consume this canonical definition at their assigned checkpoints; real auth, persistence, providers, and domain integration remain their named tasks. Affected owners and an independent human peer review the shared handoff before main acceptance. This decision is not evidence of implemented behavior.

## Approver

Current Stream 1 contributor, by explicit approval in the execution session on 2026-10-17; no person's name inferred from the stream label.

## Supersedes

None.
