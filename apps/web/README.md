# Web application guide

The web app is a runnable scaffold: it has the approved routes, shared shell,
and domain-owned placeholders. Product data, authentication, APIs, saving,
offers, and messaging are still implemented by later tasks.

Use Node.js 24 LTS and npm 11, as recorded in the
[workstation guide](../../docs/environment/development-workstation.md). Run
commands from the repository root; the root `package.json` and
`package-lock.json` are the only Node manifest and lockfile.

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
endpoints. The current scaffold does not read frontend environment variables
or call an application API. `npm ci` downloads packages in the committed lockfile
from the configured npm registry.

## Conversations API boundary

`features/conversations` exports `ConversationApi` and `ConversationHttpTransport`.
The adapter implements the reviewed inbox, summary, entries, message, explicit
displayed-read and public-key/prekey HTTP mappings using generated contract types.
It validates successful response shapes, rejects malformed routing/cursors/key
material, and exposes only content-free error status/kind. It never automatically
retries a write; the caller must retain and reuse its prepared ciphertext and
operation ID after an ambiguous outcome. Fetching entries never acknowledges reads.

Identity must supply the authenticated request function, including session and
CSRF behavior. The adapter has no default transport or test-identity fallback.
It is not yet mounted by the scaffold pages. Real auth, SDK relay/startup,
local history persistence and two-browser integration remain pending. In
particular, `readOwnKey()` now maps the approved authenticated
`GET /me/conversation-key`: only an explicit valid null means never registered.
Errors or malformed bundles never become a missing key. The SDK relay must
connect this operation to its own-identity lookup before startup is complete.
