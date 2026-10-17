# API foundation

PD-05 steps 1–4 supply a FastAPI application, process-health endpoint, typed startup settings, the [shared-core boundary](app/core/README.md), and README-only domain ownership placeholders under `app/domains/`. Persistent API tests are a subsequent PD-05 output; marketplace features remain later domain tasks.

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

For example, `CLIP_ENVIRONMENT=test CLIP_DEBUG=false uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000` uses explicit test settings. No file is automatically loaded: `.env.example` is documentation, not a source of runtime settings. Restart your server after changing environment values. Configuration failures name the affected settings but do not echo supplied values; startup stops instead of falling back to a successful response.

No database/provider setting is required by this liveness-only skeleton. Their required names and missing-value checks must be added with the tasks that implement those dependencies; no placeholder credential or fake service is required to start locally. Fake-provider controls remain PD-06/10 work. Do not treat production configuration mode alone as evidence of a working or safe cloud deployment.

See the [command registry](../../docs/environment/commands.md) for effects and readiness. PD-13 later adds the shared lifecycle commands. Persistent API/configuration tests remain PD-05 step 5 outputs; the current settings checks are isolated smoke verification.
