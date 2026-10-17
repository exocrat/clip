# Whole-rupee prices with integer-paise units

**Date:** 2026-10-17

**Origin:** Decision taken in PD-06 step 2.

## Question

Which shared whole-rupee prices with integer-paise units convention should domain consumers use?

## Options considered

- Change shared API/storage units to integer rupees.
- Retain integer paise and restrict marketplace amounts to whole rupees.

## Selected choice

Retain integer paise; listing prices, offers, and price filters use multiples of 100, with whole-rupee input/display.

The authoritative details and examples are in [shared conventions section 2](../conventions/shared-conventions-and-cross-domain-contract-rules.md).

## Rationale

This preserves existing canonical units while meeting the requested whole-rupee experience without floating point or rounding.

## Implications

PD-06 steps 3–6 implement and verify the applicable shared boundary. PD-08/10/11 and later domain owners consume this canonical definition at their assigned checkpoints; real auth, persistence, providers, and domain integration remain their named tasks. Affected owners and an independent human peer review the shared handoff before main acceptance. This decision is not evidence of implemented behavior.

## Approver

Current Stream 1 contributor, by explicit approval in the execution session on 2026-10-17; no person's name inferred from the stream label.

## Supersedes

None.
