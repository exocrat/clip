# Structured safe logs and server correlation

**Date:** 2026-10-17

**Origin:** Decision taken in PD-06 step 2.

## Question

Which shared structured safe logs and server correlation convention should domain consumers use?

## Options considered

- Accept client-supplied correlation IDs as the primary identifier.
- Generate server request IDs with controlled structured metadata and central redaction.

## Selected choice

Use structured JSON, server UUIDv4 request IDs returned in X-Request-ID, bounded approved metadata, and central redaction.

The authoritative details and examples are in [shared conventions section 8](../conventions/shared-conventions-and-cross-domain-contract-rules.md).

## Rationale

Server-generated correlation and controlled metadata reduce untrusted-log and private-data exposure while retaining request diagnostics.

## Implications

PD-06 steps 3–6 implement and verify the applicable shared boundary. PD-08/10/11 and later domain owners consume this canonical definition at their assigned checkpoints; real auth, persistence, providers, and domain integration remain their named tasks. Affected owners and an independent human peer review the shared handoff before main acceptance. This decision is not evidence of implemented behavior.

## Approver

Current Stream 1 contributor, by explicit approval in the execution session on 2026-10-17; no person's name inferred from the stream label.

## Supersedes

None.
