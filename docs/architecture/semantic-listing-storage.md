# Listings-owned semantic storage and write plan

**Origin:** SE-01 hybrid amendment checkpoint 4, following the
[isolated Mac probe](semantic-search-feasibility.md).
**Status:** Mohit approved all presented plan and derived-content deletion
implementation gates. Additive migration/inactive store and tests are prepared;
the prepared increment was verified and the subsequent native checkpoint ran
only on fresh private test databases. No existing/shared DB, backfill or worker
was started/touched; live activation remains pending. Independent exact-code/schema review and real native
checks remain required; no peer approval of newly written code is inferred.

## Audit and current source anchors

The reviewed hybrid design needs durable storage, complete generation markers,
atomic invalidation and retirement fencing. The probe alone supplies none of
these. Its weak long-description similarity also leaves chunk aggregation and
threshold calibration open; no storage choice remedies that quality gap.

Current integration anchors:

- `PostgresListingsStore.create_listing`: one transaction inserts a listing,
  attaches uploads and records the operation-id retry receipt; a replay must
  not enqueue duplicate embedding work.
- `replace_listing`: locks the listing/revision and replaces fields/images in
  one transaction. Only title/description changes require new vectors; price,
  availability, image, condition and category changes affect live filtering,
  not the embedding source.
- `begin_listing_retirement`: locks the listing and persists operation/cutoff
  before Conversations. Pending retirement is already excluded from discovery.
- `finalize_listing_retirement`: locks and verifies that same pair, retires
  images and scrubs sale content in one transaction. Vectors must be removed
  inside that transaction, without changing Conversations/S3 cleanup semantics.
- `browse_store.py`: native vector/filter predicates precede stable order and
  pagination; its expansion opt-in remains native-test-only.

These sources are in the Listings-owned API directory. Search continues to use
public query contracts; no private Search projection or cross-domain trigger is
proposed. All planned triggers touch only Listings-owned state.

## Proposed migration inventory

Keep the initial feasibility store in PostgreSQL **native `real[]`**, exact scoring,
no extension/service. Preserve the existing generated `search_vector` and GIN.
This selects an implementation candidate, not measured production acceptance.
Create an additive dbmate migration only after this plan is verified, affected
owners review it, and a fresh non-colliding UTC identifier/head is reserved.
Current local head is `20261022062357`; it is not proof of current remote head.
Use the established UTC/10-second-lock-timeout/advisory migration lock conventions.
Implementation reserves `20261024153316` after checking main's migration names
and open PRs. The [additive migration](../../database/migrations/20261024153316_listing_embedding_generations.sql)
is now prepared and verified only on fresh private test databases. Existing
migrations and existing/shared/production databases are unchanged.

| Proposed object | Keys/content | Constraints and indexes |
|---|---|---|
| `listings.embedding_pipelines` | SHA-256 pipeline ID; exact model/export/tokenizer/pooling/chunk versions; dimension/window/overlap; `planned`, `building`, `serving`, `retired` state | Pipeline ID 32 bytes; no mutable encoding under an existing ID; at most one serving pipeline, at most two building/serving pipelines during transition |
| `listings.embedding_generations` | `(listing_id, pipeline_id)` PK; fresh UUIDv4 generation ID; 32-byte source fingerprint; `pending`, `leased`, `ready`, `failed`; lease token/deadline; attempts/retry time; bounded fixed failure code; expected title/description part counts; UTC timestamps | Listing FK restricts hard deletion; pipeline FK restricts deletion; unique generation ID; state/lease/count consistency; due-work index `(retry_after, listing_id, pipeline_id)` for pending/expired lease candidates |
| `listings.embedding_chunks` | Generation FK; `title` or `description`; zero-based ordinal; `real[ ]` vector | PK `(generation_id, part_kind, ordinal)`; child rows cascade only when their derived generation is deleted; one-dimensional, lower bound 1, cardinality 384, no null/nonfinite components, norm tolerance <=1e-3; title ordinal 0 only; description ordinals 0–95 |
| `listings.embedding_source_fingerprint(title, description)` | Strict deterministic function returning 32-byte SHA-256 | Version-tag + 64-bit network-byte-order UTF-8 byte lengths + exact UTF-8 text bytes; no `pgcrypto`, raw text cache or locale-dependent JSON serialization |
| Own-schema invalidation/retirement trigger | After insert or actual title/description/retired-state change | Queues/invalidate registered building/serving generations in the originating listing transaction; no inference, network, Conversations reads, owner IDs in derived payloads or background side effects |
| Deferred generation completeness guards | Own-schema constraint triggers on generation/chunk changes | At commit, a ready generation must have its exact expected contiguous parts; pending/leased/failed generations cannot retain published chunks |
| Vector validation/exact score helpers | Controlled finite 384-real vector validation and double-precision dot/norm calculation | Explicit array ordinality for deterministic component accumulation; reject dimension/nonfinite/zero-norm input, never accept silent NULL scores |

`real[]` declarations alone do not enforce dimensions. Implement explicit checks,
including NaN/infinities, not merely numeric range comparisons. Every null-sensitive
CHECK must explicitly reject nulls instead of relying on SQL's unknown result.
Compute cosine as the ordered double-precision dot product divided by both
vector norms; approximate unit validation alone is not exact cosine. Retain
separate title/description scores until the reviewed fusion policy exists.
Use fixed error codes; do not store exception messages, input text or tensor dumps.
Pipeline configuration contains digests/encoding parameters only, not user content.
Vectors are derived content and receive the same internal privacy/retirement
protection as listing text; they are never public response fields or log payloads.

The migration leaves the registry empty. The explicit store registration method
creates the candidate pipeline as `planned`; it is not called by app startup.
Migration/registration do not silently start inference or backfill. A later explicit bounded bootstrap changes it to building,
enqueues existing non-retired rows idempotently and reconciles concurrently
created/edited rows. Publication/readiness checks below are mandatory even during
bootstrap; a registry-state race cannot be interpreted as full coverage. New
pipeline activation needs actual registry-transition/write concurrency tests.

## Fingerprint, invalidation and idempotency

Use the actual stored normalized title/description as fingerprint input. The
worker receives the DB-calculated fingerprint and source, not a differently
serialized Python hash. Model/chunk/pooling config is the separate pipeline ID.
A price-only edit/revision increment must not invalidate otherwise current vectors.

On a new source, while the listing write holds its row lock:

1. Delete old derived generation rows for **all** of that listing's pipelines;
   chunk FKs remove their vectors in the same transaction. This is derived-content
   invalidation, not a request to delete listing/image/customer data.
2. Insert new pending generations with fresh IDs and matching current fingerprint,
   empty lease and zero published counts. Repeated identical writes keep an
   existing matching generation; exact create-operation replay changes nothing.
3. Commit together with the existing listing/image/receipt transaction, or roll
   everything back. Trigger failure fails the write; no stale generation may
   survive a successful text edit. Test native loader/direct sale-write paths too.

A later model/pipeline change may retain the old complete generation while building
new-space vectors; a text change invalidates *both* old and new source versions.
Pipelines retired for rollback/history must never leave old-text vectors behind:
text edit/retirement invalidates **all** derived generations for the listing,
including retired pipelines, before rebuilding only building/serving ones.

## Worker claim, publication and crash recovery

Canonical lock order: **listing row → generation row → chunk rows**, sorted listing
and pipeline IDs for multi-row maintenance. Never first lock a generation and then
wait for its listing: that can deadlock with edit/retirement.

- Claim one due candidate by joining jobs to sale rows and using `FOR UPDATE OF
  listing SKIP LOCKED`, then lock/recheck its generation. Exclude retired and
  retirement-pending rows. Set a fresh UUIDv4 lease token and 30-second deadline
  using server UTC time; commit before model work. One active worker per process,
  batch size one, and no inference under DB row locks. Bound total generation
  work (including helper queue time) to 20 seconds, below the 30-second lease;
  abort/retry rather than publish after expiry. No unbounded lease heartbeat.
- Read the source/fingerprint under that claim; send only title/description to the
  bounded local helper. Keep it in memory, not a duplicate text/chunk table or log.
  Worker and interactive helper requests share the approved bounded queue; defer
  worker work when full rather than unbounded retries. Enforce chunk/IPC byte limits.
- Publish in a new transaction, locking the listing first. Require non-retired,
  no pending retirement, unchanged source fingerprint, same generation/pipeline,
  matching unexpired lease token and supported helper/model config. Reject stale
  completion even if the title changed away and back; generation IDs fence that
  ABA case. A price-only revision change does not invalidate matching content.
- Validate every vector/ordinal and all expected chunks before changing `ready`.
  Insert all title/description vectors and the ready marker atomically. Validate
  exactly one title vector and contiguous complete description ordinals, no gaps
  or duplicates. Readers never see partial ready generations.
- On timeout/error, clear only the currently owned lease and retain fixed error
  metadata. Retry delays: 5, 30, 120 seconds, then at most 300 seconds; after five
  consecutive failures mark failed, retaining the fixed reason until explicit
  retry/new source. Empty/missing vectors never become ready. Lease expiry can
  be reclaimed with a new token; late old tokens cannot publish or clear it.
- Crash during compute leaves a reclaimable lease. Crash inside publish rolls
  back vectors and ready state. Cancellation/restart never loses the durable job.
  Content changes reset the generation/failure count; no uncontrolled loop over
  permanently bad data.

All canonical worker writes must follow this lock/check protocol, with native
concurrency tests. Existing repository records do not establish actual deployment
DB-role grants for these new objects; inspect/review them at deployment integration.
Do not claim FK/trigger checks alone secure arbitrary privileged ad-hoc derived
writes, add privileged `SECURITY DEFINER` functions or change cloud roles here.

## Hybrid read and coverage contract

Compute the query vector through the bounded helper, then execute **one native
statement** containing an eligible-row CTE, coverage check, lexical/expanded
matches, exact semantic scores, deduplication, final ordering and page lookahead.
Use the same fixed server UTC instant throughout that statement.

1. Caller authorization precedes query work. The eligible set uses the authoritative
   non-retired/non-pending/current-availability predicates and every supplied
   category/condition/price/negotiability filter, before similarity limits.
2. Left join *all* eligible listings to the one serving pipeline's complete current
   fingerprint/config generation. If any is missing/stale/failed/leased, return
   the shared `503` outcome with no partial page. Do not restrict coverage to
   keyword matches; that would hide the very records semantic retrieval adds.
3. Within the **same statement snapshot**, compute exact scores only for valid
   generations. Never check readiness in one query and fetch in a second snapshot.
   A single-statement CTE is a snapshot-consistency choice, not a claim that a CTE
   alone guarantees optimal execution or an optimization fence.
4. Aggregate chunks per listing (proposed max description similarity plus separate
   title signal). Union lexical and semantic candidates with one row per listing.
   Relevance fusion/thresholds/caps remain a later reviewed development-calibration
   output; the weak long-description probe forbids selecting an arbitrary final
   threshold now. Apply explicit recency/price or reviewed relevance order and
   UUID tie-break before offset/size+1. Do not rerank each page separately.
5. Query vector/helper/model mismatch or capacity/deadline failure returns `503`;
   keyword mode continues independently. Public fields/cache policy remain the
   reviewed summary/private-no-store envelope, with no embeddings/source hashes/
   generation counts or private state exposed.

No exact shared success/error schema or public new mode/sort field is activated
by this proposal. Those changes require registered contract generation in the
later public integration checkpoint. A concurrent commit after the snapshot can
change later requests; do not promise cross-page snapshots or linearizability
beyond the existing offset contract. Native normalization activation is still gated.

## Concrete retirement mechanism and separate gate

Proposed order inside the existing `finalize_listing_retirement` transaction:
lock/verify listing and pending pair → retire existing image references as today →
perform existing text scrub/retired-state update → own-schema AFTER trigger deletes
**all** embedding generations (chunk cascade) and cancels pending/leased work →
commit the existing retired marker. Failure rolls the whole transaction back.
The worker's listing lock, retired/pending checks and generation/lease fences
prevent an in-flight completion from republishing deleted vectors.

Pending retirement hides rows immediately but need not delete retained content
before Conversations confirms retirement. Cancellation preserves eligibility rules;
expired leases are reconciled without exposing pending origins. Final retirement
is irreversible under the current origin contract; repeat finalization finds no
vectors/jobs and stays idempotent. No S3 calls, new retirement eligibility rule,
new cascade into saved references/conversations, or changes to the existing image
cleanup order are proposed. Do not infer physical backup erasure from logical
row deletion; existing backup/retention policy remains applicable.

**Approval recorded:** Mohit explicitly approved all presented plan/deletion
implementation gates after the mechanism was explained. That authorizes preparing
the exact derived-generation/chunk invalidation/final-retirement code and tests.
It does not authorize applying a migration or running cleanup on a database.
Independent review of the exact new code/schema remains separate.

## Migration, backfill and rollback gates

| Increment | Concrete output | Required verification |
|---|---|---|
| A — plan (current) | This object/transaction/deletion/check inventory | Mohit verifies storage/protocol; Suraj reviews affected schema/write paths; explicit cleanup approval before implementing deletion |
| B — prepare migration/store | Reserved dbmate ID; additive objects; inactive worker/store code; schema documentation and tests | Review exact up/down SQL, catalogue/base-guard interaction, all changed code; no apply/backfill implied |
| C — local native checks | Disposable migrated database, integrity/concurrency/restart/query plans, clean up/down/reapply | Real supported PostgreSQL environment; no Docker install assumed, fake vector scores cannot prove SQL |
| D — bounded real preparation | Reviewed fixed synthetic DB target, corpus/pipeline pin, <=1 worker/1,000 rows per run, ten-minute limit, 512 MiB helper/API cap; resume unfinished jobs | Exact target/operator approval; stop on DB lock/deadline, budget/resource or integrity failure; no shared/cloud target inferred |
| E — public integration | Reviewed mode/sort/coverage/error contract, generated artifacts, real helper lifecycle and UI | Native checkpoint 3, complete coverage, Linux/resource/support validation, browser checks; no automatic deployment |

The 1,000-row cap in D is per run; larger required corpora need reviewed resumable
batches, never hidden omissions or a lower product/data requirement. Initial
migration applies metadata only; expensive embedding backfill never runs inside
DDL. Set bounded lock/statement timeouts before real work; record exact values
with the reviewed native/target run manifest.

Rollback first disables hybrid serving/worker dispatch under a reviewed operational
plan, then returns public behavior to the preserved keyword baseline. Leave derived
objects for diagnosis until exact removal is approved. A dbmate down migration
must fail if generations/chunks exist; do not silently drop embeddings/history or
use `CASCADE` into unrelated objects. Remove only empty new objects in reverse
order (invalidation/completeness triggers, chunks, generations, pipelines, then
score/vector-validation/fingerprint helpers), retaining
sale rows, original GIN and all baseline tables. Recheck active writes before
reversing the migration; no rollback command is executed now.

## Required native acceptance matrix

- Clean migration; UTC/type/shape/FK/index/trigger inventory; fresh down/reapply;
  refusal to down a populated derived store; original Listings/image invariants.
- Create retry, identical text, nontext edit, text edit and transaction failure;
  old vectors absent exactly when the new text commit becomes visible.
- Two workers, lease expiry, helper crash, failed publication, retry ceiling,
  edit during compute (including away/back), pending/final retirement during
  compute, cancelled retirement, duplicate/late completion and restart recovery.
- Finite/NaN/infinite/null/zero/wrong-size vectors, malformed dimensions, missing
  title or ending description chunks, noncontiguous/duplicate ordinals and
  ready-marker inconsistency; no silent partial generation.
- No source/plaintext or retired vectors in public responses/logs; no contacts,
  private buyer/owner state or cross-domain table reads.
- Single-snapshot missing/stale coverage yields `503`, all filters before scoring,
  no duplicate/missing fixed-corpus pages at sizes 20/50/100, stable ties, empty set,
  huge-price boundaries and all current availability/retirement transitions.
- Actual native scoring correctness and query plans; full-corpus resource/latency
  measurements on the real deployed path later. Arrays have no vector index;
  no claim this scan meets NFR-02 or production concurrency.
- Bootstrap/pipeline switch with concurrent create/edit; all-source reconciliation
  detects missing jobs; complete-coverage/version checks prevent premature serving.

No check above is passed merely because this document or the Mac model probe exists.

## Technical references

PostgreSQL documents [native SHA-256](https://www.postgresql.org/docs/18/functions-binarystring.html),
[row-lock/SKIP LOCKED behavior](https://www.postgresql.org/docs/18/sql-select.html),
[statement snapshot isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
and [CTE behavior](https://www.postgresql.org/docs/18/queries-with.html). These support
mechanisms, not this repository's unexecuted migration or performance acceptance.

## Implementation checkpoint — prepared, not native-verified

`embedding_types.py` validates the controlled encoding manifest, hashes its
canonical configuration, hides source/vectors from work-receipt repr and rejects
malformed/partial vector outputs. `embedding_pipeline.json` contains the actual
probe model/tokenizer/runtime pins, without model bytes. `embedding_store.py`
registers planned pipelines, serializes registry transitions before row locks,
reconciles bounded missing work, leases, publishes, records bounded retries and
explicitly retries one failed generation with a new identity. It accepts only an
injected connection and has no app/pool/worker/HTTP binding. The 20-second overall
generation/IPC deadline remains a future orchestrator responsibility; no production
helper loop is implemented by this persistence layer.

The migration defines the three tables, six functions and four own-schema triggers.
Completeness guards inspect both old/new generations when a chunk is moved. Down
locks the relevant tables and refuses populated derived storage before dropping
only new objects. Runtime slot/state races are rechecked after obtaining listing/
generation locks. Native fixture definitions exercise old/new source and lease
fences, deferred publication/rollback, retry exhaustion, guarded down and two
server-observed publication races with edit/retirement. These assertions subsequently ran on this Mac's fresh PostgreSQL 18.6 test
cluster; the [native checkpoint evidence](../evaluation/domain/se-01/native-postgres/result.json)
records seven passing adapter-suite checks (four database cases and three pre-connect guards) and the schema round trip. This does not
accept production helper/read integration or the entire future matrix.

The registered database runners now include `embedding-smoke.sql` and the new
native adapter file, with expected branch head `20261024153316`, 12 migrations,
29 domain tables, 30 domain functions and 40 domain triggers. These are expected
inventory values now also checked in the native disposable run. Previous native wrapper
counts/rollback loop were stale even before this migration and are aligned here.
Source-bound preview manifests from earlier steps remain historical; regenerate/
validate against this schema revision at the original real-data checkpoint.

Pipeline JSON shape/pin validation is in `pipeline_spec` before registration/claim;
the SQL table enforces object form/identity immutability, not a general JSON-schema
engine. A malformed or hash-mismatched manually inserted pipeline is refused by
the inactive worker store, not treated as a supported model configuration.

## Native checkpoint C result — 2026-10-24

The optional native harness mode rebuilt exact local tools, passed clean apply/
repeat/three smoke scripts/twelve downs/clean reapply and compared identical
inventories, then migrated a second fresh database and passed seven adapter-suite checks: four real
Listings/browse/embedding database cases and three pre-connect guards. All owned test clusters were stopped;
logs/data remain private under the recorded `/tmp` paths. Native arrays/math,
lease/publication/rollback/retirement fixtures and the server-observed races now
have actual scoped SQL evidence. Public expansion/semantic serving is still off.

First run exposed overly strict full-query GIN selection and invalid retirement
test setup, corrected without production-constraint changes. Second run exposed
shared browse-fixture marker ordering; expansion now runs last with its own price/
negotiability setup. Original full-query planner selection is not a latency failure:
the revised text-only compiled-predicate diagnostic proves GIN eligibility, while
actual browse/filter/sort/page assertions verify the complete query. Two failures
and final success are retained, not overwritten or counted as full passes.

Pipeline-switch/bootstrap mutation coverage, real runtime orchestration/20-second
generation deadline, single-snapshot hybrid read, Linux/production resources and
original human labels/FR/NFR/readiness gates remain pending. The native cluster's
UTF-8/C and no-ICU/TLS build is not the production locale/security configuration.

## Remaining pipeline matrix follow-up — native verified

The [expanded native result](../evaluation/domain/se-01/native-pipeline-switch/result.json)
now covers bootstrap/registry-switch mutation scenarios. The matrix uses explicit
mathematical pipeline spaces/coordinate vectors, never installs its synthetic
runtime version tags and leaves public application behavior inactive. It bounds
the private fixture corpus to <30 retained rows and work to <=60 jobs.

An uncommitted source inserted while a pipeline is planned is missed by an early
reconciliation after another connection enables building. Promotion correctly
refuses incomplete coverage; limit-one resumable reconciliation repairs it, and
repeated reconciliation preserves ready generation IDs. The two-active limit and
one-serving unique constraint reject invalid transitions without losing the old
serving state. The old→new switch is atomic to the other connection.

A source edit held uncommitted during that switch illustrates snapshot semantics:
promotion sees prior complete data, then the source commit invalidates old vectors
and leaves the newly serving pipeline with pending work. Actual source coverage
therefore falls below complete even though its enum says serving. The matrix
verifies old vectors are gone and active-space work restores coverage. **Future
public reads must still implement the one-statement coverage/503 guard**; this
test's coverage query is not an implemented HTTP behavior or a perpetual-readiness
guarantee from promotion. No production schema/store correction was needed.

The test restores prior fixture-pipeline states and retires/removes only its own
mathematical fixtures in the disposable database. Failed import-only run
`Mxq5GE` and successful run `4FB6Mb` are retained, both clusters stopped. A portable
fixture-key isolation check also runs without SQL so skipped native tests cannot
hide that factory/import mistake again. Real worker/IPC/deadlines, public hybrid
reads, full corpus/image reconciliation, Linux/providers/human labels/NFR gates
remain pending.

## Real helper boundary follow-up

The [private helper protocol/client](semantic-helper-protocol.md) now runs the
actual local model with bounded frames, queue/deadlines, one process-wide owner
and failure/restart/reaping behavior. It returns validated complete private parts
and fixed job failure classifications; it does not claim/publish DB generations
or start a worker. The overall claim-to-compute20s orchestration, lease handling
and real fenced-publication bridge remain the next integration obligation.

## Private DB/helper bridge follow-up

The explicitly invoked `embedding_worker.py` now implements the overall20s
claim/queue/compute/publication budget, exact supported-pipeline selection,
idle-autocommit/no-inference-lock guard and fixed failure/capacity/cancellation
handling. `EmbeddingStore` adds per-job local3s statement/1s lock bounds and a
fenced5s capacity deferral that refunds the claim attempt. This extends the
previously prepared store without changing schema or automatically starting work.
See the [bridge contract/evidence](semantic-embedding-worker.md). Disposable
PostgreSQL+actual-model checks are scoped separately from the earlier coordinate
matrix. Public one-statement coverage/read/fusion and deployment dispatch remain
unimplemented; the older sections record their historical checkpoint states.

## Private hybrid-read follow-up

The [single-snapshot private reader](hybrid-listing-read.md) now implements the
selected35/65blend/0.35/tiered/no-cap policy, eligibility-first full coverage,
exact supported serving space, native cosine/lexical/typo union and stable pages.
It checks real chunk completeness and source fingerprints in the result snapshot;
missing data yields existing dependency_unavailable503. The one-statement read,
real helper composition and concurrent commit behavior have separate scoped
native evidence. Earlier planning paragraphs are historical pending-state records.
Public contract/generated/UI/dispatch/deployment and final original gates remain.


## Explicit initial bootstrap tooling

The subsequent [operator bootstrap contract](semantic-pipeline-bootstrap.md)
implements aggregate status, idempotent preparation, bounded existing queue
reconciliation and guarded initial activation. Registry advisory/coverage/source/
chunk guards remain; unavailable live sources are included. No automatic worker
startup, shared backfill, model replacement or serving switch is introduced by
these operations. Native CLI/SQL/model concurrency checks demonstrate a writer
can invalidate an earlier complete activation snapshot; request-time coverage
continues refusing incomplete results until current generation recovery.
