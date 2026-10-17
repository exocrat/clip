# UTC timestamp representation

**Date:** 2026-10-17

**Origin:** Decision taken in PD-06 step 2.

## Question

Which shared utc timestamp representation convention should domain consumers use?

## Options considered

- Accept only UTC Z inputs.
- Accept explicit timezone offsets and normalize; emit one UTC form.

## Selected choice

Use aware instants and output six fractional digits plus Z; accept explicit offsets and reject naive input.

The authoritative details and examples are in [shared conventions section 2](../conventions/shared-conventions-and-cross-domain-contract-rules.md).

## Rationale

A single output format keeps contracts consistent while offset input remains practical and unambiguous.

## Implications

PD-06 steps 3–6 implement and verify the applicable shared boundary. PD-08/10/11 and later domain owners consume this canonical definition at their assigned checkpoints; real auth, persistence, providers, and domain integration remain their named tasks. Affected owners and an independent human peer review the shared handoff before main acceptance. This decision is not evidence of implemented behavior.

## Approver

Current Stream 1 contributor, by explicit approval in the execution session on 2026-10-17; no person's name inferred from the stream label.

## Supersedes

None.
