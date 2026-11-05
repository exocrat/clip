# Coordinated database migrations

**Current planning branch:** 21 previously published migrations, two prior
forward corrections, NEXT-03 catalogue/search/amount migrations and CN-03's
encrypted Identity destination, delivery-state and preference migrations: 32
migrations, head `20261029182500`, 41 domain tables, 36 functions and 46 triggers. All 22
previously published SQL files are unchanged. Older isolated
Identity/Listings sections below retain selected historical context; old PR10
deferral/counts do not describe this combined checkout. See the [current work-log
status](../docs/status/work-log.md); detailed old receipts are recoverable through
the [evaluation history guide](../docs/evaluation/README.md).

CN-02's offer, revision, and contact behavior is tracked as complete in the work
log. The linked [historical storage checkpoint](../docs/evaluation/domain/conversations-offers.md#step2-storage-verification--2026-10-27-063124-utc)
records its original direct-SQL evidence; that evidence is not a fresh integration
run or a live-database assertion.

PD-08 Step 3 created SQL migrations from the historical
[schema design map](../docs/architecture/mvp-database-schema.md) under the approved
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

Backup/restore procedures and their operational limits are in
[backup-and-restore.md](backup-and-restore.md). That document is planning and
procedure guidance; it does not authorize or perform a cloud operation.

`dbmate.version` pins dbmate **2.36.0**, a standalone SQL migration tool. The
selected image is `ghcr.io/amacneil/dbmate:2.36.0`. Local setup and checks are
recorded below; the migration-tool choice is explained in the
[tool rationale](../docs/decisions/database-migration-tool.md).

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
| `20261028090000_marketplace_category_catalogue.sql` | Rename the Electronics and Home appliances labels and add Sports & fitness, retaining stable existing codes and assignments. |
| `20261028100100_marketplace_title_case_labels.sql` | Update only category and condition display labels to title case, including Like New; rollback restores the preceding labels. |
| `20261028100200_wanted_discovery_text_search.sql` | Add a partial GIN index for English-normalized title/description keyword search over open, visible Wanted Requests. |
| `20261028120000_sale_original_price_and_marketplace_amount_cap.sql` | Add optional seller-stated Original price and enforce the ₹1 crore cap on listing prices and Wanted budgets. |
| `20261028181500_private_buyer_selection.sql` | Decouple private seller buyer-tracking from availability, including tracking on unavailable non-retired records. |
| `20261029043000_unique_handles_and_participant_projection.sql` | Stage required case-insensitive unique Handle claims without rewriting legacy names; expose the safe Identity participant view. |
| `20261029133500_identity_notification_destinations.sql` | Identity-owned encrypted login destinations; no plaintext addresses in notification intents. |
| `20261029134500_notification_delivery_state.sql` | Bounded retry timing, dispatch reservation and fenced outcome replay state. |
| `20261029182500_identity_notification_preference.sql` | Default-on account preference and fenced preference suppression outcome. |

Four superseded branch-only SQL files are preserved byte-for-byte in
[`archived/cn-01-pre-main`](archived/cn-01-pre-main/README.md), outside the executable
chain. A target containing any archived version needs its own reviewed upgrade
procedure; this fresh-chain procedure does not cover it. Old Identity package
sizes and review statements below are historical records, not current release
requirements. Local checks do not authorize shared, Compose, or cloud migration.

Expected planning-branch migration version: **20261029182500**. One integrator allocates
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

CI and local procedures use PostgreSQL **18.6**. The lifecycle commands below
validate only the explicitly owned local container. Prior runtime checks are
historical; the work-log status is authoritative for task completion.

## Local lifecycle commands (PD-08 Step 5)

Run from the repository root on macOS/Linux with **Bash 3.2+**, Docker Engine
and the **Compose v2** plugin. A local Unix-socket context is mandatory; Docker
Desktop's local context is compatible by design. No Python/Node/dbmate
installation is required on the host. Docker may
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
| `bash database/local-db.sh status` | Wait for connectivity and show dbmate migration status. A successful listing can still contain pending migrations; compare to expected branch head `20261029182500`, not merely process exit status. |
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
scripts create no marketplace readiness milestone. The root Makefile integration preserves the same target/refusal behavior.

## Important SQL behavior

- Identity guards protect account lifetime/credential class and minimal
  enrollment records. Cross-key enrollment, password, OTP, session, and reset
  behavior are implemented at the Identity service boundary; task status and
  acceptance evidence are in the work log. These SQL guards alone do not implement
  the full authentication flow.
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
  instead of removing the minimal lifetime uniqueness records. Conversations
  authentication and notification acknowledgements are tracked as complete in
  the work log; historical database notes below describe only schema behavior.
- `guard_notification` derives immutable event keys and original due/deadline
  from source records, validates reminder targets and refuses expired replay or
  read/already-reminded episode leasing. It does not enqueue automatically,
  dispatch email, fence a worker's provider call or guarantee exactly-once
  delivery. CN-01/CN-03 implement atomic intent persistence, final read/recipient
  checks, retry scheduling and external-effect handling at the application layer;
  task status is recorded in the work log.

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

## Current verification commands

`uv run --locked python scripts/check_database.py` is the disposable migration
gate used by the repository checks. It creates a fresh `clip_test_ci` database
with the pinned PostgreSQL/dbmate tools and removes only its own container.
Never point it at a retained or shared database.

### Storage concurrency and index diagnostics

Run the isolated local concurrency harness from the repository root:

```bash
uv run --locked python database/tests/concurrency-checks.py
```

It creates a fresh `clip_test_races_*` database and uses independent PostgreSQL
sessions with bounded timeouts. It covers database integrity races and checks
whether key indexes can be used on small fixtures. It does not establish real
service workflows, production query plans, scale, latency or NFR results. It
retains its test database and does not reset local data. Do not run while another
operator is using the local database lifecycle.

This guide contains the current database commands. The [domain task list](../docs/tasks/domain-task-list.md)
defines acceptance; the [command index](../docs/environment/commands.md) links
common commands and owner guides. The [work log](../docs/status/work-log.md) has
current status; detailed prior platform/run receipts are recoverable through the
[evaluation history guide](../docs/evaluation/README.md).

The `20261029043000_unique_handles_and_participant_projection.sql` migration adds staged Handle claims and an Identity-owned `participant_profiles` view. Existing names and account IDs are preserved; valid unambiguous names are claimed, while invalid/colliding names require setup. The view exposes only user ID, claimed Handle and active account class. An integrated Conversations runtime needs `USAGE ON SCHEMA identity` and `SELECT ON identity.participant_profiles`; it needs no direct access to Identity contacts or provider tables. Historical Identity-only migration packages are not the complete integrated marketplace migration set.
