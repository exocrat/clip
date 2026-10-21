# Runtime Command Registry

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
allowlisted context under `/tmp` containing only the two locked dependency
files, API source, Dockerfile and its ignore file. The Docker build uses the
host's native architecture and never contacts AWS:

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
mkdir -p "$build_context/apps/api"
cp pyproject.toml uv.lock "$build_context/"
cp -R apps/api/app "$build_context/apps/api/"
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

PD-08 Step 3 originally reserved `database/migrations/20261018094330_mvp_tables.sql`,
`20261018094331_mvp_integrity.sql`, `20261018094332_initial_catalogue.sql`, and
forward correction `20261018152702_reject_retired_origin_entries.sql`. That
checkpoint's head was `20261018152702`; the current CN-01 branch adds
`20261021101000_api_owned_retirement_and_trigger_boundaries.sql`, so its
expected head is `20261021101000` across five migrations.
`database/dbmate.version` pins 2.36.0 and
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
| `bash database/local-db.sh status` | Display migration state. Pending migrations can appear with exit 0; on the current CN-01 branch compare expected head `20261021101000` (five migrations). |
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
| `bash database/tests/native-checks.sh /tmp/clip-pd08-native.pKC5jz/pgsql /tmp/clip-pd08-native.pKC5jz/bin/dbmate` | Requires macOS/Bash 3.2+, native PostgreSQL 18.6 and dbmate 2.36.0 at these explicit tool locations. Creates only its own private `/tmp/clip-pd08-native-check.*` cluster/database `clip_test_native`; disables TCP, uses an owner-only socket, applies/repeats the current five migrations, runs both smoke suites, rolls back all five migrations, reapplies, compares ordered schema inventory and stops its cluster. Logs/data retained under printed evidence path. Nonzero on any failure or stop failure; inspect retained logs, never substitute an existing cluster. |

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

The native pass just described is historical evidence for the initial three migrations. The next checkpoint updated the harness for head `20261018152702` and four migrations; that macOS/dbmate route was not rerun here. The current CN-01 branch adds a fifth migration and expects head `20261021101000`; rerun the native route against this branch before treating it as current evidence. PR #5 correction checks include the then-current SQL round-trip and both smoke suites on an isolated Linux ARM64 PostgreSQL image, plus 35 simulated lifecycle cases. Internal metadata is preserved before separately redacting human diagnostics; these tests do not establish the real Compose lifecycle.

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
| `make contracts-double-check` | Run pinned Mypy against Search's consumer-owned Listings adapter and a typed Conversations retirement consumer using the generated provider protocol. |
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
| `uv run --locked python scripts/check_database.py` | Requires local Unix-socket Docker. Creates a fresh PostgreSQL 18.6 container with temporary memory-backed data, no host port/volume; dbmate 2.36.0 checks clean apply of five migrations, exact head `20261021101000`, repeat migration, both SQL smoke suites and the latest migration down/up round-trip. Removes only its own container; nonzero on SQL/setup/cleanup failure. Never targets retained Compose data. |
| `uv run --locked python scripts/check_secrets.py` | Requires local Unix-socket Docker. Gitleaks 8.30.1 scans tracked and nonignored new source in a temporary snapshot, offline/read-only. Uses `.gitleaks.toml`; findings print file/line/rule only and fail. This scans current source, not Git history; ignored files are excluded and symlinks rejected. |

Images may be downloaded from public registries. No cloud/provider configuration
is forwarded. These commands accept no target arguments; `--help` describes them.
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
| `make contracts-double-check` | Static type checks for the representative Listings interface double and Conversations retirement consumer probe. |
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
