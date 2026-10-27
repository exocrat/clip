# Coordinated database migrations

**Current Conversations integration checkout:** 21 published migrations plus two
forward corrections, head `20261027112205`, 40 domain tables, 36 functions and 46 triggers.
All 21 previously published SQL files are unchanged. Older isolated
Identity/Listings sections below retain their historical checkpoints; their
former PR10 deferral/counts do not describe this combined checkout. See the
[merge evidence](../docs/evaluation/identity/integration.md#main-reconciliation).

CN-02 Step2 reuses the existing offer/revision/contact tables and installed local
guards; it adds no migration. The registered Conversations checker includes
`apps/api/tests/test_conversation_offer_storage.py` for revision/withdrawal,
ownership/origin, integer-paise, rollback, encrypted-note key binding and retained
identity checks after90-day cleanup. The18 new cases passed inside the132-case
fresh PostgreSQL18.6 suite. These are synthetic direct-SQL storage checks; the
offer service/HTTP/idempotency integration remains CN-02 Step3. See the
[checkpoint](../docs/evaluation/domain/conversations-offers.md#step2-storage-verification--2026-10-27-063124-utc).

PD-08 Step 3 created SQL migrations from the
[schema](../docs/architecture/mvp-database-schema.md) under the approved
sequencing exception. The carried PD-08 gates are user-confirmed complete; the
exact other-machine platform runs are described in the handoff and matrix below.

**Phase handoff, 2026-10-18:** Mohit shifted unfinished PD-08 checks/reviews to
pre-domain integration. The [handoff decision](../docs/decisions/database-integration-handoff.md)
maps the original obligations and roles. The user later confirmed the carried
PD-08 acceptance gates complete. On 2026-10-20, the user specifically confirmed
that the previously deferred Linux AMD64 and macOS checks passed on other
machine(s). The exact architecture, commands, and raw outputs are not retained
in this repository; this is a user-confirmed status, not a locally reproducible
run record. PD-19/PRE-00 retain their separate review and merge gates. No
installation, cleanup, or cloud action is authorized by this status update.
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
| `20261018094330_mvp_tables.sql` | Four owned namespaces, 23 initial application tables, FK/scalar/live-versus-retired constraints, query indexes and the deferred current-offer FK. |
| `20261018094331_mvp_integrity.sql` | Cross-row guards, deferred publication/member/entry/offer consistency, immutable origin/key/operation identities, sequence allocation, unread-episode and source-derived notification invariants. |
| `20261018094332_initial_catalogue.sql` | The approved eight categories/four conditions only; no users, fake credentials, private data or final evaluation dataset. |
| `20261018152702_reject_retired_origin_entries.sql` | Forward correction: reject new entries on permanently retired origins under the existing origin lock, before allocating sequence/activity state. Down restores the original guard. |
| `20261020102224_listing_owner_command_results.sql` | Add Listings-owned saved request/results for availability and selection retries; delete them atomically when a listing retires. |
| `20261020111741_listing_create_command_results.sql` | Save the original create request/result for retry; on retirement clear both payloads but preserve the owner/operation/listing key so a later retry cannot create another listing. |
| `20261020113531_listing_selection_and_confirmed_image_metadata.sql` | Add the missing nullable selected-conversation reference and buyer/conversation pair constraint, plus nullable fields for image metadata verified during LI-02 upload confirmation. |
| `20261020142319_api_owned_retirement_and_trigger_boundaries.sql` | Add paired owner-side pending-operation/cutoff fields and thread write-disable markers; replace cross-domain trigger checks with API-owned checks while retaining local thread, sequence, offer and origin protections. The marker is checked under the thread lock for entries, offer revisions and contact-share inserts; rollback refuses while retirement records or markers exist. |
| `20261021105546_optional_listing_pickup_area.sql` | Allow a null pickup area on live listings while preserving other live/retired requirements. Down refuses while live rows without an area exist; never invents data. |
| `20261022050000_listing_image_upload_intents.sql` | Persist owner-scoped upload operation keys and declared metadata so image-upload intents can be retried safely before confirmation. |
| `20261022062357_listing_image_cleanup_retries.sql` | Add bounded cleanup retry timestamps and indexes for retired images and abandoned uploads. |
| `20261023173439_identity_account_profile_integrity.sql` | Identity-only forward guards: contract profile/contact length bounds, paired chronological revocation event and immutable provider/account mapping. Down removes only its own checks/trigger/function, preserving data. |
| `20261023192856_identity_otp_transactions.sql` | Protected OTP metadata plus key commitments, minimal operation acknowledgements, send reservations and shared verification windows. Empty-state down preserves legacy rows; occupied down fails closed. |
| `20261023202807_identity_sessions_and_login.sql` | Nullable legacy-safe last-seen session time, bounded password failure windows/source events and server Microsoft attempt digests. Occupied down refuses security-state loss. |
| `20261024153316_listing_embedding_generations.sql` | Accepted Listings semantic pipeline/generation/vector storage and invalidation guards; no automatic backfill or worker activation. |
| `20261025012200_wanted_category_code_reference.sql` | Accepted Search wanted category UUID-to-immutable-code FK migration, preserving request content/lifecycle. |
| `20261025013000_wanted_command_results.sql` | Accepted Search private idempotency receipts and guards for wanted commands. |
| `20261026090000_conversation_retirement_hardening.sql` | Preserve immutable thread markers and local offer/contact guards using the published write-disable column. No second retirement schema or cross-domain business queries. |
| `20261026090100_conversation_message_transport.sql` | Ciphertext transport, immutable routing, protocol metadata and ordered read-state protections. |
| `20261026090200_conversation_public_key_directory.sql` | Owned public key-directory and prekey metadata; no private keys. |
| `20261026090300_conversation_recovery_storage.sql` | Typed encrypted protocol-control storage; client content recovery remains disabled. |
| `20261027064000_conversation_offer_requests.sql` | Original expected-revision metadata on retained offer revisions for exact retries, including null after history purge. Legacy rows remain readable without claiming exact replay. Down refuses while recorded request metadata exists; approved history cleanup removes it with revisions. |
| `20261027112205_contact_share_initial_prekey_envelopes.sql` | Permit OpenE2EE's encrypted first-send `prekey_bundle` for contact shares, while still rejecting recovery/control envelopes; down restores the previous entry-kind guard. |

Four superseded branch-only SQL files are preserved byte-for-byte in
[`archived/cn-01-pre-main`](archived/cn-01-pre-main/README.md), outside the executable
chain. A target containing any archived version requires a separately reviewed
upgrade plan; do not apply this fresh-chain procedure to it. Aditya's pinned
17-file Identity manifest remains unchanged and intentionally rejects this larger
chain until a new candidate is reviewed. No shared apply is authorized here.

The optional-pickup forward migration is under Listings writer scope; affected
consumer/schema review and exact shared-database apply remain pending. Local
isolated checks do not authorize shared/Compose/cloud migration.

Expected combined migration version: **20261027112205**. One integrator allocates
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
| `bash database/local-db.sh status` | Wait for connectivity and show dbmate migration status. A successful listing can still contain pending migrations; compare to expected branch head `20261022062357`, not merely process exit status. |
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
read-only. The dbmate container uses the contributor UID/GID so private checkouts
remain readable with all capabilities dropped; it never needs broader file permissions. `docker_local` pins the inspected context, preserves exit codes and
redacts the local password from displayed diagnostics. `wait_ready` separately
checks password authentication; `run_dbmate` constructs the fixed local URL.
No caller URL or host-network connection is accepted.

All actions use an atomic per-user lock directory
`${TMPDIR:-/tmp}/clip-local-database-<uid>.lock`. One operator must run lifecycle
actions serially using a consistent TMPDIR. An existing lock fails closed; never
delete it until the previous operator/process has stopped and the directory is
confirmed stale. The wrapper removes only its own acquired empty lock on exit.
Do not bypass it with direct dbmate/Compose invocations during another run.

Internal `docker_query`/`docker_value` calls preserve raw machine-readable stdout for resource checks. Stderr is streamed separately through `redacted_stderr`, without writing raw diagnostic files; failed stdout is redacted as diagnostic output too. `docker_local` sanitizes human-facing successful stdout. Thus passwords overlapping a volume name, container ID, port or image tag cannot change the validated resource identity. `release_lock` removes only its acquired empty lock. Readiness captures sanitized diagnostics until the final failure report.

Failures retain nonzero status and sanitized diagnostics. Missing Docker/Compose
or an inactive engine needs environment setup, not a different database target.
On a port conflict inspect the owning process without killing unrelated work.
On ownership/mount/image mismatch stop and inspect; do not relabel resources to
force acceptance. On migration failure inspect status and the original cause;
do not rewrite applied migrations or automatically reset data. Reset requires
separate deliberate approval and cannot recover data after volume deletion.

At the Step 5 implementation checkpoint, real Docker/Compose/container
execution, image inspection, stop/start persistence and reset/recreate were
pending Step 6. The user later confirmed the carried PD-08 acceptance gates
complete; exact cross-platform execution details are not retained here. These
scripts create no marketplace readiness milestone. PD-13 owns the root Makefile
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
  inactivity, and enforces the local 180-day retirement age. Listings obtains
  conversation activity and selected-buyer membership through Conversations'
  public operations; the trigger no longer reads Identity or Conversations.
- `conversations.guard_thread`, `guard_member`, `guard_entry`, `register_unread`
  and `check_thread` preserve local thread identity, membership, ordered entry
  sequences, operation keys, unread episodes and read-watermark invariants.
  `guard_entry`, `guard_offer_revision` and the contact-share insert guard lock
  the thread and reject its no-write marker. Entry insertion then advances the
  sequence and activity time from the server clock. The retirement API checks
  origin state/activity and sets markers through public calls; ordinary
  unavailability or request closure still permits discussion. API authentication and actual displayed
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

Migration `20261020142319` removes cross-domain business-table reads/writes from
the origin, thread, entry and offer-revision triggers while retaining local
integrity protections and structural foreign keys. Each origin owner's pending
operation ID is paired with its server-derived cutoff so unknown outcomes can
be retried with the exact request. Public reads/commands hide pending Listings;
the seller's management list keeps retained rows visible. The thread write
marker and content-free result ledger support the owning public APIs; no
database trigger calls a Python `public.py` function. The selected-conversation
backfill migration also fails closed instead of querying Conversations to
infer Listings-owned state.

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

### PR #5 corrective verification

`tests/retired-origin-smoke.sql` is a second rollback-only administrator test
restricted to an isolated `clip_test_` database. It proves ordinary listing
unavailability/request closure still allow messages and contact shares, then
sets the Conversations-owned no-write marker and checks both origin types
reject those same entries without advancing thread sequence/activity. To model
a historical closure, it briefly uses session-local replica mode only while
backdating that fixture's closure instant; origin mode is restored before
retirement and the marker guard are tested. The test does not exercise the
public API's activity check or concurrent ordering; those remain service
integration checks. It is not an application bypass or a production script.
`native-checks.sh` now expects nine migrations and runs both smoke suites before
and after rollback/reapply. The original native results below describe the
initial three-migration checkpoint, not a run of the revised harness.

The lifecycle safety suite now has **35 simulated cases**, including passwords
that overlap metadata, nonfatal diagnostic stderr, and secret-bearing stdout
on success/failure. These additions fail against the original wrapper. The SQL
regression likewise fails against the original entry guard and passes with the
forward correction. The full four-migration SQL round-trip and runtime inventory
comparison were checked separately on an isolated PostgreSQL 18.6 ARM64 image;
exact results are recorded in the work log. At this 2026-10-18 checkpoint, real
Compose persistence, authenticated lifecycle/reset, broader concurrency/query
plans and revised native macOS/dbmate/CI checks remained integration obligations.
The later user-confirmed status is recorded in the platform matrix below; missing
other-machine logs are not reconstructed.

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

### Integration Compose checkpoint — 2026-10-18

Real Linux/ARM64 Docker execution verified PostgreSQL **18.6** and dbmate
**2.36.0**, UTF-8/C.UTF-8, UTC, five SCRAM host rules and no host-trust rules.
The existing local wrapper passed startup/authenticated TCP readiness, all four
migrations to `20261018152702`, status (Applied 4/Pending 0), repeat migrate,
stop/start and final stop. Both rollback-only SQL smoke suites passed in the
separate synthetic `clip_test_integration` database. Its four migration records
and 23 domain tables remained after restart. This supersedes historical
Compose-not-run statements for this Linux/ARM64 checkpoint only. At that
checkpoint macOS/AMD64 compatibility and CI parity were not proved; later
user-confirmed status is described below.

Evidence: `/tmp/clip-pd08-compose-3ej1goas` (temporary local files; the synthetic
password file is private and must not be published). The owned service is
stopped; its container, network and named volume remain. No reset, volume
removal, down migration or cloud operation was performed in this checkpoint.
At that time, reset/recreate, concurrency/query plans, affected-owner
acceptance and CI/common-command integration remained pending; the user later
confirmed the carried PD-08 gates complete.

### Required platform verification matrix

Each row must run the same lifecycle, authenticated connectivity, migration,
smoke, persistence, reset/recreate and wrapper-refusal checks. An image manifest
or emulated run does not establish native host compatibility. Record runtime,
architecture and evidence for each actual run; PD-12 owns CI wiring.

| Host | Container platform | State / evidence |
|---|---|---|
| Linux ARM64 | `linux/arm64` | Local storage checkpoint passed: lifecycle/reset, seven concurrency cases and five index diagnostics; exact evidence is recorded below. |
| Linux AMD64 | `linux/amd64` | User-confirmed pass on another machine (2026-10-20 Asia/Kolkata); exact host, commands, and outputs are not retained here. |
| macOS (architecture not specified) | `linux/arm64` or `linux/amd64` | User-confirmed macOS check passed on another machine (2026-10-20 Asia/Kolkata); the report does not identify Apple Silicon versus Intel or retain commands/outputs. |

This table combines recorded local evidence with the user's confirmation; only
the Linux ARM64 result has its detailed run evidence in this repository. A
reusable verification harness is planned work, not an implemented command.
Do not cite the unavailable run details as independently inspected platform
evidence.

### Approved reset/recreate checkpoint — 2026-10-18

With explicit contributor approval, the local wrapper deleted only
`clip-local_clip_local_postgres_data` and its validated service container.
The volume was confirmed absent before recreation; the old synthetic test
database was absent afterward. Fresh startup/authentication, four migrations
(Applied 4/Pending 0), repeat migrate and both SQL smoke suites in
`clip_test_reset` passed. Inventory: four migration records, 23 domain tables.
The service was stopped; the recreated synthetic volume remains. Evidence:
`/tmp/clip-pd08-compose-3ej1goas/reset-*.log`.

This closes reset/recreate for the Linux ARM64 row only. Concurrency/query
plans, other platform rows, affected-owner acceptance and CI/common-command
integration remain pending. No cloud or unrelated resource was changed.

### Storage concurrency and index diagnostics

With the local synthetic password exported, run from the repository root:

```bash
uv run --locked python database/tests/concurrency-checks.py
```

The standard-library harness validates/starts the existing local Compose target,
creates a fresh `clip_test_races_*` database, applies pinned migrations, and uses
independent psql sessions. It observes actual lock contention before releasing
the first transaction. Statement/lock/idle-transaction timeouts bound server
work. It checks final-image protection under READ COMMITTED and REPEATABLE READ,
the eight-image ceiling, unique Sale Listing and Wanted Request conversation
pairs, sequence allocation, and competing offer revisions with aborted-sequence
rollback. Expected SQLSTATEs and final stored state must both match.

Natural JSON plans are retained for owner feeds, images, entry pagination,
full-text search and due notifications. A separate diagnostic disables sequential
scans to verify index eligibility on tiny fixtures; it is not production plan,
scale, latency or NFR evidence. Representative domain workload/plans remain with
owning domain tasks.

Exit 0 means these checks passed; any other exit needs investigation. Evidence
and the new synthetic database name are printed. Evidence is temporary; test
databases are retained. The validated local service is stopped on exit; no
volume reset/drop or cloud action occurs. Existing local data is not removed.
Run only with no other operator using the local lifecycle; CI wiring is PD-12.

Approved scope: database integrity only. Application transaction/locking
contracts for closure/create, offer retention and read/reminder/lease/replay or
cleanup races remain DL-00/domain-owner review and real integration obligations;
these tests do not establish those workflows or cryptographic correctness.

Latest Linux ARM64 run: seven concurrency cases and five index diagnostics
passed; evidence `/tmp/clip-pd08-races-j6takuzv`, retained database
`clip_test_races_36a74120a8aa`. The first run expected the wrong offer-revision
SQLSTATE; PostgreSQL correctly returned unique violation `23505`. The assertion
was corrected and final state/aborted-sequence rollback checked on the rerun.

## Disposable CI migration gate — PD-12

`uv run --locked python scripts/check_database.py` uses the same PostgreSQL
18.6 image and dbmate 2.36.0 as local development, with a new `clip_test_ci`
database, no published port and temporary memory-backed storage. The current
checker requires clean apply/exact combined head (`20261027112205`), repeated
application, seven SQL smoke suites, the40-table inventory, preserved Identity
upgrades/rollback and full rollback of all23 migrations with a clean reapply, then removes only its own container. The
`--listings-store` option additionally mounts one private temporary Unix-socket
directory and runs the focused Listings adapter workflow against that same
disposable database. It uses synthetic test rows and Identity/Conversations test
doubles; it does not call object storage or touch the shared Compose database.
The checker prints a compact SQL-selected sample listing row before removing
the disposable container.
Historical checkpoint: earlier head `20261020111741` passed locally at
2026-10-20 11:22:17 UTC. Head `20261020113531` passed the disposable check,
including seven rollbacks and clean reapply. At that historical checkpoint, the API-owned retirement migration
was the expected head. Its disposable check passed clean apply, exact head,
repeat apply, both smoke suites, refusal to roll back while a synthetic
retirement result exists, full empty-state rollback, and clean reapply. The
shared Compose database remains untouched. This is local evidence, not hosted
CI. The macOS native schema-inventory run, other platform rows and affected-owner
acceptance remain pending. See the [command registry](../docs/environment/commands.md).

## ID-01 Step3 isolated Identity schema

Aditya is the current writer for migration20261023173439 and its Identity storage
checks on task/id-01-identity. This branch contains the four foundation migrations
plus this forward correction. PR10's seven additional accepted migrations are
explicitly deferred by Aditya; a higher branch version is not proof those ran.
Before ID-READY review/merge, incorporate current main and verify the entire
ordered chain and affected-domain checks. Do not apply this isolated chain to a
retained/shared environment ahead of that integration: strict dbmate would reject
later introducing earlier timestamped migrations. No persistent database was
migrated by this step.

Run `uv run --locked python scripts/check_database.py`. Its fresh network-isolated
PostgreSQL18.6/dbmate2.36.0 test checks clean/repeat apply, three rollback-only
smokes and unchanged23 domain tables. It then rolls back only the new guards,
seeds synthetic regular/temporary/provider/contact rows at the old head, verifies
a failed incompatible-data upgrade leaves no version/partial constraints/data
rewrite, and exercises successful upgrade/down/reapply with fixture preservation.
The runner accepts no database target and removes only its own disposable container.
The seeded rows exist only in that new tmpfs database; they are not user data.

Existing Identity UUID/provider-tuple/expiry indexes remain; no duplicate index,
new table, raw credential storage or authentication behavior is introduced.
The migration validates existing rows and fails atomically if they violate the
new limits/revocation pairing; it does not truncate data or infer timestamps.
The native macOS harness is wired to the fifth migration,21 functions/33 triggers
and new smoke. Bash syntax is checked here; execution of this revised native
harness is not claimed on this Linux ARM64 machine. Historical macOS evidence
above remains evidence only for its original revision.

## ID-01 Step5 isolated OTP transactions

Migration20261023192856 adds four Identity-owned tables (27 domain tables total)
and nullable protected fields to the existing OTP table. Legacy rows remain
unchanged and cannot be verified by the new service. Minimal operation markers
contain a keyed request digest, key version, public challenge ID and expiry;
they contain no target/IP digest, email, code or verifier. Aditya approved
service-lifetime marker retention; the canonical private-data retention decision
records the exception. The migration implements no cleanup job; other private
state retains its separate windows and cleanup-design gate.

`otp_send_reservations` stores protected target/source identifiers for send
limits, including suppressed requests. `otp_verification_windows` holds three
failed verifications per target/purpose through the latest code's expiry.
`otp_key_binding` stores only SHA-256 commitments to three high-entropy keys;
the service rejects accidental key/version changes or unreviewed legacy-state
adoption. Keys themselves are never stored here.

Down takes exclusive locks and refuses occupied security state instead of
silently deleting deduplication/attempt/key guards. A deployed rollback with
state needs a reviewed migration/reset plan. Empty OTP down/up and legacy-row
preservation are exercised by `scripts/check_database.py`, which pins Step3's
older round trip separately so that adding this migration cannot invalidate its
original proof. Four SQL smoke suites now run. The native harness source expects
six migrations,27 tables,21 functions/33 triggers; only Bash syntax is checked
on this contributor's Linux ARM64 environment. PR10/current-main integration
and affected-owner review remain pending before ID-READY/shared application.

## ID-01 Step7 sessions, sign-in and cleanup state

Forward migration20261023202807 adds `last_seen_at` to sessions without inventing
legacy activity; unbound legacy sessions cannot silently authenticate. Three
Identity tables add password target windows (five failures), protected auth
source events and ten-minute single-use Microsoft attempts.30 domain tables and
seven migrations on this isolated branch. Down locks and refuses occupied state.
Existing Step3/5 round trips remain pinned to their historical heads; the
checker now tests five SQL smokes and session empty down/up. Native source
expects seven migrations/30 tables with unchanged21 functions/33 triggers; only
Bash syntax is checked here, no new native macOS evidence.

Identity cleanup operates only on OTP/session/credential and obsolete rate/
attempt state under the approved decision, preserving enrollment/operation/key
markers. CLI defaults to dry-run and requires actual database name matching its
explicit --expected-database; DSN is environment-only and errors/counts exclude
credentials and identifiers. Apply is bounded, per-item transactional and safe
to rerun after partial failure; it is not a blanket cascade or scheduled job.
No retained/shared database apply or cleanup occurred. PR10/current-main ordered
migration reconciliation and affected-owner review remain mandatory before
shared deployment/readiness. A higher branch head does not prove earlier main
migrations were installed.

## SE-01 semantic storage migration — prepared, unapplied

[Migration 20261024153316](migrations/20261024153316_listing_embedding_generations.sql)
implements the [reviewed storage plan](../docs/architecture/semantic-listing-storage.md):
three private Listings-owned tables, source hashing, vector validation/exact cosine,
registry limits, atomic source/retirement invalidation and deferred complete-vector
publication guards. Registry starts empty; no automatic backfill or worker.
Existing migrations/base tables/GIN are preserved. Down refuses populated derived
storage and removes only new empty objects under locks. Mohit approved preparing
the exact derived-content deletion mechanism; no database apply/cleanup run occurred.

Expected source inventory: 12 migrations, 29 domain tables, 30 functions and 40
triggers. Native wrapper counts/rollback loop were updated from stale values;
these are expected values, not a native-run result. The registered container
checker includes `embedding-smoke.sql` in both clean cycles and
`test_embedding_postgres.py` with `--listings-store`. The test file has real
integrity/rollback/race assertions and portable pre-connect refusals; native tests
skip when the disposable runner URL is absent. No alternate external DB target or
ambient PG settings are accepted. PostgreSQL/Docker remains absent here, so this
migration's broader production checks remain pending. The subsequent native
checkpoint below provides scoped disposable SQL evidence.

## SE-01 native macOS checkpoint C — passed, isolated scope

`tests/native-checks.sh` now supports `--listings-store`. It first runs the existing
fresh `clip_test_native` schema round trip, then creates a second new `clip_test_ci`
database/clip_ci role inside the same owned cluster and runs the actual Listings,
browse/vocabulary and embedding adapter files through another private Unix socket.
The embedding test target gate permits the fixed native port 55438 as well as
the disposable container's 5432; it still refuses other names/paths/ambient PG
settings before connecting. No existing data directory/DB URL is accepted.

Tools are under `.tools/native-db/` (about 300 MiB), rebuilt from checksum-verified
PostgreSQL 18.6 source with the historical no-ICU/readline/zlib flags and the
checksum-verified dbmate 2.36.0 ARM64 release binary. No global/Homebrew service,
Docker installation, system/Python edit or cloud access.

Final run `/tmp/clip-pd08-native-check.oLISmK` passed: 12 migrations to
`20261024153316`, repeated apply, three smokes twice, all 12 downs and reapply;
29 tables/30 functions/40 triggers; identical inventories; seven adapter checks (four native database cases and three pre-connect
guards). The cluster stopped successfully and logs/data remain.
[Retained result](../docs/evaluation/domain/se-01/native-postgres/result.json)
and raw migration/adapter/stop logs identify the exact uncommitted source.
Failed runs `Wqe42G` and `6HqtAw` are retained for fixture/diagnostic corrections.
No production schema, Identity/Conversations integration, full data/image check,
Linux/TLS/locale equivalence, model fusion or FR/NFR/readiness acceptance follows.

## SE-02 Step2 wanted/saved storage verification

The existing MVP migration already supplies `search.wanted_requests` and
`search.saved_listings`, their content/budget/state constraints, restrictive
foreign keys and access indexes. The API-owned retirement migration supplies
paired pending fields; `closed_at` is the request's continuous-unavailability
anchor. Step2 reuses these migrations without another schema version.

`tests/search-storage-smoke.sql` tests null/zero budget, field/FK rejection,
closure preservation and reset, immutable authors, paired pending state, duplicate
save timestamps, reference survival after unavailability, restrictive save FKs
and indexes. Every fixture rolls back; the target must be named `clip_test_*`.
Both native and Docker runners invoke this fourth smoke before and after their
full migration down/reapply. Existing retirement smoke covers retired-content
constraints. This proves storage only, not API privacy/auth or real providers.

Native Step2 checks passed at `/tmp/clip-pd08-native-check.UQB7Op`, with all12
migrations, four smokes twice, identical schema inventory and successful stop;
optional adapter suite11passed/3skipped. [Evidence](../docs/evaluation/domain/se-02/storage/result.json).
Docker/hosted acceptance remains pending. Request command/idempotency persistence
is developed with Step3; no command, cleanup or UI behavior is activated here.

## SE-02 category-reference correction

Migration13, `20261025012200_wanted_category_code_reference.sql`, corrects the
previous storage-only audit: wanted categories now reference Listings' unique
immutable code, matching the reviewed public catalogue interface. The migration
converts existing assignments without firing request-update triggers, preserves
NULL retired references, FK protection, the live/retired check and category index,
and reverses populated data back to UUIDs on rollback. Sale categories are unchanged.

The native runner now rolls back all13 revisions. The optional adapter check
includes `test_category_migration_postgres.py`, whose rollback-only fixtures prove
open/unavailable/pending/retired data, revisions, timestamps and inactive category
assignments survive down/up. Conversion functions leave no runtime objects.
[Decision](../docs/decisions/wanted-category-code-reference.md);
[evidence](../docs/evaluation/domain/se-02/category-reference/result.json).
No existing/shared database or deployment was migrated.

## SE-02 Step3 wanted command retry storage

Head `20261025013000` adds private wanted-command receipts (14migrations,
30tables/32functions/42triggers). Author/request-scoped keys and normalized intent
protect retries; immutable original responses are committed with request writes.
Local triggers prevent other-author receipts, rewritten key/outcome data, retired
receipt content and origin retirement with remaining payloads. They delete nothing.
Rollback refuses populated receipt storage rather than discarding retry identity.
Concrete request cleanup is [approved separately](../docs/architecture/wanted-request-retirement.md)
and now implemented as explicit internal transactions; it is not scheduled.

`test_wanted_postgres.py` uses real HTTP/service/SQL/locking in the owned native
database, with explicit upstream eligibility/catalogue doubles. Committed synthetic
origins remain in the stopped disposable database because immutable reference
guards correctly prohibit physical deletion. Do not disable guards for teardown.
[Evidence](../docs/evaluation/domain/se-02/wanted-api/result.json). Docker and real
upstream/retirement integration remain pending. No shared/live migration was run.

### SE-02 Step3 approved local retirement checks

No new migration is needed. The native/Docker optional adapter suite now includes
`test_wanted_retirement_postgres.py`: exact180day eligibility/reset/pair fences,
unknown marker replay, recent-activity preservation, content-free retained keys,
retired visibility, forced SQL failure after receipt clearing (full rollback)
and competing attempts with blocked owner edits. Conversations is a reviewed
explicit test double. One server-selected origin is processed per internal call;
there is no external target selector, cleanup HTTP route or automatic job.
[Retained evidence](../docs/evaluation/domain/se-02/wanted-retirement/result.json).

### SE-02 Step4 real draft-query verification

The optional adapter suite includes `test_draft_matches_postgres.py`. It runs real
Listings availability/native query/order/pagination behind the public signature,
checks Search table counts before/after draft matching and outages, then verifies
wanted submission remains independent. Fixtures include21 tied-time available
items plus unavailable/future/ended/pending/retired cases. Only this fixture's
retired test image/upload metadata is removed after the check (no storage object
was created); immutable parent/user references stay in the owned disposable DB.
This avoids contaminating unrelated cleanup tests without weakening their checks.
No migration, new database resource or private-table read in Search application
code is added. [Evidence](../docs/evaluation/domain/se-02/draft-matches/result.json).

### SE-02 Step5 saved pair persistence

No migration is required: `search.saved_listings` already has the unique pair,
restrictive foreign keys and own-list recency index. Search's new saved store
uses only that table, with actor scope and pair advisory-lock serialization for
save/unsave. It stores no listing title/description/image state.

`test_saved_postgres.py` runs real Search SQL/HTTP with explicit public Listings
fixture scripts. Controlled source changes and real parent retirement validate
reference retention; returned summary states are scripts, not an implemented
upstream resolver. Native tests prove duplicate timestamps, private multi-user
rows, tied pagination/own-page-only batch IDs, unavailable/retired views, outage
behavior and the allowed change-after-target-check race. Only its retired fixture
image/upload metadata is removed; no real object existed and parent refs remain.

Both wrappers run the large committed saved-pagination fixture **last**, after the
earlier mathematical bootstrap test's intentionally small corpus/batch budget.
Keep that guard and bound intact. [Evidence](../docs/evaluation/domain/se-02/saved-listings/result.json).
Real providers, Docker/hosted and final acceptance remain pending.

### SE-02 Step6 response origin lock

No migration is required. `test_wanted_response_postgres.py` verifies response
capability/privacy and exact pair retry through real Search HTTP/SQL. Its real
row-lock race observes owner closure waiting and then completing after response;
closure-first can only look up existing state. The observer refreshes activity
snapshots before each poll. An independent schema-only C thread/member fixture
commits under the origin guard, proving FOR NO KEY UPDATE allows its parent FK
check. C public-service behavior still uses a reviewed explicit double. Retain
immutable metadata and close only owned public wanted fixtures after testing.
[Evidence](../docs/evaluation/domain/se-02/wanted-response/result.json).
