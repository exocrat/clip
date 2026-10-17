# API foundation

PD-05 steps 1–5 supply a FastAPI application, process-health endpoint, typed startup settings, the [shared-core boundary](app/core/README.md), README-only domain ownership placeholders under `app/domains/`, and persistent API/configuration tests. Marketplace features remain later domain tasks.

From the repository root, install the locked dependencies and start the local API:

```bash
uv sync --locked
uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

In another terminal, `curl --fail http://127.0.0.1:8000/health` should return HTTP 200 with `{"status":"ok"}`. This confirms only that the API process responds; it does not check a database, provider or cloud environment. The initial app exposes only `/health`; generated schema/docs routes are disabled until later contract work.

Stop the foreground server with Ctrl+C. The server binds only to loopback, requires no cloud credentials or local database, and creates no external resources. If the port is occupied, stop only your own earlier process or explicitly choose another local port and use that same port in the health request. An import/dependency error should be investigated after `uv sync --locked`; do not replace it with a fake success response. Runtime dependencies are declared only in root `pyproject.toml` and locked by uv.

## Startup settings

The API reads these non-secret values from the process environment at startup:

| Variable | Type and local default | Behavior |
|---|---|---|
| `CLIP_ENVIRONMENT` | `local`, `test`, or `production`; default `local` | Rejects unsupported or empty values. This labels configuration mode, not deployment readiness. |
| `CLIP_DEBUG` | Boolean; default `false` | Controls FastAPI debug responses; production rejects `true`. Invalid or empty boolean values fail startup. |
| `CLIP_IDENTITY_PROVIDER` | `disabled` or `fake`; default `disabled` | Reserved explicit local/test adapter selection; production rejects `fake`. No real/fake authentication is implemented here. |
| `CLIP_EMAIL_PROVIDER` | `disabled` or `fake`; default `disabled` | Reserved explicit local/test adapter selection; production rejects `fake`. No email is sent or claimed delivered. |
| `CLIP_DEVELOPMENT_AUTH` | Boolean; default `false` | Reserved testing control; production rejects `true`. This setting creates no public authentication bypass. |

For example, `CLIP_ENVIRONMENT=test CLIP_DEBUG=false uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000` uses explicit test settings. No file is automatically loaded: `.env.example` is documentation, not a source of runtime settings. Restart your server after changing environment values. Configuration failures name the affected settings but do not echo supplied values; startup stops instead of falling back to a successful response.

No database/provider setting is required by this liveness-only skeleton. Their required names and missing-value checks must be added with the tasks that implement those dependencies; no placeholder credential or fake service is required to start locally. PD-06 implements selection safeguards; PD-10 supplies controlled fake adapters. Unknown provider names fail startup, and the skeleton never falls back to fake success. Do not treat production configuration mode alone as evidence of a working or safe cloud deployment.

## Tests

From the repository root, run:

```bash
uv sync --locked
uv run --locked pytest apps/api/tests -q
```

`uv run --locked pytest` runs all currently configured test roots. API tests start the real ASGI app in explicit test mode using FastAPI's TestClient; no HTTP listener, database, provider or cloud access is needed. The tests discard inherited `CLIP_`/`AWS_` settings for isolation and restore the developer's environment afterward. Synthetic cases cover local defaults, typed overrides, malformed/empty values, production-debug rejection, redacted errors, fresh reads and ignored dotenv/example files. Fresh credential-free subprocesses verify invalid configuration prevents the actual entry point from importing. Temporary fixture files stay under pytest's temporary directory.

Exit 0 means the collected suite passed; a failure must be investigated, and exit 5 (no tests collected) is not a pass. The development-only `httpx2` pin supports the installed Starlette TestClient. No fake identity or storage implementation is used, and this suite does not prove domain integration, deployed readiness or performance.

See the [command registry](../../docs/environment/commands.md) for effects and readiness. PD-13 later adds the shared lifecycle/test Make targets.

## Shared conventions (PD-06 step 3)

See the [core interface guide](app/core/README.md) for IDs, timestamps, whole-rupee integer-paise money, pages, caller context, and safe errors/logging. Common HTTP failures use `error.code`, `error.message`, optional safe `error.details`, and a server `request_id`; clients receive the same identifier in `X-Request-ID`, including on successful health responses. Incoming request IDs do not replace the server identifier. Health response JSON is unchanged.

Application and Uvicorn logs use controlled JSON metadata without raw paths, queries, bodies, credentials, exception text or provider output. Generic request validation errors report input locations only; domain field errors use reviewed names/codes. Persistent PD-06 coverage is pending steps 4–5; existing PD-05 tests do not prove every new convention. No extra endpoints or external services are introduced.
