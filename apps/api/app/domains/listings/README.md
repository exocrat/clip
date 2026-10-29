# Listings API implementation

## SE-01 Step 3 collection browse

`browse_routes.py` adds the reviewed `GET /listings` collection operation to
the existing router. `browse.py` checks trusted caller expiry and current
Identity eligibility for regular or temporary accounts, then calls the narrow
owned browse-store operation. Its public Identity adapter requests either
eligible class (`required_class=None`); it does not reuse seller-only checks.
Missing Identity/storage fails closed. Synthetic adapters are bound only by
explicit test applications; normal startup installs no browse-auth bypass.

`PostgresListingsStore.browse_available_listings` delegates to
`browse_store.py` through its existing connection/error mapping. The result SQL
filters retired/pending-retirement, unavailable, future and ended rows before
the selected stable ordering and LIMIT/OFFSET. It
fetches size+1 public summaries to compute `has_next`; image references carry
no image-body transfer. Pages are deterministic for fixed state, not snapshots
across concurrent changes. There is no listing projection or cache.

Step 6 adds `Cache-Control: private, no-store` to successful discovery responses.
Each request rechecks caller eligibility and reads current SQL state; dependency
failures never return a previously successful page. The native fixture test
checks available → unavailable → reopened transitions, the exclusive end
boundary and inclusive start boundary for the same listing through both browse
and text search. The seller's raw flag remains independent of its time window.
These real PostgreSQL checks still need execution on a supported local runtime.

Saved-item retrieval is separate: SE-02 consumes the reviewed public
`read_saved_listing_summaries` operation for caller-owned save-page IDs; it must
not reuse discovery or infer new-save eligibility from a displayed summary.
Non-retired unavailable items retain their approved saved summary; retired
references are content-free. `search_access.py` now supplies all five reviewed
Listings calls to Search: the existing browse query and active catalogue,
historical category labels, current save eligibility and safe saved summaries.
Normal app startup and the isolated browser harness inject this same real
provider. Saved summaries use the discovery-safe SQL projection, retain
unavailable records, and expose no retired content; pending retirement fails
closed. Search keeps its own saved rows and never queries Listings tables.
The disposable database runner covers these connections with synthetic Identity;
real Identity and complete domain acceptance remain pending.

Step 4 adds plain-text `q` matching through
`search_vector @@ plainto_tsquery('pg_catalog.english', q)`. The service trims
text and treats blank as ordinary browse; SQL applies all normalized terms to
the stored combined title/description vector. Stop-word-only/punctuation-only
queries produce no matches. SQL-looking syntax remains a bound plain-text value,
not a tsquery expression. Default ordering remains recency/UUID, with no
relevance-score ordering. No client-side or in-memory matching is used.

The existing `20261018094330_mvp_tables.sql` already defines the stored English
vector and `sale_full_text` GIN index; no duplicate migration/index is added.
Step 5 adds category, condition, inclusive minimum/maximum price and optional
negotiability filters before paging. `false` and zero are preserved. Category and
condition codes are checked against the current active owned catalogue on the
same database connection; unknown/inactive codes return safe 422 even when no
listing would match. The catalogue read is not a snapshot guarantee across
concurrent catalogue edits. Sorts use `created_at DESC, id DESC`, price ascending
then ID ascending, or price descending then ID descending.

`browse_validation.py` layers runtime validators over the generated query
declaration without editing it. HTTP money/page values require exact integers;
floats, bool amounts, reversed ranges and malformed inputs produce shared 422
errors without rejected values. Text is trimmed before the 120-code-point bound;
page sizes remain 20/50/100 and offsets must fit PostgreSQL's signed integer.
Listings-owned inputs use `BrowseQuery` before coercion can discard original
types. Other domains retain generated public query types and validate raw input
at their own boundary; they do not import this private model. Active catalogue
codes come from SQL, not a duplicate list.

No monetary product cap is selected: values above the largest whole-rupee bigint
are evaluated equivalently (impossible minimum gives no rows; excessive maximum
adds no restriction), without binding overflowing integers. No request-rate
quota was selected in the reviewed sources, so no new throttle or 429 behavior
is invented. Existing shared error/rate-limit envelope conventions remain.

`test_browse.py` checks HTTP/auth/privacy with scripted pages, not fake SQL.
`test_browse_postgres.py` tests real SQL visibility/time boundaries, UUID ties,
all supported page sizes and no skips/duplicates inside a force-rollback
fixture transaction. It also tests title/description matching, English stemming,
all-term and plain-text semantics, stop-word/no-result cases, generated-vector
update propagation, search paging, stored vector expression and GIN validity.
Step 5 extends the matrix to every filter/combination, both negotiability values,
zero/inclusive/large price boundaries, all three sorts/ties and current active
catalogue validation. A transaction-local planner diagnostic checks index eligibility with sequential
scans discouraged; it does not prove natural plan choice or performance.
It is registered with
`uv run --locked python scripts/check_database.py --listings-store` and skips
without that runner's local database. Real SQL execution is still pending on
Mohit's current checkout; upstream Identity and affected-owner review also remain
pending. No UI, image/storage behavior, generated declaration or migration changed.

`routes.py` mounts image-upload intent (`POST /image-uploads`), confirmation
(`POST /image-uploads/{upload_id}/confirm`), cancellation
(`DELETE /image-uploads/{upload_id}`), and authorized image delivery
(`GET /images/{image_id}/delivery`), plus create (`POST /listings`), detail read
(`GET /listings/{id}`), owner list (`GET /me/listings`), full replacement
(`PUT /listings/{id}`), availability (`PUT /listings/{id}/availability`),
buyer selection (`PUT /listings/{id}/selection`), offer submission/revision,
and offer withdrawal. Each path matches the reviewed Listings HTTP contract.
`service.py` owns field checks, current-account and seller ownership checks,
owner-bound upload intent/confirmation, image ownership/publication validation,
availability and buyer-selection rules, the serialized offer gate, and safe
response shapes. Before image delivery, it checks that the image remains
attached to a retained listing and applies the same owner/discoverability rule
as listing details. `s3_storage.py` signs create-only PUT requests and short-lived
GET requests against the private bucket, and reads storage metadata through the
server's AWS credentials or task role. Image GET links expire within five
minutes, are marked `private, no-store`, and are returned without exposing the
object key. The bucket is not made public.

Full replacement accepts an ordered list of existing image references to keep
and newly confirmed upload IDs to add. The PostgreSQL adapter checks that kept
references belong to the listing, consumes confirmed uploads under the same
transaction, retires omitted images for cleanup, and stores the selected order.
The live schema prohibits unretiring a removed image, so a later re-add must be
a new confirmed upload. Responsive upload and gallery UI remain Step 9 of LI-02.

The service depends on a `ListingsStore` adapter. The adapter must use the
Listings schema, call Identity through its public eligibility interface, check
confirmed owner-bound image records, and make listing plus image attachment a
single transaction. It must enforce expected revisions for replacement,
availability, and selection. Its offer guard must serialize an offer against
availability changes and any retirement write while keeping Conversations in
its own transaction. It must replay matching operation IDs and reject
conflicting reuse as specified by the contract. It must not query another
domain's private tables.

Selection uses only the public Conversations participant check. Listing offer
commands use only the public Conversations offer-write call. The selection
and offer endpoints cannot return successful results until those adapters are
injected. A retired listing is treated as absent by the store read/offer guard.
Retirement is finalized only after the public Conversations marker confirms it;
Listings then scrubs its content and marks its images retired.

LI-02's image upload intent migration persists the owner-scoped operation ID
and initially declared media metadata. This makes retries return the same
upload intent while rejecting reuse of an operation ID for different metadata.
Older rows are backfilled with their own upload ID as a one-time operation key.
The migration does not alter listing or identity data.

The separate schema inventory still does not define durable replay receipts
for availability and selection operation IDs; that existing adapter detail
remains unresolved and is outside the image-upload migration.

The API startup currently has no configured Listings store, Identity wiring,
or Conversations adapter. Until those are supplied, the mounted routes fail
closed with the shared 503 error (or 401 when there is no trusted caller
context). No in-memory or fake store is selected by default. Cancellation marks
an unattached upload failed but retains its object key for cleanup. Confirmation
checks uploaded file signatures, actual S3 size, and content metadata before
marking the image confirmed. The internal `cleanup_image_objects` operation
processes at most 100 records by default and 500 at most per pass. It handles
retired images and expired unattached uploads, deletes S3 objects before their
database references, and delays failed/unknown deletes by five minutes so
other work can proceed. It is a worker operation, not a public HTTP route; no
cleanup schedule is installed here. Its migration adds per-object retry times
and due-work indexes; expired upload rows are made terminal under a database
lock before S3 deletion, preventing a concurrent confirmation or listing edit
from publishing an object being removed. A test-only adapter may be injected
by owned test fixtures; its results do not prove PostgreSQL, Identity,
Conversations, or LI-02 storage integration.

## Hybrid amendment checkpoint 2 — controlled vocabulary

`search_vocabulary.json` contains versioned common concepts, aliases, one-way
narrower relations, literal-only ambiguous words and expansion budgets.
`vocabulary.py` validates configuration and returns immutable records plus a
content fingerprint. It supplies the explicit compiler test path described below; public requests
retain ordinary matching until native activation gates pass. [Vocabulary rules](../../../../../docs/architecture/search-vocabulary.md)
record phrase/multiword behavior and pending native acceptance cases.
`test_vocabulary.py` checks the actual artifact and malformed configuration.
Human verification/affected-owner review precede runtime integration; no semantic
model, category change, seller tags or human evaluation labels are created.

## Hybrid amendment checkpoint 3 — unactivated lexical compiler

`lexical_expansion.py` performs one bound PostgreSQL normalization lookup, then
`plan_expansion` builds bounded AND/OR query expressions with all text bound as
parameters. The original query remains a lexical OR branch; added multiword
alternatives use phrase queries. Unsupported parser shapes or exceeded budgets
keep the complete original query. Unknown terms are never discarded.
`TextQuery` holds SQL/parameters and content-free outcome/vocabulary fingerprint.

`browse_store.py` accepts compiled text only through the explicit
`read_browse_page(..., expanded_search=True)` native-test opt-in. Production
`PostgresListingsStore` uses the default false; no HTTP/config flag enables this
path. `test_lexical_expansion.py` checks planning over scripted normalization;
`test_browse_postgres.py` adds genuine normalization/matching/filter/paging/edit/
index checks in its existing rollback transaction. Native execution and activation
remain pending. These are vocabulary queries, not embedding/semantic inference.

## Hybrid storage implementation — inactive, native checks pending

`embedding_pipeline.json` records actual candidate model/export/tokenizer/runtime
pins. `embedding_types.py` derives a canonical pipeline ID, represents private
work/parts without plaintext/vector repr, and validates complete unit-vector
outputs. `embedding_store.py` provides only injected-connection persistence:
planned registration, explicit state changes, bounded missing-row reconciliation,
30-second leases, fenced atomic publication, bounded failure backoff and explicit
single-row failed retry with a new generation ID. It imports no inference runtime,
reads no ambient DB target and is not instantiated by production app/routes.
No worker, queue or 20-second generation/IPC supervisor is started here.

[Migration 20261024153316](../../../../../database/migrations/20261024153316_listing_embedding_generations.sql)
adds private pipeline/generation/chunk storage, deterministic source hashes, finite
384-real vector/exact cosine checks, own-schema text/retirement invalidation and
deferred generation completeness. Source edits/final retirement delete all derived
spaces atomically with the Listing write; no base content/images/conversations
are independently deleted. Populated derived storage blocks down migration.

`test_embedding_store.py` tests validation and scripted SQL transport/refusal only.
`test_embedding_postgres.py` prepares actual migrated-state/rollback and two-
connection races plus portable pre-connect target refusals. It restricts execution
to the registered disposable Unix-socket runner and writes synthetic fixtures only;
concurrency fixtures commit so both connections can observe them, then remain
inside the runner-owned temporary container. No real native run is claimed.
See the [storage protocol](../../../../../docs/architecture/semantic-listing-storage.md).

## Native storage/query checkpoint C

The optional native harness mode now executes the same adapter files on a second
fresh private Unix-socket `clip_test_ci` database after the schema round trip.
The seven adapter checks passed (four native DB cases and three pre-connect
guards), including actual expanded title/description matching,
filters/pages, embedding validation/publication/retry/rollback and two-connection
edit/retirement fences. The GIN diagnostic isolates the actual compiled text
predicate rather than demanding the full broad browse query select GIN over a
valid recency plan. Retirement fixtures use an already-ended 199-day window and
restore the existing deferred parent/image publication checks; production checks
were not weakened. The race helper drains its owned publication task on failures.

[Native run receipt in Git history](../../../../../docs/evaluation/README.md)
records source hashes and limits. Actual native success does not activate the
store/expanded public route, run a background worker or replace pending public
hybrid contracts/read integration, full corpus/labels and upstream provider gates.

## Native bootstrap/switch follow-up

`test_embedding_postgres.py` now includes bounded mathematical fixture helpers
and a two-connection bootstrap/switch matrix: interrupted reconciliation,
idempotent resume, incomplete promotion, active/serving limits, atomic switching
and concurrent text invalidation. `test_embedding_store.py` checks those fixture
keys are distinct from the real candidate without SQL or model calls. Native
suite: eight checks (five DB cases/three guards) passed; source/store/migrations
required no behavior change. Public read coverage checks and real helper
orchestration are still future implementation. Its original receipt is recoverable
through the [evaluation history guide](../../../../../docs/evaluation/README.md).

## Private real helper boundary — not startup-bound

`embedding_protocol.py` shares strict bounded JSONL and full token-window coverage
between API3.14 and helper3.13. `embedding_helper.py` verifies actual local hashes/
runtime and serially produces CPU mean-pooled/unit vectors with network/children
blocked. `embedding_client.py` owns one child/controller per process, eight waiting
requests, startup/inference/request/cleanup deadlines and safe crash/cancellation/
reaping/restart. It preserves the supplied venv executable path and forwards no
ambient provider/DB credentials. `embedding_types.py` now shares vector validation
between query and listing output; no ML package enters the root API environment.

`test_embedding_client.py` and the owned fault double cover protocol/lifecycle
failures without pretending to run a model. The separate `ipc_probe.py` ran the
actual model through pipes, including an owned-child crash/restart. See the
[private protocol](../../../../../docs/architecture/semantic-helper-protocol.md)
and the [historical run receipt](../../../../../docs/evaluation/README.md).
No controller is constructed by app/routes and no DB-generation loop or public
503/coverage/read/fusion path is implemented here. Those retain their own gates.

## Private one-job embedding bridge — explicitly invoked only

`embedding_worker.py` accepts the existing store/helper and performs one fenced
claim/encode/publish within20s. A process slot prevents competing worker calls;
unsafe outer transactions are refused. `embedding_store.py` claims only the
helper-supported space when specified, locally bounds job SQL and defers full
helper queues for5s without exhausting model retries. Cancellation propagates;
committed leases remain recoverable. There is no automatic dispatcher or public
binding. [Bridge contract](../../../../../docs/architecture/semantic-embedding-worker.md).

`test_embedding_worker.py` scripts operation outcomes, not SQL/ranking;
`test_embedding_store.py` checks bound transport/defer limits. The new
`test_embedding_worker_postgres.py` uses the guarded disposable database with
fault pipes and, by explicit native runner opt-in, the actual pinned local model.
`native-checks.sh --embedding-worker` additionally verifies real crash/restart,
long-text publication and mutation fencing. The ordinary Docker database runner
includes the portable native fault test; it does not require/download the optional
local model. Its original receipt is recoverable through the [evaluation history guide](../../../../../docs/evaluation/README.md).

## Vocabulary-only typo preparation

`typo_tolerance.py` implements bounded spelling distance and unique closest
concept selection, using the reviewed vocabulary as its only target set.
`lexical_expansion.py` invokes it after exact PostgreSQL phrase recognition,
retaining original terms, one-way expansion, independent AND/added phrase rules
and all existing budgets. Query-scoped work/correction limits require whole-query
fallback. Short/ambiguous/initial-letter cases are conservative; an unknown real
word such as chain can add chair while retaining chain. No general dictionary,
new dependency/extension/model or public field is added.

`test_typo_tolerance.py` supplies pure operation/planner checks, not ranking;
`test_browse_postgres.py` now checks real typo/ambiguity/original/filter/page/index
behavior on its existing guarded native fixtures. [Policy/evidence](../../../../../docs/architecture/search-typo-tolerance.md).
Public stores still leave the expansion/typo opt-in off. Actual hybrid read and
public activation retain separate implementation/verification gates.

## Private hybrid read — no public binding

`hybrid_read.py` binds exact query/model vectors, normalizes text through the
existing compiler and performs one snapshot eligibility/coverage/score/union/
order/page statement. The selected hybrid-blend-v1 rule is35%title/65%max-description,
cutoff0.35 for semantic additions, original>expanded/typo>semantic tiers and no
semantic pre-cap. Existing recency/price orders retain their meanings. Every
eligible source must have complete current vectors in the exact serving space;
otherwise the whole hybrid read raises the common controlled503. Catalogue
errors stay422 and keyword reads remain independent.

`search_hybrid_page` explicitly borrows the real helper/idle connection with20s
work budget; nothing constructs or mounts it at startup. `test_hybrid_read.py`
checks internal contracts/controlled HTTP, and `test_hybrid_read_postgres.py`
checks native math, actual concurrent snapshot behavior and separately opted-in
real helper/worker/read integration. `test_embedding_postgres.py` accepts a fixed
fixture INSERT instant so immutable creation-time sorting ties are valid.
[Contract/evidence](../../../../../docs/architecture/hybrid-listing-read.md).

## Private keyword relevance

`browse_store.py` now accepts private keyword_relevance=True: compile the existing
vocabulary/typo query, preserve original membership, order original matches first,
then native matching-query ts_rank_cd and UUID ascending before pagination. Rank
never enters the summary; old defaults/recency/price SQL remain unchanged. No model
client/configuration/artifact/embedding metadata is consulted. Blank relevance is
422; the compiled original text/vocabulary must bind to this request.

`test_keyword_relevance.py` verifies construction/transport/guards; the extended
`test_browse_postgres.py` native fixture verifies actual tier/rank/proximity,
filters, tied65-row pages and reads with no serving space/failed jobs.
[Contract/evidence](../../../../../docs/architecture/keyword-listing-relevance.md).
No public mode/sort registration or UI activation occurs in this checkpoint.


## Registered search modes and relevance (SE-01 API checkpoint)

The canonical query now adds search_mode (keyword default, hybrid opt-in) and
relevance sort (nonblank text required). `PostgresListingsStore` normalizes before
I/O, enables vocabulary/typo matching for public Keyword, and selects native rank
only for relevance. Blank text in either mode uses ordinary browse. Nonblank
Hybrid requires constructor-only `hybrid_helper` injection and an idle autocommit
pool connection; the adapter reuses `search_hybrid_page`. Missing capability is
safe503, no fallback. Active catalogue validation retains422 when a helper is
missing. No app startup/configuration, worker loop or helper process is added;
normal construction leaves Hybrid unavailable. The caller/service authorization
precedes retrieval. Browse's scoped route wrapper applies private,no-store to
success and common auth/validation/dependency errors through shared sanitizers.
Responses stay unchanged. Mode semantics are in
[the specification](../../../../../contracts/search-mode-proposal.md).


## Normal API read-side helper lifecycle

`search_runtime.py` owns optional real helper and max2autocommit read connections
under explicit Settings; its disabled default creates neither. app.main supplies
these borrowed handles to PostgresListingsStore. Only nonblank Hybrid uses that
pool; Keyword and commands preserve the original pool/transaction behavior.
Expected startup failure closes partial resources and safely disables Hybrid;
cancellation/close errors are handled without leaking or claiming cleanup success.
No pipeline DML, worker loop or backfill occurs here. The normal application still
uses real upstream eligibility, never the preview identity. Configuration,
resource limits, typed guards and pending integration are recorded in
[the lifecycle contract](../../../../../docs/architecture/normal-api-search-runtime.md).


## Optional existing-job dispatcher

`embedding_dispatch.py` adds a separately configured serial background task and
max1worker pool, sharing the normal runtime helper. `search_runtime.py` starts it
only when explicitly enabled and helper-ready; shutdown awaits it before helper/
read-pool cleanup. Default remains off. Ten-job bursts yield1s; idle2s and failure/
capacity5s pauses release the connection first. Existing source/lease/publication/
retry/retirement guards remain in the worker/store. No queue reconciliation,
registration, backfill or serving transition is added. Source-edit/native HTTP
and failure evidence are linked from [the dispatcher contract](../../../../../docs/architecture/semantic-embedding-dispatcher.md).


## Explicit pinned pipeline bootstrap

`embedding_bootstrap.py` supplies read-only aggregate status, resumable preparation,
one bounded queue batch and separate guarded activation over an explicitly owned
idle autocommit connection. It reuses registry/job guards, includes unavailable
live listings in full coverage and never resets current jobs or replaces another
serving space. The separate target-bound scripts/search_pipeline.py operator CLI
requires exact binding and --execute for each mutation; the flag is not approval.
No normal startup or public route calls these operations. [Contract/commands and
real concurrency evidence](../../../../../docs/architecture/semantic-pipeline-bootstrap.md).
