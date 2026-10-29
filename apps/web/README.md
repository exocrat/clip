# Web application guide

The web scaffold provides shared routes and UI primitives. Identity implements
authentication/contact screens under its explicit local modes; Listings supplies
its accepted lifecycle/image UI and isolated demo. Real combined auth/runtime
integration is pending ID-READY. Both domains retain their documented test gates.

## Install and run locally

```bash
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The page header links to each approved route;
dynamic routes use the sample identifier `example`. Stop the foreground server
with Ctrl+C. Vite binds to loopback and fails if its configured port is busy.

## Run checks

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

`lint` runs Biome's recommended code checks on the web source, architecture
tests, and Vite configs. `typecheck` checks the app plus tests and Vite/Vitest configs.
`test` checks the route table used by the app and scans imports for violations
of the documented page/feature boundaries. The route tests deliberately check
paths and matching, not placeholder text or appearance. `build` type-checks the
app and creates production assets under ignored `apps/web/dist/`.

Run the same local suite with one command:

```bash
npm run check
```

## Preview a production build

```bash
npm run preview
```

Open `http://127.0.0.1:4173` and stop the foreground process with Ctrl+C. Build
first; preview serves only the generated local assets and does not deploy them.

These commands need no AWS credentials, external accounts, or production
endpoints. Identity reads its documented public build flag and calls the reviewed
same-origin API when configured. `npm ci` downloads packages in the committed lockfile
from the configured npm registry.

## Current feature references

Use the [frontend ownership map](../../docs/architecture/frontend-collaboration.md)
for approved routes, page owners and public feature boundaries. The
[domain task list](../../docs/tasks/domain-task-list.md) defines feature behavior
and acceptance; the [work log](../../docs/status/work-log.md) records current
status. Do not treat old checkpoint notes as current acceptance.

The Search product defaults to Hybrid and has no visible mode selector. Legacy
Keyword URLs and API mode handling remain for compatibility. The command index
contains the isolated Search preview and local Listings browser commands; the
[browser procedure](../../docs/environment/browser-verification.md) covers human review.

For Identity provider setup and secret references, use
[provider setup](../../docs/environment/identity-provider-setup.md) and
[secret handling](../../docs/environment/secret-handling.md). The retained
[Conversations integration handoff](../../docs/evaluation/domain/conversations-integration.md)
and [offers/contact-sharing handoff](../../docs/evaluation/domain/conversations-offers.md)
are the task-specific references for those flows.
