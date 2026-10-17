# DEC-WEB-03 — Web route scaffold

**Date:** 2026-10-17

## Question
Which route mechanism should register the twelve approved frontend paths while
the domain features and their data contracts remain unimplemented?

## Options considered
- React Router declarative routing: provides browser history, path matching,
  route parameters, and nested shell/page composition without introducing
  loaders, actions, or server-data conventions.
- Hand-written pathname matching: avoids a dependency but requires custom
  handling for browser history, dynamic segments, and unknown paths.
- A data/framework router: offers additional data or server conventions not
  needed by this static scaffold and risks implying contracts that DL-00 and
  domain tasks have not established.

## Selected choice
Use the pinned `react-router` package with `BrowserRouter`, `Routes`, `Route`,
`NavLink`, and `Outlet` in declarative mode. Register only the twelve approved
product routes; the `*` route renders a local not-found state and is not a
product route.

## Rationale
The app needs standard browser navigation and dynamic route parameters, while
all business data, authorization, mutations, and API integration are still
owned by DL-00 and later domain tasks. Declarative mode supplies the route and
shell composition needed now without adding loaders/actions or pretending a
domain service exists. See the official [React Router mode guidance](https://reactrouter.com/start/modes).

## Implications
`apps/web/src/app/approvedRoutes.tsx` is the route definition consumed by
`apps/web/src/app/router.tsx` and the automated route-inventory tests. The shared
preview shell is in `apps/web/src/app/AppShell.tsx`; page composition is in
`apps/web/src/pages/ScaffoldPages.tsx` and imports domain placeholders only from
their public feature entry points. Dynamic examples in the shell use the
literal sample identifier `example`. The browser router is a navigation aid
only; it does not authorize private conversations or other protected data.
Domain routes must enforce access through their real trusted interfaces.

## Approver
Not required for a routine technical routing choice within the approved route
inventory.

## Supersedes
None.
