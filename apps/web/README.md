# Web application guide

The web app is a runnable scaffold: it has the approved routes, shared shell,
and domain-owned placeholders. Identity temporary sign-in/registration is now in its first local UI checkpoint.
Other product surfaces remain placeholders; Microsoft callback/reset/contact
editing and real provider/runtime acceptance are still pending.

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

## Identity first browser checkpoint — explicit local synthetic mode

From the repository root, in two foreground terminals:

```sh
CLIP_ENVIRONMENT=test uv run --locked python scripts/identity_ui_preview.py --synthetic-preview --seconds 1800
npm run dev -- --mode identity-preview
```

Open `http://localhost:5173/sign-in`. Both servers bind only to loopback. The
backend creates/migrates its own no-network disposable PostgreSQL container,
uses real Identity sessions/OTP/SQL and a reserved synthetic-only inbox; no SES
or Microsoft calls. Use only `preview@example.invalid` and a made-up password.
Create a temporary account, open Check test inbox, enter its transient code and
choose a8–128character password. Sign out and sign back in with those details.
The normal attempt/resend limits apply; code acknowledgements do not prove send
or eligibility. The preview code is only in local memory/browser, never logs or
evidence. Do not use real personal data or passwords in this mode.

The API expires after the chosen cap (default1800s, allowed60–3600s); Ctrl+C
also stops it and removes only its owned ephemeral database. Stop Vite separately
with Ctrl+C. A restart starts a new database, not the previous synthetic account.
The API port is8001 and Vite5173; busy ports fail rather than choose another.
The identity-preview mode is prohibited for builds/deployment. Normal builds
exclude the synthetic inbox; normal dev enables no proxy. Deployed runtime
wiring/cloud exposure and actual-phone access need their own reviewed plan.

Tests in `tests/identity.test.tsx` use jsdom/Testing Library and synthetic reviewed
HTTP results, covering forms, safe errors, duplicate/uncertain writes, session
expiry/stale reads and CSRF. The existing route/boundary tests remain. Full web
lint/types/tests/build uses `npm run check`. Human visual/device verification
follows the [browser procedure](../../docs/environment/browser-verification.md).
