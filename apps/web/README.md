# Web application guide

## SE-01 Step 7 — first discovery UI checkpoint

`features/search/SaleDiscovery.tsx` supplies responsive sale discovery through
the public Search export. Only DiscoveryPage's sale slot is replaced. Wanted,
saved and other feature actions remain at their original checkpoints. The UI
uses the generated public summary/page/catalogue types, strict response guards,
same-origin uncached reads, URL-backed applied filters, exact whole-rupee input,
stable numbered paging, cancellation and explicit retry. Changing controls and
applying them resets page 1. No query response or previous availability is used
as a fallback after a failure. Image bodies are not fetched by discovery cards.

With real API/Identity/PostgreSQL dependencies available, normal `npm run dev`
uses `/api` through the existing loopback proxy. This checkout lacks those real
providers. For the initial **UI-only** human checkpoint the agent starts:

```bash
CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true .venv/bin/python apps/api/tests/domains/search/browser_preview.py --isolated-search-ui
PATH="$PWD/.tools/node/bin:$PATH" NPM_CONFIG_CACHE="$PWD/.tools/npm-cache" NPM_CONFIG_USERCONFIG=/dev/null VITE_SEARCH_UI_PREVIEW=true .tools/node/bin/npm run dev
```

Open **http://127.0.0.1:5173/**. The banner identifies synthetic fixture responses,
not a database-backed marketplace. The test server binds only loopback 8000,
requires explicit test settings, rejects ambient database/AWS configuration,
and requires the development client's preview header/local origin. Normal or
production clients cannot silently consume it. No test server is imported by
normal API startup. Vite's production build excludes the preview header/banner
branch. The flag labels/selects test transport opt-in only; it adds no real auth.

The harness offers 42 synthetic summaries and named query scripts: `bicycle`,
`books`, `desk`, `empty`, `slow`, `retry` (fails once, then succeeds),
`unavailable`, `denied`, `expired`, and `malformed`. Fixture selection/sorting
exists only to inspect UI interactions; it is not PostgreSQL search/ranking or
acceptance evidence. Detail links use the real approved route, but detail/auth/
save integration is not supplied by this preview. There are no writes/providers.

Human checkpoint: inspect desktop, narrow portrait/landscape and tablet layouts;
try search, filters/sorts/sizes, Previous/Next, Back/refresh, reversed/fractional
prices, empty/loading/error/retry and sign-in-required display states. Record
actual browser/version and viewport sizes. Stop here for verification before
further visible increments. Real auth/SQL/filter/image/browser integration and
required physical-device checks remain pending. Ctrl+C in each agent-owned
server session stops only that service; no database cleanup is involved.

Client price inputs use decimal text/BigInt so large whole-rupee filters are not
rounded. JSON money/page numbers that JavaScript cannot represent safely are
rejected rather than displayed approximately; this is a client representation
limit, not a new product price cap. Live high-value schema/transport compatibility
remains subject to real integration review.

The web app retains the approved routes, shared shell and domain-owned surfaces.
Listings supplies create/detail/edit/My Listings components; the SE-01 sale
discovery increment is described above. Real Identity, fully integrated image
behavior, wanted/saved flows and Conversations remain at their owning tasks'
pending checkpoints. Component presence does not establish domain acceptance.

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


### Search modes/relevance checkpoint

Search starts in Keyword/Newest unless a valid URL selects other inputs. The
immediate mode selector retains applied filters/sort/page size, resets page1,
and preserves unsaved form edits. Apply uses the current mode and drafts; a
cleared relevance query becomes Newest. History navigation reloads URL inputs.
Visible associated help explains both modes/relevance. Hybrid503 offers explicit
Retry or Use Keyword; no automatic fallback or stale page. Request cleanup aborts
and ignores late callbacks, and rendered result state is keyed to query/retry.
The preview's `hybrid-down` query fails only in Hybrid so recovery can be inspected;
`slow` and `retry` retain their labelled scripts. Fixture results never prove
semantic matching/rank/auth. Human browser verification remains separate.


### Real local search backend

The native Search preview command in the registry connects actual SQL/vocabulary/
typo/relevance and offline embeddings on3synthetic listings. The development banner
identifies the responding backend via X-Clip-Preview: real local SQL/model,
scripted UI fixtures, or unknown. The metadata changes disclosure only, never
routing/auth. Native mode accepts real queries; old scripted words are ordinary
text. Real sign-in/image delivery and final corpus/evaluation remain pending.

### SE-02 wanted/saved UI checkpoint

Search's public `WantedBrowse`, `MyWantedRequests`, `WantedDetail`,
`SavedListings` and `SaveListingAction` compose into the existing approved routes
in `ScaffoldPages.tsx`. No other feature's private files are imported.

`wantedApi.ts` uses generated contract types, same-origin credentials and no-store
reads/writes. It validates public/private projections, pages and money before
rendering. `budgetPaise` parses whole rupees exactly: blank clears/omits a budget,
zero means free; unsafe JS integers and decimal inputs are refused. `SearchIntent`
retains a UUID for identical uncertain retries and changes it when intent changes;
no private drafts, saved state or operation keys are placed in browser storage.

`WantedViews.tsx` keeps request results keyed to current inputs and aborts old
requests. `useRead` hides stale results immediately; `DraftSuggestions` debounces
title-only matches, ignores late replies and never blocks publication. The owner
editor submits a revision for edits; availability changes use the same protection.
After a stale-revision error, cancel editing and refresh requests before retrying.
The private list supplies edit controls; public responses carry no author identity.
Detail eligibility comes from reviewed Identity `GET /me`, including expiry;
Conversations still authorizes independently. Only a validated successful response
can navigate to the existing conversation route. A 503 stays on the request page.
Saved lists retain current unavailable details; retired rows render no content.
Save/unsave acknowledge confirmed server results and have explicit retry actions.
`wanted.css` scopes responsive inputs/cards to Search without changing the shell.

The opt-in native UI/API test uses the same TS transport as these components
against the running disposable harness. Default `npm run check` skips its two
network tests; unit/initial-render tests still run. This does not exercise React
effects or replace human browser/device checks. See the command registry and
`docs/evaluation/domain/se-02/frontend/README.md` for the exact review package.
