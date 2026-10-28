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
