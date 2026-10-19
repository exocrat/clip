# PR #7 review-correction evidence

**Observed:** 2026-10-19 15:26:39 UTC.

Suraj (B), branch `task/pr7-review-fixes`, based on PR #7 head `d82b54125d8e7ea86dc9179bfddf1b80300533e0`; main base `1171b4a6543851bf242da96a8211f3b947b9742a`. These results cover the uncommitted correction worktree, not the untouched PR head or a published revision. Suraj subsequently verified these results and approved the named fix commit (recorded 2026-10-19 15:31:26 UTC). Publication, current hosted CI and independent peer approval remain pending.

## Source fingerprints

SHA-256 fingerprints identify the exact tested behavior before a commit exists:

| File | SHA-256 |
|---|---|
| `infra/terraform/shared/test/scripts/setup-db-role.sh` | `0d205b55c395a2dff1551508039020a47cfbf045af5beebb7bd7b4617dcc222c` |
| `infra/terraform/shared/test/scripts/probe-db.sh` | `93792cd721574a2ede36efd67ef7dbd9f6c38f43e9186dbc60644967532120c4` |
| `tests/architecture/test_db_task_timeouts.py` | `95ebc0fc4ccbdf8783acbaf269dfe9c37b88980f270d6de01b68772e4926c0c2` |

## Environment and commands

Linux x86_64 host and Docker engine; Python 3.14.4, uv 0.10.7, Node 24.22.0/npm 11.19.1, Terraform 1.15.9 and locked AWS provider 6.69.1. Tools were selected explicitly with this session's local paths; no global installation or provider configuration was changed. Downloads/caches and dependency environments are generated local state.

For Python/Node commands, prepend `/tmp/clip-pr7-tools/uv-x86_64-unknown-linux-gnu:/home/suraj/src/.clip-tools/node-v24.22.0-linux-x64/bin` to PATH; use `UV_CACHE_DIR=/tmp/clip-pr7-uv-cache` and `NPM_CONFIG_CACHE=/tmp/clip-pr7-npm-cache`. Paths under `/tmp` are session-local conveniences, not durable tooling prerequisites for another contributor.

| Command | Observed result |
|---|---|
| `uv run --locked black tests/architecture/test_db_task_timeouts.py` | Exit 0; unchanged. |
| `uv run --locked pytest tests/architecture/test_db_task_timeouts.py -q -W error` | Exit 0; 8 passed. Real GNU timeout with shortened test durations stops a hung stand-in ignoring TERM; both tasks hide controlled private error output, override unlimited caller settings, and fail if the required tool is missing. |
| `make check` | Exit 0: Black 60 files, 395 root tests, 63 explicit data tests, boundaries, 3 current generated contracts, web lint/types/build and 16 tests, 35 wrapper cases, real PostgreSQL 18.6 clean/repeat migrations and schema smoke checks, Gitleaks 8.30.1 snapshot all passed. |
| `TERRAFORM_BIN=/tmp/clip-pr7-tools/terraform/terraform make terraform-check` | Exit 0: format and backend-disabled validation for both roots, readonly provider locks. No plan, remote state access or AWS action. |
| `bash -n infra/terraform/shared/test/scripts/setup-db-role.sh infra/terraform/shared/test/scripts/probe-db.sh` | Exit 0. |
| `git diff --check` | Exit 0. |

## Real database failure diagnostic

`python3 /tmp/clip-pr7-tools/check-pd16-db.py` exited 0 on a fresh `postgres:18.6-bookworm` container, with synthetic credentials generated only in process memory, networking disabled, no host ports and temporary database storage. The supplemental diagnostic is session-local; its future availability is not assumed. The permanent eight-case regression above remains in the repository.

- GNU coreutils `timeout` 9.1 was present in this candidate client image; a future selected immutable image still needs its capability check.
- The committed-form setup and probe scripts with the correction worktree contents both exited 0 on their normal paths.
- A probe against an unavailable local port exited nonzero with the safe failure message.
- A separate transaction held a database ACL lock for up to 90 seconds. Corrected setup waited on that lock and exited 1 after 30.2 seconds, without waiting for the holder's completion.
- The diagnostic removed its own disposable container successfully. No retained local database was used or reset.

These checks establish local script behavior. They do not accept native macOS/whole-lifecycle compatibility, RDS/ECS behavior, image publication, PD-16 completion or PRE-00.

## Documentation resolution and remaining work

The [runbook](../../../../infra/terraform/shared/test/README.md#ecr-retention-and-manual-cleanup), task list, proposal and [decision](../../../decisions/database-task-deadlines-and-manual-image-cleanup.md) now agree: retain images through normal stop/start, manually clean selected unused images, and manually empty/verify ECR before a separately approved full destroy. No force-delete setting or automated purge was added. The evidence index table is repaired.

No cloud cleanup, upload, deployment, API image build, commit, push or merge occurred in this correction step. The AMD64 API image remains a separate pending check. The correction diff and named commit are now human-approved. Commit and publish the fixes, review the changed PR revision, and run current CI before any exact-revision squash merge.
