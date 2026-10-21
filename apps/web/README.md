# Web application guide

The web app has the approved routes, shared shell, and domain-owned surfaces.
LI-01 Step 7's first increment implements create → saved listing detail through
the Listings API. Edit/My Listings and other domains are still placeholders.
Real Identity, photo upload/delivery, Search and Conversations are pending.

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
endpoints. Listings calls `/api`; the development server forwards that prefix
to `127.0.0.1:8000`, stripping it before reaching FastAPI. This proxy is development
only; production routing remains a later runtime integration obligation.
`npm ci` downloads packages in the committed lockfile from the configured registry.

## LI-01 Step 7: isolated browser check with real PostgreSQL

The agent starts the services for each human checkpoint. Commands below document
the reproducible setup; the human only needs the supplied browser URL and actions.
Use the recorded Node 24/npm 11 and locked Python environment. Docker must use a
local Unix-socket context. No existing Compose database is targeted.

In one foreground terminal, from the repository root:

```bash
CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true uv run --locked python apps/api/tests/domains/listings/browser_demo.py --isolated-listings-browser
```

This explicit test-package launcher creates its own PostgreSQL 18.6 container,
applies the current migrations using pinned dbmate 2.36.0, seeds a synthetic
seller, and runs the actual Listings routes/store at `127.0.0.1:8000`. PostgreSQL
has no published port/network and is reached through a private Unix-socket path.
Only this test app installs synthetic trusted authentication and a prepared-image
metadata endpoint. It refuses production/default settings and ambient database
URLs. The production app neither mounts these test routes nor selects fake auth.

In a second foreground terminal:

```bash
VITE_LISTINGS_ISOLATED_DEMO=true npm run dev
```

Open **http://127.0.0.1:5173/listings/new**. The labelled isolated mode uses real
Listings API/SQL writes but synthetic account and image confirmation metadata.
“Use a prepared test image record” creates metadata only: it does not upload a
photo, inspect an object, or prove LI-02 storage behavior. No public draft listing
is inserted while the form is being completed. The development flag is ignored
in production builds. Ordinary `npm run dev` uses no test controls.

First human checkpoint:

1. Submit the empty form: required-field/image messages appear, and no listing is saved.
2. Enter a synthetic title/description, optionally enter a pickup area, choose category/condition, and
   enter a whole-rupee price (0 is valid). Prepare the test image record and publish.
3. The browser opens `/listings/<real UUID>`, loads the saved detail through a fresh
   API request, and shows price, condition, dates, proof statement and sensitive flag.
4. Refresh that URL and confirm the same data remains. Save the URL for later
   edit/My Listings increments; shell links containing `example` are only samples.
5. Repeat with proof omitted/Yes/No, books at ₹5,000/₹5,001 and a phone at ₹0;
   check declarations/flags, invalid fractional/negative prices, whitespace-only
   text, and invalid date order. Stop the API temporarily or use browser Offline
   mode to inspect errors; restore it and retry. No automatic write retries occur.
6. Inspect desktop and narrow phone portrait/landscape layouts. Record browser/
   version, sizes and observed results. Emulation is not actual-phone camera evidence.

The launcher prints a private session directory. To inspect its rows while it runs,
replace `SESSION_PATH` with that exact printed path:

```bash
CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true uv run --locked python apps/api/tests/domains/listings/browser_demo.py --isolated-listings-browser --inspect SESSION_PATH
```

This uses a read-only SQL session and shows listing ID, title, price, availability
and proof declaration from the actual database. Ctrl+C stops the API and its owned
database container, retaining rows and session metadata. Resume with the same test
settings and `--resume SESSION_PATH`; restart Vite separately if stopped. Ctrl+C in
the web terminal stops Vite. No script removes retained database data; cleanup is
separate. Lost `/tmp` session metadata is a resume limitation, not durable deployment.

Step 7 is partial until edit/My Listings and the remaining UI states pass their
browser checkpoints. Real sign-in/authorization integration, photo selection and
uploads (LI-02), Search/discovery, save and chat remain pending. See the work log
for original Step 5/8–13 checks and affected-owner review gates.
