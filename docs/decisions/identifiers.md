# UUIDv4 identifiers

**Date:** 2026-10-17

**Origin:** Decision taken in PD-06 step 2.

## Question

Which shared uuidv4 identifiers convention should domain consumers use?

## Options considered

- UUIDv4 with random identifiers and no intentional creation-time ordering.
- UUIDv7 for time ordering, with creation-time information in identifiers.

## Selected choice

Use server-generated UUIDv4 and canonical lowercase hyphenated strings.

The authoritative details and examples are in [shared conventions section 2](../conventions/shared-conventions-and-cross-domain-contract-rules.md).

## Rationale

UUIDv4 is sufficient for the foundation; no time-order requirement justifies another strategy.

## Implications

PD-06 steps 3–6 implement and verify the applicable shared boundary. PD-08/10/11 and later domain owners consume this canonical definition at their assigned checkpoints; real auth, persistence, providers, and domain integration remain their named tasks. Affected owners and an independent human peer review the shared handoff before main acceptance. This decision is not evidence of implemented behavior.

## Approver

Current Stream 1 contributor, by explicit approval in the execution session on 2026-10-17; no person's name inferred from the stream label.

## Supersedes

None.
