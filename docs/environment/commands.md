# Runtime Command Registry

**Canonical path:** `docs/environment/commands.md`

This registry contains implemented commands and planned outputs, distinguished in the table below. Each command-creating task populates exact spellings/arguments/script paths and verifies safe behavior; a planned row is not proof of implementation. The normal front door is root Makefile, unless PD-02 explicitly approves an equivalent and records actual mappings. Root README/CONTRIBUTING/CI must match this registry after PRE-00.

For EACH command record: creator task, exact invocation and required inputs, supported shell/runtime, target/environment, effects and destructive/billable behavior, prerequisite milestone, expected output/exit status, failure/recovery, tests/evidence. Commands must reject unspecified or wrong targets rather than guessing an AWS account/region/database.

| Required command outcome | Creator | Current state |
|---|---|---|
| Install/setup | PD-02/04/07/13 | Python: `uv sync --locked` implemented/verified in PD-04; web: root `npm ci` implemented/verified in PD-07. Combined setup remains pending PD-13. |
| Local start/stop/readiness | PD-05/07/08/13 | API foreground start/stop/health and typed settings verified in PD-05; web loopback start/stop verified in PD-07. PD-08 Step 5 database wrapper implemented with simulated-Docker safety checks; real runtime remains Step 6. Combined lifecycle remains PD-13. |
| Local migration/status/reset and small seed | PD-08/13 | Provisional dbmate SQL, PostgreSQL 18.6 local Compose configuration and Step 5 lifecycle wrapper exist. Real checks remain Step 6/PD-13. Reset is local-only with an explicit deletion flag; no final domain data loader exists. |
| Generator framework/tests | PD-09 | Not implemented |
| Final reference generate/load/validate/fingerprint | SE-01/DATA-READY | Not implemented; requires domain schemas/configuration |
| Python format and non-mutating pinned Black check | PD-04 | Implemented and human-verified at step 3; exact commands and verification below |
| Test/lint/type/build/aggregate CI-equivalent | PD-05/07/12/13 | API/configuration/core/fixture tests implemented in Stream 1; web lint, typecheck, tests, build, and `npm run check` implemented/verified in PD-07. Exact commands below; CI and combined command-front-door integration remain pending PD-12/13. |
| Contract regenerate/stale-check | PD-11/DL-00 | Not implemented |
| Terraform static format/validate (no remote state mutation) | PD-15 | Implemented: run `bash scripts/terraform-static-check.sh` from the repository root with Terraform `1.15.9`. Checks recursive Terraform formatting, then runs `terraform init -backend=false` and `terraform validate` for each root. Exit 0 means all checks pass; a format, provider-download, or validation failure exits nonzero and must be resolved before planning. It does not contact AWS or read remote state; first initialization needs Terraform Registry access and may download the pinned provider into ignored `.terraform/`. |
| Plan/apply/build-release/deploy/verify/rollback/teardown | PD-15/16; domain/EXP additions | PD-15 documents the reviewed plan/apply/verify/cleanup workflow and command templates in `infra/terraform/README.md`; actual targets, state keys, protected plan path, and commands must be selected per approved plan. Cloud operations remain separately gated and are not part of local/CI checks. |
| Search evaluator/load workload/NFR manifests | SE-01 | Not implemented |
| Two-client chat/read-state/latency measurement | CN-01/CN-03 | Not implemented |
| Integrated peak/runtime-loss/DB-restore checks | INT-01 | Not implemented |
| Mixed Lambda package/routing/parity/deploy/workloads/analysis | EXP-02/03–08 | Not implemented |
| Final regression/export/demo/package verification | CLOSE-00 | Not implemented |

An absent command assigned to the selected creation step is an expected output; the agent creates/registers/tests it. An absent prerequisite or uncertain expected effect blocks the dependent action and requires a question. No cloud operation belongs in the generic local/CI aggregate target.

## PD-07 Step 1 — local web bootstrap

Run these commands from the repository root with Node.js 24 LTS and npm 11 on
PATH. The first verified runtime is Node 24.22.0/npm 11.19.1. These commands use
the one root Node manifest and lockfile; they do not invoke the root Makefile.
PD-13 integrates the common front door later. See
[web instructions](../../apps/web/README.md) and the
[build-tool decision](../decisions/web-build-tooling.md).

| Exact command | Inputs and effects | Success | Failure and recovery |
|---|---|---|---|
| `npm ci` | Requires the Step 1 manifest/lockfile and public npm-registry access; replaces this checkout's generated `node_modules/` and uses the contributor's npm cache. No cloud resources or private application data. | Exit 0; dependencies match the lockfile. | Resolve runtime/network or manifest/lock mismatch; do not hide it with unrelated upgrades or a second lockfile. |
| `npm run dev` | Starts the foreground Vite process on `127.0.0.1:5173`; may write generated dependency-cache files inside ignored `node_modules/`. No application API calls/providers are configured. | Vite reports the exact loopback URL and serves the technical HTML/TSX mount point. | An occupied port fails instead of silently moving. Inspect the owned process; do not terminate an unrelated service. Stop this foreground process with Ctrl+C. |
| `npm run build` | Type-checks the app and test/config TypeScript, then bundles into ignored `apps/web/dist/`, replacing that generated output. | Exit 0 from both TypeScript and Vite, with built assets. | Preserve the error and fix the owned source/configuration; a failed check is not deployment evidence. |
| `npm run preview` | Requires the completed local build; starts a foreground loopback server on `127.0.0.1:4173` to inspect `apps/web/dist/`. | Exact preview URL serves the built HTML/assets. | Build first if output is missing; investigate occupied ports. Stop with Ctrl+C. This command does not deploy. |

Each command is local and requires no AWS credentials, database, account, or
production endpoint. The development/preview processes do not detach or create
a persistent service. An unwritable npm cache can be redirected to a writable
contributor-local location with `NPM_CONFIG_CACHE`; do not change credentials or
use a privileged install merely to write the cache. Step 1 checks install,
build, bootstrap rendering, and HTTP start/stop. Step 8 records full scaffold
acceptance after running the registered checks against the implemented routes.

## PD-07 Step 7 — web lint, type, test, build, and aggregate checks

Run from the repository root with Node.js 24 LTS and npm 11. Tool versions are
exactly pinned in the root manifest/lockfile. These commands are local; none
reads cloud credentials, contacts a production endpoint, or requires an
external account. `npm run dev` and `npm run preview` remain foreground,
loopback-only processes stopped with Ctrl+C.

| Exact command | Inputs and effects | Success | Failure and recovery |
|---|---|---|---|
| `npm run lint` | Runs the pinned Biome linter on `apps/web/src/`, `apps/web/tests/`, and the Vite/Vitest configs using `apps/web/biome.json`. Does not rewrite files. | Exit 0 with no lint findings. | Read the reported file/rule, correct the owned code or discuss a rule change; do not suppress unrelated findings. |
| `npm run typecheck` | Runs TypeScript with the app config, then with `apps/web/tests/tsconfig.json` for tests and Vite/Vitest configs. Both configs have `noEmit`; no generated JavaScript is written. | Exit 0 for both projects. | Fix the reported type/config issue, then rerun the command. |
| `npm test` | Runs Vitest once using `apps/web/vitest.config.ts`. It checks the actual route configuration against the approved paths and matches representative static/dynamic/unknown URLs. It also parses source imports to enforce public feature entry points for pages and prevent private cross-domain imports. It does not assert placeholder labels or `.gitkeep` files. | Exit 0 with architecture tests passing. | Use the failing route or import report to fix the route tree/boundary; update expected paths only after an approved route change. |
| `npm run build` | Runs the app/test TypeScript checks, then Vite production bundling into ignored `apps/web/dist/`, replacing generated output. | Exit 0 with built assets. | Resolve TypeScript or bundler errors. Build output is local and is not deployed. |
| `npm run check` | Runs lint, Vitest architecture tests, and production build in sequence; the build includes both TypeScript checks. May replace local ignored `apps/web/dist/`. | Exit 0 only when all checks pass. | Fix the first failing command and rerun the aggregate command. |

The route test's approved-path list is a product-structure assertion and changes
only after a route is approved. It deliberately avoids assertions tied to
placeholder wording/appearance. Page composition connections and the continuing
handoff markers are reviewed during PD-07 Step 8; there is no marker-presence
automated test. PD-12 later wires the agreed web checks into CI, and PD-13 later
adds them to the shared repository command front door.

## Local Python/API commands (PD-04–PD-06)

Run from the repository root on Linux/macOS with GNU Make, uv and Python `>=3.14,<3.15`. The root `pyproject.toml` and `uv.lock` pin dependencies, Black 26.10.1 and pytest 9.1.1. Initial setup may need network access; uv commands may synchronize the ignored `.venv` and local caches. No command below provisions cloud resources or calls a database/provider.

| Purpose / creator | Invocation | Expected result / effects |
|---|---|---|
| Setup — PD-04 | `uv sync --locked` | Install locked runtime/development dependencies; uv may obtain a compatible interpreter. |
| Format — PD-04 | `make format-python` | Runs `uv run --locked black .`; rewrites discovered Python source. Review the diff. |
| Check format — PD-04 | `make check-python-format` (also plain `make`) | Runs `uv run --locked black --check --diff .`; exit 0 when formatted, nonzero on drift/tool failure. Leaves source unchanged. |
| Start API — PD-05 | `uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000` | Foreground loopback listener; stop with Ctrl+C. |
| Health — PD-05 | `curl --fail http://127.0.0.1:8000/health` | Exit 0, HTTP 200, `{"status":"ok"}`. Process liveness only. |
| All tests — PD-04/05 | `uv run --locked pytest -q -W error` | Collect API and shared fixture tests; warnings fail the run. |
| API tests — PD-05 | `uv run --locked pytest apps/api/tests -q -W error` | API/configuration and shared-core checks. |

For setup/start failures, inspect the dependency, import, configuration or occupied-port error. If choosing another local port, update both start and health invocations. For formatting drift, run the formatter, review changes and rerun the check. Locked commands do not rewrite an outdated lockfile; resolve dependency/configuration errors before retrying.

Tests use synthetic data, in-memory ASGI requests, temporary files and bounded local subprocesses; they may write local caches and restore changed environment/logger settings. They need no external services or credentials. Pytest exit 0 means collected tests passed; exit 1 means failure; exit 5 (no tests) is not a pass. Investigate failures. Root pytest configuration supplies import paths; TestClient uses pinned development-only httpx2.

Settings, request IDs, JSON logging and production provider guards are documented in the [API guide](../../apps/api/README.md) and [core guide](../../apps/api/app/core/README.md). No dotenv file is loaded automatically. Python lint/type tooling, CI wiring and combined lifecycle/test Make targets remain future PD-12/13 outputs. Tool choices: [test tooling decision](../decisions/python-test-tooling.md); verification evidence: [work log](../status/work-log.md).

## Focused core/fixture checks (PD-06/PD-10)

These subsets use the same prerequisites, effects and exit rules above; the full test command includes all of them.

| Coverage / creator | Invocation |
|---|---|
| Shared conventions — PD-06 | `uv run --locked pytest apps/api/tests/core -q -W error` |
| Security boundaries — PD-06 | `uv run --locked pytest apps/api/tests/core/test_security_boundaries.py -q -W error` |
| Shared fixtures and API usage — PD-10 | `uv run --locked pytest tests/fixtures/core apps/api/tests/core/test_shared_fixtures.py -q -W error` |
| Fixture library/scripted providers — PD-10 | `uv run --locked pytest tests/fixtures/core -q -W error` |
| Production provider matrix — PD-10 | `uv run --locked pytest apps/api/tests/core/test_provider_settings.py apps/api/tests/core/test_security_boundaries.py -q -W error` |
| Retry/duplicate/concurrency/failure/validation scenarios — PD-10 | `uv run --locked pytest apps/api/tests/core/test_shared_scenarios.py -q -W error` |
| Redacted diagnostics — PD-10 | `uv run --locked pytest tests/fixtures/core/test_privacy.py -q -W error` |

Security checks include request-ID spoofing and credential-free entry-point children (10-second timeout). Production rejects fake identity/email/storage selections and development auth; empty/unsupported provider selections fail. Safe configurations supply positive controls. Test-only scripts follow the [reviewed adapter interfaces](../../tests/fixtures/core/adapter-interfaces.md); domain retry/deduplication/transaction and OTP behavior remain with their owning contracts.

The privacy check launches a credential-free pytest child (15-second timeout) that intentionally fails; the parent passes only when the failure report is correctly redacted. See [fixture usage and snapshot limits](../../tests/fixtures/core/README.md). Fixtures do not establish real provider/domain integration or cloud/NFR acceptance.

## Workstation and stub command registration

PD-08 Step 3 reserves `database/migrations/20261018094330_mvp_tables.sql`,
`20261018094331_mvp_integrity.sql` and `20261018094332_initial_catalogue.sql`;
expected head is `20261018094332`. `database/dbmate.version` pins 2.36.0 and
`database/tests/schema-smoke.sql` prepares rollback-only synthetic integrity
checks for a validated local `clip_test_` database. Step 5 now implements the
local lifecycle commands below; their real Docker/PostgreSQL execution remains
Step 6. Use one migration operator; the pinned version has no
CLI-wide migration lock. See [database instructions](../../database/README.md)
for per-transaction advisory locks and current verification limits.

PD-08 Step 4 adds root `docker-compose.yml`: image `postgres:18.6-bookworm`,
project `clip-local`, service `postgres`, local database/user `clip_local`,
required local-only `CLIP_LOCAL_POSTGRES_PASSWORD`, TCP `127.0.0.1:5432`, and
project-scoped volume `clip_local_postgres_data`. Root `.env.example` contains
only a clearly fake example for that setting. Configuration source passed YAML
parsing and the official Compose JSON schema; Docker/Compose runtime validation
and startup have not run on Mohit's Mac. Do not print interpolated configuration
with supplied credentials. Step 5 registers exact lifecycle invocations below;
source/simulated checks do not establish real runtime success. CI must
match PostgreSQL 18.6 through PD-12/integration; no CI file is changed here.

### PD-08 Step 5 — local database commands

Run from the repository root using Bash 3.2+, local Docker Engine and Compose v2.
All lifecycle actions require process environment `CLIP_LOCAL_POSTGRES_PASSWORD`
(ASCII URL-unreserved characters only); no dotenv is read. Target is fixed to
the Unix-socket Docker context, Compose project `clip-local`, PostgreSQL 18.6,
database/user `clip_local`, loopback 5432 and its named local volume. URL/PG
target and Docker endpoint overrides fail closed. Initial image downloads need
registry access; no cloud resource/provider is invoked.

| Exact invocation | Effect / success / failure |
|---|---|
| `bash database/local-db.sh start` | Create/start only the local service, then authenticated readiness. Nonzero on unavailable tools, ownership/configuration/port conflict or readiness failure; inspect sanitized output. |
| `bash database/local-db.sh wait` | Authenticated TCP `SELECT 1`, up to 30 attempts (2-second connect timeout and pauses). Exit 0 means connectivity only; absent container/timeout fails. |
| `bash database/local-db.sh migrate` | Pinned dbmate 2.36.0, fixed local URL, strict transactional migrations, no schema dump/implicit dotenv. Exit 0 means the tool finished; Step 6 separately verifies expected head/schema. Inspect failures before retry; never automatically reset. |
| `bash database/local-db.sh status` | Display migration state. Pending migrations can appear with exit 0; compare expected head `20261018094332`. |
| `bash database/local-db.sh stop` | Stop validated local container; retain all volume data. Absent container succeeds. |
| `bash database/local-db.sh reset --confirm-delete-local-data` | Warn and permanently delete only the validated service container and `clip-local_clip_local_postgres_data`. Requires deliberate approval of that destructive action. No force/prune/broad volume deletion; leaves DB stopped. Missing confirmation fails before Docker. |
| `bash database/local-db.sh --help` | Fixed usage; no tools/password required. |
| `bash database/tests/local-db-safety.sh` | 22 simulated-Docker wiring/refusal/redaction cases; exit 0 on success, no registry/engine/database/cloud calls. |

The wrapper preserves failing command status, redacts the local password and
serializes actions through a per-user temporary lock. Ownership/target/lock
failure requires inspection, not bypassing/relabeling. Inspect a stale lock only
after confirming its previous operator has stopped. Never print interpolated
configuration, enable credential tracing or put real secrets in evidence.
See [database instructions](../../database/README.md#local-lifecycle-commands-pd-08-step-5)
for function purposes, exact input limits, reset/recreate and safe recovery.
Step 5 passed shell syntax and simulated safety checks on system Bash 3.2;
Docker/Compose/container execution, image inspection, persistence and actual
reset/recreate remain Step 6; native SQL/tool checks now pass below. PD-13 owns root
Makefile integration; no root Makefile/CI/other stream implementation was edited.

### PD-08 Step 6 — native macOS verification checkpoint

Mohit selected native testing now and explicitly deferred other checks. Native
tools were built in `/tmp` without changing global/Homebrew installations.

| Exact invocation / inputs | Target, effects and expected result |
|---|---|
| `bash database/tests/native-checks.sh /tmp/clip-pd08-native.pKC5jz/pgsql /tmp/clip-pd08-native.pKC5jz/bin/dbmate` | Requires macOS/Bash 3.2+, native PostgreSQL 18.6 and dbmate 2.36.0 at these explicit tool locations. Creates only its own private `/tmp/clip-pd08-native-check.*` cluster/database `clip_test_native`; disables TCP, uses an owner-only socket, applies/repeats migrations, runs smoke twice, rolls back all three migrations, reapplies, compares ordered schema inventory and stops its cluster. Logs/data retained under printed evidence path. Nonzero on any failure or stop failure; inspect retained logs, never substitute an existing cluster. |

Fresh child environments and fixed new targets prevent ambient database/provider
configuration from redirecting checks. Local socket trust is confined to the
private temporary directory; it does not verify SCRAM/TCP or production auth.
Native tools used the checksum-verified official PostgreSQL source with build
flags `--without-icu --without-readline --without-zlib`, UTF-8/C locale, and
dbmate's pinned Go module. Tool paths under `/tmp` may disappear; verify/rebuild
exact versions before rerunning if absent. No Homebrew service or VM is created.

Passed: native version checks, head `20261018094332`, Applied 3/Pending 0,
23 tables/20 functions/32 triggers, catalogue counts, repeated migrate, smoke
twice, three down migrations, reapply and identical runtime inventories. Evidence
is `/tmp/clip-pd08-native-check.0buobO`. Runtime tests corrected the wrapper's
flag order to `migrate --strict`; `status`/`rollback` omit that command-only flag.
The corrected Compose wrapper's 22 simulated cases also passed. The initial
sandbox shared-memory denial and corrected harness/CLI failures remain recorded
in the work log; no failure is counted as a pass.

Deferred: container image/Compose runtime, loopback TCP/SCRAM readiness,
stop/start volume persistence, approved reset/recreate, platform/locale parity,
multi-connection concurrency, query-plan checks, affected-owner acceptance and
CI same-version checks. Native results do not close PD-08/PRE-00. See the
[database verification notes](../../database/README.md#native-macos-checkpoint--2026-10-18).

One-time clone/agent setup belongs in the [workstation guide](wsl-and-first-session.md). Future command owners must register explicit targets and effects above. PD-10/DL-00/domain owners register explicit test-double scenarios and real integration commands with distinct names/modes. No deployed command may default to fake auth/storage/notification/domain providers; startup validation rejects them. Stub tests never share a label or result classification with cloud/NFR runs. No cloud operation belongs in the generic local/CI aggregate target.
