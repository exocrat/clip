# Runtime Command Registry

**Canonical path:** `docs/environment/commands.md`

This registry contains implemented commands and planned outputs, distinguished in the table below. Each command-creating task populates exact spellings/arguments/script paths and verifies safe behavior; a planned row is not proof of implementation. The normal front door is root Makefile, unless PD-02 explicitly approves an equivalent and records actual mappings. Root README/CONTRIBUTING/CI must match this registry after PRE-00.

For EACH command record: creator task, exact invocation and required inputs, supported shell/runtime, target/environment, effects and destructive/billable behavior, prerequisite milestone, expected output/exit status, failure/recovery, tests/evidence. Commands must reject unspecified or wrong targets rather than guessing an AWS account/region/database.

| Required command outcome | Creator | Current state |
|---|---|---|
| Install/setup | PD-02/04/07/13 | Python tools: `uv sync --locked` implemented/verified in PD-04; web and combined setup remain pending PD-07/13 |
| Local start/stop/readiness | PD-05/07/08/13 | API process start/stop/health and typed settings human-verified at PD-05 steps 1–2; web/database/combined lifecycle remain future outputs |
| Local migration/status/reset and small seed | PD-08/13 | Not implemented; reset local-only and explicit |
| Generator framework/tests | PD-09 | Not implemented |
| Final reference generate/load/validate/fingerprint | SE-01/DATA-READY | Not implemented; requires domain schemas/configuration |
| Python format and non-mutating pinned Black check | PD-04 | Implemented and human-verified at step 3; exact commands and verification below |
| Test/lint/type/build/aggregate CI-equivalent | PD-05/07/12/13 | API/configuration suite implemented and human-verified at PD-05 step 5; web/CI/aggregate commands remain future outputs |
| Contract regenerate/stale-check | PD-11/DL-00 | Not implemented |
| Terraform static format/validate (no remote state mutation) | PD-15 | Not implemented |
| Plan/apply/build-release/deploy/verify/rollback/teardown | PD-15/16; domain/EXP additions | Not implemented; gated actions separate from local/CI check |
| Search evaluator/load workload/NFR manifests | SE-01 | Not implemented |
| Two-client chat/read-state/latency measurement | CN-01/CN-03 | Not implemented |
| Integrated peak/runtime-loss/DB-restore checks | INT-01 | Not implemented |
| Mixed Lambda package/routing/parity/deploy/workloads/analysis | EXP-02/03–08 | Not implemented |
| Final regression/export/demo/package verification | CLOSE-00 | Not implemented |

An absent command assigned to the selected creation step is an expected output; the agent creates/registers/tests it. An absent prerequisite or uncertain expected effect blocks the dependent action and requires a question. No cloud operation belongs in the generic local/CI aggregate target.

## PD-04 Python formatter commands

Run from the repository root with GNU Make and uv on the supported Linux/macOS development environment. Requires the PD-02 toolchain decision and the PD-04 root `pyproject.toml`/`uv.lock`; no cloud prerequisites. Python must satisfy `>=3.14,<3.15`. `uv sync --locked` installs the locked development dependencies into the ignored `.venv`; uv can obtain a missing compatible interpreter. Each developer uses their own environment. First-time installation can require network access.

| Invocation | Mapping and effects | Expected result and recovery |
|---|---|---|
| `make format-python` | `uv run --locked black .`; formats discovered Python files using the root configuration; respects Black defaults, Git ignores and configured exclusions. | Exit 0 after formatting (or when already formatted). Review the source diff. Resolve reported syntax/configuration/dependency errors before retrying. |
| `make check-python-format` | `uv run --locked black --check --diff .`; reports proposed source changes without writing them. Plain `make` runs this target too. | Exit 0 when formatted or no Python files exist; nonzero on drift or tool failure. For drift, run `make format-python`, review changes and rerun the check. |

Both commands select pinned Black 26.10.1 and refuse an out-of-date lockfile rather than rewriting it. uv may synchronize `.venv` and update local caches; check-only means Python source is unchanged. There are no cloud, database, or provider effects. An empty repository scan is not evidence that real Python code is formatted. Verification uses a temporary synthetic Python sample to prove drift detection, source preservation, formatting and repeatability; see the PD-04 step 3 work-log entry. CI wiring remains PD-12's output; the combined setup/lifecycle command front door remains PD-13's output.

## PD-04 Python test runner

PD-04 step 5 pins pytest 9.1.1 in the root development group for PD-05/06/10. Run `uv sync --locked` after receiving the updated lockfile, then `uv run --locked pytest` from the repository root. This runs tests in the local uv environment using root `pyproject.toml`; it may update local caches/environment and requires no cloud resources. Exit 0 means collected tests passed; exit 1 means a test failed; exit 5 means no tests were collected, which is not a passing suite. Investigate reported failures before retrying. PD-04 verified the runner with temporary smoke probes; PD-05 now supplies the persistent health/configuration suite below. See [the tooling decision](../decisions/python-test-tooling.md). No test Make target or CI workflow is implemented yet.

## PD-05 API process startup and health

From the repository root, run `uv sync --locked`, then `uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000`. Requires the Python 3.14/uv environment and locked FastAPI/Uvicorn runtime dependencies; no database or cloud credentials. The foreground process binds only to loopback and may synchronize the local uv environment/cache. Stop it with Ctrl+C. PD-13 supplies the shared start/stop front door later; no API Make target is added here.

`curl --fail http://127.0.0.1:8000/health` should exit 0 with HTTP 200 and `{"status":"ok"}`. This proves only process liveness, not database/provider/deployment readiness. Connection failure, non-2xx health response, dependency/import error or occupied port is a failure to investigate; do not silently switch targets or replace failure with a fake response. If necessary, explicitly select another local port and use it in both commands. No provider/cloud operation is performed. Live loopback verification used an ephemeral port and an environment containing no cloud credentials, checked the exact JSON response and disabled docs/unknown routes, then stopped its owned process. See [API instructions](../../apps/api/README.md) and the PD-05 step 1 work-log evidence. Typed process-environment settings are implemented in step 2: optional `CLIP_ENVIRONMENT` defaults to local, optional `CLIP_DEBUG` defaults false, invalid/empty values fail startup and production rejects debug. No dotenv/example file is loaded; examples are in `.env.example`. Persistent API tests remain step 5.

## PD-05 API/configuration tests

Run `uv sync --locked`, then `uv run --locked pytest apps/api/tests -q` from the repository root; `uv run --locked pytest` includes this suite through the root configuration. Prerequisites are the PD-05 skeleton/settings, pinned pytest and development-only httpx2 2.13.1. This is the [supported Starlette TestClient transport](https://starlette.dev/testclient/); plain httpx produced a deprecation warning and was replaced rather than suppressed. Root `pyproject.toml` supplies the API import path and is the sole test configuration.

Tests run in-process ASGI requests and bounded local subprocesses, use only synthetic values, and restore inherited environment changes. They may update pytest/Python caches and create temporary synthetic dotenv files; they need no listener, cloud credentials, database or external services. Success is exit 0 with collected tests passed; failures must remain failures, and exit 5 is no collection, not a pass. PD-05 step 5 verified 13 tests, including startup rejection/redaction, with warnings treated as errors (`uv run --locked pytest -q -W error`). PD-12/13 still own CI and the shared command front door.

## PD-06 shared-core wiring (step 3)

The existing API start/stop, test and formatting commands above are unchanged. PD-06 adds common error responses, `X-Request-ID`, and safe application/Uvicorn JSON logs; see the [core guide](../../apps/api/app/core/README.md). Provider selections `CLIP_IDENTITY_PROVIDER`/`CLIP_EMAIL_PROVIDER` default to `disabled`; reserved `fake` selections and `CLIP_DEVELOPMENT_AUTH=true` are rejected in production. Unsupported provider names fail startup; no adapter or credential is supplied by this step. Exact setting behavior is in the [API README](../../apps/api/README.md#startup-settings).

## PD-06 initial tests (step 4)

Step 4 adds `uv run --locked pytest apps/api/tests/core -q -W error` for focused convention tests; the existing full API/root pytest commands collect it too. Run from the repository root with the same locked Python/pytest/TestClient prerequisites. Warnings fail the run; success is exit 0 with collected tests passing, exit 5 is not a pass. Failure requires inspecting the failing behavior rather than changing expected output to hide a defect. Tests use in-memory ASGI apps, synthetic fixtures, local temporary files/caches and restored environment/logger settings, with no cloud, provider, listener or database effects. Step 5 adds explicit client-ID spoofing and real production-entry-point rejection checks. See [API test guidance](../../apps/api/README.md#shared-core-tests-pd-06-step-4).

## PD-06 security boundary tests (step 5)

Run `uv run --locked pytest apps/api/tests/core/test_security_boundaries.py -q -W error` from the repository root with the same locked test prerequisites. This focused subset is included in existing shared-core/full pytest commands. It uses temporary in-memory HTTP routes and bounded credential-free Python children importing the actual API entry point; it opens no listener and contacts no provider/database/cloud service. The children accept safe configuration or fail startup on unsafe production selections; no provider success is simulated. Exit 0 means collected checks passed; failures require investigation and exit 5 is not a pass. See [coverage and limits](../../apps/api/README.md#security-boundary-tests-pd-06-step-5).

## PD-10 shared fixture checks (step 1)

Run `uv run --locked pytest tests/fixtures/core apps/api/tests/core/test_shared_fixtures.py -q -W error` from the repository root. Root pytest configuration exposes the test-only fixture package; the full pytest command collects these checks too. Requires the existing locked Python/test tools. The checks use deterministic references/clocks and in-memory contexts/errors, may write local test caches, and contact no database/provider/cloud service. Exit 0 means collected checks passed; failures need investigation and exit 5 is not a pass. See [fixture usage and limits](../../tests/fixtures/core/README.md).

## PD-10 scripted test-provider checks (step 2)

Run `uv run --locked pytest tests/fixtures/core -q -W error` for shared factories and scripted-provider tests. The existing full pytest command includes them. These tests load explicit isolated settings and perform no provider/network/file delivery operations; pytest may update local caches. Requires existing locked test tools. Success is exit 0 with collected tests passing; failures require investigation and exit 5 is not a pass. See [approved interfaces](../../tests/fixtures/core/adapter-interfaces.md). `CLIP_STORAGE_PROVIDER` now follows the existing disabled/fake selection guard; step 3 verifies the production startup/configuration matrix below.

## PD-10 production provider matrix (step 3)

Run `uv run --locked pytest apps/api/tests/core/test_provider_settings.py apps/api/tests/core/test_security_boundaries.py -q -W error` from the repository root. Existing full pytest commands include these tests. This checks isolated settings and the actual entry point in credential-free subprocesses with ten-second timeouts, with no listener, credentials or provider calls. Every fake identity/email/storage selector combination must prevent production startup; empty/unsupported selections fail and safe configurations provide positive controls. OTP-specific verification remains an Identity contract concern; no separate OTP provider is implemented here. Existing locked test prerequisites and pytest exit/failure rules apply.

## Workstation and stub command registration

The setup guide contains one-time agent-access/clone commands, not implemented application targets. BOOT-00 records actual Linux paths/agent availability; PD-02/13 freeze the verified development toolchain and application commands. PD-10/DL-00/domain owners register explicit test-double scenarios and real integration commands with distinct names/modes. No deployed command may default to fake auth/storage/notification/domain providers; startup validation rejects them. Stub tests never share a label or result classification with cloud/NFR runs.
