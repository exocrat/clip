# Coordinated database migrations

PD-08 Step 3 supplies **provisional** SQL migrations from the
[schema](../docs/architecture/mvp-database-schema.md). Mohit authorized proceeding
before affected-owner review; review and full runtime acceptance remain pending.
Native PostgreSQL checks have passed as described below; Compose is unverified.
No API, domain service, provider, deployment or crypto implementation is supplied.

## Tool and migration head

Future cloud backup/restore planning is in
[backup-and-restore.md](backup-and-restore.md) (PD-08 Step 7). It assigns the
PD-16/INT-01 handoff, finite-retention/privacy decisions, isolated restore
procedure and NFR-07 evidence. No cloud commands or operations are implemented
or authorized by that document; deferred Step 6 checks remain open.

`dbmate.version` pins dbmate **2.36.0**, a standalone SQL migration tool. The
selected image is `ghcr.io/amacneil/dbmate:2.36.0`; Step 5 wires the local
container route and real container verification remains Step 6. Native tool
execution passed in Step 6. No shared Python/Node manifest or other owner's directory
was changed. [Tool rationale](../docs/decisions/database-migration-tool.md).

| Ordered migration | Purpose |
|---|---|
| `20261018094330_mvp_tables.sql` | Four owned namespaces, 23 application tables, FK/scalar/live-versus-retired constraints, query indexes and the deferred current-offer FK. |
| `20261018094331_mvp_integrity.sql` | Cross-row guards, deferred publication/member/entry/offer consistency, immutable origin/key/operation identities, sequence allocation, unread-episode and source-derived notification invariants. |
| `20261018094332_initial_catalogue.sql` | The approved eight categories/four conditions only; no users, fake credentials, private data or final evaluation dataset. |

Expected final migration version: **20261018094332**. One integrator allocates
later timestamp identifiers; no parallel heads or uncoordinated edits to initial
DDL. Published/applied migrations are corrected forward, not rewritten.

The up/down sections use dbmate transactions. Future invocation must explicitly
select migrations directory, `--strict`, `--no-dump-schema`
and an explicit empty/non-secret env-file path to prevent implicit root `.env`
loading. Use `migrate`, not an implicit database-create/drop command. Step 5
supplies the target-validating local wrapper described below; Step 3 itself
provided only migration/test source.

One named operator serializes full migration CLI runs. Every up/down transaction
also takes advisory key `(1129072976, 8)` with a 10-second lock wait. Version
2.36.0 does not support the main branch's newer `--migration-lock` option; do not
pass it or promise automatic concurrent CLI safety. The SQL lock serializes DDL
transactions, but a concurrently planned stale migration can still fail and
must be inspected/retried only after the other operator finishes.

Down sections name only these objects and avoid broad `CASCADE`. They are
destructive local-test definitions, not permission to roll back a live database;
unrelated/later dependencies cause failure. No schema dump is hand-maintained.

## Local PostgreSQL configuration (PD-08 Step 4)

[Root Compose](../docker-compose.yml) selects **PostgreSQL 18.6**, official image
`postgres:18.6-bookworm`. The image publisher lists both arm64v8 (this Mac) and
amd64; neither platform has been run here yet. This pins the database minor
version and OS family, not an immutable image digest. See the
[version decision](../docs/decisions/local-postgresql-version.md).

The sole service, `postgres`, creates local database/user `clip_local` on first
initialization, requires nonempty `CLIP_LOCAL_POSTGRES_PASSWORD`, and publishes
TCP 5432 only on IPv4 loopback `127.0.0.1`. It uses SCRAM host authentication,
UTF-8/C.UTF-8 initialization and UTC server/log time. The image-created user is a
local database superuser for migration/testing, not a production application-role
design. The clearly fake root `.env.example` value is local-only. Keep real
credentials out of tracked files and chat; do not print interpolated Compose
configuration because it includes the supplied password.

Compose project `clip-local` owns volume key `clip_local_postgres_data` (default
engine name `clip-local_clip_local_postgres_data`). PostgreSQL 18 requires the
mount at `/var/lib/postgresql`, with `PGDATA=/var/lib/postgresql/18/docker`.
Stopping the service retains data; changing the environment password does not
rotate an already initialized cluster's password. Do not delete a volume to
resolve authentication trouble without reviewing its contents/target and the
reset warning. The fixed port must fail if occupied, never kill another process
or silently pick a different target. Use one active local project per Docker
engine until the wrapper explicitly supports isolated additional projects.

No SQL initialization mount bypasses dbmate. The healthcheck is readiness only,
not successful password authentication, migration completion or cloud evidence.
There is no automatic restart, provider, deployment or cloud database. The local
connection is not a production TLS configuration.

CI must use the same PostgreSQL **18.6** version; PD-12/integration owns that
configuration and must confirm it before acceptance. No CI file is edited here.
Step 5 supplies the target-validating lifecycle commands below. Docker and
Compose are absent on Mohit's verified macOS environment: image pull, Compose
runtime validation, initialization, authenticated readiness and volume
persistence are **not yet verified**. Real migration checks retain Step 6.

## Local lifecycle commands (PD-08 Step 5)

Run from the repository root on macOS/Linux with **Bash 3.2+**, Docker Engine
and the **Compose v2** plugin. A local Unix-socket context is mandatory; Docker
Desktop's local context is compatible by design, but runtime verification is
pending. No Python/Node/dbmate installation is required on the host. Docker may
download the pinned PostgreSQL/dbmate images from their public registries; this
does not provision cloud infrastructure. Install/activate the container engine
using the contributor's approved environment procedure before runtime checks.

Set/export `CLIP_LOCAL_POSTGRES_PASSWORD` through the local process environment.
The root `.env.example` supplies only a clearly fake local-development example;
the wrapper never sources it or any `.env` file. Local passwords must use ASCII
letters, digits, `_`, `.`, `~`, `-` (URL-unreserved characters), with no whitespace
or URL delimiters. This is a local wrapper input limit, not a production password
policy. Do not use a shared/provider/production credential. Do not enable shell
tracing around credential setup. Child container environments contain the local
password and are visible to administrators of the local Docker engine.

| Exact invocation | Effect and expected result |
|---|---|
| `bash database/local-db.sh start` | Validate local context/configuration/resource ownership, create/start only PostgreSQL, then wait for authenticated TCP `SELECT 1`. Exit 0 means connectivity, not migrations. |
| `bash database/local-db.sh wait` | Up to 30 authenticated connection attempts with a 2-second connection timeout and 2-second pauses; nonzero on timeout/absent container. Final sanitized connection diagnostic is retained. |
| `bash database/local-db.sh migrate` | Wait for connectivity, then run pinned dbmate 2.36.0 `migrate` with strict ordering and no schema dump. Applies pending migrations only to `clip_local`. Nonzero aborts; inspect sanitized output before recovery. |
| `bash database/local-db.sh status` | Wait for connectivity and show dbmate migration status. A successful listing can still contain pending migrations; compare to expected head `20261018094332`, not merely process exit status. |
| `bash database/local-db.sh stop` | Stop only the validated service container, retaining its container and named data volume. An absent container is a successful no-op. |
| `bash database/local-db.sh reset --confirm-delete-local-data` | **Permanently delete all local database data.** Warn, validate labels/clone/image/port/mount, stop/remove only the service container, then remove only `clip-local_clip_local_postgres_data`, without force. Leaves the database stopped. Explicitly review/approve this destructive invocation before using it; then run `start` and `migrate` to recreate. |
| `bash database/local-db.sh --help` | Show fixed usage without password/Docker setup. |
| `bash database/tests/local-db-safety.sh` | Exercise command wiring/refusal/redaction against a simulated Docker CLI; no real database, registry or engine is used. |

The wrapper accepts no target arguments. Nonempty `DATABASE_URL`, `PGHOST`,
`PGPORT`, `PGDATABASE`, `PGUSER`, `PGSERVICE`, `PGSERVICEFILE`, `DOCKER_HOST`,
`DOCKER_CONTEXT`, `DOCKER_TLS_VERIFY`, `DOCKER_CERT_PATH` and
`COMPOSE_REMOVE_ORPHANS` are rejected. Unset
these for the invocation rather than repurposing a remote setup. Other PG/dbmate
variables are not forwarded into the fresh tool container. Compose uses an
explicit project/directory/file and `/dev/null` env-file. It never invokes a
broad `down --volumes`, prune, forced removal or database-create/drop command.

Before existing resources are touched, `validate_volume` checks exact Compose
volume labels; `find_container` checks one service container, clone working
directory, PostgreSQL image, loopback binding and sole named volume mount. The
dbmate child shares that validated container's network namespace and connects
to `127.0.0.1:5432/clip_local`; only the migrations directory is bind-mounted,
read-only. `docker_local` pins the inspected context, preserves exit codes and
redacts the local password from displayed diagnostics. `wait_ready` separately
checks password authentication; `run_dbmate` constructs the fixed local URL.
No caller URL or host-network connection is accepted.

All actions use an atomic per-user lock directory
`${TMPDIR:-/tmp}/clip-local-database-<uid>.lock`. One operator must run lifecycle
actions serially using a consistent TMPDIR. An existing lock fails closed; never
delete it until the previous operator/process has stopped and the directory is
confirmed stale. The wrapper removes only its own acquired empty lock on exit.
Do not bypass it with direct dbmate/Compose invocations during another run.

Failures retain nonzero status and sanitized diagnostics. Missing Docker/Compose
or an inactive engine needs environment setup, not a different database target.
On a port conflict inspect the owning process without killing unrelated work.
On ownership/mount/image mismatch stop and inspect; do not relabel resources to
force acceptance. On migration failure inspect status and the original cause;
do not rewrite applied migrations or automatically reset data. Reset requires
separate deliberate approval and cannot recover data after volume deletion.

Source/refusal tests pass, including system Bash 3.2. Real Docker/Compose/container
execution, image inspection, stop/start persistence and reset/recreate remain
**pending Step 6**. Native apply/head/smoke checks passed below; multi-connection
concurrency remains pending. These
scripts create no accepted readiness milestone. PD-13 owns later root Makefile
integration and must preserve the same target/refusal behavior.

## Important SQL behavior

- `identity.guard_user_history`, `guard_local_credential` and `guard_enrollment`
  protect original lifetime/credential class and minimal enrollment records.
  Cross-key normalized enrollment lookup still needs ID-01/A/D review: the
  per-key unique index alone cannot establish non-renewal after key rotation.
  Credential verification, password hashing, OTP/session limits and atomic
  reset/session revocation are future Identity service behavior.
- `listings.guard_image` serializes image mutations with an actual parent-row
  version write. `check_publication` runs deferred so listing/image insertion or
  retirement is atomic while a committed live listing always has 1–8 images.
  `guard_upload` protects owner/key/deadline and attached-confirmation state.
  These cannot prove a cloud object exists or that its bytes were validated.
- `listings.guard_origin` preserves owner/retired identity, anchors continuous
  inactivity, and checks retirement age/conversation activity. It performs
  integrity-only FK reads, not a public cross-domain service. Application
  transactions must follow the reviewed origin-before-thread locking contract;
  runtime consumers cannot use another domain's private tables directly.
- `conversations.guard_thread`, `guard_member`, `guard_entry`, `register_unread`
  and `check_thread` bind two participants, allocate monotonically ordered entry
  sequences, preserve operation keys, coalesce unread episodes and reject
  nonexistent/decreasing read watermarks. API authentication and actual displayed
  acknowledgements remain CN-01 work. Whole-transaction/savepoint rollback is
  required on duplicate inserts; blindly using `ON CONFLICT DO NOTHING` after
  sequence allocation is not the duplicate-return contract.
- `guard_key` and `guard_payload` preserve historical public versions and check
  envelope byte limits/protocol/participant ownership. Opaque bytes are **not**
  validated cryptography; a reviewed established protocol is still required.
- `guard_offer`, `guard_offer_revision`, `check_offer` and `check_entry_content`
  bind immutable revisions/subtypes to their buyer and conversation, validate
  current pointers, permit note-less offers, and preserve content-free
  ordering/offer uniqueness markers on history deletion.
- `reject_reference_change` prevents physical origin/thread/offer deletion or
  contact-share PK rebinding; approved maintenance retires content in place
  instead of removing the minimal lifetime uniqueness records.
- `guard_notification` derives immutable event keys and original due/deadline
  from source records, validates reminder targets and refuses expired replay or
  read/already-reminded episode leasing. It does not enqueue automatically,
  dispatch email, fence a worker's provider call or guarantee exactly-once
  delivery. CN-01/CN-03 still implement atomic intent persistence, final read/
  recipient checks, retry scheduling and external-effect handling.

All trigger exceptions contain fixed messages, not user input/ciphertext.
Applications must still redact native driver/database diagnostic details.
Database ownership is not client authorization. UUID columns are native UUIDs;
application creation uses the approved UUIDv4 helper, while catalogue migration
IDs use PostgreSQL's built-in UUIDv4 generator. Text checks bound stored character
length/nonblank content; domain APIs still normalize outer Unicode whitespace
consistently before binding.

## Verification state and later checks

Step 3 statically parses every up/down section and PL/pgSQL body using a pinned
temporary pglast 7.10 installation outside the project. That checks syntax,
not PostgreSQL object resolution, migration application or transaction races.
It adds no project dependency or production parser requirement.

`tests/schema-smoke.sql` is a rollback-only synthetic test, with a database-name
guard requiring the `clip_test_` prefix. It exercises zero/required/fractional
prices, last-image protection, optional budgets, saved uniqueness, membership,
key-owner binding, operation replay/order, read bounds, zero offers and purged
history uniqueness. Fake public/envelope bytes prove storage shape only, never
crypto interoperability. This smoke passed twice against native PostgreSQL 18.6
in Step 6. The Step 5 Compose wrapper still has only simulated-Docker checks.

Native Step 6 passed clean apply/head, repeat migrate, smoke, down/up in an
isolated empty test database and runtime schema inventory repeatability. It must
still add/run multi-connection concurrency cases for final-image deletion/count,
origin closure/creation, sequence allocation, offer revision/retention and
read/reminder/cleanup races. No concurrency or full acceptance is claimed yet.

### Native macOS checkpoint — 2026-10-18

Mohit selected native macOS checks now and explicitly deferred the other checks.
This is a bounded Step 6 checkpoint, not replacement of Compose/CI acceptance.
No VM or system service was created. The native tools live only under
`/tmp/clip-pd08-native.pKC5jz`; no Homebrew/global installation was changed.

`tests/native-checks.sh` accepts a PostgreSQL installation prefix and dbmate
binary path, verifies exact versions **18.6 / 2.36.0**, then creates its own
private `/tmp/clip-pd08-native-check.*` cluster and `clip_test_native` database.
It accepts no existing data directory or database target. Child processes have
a clean environment. TCP listening is disabled; local trust is bounded by an
owner-only Unix-socket directory, with all host authentication rejected. It
always attempts to stop only that cluster on exit and retains logs/data for
review. It never resets the Compose volume.

Exact invocation for this session:

```bash
bash database/tests/native-checks.sh /tmp/clip-pd08-native.pKC5jz/pgsql /tmp/clip-pd08-native.pKC5jz/bin/dbmate
```

`clean_env` isolates runtime settings, `sql` fixes the new test database/socket,
`migrate` applies version-correct command flags, `check_head` verifies the applied
versions/counts, and `inventory` compares ordered runtime columns/defaults,
constraints, indexes, functions and triggers across down/reapply. `cleanup`
stops the owned cluster and fails the run if shutdown fails. The generated
`schema.sql` stays in temporary evidence; it is not a hand-maintained source.

Passed: three migrations to head `20261018094332`, status Applied 3/Pending 0,
no-op repeat migrate, 23 tables/20 functions/32 triggers, eight categories/four
conditions, synthetic smoke twice, all three down migrations, clean reapply,
identical runtime inventories and clean shutdown. Final evidence:
`/tmp/clip-pd08-native-check.0buobO`; both inventory SHA-256 values are
`886207fdd1ac8d7cf7791c234807ccf864dc786bedff03315dd9cb90959d496e`.

Native build uses UTF-8 with `C` locale and `--without-icu --without-readline
--without-zlib`; Compose uses Debian/C.UTF-8. These checks do not establish
locale/platform equivalence, image compatibility, SCRAM/TCP readiness, container
lifecycle/persistence/reset, concurrency safety, query-plan performance or CI
success. Those checks retain their original Step 6/integration gates. Tools and
evidence under `/tmp` are temporary and may be removed by the OS; rerun with
verified tools if they disappear.

The first sandboxed initdb was denied shared memory. Approved retry outside the
sandbox succeeded. Native execution also caught an introspection query using
the removed `lc_collate` setting and a wrapper error placing `--strict` globally.
Both were corrected: collation comes from `pg_database`, and dbmate 2.36.0 uses
`migrate --strict` while `status`/`rollback` omit it. The Compose wrapper and its
22 simulated safety cases were corrected/retested; real Compose execution is
still pending. These failed-run logs remain in the work-log evidence paths.
