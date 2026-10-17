# Numbered pages and fixed page sizes

**Date:** 2026-10-17

**Origin:** Decision taken in PD-06 step 2.

## Question

Which shared numbered pages and fixed page sizes convention should domain consumers use?

## Options considered

- Cursor pagination with continuation/filter-binding complexity.
- Offset-backed numbered pages with sizes 20, 50, and 100.

## Selected choice

Use page/page_size, default page 1 and size 20, allowed sizes 20/50/100, and items/page/page_size/has_next responses.

The authoritative details and examples are in [shared conventions section 5](../conventions/shared-conventions-and-cross-domain-contract-rules.md).

## Rationale

Page navigation is sufficient; the contributor accepted that concurrent changes can move results across pages. Deterministic sorting is still required.

## Implications

PD-06 steps 3–6 implement and verify the applicable shared boundary. PD-08/10/11 and later domain owners consume this canonical definition at their assigned checkpoints; real auth, persistence, providers, and domain integration remain their named tasks. Affected owners and an independent human peer review the shared handoff before main acceptance. This decision is not evidence of implemented behavior.

## Approver

Current Stream 1 contributor, by explicit approval in the execution session on 2026-10-17; no person's name inferred from the stream label.

## Supersedes

None.
