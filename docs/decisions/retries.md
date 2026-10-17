# Domain-owned transactions and explicit retries

**Date:** 2026-10-17

**Origin:** Decision taken in PD-06 step 2.

## Question

Which shared domain-owned transactions and explicit retries convention should domain consumers use?

## Options considered

- Universal automatic write retries/idempotency storage.
- Operation-specific retry/duplicate contracts with domain transaction ownership.

## Selected choice

No arbitrary automatic write retries; each operation declares safe retry/duplicate behavior, and independent notification failure preserves primary success.

The authoritative details and examples are in [shared conventions section 7](../conventions/shared-conventions-and-cross-domain-contract-rules.md).

## Rationale

Operation semantics must determine retry safety; no speculative shared transaction/provider implementation is needed.

## Implications

PD-06 steps 3–6 implement and verify the applicable shared boundary. PD-08/10/11 and later domain owners consume this canonical definition at their assigned checkpoints; real auth, persistence, providers, and domain integration remain their named tasks. Affected owners and an independent human peer review the shared handoff before main acceptance. This decision is not evidence of implemented behavior.

## Approver

Current Stream 1 contributor, by explicit approval in the execution session on 2026-10-17; no person's name inferred from the stream label.

## Supersedes

None.
