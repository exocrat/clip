# Combined API: Identity, Listings, Search and Conversations

SE-01 Steps 3–6 add authenticated `GET /listings` collection browse/search with stable
numbered pages over currently available records. Both eligible account classes
are supported through a separate public Identity read adapter. Explicit Identity
composition binds its real implementation; default startup remains unbound, so
unauthenticated requests fail closed. Plain-text `q` uses
the existing PostgreSQL English title/description vector and GIN index, with
recency or price ordering. Category, condition, inclusive price and negotiability
filters are applied before paging. Runtime validation rejects malformed/range-
reversed inputs through shared 422 errors; unknown/inactive catalogue codes are
validated by the owned store. Discovery responses are `private, no-store` and
each request rechecks eligibility/storage. Saved-item retrieval remains separate
SE-02 work, including retained unavailable summaries and retired-content privacy.
Isolated PostgreSQL checks are available; integrated hosted readiness and final Search acceptance remain separate gates. See the
[browse implementation and current checks](app/domains/listings/README.md).

The API serves process health and Listings create, detail, owner-list,
replacement, availability, buyer-selection, offer-command, and image-upload
routes. The image-upload endpoints create owner-bound intents, issue short-lived
S3 upload URLs, verify stored object metadata, and retain canceled object keys
for the later cleanup step. The Listings handlers are implemented in
`app/domains/listings/`; they require trusted Identity caller wiring, an
explicit Listings storage adapter, and (for selection and offers) the
Conversations public-call adapter. An explicit database URL opens the
PostgreSQL-backed Listings store at startup; without it, feature routes fail
closed. The combined factory also mounts Search/Wanted/Saved and Conversations
routes and binds Conversations' real thread, message, key, read-state and retirement
operations. Real Identity authentication requires explicit trusted composition;
selecting a provider name alone does not enable it. CN-02 offer persistence and
contact-sharing integration, and CN-03 recipient/delivery workers, remain pending.
The [shared-core boundary](app/core/README.md) and typed startup
settings remain the foundation for the remaining domain tasks.

From the repository root, install the locked dependencies and start the local API:

```bash
uv sync --locked
uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

In another terminal, `curl --fail http://127.0.0.1:8000/health` should return HTTP 200 with `{"status":"ok"}`. This confirms only that the API process responds; it does not check a database, provider or cloud environment. Schema/docs routes remain disabled; generated contracts are separate from runtime implementations.

Stop the foreground server with Ctrl+C. The server binds only to loopback, requires no cloud credentials or local database, and creates no external resources. If the port is occupied, stop only your own earlier process or explicitly choose another local port and use that same port in the health request. An import/dependency error should be investigated after `uv sync --locked`; do not replace it with a fake success response. Runtime dependencies are declared only in root `pyproject.toml` and locked by uv.

## Startup settings

The API reads these values from the process environment at startup:

| Variable | Type and local default | Behavior |
|---|---|---|
| `CLIP_ENVIRONMENT` | `local`, `test`, or `production`; default `local` | Rejects unsupported or empty values. This labels configuration mode, not deployment readiness. |
| `CLIP_DEBUG` | Boolean; default `false` | Controls FastAPI debug responses; production rejects `true`. Invalid or empty boolean values fail startup. |
| `CLIP_IDENTITY_PROVIDER` | `disabled`, `fake`, or `microsoft`; default `disabled` | `microsoft` permits private local/test validator construction; production rejects this incomplete integration and all fake auth. No sign-in route/session is installed. |
| `CLIP_EMAIL_PROVIDER` | `disabled`, `fake`, `ses`, or `dual`; default `disabled` | Explicit provider selection; the notification worker requires controlled test-mode `dual`. |
| `CLIP_NOTIFICATION_WORKER_ENABLED` | Boolean; default `false` | Explicitly starts one notification poller only with the real hosted Identity test runtime and controlled recipients. Production is not enabled. |
| `CLIP_NOTIFICATION_BATCH_SIZE` | Integer 1–50; default `20` | Maximum claimed jobs per serial worker batch. |
| `CLIP_NOTIFICATION_POLL_SECONDS` | Integer 1–3600; default `60` | Delay between completed batches. Provider attempts remain capped at five per intent. |
| `CLIP_STORAGE_PROVIDER` | `disabled`, `fake`, or `s3`; default `disabled` | `s3` selects the real private S3 adapter; `fake` is reserved for explicit test helpers and is rejected in production. |
| `CLIP_IMAGE_BUCKET` | Optional bucket name; default unset | Required with `CLIP_STORAGE_PROVIDER=s3`. It names the private bucket and is not a credential. |
| `CLIP_IMAGE_REGION` | Optional AWS region; default unset | Required with `CLIP_STORAGE_PROVIDER=s3`; the S3 adapter uses the normal AWS credential provider chain (task role in ECS, selected profile locally). |
| `CLIP_IMAGE_KEY_PREFIX` | Optional private object prefix; default unset | Required with `CLIP_STORAGE_PROVIDER=s3`; use a run-scoped prefix for isolated testing. Object keys are generated by Listings under this prefix. |
| `CLIP_DEVELOPMENT_AUTH` | Boolean; default `false` | Reserved testing control; production rejects `true`. This setting creates no public authentication bypass. |
| `CLIP_DATABASE_URL` | Optional PostgreSQL URL; default unset | Stored as a redacted secret. When set, startup opens a bounded async connection pool; do not paste the URL into logs or chat. Without it, health starts and Listings routes return the safe unavailable response. |
| `CLIP_DATABASE_DSN` | Optional redacted PostgreSQL connection string | Overrides only the Conversations tuple-row pool; otherwise it uses `CLIP_DATABASE_URL`. Syntax is checked without revealing its value. This is not a new authentication mechanism. |
| `CLIP_HYBRID_SEARCH_ENABLED` | Boolean; default `false` | Opts into the normal API-owned real helper and separate read pool; starts no worker/backfill and activates no pipeline. |
| `CLIP_HYBRID_WORKER_ENABLED` | Boolean; default `false` | Requires Hybrid enabled; processes existing durable jobs serially using the same helper and one dedicated connection. No register/backfill/serving activation. |
| `CLIP_HYBRID_SEARCH_INTERPRETER` | Absolute local path, unset by default | Required with enabled Hybrid and database URL; preserve the venv interpreter path. Not shown in settings repr. |
| `CLIP_HYBRID_SEARCH_MODEL_DIR` | Absolute local path, unset by default | Required with enabled Hybrid; real helper validates pinned artifacts/runtime. No download/discovery. Paths with disabled mode are rejected. |
| `CLIP_SENSITIVE_PURCHASE_THRESHOLD_PAISE` | Nonnegative whole-rupee paise; default `500000` | Listings flags non-sensitive categories only when asking price is greater than this value. Mobile phones and laptops are flagged at every price. |

For example, `CLIP_ENVIRONMENT=test CLIP_DEBUG=false uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000` uses explicit test settings. No file is automatically loaded: `.env.example` is documentation, not a source of runtime settings. Restart your server after changing environment values. Configuration failures name the affected settings but do not echo supplied values; startup stops instead of falling back to a successful response.

No database/provider setting is required to start the health endpoint locally.
The database adapter is real PostgreSQL code and is enabled only by an explicit
`CLIP_DATABASE_URL`; it does not create or reset a database. The S3 adapter is
enabled only when `CLIP_STORAGE_PROVIDER=s3` and its bucket, region, and
run-scoped prefix are configured; AWS credentials are never placed in these
settings. The upload URL lasts at most five minutes, and its signed request
requires the declared content type plus `If-None-Match: *`, so a replay cannot
replace an object at that key. Confirmation currently checks S3-reported type
and byte count; Step 5 will add actual file-content checks before the upload can
be accepted as an image. Identity's public eligibility declaration is not
bound by default. Explicit Identity composition now supplies eligibility, and
the configured Conversations provider supplies thread creation, exact-pair lookup,
participant checks and retirement operations. CN-02 offer persistence remains
unavailable. Requests needing an unbound dependency return the shared safe error. No
placeholder credential or fake service is required to start locally. PD-06 implements selection safeguards; PD-10 supplies
[controlled test helpers](../../tests/fixtures/core/README.md) that normal API
startup never installs. Unknown provider names fail startup, and the API never
falls back to fake success. Do not treat production configuration mode alone
as evidence of a working or safe cloud deployment.

## Tests

From the repository root, run:

```bash
uv sync --locked
uv run --locked pytest apps/api/tests -q -W error
```

`uv run --locked pytest` runs all currently configured test roots; PD-11 contract generation tests also require root `npm ci` and the pinned Node toolchain. The API-only command above needs no Node installation. Foundation API tests start the real ASGI app in explicit test mode using FastAPI's TestClient without an HTTP listener/provider/cloud call. ID-01 Microsoft persistence tests additionally require local Docker: they create only their own tmpfs PostgreSQL18.6 database, private Unix socket and synthetic records, then remove the container; no retained database or host port is used. The tests discard inherited `CLIP_`/`AWS_` settings for isolation and restore the developer's environment afterward. Synthetic cases cover local defaults, typed overrides, malformed/empty values, production-debug rejection, redacted errors, fresh reads and ignored dotenv/example files. Fresh credential-free subprocesses verify invalid configuration prevents the actual entry point from importing. Temporary fixture files stay under pytest's temporary directory.

The Listings store workflow also has a separate explicit runner. Run
`uv run --locked python scripts/check_database.py
--listings-store` to apply migrations to a fresh disposable PostgreSQL container
and exercise listing creation, edit, selection, availability, and retry writes.
It uses a temporary Unix socket and synthetic Identity/Conversations test
doubles, then prints a sample row selected from PostgreSQL before cleanup. Its
image metadata is fixture data, not an S3 upload. The shared Compose database
is not used.

Exit 0 means the collected suite passed; a failure must be investigated, and exit 5 (no tests collected) is not a pass. The development-only `httpx2` pin supports the installed Starlette TestClient. Individual tests label controlled signer/mail/storage ports or caller doubles. Do not mistake these for live providers, deployed readiness or performance evidence.

See the [command index](../../docs/environment/commands.md) for common commands and links to current owner guides. The [common setup guide](../../docs/environment/README.md#local-foundation-setup) documents shared Make targets. The user later confirmed the previously pending PD-13 clean-environment gates on 2026-10-19; PD-19 Step 2 reran setup on Linux ARM64.

## Local container image (PD-16 Step 4)

The [PD-16 image command](../../docs/environment/commands.md#local-api-container-image--pd-16-step-4) stages the API, web source, generated contracts and locked manifests into a local build context, builds for the Docker host's native architecture, starts the container on loopback for a health check, and removes only its own container/image/context. The Dockerfile uses locked runtime dependencies and runs as a non-root user with production-safe settings. Record the host architecture, current worktree revision, and dirty state with the local check. The user later confirmed the previously pending PD-08/PD-13 platform and database compatibility gates on 2026-10-19; this local image check does not replace their recorded evidence. The later ECR image must be rebuilt for `linux/amd64` from the exact reviewed commit because the ECS host is x86_64.

## Shared conventions (PD-06 step 3)

See the [core interface guide](app/core/README.md) for IDs, timestamps, whole-rupee integer-paise money, pages, caller context, and safe errors/logging. Common HTTP failures use `error.code`, `error.message`, optional safe `error.details`, and a server `request_id`; clients receive the same identifier in `X-Request-ID`, including on successful health responses. Incoming request IDs do not replace the server identifier. Health response JSON is unchanged.

Application and Uvicorn logs use controlled JSON metadata without raw paths, queries, bodies, credentials, exception text or provider output. Generic request validation errors report input locations only; domain field errors use reviewed names/codes. PD-06 step 4 adds persistent helper/error/logging/settings coverage; step 5 adds explicit client-ID spoofing and real production-startup checks. No extra endpoints or external services are introduced.

## Shared-core tests (PD-06 step 4)

Run `uv run --locked pytest apps/api/tests/core -q -W error` from the repository root for the focused shared-core suite. The existing full API command includes it automatically. The suite checks UUID and UTC round trips, exact whole-rupee conversions, pagination bounds/order preservation, error/status mappings and safe validation details, immutable caller validity, log redaction/concurrent correlation, and provider-setting guards. Warnings are treated as errors.

Test-only routes live in test fixtures. The production app also mounts the reviewed Listings subset, which remains unavailable without its configured dependencies. Synthetic static rows test page-window ordering, not future SQL ordering, authorization, or concurrent snapshots. Tests restore environment/logger changes and need no network listener, database, credentials, real provider, or extra dependency. Step 5 supplies the explicit HTTP identity-spoofing and production-entry-point rejection checks below; step 6 performs the final fixture/output review.

## Security boundary tests (PD-06 step 5)

Run `uv run --locked pytest apps/api/tests/core/test_security_boundaries.py -q -W error` for focused security checks; the existing shared-core/full commands include them. Tests reject client identity/account/eligibility/ownership claims in headers, query parameters, JSON and cookies. Test-only server wiring supplies positive controls: valid internal contexts work, client claims cannot replace them, and claimed future deadlines cannot revive expired contexts.

Fresh credential-free child processes import `app.main` with a ten-second timeout. Production rejects every nonempty combination of fake identity/email/storage selection, development authentication, debug, combined unsafe controls and empty/unsupported provider selections; safe production defaults and explicit local/test selections provide positive controls. No listener or actual provider is started. These checks establish shared-boundary/configuration safety; actual credential verification, revocation, domain authorization and provider delivery remain with their owning implementation tasks.

## Health contract generation

`app.main` binds `/health` using the generated types/metadata in
`app/contracts/health.py`. Edit `contracts/source/health.py`, then use the
[contract guide](../../contracts/README.md) to regenerate/check; do not edit the
generated runtime module. The handler still returns only `{"status":"ok"}`.
Generation and public schema publication are separate; no schema endpoint or
marketplace feature is enabled.

## Identity provider setup and current status

Current Microsoft/email configuration, secret references and live gates are in
[ID-01 provider setup](../../docs/environment/identity-provider-setup.md) and
[secret handling](../../docs/environment/secret-handling.md). The normal API
remains Identity-unbound unless the reviewed composition is explicitly selected;
a provider setting alone does not activate deployed sign-in. Use the
[ID-01 task/status](../../docs/tasks/domain-task-list.md) and
[work-log row](../../docs/status/work-log.md) for current acceptance; older
step-by-step receipts are in Git history.

## Combined Conversations runtime — CN-01 integration

`app.application.create_app` composes all four domains in the same ASGI app.
Listings and Search own origin commands; they call the app-bound Conversations
public provider rather than another domain's private store. Listing and Wanted
start endpoints return an actual persisted thread (201 new, 200 existing).
The public web `ConversationRuntime` consumes Identity session state and the
shared cookie/CSRF transport; it does not authenticate a browser itself.

### Configuration and lifecycle

- `CLIP_DATABASE_URL` supplies the existing dictionary-row Listings/Search pool
  (min1/max10, acquisition/startup wait5seconds). The separate Conversations
  tuple-row pool uses `CLIP_DATABASE_DSN` when supplied, otherwise the same URL
  (min0/max1, lazy startup). An override may use a separate authorized login but
  must address the **same logical database**: cross-domain foreign keys and owner
  workflows do not support independently populated databases. Settings validate
  connection syntax, not this target identity or the login's grants.
- Both pools belong to the ASGI lifespan and close on orderly exit or failed
  marketplace startup. Optional Search helper/dispatcher resources retain their
  existing lifecycle; the Conversations connection adds no worker or backfill.
- Startup never applies migrations, creates database roles, reconciles data or
  schedules cleanup. Provision the complete reviewed migration chain and exact
  runtime grants through the existing [database process](../../database/README.md).
  Do not apply only Conversations SQL to an empty target. Persistent targets
  retain their exact-target preflight/run-plan approval requirements.
- `/health` is process liveness only. The lazy Conversations pool does not probe
  its schema/grants at startup. A healthy process is not an integration/readiness
  assertion; configured database/schema/authorization failures must be checked
  through actual permitted workflows and may return safe503 responses.
- Default `app.main:app` mounts the routes but leaves Identity unbound. Use explicit
  trusted `IdentityHttpDependencies` for local SQL tests, or the separately approved
  Identity launcher. Its `--check` reads live secrets and checks Identity only;
  it does **not** validate the marketplace/Conversations pools or schema. Do not
  run that launcher as an offline setup check.

### Local checks and build (no live providers)

From the root with the pinned Python/Node24/npm11 setup:

```bash
uv run --locked pytest apps/api/tests/test_database_lifespan.py apps/api/tests/test_config.py -q -W error
uv run --locked pytest apps/api/tests/test_conversation_identity_integration.py apps/api/tests/domains/identity/test_application_composition.py -q -W error
npm run build
```

The second command creates/removes its own disposable PostgreSQL18.6 containers,
applies the full migration chain and uses real sessions, owner HTTP commands and
database side effects. Microsoft signing/discovery, OTP mail and external image
storage are controlled test ports. Public keys/opaque envelopes in these HTTP
tests are synthetic; actual SDK encryption/IndexedDB evidence is separate.
For migration/message/retirement storage checks, use the registered
`uv run --locked python scripts/check_conversations_retirement.py` disposable
runner. It accepts no retained database target.

The existing API Dockerfile already builds/copies the normal web bundle and
Conversations application source; no extra image, service or dependency install
is needed for chat. `CLIP_SERVE_WEB_APP=true` uses the existing `/api` same-origin
composition. Local Vite's normal `/api` proxy rewrites to8000; `identity-preview`
is a separate synthetic profile, not a combined-app connection. A web build does
not validate a container image or deploy it. No image/cloud run occurred here.

### Concrete remaining runtime gates

Before a real environment can serve signed-in chat, its operator must validate
the reviewed full schema, same-target domain logins/grants, Identity secret and
provider configuration, exact browser origin/cookie/CSRF and TLS/proxy routing,
and the built web artifact. Test-mode Identity opt-in is not production auth
approval. Use the existing approved launcher/deployment handoff; do not add a
fixed caller or invent a new secret path to bypass missing setup. No real grant,
secret lookup, provider call or deployment is implied by local tests.

Offer persistence, selected-contact sharing and notification recipient/delivery
workers are not implemented by this CN-01 integration. The existing cleanup CLI
is bounded/dry-run by default and has no automatically installed schedule. These
are concrete follow-ons, not claims that chat cannot be reviewed/merged now.


## Combined Conversations runtime — CN-01 integration

The combined API connects domains through their public interfaces. The current
CN-01 integration result and remaining real checks are in the
[Conversations handoff](../../docs/evaluation/domain/conversations-integration.md)
and [domain task list](../../docs/tasks/domain-task-list.md). Use those current
gates when changing shared runtime composition; this guide's former checkpoint
details were removed.

## Normal API Hybrid read lifecycle (SE-01)

The combined merge now supplies an optional Linux AMD64 container extension with
the pinned helper, model and operator CLI. Normal `CLIP_SERVE_WEB_APP=true` may
serve the built UI without enabling the isolated test caller. See the
[Listings/Search deployment handoff](../../docs/architecture/listings-search-deployment.md)
for builds, runtime settings, pipeline initialization and the remaining
Identity/Conversations bindings.

Normal startup can now explicitly own the real helper and a separate min1/max2
idle-autocommit read pool. The existing Listings command/Keyword pool keeps its
transactional behavior. Invalid/partial configuration fails safely; an enabled
helper/read-pool startup failure closes partial resources and leaves Keyword
available, with nonblank Hybrid503. Shutdown/cancellation cleans helper/pools;
cleanup failures remain failures. No test caller, pipeline registration, serving
switch, worker or backfill is enabled by this setting. Real Identity eligibility,
serving-space/vector coverage, resource sizing and deployment gates
still apply. See [the lifecycle contract](../../docs/architecture/normal-api-search-runtime.md)
and the registered guarded native probe. Do not run the normal API against an
existing/shared database merely to test these settings.


### Optional durable embedding dispatcher

CLIP_HYBRID_WORKER_ENABLED=true separately starts serial existing-job processing
when Hybrid capability is available. It owns1extra autocommit connection, shares
the helper, paces bounded bursts/idle/failures and stops before helper shutdown.
Both settings default false. The registry/bootstrap remain unchanged; an empty
registry stays idle. See [dispatcher semantics](../../docs/architecture/semantic-embedding-dispatcher.md).


### Controlled pipeline initialization

The separate `scripts/search_pipeline.py` operator tool now provides status,
prepare, bounded queue and guarded activation. It does not start inference or
change normal startup. Status is read-only; mutations require explicit execution
and exact approved target/pipeline binding. Existing live listings, including
unavailable ones, need complete current vectors before activation. Concurrent
edits can invalidate readiness afterward, so request guards remain. No shared
or cloud target was run/approved here. See [the bootstrap contract](../../docs/architecture/semantic-pipeline-bootstrap.md).

## Normal API Hybrid read lifecycle (SE-01)

The current helper, worker and pipeline limits are documented in the
[normal API lifecycle](../../docs/architecture/normal-api-search-runtime.md),
[dispatcher](../../docs/architecture/semantic-embedding-dispatcher.md) and
[pipeline bootstrap](../../docs/architecture/semantic-pipeline-bootstrap.md)
designs. Local/default startup does not turn on Hybrid work. The SE-01 task and
work log distinguish isolated checks from hosted readiness and NFR acceptance.

## SE-02 wanted-request author/read API checkpoint

The normal composition now mounts reviewed wanted create, open browse/detail,
own list, edit and availability operations. The Search store shares the existing
transactional pool; no additional pool, auth bypass or worker is installed.
`CLIP_DATABASE_URL` absence leaves storage unavailable. Trusted regular/temporary
callers still require actual Identity eligibility and public Listings catalogue
providers; declaration-only defaults fail closed503. Native contract doubles are
explicit test injection, not normal-server fallbacks.

[Search boundary](app/domains/search/README.md) explains validation, privacy,
optimistic revision and exact retry behavior. Saves and UI are still pending; draft matching is described below. The approved internal
request-retirement coordinator and atomic scrub now have isolated tests; they
are unscheduled and real Conversations integration remains pending. This checkpoint
is not real readiness/FR acceptance or a deployment.

### SE-02 draft matches

`POST /wanted-requests/draft-matches` accepts only `{draft_title}` and returns
`{items,has_more}` with at most20 public summaries from the available-sale query,
newest first. It requires a current eligible regular/temporary caller, stores
nothing, and is independent of wanted creation. No category/budget is inferred.
Inputs trim before the120-code-point limit; invalid/blank text is422 and required
provider failure503. Responses and safe errors are private/no-store.
The default public Identity/Listings calls remain declaration-only; native checks
use the real Listings SQL provider with explicit synthetic Identity. UI and real
provider integration remain separate gates.

### SE-02 private saved-listing API

The normal composition mounts `GET /me/saved-listings`,
`PUT /me/saved-listings/{listing_id}` with `{operation_id}`, and idempotent
`DELETE /me/saved-listings/{listing_id}` (empty 204). All use the current trusted
caller; user IDs are not accepted in paths/bodies/query selectors. Saves keep the
original timestamp on duplicate calls. Current saved state comes only through
Listings' public resolver; unavailable details remain and retired content is not
returned. Provider failures do not return stale summaries.

The saved store shares the existing pool and existing schema. Current public
Identity/target/resolver declarations are not implementations; required calls
fail with 503 until real integration. Native tests explicitly supply reviewed scripts
while running actual Search SQL/HTTP/privacy/concurrency behavior. UI is Step7.

### SE-02 Contact requester backend

The reviewed response endpoint is mounted. Current regular callers may respond;
temporary callers are denied. Open requests create/return a thread through public
Conversations; closed requests can only resolve the same caller's existing pair.
Both201/200 include the conversation ID; no contacts/author ID are returned.
Retired/pending/missing requests fail404, self403, unavailable dependencies503.
Normal public providers remain unimplemented defaults, so no successful thread
is fabricated. Native tests use explicit C scripts; real integration and Step7
UI remain pending. No scheduler, resource or migration was added.

## Wanted requests and saved listings (SE-02)

Feature-specific request, save and response behavior is in
[Search API documentation](app/domains/search/README.md). The current local and
real-integration gates are in the [SE-02 task](../../docs/tasks/domain-task-list.md)
and [work-log row](../../docs/status/work-log.md). Older step-by-step details are
recoverable from Git history; they are not a current readiness claim.

## RDS system trust in the shared image

The ordinary image installs pinned public ap-south-1 RDS roots alongside its
existing distribution roots and points SSL_CERT_FILE at the standard OS CA file.
This also corrects the bundled libpq OpenSSL wheel-build default path. Identity
continues to require verify-full/system roots; no URI or provider setting changes.
The optional Hybrid image inherits the corrected store from its selected parent.
See the [shared trust decision](../../docs/decisions/identity-rds-system-trust.md)
and [local image checks](../../docs/environment/commands.md#api-image-rds-root-trust--id-01-step12).
AMD64/Hybrid rebuild and actual deployed RDS verification remain separate gates.
