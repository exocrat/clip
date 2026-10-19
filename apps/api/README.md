# API foundation

PD-05 steps 1–5 supply a FastAPI application, process-health endpoint, typed startup settings, the [shared-core boundary](app/core/README.md), README-only domain ownership placeholders under `app/domains/`, and persistent API/configuration tests. Marketplace features remain later domain tasks.

From the repository root, install the locked dependencies and start the local API:

```bash
uv sync --locked
uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

In another terminal, `curl --fail http://127.0.0.1:8000/health` should return HTTP 200 with `{"status":"ok"}`. This confirms only that the API process responds; it does not check a database, provider or cloud environment. The initial app exposes only `/health`; schema/docs routes remain disabled; PD-11 generates contracts offline.

Stop the foreground server with Ctrl+C. The server binds only to loopback, requires no cloud credentials or local database, and creates no external resources. If the port is occupied, stop only your own earlier process or explicitly choose another local port and use that same port in the health request. An import/dependency error should be investigated after `uv sync --locked`; do not replace it with a fake success response. Runtime dependencies are declared only in root `pyproject.toml` and locked by uv.

## Startup settings

The API reads these non-secret values from the process environment at startup:

| Variable | Type and local default | Behavior |
|---|---|---|
| `CLIP_ENVIRONMENT` | `local`, `test`, or `production`; default `local` | Rejects unsupported or empty values. This labels configuration mode, not deployment readiness. |
| `CLIP_DEBUG` | Boolean; default `false` | Controls FastAPI debug responses; production rejects `true`. Invalid or empty boolean values fail startup. |
| `CLIP_IDENTITY_PROVIDER` | `disabled` or `fake`; default `disabled` | Explicit local/test helper selection; production rejects `fake`. No real/fake authentication is implemented here. |
| `CLIP_EMAIL_PROVIDER` | `disabled` or `fake`; default `disabled` | Explicit local/test helper selection; production rejects `fake`. No email is sent or claimed delivered. |
| `CLIP_STORAGE_PROVIDER` | `disabled` or `fake`; default `disabled` | Authorizes only explicit test-helper construction; production rejects `fake`. No real storage is configured. |
| `CLIP_DEVELOPMENT_AUTH` | Boolean; default `false` | Reserved testing control; production rejects `true`. This setting creates no public authentication bypass. |

For example, `CLIP_ENVIRONMENT=test CLIP_DEBUG=false uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000` uses explicit test settings. No file is automatically loaded: `.env.example` is documentation, not a source of runtime settings. Restart your server after changing environment values. Configuration failures name the affected settings but do not echo supplied values; startup stops instead of falling back to a successful response.

No database/provider setting is required by this liveness-only skeleton. Their required names and missing-value checks must be added with the tasks that implement those dependencies; no placeholder credential or fake service is required to start locally. PD-06 implements selection safeguards; PD-10 supplies [controlled test helpers](../../tests/fixtures/core/README.md) that normal API startup never installs. Unknown provider names fail startup, and the skeleton never falls back to fake success. Do not treat production configuration mode alone as evidence of a working or safe cloud deployment.

## Tests

From the repository root, run:

```bash
uv sync --locked
uv run --locked pytest apps/api/tests -q -W error
```

`uv run --locked pytest` runs all currently configured test roots; PD-11 contract generation tests also require root `npm ci` and the pinned Node toolchain. The API-only command above needs no Node installation. API tests start the real ASGI app in explicit test mode using FastAPI's TestClient; no HTTP listener, database, provider or cloud access is needed. The tests discard inherited `CLIP_`/`AWS_` settings for isolation and restore the developer's environment afterward. Synthetic cases cover local defaults, typed overrides, malformed/empty values, production-debug rejection, redacted errors, fresh reads and ignored dotenv/example files. Fresh credential-free subprocesses verify invalid configuration prevents the actual entry point from importing. Temporary fixture files stay under pytest's temporary directory.

Exit 0 means the collected suite passed; a failure must be investigated, and exit 5 (no tests collected) is not a pass. The development-only `httpx2` pin supports the installed Starlette TestClient. No fake identity or storage implementation is used, and this suite does not prove domain integration, deployed readiness or performance.

See the [command registry](../../docs/environment/commands.md) for effects and readiness. The [common setup guide](../../docs/environment/README.md#local-foundation-setup) documents shared Make targets. The user later confirmed the previously pending PD-13 clean-environment gates on 2026-10-19; PD-19 Step 2 reran setup on Linux ARM64.

## Local container image (PD-16 Step 4)

The [PD-16 image commands](../../docs/environment/commands.md#local-api-container-image--pd-16-step-4) build the API for the local Docker host's native architecture from the repository root, start it on loopback for a health check, and stop/remove the local container. The Dockerfile uses the locked runtime dependencies, runs as a non-root user with production-safe settings, and includes only the API application source. Record the host architecture, current worktree revision, and dirty state with the local check. The user later confirmed the previously pending PD-08/PD-13 platform and database compatibility gates on 2026-10-19; this local image check does not replace their recorded evidence. The later ECR image must be rebuilt for `linux/amd64` from the exact reviewed commit because the ECS host is x86_64.

## Shared conventions (PD-06 step 3)

See the [core interface guide](app/core/README.md) for IDs, timestamps, whole-rupee integer-paise money, pages, caller context, and safe errors/logging. Common HTTP failures use `error.code`, `error.message`, optional safe `error.details`, and a server `request_id`; clients receive the same identifier in `X-Request-ID`, including on successful health responses. Incoming request IDs do not replace the server identifier. Health response JSON is unchanged.

Application and Uvicorn logs use controlled JSON metadata without raw paths, queries, bodies, credentials, exception text or provider output. Generic request validation errors report input locations only; domain field errors use reviewed names/codes. PD-06 step 4 adds persistent helper/error/logging/settings coverage; step 5 adds explicit client-ID spoofing and real production-startup checks. No extra endpoints or external services are introduced.

## Shared-core tests (PD-06 step 4)

Run `uv run --locked pytest apps/api/tests/core -q -W error` from the repository root for the focused shared-core suite. The existing full API command includes it automatically. The suite checks UUID and UTC round trips, exact whole-rupee conversions, pagination bounds/order preservation, error/status mappings and safe validation details, immutable caller validity, log redaction/concurrent correlation, and provider-setting guards. Warnings are treated as errors.

Temporary FastAPI routes live only in test fixtures; they add no production endpoints. Synthetic static rows test page-window ordering, not future SQL ordering, authorization, or concurrent snapshots. Tests restore environment/logger changes and need no network listener, database, credentials, real provider, or extra dependency. Step 5 supplies the explicit HTTP identity-spoofing and production-entry-point rejection checks below; step 6 performs the final fixture/output review.

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
