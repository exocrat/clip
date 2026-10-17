# Runtime Command Registry

**Canonical path:** `docs/environment/commands.md`

This registry contains implemented commands and planned outputs, distinguished in the table below. Each command-creating task populates exact spellings/arguments/script paths and verifies safe behavior; a planned row is not proof of implementation. The normal front door is root Makefile, unless PD-02 explicitly approves an equivalent and records actual mappings. Root README/CONTRIBUTING/CI must match this registry after PRE-00.

For EACH command record: creator task, exact invocation and required inputs, supported shell/runtime, target/environment, effects and destructive/billable behavior, prerequisite milestone, expected output/exit status, failure/recovery, tests/evidence. Commands must reject unspecified or wrong targets rather than guessing an AWS account/region/database.

| Required command outcome | Creator | Current state |
|---|---|---|
| Install/setup | PD-02/04/07/13 | Python tools: `uv sync --locked` implemented/verified in PD-04; web and combined setup remain pending PD-07/13 |
| Local start/stop/readiness | PD-05/07/08/13 | API process start/stop and health human-verified at PD-05 step 1; typed settings implemented at step 2 (verification pending); web/database/combined lifecycle remain future outputs |
| Local migration/status/reset and small seed | PD-08/13 | Not implemented; reset local-only and explicit |
| Generator framework/tests | PD-09 | Not implemented |
| Final reference generate/load/validate/fingerprint | SE-01/DATA-READY | Not implemented; requires domain schemas/configuration |
| Python format and non-mutating pinned Black check | PD-04 | Implemented and human-verified at step 3; exact commands and verification below |
| Test/lint/type/build/aggregate CI-equivalent | PD-07/12/13 | Not implemented |
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

PD-04 step 5 pins pytest 9.1.1 in the root development group for PD-05/06/10. Run `uv sync --locked` after receiving the updated lockfile, then `uv run --locked pytest` from the repository root. This runs tests in the local uv environment using root `pyproject.toml`; it may update local caches/environment and requires no cloud resources. Exit 0 means collected tests passed; exit 1 means a test failed; exit 5 means no tests were collected, which is not a passing suite. Investigate reported failures before retrying. The runner was verified with temporary synthetic fixture/parameterized cases and an intentional failure, then those probes were removed. Real foundation tests remain future outputs. See [the tooling decision](../decisions/python-test-tooling.md). No test Make target or CI workflow is implemented by this step.

## PD-05 API process startup and health

From the repository root, run `uv sync --locked`, then `uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000`. Requires the Python 3.14/uv environment and locked FastAPI/Uvicorn runtime dependencies; no database or cloud credentials. The foreground process binds only to loopback and may synchronize the local uv environment/cache. Stop it with Ctrl+C. PD-13 supplies the shared start/stop front door later; no API Make target is added here.

`curl --fail http://127.0.0.1:8000/health` should exit 0 with HTTP 200 and `{"status":"ok"}`. This proves only process liveness, not database/provider/deployment readiness. Connection failure, non-2xx health response, dependency/import error or occupied port is a failure to investigate; do not silently switch targets or replace failure with a fake response. If necessary, explicitly select another local port and use it in both commands. No provider/cloud operation is performed. Live loopback verification used an ephemeral port and an environment containing no cloud credentials, checked the exact JSON response and disabled docs/unknown routes, then stopped its owned process. See [API instructions](../../apps/api/README.md) and the PD-05 step 1 work-log evidence. Typed process-environment settings are implemented in step 2: optional `CLIP_ENVIRONMENT` defaults to local, optional `CLIP_DEBUG` defaults false, invalid/empty values fail startup and production rejects debug. No dotenv/example file is loaded; examples are in `.env.example`. Persistent API tests remain step 5.

## Workstation and stub command registration

The setup guide contains one-time agent-access/clone commands, not implemented application targets. BOOT-00 records actual Linux paths/agent availability; PD-02/13 freeze the verified development toolchain and application commands. PD-10/DL-00/domain owners register explicit test-double scenarios and real integration commands with distinct names/modes. No deployed command may default to fake auth/storage/notification/domain providers; startup validation rejects them. Stub tests never share a label or result classification with cloud/NFR runs.
