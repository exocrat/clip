# Search domain boundary and pending implementation

Owner: C — Mohit. SE-01 implements sale browse/search through the reviewed
Listings-owned query/store boundary. This directory's generated `public.py`
remains declaration-only; the SE-02 wanted author/read implementation is described
below. Saved Listing APIs and remaining lifecycle/UI behavior remain SE-02 work. See the [task list](../../../../../docs/tasks/domain-task-list.md)
and [reviewed Search contract](../../../../../contracts/search.md).

Shared technical primitives belong in `app.core`. The selected MVP has no Search
listing projection and no private cross-domain table reads. Search uses public
Listings operations; it owns its own wanted/saved rows. Saved retrieval must use
current `read_saved_listing_summaries` for IDs from the same caller's save page,
not the available-only discovery operation or stale cached listing content.
An unavailable non-retired summary can remain visible; retired content cannot.
New saves use the separate current `read_save_target` check.

SE-01 Step 6's test double and contract tests cover explicit unavailable/future/
ended snapshots, content-free retired markers, denied/unavailable dependencies,
expiry and bounded batches. They neither implement saved behavior nor prove
cross-user privacy, real provider or database integration; these checks remain
pending under SE-02 and the original SE-01 real-integration checkpoints.

## SE-02 Step2 storage reused

The baseline MVP migration already creates the wanted/saved tables, budget and
live/retired constraints, foreign keys and indexes. `closed_at` is the request
retirement anchor; the API-only retirement migration adds the paired pending
operation/cutoff. No duplicate table or migration is introduced in Step2.
`database/tests/search-storage-smoke.sql` verifies these invariants using
rollback-only controlled fixtures; both database runners register it.
Application request commands/retries, save APIs, privacy checks, real integration
and destructive cleanup approval remain subsequent work.

The [subsequent category correction](../../../../../docs/decisions/wanted-category-code-reference.md)
supersedes Step2's no-new-migration conclusion for category assignment: wanted
rows now reference the public `category_code`, preserving all other schema rules.
A populated rollback/reapply check verifies content and lifecycle metadata.

## SE-02 Step3 wanted API/retry checkpoint

`wanted_models.py` validates trimmed text, omitted/null/zero budgets, exact money
and revisions, and bounded pages; amounts must fit the existing bigint storage.
`wanted.py` authorizes current regular/temporary callers via public Identity and
uses active/historical Listings category operations. `wanted_store.py` queries
only Search-owned rows, filters before stable pagination, and atomically saves
writes plus their original retry result. `wanted_routes.py` mounts six reviewed
operations with shared safe errors and private/no-store responses. Normal main
composition shares the existing10-connection pool; it adds no credentials, worker
or synthetic caller. Real public dependencies remain declaration-only and fail
closed503; native tests explicitly inject reviewed eligibility/catalogue doubles.

Create retry scope is author/operation; edits/state add request and command kind.
Identical normalized intent returns its original response while retained; changed
intent conflicts. Empty edit/same-state commands preserve revision; actual changes
advance it. Stale revisions conflict. Missing/nonowned writes return404; retired
or retirement-pending owner writes and receipt replays conflict. Open detail uses
public fields; own unavailable detail uses the owner view; retired content is404.

Migration `20261025013000_wanted_command_results.sql` stores private retry payloads
and content-free keys. Guards reject author/key/outcome changes, retained content
on retired origins, and retirement before receipt scrubbing. Migration rollback
refuses populated command storage. The approved scrubber is explicit and unscheduled.
The [concrete local cleanup order](../../../../../docs/architecture/wanted-request-retirement.md)
is now human-approved and implemented by `wanted_retirement.py` plus store
begin/clear/finalize methods. Pending is committed before bounded public calls;
only a confirmed marker permits atomic receipt-first/origin-second scrubbing.
Unknown outcomes preserve the pair; blocked results clear only that pair. There
is no scheduler, route, normal-startup invocation or shared/live cleanup. Local
Step3 checks pass; actual provider/race integration remains pending.
UI/real integration remain later steps; draft matching and saved behavior are described below.

## SE-02 Step4 transient draft-title matching

`draft_matches.py` consumes only public eligibility and Listings available-query
contracts. `DraftTitle` in `wanted_models.py` trims before the required 1–120
code-point bound. `wanted_routes.py` exposes the already reviewed
`POST /wanted-requests/draft-matches` operation independently of Search storage.
It forwards the title as the only text input, using the approved Keyword path,
`created_desc`, page1/size20, and no category/budget/price/condition filters.
The response contains bounded public summaries and `has_more`, with no rank or
recommendation guarantee. Empty results are valid; query failure is safe 503,
never fabricated empty success. It creates no draft/search history/request.

Normal defaults remain the real public declarations (fail closed until real
providers are integrated). Native tests explicitly bridge the actual Listings
browse service/store and native SQL over owned image-backed fixtures, using only
synthetic Identity. They prove tied-ID newest order,20-result bound/has_more,
text/description matching, availability/window/pending exclusions and unchanged
Search storage. Submission succeeds independently after a match outage.
Current UI behavior and actual upstream acceptance remain Steps7–8.

## SE-02 Step5 private saved listings

`saved_store.py` stores only caller/listing UUID pairs and server save times in
the existing table. Every query/write is actor-scoped. Save and unsave serialize
on the same pair; duplicate saves preserve the first time, absent unsaves succeed,
and stable pages order save time then listing UUID descending. No listing fields
are copied or joined. Main shares the existing transactional pool, adding no pool
or credentials. `saved_routes.py` mounts the three reviewed private operations
with shared safe errors and private/no-store behavior.

`saved.py` checks current regular/temporary eligibility, then returns an existing
pair acknowledgement or asks public Listings to confirm a new target. The allowed
availability change after that check does not invalidate the reference. Save
operation UUID syntax is validated; pair uniqueness defines idempotence. Saved
page IDs come only from this caller's already-filtered page (max100), and public
Listings resolves their current state. Response order follows saves even if the
provider reorders states. Unavailable details remain visible; retired entries
contain only ID/save time/retired flag and a null listing. Missing, duplicate,
foreign or inconsistent provider states fail the whole page with 503; no stale content
or fake empty fallback. Unsave needs no Listings lookup.

Normal public Identity/save-target/saved-summary defaults remain declaration-only
and fail closed where required. Isolated tests use real Search SQL/HTTP and
reviewed explicit Listings scripts; real upstream availability/retirement
integration remains Step8. No UI or migration is added in Step5.

## SE-02 Step6 response correction

`wanted_response.py` owns current regular-only response capability and delegates
only through C's public create-or-existing/existing-only operations. Source
`wanted_routes.py` adds the reviewed endpoint, validates the retry UUID and returns
201/200 with thread ID/created; both cases use private/no-store/error policy.
`wanted_store.response_guard` resolves minimal author/state facts with FOR NO KEY
UPDATE while the bounded call runs. That blocks owner writes and permits the
separate C thread transaction's FK key-share check. No local thread/receipt or
new migration is created. Temporary/self/hidden/retired/pending cases fail safely;
closed requests cannot create, and ambiguous results use the same responder pair.

Search's response200 declaration now includes the documented result. Generated
Python/JSON/TypeScript were regenerated, and a compile-only consumer checks both
201/200. Normal providers are still real public declarations and fail503 where
unavailable; explicit C scripts are tests, not a browser success fallback.
Native tests prove actual Search locking and a separate FK metadata fixture,
not real C membership/uniqueness. [Decision](../../../../../docs/decisions/wanted-response-contract-correction.md).
Step6 isolated checks now pass; human result verification and actual provider
acceptance remain pending.
