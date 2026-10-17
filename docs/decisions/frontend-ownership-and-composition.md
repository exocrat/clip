# DEC-WEB-02 — Frontend ownership and page composition

**Date:** 2026-10-17

## Question
How should page composition and shared frontend work be assigned across the
four existing domain owners to limit overlapping edits while keeping staffing
flexible?

## Options considered
- Permanently assign one page-composition owner per route. This gives a clear
  reviewer but requires a fixed assignment even when that person is unavailable.
- Leave composition ownership open and list each page's primary domain
  contributors and bounded integration contributions. An available integrator
  coordinates each necessary page edit as its sole current writer.
- Let every domain edit shared page files independently. This offers local
  autonomy but increases overlapping edits and merge conflicts.

## Selected choice
Use primary and small-integration contributor roles for each approved page,
recorded in the [frontend collaboration map](../architecture/frontend-collaboration.md).
Do not permanently assign page-composition owners. When a shared page edit is
needed, the available integrator/merger coordinates it and is the sole current
writer for that page composition. Feature code remains within its domain root.

Page compositions import feature components through the public entry points
`src/features/identity/index.ts`, `src/features/listings/index.ts`,
`src/features/search/index.ts`, and
`src/features/conversations/index.ts`. Features do not import another feature's
private files. A owns the app shell/navigation and shared presentation area in
`src/shared/ui/` and `src/shared/styles/`; bounded shared changes identify
affected consumers and receive review from their contributors.

## Rationale
This keeps routine domain implementation in separate feature roots while giving
cross-domain pages an explicit place and process for composition. Leaving
permanent composition assignments open lets the available integrator handle a
bounded edit without making one person a permanent bottleneck. A single current
writer per page composition limits simultaneous edits to the same shared file.

## Implications
PD-07 Steps 4–6 create the feature roots, public entry points, shared UI/styles,
and approved page compositions. The Step 3 roles and boundaries are documented
in the frontend map. Page composition does not authorize private cross-feature
imports or invent API/data/session contracts; DL-00 and the domain task owners
define those contracts. Any new route requires human approval. Later domain
agents remove only their own feature `.gitkeep` at their first authorized
implementation write.

## Approver
Suraj verified the Step 3 page contributor roles and open-composition approach
on 2026-10-17.

## Supersedes
None.
