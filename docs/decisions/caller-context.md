# Internal trusted caller context

**Date:** 2026-10-17

**Origin:** Decision taken in PD-06 step 2.

## Question

Which shared internal trusted caller context convention should domain consumers use?

## Options considered

- Minimal immutable identity/account-class/validity context.
- Include precomputed capabilities and their additional freshness/ownership obligations.

## Selected choice

Use immutable user_id/account_class/valid_until context from server authentication wiring; retain resource authorization in domains.

The authoritative details and examples are in [shared conventions section 4](../conventions/shared-conventions-and-cross-domain-contract-rules.md).

## Rationale

A small context is understandable and avoids duplicate domain policy. Type construction alone is not authentication.

## Implications

PD-06 steps 3–6 implement and verify the applicable shared boundary. PD-08/10/11 and later domain owners consume this canonical definition at their assigned checkpoints; real auth, persistence, providers, and domain integration remain their named tasks. Affected owners and an independent human peer review the shared handoff before main acceptance. This decision is not evidence of implemented behavior.

## Approver

Current Stream 1 contributor, by explicit approval in the execution session on 2026-10-17; no person's name inferred from the stream label.

## Supersedes

None.
