# Runtime Command Registry

## SE-01 Step 8 — functional contract checks

| Command | Coverage/evidence limit |
|---|---|
| `uv run --locked pytest apps/api/tests/domains/listings/test_browse.py apps/api/tests/domains/listings/test_browse_contract.py apps/api/tests/domains/listings/test_browse_postgres.py apps/api/tests/domains/search data/tests tests/contracts -q -W error` | Current isolated browse/validation/transport, reviewed OpenAPI/source response conformance, Search fixtures/data and existing contract tests. Node/npm must be on process PATH for contract tooling. Real SQL remains skipped without the disposable runner. |
| `npm run check` | Includes `discovery-contract.test.ts`: generated request/response typing, reviewed OpenAPI public property sets and handwritten reader compatibility, plus existing lint/types/build/behavior tests. No Python subprocess added to web-only checks. |

Use repository-local Node/uv PATH/cache prefixes from the workstation guide
where appropriate. See the [functional coverage ledger](../evaluation/domain/se-01/README.md)
for every pending real check. Test fixtures and metadata conformance do not
accept ranking, SQL/auth, NFRs or readiness. No generated file is hand-edited.

## SE-01 Step 7 — initial discovery UI preview

Creator/current scoped writer: Mohit (C). Uses the existing root package lock;
no new dependency or product route. [Web checkpoint](../../apps/web/README.md#se-01-step-7--first-discovery-ui-checkpoint).

| Command | Target/effect and evidence limit |
|---|---|
| `CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true .venv/bin/python apps/api/tests/domains/search/browser_preview.py --isolated-search-ui` | Foreground fixed loopback 8000, explicit synthetic read-only UI scripts, no DB/auth/storage. Rejects default/production/ambient DB/AWS and non-opt-in/cross-origin clients; Ctrl+C stops it. Never a real provider or NFR check. |
| `PATH="$PWD/.tools/node/bin:$PATH" NPM_CONFIG_CACHE="$PWD/.tools/npm-cache" NPM_CONFIG_USERCONFIG=/dev/null VITE_SEARCH_UI_PREVIEW=true .tools/node/bin/npm run dev` | Existing loopback 5173 Vite server with explicit development fixture disclosure/header. Open `http://127.0.0.1:5173/`; Ctrl+C stops it. No global PATH edits or public exposure. Production builds omit the preview branch. |
| `PATH="$PWD/.tools/node/bin:$PATH" NPM_CONFIG_CACHE="$PWD/.tools/npm-cache" NPM_CONFIG_USERCONFIG=/dev/null .tools/node/bin/npm run check` | Registered lint/Vitest/type/build suite using repo-local Node/npm; replaces ignored dist only. Does not complete human desktop/phone/browser or real SQL/auth integration checks. |

Pause at the first usable screen for human observations/version/viewports per
the browser procedure. Future visible increments need renewed checks. The normal
app still calls the real API when the development fixture flag is absent.

## SE-01 Steps 3–6 — browse/search checks

| Command | Behavior and evidence limit |
|---|---|
| `uv run --locked pytest apps/api/tests/domains/listings/test_browse.py apps/api/tests/domains/search data/tests -q -W error` | Isolated HTTP/auth/privacy, current-read/cache-header behavior, strict query/filter checks, Search-owned saved boundary fixtures, SQL parameterization, corpus and loader refusals. Scripted pages/states do not prove SQL or real saved behavior. |
| `uv run --locked python scripts/check_database.py --listings-store` | Existing pinned Docker/PostgreSQL runner executes `test_browse_postgres.py`: real availability/time/retirement predicates and state transitions, title/description/stemming/plain-text search, generated-vector updates, GIN eligibility, filters/catalogue and stable paging. Fixtures force rollback. Planner diagnostic is not performance evidence; no real saved API is supplied. Requires Docker; not run successfully here. |
| `uv run --locked pytest apps/api/tests/domains/listings/test_browse_postgres.py -q -W error` | Skips explicitly without the runner's `LISTINGS_TEST_DATABASE_URL`; a skip is not SQL acceptance. Do not supply a shared/cloud/application database. |

Runtime entry: reviewed Listings-owned `GET /listings`; Step 4 adds plain-text
`q` through native English full-text matching. Step 5 adds the reviewed filters
and recency/price sorts with UUID ties. Invalid ranges/types/bounds/codes use
shared 422 errors. No new monetary cap or request-rate quota is invented.
Existing vector/GIN definitions are reused, with no new migration or search service. Real
Identity/SQL/index checks and affected-owner review remain pending. Step 6 sets
discovery responses to `private, no-store`; current eligibility/storage is
rechecked. Retained unavailable saved summaries/content-free retired markers are
distinct SE-02 behavior, still awaiting actual providers, API and privacy checks.

## SE-01 Step 2 — isolated schema-shaped data

Creator/current writer for this bounded registry addition: Mohit (C),
`task/se-01-search`. Existing Make/PD-09 commands remain unchanged. With locked
dependencies installed, `.venv/bin/python` may replace `uv run --locked python`
on the repository-local setup. [Format](../../data/formats/search-preview.md)
and [local prerequisites](../../data/README.md#se-01-isolated-schema-shaped-corpus).

| Command | Target/effect | Success/failure |
|---|---|---|
| `uv run --locked python -m data.generators.search_preview generate --name <fresh-name> --seed 42 --users 5000 --listings 1000 --logical-time 2026-10-24T09:00:00.000000Z` | Creates only `data/runs/<fresh-name>/dataset.json` and `manifest.json`; schema-shaped preview with explicit logical clock. | Prints fingerprint, exit 0; exit 2 on invalid/unsafe/existing targets. No overwrite or database writes. |
| `uv run --locked python -m data.generators.search_preview validate --name <name>` | Verifies closed schema, current source binding, counts, fingerprint and retained manifest. | Prints fingerprint, exit 0; altered/stale/unsafe data exits 2. |
| `CLIP_ENVIRONMENT=test uv run --locked python -m data.generators.search_loader --name <name> --socket-dir <canonical-local-directory> --isolated-preview` | Fixed Unix-socket `clip_test_search_preview` database / `clip_search_preview` role, empty migrated fixture tables only; atomic user/listing/image-metadata insertion. No provisioning, credentials, storage calls or deletes. | Exit 0 only after SQL constraints/counts/commit; otherwise safe exit 2. Real PostgreSQL execution remains unverified. Refuses ambient DB/libpq overrides and nonempty/mismatched targets. |
| `uv run --locked pytest data/tests -q -W error` | Existing plus schema-shaped corpus/contract and loader refusal tests; local synthetic data only. | Passing tests are isolated evidence, not SQL/FK/index/image integration. |

Reset is intentionally unsupported. Use no truncate/drop/reset workaround;
destructive cleanup requires a separately approved exact target. Final real
schema/count/FK/image/index checks and human labels remain SE-01 steps 2/4/9.

**Canonical path:** `docs/environment/commands.md`

This registry contains implemented commands and planned outputs, distinguished in the table below. Each command-creating task populates exact spellings/arguments/script paths and verifies safe behavior; a planned row is not proof of implementation. The normal front door is root Makefile, unless PD-02 explicitly approves an equivalent and records actual mappings. Root README/CONTRIBUTING/CI must match this registry after PRE-00.

For EACH command record: creator task, exact invocation and required inputs, supported shell/runtime, target/environment, effects and destructive/billable behavior, prerequisite milestone, expected output/exit status, failure/recovery, tests/evidence. Commands must reject unspecified or wrong targets rather than guessing an AWS account/region/database.

**Status reconciliation (2026-10-19):** The user confirmed all previously pending PD-08/09/12/13/15 acceptance gates. Step-specific notes below retain checkpoint-time status; see the work log for current acceptance. PD-19 Step 2 reran the clean local command path. Final schema-aware data loading remains SE-01/DATA-READY.

| Required command outcome | Creator | Current state |
|---|---|---|
| Install/setup | PD-02/04/07/13 | Python: `uv sync --locked` implemented/verified in PD-04; web: root `npm ci` implemented/verified in PD-07. `make setup` and clean-checkout verification passed in PD-13/PD-19 Step 2. |
| Local start/stop/readiness | PD-05/07/08/13 | API and web loopback checks plus the PD-08/13 lifecycle gates are complete; user confirmed the previously pending acceptance on 2026-10-19. PD-19 Step 2 repeated API/web/DB start and stop locally. |
| Local migration/status/reset and small seed | PD-08/13 | PostgreSQL 18.6/dbmate 2.36.0 wrapper, migrations and small catalogue seed are verified; user confirmed the previously pending PD-08/13 acceptance on 2026-10-19. Reset remains local-only with an explicit deletion flag; no final domain data loader exists. |
| Generator framework/tests | PD-09 | All six local steps/audit and final acceptance were user-confirmed on 2026-10-19; 63 data tests and pinned Black passed. No domain loader/evaluator. |
| Final reference generate/load/validate/fingerprint | SE-01/DATA-READY | Not implemented; requires domain schemas/configuration |
| Python format and non-mutating pinned Black check | PD-04 | Implemented and human-verified at step 3; exact commands and verification below |
| Test/lint/type/build/aggregate CI-equivalent | PD-05/07/12/13 | `make check` runs the shared Python/web/database/contracts/secret gates used by CI; it passed in PD-19 Step 2. PD-12/13 hosted acceptance and lifecycle front door were user-confirmed complete on 2026-10-19. |
| Contract regenerate/stale-check | PD-11/DL-00 | Health generation/check and actual API schema/consumer regression checks implemented in PD-11; full domain declarations remain DL-00. Exact commands below. |
| Terraform static format/validate (no remote state mutation) | PD-15/13 | `make terraform-check` with Terraform 1.15.9: format check and backend-free validation, readonly provider lock; individual targets documented below. Public provider downloads may be needed; no cloud login or apply. |
| Plan/apply/build-release/deploy/verify/rollback/teardown | PD-15/16; domain/EXP additions | PD-15 documents reviewed plan/apply/verify/cleanup. PD-16 per-run ECS capacity plans and RDS stop/start templates are in `infra/terraform/shared/test/README.md`; select exact targets and review/approve each cloud operation. These are not local/CI checks. |
| Isolated Listings demo lifecycle | LI-02 Step 12 | Implemented locally as `make li02-demo-start AWS_PROFILE=<approved-profile>` and `make li02-demo-stop AWS_PROFILE=<approved-profile>`. Start continues a recorded partial run from its saved phase; there is no separate resume command. The driver gates image publication, database operations, exact Terraform plans, public app start, and teardown. |
| Search evaluator/load workload/NFR manifests | SE-01 | Not implemented |
| Two-client chat/read-state/latency measurement | CN-01/CN-03 | Not implemented |
| Integrated peak/runtime-loss/DB-restore checks | INT-01 | Not implemented |
| Mixed Lambda package/routing/parity/deploy/workloads/analysis | EXP-02/03–08 | Not implemented |
| Final regression/export/demo/package verification | CLOSE-00 | Not implemented |

An absent command assigned to the selected creation step is an expected output; the agent creates/registers/tests it. An absent prerequisite or uncertain expected effect blocks the dependent action and requires a question. No cloud operation belongs in the generic local/CI aggregate target.

## LI-02 Step 12 demo lifecycle

Run from the repository root with Python 3, AWS CLI, Terraform 1.15.9, Docker
Buildx and an explicitly approved AWS profile. The command fixes the target to
account `335523638354`, Region `ap-south-1`, the dedicated LI-02 ECS cluster and
ASG, disposable LI-02 RDS, and existing shared API ECR repository. The VPC,
private workload subnet and NAT are shared dependencies; the shared ECS cluster,
capacity provider, ASG and host security group are neither queried for workload
state nor changed. Start refuses modified LI-02 build inputs and requires a
committed source revision. No credentials, URL values, or database passwords
are printed or written to Terraform state. Local baseline metadata is ignored
by Git and contains only resource IDs/status, run ID and image digests.

| Exact command | Effects and gates | Expected result / recovery |
|---|---|---|
| `.venv/bin/pytest apps/api/tests/domains/listings/test_demo_database_lifecycle.py -q` | Runs the actual Listings lifecycle shell script with a controlled local psql process. Checks metadata capture, empty/existing/owned/mismatched states, invalid/failed queries, idle clients, private diagnostics and bounded client settings. No AWS, database or Docker access. | 27 passing regression cases, including the URL-only seed secret contract and admin-secret/invalid-URL rejection; these do not prove real PostgreSQL bootstrap, migrations or cleanup. |
| `.venv/bin/pytest apps/api/tests/domains/listings/test_li02_demo_driver.py -q` | Exercises the cloud driver's AZ retry decision, partial-RDS refusal, exact AWS capacity-error classification, absent-provider handling, dedicated cluster/task target, ASG/root-volume teardown target, durable bridge-task metadata block, and single run-level authorization persistence. It does not call AWS, Terraform plans/applies, Docker, or a database. | 11 passing local lifecycle-driver cases; these do not prove a real EC2 boot, AWS capacity response, or cloud cleanup. |
| `make li02-demo-start AWS_PROFILE=<approved-profile>` | One command checks account/budget/state, builds and pushes immutable UI/API and database images, creates the run URL SecureString, owner-checks/resets only `clip_test_listings`, migrates/seeds it, creates the private LI-02 ECS cluster/ASG/host plus temporary public ALB and disposable encrypted RDS, then starts one app task. It asks once for `START LI02 DEMO <run-id>` before run writes. Every Terraform plan still displays its saved plan and requires that exact SHA-256; if AWS explicitly returns `InsufficientDBInstanceCapacity` for `ap-south-1b`, the driver confirms no partial RDS remains and prepares a separate hash-gated plan for `ap-south-1a`. Shared RDS and shared ECS resources are untouched. | Exit 0 prints the generated HTTP URL for desktop and phone checks. On failure, retain `.demo-baseline.json` and rerun start to continue or stop to clean up. No HTTPS/domain is configured. |
| `make li02-demo-stop AWS_PROFILE=<approved-profile>` | One `STOP LI02 DEMO <run-id>` confirmation authorizes stop of the app, owner-checked deletion of only `clip_test_listings`/its login, removal of this run's S3 prefix and URL parameter, temporary ALB/subnet/route/service/tasks/disposable RDS, log streams, and termination of the dedicated EC2 host/root volume. Run ECR images are retained for reproducible restart. The Terraform removal plan still needs its own exact hash approval. | Exit 0 leaves the empty LI-02 cluster/provider/ASG and host IAM/SG, Step 4 bucket/IAM/log group/state backend, shared RDS/database, VPC/NAT and shared ECS resources intact. The baseline remains if cleanup fails, so retry the same command. |

The disposable RDS adds about USD 0.021 per available hour for compute in
`ap-south-1`, plus 20 GiB of gp3 storage while it exists; RDS bills in one-second
increments with a 10-minute minimum. The exact run cost also includes the
temporary ALB, one `c7i-flex.large` private LI-02 EC2 host, its 30-GiB gp3
root disk, and shared NAT data transfer; check current billing data before
apply. Stop removes the host and root disk as well as disposable LI-02 RDS.
The empty LI-02 ECS/ASG control resources remain but have no running compute.
This driver has not yet completed an AWS run with the separate cluster and
database. Refresh the
current account inventory before using it. If interrupted, keep the local
baseline file, then rerun `start` to continue or
`stop` to clean up; the script refuses to guess an account, resource, or
database target. Cloud actions still require review of the current exact plans,
cost and public exposure.

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
| `npm run dev` | Starts foreground Vite on `127.0.0.1:5173`; may write ignored dependency caches. LI-01 create/detail calls `/api`, forwarded only in development to local API `127.0.0.1:8000`. No test auth is activated by this command. | Exact loopback URL serves the app; Listings API success requires its configured dependencies. | An occupied port fails. Stop only the owned foreground process with Ctrl+C. |
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

Settings, request IDs, JSON logging and production provider guards are documented in the [API guide](../../apps/api/README.md) and [core guide](../../apps/api/app/core/README.md). No dotenv file is loaded automatically. PD-12/13 provide CI wiring and combined lifecycle/test Make targets; Python lint/type tooling remains deferred. Tool choices: [test tooling decision](../decisions/python-test-tooling.md); verification evidence: [work log](../status/work-log.md).

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

## PD-16 database-task deadlines

The fixed ECS task definitions embed `infra/terraform/shared/test/scripts/setup-db-role.sh` and `probe-db.sh`. Their pinned Linux PostgreSQL client image must contain GNU `timeout`. Each script sets `PGCONNECT_TIMEOUT=10` and `PGOPTIONS='-c statement_timeout=30000 -c lock_timeout=30000'`, then runs its single psql process with `timeout --signal=TERM --kill-after=5s 60s`. Total client execution stops within 60 seconds plus up to 5 seconds for forced termination; this excludes ECS scheduling. Missing tools, failed SQL and timeouts exit nonzero with safe messages. No raw client diagnostics or credentials are emitted. Inspect before retrying; a timeout does not establish whether earlier work committed. The setup script also checks effective logging in the same connection before ACL/role/password changes and aborts on unsafe settings, including error-statement logging; the approved DEC-05 correction applies and verifies only transaction-local suppression beforehand, restoring prior settings on commit/rollback. Denied permissions or remaining unsafe settings abort without grants, global changes or retries.

Local regression command: `uv run --locked pytest tests/architecture/test_db_task_timeouts.py -q -W error`. Controlled client stand-ins exercise success, private-error suppression, a stuck process that ignores TERM, caller timeout overrides and a missing timeout tool. A real GNU timeout uses shortened test deadlines. No database/cloud access occurs; the check also runs in the root test suite. See the [runbook](../../infra/terraform/shared/test/README.md#database-task-deadlines) and [approved decision](../decisions/database-task-deadlines-and-manual-image-cleanup.md).

## PD-16 Step 12 read-only review

Use the approved non-root profile/account. `aws budgets describe-budget`, `describe-notifications-for-budget` and `describe-subscribers-for-notification` target budget `CLIP-Account-Actual-Spend-From-2026-10-17` in account `335523638354`, endpoint `us-east-1`; capture subscriber output privately and report only counts/matches. Project resources remain Mumbai. No notification-send/update command is part of this review. `aws cloudwatch get-metric-statistics` reads standard ECS/EC2/RDS metrics for a bounded run window in `ap-south-1` (300-second periods, Average/Maximum/Minimum); no custom metric or load is created. [Recorded inputs/results, billing lag and query-cost boundary](../evaluation/foundation/pd-16/step12-cost-review.md).

## PD-16 Step 7 publication evidence

The authorized one-off [ECR publication](../evaluation/foundation/pd-16/ecr-publication.md) used `sudo docker` login with temporary auth and the AWS CLI layer/manifest APIs to preserve the verified OCI bytes. Its evidence records the exact immutable source tag, remote digest, verification, limits and API sequence; no reusable upload wrapper was introduced. Repeat uploads need their own exact artifact/target approval.

## Local API container image — PD-16 Step 4

Run from the repository root with Docker Engine. Record `git rev-parse HEAD`,
`git status --short`, and the engine architecture with the local check: it
builds the current worktree, including uncommitted API changes. The later
registry image must be rebuilt from the exact reviewed commit.

The current engine has only the legacy builder, which ignores the
Dockerfile-specific ignore file and would send the repository's 1.7 GB context.
The Dockerfile avoids BuildKit-only instructions, and this procedure stages an
allowlisted context under `/tmp` containing the Python and web lockfiles, API
and web source, generated frontend types, Dockerfile and its ignore file. The
image serves the built website and API from one process; the demo disclosure is
enabled only with `--build-arg VITE_LISTINGS_PUBLIC_DEMO=true`. The Docker build
uses the host's native architecture and never contacts AWS:

```sh
(
set -eu
build_context=$(mktemp -d /tmp/clip-api-pd16.XXXXXX)
image_tag="clip-api:pd16-local-${build_context##*.}"
container_id=
image_id=
# Only clean artifacts created by this invocation; preserve its exit status.
cleanup() {
  result=$?
  trap - EXIT
  if [ -n "$container_id" ]; then
    sudo docker rm --force "$container_id" >/dev/null 2>&1 || true
  fi
  if [ -n "$image_id" ]; then
    sudo docker image rm "$image_tag" >/dev/null 2>&1 || true
  fi
  rm -rf "$build_context"
  exit "$result"
}
trap cleanup EXIT
mkdir -p "$build_context/apps/api" "$build_context/apps/web" "$build_context/contracts"
cp pyproject.toml uv.lock "$build_context/"
cp -R apps/api/app "$build_context/apps/api/"
cp -R apps/web "$build_context/apps/"
cp -R contracts/generated "$build_context/contracts/"
cp package.json package-lock.json "$build_context/"
cp apps/api/Dockerfile apps/api/Dockerfile.dockerignore "$build_context/"
sudo docker build --file "$build_context/Dockerfile" --tag "$image_tag" "$build_context"
image_id=$(sudo docker image inspect --format '{{.Id}}' "$image_tag")
container_id=$(sudo docker create --publish 127.0.0.1:8000:8000 "$image_tag")
sudo docker start "$container_id" >/dev/null
# A port conflict fails this run; never stop another process to free the port.
curl --retry 20 --retry-all-errors --retry-delay 1 --max-time 2 --fail http://127.0.0.1:8000/health
attempt=0
health=starting
while [ "$attempt" -lt 40 ] && [ "$health" = starting ]; do
  health=$(sudo docker inspect --format '{{.State.Health.Status}}' "$container_id")
  [ "$health" = healthy ] || [ "$health" = unhealthy ] || sleep 1
  attempt=$((attempt + 1))
done
[ "$health" = healthy ]
)
```

The native ARM64 check is sufficient for Step 4. The user later confirmed the previously pending PD-08/PD-13 native-platform and database compatibility gates (2026-10-19); see the work log. PD-16 Step 7 subsequently built, uploaded and verified the `linux/amd64` image from its reviewed commit; see [PD-16 publication evidence](../evaluation/foundation/pd-16/README.md). The approved local procedure uses `sudo docker` on this host.

PD-16's ECS scale-to-zero and RDS stop/start procedures are documented in the
[shared test Terraform runbook](../../infra/terraform/shared/test/README.md#ecs-capacity-lifecycle).
The [target-specific RDS stop/resume plan](shared-test-rds-operations.md) supplies explicit profile, instance, waiter and status templates. These require separate reviewed cloud operations and are not part of this local
image build or `make check`.

## Native AMD64 API-image validation — PD-16 Step 7 local check

The [native validation evidence](../evaluation/foundation/pd-16/native-amd64-image-validation.md) records the exact clean source SHA, allowlisted `git archive` inputs, `DOCKER_BUILDKIT=0 docker build --platform linux/amd64` command, platform/non-root/runtime check and loopback HTTP/Docker-health checks. That run used Docker directly because the contributor already had local socket access; it did not require sudo or emulation. The archive excludes ignored/untracked files as well as all credentials, Git metadata and dependency caches.

Unlike the temporary Step 4 smoke image above, this successfully validated image is deliberately retained under its commit-derived local tag for later handoff. Remove only the owned smoke container and temporary context after recording the outcome; do not overwrite an existing tag or prune unrelated images. Public image/package downloads can occur. Building and retaining a local image does not authorize Git publication, ECR upload, deployment or a cloud action; the local image ID is not proof of a remote registry manifest digest. Follow the separate exact-upload approval before publishing.

## PD-09 Step 2 — schema-independent preview generator

From the repository root, run
`uv run --locked python -m data.generators --seed 42 --users 3 --listings 2`.
Requires the locked Python 3.14 project environment. All three inputs are
mandatory: signed 64-bit seed, user/listing counts each 0–100,000. Exit 0 streams
five deterministic JSON Lines in this example; invalid configuration exits 2
without output. Predictable test-only UUIDv4 IDs, controlled synthetic labels and
`example.invalid` addresses are preview scaffolding, not domain records.

The generator writes stdout only and accepts no output path/database/provider
target; no file, database or cloud mutation occurs. uv may synchronize the local
ignored environment/cache. Fix invalid inputs before retrying; no reset is
needed. See [generator contract](../../data/generators/README.md). Steps 3–4
supply the [manifest format](../../data/formats/manifest.md), build/validation
API and safe file commands below. Query-label preparation remains Step 5 and
persistent tests/full closeout Step 6. Actual final adapters/loading remain
SE-01/DATA-READY. Initial determinism, UUID/RNG/count/hook and fake-input safety
checks passed; pinned Black check passed across the repository.

### PD-09 Step 4 — local preview run files

Same repository-root/Python 3.14/locked-environment prerequisites as above. All
targets are fixed below `data/runs/<name>`; a name is 1–64 lowercase ASCII
letters/digits/underscore/hyphen starting with a letter/digit. No custom path,
database URL, overwrite, reset or provider input is accepted.

| Exact command | Effects / success / failure |
|---|---|
| `uv run --locked python -m data.generators.files generate --name preview-42 --seed 42 --users 3 --listings 2` | Create a new owner-private run directory with exclusively created `dataset.json` and retained `manifest.json`. Print logical fingerprint and exit 0. Existing/unsafe targets or invalid inputs exit 2. Never overwrite; choose a fresh name. |
| `uv run --locked python -m data.generators.files validate --name preview-42` | Read only that run's bounded regular UTF-8 JSON files, reject duplicate keys/unsafe paths, validate the closed bundle and matching manifest, print fingerprint/exit 0. Incomplete/tampered/invalid runs exit 2; inspect before separately deciding cleanup. |
| `uv run --locked python -m data.generators.files load` | Always exits 2 naming DL-00, accepted ID-READY/LI-CORE and SE-01 adapter/loader validation prerequisites. No database connection, write or fake success. |

`.gitignore` excludes regenerable `data/runs/*/dataset.json` only; source, formats,
inputs and manifests stay eligible for Git. Retain meaningful reviewed manifests
with the code revision; regenerate under a fresh name and compare fingerprints.
IO interruption can leave partial files; validation must pass before use. No
reset/removal command is supplied and no cloud resource is touched. See
[data usage/safety/retention](../../data/README.md). Successful command wiring,
repeat fingerprints, overwrite/path/symlink/input/duplicate-key/manifest mismatch
refusals and the unavailable-loader diagnostic passed initial checks in isolated
temporary run directories. Ignore-rule and pinned Black checks passed; full
persistent tests remain Step 6. No final domain data was loaded.

PD-09 Step 5 supplies the [query-label format/review procedure](../../data/formats/query-labels.md)
and [empty draft template](../../data/evaluation/query-labels.template.json).
These are retained source artifacts, not executable evaluator/label-loader
commands. SE-01 Step 9 supplies actual dataset-bound human labels and evaluator;
no labeled-set generation, DATA-READY or NFR-04 result is claimed here.

### PD-09 Step 6 — persistent tests and Python checks

| Exact command | Inputs/effects and expected result |
|---|---|
| `uv run --locked python -m pytest data/tests -q -W error` | Python 3.14, locked pytest 9.1.1; synthetic values and private temporary filesystem only, plus read-only Git ignore queries. Exit 0: 63 tests passed at this checkpoint. No database/cloud/provider access. |
| `uv run --locked python -m pytest apps/api/tests tests data/tests -q -W error` | Run existing Python/API/core tests plus PD-09 data tests explicitly. Exit 0: 361 passed at this checkpoint. Retain failures; repair only owned code or coordinate shared findings. |
| `make check-python-format` | Existing pinned Black 26.10.1 read-only gate. Exit 0: 42 Python files unchanged at this checkpoint. |

Root pytest defaults do not yet discover `data/tests`; `python -m pytest` and
explicit test paths keep the data import/collection unambiguous without editing
another owner's shared configuration. PD-12/13 must wire the explicit command
into CI/common lifecycle. Fixture/snapshot privacy checks in the existing Python
suite remain active. These local results do not prove upstream acceptance,
final-schema loading, real labels, DATA-READY, cloud NFRs or successful CI.

## Workstation and stub command registration

**PD-08 phase transfer (Mohit, 2026-10-18):** All unfinished PD-08 checks/reviews
are assigned to pre-domain integration, as mapped in the
[handoff decision](../decisions/database-integration-handoff.md). Command source and
native successes below remain valid for their recorded scope; real Compose,
remaining SQL/CI/command integration and affected-owner/final acceptance are
still pending. Integration intake must sequence prerequisites and keep original
checkpoint IDs; no cloud/reset/merge authority or passed check is implied.

PD-08 Step 3 reserves `database/migrations/20261018094330_mvp_tables.sql`,
`20261018094331_mvp_integrity.sql`, `20261018094332_initial_catalogue.sql`, and
forward correction `20261018152702_reject_retired_origin_entries.sql`; current
expected head is `20261018152702`. `database/dbmate.version` pins 2.36.0 and
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
| `bash database/local-db.sh status` | Display migration state. Pending migrations can appear with exit 0; compare expected head `20261018152702`. |
| `bash database/local-db.sh stop` | Stop validated local container; retain all volume data. Absent container succeeds. |
| `bash database/local-db.sh reset --confirm-delete-local-data` | Warn and permanently delete only the validated service container and `clip-local_clip_local_postgres_data`. Requires deliberate approval of that destructive action. No force/prune/broad volume deletion; leaves DB stopped. Missing confirmation fails before Docker. |
| `bash database/local-db.sh --help` | Fixed usage; no tools/password required. |
| `bash database/tests/local-db-safety.sh` | 35 simulated-Docker wiring/refusal/redaction cases; exit 0 on success, no registry/engine/database/cloud calls. |

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
| `bash database/tests/native-checks.sh /tmp/clip-pd08-native.pKC5jz/pgsql /tmp/clip-pd08-native.pKC5jz/bin/dbmate` | Requires macOS/Bash 3.2+, native PostgreSQL 18.6 and dbmate 2.36.0 at these explicit tool locations. Creates only its own private `/tmp/clip-pd08-native-check.*` cluster/database `clip_test_native`; disables TCP, uses an owner-only socket, applies/repeats migrations, runs smoke twice, runs both storage and retired-origin smoke suites, rolls back all four migrations, reapplies, compares ordered schema inventory and stops its cluster. Logs/data retained under printed evidence path. Nonzero on any failure or stop failure; inspect retained logs, never substitute an existing cluster. |

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

The native pass just described is historical evidence for the initial three migrations. The updated harness expects head `20261018152702` and four migrations; that revised macOS/dbmate route must be rerun. PR #5 correction checks include the current SQL round-trip and both smoke suites on an isolated Linux ARM64 PostgreSQL image, plus 35 simulated lifecycle cases. Internal metadata is preserved before separately redacting human diagnostics; these tests do not establish the real Compose lifecycle.

Deferred: container image/Compose runtime, loopback TCP/SCRAM readiness,
stop/start volume persistence, approved reset/recreate, platform/locale parity,
multi-connection concurrency, query-plan checks, affected-owner acceptance and
CI same-version checks. Native results do not close PD-08/PRE-00. See the
[database verification notes](../../database/README.md#native-macos-checkpoint--2026-10-18).

One-time clone/agent setup belongs in the [workstation guide](wsl-and-first-session.md). Future command owners must register explicit targets and effects above. PD-10/DL-00/domain owners register explicit test-double scenarios and real integration commands with distinct names/modes. No deployed command may default to fake auth/storage/notification/domain providers; startup validation rejects them. Stub tests never share a label or result classification with cloud/NFR runs. No cloud operation belongs in the generic local/CI aggregate target.

## PD-08 database concurrency and index diagnostics

`uv run --locked python database/tests/concurrency-checks.py` requires the existing
local Docker/Compose service definition and exported synthetic
`CLIP_LOCAL_POSTGRES_PASSWORD`. It starts the validated local service, downloads
pinned images if needed, creates/retains a fresh synthetic test database, checks
seven overlapping transaction cases and five index diagnostics, then stops the
service. Exit 0 means pass; nonzero requires inspecting the printed evidence
path. No reset/deletion/cloud/provider calls. See [scope and limits](../../database/README.md#storage-concurrency-and-index-diagnostics).

## PD-11 boundary checks

| Check | Exact command |
|---|---|
| Python application/contract-source boundary scan | `uv run --locked python scripts/check_boundaries.py` |
| Checker positive/negative and CLI regression tests | `uv run --locked pytest tests/architecture/test_boundaries.py -q -W error` |
| Existing frontend route/import boundaries | `npm test` |

Run from the repository root with locked Python tools and the existing pinned
Node/npm dependencies (`npm ci` for installation). The Python scan reads
`apps/api/app/` and `contracts/source/` without importing code; no database,
provider, listener or cloud is used. It exits 0 on no findings, nonzero on
violations/scan failure; diagnostics contain path/line/rule, not source values.
Do not suppress a finding: correct the dependency or obtain review of an exact
composition exception. Root pytest includes the checker tests. Frontend tests
remain unchanged and are also included in `npm run check`.

Coverage: static/relative/type-only imports, recognized dynamic import calls,
known aliases, domain import cycles, qualified literal SQL/search-path targets
and explicit ORM schema declarations. No router exception is currently granted.
Computed SQL, unqualified table resolution, arbitrary reflection and semantic
business call cycles are not proven safe by this scan; review and domain tests
remain required. Migrations/database verification are outside the runtime scan.

## PD-11 / DL-00 contract generation

Requires `uv sync --locked` and root `npm ci`: Node 24, TypeScript 5.9.3,
Hey API 0.99.0 (TypeScript-only plugin), and existing locked FastAPI/Pydantic.

| Invocation | Effect |
|---|---|
| `uv run --locked python scripts/generate_contracts.py generate` | Rebuild eight registered Python/OpenAPI/TypeScript outputs from reviewed health/domain source, including four declaration-only `public.py` modules. |
| `uv run --locked python scripts/generate_contracts.py check` | Render in temporary storage; exit 0 if current, nonzero for missing/stale outputs or tool/source failure; outputs unchanged. |
| `make contracts-double-check` | Run pinned Mypy against Search's consumer-owned Listings adapter and generated provider protocol. |
| `uv run --locked pytest apps/api/tests/domains/search -q -W error` | Isolated Search-to-Listings contract-double suite; synthetic success/failure cases only, not real integration evidence. |
| `uv run --locked pytest tests/integration -q -W error` | Future real cross-domain integration suite. It currently has no tests (pytest exit 5) and is pending, not a pass or readiness evidence. |

Run from the root. Generated files must not be hand-edited. On drift, correct
source, regenerate, review the diff and rerun check. On tool mismatch, inspect
pins/lock and use `npm ci`; no unpinned network fallback. No listener, database,
provider or cloud calls. [Outputs and limits](../../contracts/README.md).

Contract regression command: `uv run --locked pytest tests/contracts -q -W error`.
It checks canonical-source parity, all 50 declared domain HTTP operations, the
live API's health-only route set, sensitive-field publication boundaries, and
generated TypeScript consumers. Requires locked Python tools plus root `npm ci`
(Node 24/TypeScript 5.9.3/Hey API 0.99.0). Synthetic negative cases use temporary
trees and local tools; generated domain routes are never installed. Exit 0 means
pass; nonzero requires investigation. API-only pytest remains usable without
Node. [Coverage](../../contracts/README.md#contract-regression-tests).

## CI setup — PD-12

`.github/workflows/ci.yml` installs Python 3.14.3, uv 0.10.7 and Node 24.22.0,
verifies bundled npm 11.19.1, then runs `uv sync --locked --python 3.14.3` and
`npm ci` at the repository root. Setup actions are pinned to immutable revisions;
checkout credentials are not persisted. Installs may download tools/packages and
write ignored environments/caches; lockfile mismatch fails. Hosted checks passed
at `05e4cb8`; current changes still require their own hosted result. CI is PR-only
and cancels superseded runs for the same workflow/PR. No post-merge main run occurs;
incorporate latest main and pass CI before merging, repeating if main advances.

### CI quality gates — PD-12 Step 3

CI runs the registered Black, root/data pytest, boundary, contract freshness,
`npm run check` and simulated database-wrapper safety commands. Python lint/type
tools remain deferred under the existing tooling decision.

| Command | Effect / failure |
|---|---|
| `uv run --locked python scripts/check_database.py` | Requires local Unix-socket Docker. Creates a fresh PostgreSQL 18.6 container with temporary memory-backed data and no host port or persistent data volume; dbmate 2.36.0 checks clean apply, repeat migration, both SQL smoke suites, rollback of every migration and clean reapply against the migration files in the current checkout. On `domain/listings` at this checkpoint, the required head is `20261022062357` with 26 domain tables. Removes only its own container; nonzero on SQL/setup/cleanup failure. Never targets retained Compose data. |
| `uv run --locked python scripts/check_database.py --listings-store` | Runs those same isolated migration checks, then mounts only a private temporary Unix-socket directory and runs `apps/api/tests/domains/listings/test_postgres_store.py` against that container. Verifies real PostgreSQL create/edit/selection/availability writes and retry behavior using synthetic Identity/Conversations test doubles; prints a sample row selected from PostgreSQL before cleanup. No shared database, host port, real object storage or cloud resource is used. Removes the temporary container and socket directory. |
| `uv run --locked python scripts/check_secrets.py` | Requires local Unix-socket Docker. Gitleaks 8.30.1 scans tracked and nonignored new source in a temporary snapshot, offline/read-only. Uses `.gitleaks.toml`; findings print file/line/rule only and fail. This scans current source, not Git history; ignored files are excluded and symlinks rejected. |

Images may be downloaded from public registries. No cloud/provider configuration
is forwarded. The database checker never accepts a caller-selected database
target; `--help` lists its optional check mode.
Local/CI aggregate parity is implemented below; full lifecycle commands remain PD-13.

### CI execution boundary — PD-12 Step 4

The PR-only workflow uses read-only repository access, no persisted checkout
credentials, no secret expressions, no deployment environment and no cloud login,
apply/deploy or production-data command. Setup downloads public tools/packages
and images; local-only describes the checks, not a network-free installation.
Database/scanner runners require local Unix-socket Docker, forward only required
inputs and isolate execution from provider settings; neither mounts cloud files.
The database uses ephemeral generated credentials and memory-backed storage;
the scanner runs without network access. Existing tests use synthetic fixtures,
in-memory HTTP and temporary files. Contract generation rejects external refs.
No root package install/check/build lifecycle hooks add a separate action.

Read-only host inspection on 2026-10-18 found no repository Actions secrets or
repository environments. This is not an organization-secret inventory or hosted
execution result; CI does not reference organization secrets either. Changes to
workflow commands, dependencies or permissions require renewed review. Hosting
protections and actual hosted CI verification remain pending.

### CI failure output — PD-12 Step 5

`Foundation quality gates` identifies the required job; each setup/check has a
unique step label and failures are not suppressed. Python/web tools retain their
normal local diagnostics. Database command failures identify Docker/psql/dbmate
and exit status with bounded, password-redacted output. Secret findings expose
only file/line/rule; scanner configuration/exit failures and Git/Docker setup
failures have separate recovery guidance, without raw scanner stderr or values.
Hosted failure presentation remains to be verified on the PR.

### Shared aggregate — PD-12 Step 6

After `uv sync --locked` and root `npm ci`, run `make check` from the clone root
with Python 3.14, Node 24, npm 11, uv, Make and local Docker. It runs all checks
through `scripts/check.py`, stops on first failure and preserves the failing exit
status. Each check has a 600-second bound. Side effects are the previously listed
caches/build output, temporary snapshots and disposable containers; no cloud
login or retained database reset is needed. Plain `make` still checks Black only.

CI calls individual selectors from the same registry, preserving named steps.
`uv run --locked python scripts/check.py --help` lists selectors; omit the selector
to run all. The first check, `ci-parity`, compares the workflow's ordered commands
with the registry and verifies the Make mapping, including `npm run check`.
It deliberately accepts only the existing single-line workflow run fields;
new YAML command forms require review. It is not a general YAML/security checker.

### Black pre-commit hook — PD-12 Step 8

| Command | Effect |
|---|---|
| `uv run --locked pre-commit install` | After `uv sync --locked`, install the local Git hook once per clone; requires uv on the commit process PATH. |
| `uv run --locked pre-commit validate-config` | Validate the tracked hook configuration without formatting files. |
| `uv run --locked pre-commit run --all-files` | Run pinned Black on tracked Python files; may rewrite source. Generated contracts excluded. Review/stage fixes before retrying a commit. |
| `uv run --locked pre-commit uninstall` | Remove the installed local hook; leaves tracked configuration/dependencies intact. |

The local hook uses root locked Black/configuration, not a separate environment;
it never stages fixes. CI's independent check-only gate remains required.

## Common Make front door — PD-13 Step 1

Run `make help` at the clone root. Targets reuse existing tools; no second npm
manifest, environment loader or daemon is introduced. GNU Make is required
(including macOS's supplied GNU Make). Existing `make` remains Black check-only.

| Target | Mapping / effects |
|---|---|
| `make setup` | `uv sync --locked`, then root `npm ci`; downloads locked dependencies, no service startup or automatic hook install. |
| `make install-hooks` | Explicit one-time local pre-commit installation. |
| `make start-db` / `make stop-db` | Existing validated local database wrapper; password environment required. Stop retains data; no reset target is added. |
| `make start-api` / `make start-web` | Foreground API on 127.0.0.1:8000 / web on 127.0.0.1:5173. Use separate terminals; Ctrl+C stops each owned server. Database start/migration are explicit preceding actions. |
| `make preview-web` | Existing `npm run preview`, loopback 4173; build first (`npm run build` or `make test-web`). |
| `make migrate` / `make migration-status` | Local dbmate apply/status; status can report pending revisions without failing. |
| `make seed` | Apply pending migrations, including the existing eight-category/four-condition catalogue. No sample accounts/listings or separate seed replay. |
| `make data-generate RUN_NAME=preview-42 SEED=42 USERS=3 LISTINGS=2` | Existing safe PD-09 preview file generator; all inputs mandatory, no overwrite. This is not final domain data. |
| `make data-validate RUN_NAME=preview-42` / `make data-load` | Existing preview validation / explicit unavailable-loader failure (nonzero, no database write). |
| `make test` | Shared runner's Python, explicit data and web gates; `test-python`, `test-data`, `test-web` select each. Web includes lint/types/build as registered. |
| `make format` / `make format-check` | Existing rewriting Black / check-only targets; old names retained. |
| `make contracts-generate` / `make contracts-check` | Registered generation / nonmutating freshness check. |
| `make contracts-double-check` | Static type check for the representative consumer-owned interface double. |
| `make check` | Existing full CI-equivalent aggregate, including disposable database and scanner. |

Normal Make failure is nonzero (usually 2), including `data-load`'s deliberate
refusal. Dataset inputs are exported as target-specific environment values and
quoted by the shell; the generator validates them. Steps 2–4 cover helper needs,
Terraform portability/mappings and the consolidated setup guide; Step 5 verifies
the full lifecycle from a clean environment. Runtime/platform acceptance is not
implied by command mapping or dry runs.

**PD-13 Step 2 helper audit:** no additional wrapper is needed. Make directly
reuses the validated database lifecycle, data CLI, contract generator and shared
check runner. API/web stay in owned foreground terminals; no PID files, background
supervisor or process-killing script is introduced. Terraform portability is Step 3.

## Terraform front door — PD-13 Step 3

Requires Terraform **1.15.9** from `.terraform-version` and Bash 3.2+; the wrapper
rejects another version. Set `TERRAFORM_BIN` to an explicit compatible executable
if the default PATH selects another version. All actions target `infra/terraform`.

| Command | Effect |
|---|---|
| `make terraform-format` | Rewrite Terraform formatting; review the diff. |
| `make terraform-format-check` | Check formatting without rewriting. |
| `make terraform-validate` | Discover configuration roots, initialize provider schemas with `-backend=false -lockfile=readonly`, then validate; may download locked providers into ignored `.terraform/`. |
| `make terraform-check` | Formatting check followed by backend-free validation; also the default when invoking the script without arguments. |

The existing `scripts/terraform-static-check.sh` accepts only these explicit
modes. It reports action/target, preserves failures and discards ambient cloud,
TF_CLI_ARGS, debug and user CLI configuration. No plan/apply/destroy target is
added, and Terraform stays outside `make check`. The provider lock is generated
for Linux/macOS AMD64/ARM64; package availability/hashes do not prove runtime
checks. On 2026-10-20 (Asia/Kolkata), the user confirmed that the previously
deferred Linux AMD64 and native macOS checks passed on other machine(s). Exact
machine architecture, commands, and raw outputs are not retained here; see the
[current platform record](../../database/README.md).

**PD-13 Step 5 local evidence:** fresh private clone/home/cache setup, hooks,
API/web/preview two start-stop cycles, deterministic preview files, repeatable
contracts and full aggregate passed on Linux ARM64. A restrictive umask exposed
dbmate read-permission failure; both migration callers now run the tool as the
contributor UID/GID, retaining read-only mounts and dropped capabilities. Wrapper
controls enforce that flag. The persistent database ran two seed/status/start-stop
cycles through its original owner clone, with catalogue/head and volume retained;
clean migration checks used disposable containers. Other-machine checks remain
pending. Exact logs/source overlay are linked from the work log; Step 6 consolidates
the evidence and task review.

## LI-01 Step 7 — isolated PostgreSQL browser checkpoint

Run from the repository root with the locked Python environment, Node 24/npm 11,
and local Unix-socket Docker. [Web guide](../../apps/web/README.md#li-01-step-7-isolated-browser-check-with-real-postgresql)
has manual actions, expected results and current limitations. These are test-only
commands, not deployment or task-completion evidence.

| Exact command | Target/effects and success | Stop/failure behavior |
|---|---|---|
| `CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true uv run --locked python apps/api/tests/domains/listings/browser_demo.py --isolated-listings-browser` | Creates its own labelled PostgreSQL 18.6 container, applies current migrations using dbmate 2.36.0 and seeds a synthetic seller. Serves actual Listings routes/store on loopback 8000 with explicit test-only trusted auth and image-confirmation metadata. Prints an owner-private `/tmp/clip-listings-browser-*` session path. Uses no ambient database URL, published DB port, shared Compose data, cloud, real sign-in or object storage. | Rejects non-test settings, missing development-auth opt-in, ambient database URL, nonlocal Docker or occupied API port. Ctrl+C stops only its API/container and retains rows. Failure stops the owned container and retains session data for diagnosis/resume; no automatic reset/removal. |
| `npm run build` then `CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true uv run --locked python apps/api/tests/domains/listings/browser_demo.py --isolated-listings-browser --image-ui-preview` | Serves the built Listings UI and actual API/store on loopback 5174, with a fresh labelled PostgreSQL 18.6 database, a fixed synthetic seller, and temporary in-memory image storage. Supports create, edit, detail and My Listings photo review. The local adapter enforces the reviewed upload protocol and byte checks but never contacts AWS. The page banner identifies this mode. | Requires the built `apps/web/dist/`, local Unix-socket Docker and an unused 5174 port. Rejects non-test settings, missing development-auth opt-in, ambient database URL, nonlocal Docker and remote/cross-origin requests. Ctrl+C stops the owned API/database and discards local image bytes; database rows stay in the labelled stopped container for `--resume`. No AWS, shared database, real Identity or durable image storage. |
| `VITE_LISTINGS_ISOLATED_DEMO=true npm run dev` | Runs the same development web server on loopback 5173; exposes only labelled local Listings controls for preparing synthetic image metadata through the separate test app. Production builds ignore this development flag. | Ctrl+C stops the owned Vite process. Missing API/dependencies produce visible failures, not simulated successful saves. |
| `CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true uv run --locked python apps/api/tests/domains/listings/browser_demo.py --isolated-listings-browser --inspect SESSION_PATH` | Requires the exact printed retained session path and matching container ownership label. Executes read-only SQL against that running browser database to print synthetic listing ID/title/price/status/proof values. | Fails closed on wrong owner/path/label, stopped/unavailable container or SQL failure; never inspects the shared database. |
| `CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true uv run --locked python apps/api/tests/domains/listings/browser_demo.py --isolated-listings-browser --resume SESSION_PATH` | Validates the recorded private session/container label, starts that same database without resetting rows, reapplies only pending migrations, and serves the isolated API again. | Ctrl+C retains rows. Does not remove containers/volumes/session files. Cleanup requires a separate targeted action. |
| `CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true uv run --locked python apps/api/tests/domains/listings/browser_demo.py --isolated-listings-browser --hybrid-search --resume SESSION_PATH` | Resumes that same local database and enables the real pinned helper, worker and Hybrid reader. Requires the repo-local CPython 3.13 helper and model under `.tools/semantic/`. Before serving, verifies the worker pool reaches `clip_listings_browser` over its private Unix socket, prepares existing rows, waits for complete vectors and activates the pinned pipeline. New listing creates/edits then use the database trigger and worker automatically; no copied vectors. | Refuses a mismatched database, unavailable helper/worker, failed vector job or incomplete five-minute bootstrap. Ctrl+C retains the labelled local database. No shared database or cloud target. |

The browser harness also mounts real Wanted Request and Saved Listings routes
on this same database. Categories, draft matches, save eligibility and saved
summaries use the real Listings provider used by `app.main`; no scripted Listings
responses are installed. `/me` and eligibility use only the fixed local synthetic
account. Conversations remain unavailable. The image UI mode supports direct
refreshes at `/saved` and `/wanted/{request_id}` as well as the Listings routes.

## SE-01 Step 9 — isolated evaluator preparation

Run at repository root with the locked project Python environment. These commands
need no database, Docker, cloud access, credentials or additional dependencies.

| Exact command | Target/effects and success | Stop/failure behavior |
|---|---|---|
| `uv run --locked python -m scripts.evaluation.search validate-labels --labels data/evaluation/query-labels.template.json` | Read-only canonical draft-format validation; prints fingerprints, format validity and `scoring_allowed: false`. | Exit 2 for malformed/unsafe input or missing final binding; no content echoed and no review inferred. |
| `uv run --locked python -m scripts.evaluation.search self-check` | Synthetic Success@5 arithmetic only: four included cases, one hit (0.25); always preview-only with NFR acceptance false. No files written. | Nonzero if arithmetic/input checks fail; never falls back to real retrieval. |
| `uv run --locked python -m pytest tests/evaluation -q` | Temporary synthetic label/binding and calculator checks; no canonical labels created. | Nonzero on regression; no final corpus/readiness result. |

Final dataset validation, human-reviewed labels and real retrieval integration
remain pending; see [tooling limits](../../scripts/evaluation/README.md).

## Listings/Search merge — deployment preparation

The [combined deployment handoff](../architecture/listings-search-deployment.md)
registers the ordinary API build and optional `apps/api/Dockerfile.hybrid` build,
including explicit Python/wheel/model artifact contexts. Both are local builds
and publish nothing. The optional image's helper install and real inference
self-check run with networking disabled; model/wheel hashes are verified. Use
Linux AMD64 artifacts, not the earlier Mac helper environment. The image includes
`python scripts/search_pipeline.py --help` and the existing target-bound bootstrap
operations for later deployment initialization. Normal `CLIP_SERVE_WEB_APP=true`
serves the UI and `/api` routes independently of the isolated test identity.

## SE-01 hybrid checkpoint 4 — repository-local semantic probe

Fixed Mac-only feasibility scope and [limits/results](../architecture/semantic-search-feasibility.md).
Root API Python remains 3.14; the isolated probe uses Python 3.13.12. For every uv
command below set process-local `UV_PYTHON_INSTALL_DIR="$PWD/.tools/semantic/python"`
and `UV_CACHE_DIR="$PWD/.tools/semantic/cache"`. No global links/PATH changes.
First create `.tools/semantic/` and copy the reviewed committed helper lock to
`.tools/semantic/resolved-mac.txt`; no automatic dependency re-resolution.

| Exact command (repository root) | Target/effects and success | Stop/failure behavior |
|---|---|---|
| `.venv/bin/python scripts/evaluation/semantic/preflight.py` | Read official PyPI/model/release metadata; select compatible pinned Mac wheels, record license/advisory/size data under `.tools/semantic/preflight.json`. | Nonzero on advisory, missing wheel, hash binding or budget failure; no model weights/install. Network sandbox needs normal escalation. |
| `.tools/uv/uv python install 3.13.12 --no-bin` | With the explicit local uv variables above, download the fixed managed interpreter only into `.tools/semantic/python/`. | Nonzero on retrieval failure; no global executable links or root environment edits. |
| `.tools/uv/uv venv .tools/semantic/venv --python .tools/semantic/python/cpython-3.13.12-macos-aarch64-none/bin/python3.13 --no-python-downloads` | Create only the separate helper environment. | Root-project 3.14 incompatibility warning is expected for this isolated helper; root `.venv` is not the target. |
| `.venv/bin/python scripts/evaluation/semantic/fetch.py` | Download preflight-bound wheels/model to ignored paths; validate sizes/hashes and retained artifact manifest. | Refuse unknown paths/hosts, changed bindings, size/hash/deadline violations; preserve failed partials, no arbitrary deletion. |
| `.tools/uv/uv pip sync .tools/semantic/resolved-mac.txt --python .tools/semantic/venv/bin/python --require-hashes --no-index --find-links .tools/semantic/wheels --only-binary :all: --offline --link-mode copy` | Install the frozen 24 packages only into the helper venv, from verified local wheels. | No source builds, network resolution or root installation; dependency/hash failures block. |
| `.venv/bin/python scripts/evaluation/semantic/supervise.py --preview-api-pid PID` | Replace PID with the verified running isolated preview API PID; supervise the fixed offline helper under memory/deadline bounds and retain a unique safe run. | Fails if process memory cannot be verified; kills only owned helper on limit/failure; never signals the API. `ps` needs process-read escalation on this Mac. |
| `.venv/bin/python -m pytest tests/evaluation/test_semantic_probe.py -q -W error` | Portable chunk/integrity checks without isolated ML packages or real model calls. | Nonzero on regression; no inference/NFR acceptance. |

Initial hash-lock generation (performed once, not a frozen replay command):
`.tools/uv/uv pip compile scripts/evaluation/semantic/requirements.in --generate-hashes --only-binary :all: --python-version 3.13 --python-platform aarch64-apple-darwin --no-python-downloads --output-file .tools/semantic/resolved-mac.txt --quiet`.
Keep the same explicit local uv variables. New resolution requires review of the
new pins, platform/size/license/advisory metadata and updated evidence.

## SE-01 embedding storage preparation — no database run

The existing `uv run --locked python scripts/check_database.py --listings-store`
now includes native embedding integrity/rollback/two-connection race tests and
three smoke scripts. It still creates only its own disposable PostgreSQL 18.6
container/socket database; no target URL, shared data or ambient PG settings is
accepted. Expected head is `20261024153316` (12 migrations/29 domain tables).
This new native check has **not run** on this Mac; Docker/PostgreSQL is absent.
Do not infer apply, trigger, concurrency or rollback success from portable tests.
The existing macOS native wrapper also expects 30 functions/40 triggers and all
12 rollbacks; actual catalogue verification is pending.

Portable check, using the root locked environment:
`uv run --locked python -m pytest apps/api/tests/domains/listings/test_embedding_store.py apps/api/tests/domains/listings/test_embedding_postgres.py -q -W error`.
It runs validation/transport and pre-connect refusal tests; two real native tests
skip without the runner. No database target or background worker is created by
this portable command. [Protocol and exact implementation limits](../architecture/semantic-listing-storage.md).

## SE-01 checkpoint C — repository-local native PostgreSQL route

User verified storage increment B and requested native testing. The existing
native harness now accepts optional `--listings-store`. Exact invocation from
this clone after verifying the pinned local tools:

```sh
LC_ALL=C bash database/tests/native-checks.sh "$PWD/.tools/native-db/pgsql" "$PWD/.tools/native-db/downloads/dbmate-macos-arm64" --listings-store
```

The tool prefixes are inputs, never an existing DB target. The harness creates a
new private `/tmp/clip-pd08-native-check.*` cluster with UTF-8/C locale, TCP disabled,
owner-only Unix sockets and rejected host authentication. It applies/smokes/
rolls back/reapplies only `clip_test_native`, compares source-expected catalogues,
then creates a SECOND fresh `clip_test_ci` database and `clip_ci` role in that
same owned cluster for the actual Listings/browse/embedding adapter tests. A
separate owner-private `/tmp/clip-listings-test-*/pgsocket` exposes only the Unix
socket at native port 55438. No global/Homebrew service, Docker, shared database,
cloud target or provider credentials are used. On exit it stops only this cluster
and retains logs/data; failed runs are not automatically deleted. The new native
adapter mode's execution result is recorded separately after the run.

Tools rebuilt under ignored `.tools/native-db/` because earlier `/tmp` tools were
gone: official PostgreSQL 18.6 source archive SHA-256
`555610c24d53e4316da5b7d3fc25c279d96856d5e0e23ee308c328c5fa881d9f`,
22,632,314 bytes; official dbmate 2.36.0 macOS ARM64 binary SHA-256
`86f799b694710a8cc330eb5763a5d13d3c4b19e5e895822734b9fb44e1c35891`,
31,639,010 bytes. Build uses existing Clang/make, two jobs, local install prefix
and historical `--without-icu --without-readline --without-zlib` flags. It does
not establish production locale/ICU/TLS/cgroup/CPU equivalence. Download/tool/build
logs and manifest stay under `.tools/native-db/`; no global executable/PATH edit.

Native execution result: final fresh run `/tmp/clip-pd08-native-check.oLISmK`
passed the schema round trip and seven adapter-suite checks (four actual DB
cases, three pre-connect guards); cluster stop succeeded. [Retained evidence](../evaluation/domain/se-01/native-postgres/result.json).
Two earlier failed runs remain for the corrected GIN diagnostic, fixture
retirement publication/age and browse marker ordering. Production constraints
were preserved. These native tool/configuration results do not accept real
providers, final corpus/labels, full pipeline-switch coverage or FR/NFR gates.

The same native command subsequently passed the expanded bootstrap/switch matrix:
`/tmp/clip-pd08-native-check.4FB6Mb`, eight adapter checks (five DB/three guards),
schema round trip and successful cluster stop. [Expanded evidence](../evaluation/domain/se-01/native-pipeline-switch/result.json).
No new command/dependency/service is introduced; all mathematical fixture state
changes remain inside the fresh disposable runner database.

## SE-01 private real helper IPC checkpoint

From repository root with the existing local model/helper interpreter (no new
install/download), identify the already-running isolated preview API PID:

` .venv/bin/python scripts/evaluation/semantic/ipc_probe.py --isolated-helper-probe --preview-api-pid PID `

Replace PID explicitly; do not guess or use a cloud process. The fixed probe starts
only owned helper children, sends <=30 model windows under ten minutes, samples
host/helper/identified preview RSS with a512MiB stop bound, tests an owned-child
SIGKILL/restart and reaps all its helpers. `ps` memory reads require the usual Mac
sandbox escalation. Results go to a new `.tools/semantic/ipc-probes/<UTC>/` folder;
no body/vector text, process arguments or environment is recorded. The existing
preview API is only observed, never signalled. No DB/public worker/cloud action.

Portable protocol/lifecycle checks:
`uv run --locked python -m pytest apps/api/tests/domains/listings/test_embedding_client.py -q -W error`.
Fault helpers are selected only by a test subclass, never an app/env flag; they
prove failures/lifecycle, not model inference. [Private protocol and limits](../architecture/semantic-helper-protocol.md).
The helper/shared files additionally compile with the isolated Python3.13:
`.tools/semantic/venv/bin/python -m py_compile apps/api/app/domains/listings/embedding_types.py apps/api/app/domains/listings/embedding_protocol.py apps/api/app/domains/listings/embedding_helper.py`.

## SE-01 private DB/helper bridge checkpoint

Portable orchestration/store/client checks, no database/model invocation:

```bash
uv run --locked python -m pytest apps/api/tests/domains/listings/test_embedding_worker.py apps/api/tests/domains/listings/test_embedding_store.py apps/api/tests/domains/listings/test_embedding_client.py -q -W error
```

Actual disposable PostgreSQL plus the **existing** repository-local model/helper,
macOS only, no install/download or existing DB target:

```bash
LC_ALL=C bash database/tests/native-checks.sh "$PWD/.tools/native-db/pgsql" "$PWD/.tools/native-db/downloads/dbmate-macos-arm64" --embedding-worker
```

This opts into the same fresh-cluster/schema round trip and adapter suite as
`--listings-store`, additionally setting test-only
`LISTINGS_TEST_EMBEDDING_WORKER_MODEL=1` for the actual model bridge case. It is
not an application flag. Existing target guards run before fixture writes;
only clip_test_native and a second fresh clip_test_ci are accepted. Standard
`--listings-store` native/Docker checks include SQL/fault-pipe bridge tests and
skip the actual model; they do not install its optional packages.

Model check caps: one explicit worker, one live helper, <=30 windows, <=10min and
512MiB sampled test-host/helper RSS. Reads only declared PIDs/PPIDs/RSS; fails if
host measurement is missing. Existing helper pins/offline process restrictions
apply. Real source/lease/generation checks use the database, not coordinate
ranking. The real test intentionally kills only its owned helper for crash/
recovery. Exit stops the owned cluster/helpers, retains private logs/data and
writes safe model metrics under `.tools/semantic/worker-probes/<UTC>/result.json`.
On this Mac process/shared-memory access requires sandbox escalation. A failed or
skipped model check cannot be called a real-model pass. Public serving, app
startup, existing/shared DB jobs, cloud, hosting and global configuration are
outside this command. [Protocol/evidence](../architecture/semantic-embedding-worker.md).

## SE-01 development-only hybrid calibration

With the existing local model/helper and native tools, run only a newly-created
private database (no existing target accepted):

```bash
LC_ALL=C bash database/tests/native-checks.sh "$PWD/.tools/native-db/pgsql" "$PWD/.tools/native-db/downloads/dbmate-macos-arm64" --search-calibration
```

This selects `LISTINGS_TEST_SEARCH_CALIBRATION=1` only for the native test. It
runs the ordinary adapter/fault suite plus `test_search_calibration_postgres.py`;
the separate actual worker-model case is intentionally not selected. Default
native/Docker adapter runs include the calibration case but skip model work
without this flag. No model package is installed by either runner. Actual reads
use only the fixed8synthetic development listings/11queries in session-temporary
tables. Cap30actual model windows/one live helper/10min/512MiB sampled host+helper;
3s SQL statement/1s lock bounds. Existing PID/RSS supervision and private Unix
socket guards apply. The test also verifies base counts, cleanup and preservation
of a pre-existing temporary-table sentinel. Only the owned helpers/cluster stop;
logs/data and unique `.tools/semantic/calibration-probes/<UTC>/` results remain.
Shared/production DBs, public routes, final data/labels, installs/cloud/hosting and
policy activation are not targets. Native process/shared-memory access on this
Mac requires sandbox escalation.

Reanalyze a captured matrix without SQL/model/network work:

```bash
uv run --locked python scripts/evaluation/semantic/calibration.py --analyze .tools/semantic/calibration-probes/RUN/matrix.json
```

Replace RUN with a retained run directory. The tool requires exact fixture/model/
vocabulary bindings and every finite query/listing score pair; it compares the
predeclared90settings and writes a new ignored calibration-analysis/<UTC>/ folder.
It never overwrites a report, selects a production winner or marks human review/
NFR acceptance. Reading valid bindings alone does not attest measurement origin;
retain the native source/evidence manifest. Portable arithmetic/input/guard checks:

```bash
uv run --locked python -m pytest tests/evaluation/test_search_calibration.py -q -W error
```

See the [provisional proposal and known failure](../architecture/hybrid-search-calibration.md).

## SE-01 known-vocabulary typo checkpoint

Portable spelling/compiler/vocabulary checks, no model/database/install:

```bash
uv run --locked python -m pytest apps/api/tests/domains/listings/test_typo_tolerance.py apps/api/tests/domains/listings/test_lexical_expansion.py apps/api/tests/domains/listings/test_vocabulary.py -q -W error
```

Real native matching/filters/pages/index eligibility use the existing fresh private
runner command (no existing database target):

```bash
LC_ALL=C bash database/tests/native-checks.sh "$PWD/.tools/native-db/pgsql" "$PWD/.tools/native-db/downloads/dbmate-macos-arm64" --listings-store
```

The expanded browse matrix now includes spelling rules; no additional runner flag,
package, extension, model download/inference or public startup switch is introduced.
The separate optional worker-model and calibration-model cases are intentionally
skipped in this mode. Existing PostgreSQL18.6/dbmate2.36/private Unix sockets,
owned cluster stop and retained logs/data rules apply. On this Mac native process/
shared-memory access requires sandbox escalation. The ordinary Docker adapter
command also includes these actual browse assertions where Docker is available.
[Limits, failure/collision cases and evidence](../architecture/search-typo-tolerance.md).

## SE-01 private hybrid-read checkpoint

Portable private-reader/binding/HTTP error checks (no model or database target):

```bash
uv run --locked python -m pytest apps/api/tests/domains/listings/test_hybrid_read.py -q -W error
```

Actual new private PostgreSQL cluster, snapshot/math checks and the already-local
pinned helper through the real worker/read path:

```bash
LC_ALL=C bash database/tests/native-checks.sh "$PWD/.tools/native-db/pgsql" "$PWD/.tools/native-db/downloads/dbmate-macos-arm64" --hybrid-read
```

The flag sets only test `LISTINGS_TEST_HYBRID_MODEL=1`; it is not an application
mode. The existing fresh-cluster/migration/smoke/down/reapply and adapter suite
runs plus hybrid math/snapshot/actual-model cases. Separate worker-model and
calibration-model cases are deliberately unselected. Default native/Docker
adapter runs include the two hybrid SQL cases and skip only the optional hybrid
model case; neither installs model packages. Tools/targets remain fixed as in the
prior native command: no existing/shared DB URL, global service or Docker install.

Model bound: <=30windows/10min/one live helper/512MiB sampled test-host/helper,
with owned-process reaping. Mathematical fixtures use <=150bounded publications
per drain and65same-source coordinate clones solely for pagination; no model
relevance is claimed from those. Test-only advisory-lock gate31 proves the real
statement overlapped a committed edit. No such lock/flag enters production code.
Only owned synthetic fixtures are retired and prior pipeline states restored in
committed cases; math fixtures roll back. Owned cluster stops, logs/data retained;
safe actual metrics go to `.tools/semantic/hybrid-read-probes/<UTC>/result.json`.
Process/shared-memory access on this Mac requires sandbox escalation. A failed/
skipped required check does not pass. [Contract/evidence](../architecture/hybrid-listing-read.md).

## SE-01 private keyword relevance

Portable construction/guard/regression checks:

```bash
uv run --locked python -m pytest apps/api/tests/domains/listings/test_keyword_relevance.py apps/api/tests/domains/listings/test_lexical_expansion.py -q -W error
```

Actual native ranking/filters/pages/model-state independence use the existing
fresh private database runner, with no model/download/install:

```bash
LC_ALL=C bash database/tests/native-checks.sh "$PWD/.tools/native-db/pgsql" "$PWD/.tools/native-db/downloads/dbmate-macos-arm64" --listings-store
```

No new flag/target is introduced. The expanded browse native case includes
keyword relevance and a nested rollback-only failed-pipeline/job fixture. All
source/index/rank behavior executes on actual PostgreSQL; optional actual-model
probes are deliberately unselected. Existing tool pins/private Unix sockets,
owned cluster stop and evidence retention apply. Native process/shared-memory
access on this Mac requires sandbox escalation. No existing/shared DB, production
API/UI mode or model process is activated. [Policy/evidence](../architecture/keyword-listing-relevance.md).


## SE-01 registered search mode/API checkpoint

Use repository-local Python/Node and the existing generation/native commands.
`PATH="$PWD/.tools/node/bin:$PATH" .venv/bin/python scripts/generate_contracts.py generate`
regenerates registered artifacts from editable source; `check` verifies freshness.
`.venv/bin/python -m pytest apps/api/tests/domains/listings/test_search_modes.py -q -W error`
checks mode/text/sort validation/dispatch, safe transport errors, auth ordering and
missing-capability behavior using explicit scripted dependencies; no model/DB is
started. The existing `--listings-store` native runner additionally checks the
public adapter over rollback-only native fixtures. No runner flag or install was
added. Normal app construction has no helper: nonblank Hybrid is503 until a later
verified lifecycle/configuration checkpoint. Existing web controls omit the new
mode field and therefore select Keyword until their own checkpoint.


## SE-01 frontend mode/relevance verification

Existing `npm run check` now includes URL/mode/form, request cancellation/late
completion/retry, static control rendering and generated-contract compatibility
checks. No package or command is added. Existing loopback preview commands above
remain unchanged. Refresh the page at `http://127.0.0.1:5173/`; `hybrid-down` with
Hybrid scripts503, and explicit Use Keyword recovers; `slow` scripts delay and
`retry` scripts one failure per fixture-app instance. All are transport fixtures,
not real auth/SQL/semantic ranking. Human checks in
[the evidence](../evaluation/domain/se-01/frontend-modes/result.json) remain pending.


## SE-01 actual native HTTP/model preview

Run from the repo root with existing tools/model; no install or Docker required.

| Command | Effects, bounds and expected result |
|---|---|
| `CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true .venv/bin/python apps/api/tests/domains/search/native_preview.py --isolated-native-search --check-only` | New private0700 `/tmp/clip-listings-test-*` native PG18.6 cluster, no TCP database; fixed `clip_test_ci`/`clip_ci`,12migrations,3synthetic listings with image metadata, real worker/model/HTTP query checks; closes/reaps helper/pool and stops owned cluster; retains logs/data/result.json. Headless failures remain failures. Rejects missing explicit opt-in and ambient DB/AWS; accepts no existing target. |
| Same command without `--check-only` | Same real bootstrap/checks; requires free loopback8000, then serves actual read-only browse/catalogue until Ctrl+C or30min. Existing Vite5173 proxies it; refresh UI and confirm Real search/local test data banner. One helper/100total windows, sampled512MiB API+helper watchdog; pool4autocommit connections, SQL5s/lock1s. PG shared_buffers16MiB/max_connections10; PG/Vite RSS not included in app/helper cap. Query budget exhaustion returns Hybrid503; Keyword independent. Stops owned processes, retains database; no resets/deletes/shared/cloud target. |
| `.venv/bin/python -m pytest apps/api/tests/domains/search/test_native_preview.py -q -W error` | Target/transport/expiry/inference-reservation guards with explicit doubles; no inference or PostgreSQL. Actual-model evidence comes only from CLI runs above. |

Use the existing development fixture-opt-in Vite command: the header gates both
isolated backends; UI disclosure reads X-Clip-Preview, never assumes the flag means
semantic integration. Native mode uses actual query inputs, so fixture words slow,
retry and hybrid-down have no scripted behavior. Identity/images/data remain
synthetic; production app, Linux/deployment/resources and real upstream readiness
remain pending. The native harness is never imported by normal app startup.


## SE-01 normal API read-helper lifecycle

Normal API startup/stop spelling stays unchanged. CLIP_HYBRID_SEARCH_ENABLED is
false by default. True requires the existing database secret setting plus explicit
absolute CLIP_HYBRID_SEARCH_INTERPRETER and CLIP_HYBRID_SEARCH_MODEL_DIR. No .env
loading, interpreter/model discovery/download, worker/backfill or serving switch.
See [the configuration/lifecycle contract](../architecture/normal-api-search-runtime.md).
Do not supply a shared target for an unapproved local test.

| Exact command | Inputs/effects and expected result |
|---|---|
| `CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true .venv/bin/python apps/api/tests/domains/search/normal_runtime_probe.py --isolated-normal-search` | Requires existing repo-local native PG18.6/dbmate2.36/helper/model. Creates new private0700 Unix-socket DB only; no existing target argument or ambient DB/AWS. Explicit test bootstrap publishes3controlled sources, closes its helper, then actual app.main lifespan verifies disabled/ready/unavailable settings, real HTTP queries, separate transactional/autocommit pools, Keyword independence and cleanup. Synthetic identity is confined to this process. <=6min/40windows,1simultaneous helper, sampled512MiB API/helper; no listener, production activation or cloud. Stops owned cluster/helper/pools and retains normal-runtime-result.json/logs in printed /tmp directory. No OS memory reservation/deployment equivalence is claimed. |
| `.venv/bin/python -m pytest apps/api/tests/domains/listings/test_search_runtime.py apps/api/tests/test_config.py -q -W error` | Settings and lifecycle/composition/cancellation/cleanup cases use explicit scripted resources; no model or DB starts. These prove lifecycle contracts, not actual model results; the native probe above proves the latter. |

Enabled startup adds at most2read connections per API process to the existing
max10command connections. Deployment process count/DB capacity, Linux packaging,
serving pipeline/bootstrap and worker dispatch remain separately reviewed work.


## SE-01 bounded existing-job dispatcher

CLIP_HYBRID_WORKER_ENABLED defaults false and requires Hybrid enabled/configured.
Normal start/stop commands are unchanged. It adds1max worker connection and no
model process; max combined connections13/API process. Startup processes only
existing due jobs, never registering/reconciling/backfilling/activating a pipeline.

| Exact command | Effects/bounds/expected result |
|---|---|
| `CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true .venv/bin/python apps/api/tests/domains/search/worker_dispatch_probe.py --isolated-worker-dispatch` | Existing native PG18.6/dbmate2.36/model/helper only. Fresh private0700Unix-socket DB; no existing target/ambient DB/AWS. Actual app.main idle without registry, then explicit fixture bootstrap; edit invalidation, pending Hybrid503/Keyword200, due-worker current generation publication/Hybrid recovery, worker-pool-failure independence and full owned cleanup. <=6min/40windows,1simultaneous model child, sampled512MiB API/helper excluding native PG; no listener/cloud. Retains worker-dispatch-result.json/migration/stop logs at printed /tmp path. |
| `.venv/bin/python -m pytest apps/api/tests/domains/listings/test_embedding_dispatch.py apps/api/tests/domains/listings/test_search_runtime.py apps/api/tests/test_config.py -q -W error` | Explicit scripted job/lifecycle/config guards; serial pacing, errors, cancellation and ownership. No actual SQL/model starts; use native probe for that evidence. |

The probe's retry_after gate is controlled fixture setup, not a product retry
policy. Worker scheduling leaves bootstrap/serving activation as a separate
operator checkpoint. Failed jobs still require their existing explicit retry.
See [dispatcher limits/remaining gates](../architecture/semantic-embedding-dispatcher.md).


## SE-01 explicit pipeline status/bootstrap/activation

The following operator forms require an approved CLIP_DATABASE_URL process secret
and exact non-secret target/pipeline bindings. Do not put credentials in arguments,
chat/logs or files. The --execute flag is not target/action approval. No shared
or cloud target has been selected or mutated by this checkpoint.

| Command/form | Effects and expected result |
|---|---|
| `.venv/bin/python scripts/search_pipeline.py status --expected-host <approved-host> --expected-port <port> --expected-database <database> --expected-role <login-role> --pipeline-id <pinned-hex>` | Template, not an executed shared command. Exact URL and actual server binding before read-only aggregate status; absent registry stays absent. No inference/model startup. |
| Same bindings with `prepare --execute` | Explicit registration/planned->building, resumable without demotion/reset. Refuses retired/mismatch. No queue/inference/activation. |
| Same bindings with `queue --execute --batch-size <1..1000>` | One bounded reconciliation batch, current jobs preserved including failed; emits queued count plus aggregate status. Zero queue is not proof of completeness. |
| Same bindings with `activate --execute` | Separate full-current-coverage and conflict checks; initial transition or idempotent serving check, never replaces another space. Incomplete/failed/leased/current-edit gaps refused. Concurrent future writes still invalidate readiness; request guard remains. |
| `CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true .venv/bin/python apps/api/tests/domains/search/bootstrap_probe.py --isolated-bootstrap` | Verified private reproduction only: new0700Unix-socket native PG18.6/dbmate2.36,3controlled sources including1unavailable, actual operator subprocesses, worker/model, concurrency/status/refusals/resume and Hybrid/Keyword checks. <=10min/40windows,1simultaneous helper, sampled512MiB API/helper (PG/operator child RSS excluded). Stops owned resources/retains bootstrap-result.json/migration/stop logs; no listener/existing target/ambient DB/AWS accepted. |
| `.venv/bin/python -m pytest apps/api/tests/domains/listings/test_embedding_bootstrap.py tests/evaluation/test_search_pipeline_cli.py -q -W error` | Read-only/transition/refusal/binding/limits/error-redaction transport tests, no real DB/model. Real evidence is the guarded probe above. |

Operator operation deadline10s, connect<=5s, SQL5s/lock1s. CLI requires explicit
host/port/db/user in the URL; ambient PG/service/options/multitarget indirection
is refused. It accepts only the current pinned pipeline. Read/worker settings do
not invoke any of these operations. [Full scope/remaining gates](../architecture/semantic-pipeline-bootstrap.md).


## SE-01 Step10 isolated k6 preparation

All k6 binary/cache/config/raw output stays under ignored .tools/k6. No global
installation, Docker, PATH change, remote metric output or usage reporting. The
pinned installer targets this macOS ARM64 machine only; Linux remains unverified.

| Exact command | Target/effects/expected result |
|---|---|
| `.venv/bin/python -m scripts.evaluation.k6.install` | Official k6v2.3.0ARM64 archive (~30MB) and checksum file; pinned SHA256/binary version/Mach-O minimum OS before execute. Installs .tools/k6/v2.3.0/k6, no global links; refuses incompatible/checksum/symlink/mismatched cache. Public download needs network approval. |
| `PATH="$PWD/.tools/node/bin:$PATH" .tools/node/bin/node --test scripts/evaluation/k6/core.test.mjs` | Pure JS profile/response/generated-contract parity and pacing tests; no network/model. Also invoked by Python evaluation suite for existing CI coverage. |
| `.venv/bin/python -m pytest tests/evaluation -q -W error` | Evaluator/calibration/CLI plus load accounting/caps/installer metadata and Node tests; native calibration check skips unless its guarded fixture target is present. |
| `.venv/bin/python -m scripts.evaluation.k6.fault_probe` | Four short owned ephemeral loopback HTTP fixtures; wrong result/401/timeout/generator shortfall must stay invalid. <=2rps/2s,max2clients,timeout<=2s. Stops servers, retains raw/manifest/report under printed .tools/k6/fault-checks path. No DB/model/auth/provider. |
| `.venv/bin/python -m scripts.evaluation.k6.runner --profile data/evaluation/workloads/local-search-pilot-v1.json --port 8000 --output .tools/k6/pilots/UNUSED_RUN_NAME --isolated-local-pilot` | Requires explicitly owned native API already running. Strict loopback only,2rps,5s warm-up+10s measured,max2HTTPconcurrency,3s timeout,30request cap, bounded nonoverlapping drains. New ignored output dir, frozen manifest, local raw metrics, report; exit2oninvalid/missing/dropped/wrong/unauthorized/timeout outcomes. Stops/reaps owned k6; caller separately stops owned native API. Never a cloud/full-rate/real-auth/NFR command. |

Profiles under data/evaluation/workloads include draft browse20rps/search10rps,
300s proposals with unresolved final oracles. Runner refuses nfr-draft profiles.
Draft NFR01/02manifest templates keep actual target/auth/data/caps/repetition/
telemetry approval values null. See [full measurement definitions/remaining gates](../../scripts/evaluation/k6/README.md).

### SE-01 isolated semantic-helper typing correction

From the repository root, use the existing root mypy executable with the helper's
separate Python3.13 environment and fixed sibling-module search path:

```sh
MYPYPATH=apps/api/app/domains/listings .venv/bin/mypy --no-incremental --python-version 3.13 --python-executable .tools/semantic/venv/bin/python apps/api/app/domains/listings/embedding_helper.py
```

This command installs nothing and changes no global environment. It checks the
helper against its actual NumPy/tokenizers packages; ONNX Runtime's untyped import
has one explicit `import-untyped` exception because the pinned wheel supplies no
`py.typed` marker. Tensor shape/finiteness remain runtime-validated. No blanket
missing-import or untyped-function exceptions apply. Root application mypy with
only API Python3.14 dependencies is not a substitute for this helper check.
This supplementary check does not replace registered CI checks, real inference
tests, or pending Linux compatibility acceptance.

### SE-02 Step2 existing wanted/saved storage

The existing native command (no new tools) now runs `search-storage-smoke.sql`
as a fourth transactional smoke before and after migration rollback/reapply:

```sh
bash database/tests/native-checks.sh .tools/native-db/pgsql .tools/native-db/downloads/dbmate-macos-arm64 --listings-store
```

It creates and stops only its own new socket-only cluster and retains its logs.
The Docker command `uv run --locked python scripts/check_database.py` registers
the same fourth smoke but remains unverified here because Docker is absent.
Native evidence supplements, rather than replaces, that required acceptance.
No new schema migration is necessary for the existing wanted/saved fields,
closure/pending state, reference uniqueness and FKs.

The subsequent approved SE-02 category correction adds migration13/head
`20261025012200` and a populated category rollback/reapply test to both wrappers'
optional adapter suite. This supersedes the Step2 no-new-migration conclusion for
the wanted category reference only. The existing native `--listings-store` command
checks four smokes twice, all13downs/reapply, schema identity and the new fixture
test; no existing target is accepted. Docker acceptance remains pending.

### SE-02 Step3 wanted API checks

```sh
.venv/bin/pytest -q -W error apps/api/tests/domains/search/test_wanted.py
.venv/bin/mypy --no-incremental apps/api/app/domains/search/wanted_models.py apps/api/app/domains/search/wanted_store.py apps/api/app/domains/search/wanted.py apps/api/app/domains/search/wanted_routes.py
bash database/tests/native-checks.sh .tools/native-db/pgsql .tools/native-db/downloads/dbmate-macos-arm64 --listings-store
```

The existing native wrapper adds real wanted HTTP/concurrency/receipt checks,
creates only its own socket-only cluster, applies14migrations to20261025013000,
runs four smokes twice, all14downs/reapply/inventory, then stops its cluster.
Synthetic origin references remain retained in that disposable database; fixture
teardown never bypasses immutable-reference guards. Docker adapter registration
includes the same test, but Docker execution remains unavailable here. These
commands install nothing. No cleanup service, cloud/scheduler or real auth
provider acceptance is implied.

### SE-02 Step3 approved retirement checks

```sh
.venv/bin/pytest -q -W error apps/api/tests/domains/search/test_wanted_retirement.py
bash database/tests/native-checks.sh .tools/native-db/pgsql .tools/native-db/downloads/dbmate-macos-arm64 --listings-store
```

The native adapter suite adds `test_wanted_retirement_postgres.py`; its private
fixture-only SQL failure trigger is dropped after testing transaction rollback.
All controlled origins remain in the stopped owned database. The coordinator
processes one server-selected origin per explicit internal call and has no HTTP
route/CLI job/scheduler/startup invocation. Test approval does not authorize
cleanup against existing/shared/live data or deployment. No new migration or
tool installation is needed. Real Conversations calls remain an integration gate.

### SE-02 Step4 draft matching

```sh
.venv/bin/pytest -q -W error apps/api/tests/domains/search/test_draft_matches.py apps/api/tests/domains/search/test_wanted.py
.venv/bin/mypy --no-incremental apps/api/app/domains/search/draft_matches.py apps/api/app/domains/search/wanted_models.py apps/api/app/domains/search/wanted_routes.py
bash database/tests/native-checks.sh .tools/native-db/pgsql .tools/native-db/downloads/dbmate-macos-arm64 --listings-store
```

The native adapter suite adds the real-Listings draft-query HTTP check. It still
creates and stops only its own new database cluster; no new tool or migration.
Docker registration includes the same test, but Docker execution remains pending
here. Draft matching has no storage/worker/history side effect or UI activation.

### SE-02 Step5 saved-listing checks

```sh
PATH="$PWD/.tools/node/bin:$PATH" .venv/bin/pytest -q -W error apps/api/tests/domains/search/test_saved.py tests/contracts
.venv/bin/mypy --no-incremental apps/api/app/domains/search/saved.py apps/api/app/domains/search/saved_store.py apps/api/app/domains/search/saved_routes.py
bash database/tests/native-checks.sh .tools/native-db/pgsql .tools/native-db/downloads/dbmate-macos-arm64 --listings-store
```

Node is exposed only to that test process; nothing is installed or changed
globally. The native/Docker adapter list runs `test_saved_postgres.py` last so its
larger committed pagination fixture follows bounded math/bootstrap checks. It
uses only the fresh owned database and stops the cluster. Public Listings saved
providers are reviewed explicit scripts; actual provider integration remains
pending. No new migration, pool, job or cloud resource is needed.

### SE-02 Step6 coverage additions

```sh
PATH="$PWD/.tools/node/bin:$PATH" .venv/bin/pytest -q -W error apps/api/tests/domains/search/test_wanted.py apps/api/tests/domains/search/test_saved.py
bash database/tests/native-checks.sh .tools/native-db/pgsql .tools/native-db/downloads/dbmate-macos-arm64 --listings-store
```

The native adapter list adds `test_step6_postgres.py` for regular/temporary own
management, budget creation variants, context expiry across wanted operations,
and tied pagination with unavailable exclusion before slicing. It closes only
its own synthetic public requests after checking them. The coverage inventory
in `apps/api/tests/domains/search/README.md` explicitly leaves response initiation
and its races pending because that declared local handler is not implemented.
No skipped/missing response path is represented as a functional pass.

### SE-02 Step6 response correction verification

```sh
PATH="$PWD/.tools/node/bin:$PATH" .venv/bin/python scripts/generate_contracts.py check
PATH="$PWD/.tools/node/bin:$PATH" .venv/bin/pytest -q -W error apps/api/tests/domains/search/test_wanted_response.py tests/contracts
bash database/tests/native-checks.sh .tools/native-db/pgsql .tools/native-db/downloads/dbmate-macos-arm64 --listings-store
PATH="$PWD/.tools/node/bin:$PATH" npm run check
```

The root package owns web scripts (there is no apps/web npm workspace). Contract
tests compile the created/repeated TypeScript response consumer, and native tests
add real Search close/response locking plus a schema-only separate C FK fixture.
The response capability/thread provider remains an explicit C contract double.
No new installation/migration/pool or real provider acceptance is implied.

## SE-02 Step7 disposable wanted/saved UI preview

Mohit's existing repository-local Python/native PostgreSQL/Node tools only. No
installation, Docker, cloud, existing database target, scheduler or real account.
From repository root, with no database/AWS environment variables:

```sh
CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true .venv/bin/python apps/api/tests/domains/search/wanted_ui_preview.py --isolated-wanted-ui
```

This test-only CLI refuses missing opt-in/test settings and ambient database/AWS
configuration. It creates a fresh0700 cluster through the existing guarded native
runner, migrates it and serves only127.0.0.1:8000 with host/origin checks. Search
wanted/saved writes and Listings draft queries are real; Identity and saved-state
providers are explicit synthetic fixtures. Conversations/image delivery remain
unavailable. No successful conversation is simulated. Session/API runtime is capped
at30minutes; Ctrl+C also closes the pool and stops only its own cluster, retaining
its `/tmp/clip-listings-test-*` directory. Restart creates a new synthetic dataset.

Use the existing root `npm run dev` frontend on127.0.0.1:5173 (reuse a running
instance; strictPort refuses collisions). Open `http://127.0.0.1:5173`; the Search
views disclose their isolated backend after its first response. The localhost
address is a desktop-only target, not a phone URL. No bind/exposure change is
included. The built production app does not enable this test harness.

```sh
PATH="$PWD/.tools/node/bin:$PATH" npm run check
PATH="$PWD/.tools/node/bin:$PATH" CLIP_WANTED_UI_HTTP=true npm test -- wanted-native-http.test.ts
.venv/bin/pytest -q -W error apps/api/tests/domains/search/test_wanted_ui_preview.py apps/api/tests/domains/search/test_native_preview.py apps/api/tests/domains/search/test_browser_preview.py
```

The second command opts into two fixed-loopback TS-client/real-Search HTTP tests;
without its flag they are skipped. It creates/closes a synthetic wanted request
and unsaves/resaves one fixture pair, leaving the preview usable. It accepts no
arbitrary target URL. It verifies API wiring, not actual Identity/Conversations,
React interaction, Safari/device behavior or final SE-02 acceptance.
