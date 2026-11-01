# Runtime Command Registry

This file lists the common project commands and points to the current owner
guides for specialized workflows. Keep command-specific inputs, effects, safety
limits and recovery beside the tool or feature they operate. The work log keeps
task outcomes; it is not a second command history.

## Common local commands

Run these from the repository root. The [environment setup guide](README.md)
covers prerequisites, local targets, expected results and safe recovery.

| Purpose | Command | Notes |
|---|---|---|
| Install locked dependencies | `make setup` | Local Python and web dependencies; no cloud login. |
| Show available targets | `make help` | Lists the Make front door. |
| Run shared checks | `make check` | Python, web, database, contracts and secret checks. Terraform is separate. |
| Start local API/web | `make start-api`; `make start-web` | Foreground loopback services; stop each with Ctrl+C. |
| Start/check the local database | `make start-db`; `make seed`; `make migration-status` | Uses the retained local Compose database. Do not reset it as a recovery step. |
| Stop the local database | `make stop-db` | Stops the service and retains its data. |
| Generate/validate preview data | `make data-generate RUN_NAME=preview-42 SEED=42 USERS=3 LISTINGS=2`; `make data-validate RUN_NAME=preview-42` | Choose a fresh name. These files are scaffolding, not final domain data. |
| Static Terraform checks | `make terraform-check` | Backend-free formatting/validation; does not plan or apply cloud changes. |

The [API](../../apps/api/README.md), [web](../../apps/web/README.md),
[database](../../database/README.md) and [data](../../data/README.md) guides
own their detailed commands and limits.

## Feature and evaluation commands

| Work | Current command source |
|---|---|
| Search/Listings focused checks and isolated preview | [Search test guide](../../apps/api/tests/domains/search/README.md), [API guide](../../apps/api/README.md), and the browser procedure below |
| Schema-shaped search data | [Data generator guide](../../data/README.md#se-01-isolated-schema-shaped-corpus); these are not the final NEXT-06 dataset commands |
| Load-runner tools and bounded local pilot | [k6 tool guide](../../scripts/evaluation/k6/README.md) |
| NFR measures and final-run requirements | [NFR measurement design](../evaluation/nfr/measurement-design.md) and the approved [ECS/Lambda experiment design](../evaluation/ecs-only-vs-ecs-lambda-task-list.md) |
| Disposable database and SQL diagnostics | [Database guide](../../database/README.md) |
| Identity provider setup and real-run gates | [Identity setup guide](identity-provider-setup.md) |
| Cloud plans, targets and lifecycle | [Cloud inventory](cloud-inventory.md), the relevant [Terraform runbook](../../infra/terraform/shared/test/README.md), and the owning task's reviewed plan |

The k6 pilot is loopback-only and cannot accept an NFR. Draft profiles are not
approved full-run inputs. NEXT-06 and NEXT-07 must register their final exact
commands, inputs and evidence locations after the owning tools and data are
ready; do not infer readiness from an example or local pilot.

## SE-01 isolated discovery preview

Use only for the synthetic local Search screen. The API fixture listens on
loopback 8000 and the web app on 5173; both require the explicit preview flags.
They use no database, cloud, sign-in provider or storage. Ctrl+C stops each
foreground process.

```bash
CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true .venv/bin/python apps/api/tests/domains/search/browser_preview.py --isolated-search-ui
PATH="$PWD/.tools/node/bin:$PATH" NPM_CONFIG_CACHE="$PWD/.tools/npm-cache" NPM_CONFIG_USERCONFIG=/dev/null VITE_SEARCH_UI_PREVIEW=true .tools/node/bin/npm run dev
PATH="$PWD/.tools/node/bin:$PATH" NPM_CONFIG_CACHE="$PWD/.tools/npm-cache" NPM_CONFIG_USERCONFIG=/dev/null .tools/node/bin/npm run check
```

This preview is not real auth, SQL integration or an NFR result. Follow the
[browser procedure](browser-verification.md) for human review.

## SE-01 Hybrid read checks

Portable HTTP/binding/error checks:

```bash
uv run --locked pytest apps/api/tests/domains/listings/test_hybrid_read.py -q -W error
```

The owned native PostgreSQL/helper probe uses the existing pinned local tools:

```bash
LC_ALL=C bash database/tests/native-checks.sh "$PWD/.tools/native-db/pgsql" "$PWD/.tools/native-db/downloads/dbmate-macos-arm64" --hybrid-read
```

The native run creates and stops its own database/helper and retains private
results. It uses the already-local model, makes no cloud call and does not
measure NFR performance. On macOS, native process/shared-memory access may need
the contributor's local system approval.

Category-text regressions are included in that native command and the existing
`scripts/check_database.py --listings-store` container workflow through
`test_category_text_postgres.py`. They exercise current labels/reassignment,
cross-field AND, aliases/typos, filters, relevance, stable pagination and the real
shared draft provider. Coordinate-vector cases isolate SQL behavior; the
`--hybrid-read` run also exercises the actual pinned helper/worker with a
model-only category match. These checks do not score the frozen final query set
or establish cloud latency. The native runner rolls back its actual applied
migration count, avoiding a stale count when main adds migrations.

## Shared aggregate — PD-12 Step 6

`make check` runs the shared local quality gates and is the ordinary project
verification command. See [local setup and checks](README.md#checks-and-data-tooling)
for coverage and skipped-check limits. It makes no cloud changes.

## PD-11 boundary checks

`make check` includes the repository's executable architecture and contract
checks. See the [shared boundary rules](../conventions/shared-conventions-and-cross-domain-contract-rules.md)
and the relevant test README for exact focused commands. A focused pass does not
replace the full check or owner review.

## Identity provider offline checks — ID-01 Step 2

From the repository root, after `uv sync --locked`:

```bash
uv run --locked pytest apps/api/tests/domains/identity/test_email.py apps/api/tests/core/test_provider_settings.py apps/api/tests/test_config.py -q -W error
```

These checks use controlled clients and synthetic recipients. They create no
AWS client, send, listener or database. Passing them does not establish provider
delivery, real sign-in or ID-READY. See the
[Identity setup record](identity-provider-setup.md) for real gates.

## Explicit real local Identity bootstrap — ID-01 Step12 preparation

This is operator preparation only. Running it needs separate review and
approval for the exact secret/database access, recipients, network path and
time window. The acknowledgement flag is not approval.

```bash
uv run --locked python scripts/identity_runtime.py --help
uv run --locked python scripts/identity_runtime.py --check --approved-bootstrap
uv run --locked python scripts/identity_runtime.py --serve --approved-bootstrap
```

`--check` opens no listener. `--serve` may create real Identity state and send
mail; do not exercise auth flows without the reviewed recipients and cleanup.
Neither mode changes cloud infrastructure. See the
[Identity setup guide](identity-provider-setup.md#real-verification-and-approvals).

## Local API container image — PD-16 Step 4

Build from the repository root with Docker. Record the current revision, dirty
state and engine architecture. This stages an allowlisted context under
`/tmp`, builds for the local architecture, starts the container on loopback,
checks health and removes only the container/image/context created by this
invocation. It does not contact AWS. The published ECS image must instead be
built from the exact reviewed commit for `linux/amd64`.

```sh
(
set -eu
build_context=$(mktemp -d /tmp/clip-api-pd16.XXXXXX)
image_tag="clip-api:pd16-local-${build_context##*.}"
container_id=
image_id=
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

The source-only staging is deliberate: do not replace it with a repository-wide
Docker context. The [API guide](../../apps/api/README.md) describes the image
boundary and the separate Linux AMD64 publication gate.

The native ARM64 check is sufficient for Step 4. The user later confirmed the previously pending PD-08/PD-13 native-platform and database compatibility gates (2026-10-19); see the work log. PD-16 Step 7 subsequently built, uploaded and verified the `linux/amd64` image from its reviewed commit; see [PD-16 publication evidence](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/foundation/pd-16/README.md). The approved local procedure uses `sudo docker` on this host.

PD-16's ECS scale-to-zero and RDS stop/start procedures are documented in the
[shared test Terraform runbook](../../infra/terraform/shared/test/README.md#ecs-capacity-lifecycle).
The [target-specific RDS stop/resume plan](shared-test-rds-operations.md) supplies explicit profile, instance, waiter and status templates. These require separate reviewed cloud operations and are not part of this local
image build or `make check`.

## Native AMD64 API-image validation — PD-16 Step 7 local check

The [native validation evidence](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/foundation/pd-16/native-amd64-image-validation.md) records the exact clean source SHA, allowlisted `git archive` inputs, `DOCKER_BUILDKIT=0 docker build --platform linux/amd64` command, platform/non-root/runtime check and loopback HTTP/Docker-health checks. That run used Docker directly because the contributor already had local socket access; it did not require sudo or emulation. The archive excludes ignored/untracked files as well as all credentials, Git metadata and dependency caches.

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
historical expected head was `20261021101000` across five migrations. The CN-01
message-transport migration advanced the branch head to `20261022213000`
across six migrations. The public key-directory migration advances the current
CN-01 head to `20261023080000` across seven migrations.
`database/dbmate.version` pins 2.36.0 and
forward correction `20261018152702_reject_retired_origin_entries.sql` and Identity
hardening `20261023173439_identity_account_profile_integrity.sql`; current
isolated-branch head is `20261023173439` (PR10 integration deferred). `database/dbmate.version` pins 2.36.0 and
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
| `bash database/local-db.sh status` | Display migration state. Pending migrations can appear with exit 0; on the current CN-01 branch compare expected head `20261023080000` (seven migrations). |
| `bash database/local-db.sh status` | Display migration state. Pending migrations can appear with exit 0; isolated branch head is `20261023173439`; do not apply the isolated chain to retained/shared data before current-main integration. |
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
| `bash database/tests/native-checks.sh /tmp/clip-pd08-native.pKC5jz/pgsql /tmp/clip-pd08-native.pKC5jz/bin/dbmate` | Requires macOS/Bash 3.2+, native PostgreSQL 18.6 and dbmate 2.36.0 at these explicit tool locations. Creates only its own private `/tmp/clip-pd08-native-check.*` cluster/database `clip_test_native`; disables TCP, uses an owner-only socket, applies/repeats the current six migrations, runs both smoke suites, rolls back all six migrations, reapplies, compares ordered schema inventory and stops its cluster. Logs/data retained under printed evidence path. Nonzero on any failure or stop failure; inspect retained logs, never substitute an existing cluster. |

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

The native pass just described is historical evidence for the initial three migrations. The next checkpoint updated the harness for head `20261018152702` and four migrations; that macOS/dbmate route was not rerun here. The current CN-01 branch has seven migrations and expects head `20261023080000`; rerun the native route against this branch before treating it as current evidence. PR #5 correction checks include the then-current SQL round-trip and both smoke suites on an isolated Linux ARM64 PostgreSQL image, plus 35 simulated lifecycle cases. Internal metadata is preserved before separately redacting human diagnostics; these tests do not establish the real Compose lifecycle.

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

CN-03 offline provider checks: `uv run --locked pytest apps/api/tests/domains/conversations -q -W error`. These use synthetic recipients and fake SES/SSM/HTTP dependencies, with no provider send; the threaded adapter requires a local environment that permits worker threads.

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
It checks canonical-source parity, all 56 declared domain HTTP operations plus
health, implemented Listings/Search/Conversations routes, sensitive-field publication boundaries, and
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
`npm run check`, database-wrapper safety, clean-schema, and Conversations
database-operation checks. Python lint/type tools remain deferred under the
existing tooling decision.

| Command | Effect / failure |
|---|---|
| `uv run --locked python scripts/check.py conversations-retirement` | Requires local Unix-socket Docker and locked Python dependencies. Creates a fresh PostgreSQL 18.6 container with tmpfs storage and a random host port bound only to `127.0.0.1`; applies the checked-in 32-migration chain with dbmate 2.36.0; runs Conversations, notification delivery/retention, and Listings conversation-start tests with synthetic data; then removes only its own container. No caller-selected database target or cloud configuration is accepted. Nonzero on startup, migration, test, timeout, or cleanup failure. |
| `uv run --locked python scripts/check_database.py` | Requires local Unix-socket Docker. Creates a fresh PostgreSQL 18.6 container with temporary memory-backed data and no host port or persistent data volume; dbmate 2.36.0 checks clean apply, repeat migration, all seven SQL smoke suites plus Identity upgrade/atomicity checks, rollback of every migration and clean reapply against the migration files in the current checkout. The combined 32-migration chain ends at `20261029182500` with 41 domain tables. Removes only its own container; nonzero on SQL/setup/cleanup failure. Never targets retained Compose data. |
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

## CN-01 — disposable Conversations database checks

Combined runtime preparation checks (Rahul, CN-01 integration Step4):

```bash
uv run --locked pytest apps/api/tests/test_database_lifespan.py apps/api/tests/test_config.py apps/api/tests/core/test_security_boundaries.py -q -W error
uv run --locked pytest apps/api/tests/test_conversation_identity_integration.py apps/api/tests/domains/identity/test_application_composition.py -q -W error
```

The first command controls pool I/O and checks real composition/configuration
failure paths without live dependencies. The second requires local Unix-socket
Docker and cached PostgreSQL18.6/dbmate2.36 images, creates/migrates only its own
disposable databases and exercises actual signed-in owner/chat workflows. Signer,
mail and external image metadata are controlled ports; no fixed caller establishes
session evidence. Both commands accept no persistent database target and perform
no AWS/secret lookup, real mail delivery or deployment. Expected result: all
collected tests pass; not readiness, encryption or cloud-performance acceptance.
Use the existing `npm run build` for the normal web artifact; this does not build
or deploy a container. [Combined runtime setup](../../apps/api/README.md#combined-conversations-runtime--cn-01-integration)
documents same-target pool configuration, schema/grant gates and liveness limits.

The approved90-day cleanup command is
`uv run --locked python scripts/conversations_cleanup.py --expected-database DATABASE --expected-host HOST --expected-port PORT`.
It reads only `CLIP_CONVERSATIONS_DATABASE_URL`; placeholders must match the
reviewed target and are never credentials. Default is dry-run counts only;
`--batch-size` defaults100/max1000. `--apply` mutates eligible content and requires
a separately approved persistent-target run plan. No cutoff override or schedule
exists. Errors are generic; per-thread rollback and retry preserve ID/sequence
guards. See the [approved mechanism](../decisions/conversation-content-cleanup.md).
The registered disposable runner below includes real retention/rollback checks.

Browser checkpoint setup: `CLIP_ENVIRONMENT=test uv run --locked python
scripts/conversation_browser.py --isolated-conversation-browser --check-only`
creates and removes only one new disposable local PostgreSQL container and
checks real Listings/Conversations HTTP/SQL, seller selection and loopback/
Origin/write guards. Requires the normal
web build (`npm run build`), local Unix-socket Docker and the pinned images.
Without `--check-only`, it serves the built UI at `http://127.0.0.1:5273` and
`:5274` for two fixed synthetic identities, real SDK/IndexedDB and chat SQL.
Default cap30min, `--seconds`60–3600; Ctrl+C stops both sides/pools and removes
only its container. No target/host/identity override, live provider or AWS access.
Refuses ambient DB/provider settings and non-test startup. This is not real
session authentication or CN-CORE/NFR acceptance. See the
[exact browser walkthrough](conversation-browser-test.md). The agent starts it
and supplies URLs; the human does not reconstruct setup.

Run `uv run --locked python scripts/check_conversations_retirement.py` from
the repository root, or use `.venv/bin/python` with the already synchronized
locked environment. It requires local Unix-socket Docker and the pinned
PostgreSQL 18.6/dbmate 2.36.0 images. It creates one tmpfs-backed database
container on a generated loopback port, applies migrations to branch head
`20261027112205`, runs the focused retirement/thread/offer/message/directory/recovery
storage tests with warnings treated as errors, then removes its own container.
It accepts no database target and uses only synthetic users and opaque test
payloads. Exit 0 means the collected checks passed; ordinary pytest without
this harness skips database tests when its private test DSN is absent.

`uv run --locked python scripts/check_database.py` separately checks clean
migration application, exact/repeated head, both SQL smoke suites, latest
rollback and reapplication on its own disposable database. It verifies that
rolling back recovery storage preserves the prior directory/transport schema.
These checks do not prove real Identity, origin-owner or browser integration.
## Identity provider offline checks — ID-01 Step 2

From the repository root, after `uv sync --locked`:

```bash
uv run --locked pytest apps/api/tests/domains/identity/test_email.py apps/api/tests/core/test_provider_settings.py apps/api/tests/test_config.py -q -W error
```

Runs controlled configuration/transport checks using injected clients and
synthetic recipients. No AWS client, send, network listener or database is
created. Exit 0 means collected offline checks pass; failures and exit 5 are not
success. This does not establish SES permission, actual delivery, Microsoft
sign-in or ID-READY. The [setup record](identity-provider-setup.md) owns real gates.

## Identity one-shot email command — ID-01 Step 2

Offline checks from the repository root:

```bash
uv run --locked pytest apps/api/tests/domains/identity -q -W error
uv run --locked mypy --no-incremental apps/api/app/domains/identity/email_smoke.py
```

Tests inject synthetic providers/role responses and never send mail. Exit 0
means collected local checks pass, not delivery or runtime-role evidence.

The future approved ECS image uses working directory `/app/apps/api` and command
`python -m app.domains.identity.email_smoke`. This is a LIVE operation only with
separately approved task/image/send inputs; do not run it as a local delivery
shortcut. Default settings refuse sending. It requires explicit smoke approval,
test mode, SES selection, exactly one allowlisted recipient and the expected ECS
container-role credentials. It attempts one fixed generic message, suppresses SDK
logs and exits within a 45-second command deadline. Success output means provider
acceptance only. See the [bounded plan](../evaluation/identity/provider-history.md#delivery-diagnostics).

### Identity diagnostic wrapper offline checks — ID-01 Step 2

Run from the repository root:

```bash
uv run --locked pytest apps/api/tests/domains/identity/test_runtime_diagnostic.py apps/api/tests/domains/identity/test_email.py apps/api/tests/domains/identity/test_email_smoke.py -q -W error
uv run --locked black --check docs/evaluation/identity/id-01-step-2/runtime_diagnostic.py apps/api/tests/domains/identity/test_runtime_diagnostic.py
```

The tests import the exact reviewed diagnostic command from the evaluation folder
and inject offline SDK failures/success. They perform no AWS calls or sends;
expected result is 28 passing tests. The wrapper itself can send when explicitly
run with approved ECS settings; do not invoke it as a local test command. Its
[live request and cleanup plan](../evaluation/identity/provider-history.md#delivery-diagnostics)
require separate exact approval. No new Make target or deployment command added.

### SES authorization diagnostic offline checks — ID-01 Step 2

```bash
uv run --locked pytest apps/api/tests/domains/identity/test_authorization_diagnostic.py apps/api/tests/domains/identity/test_runtime_diagnostic.py apps/api/tests/domains/identity/test_email.py apps/api/tests/domains/identity/test_email_smoke.py -q -W error
uv run --locked black --check docs/evaluation/identity/id-01-step-2/runtime_authorization_diagnostic.py apps/api/tests/domains/identity/test_authorization_diagnostic.py
```

These are offline checks (37 tests), not a send command. The extended diagnostic
parses denied-resource/reason text only in memory and emits fixed categories;
[the exact live plan](../evaluation/identity/provider-history.md#delivery-diagnostics)
retains a separate approved task/send/cleanup window. Shared sandbox plans must
preserve the private `TF_VAR_ses_sandbox_recipient_identity_arn` when its additional
identity scope is still needed; see the shared Terraform README. Never supply
its value in a shell argument, repository file or printed evidence.

### Identity schema verification — ID-01 Step3

`uv run --locked python scripts/check_database.py` is the existing database gate
used by `make check`; it now covers the Identity-only fifth migration and three
SQL smokes. It creates only a new tmpfs PostgreSQL18.6 container with no host
ports/retained volume and uses pinned dbmate2.36.0 with strict ordered migration,
explicit empty dotenv input and advisory locks. No external target arguments,
cloud/profile/database credentials or retained database are accepted.

The new identity-schema-smoke.sql checks valid/invalid profile/contact bounds,
revocation event pairing/chronology, provider-mapping immutability/uniqueness/FK,
and original UTC/activation/enrollment protections. identity-upgrade-seed.sql and
identity-upgrade-check.sql create/verify only synthetic rows in that disposable
database. Upgrade failure must preserve incompatible data and leave no applied
version/partial constraints. Successful upgrade/down/reapply preserves rows.

The native macOS runner's source now expects five migrations/head20261023173439,
21 functions/33 triggers and three smokes; only Bash syntax is checked on this
Linux ARM64 contributor environment. Earlier native run evidence is historical.
PR10/current-main combined-chain verification remains pending before ID-READY;
no persistent/shared database apply is authorized by local check success.

### Microsoft token/account checks — ID-01 Step4

```bash
uv run --locked pytest apps/api/tests/domains/identity/test_microsoft.py apps/api/tests/domains/identity/test_microsoft_postgres.py -q -W error
uv run --locked mypy --no-incremental apps/api/app/domains/identity/microsoft.py apps/api/app/domains/identity/microsoft_accounts.py apps/api/app/core/config.py
```

The first file uses fresh in-memory RSA keys and controlled public-metadata
responses, never a real user/token. The second requires a local Unix-socket
Docker context and creates a new network-none tmpfs PostgreSQL18.6 instance,
SCRAM-authenticated socket under a private test directory, and pinned dbmate
2.36.0 migrations. No retained target or host ports are accepted. It tests actual
validator/store concurrency, stable mapping, revocation and transaction failure;
finally removes only its own container. Root/API pytest includes these real DB
checks, so Docker is now required for that full suite. Runtime dependencies are
locked PyJWT2.15.1 crypto and psycopg3.3.6 binary; tests do not call Microsoft.

Public discovery/JWKS reads are distinct from sign-in checks. No public route,
session cookie, trusted CallerContext or production Microsoft integration is
installed by these checks; nonce lifecycle/session design remains a real gate.

### Temporary OTP primitives and offline delivery — ID-01 Step 5 (partial)

```sh
uv run --locked pytest apps/api/tests/domains/identity/test_temporary_crypto.py apps/api/tests/domains/identity/test_temporary_policy.py apps/api/tests/domains/identity/test_temporary_delivery.py apps/api/tests/domains/identity/test_email.py -q -W error
uv run --locked mypy --no-incremental apps/api/app/domains/identity/temporary_crypto.py apps/api/app/domains/identity/temporary_policy.py apps/api/app/domains/identity/temporary_delivery.py
```

Uses synthetic keys, controlled time and a recording SDK client with the actual
SES adapter. Exercises normalization, protected target/verifier binding, shared
attempt windows, concurrent one-shot delivery, leading-zero codes, suppression,
expiry and uncertain provider failures. No AWS client, live send or database is
used. These checks do not establish transactional persistence or real delivery.

### Transactional temporary OTP checks — ID-01 Step5

```sh
uv run --locked pytest apps/api/tests/domains/identity/test_temporary_postgres.py -q -W error
uv run --locked mypy --no-incremental apps/api/app/domains/identity/temporary_challenges.py apps/api/app/domains/identity/temporary_crypto.py apps/api/app/domains/identity/temporary_policy.py apps/api/app/domains/identity/temporary_delivery.py
uv run --locked python scripts/check_database.py
```

The test reuses `postgres_fixtures.py` through explicit Identity conftest
registration. Each module gets a new private socket/SCRAM PostgreSQL18.6/dbmate
2.36.0 target with no host port, network or retained data; cleanup removes only
its owned container. Synthetic mail capture/SDK failures do not contact AWS.
Checks exercise source/target limits, shared failures/latest expiry, duplicate
and consume races, rollback, eligibility, non-renewal, key continuity and safe
uncertain SES outcomes. No password activation/reset or session is implemented.

The migration checker now verifies six migrations/head20261023192856,27 tables,
four SQL smokes, preserved historical Step3 failure/round-trip proof, and empty
OTP down/up with legacy-row preservation. Occupied down refusal is covered by
actual service tests. Native harness source is updated but no new macOS run is
claimed; PR10/current-main integration remains pending. These commands accept no
retained/cloud DB target and do not authorize provider sends or cleanup jobs.

### Temporary account activation — ID-01 Step6 (private)

```sh
uv run --locked pytest apps/api/tests/domains/identity/test_temporary_passwords.py apps/api/tests/domains/identity/test_temporary_activation_postgres.py apps/api/tests/domains/identity/test_temporary_postgres.py -q -W error
uv run --locked mypy --no-incremental apps/api/app/domains/identity/temporary_passwords.py apps/api/app/domains/identity/temporary_accounts.py
uv lock --check --offline
uv pip check --python .venv/bin/python
```

Uses actual Argon2id hashing and the shared private disposable PostgreSQL fixture,
controlled time and synthetic OTP/mail/password data only. Tests activation time,
exact336-hour expiry, concurrent/replayed proof, rejected challenge/password,
atomic rollback on hash/credential/enrollment failure, enrollment after credential
cleanup and stale-caller/current-state denial. Existing Step5 integration tests
remain included. No user input/password/OTP file, actual email, ambient DB target,
cloud action or live cleanup is used. Runtime hashes are sensitive and never
responses/logs; lock pins argon2-cffi25.1.0 and bindings26.1.0. Public session/API/UI
and real protected-operation/provider checks remain pending before ID-READY.

### Sessions, Identity HTTP and bounded cleanup — ID-01 Step7

```sh
uv run --locked pytest apps/api/tests/domains/identity/test_sessions_postgres.py apps/api/tests/domains/identity/test_identity_http.py apps/api/tests/domains/identity/test_identity_cleanup.py -q -W error
uv run --locked mypy --no-incremental apps/api/app/domains/identity/sessions.py apps/api/app/domains/identity/http.py apps/api/app/domains/identity/cleanup.py scripts/identity_cleanup.py apps/api/app/domains/identity/microsoft_accounts.py apps/api/app/domains/identity/temporary_accounts.py apps/api/app/domains/identity/temporary_passwords.py apps/api/app/domains/identity/temporary_challenges.py
uv run --locked python scripts/check_database.py
make contracts-check
```

Requires local Docker for fresh private PostgreSQL18.6/dbmate2.36.0, no retained
DB target or host port. Actual RSA/Argon2id/session/HTTP/cleanup implementations
use synthetic keys/accounts/mail only. Covers cookie/CORS/CSRF/origin/context,
atomic credential/reset/activation/Microsoft replay races, idle/absolute/account
expiry, limits, bounded cleanup/CLI target checks and permanent guard retention.
No real provider or frontend browser is used. Normal app.main includes health/Listings; Identity runtime remains unbound;
explicit create_identity_app runtime binding still needs reviewed secrets/DB
roles/TLS/proxy/provider configuration before deployment. Never treat arbitrary
forwarded headers as trusted source/identity.

Cleanup invocation (reference only; no retained/cloud execution authorized):

```sh
uv run --locked python scripts/identity_cleanup.py --expected-database clip_test_identity
```

Supply CLIP_IDENTITY_DATABASE_URL through the approved secret-access path,
never argv/logs/files; no dotenv fallback. Default is count-only; --apply writes
only after exact target/dry-run/operator approval, and --batch-size is1–1000
(default100 per table). No schedule is installed. Output is per-table counts,
errors are generic and apply can be partially committed before a failure; retry
rechecks cutoffs. Do not delete lifetime markers/users/key bindings. Step9 removes only source
contacts/display names at the approved thirty-day terminal cutoff.
The revised migration checker expects seven versions/head20261023202807 and30
tables/five smokes while preserving historical Step3/5 proofs. Revised native
harness is syntax-checked only on Linux; PR10/current-main integration pending.

### Capability policy and public runtime binding — ID-01 Step8

```sh
uv run --locked pytest apps/api/tests/core/test_runtime_bindings.py apps/api/tests/domains/identity/test_capabilities_postgres.py apps/api/tests/domains/identity/test_capabilities_http.py tests/contracts/test_runtime_binding_generation.py tests/contracts/test_domain_declarations.py tests/contracts/test_identity_declarations.py -q -W error
uv run --locked mypy --no-incremental apps/api/app/core/runtime_bindings.py apps/api/app/domains/identity/capabilities.py apps/api/app/domains/identity/sessions.py apps/api/app/domains/identity/http.py apps/api/app/domains/identity/public.py
make contracts-check
```

Uses explicit context scopes and actual PostgreSQL/RSA/session/HTTP with synthetic
keys/accounts only, through the existing new private socket/tmpfs DB fixture.
Tests26 regular/temporary matrix combinations, fresh lifecycle/stale/forged
context, exact class/boolean result, unavailable/unbound503, parallel real
providers, generated adapter invariants and malformed results/metadata. HTTP
probes are fixture-only capability categories, not implemented marketplace
resources. Source declarations refuse; only generated eligibility dispatches.
Other generated domains and HTTP/OpenAPI/TypeScript shapes stay unchanged.
No runtime/provider/cloud/retained data action or full FR-03 claim; Step14 keeps
its required actual consumer matrix and ID-READY keeps real integration gates.

### Own profile/contact sharing and cleanup — ID-01 Step9

```sh
uv run --locked pytest apps/api/tests/domains/identity/test_contacts.py apps/api/tests/domains/identity/test_contacts_http.py apps/api/tests/domains/identity/test_identity_cleanup.py tests/contracts/test_domain_declarations.py -q -W error
uv run --locked mypy --no-incremental apps/api/app/core/runtime_bindings.py apps/api/app/domains/identity/contacts.py apps/api/app/domains/identity/cleanup.py apps/api/app/domains/identity/sessions.py apps/api/app/domains/identity/http.py apps/api/app/domains/identity/public.py
```

Uses only synthetic data/keys and owned disposable PostgreSQL, no provider or
retained/cloud cleanup. Covers own display-name/field CRUD, immutable login,
scoped confirmed-only sharing/privacy, fresh denial, concurrent writes and exact
thirty-day cutoff/guard preservation. Controlled sharing grants are not actual
CN membership/confirmation evidence. Existing contracts-generate/check commands
regenerate the two additional selected dispatch adapters; HTTP schemas unchanged.
Use the existing target-checked cleanup command only with separate actual-target
approval; no scheduler/deadline acceptance follows from local tests. Full make
check remains the aggregate gate; ID-READY/provider/browser integration is open.

### Deterministic Identity security integration — ID-01 Step10

```sh
uv run --locked pytest apps/api/tests/domains/identity/test_microsoft.py apps/api/tests/domains/identity/test_identity_security_integration.py apps/api/tests/core/test_security_boundaries.py tests/fixtures/core/test_providers.py -q -W error
```

Explicit signed_tokens/jwt_clock fixtures control only the installed PyJWT date
lookup during requesting tests; actual RSA/claim checks stay enabled and the
patch is restored afterward. No global wall-clock change or production fake
activation. Owned disposable SQL/actual HTTP tests cover lifecycle/reset/contact/
retention/concurrency; shared guarded fake and actual production startup controls
remain in their existing owners' tests. No provider/send/retained DB/cloud action.
The full make check includes these tests and all pre-existing OTP/session/privacy
coverage; local results cannot accept real provider/browser/consumer/readiness.

### Identity first UI checkpoint — ID-01 Step11

```sh
CLIP_ENVIRONMENT=test uv run --locked python scripts/identity_ui_preview.py --synthetic-preview --seconds 1800
npm run dev -- --mode identity-preview
```

Separate foreground terminals; URL `http://localhost:5173/sign-in`. Both bind
loopback only; fixed API8001/Vite5173, fail on conflicts. Script creates only an
owned no-network disposable PostgreSQL18.6/dbmate2.36.0 database, transient keys
and synthetic-only mailbox. It refuses non-test environment/implicit enablement;
60–3600s cap, default1800s, or Ctrl+C then own DB removal. Stop Vite separately.
No real SES/Microsoft call, account/credential input, retained DB or cloud action.
Use only the reserved example recipient documented in apps/web/README.md.
Preview mode cannot build/deploy; ordinary dev has no proxy and ordinary builds
remove preview inbox. Normal API startup includes health/Listings; Identity remains explicitly unbound.

```sh
uv run --locked pytest apps/api/tests/domains/identity/test_ui_preview.py apps/api/tests/test_health.py -q -W error
npm run check
```

Python checks refusal, unbound-Identity production composition, actual registration/
SQL/cookie and non-loopback denial. Web checks include DOM interaction tests
with synthetic contract responses and existing route/import boundaries. Source
formatter remains disabled automatically; an explicit one-off web-local command
can format only this step's new files using `npx biome format --write
--javascript-formatter-enabled=true --javascript-formatter-indent-style=space
--javascript-formatter-indent-width=2 --javascript-formatter-line-width=100
--javascript-formatter-quote-style=single <explicit-file-paths>` from apps/web.
No shared formatter configuration change. Full make check remains required;
local/browser doubles do not accept actual provider/device/ID-READY gates.

The Step11 recovery increment uses the same preview commands/ports and disposable
backend; no new route/provider/resource. After restarting the harness, recreate
its synthetic account. Wait the shared60s OTP cooldown, then exercise Forgot
password → reset code → new password → explicit sign-in. Existing make check/
npm run check include the added reset UI cases. Preview restart discards only
its own ephemeral data; it never reconnects to a retained/shared database.

The Step11 contact-editor increment uses the same capped synthetic preview and
registered make check/npm run check commands. Visit `/account/contacts` after
signing in. Existing backend tests use actual own-contact SQL/HTTP; new DOM
cases cover CSRF/refetch/delete/privacy/known-actor race behavior. Headless layout
positive controls use explicitly intercepted synthetic read results and are not
real authenticated provider evidence; human exercises the actual local API.

### Microsoft browser UI — ID-01 Step11

Existing `npm run check` and `make check` include the controlled SDK/callback/
StrictMode/replay/recovery tests. The same capped identity-preview commands serve
local disabled-button and callback/error/status screens; no new resource/provider
or route. Preview always disables Microsoft. Public build flag
VITE_MICROSOFT_SIGN_IN_ENABLED defaults false in the example; the API does not
read it and it grants no authority. Actual enablement, metadata/token traffic,
registered localhost/HTTPS redirect, consent/default scopes, provider artifacts
and server-cookie flow need their own approved live/runtime verification plan.
No live-enable command or provider action is authorized by this registry entry.

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

### Shared Identity/Listings API composition — ID-01 Step12

`uv run --locked pytest apps/api/tests/domains/identity/test_application_composition.py apps/api/tests/domains/listings/test_integrations.py -q -W error`
checks the real shared factory with disposable PostgreSQL, actual session/OTP/
signed-token validation and Listings routes. Synthetic signer/mail are explicit
controlled ports; no fake caller override, external provider, shared database,
secret-manager read or retained data. Requires local Docker and locked setup.
Checks regular cookie/eligibility, temporary browsing and sale/upload denial,
contact CSRF, logout, expiry/revocation, per-app isolation, one-time installation,
pool closure and refusal of incomplete/production/demo bindings. No website or
provider acceptance is inferred. `app.main:app` remains unbound by default.


### Identity database setup procedure — ID-01 Step12 (local checks only)

`uv run --locked pytest apps/api/tests/domains/identity/test_database_setup.py -q -W error`
uses the owned networkless PostgreSQL18.6 fixture and applies current migrations.
It changes roles/ACLs only inside that disposable container and removes the owned
container afterward. Requires the locked environment and local Unix-socket Docker;
no AWS credentials, cloud calls, published DB port or shared database URL are used.
Expected: real SCRAM restricted-login validation, unchanged-key startup audit,
existing-role collision and unsafe metadata/logging/target refusals, and rollback
after a post-create failure. Failures remain failures; no retry or live fallback.
`make check` includes these tests. Strict typing:
`uv run --locked mypy --strict apps/api/app/domains/identity/database_setup.py`.

`database_setup.py` exposes operator-only `inspect_identity_database` and
`create_identity_role` functions with an explicit connection factory and expected
database/admin. They are not connected to startup or a live CLI. Each transaction
has5-second statement/3-second lock limits; the execution launcher must separately
bound total process/connection time. Live launcher/private networking, credentials,
RDS start, exact SQL, URL publication and cleanup still need their reviewed plans.


### Safe Identity database metadata — ID-01 Step12

`uv run --locked pytest apps/api/tests/domains/identity/test_database_metadata.py -q -W error`
checks only owned disposable PostgreSQL. Requires local Unix-socket Docker and
locked setup; no AWS credentials, secret reads or shared database URL. Expected:
missing migration tracker/column/schema reported as findings; later failures
retain completed allowlisted fields; wrong targets stop; the actual transaction
is repeatable-read/read-only. `make check` includes the suite. Strict types:
`uv run --locked mypy --strict apps/api/app/domains/identity/database_metadata.py`.

`collect_database_metadata` accepts an explicit trusted connection factory and
expected database/admin, returning a serializable report. `complete` means the
metadata collection completed, not that setup or migrations passed. Inspect
required-version and inventory/logging/ACL fields; missing objects remain blockers.
It has no live CLI, secret retrieval, provider, writes, repair or retries. Live
callers still require exact endpoint/account/TLS checks, process/connection bounds,
a separately approved secret read/window and sanitized report handling.


### Identity migration runner and logging probe — ID-01 Step12 local checks

`uv run --locked pytest apps/api/tests/domains/identity/test_migration_runner.py -q -W error`
requires locked setup, Linux Docker on a local Unix socket, cached/retrievable
PostgreSQL18.6/dbmate2.36 images. Creates only owned disposable PostgreSQL containers
with tmpfs data, an ephemeral loopback-published TLS port and synthetic short-lived
certificates/passwords. Unlike the networkless socket fixtures, this fixture uses
Docker bridge plus loopback publication to test real TLS. Deletes its own container
and synthetic private key afterward; no AWS/shared URL or real credential is used.

Expected: pinned23file clean/repeat (head20261027112205;40tables/36functions/46triggers),
real TLS hostname mismatch rejection, no secret
in Docker config/args, hash/image/namespace/prefix/target refusals, real partial-DDL
preservation and no replay, client-success structural postconditions, timed-out
version-client cleanup, and rollback-only logging role/default checks. Full
`make check` includes the tests. Strict types:
`uv run --locked mypy --strict apps/api/app/domains/identity/migration_runner.py`.

The operator functions have no live CLI or startup binding. `run_migrations`
requires the reviewed manifest/image, fixed target and trusted private connection;
live use rejects the current image-review-pending manifest. `probe_logging`
creates only a passwordless NOLOGIN probe role inside a rolled-back transaction
and checks absence/defaults through a fresh connection. Neither function retrieves
AWS secrets or grants cloud authorization. The recorded17-file shared target is
still refused: preparing this candidate does not add an incremental upgrade mode.
That target requires a reviewed Step13 reset/bootstrap (Aditya reports no
application data requiring preservation), or a separately approved upgrade.
Read-only preflight is not permission
to call these write-capable tools; exact window, SQL/role probe, metadata/secret
access, shared-schema review and cleanup approvals remain mandatory.

### Offline Identity migration review consistency — ID-01 Step12

```bash
uv run --locked python scripts/identity_readiness.py --upstream <full-accepted-main-commit-sha>
```

Reads local Git objects and current source only; no fetch, Docker, SQL connection,
settings/credential load, provider request or file write. Requires locked Python
setup. Use the actual accepted main revision after integrating it. Exit0 means
manifest/reference/SHA, runner compatibility, recorded local image, preserved
upstream SQL and reviewed migration/setup source agree. Exit1 means the review
package is stale/invalid; inspect the safe JSON check names and reconcile source
and evidence. Git external diff/text conversion drivers are disabled.

`ready_for_live` is always false: success is not image/owner/cloud approval or a
live-schema inspection. The runner's live-review guard is not modified. Refresh
manifest/candidate/runner expectations after upstream schema changes and rerun
real disposable migration tests before requesting a live apply.

Focused offline regression command:
`uv run --locked pytest apps/api/tests/domains/identity/test_readiness_audit.py -q -W error`.
Strict types: `uv run --locked mypy --strict scripts/identity_readiness.py`.

### Explicit real local Identity bootstrap — ID-01 Step12 preparation

**Prepared only; running either mode requires separate live secret/DB access
approval.** Import/help is offline:

```bash
uv run --locked python scripts/identity_runtime.py --help
```

After the exact account/region, references, database roles/URLs, recipient list,
network/TLS route and execution window have been reviewed and approved:

```bash
uv run --locked python scripts/identity_runtime.py --check --approved-bootstrap
uv run --locked python scripts/identity_runtime.py --serve --approved-bootstrap
```

The acknowledgement flag prevents accidental startup; it does not grant approval.
Both modes retrieve fixed Identity SSM keys/DB URL/email configuration and perform
real Identity database safety checks. Warmup does not send mail. `--check` opens no
listener and does not start/check the Listings pool. `--serve` starts the existing
combined app on127.0.0.1:8000, one worker, no reload or forwarded-header trust, with
safe application logging and raw access logging disabled. Auth requests can create
real state and dispatch real mail, so exact user/recipient/send/cleanup approval is
required before exercising them. Ctrl+C closes the app's own pool; it does not
stop cloud infrastructure or delete data.

Requires explicit local/test Settings, Microsoft+dual selectors, controlled
recipient list, debug off and the separate private Listings `CLIP_DATABASE_URL`;
Identity uses its own fixed SSM DB URL/login. Do not put credential values in
arguments, this guide, logs or chat. The UI uses registered
`http://localhost:5173/auth/callback`;127.0.0.1 is not a Microsoft callback alias.
Use the normal Vite API proxy to8000, not the synthetic preview proxy to8001.
Enable the existing Microsoft UI flag only in the approved real test session.
Default app.main, production rejection and synthetic preview behavior are unchanged.

This is operator-local preparation, excluded from the production API image. It
is not a deploy route or proof of image CA trust, actual permissions or delivery.
The corrected local image installs regional RDS roots and selects the standard
OS CA file; AMD64/Hybrid rebuild and real deployed TLS acceptance remain gated.
See the image-trust checks below and integration evidence.

Checks: `uv run --locked pytest apps/api/tests/domains/identity/test_runtime_command.py -q -W error`
and `uv run --locked mypy --strict scripts/identity_runtime.py`.

### Real-provider local demo — ID-01 Step12

`uv run --locked python scripts/identity_local_demo.py --approved-live-local --recipient APPROVED_ADDRESS --seconds 10800`

Requires exact human approval for live access and each controlled recipient; repeat
`--recipient` for up to five. Uses profile `adityalaxmi1` to capture short-lived
credentials privately, reads only `/clip/test/identity/authentication-keys` and
`/clip/test/identity/email-delivery`, and uses a generated local Identity URL.
No shared DB URL/master secret, AWS mutation or automatic send. Creates a fresh
network-isolated PostgreSQL18.6 container through the existing disposable helper,
applies the current migrations, and creates separate Identity and marketplace
logins. The latter has local Listings/Search table grants only. Real Microsoft
validation, email routing, sessions and HTTP handlers are unchanged; no fixture
signer, mailbox route or auth bypass is installed. API binds127.0.0.1:8000 with
raw access logs/proxy trust disabled. Ctrl+C or the60–14400second cap removes
only this run's container/data; local accounts are disposable. Credentials remain
in process memory; never print provider/DB configuration. Script/tests are outside
the image's copied application source.

Start the frontend with `VITE_MICROSOFT_SIGN_IN_ENABLED=true npm run dev`; browse
`http://localhost:5173/sign-in`, not127.0.0.1. Both ports must be available. Real
registration/reset requests send to approved recipients; startup does not send.
No image uploads/Hybrid/cloud/ID-READY acceptance is implied. Offline checks:
`uv run --locked pytest apps/api/tests/domains/identity/test_local_demo.py -q -W error`.

### Hosted test-mode Identity startup — ID-01 Step12 preparation

The default `app.main:app` stays Identity-unbound. The explicit ASGI opt-in is
`CLIP_IDENTITY_RUNTIME_ENABLED=true`; Settings accept it only with
`CLIP_ENVIRONMENT=test`, `CLIP_IDENTITY_PROVIDER=microsoft`,
`CLIP_EMAIL_PROVIDER=dual`, debug/development auth off, a separate Listings
`CLIP_DATABASE_URL`, the exact JSON origin list
`CLIP_IDENTITY_BROWSER_ORIGINS=["https://clip-iisc.site"]`, and the approved
controlled-recipient list. The app reads only the three fixed Identity SSM
parameters during ASGI import and fails closed if they, the restricted Identity
DB role, or the email snapshot are invalid. It performs no migrations or sends at
startup. Auth requests can create account/session state and send real email.

This is prepared code, not an operator command or current deployment config. The
shared ECS task still lacks these settings, SSM access, the separate Listings DB
URL/role, and a reviewed public HTTPS/proxy route. Do not enable the flag until
the exact runtime, ingress, recipient and cleanup plan is approved. If
`CLIP_SERVE_WEB_APP=true`, Identity routes and marketplace APIs use `/api` with
the bundled UI; otherwise the HTTPS same-origin proxy must strip `/api` before
forwarding to the API's unprefixed routes. Uvicorn forwarded-header trust remains
unset until the actual proxy peer is verified.

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
cases, three pre-connect guards); cluster stop succeeded. [Retained evidence](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/domain/se-01/native-postgres/result.json).
Two earlier failed runs remain for the corrected GIN diagnostic, fixture
retirement publication/age and browse marker ordering. Production constraints
were preserved. These native tool/configuration results do not accept real
providers, final corpus/labels, full pipeline-switch coverage or FR/NFR gates.

The same native command subsequently passed the expanded bootstrap/switch matrix:
`/tmp/clip-pd08-native-check.4FB6Mb`, eight adapter checks (five DB/three guards),
schema round trip and successful cluster stop. [Expanded evidence](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/domain/se-01/native-pipeline-switch/result.json).
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
[the evidence](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/domain/se-01/frontend-modes/result.json) remain pending.


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
creates only its own socket-only cluster, applies17migrations to20261025013000,
runs seven smokes twice, all17downs/reapply/inventory, then stops its cluster.
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

### API image RDS root trust — ID-01 Step12

Public certificate integrity check (no Docker or network):

```bash
uv run --locked pytest apps/api/tests/domains/identity/test_image_trust.py::test_public_regional_roots_match_pinned_manifest_and_are_current -q -W error
```

To check a previously built local image, select its exact local tag or immutable
image ID; the test never pulls:

```bash
CLIP_IDENTITY_TEST_IMAGE=clip-api:id-ready-rds-ca-arm64-local uv run --locked pytest apps/api/tests/domains/identity/test_image_trust.py -q -W error
```

This verifies the selected local image and fixture-owned PostgreSQL TLS only.
It does not prove AMD64, Hybrid-image or deployed RDS readiness. See the
[trust decision](../decisions/identity-rds-system-trust.md) and
[Identity setup guide](identity-provider-setup.md#api-image-database-trust).

## LI-02 Step 9 — isolated PostgreSQL browser checkpoint

For the local Listings browser review, use the locked Python environment, Node
24/npm 11 and a local Unix-socket Docker daemon. This starts an owned synthetic
PostgreSQL database and the real Listings routes on loopback. It uses no cloud,
shared database, real sign-in or object storage; Ctrl+C stops only its owned
process/container and preserves the labelled rows for an explicit resume.

```bash
npm run build
CLIP_ENVIRONMENT=test CLIP_DEVELOPMENT_AUTH=true uv run --locked python apps/api/tests/domains/listings/browser_demo.py --isolated-listings-browser --image-ui-preview
```

The page is served at `http://127.0.0.1:5174/listings/new`. See the
[human browser procedure](browser-verification.md) for the actions and viewport
checks. To inspect or resume a retained fixture, use only the exact private
session path printed by the tool and its documented `--inspect`/`--resume`
options; do not substitute a shared or cloud target.

## LI-02 demo lifecycle

These commands operate a separate temporary cloud demo. They can publish images,
create resources and data, send no general safety guarantee from this index, and
must not be run without reviewing the current account, inventory, costs, exact
plans, public exposure and cleanup.

```bash
make li02-demo-start AWS_PROFILE=<approved-profile>
make li02-demo-stop AWS_PROFILE=<approved-profile>
```

The start command continues its own recorded partial run; stop cleans only its
run-owned resources and retains published images. Read the current
[cloud inventory](cloud-inventory.md) and
[shared-test Terraform runbook](../../infra/terraform/shared/test/README.md)
before considering either command. Past human approval does not authorize a new
run.

### SE-01 isolated semantic-helper typing correction

From the repository root, the helper's separate Python 3.13 environment and
fixed module path are required:

```sh
MYPYPATH=apps/api/app/domains/listings .venv/bin/mypy --no-incremental --python-version 3.13 --python-executable .tools/semantic/venv/bin/python apps/api/app/domains/listings/embedding_helper.py
```

This installs nothing. It checks the helper against its actual pinned runtime;
it does not replace CI, inference checks or platform acceptance.

## NEXT-03 complete local inspection

After building the normal web bundle with pinned Node/npm, run:

```bash
CLIP_ENVIRONMENT=test .venv/bin/python scripts/marketplace_inspection.py --synthetic-inspection
```

This creates only its own disposable PostgreSQL18.6 database, runs the actual
authenticated app action sweep, seeds synthetic inspection records and serves
the normal built application at `http://127.0.0.1:5174/__inspection`. It uses the
pinned local Hybrid model/interpreter and synthetic external signing/mail/photo
storage. No AWS, real mail, or retained database is used. Account switching stays
in the loopback-only launcher and is absent from deployed code. Ctrl+C removes
its database and temporary photos; `--check-only` checks and cleans up without
serving. `--port 5175` starts an independent debugging fixture while preserving
the default5174 inspection session; ports outside5174/5175 are rejected. Full steps and sample-account guidance are in the
[NEXT-03 visual checklist](../tasks/next-03-step-10-visual-checklist.md).

Requires locked Python/Node dependencies and local Docker, using only owned
disposable PostgreSQL. The first command starts one loopback ephemeral HTTP port,
uses the real shared app/cookie/CSRF/domain SQL and runs the actual TS adapters in
Vitest. Only signing/mail/image metadata and browser Origin/cookie/proxy handling
are synthetic. No public test-auth/OTP-inbox endpoint, live provider/send/secret or
cloud target is used. It cleans its server/socket/container and redacts transient
synthetic cookies in /tmp/clip-id-ready-csrf-http-node.log. The standalone JS HTTP
case skips unless the Python owner supplies CLIP_IDENTITY_TRANSPORT_HTTP privately;
never supply a real cookie or retained/hosted target. Ordinary npm checks skip it.
This automation is not actual browser/device, deployment or full Step14 evidence.
The second command proves normal/production runtime exposes no synthetic CSRF
route and existing isolated local/hosted profiles retain their transport gates.

### Identity HTTPS proxy preparation — ID-01 Step13

`TERRAFORM_BIN=/path/to/terraform-1.15.9 uv run --locked python scripts/check_identity_https_proxy.py`
runs the fixed mock plans in a temporary copy without a backend, state/plan/tfvars,
AWS configuration/credentials or metadata credentials. Readonly provider schema
installation may contact the public registry; no AWS resource API or live plan is
performed. Expected3passes: defaults off, exact trust/no secret-read role, missing
upstream/date refusal. Cleanup removes only the private copy.

`uv run --locked pytest apps/api/tests/domains/identity/test_proxy_transport.py -q -W error`
uses the existing disposable PostgreSQL/controlled signer fixture. Expected6passes
for actual Identity HTTPS/origin/cookie gates behind exact Uvicorn peer trust.
No provider, cloud, retained database or DNS query is involved.

`make terraform-check` remains the backend-free all-root format/schema check;
`make check` includes the Python transport cases but not the mock-plan wrapper.
[Reviewed scope and remaining approval gates](../evaluation/identity/id-01-step-13/README.md).

## ID-01 Step13 — native Micro build preparation

These operator helpers require the separately approved exact
[build/database window](../evaluation/identity/id-01-step-13/build-and-database-window.md).
They are not `make check`, an application startup path or authorization to start AWS.

| Command | Effects and expected result |
| --- | --- |
| `uv run --locked pytest -q tests/test_identity_build_transfer.py` | Four real disposable loopback HTTP/host-grammar tests; synthetic bytes only, no AWS/Docker/provider/SQL. Tests hash/size/overwrite boundaries and completed-artifact-only downloads; local sockets require the ordinary test permission. |
| `uv run --locked python scripts/identity_build_transfer.py --help` | Help only; does not create a directory, listen or bootstrap. The script is stdlib-compatible with the host Python3. |
| `python3 scripts/identity_build_transfer.py --directory "$ID01_BUILD_DIR" --source-sha256 "$ID01_SOURCE_SHA256"` | Only on the reviewed disposable private build host: creates a fresh owner-only directory and loopback18765 server for at most two hours of request admission. One exact ≤100MiB source upload; completed image/result downloads only. No extraction, AWS APIs, credentials or build. Stop owned process/session and terminate host at cleanup. |
| `bash scripts/identity_amd64_build.sh "$ID01_BUILD_DIR" "$ID01_SOURCE_SHA256" "$ID01_SOURCE_COMMIT"` | Only root on approved native x86_64 disposable host with Docker25 and completed source upload. Validates fixed run path/archive; adds2GiB temporary encrypted-root swap; bounded sequential45minute build,512MiB RAM/1536MiB RAM+swap, Microsoft button true/demo false, optional web-build Node heap768 (requires exact-window approval); non-root/platform/loopback health/UI smoke and hash-bound image export. No AWS API/push/SQL/provider. Exit0 exposes completed image.tar/result.json; failures stop the trial, never resize automatically. Owned swap/container cleanup on exit; final host termination is required even after failure. |

Live transfer uses the approved SSM forwarding document, never public ingress or
a remote Docker socket. Local Docker may load/store/push AMD64 without executing
it; publication still needs the reviewed account/repository/tag approval.

## ID-01 Step13 — bootstrap review preparation

`uv run --locked pytest -q tests/test_identity_bootstrap_review.py` runs three
owned disposable local PostgreSQL18.6/TLS review cases: cross-schema FK/view
dependency detection, live-target predicate refusal and historical-grant
insufficiency for current invoker triggers/Conversations. It applies only the
unchanged23-file package to its fixture and removes its container; no shared
SQL, AWS, provider, credential lookup or live reset.

`docs/evaluation/identity/id-01-step-13/bootstrap-inventory.sql` is a pinned-target
repeatable-read/read-only review input, not an automatic live command. Proposed
live counts/window/master read need the separate approval in the linked
[bootstrap plan](../evaluation/identity/id-01-step-13/bootstrap-and-grants-plan.md).
The destructive coordinator/grants package is still gated, not registered as
an executable route.

## ID-01 Step13 — guarded bootstrap preparation

| Command | Effect and evidence limit |
|---|---|
| `uv run --locked python scripts/identity_bootstrap.py` | Inert documentation entry; does not connect or reset. Actual execution is an operator API requiring reviewed bound inputs and separate live approval, not an unattended CLI. |
| `uv run --locked pytest -q tests/test_identity_bootstrap.py tests/test_identity_bootstrap_review.py` | Thirteen disposable local TLS tests covering guarded17→23 bootstrap, lock/role preservation, refusal/rollback and restricted trigger grants. Requires Docker; never supply a shared database. Not hosted acceptance. |

[Exact proposed live target, grants, failure behavior and60minute/$1 window](../evaluation/identity/id-01-step-13/bootstrap-live-review.md). No live execution is authorized by these commands.

## ID-01 Step13 — window-only retention launcher

`uv run --locked python scripts/identity_retention_job.py --help` is inert.
`uv run --locked pytest -q tests/test_identity_retention_job.py` runs four offline
safety checks; no cloud/DB. `--image`, `--revision` and `--deadline-utc` bind the
operator job; default is dry-run. `--apply` and installing the inactive proposed
service/timer require the [exact live approval](../evaluation/identity/id-01-step-13/retention-window-review.md).
The launcher uses unchanged identity_cleanup.py inside the actual container,
returns counts only and never installs scheduling itself. No build is needed.

For an SSM-shell invocation of the retention launcher, supply the actual root
account HOME only to that process (resolve it with pwd); SSM omits HOME. The
reviewed service has User=root and its actual automatic run supplies the proper
account environment. Do not change system-wide environment or job source to
work around that caller context. [First scheduled run](../evaluation/identity/id-01-step-13/retention-window-result.json).

## ID-01 Step14 — actual consumer authorization matrix

`uv run --locked pytest apps/api/tests/domains/identity/test_consumer_capability_matrix.py -q`
runs the mounted HTTP routes with real cookie/CSRF middleware and actual domain
services on a fresh, network-isolated disposable PostgreSQL18.6 database. The
Identity fixture owns and removes its container; never supply a shared DSN.
Controlled signer/mail/clock and ordinary SQL listing/image metadata are test
inputs. This command does not access AWS, actual S3 objects, Hybrid serving,
provider delivery or hosted database roles, and cannot accept those gates.

`uv run --locked pytest apps/api/tests/domains/identity/test_consumer_capability_matrix.py apps/api/tests/domains/identity/test_conversation_runtime_principal.py -q`
also exercises the opt-in proposed Conversations login in a separate disposable
fixture database. The proposal lives in the Step14 evidence directory and is
never applied by application startup or migrations. Only that owned test cluster
creates/drops the login and revokes its database's PUBLIC TEMP/schema CREATE;
never run these fixture operations against a retained/shared database. Actual
consumer flows and privilege denials do not accept live grants/SSM provisioning.

## ID-01 Step14 shared consumer runtime mock plans

Use pinned Terraform1.15.9. In a new private temporary directory, copy only
`infra/terraform/shared/test/*.tf`, `.terraform.lock.hcl`, `tests/` and `scripts/`
(no `.terraform`, state, tfvars or credentials). Clear ambient cloud/TF_CLI_ARGS
settings. Run `terraform init -backend=false -input=false -lockfile=readonly`,
`terraform validate`, then `terraform test` in that disposable copy. Both test
files use `mock_provider "aws"`; no AWS API, shared backend or real secret values.
Four consumer tests cover unchanged defaults, exact separate-secret injection/
permission, explicit Hybrid capacity/flags and invalid opt-in refusals; three
HTTPS tests retain existing proxy checks. No mock result authorizes deployment,
creates the proposed SQL login/SSM parameter or proves measured resource fit.

## ID-01 Step14 role-only operator preparation

`uv run --locked pytest tests/test_identity_conversations_role.py -q` creates
only a network-isolated fixture database/role, checks refusals/rollback and
removes its cluster. `scripts/identity_conversations_role.py` is an import-only
operator library; it has no default DSN/CLI/cloud client or startup hook.
`provision` requires a private connection callback, SecretStr password and
explicit approved SQL hash. Live use requires the exact separately approved
role/credential plan; the default live guard rejects the fixture target.
`credential_uri` returns a masked SecretStr only; never print/serialize its
private value to logs, argv or ordinary Terraform input/state. SSM storage is
separate; no rotation, repair or automatic unknown-outcome retry.

Step14 role-window connections use the approved private SSM remote-host tunnel
on local loopback5432 so the fixed RDS host/port guard and verify-full certificate
name remain intact (`hostaddr=127.0.0.1`). Recheck port availability before start.
Stored runtime DSN uses `sslrootcert=system`, matching the existing image's pinned
RDS roots; operator transport uses the reviewed public CA files. The helper
also accepts an explicit absolute CA path and rejects query-based user/options
overrides. This documentation authorizes no start or credential operation.

`uv run --locked pytest tests/test_identity_private_aws.py tests/test_identity_conversations_role.py -q`
checks the Linux RAM-backed AWS CLI payload transport and role guards locally.
The CLI helper never runs on import; cloud writes require explicit opt-in and
the separately approved window. Responses may contain secrets and stay in memory.

`uv run --locked pytest tests/test_identity_catalogue_lock_grants.py -q` proves
the two column-level FOR SHARE grants against disposable PostgreSQL; it never
changes a shared database. The live grants require affected-owner review and
durable restoration handling before task acceptance.

## NEXT-06 reference generation and isolated local loading

The [reference generator guide](../../data/README.md#next-06-reference-inputs-and-local-loading)
registers the exact generate/validate/test commands and retained two-run names.
`data.generators.reference` accepts only generate/validate, fresh named outputs
under data/runs, explicit UTCmidnight/day/threshold and an external ordinary image
root. It rechecks45approved photo hashes/magic/sizes and safe paths. No overwrite,
reset, database/cloud target, provider call, photo modification or session creation.
The amended2026-10-30runs contain5000regular users/1000listings/1000planned objects.
The guide also registers `scripts.evaluation.reference_local` with required
`CLIP_ENVIRONMENT=test` and `--isolated-local-reference`: fresh fixed-role Unix-only
native PG18.6,29migrations, real local photo bytes and Listings HTTP checks.
Optional `--embeddings` uses the installed pinned offline model and supported
pipeline tools; it verifies1000current vectors, searches and automatic vector
publication in a separate probe clone. No existing/cloud target is accepted;
owned processes stop and private evidence is retained. Caller/storage fixtures
do not accept actual Identity/S3; human labels/freeze/DATA-READY remain pending.
Use a fresh name and current UTCday
for future generation; old run validation is read-only. Deployment/upload/load
commands and actual storage prefix/target require separate cloud approval.

The same local command additionally accepts `--rebuild-check` with `--embeddings`
for Step6. Only the new DB created by that invocation is reset, migrated/reloaded
and re-encoded; record/media/vector/index fingerprints must match. The ordinary
loader retains its nonempty-target refusal. No target/prefix URL or forced-drop
option exists. See the guide for the exact command and local freeze-candidate
limits; this is not authorization to reset existing/cloud data or accept DATA-READY.


## NEXT-06 guarded cloud adapter — offline preparation

The [operator handoff](../evaluation/domain/next-06/cloud-handoff.md#6-review-the-prepared-cloud-adapter-then-load)
registers exact `data.generators.reference_cloud plan` and `load` forms.
`plan` is offline and validates inputs; `load` requires an explicit fully reviewed
JSON target, fresh private ledger, exact TLS process secret and `--execute`, plus
separate cloud approval. The null target template is not executable. Only account
335523638354/ap-south-1/non-root identity is permitted. The15minute CLI enforces
create-only/hash-verified media, exact server/role/schema, empty rows/registry and
transactional validation. No reset/migrate/grant/delete/start/retry is implemented.
No live execution or actual session/S3/IAM acceptance has occurred.

```sh
.venv/bin/python -m data.generators.reference_cloud plan --name next06-transfer-42-20261030-a --image-root /absolute/path/to/clip-dataset-images
.venv/bin/python -m pytest data/tests/test_reference_cloud.py -q -W error
```


### NEXT-06 browser-login compatibility

The explicit `reference_cloud load` command now uses `reference_login.sdk_session`.
For a named `login_session` profile it delegates to the existing AWS CLI process
credential-export interface, captures credentials only in memory and refreshes
before expiry; no CRTextra, access keys or global AWSprofile writes are needed.
Offline `plan` remains client/credential-export free. Existing non-login profiles
keep their normal SDK chain. Account, non-root, region, target and action gates
remain unchanged; no live cloud load is accepted by this local compatibility fix.

```sh
.venv/bin/python -m pytest data/tests/test_reference_login.py data/tests/test_reference_cloud.py -q -W error
```


### NEXT-06 prepared private read-only DBinventory window

The [exact proposal](../evaluation/domain/next-06/transfer/start-access-load-proposal.md)
records fixed resources, public-price evidence, proposed1USD/60+15min budget,
conditional ASG safety and cleanup, and separately gated later load phases.
`scripts/evaluation/reference_db_inventory.py` is inert without its explicit mode
and is intended only for the approved existing remote host, not the contributor's
Mac. Its reviewed SSMpayload is prepared but NOT approved/executed. It uses the
existing instance role/cached pinned APIimage, captures only one named runtime
connection secret to stdin, enforces fullTLS/readonly/nonsuperuser SQL and reads
only metadata. No pull/install/grant/schema/data mutation exists. Cleanup checks
its random label and removes only that owned container ID. Missing tools/image/
permissions/route cause refusal, not fallback. Do not run this under current
read-only-metadata approval or use it as a generic remote shell.

```sh
.venv/bin/python -m pytest data/tests/test_reference_db_inventory.py -q -W error
```

Prepared local-only [v2 probe diagnostics](../evaluation/domain/next-06/transfer/probe-diagnostic-v2.md) supersede the proposed remote payload. Historical Phase A failed with both resources stopped. A retry is not authorized by local preparation; verify exact hashes and obtain separate cloud-window approval.

NEXT-06 private admin catalog inventory: [exact proposed window](../evaluation/domain/next-06/transfer/admin-inventory-plan.md). Local guard tests: `.venv/bin/python -m pytest data/tests/test_reference_admin_inventory.py -q -W error`. The helper imports inertly; only the separately approved hash-bound controller may connect. Repository-local plugin `.tools/session-manager/1.2.896.0/bin/session-manager-plugin --version` is a local version check, not cloud-session approval.

NEXT-06 isolated database setup: [exact proposed cloud scope](../evaluation/domain/next-06/transfer/database-setup-plan.md). Local unit controls: `.venv/bin/python -m pytest data/tests/test_reference_database_setup.py -q -W error`. Real native permission rehearsal: `.venv/bin/python -m scripts.evaluation.reference_setup_local --local-rehearsal`; creates only a fresh Unix-only cluster under `/private/tmp`, uses existing pinned PG/dbmate, compares full schema and exercises restricted bulk SQL, then stops/retains it. macOS may require sandbox approval for shared memory. No AWS/media/model/provider calls. This command never approves cloud setup; both new cloud roles remain NOLOGIN until separate credential/load authorization.

NEXT-06 exact S3/SQL load package: [proposed scope and recovery](../evaluation/domain/next-06/transfer/cloud-load-plan.md). Local controls: `.venv/bin/python -m pytest data/tests/test_reference_load_access.py data/tests/test_reference_cloud.py -q -W error`. Native authentication/revocation proof: `.venv/bin/python -m scripts.evaluation.reference_setup_local --local-rehearsal --credentials`; only a fresh private Unix cluster, actual SCRAM/bulk SQL then credential clearing and stopped cleanup. Uses existing native tools, no AWS/S3. Proposed cloud controller is not a general CLI and refuses unconfirmed storage review before any AWS call; exact cloud action approval remains separate.

NEXT-06 dedicated vector-producer preparation: [exact proposed cloud window](../evaluation/domain/next-06/transfer/vector-window-plan.md). Unit controls: `.venv/bin/python -m pytest data/tests/test_reference_vector_access.py -q -W error`. Actual local model/role/SQL rehearsal: `.venv/bin/python -m scripts.evaluation.reference_setup_local --local-rehearsal --credentials --vectors`; new private Unix-only PG18.6 cluster, canonical schema/restrictedbulk/SCRAM, dedicated producer/real pinned worker and productionSQLcases, source invariance and password/helper/cluster closeout. Existing tools/model only; no AWS/S3/HTTPfake caller. Cloud execution needs the exact separate approval; raw metadata/APIflags do not enable an app runtime.

NEXT-06 current dataset reproducibility: `CLIP_ENVIRONMENT=test .venv/bin/python -m scripts.evaluation.reference_local --name next06-transfer-42-20261030-a --image-root /Users/mohitmahapatra/Desktop/clip-dataset-images --isolated-local-reference --embeddings --rebuild-check`. Requires existing native tools/model/photos; creates/resets only its new private Unix target and stops it. No AWS. The SELECT-only `reference_freeze_snapshot.py` is a bound reader, not a general target CLI. [Read-only cloud comparison scope](../evaluation/domain/next-06/transfer/dataset-evidence-plan.md) needs separate approval.

NEXT-06 Step3 runtime metadata inspection: `.venv/bin/python -m scripts.evaluation.reference_runtime_inspection --approved-cloud-inspection`; requires separate exact [read-only plan](../evaluation/domain/next-06/transfer/step-03-runtime-inspection-plan.md) approval. Fixed non-root335523638354/Mumbai;10metadata calls maximum, no secret values/starts/writes. Controls: `.venv/bin/python -m pytest data/tests/test_reference_runtime_inspection.py -q -W error`.

NEXT-06 Step3 real workflow: native-only preparation `CLIP_ENVIRONMENT=test .venv/bin/python -m scripts.evaluation.reference_workflow_local --local-rehearsal`. Actual Microsoft/browser/S3mode requires separate [exact live plan](../evaluation/domain/next-06/transfer/step-03-workflow-live-plan.md) approval; no SSMsecret/RDS/EC2 actions. New private SQL/model process stops on exit; reference data untouched. Tests: `.venv/bin/python -m pytest data/tests/test_reference_workflow_local.py -q -W error`.

NEXT-06 Search vector operator: [narrowed automatic Step3 plan](../evaluation/domain/next-06/transfer/step-03-search-vector-plan.md) supersedes the manual Listings exercise. The existing local workflow command now serves a loopback-only operator page after real sign-in; it invokes unchanged public APIs and verifies current vectors before/after one edit. No product UI/feature change; separate live S3/provider approval required. Unit controls: `.venv/bin/python -m pytest data/tests/test_reference_search_operator.py data/tests/test_reference_workflow_local.py -q -W error`.

NEXT-06 Step5 labels: `.venv/bin/python -m scripts.evaluation.reference_labels validate --image-root /absolute/path/to/clip-dataset-images`. Existing canonical22judgments/actual corpus bindings are revalidated, never rewritten; no network/provider/model/SQL/scoring. Requires retained/restored named payload and original45photos/full accepted source Git objects. Initial `write` creates fixed outputs only once and refuses existing files. [Step5 evidence](../evaluation/domain/next-06/transfer/step-05-final-labels-result.json); Step6freeze remains separate.

NEXT-06 frozen release: `.venv/bin/python -m scripts.evaluation.reference_release validate --image-root /absolute/path/to/clip-dataset-images --model-root /absolute/path/to/model`. Verifies both payloads, all52archive members, actual load ledger/model/index/reset/label evidence without extraction/network/inference/SQL. Initial `freeze` exclusively creates the fixed release and refuses overwrite; do not remove a release to bypass versioning. [Task-wide handoff](../evaluation/domain/next-06/task-wide-review.md). Valid content is separate from DATA-READY/CI/peer/run approval.
