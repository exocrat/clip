# Search contract

**Current disposition (2026-11-05 15:26:56 UTC): Aditya marks SE-01/SE-02 complete, including the Hybrid runtime/lifecycle acceptance. Earlier pending integration notes below are historical and superseded for task status.**

**Status:** Step 10 domain-owner documentation review is reported approved by
the user. Step 11 typed declarations are generated from this contract and the
[combined registry](combined.md). Search implementation and migrations remain
with SE-01/SE-02.

## Ownership and dependency boundary

The [hosted functional repair](../docs/decisions/hosted-functional-repair.md) adds
GET`/me/saved-listings/status` with repeated `listing_ids` (1–100 UUIDs). It
returns deduplicated `{listing_id,saved}` items scoped only to the trusted caller.
It discloses no listing content or other user's references and does not require
resolving the caller's whole Saved collection. Eligibility remains current;
responses are private/no-store. Save/unsave writes and existing pagination remain.

Search owns Wanted Request records and private saved-listing references.
Listings owns sale-listing records, their availability, catalogue, public
summaries, and the authoritative title/description search index. Search does
not read Listings tables or maintain a listing projection. Search clients use
the Listings-owned browse/detail HTTP operations directly; Search's draft-match
and saved-list operations call only Listings' reviewed public query/summary
operations. Search calls Conversations to start or look up a Wanted Request
response thread and to use its public activity and no-write-marker operations
for retirement. Destructive local content/object cleanup needs separate approval; Search's
local request/receipt order is now approved as recorded below. Existing/shared/live
cleanup runs and other domains' cleanup retain their own gates.
Conversations never calls Search or Listings. This preserves the reviewed
acyclic graph.

The chosen listing boundary is the Listings-owned query backed by PostgreSQL
native full-text search, using `pg_catalog.english` for both the stored vector
and query normalization. Listings owns its GIN and supporting indexes; no
Search projection, backfill, synchronization job, or separate search service
is part of the MVP. Search never interprets a cached availability flag as
authoritative.

## Human-selected hybrid-search amendment (pending runtime activation)

Mohit verified the six-checkpoint [hybrid-search amendment](../docs/decisions/hybrid-listing-search.md) on
2026-10-24. It adds curated vocabulary expansion and local semantic retrieval
across item types, retaining PostgreSQL full-text search. The proposed optional
`search_mode` (`keyword` default / `hybrid`) and `relevance` sort are not current
wire inputs. Existing query rules below and generated declarations remain the
runtime baseline until the required reviews/checks, concrete model/storage/
scoring/freshness decisions and registered contract generation. No hybrid
implementation or platform feasibility is claimed. Consult the decision for
ordered checkpoints, filtering/pagination/failure rules and final evaluation gates.
Mohit confirms Suraj approved this amendment; no separate review artifact is
linked. The compiler and native keyword checks subsequently passed; the public API
checkpoint below now enables reviewed vocabulary/typo matching for Keyword.

### Registered public mode/relevance checkpoint

Mohit verified Keyword as the default, reversible Hybrid selection and Relevance
in both modes. Source/generated inputs and API validation/dispatch are now
implemented together. The [mode specification](search-mode-proposal.md) records
the exact semantics. UI controls and helper lifecycle/bootstrap remain separate;
normal startup has no helper, so nonblank Hybrid returns controlled503. This is
isolated implementation, not final upstream/readiness/FR/NFR acceptance.

## Sale-listing browse, search, and detail

The sale view uses Listings-owned `GET /listings` and
`GET /listings/{listing_id}`. It requires an eligible authenticated caller;
anonymous access is not implied by the word “public.” Temporary and regular
callers may browse and search. The detail operation follows the Listings
contract: discovery-eligible records are visible, an owner may read their own
unavailable non-retired record, and retired or otherwise inaccessible content
is not disclosed. Search adds no competing listing route or authorization
rule. Catalogue values come through the Listings public catalogue operation.

`GET /listings` accepts:

| Query field | Meaning and validation |
|---|---|
| `q` | Optional trimmed plain-text query, at most 120 Unicode code points. Omitted or whitespace-only means browse without text matching. Keyword retains original English full-text matches and adds bounded reviewed vocabulary/typo matches. Zero-lexeme Keyword queries return no rows; Hybrid may add semantic matches. Raw tsquery syntax is not accepted. |
| `category_code` | Zero or more active Listings category codes using repeated query values, for example `category_code=appliances&category_code=bicycles`. Values match with OR; omission means all categories. One legacy single value remains valid. Unknown/inactive values return `422 validation_error`. |
| `min_price_paise`, `max_price_paise` | Optional inclusive nonnegative integer paise values, each a multiple of 100. If both are supplied, minimum must not exceed maximum. |
| `condition_code` | Zero or more active condition codes (`new`, `like_new`, `good`, `fair`) using repeated query values. Values match with OR; omission means any condition. One legacy single value remains valid. Unknown/inactive values return `422 validation_error`. |
| `negotiable` | Optional boolean; true and false are distinct filters. |
| `search_mode` | `keyword` (default) or `hybrid`. Blank text browses in either mode without semantic dependencies. Nonblank Hybrid requires explicitly configured capability and complete eligible coverage, otherwise503; no silent fallback. |
| `sort` | `created_desc` (default), `price_asc`, `price_desc`, or `relevance`. Relevance requires nonblank text in either mode; otherwise422. |
| `page`, `page_size` | Shared numbered pagination: page defaults to 1; size defaults to 20 and may be 20, 50, or 100. |

Apply current availability/window, authorization, text and supplied filters
before pagination. Category choices match with OR; condition choices match
with OR; category, condition, text, price, and negotiability filters combine
with AND. Empty category or condition selections add no restriction. Sale results exclude retired listings, seller-unavailable
listings, future listings, and listings whose end instant has arrived. Include
the Listings-owned public listing summary and the shared page envelope
`{items, page, page_size, has_next}`. Order `created_desc` by
`created_at DESC, listing_id DESC`; `price_asc` by
`asking_price_paise ASC, listing_id ASC`; and `price_desc` by
`asking_price_paise DESC, listing_id DESC`. Each order has a unique ID
tie-breaker. Relevance follows the mode-specific ordering in the [mode specification](search-mode-proposal.md), with final UUID ascending ties. Offset pages are deterministic for a fixed result set; concurrent
changes may move rows between page requests, as accepted by the shared page
decision. Empty `q` is treated as absent only after trimming, as explicitly
defined above.

The browser's Sale Discovery UI does not expose `negotiable` as a filter. The
API field remains available for compatibility and possible future callers;
legacy website links containing it are accepted but the value is ignored and
is not sent with the request. Sale cards and detail pages continue to display
the listing's negotiability state. In the browser, `sort=relevance` is labeled
**Best Match**, is the default for nonblank searches, and remains selectable;
empty browsing defaults to newest-first. The public API spelling remains
`relevance` for compatibility.

The detail response and public fields are owned by the Listings contract. They
must not include owner IDs, private contacts, selected-buyer state, upload
state, private operational fields, or storage keys. Search does not expand
that response when composing discovery.

## Wanted Request public discovery and author management

Search stores the immutable public `category_code` with a restrictive FK to
Listings' unique code. New assignment uses the active public catalogue; existing
labels use the historical-display operation. Only schema migration/backfill may
resolve the former category UUID. See the [approved storage correction](../docs/decisions/wanted-category-code-reference.md).
Public wire fields and contract version are unchanged.

Search owns Wanted Request state. A live request has a server UUIDv4, author,
trimmed title (1–120 Unicode code points), trimmed description (1–5,000), an
active Listings category, optional `budget_paise`, status `open` or
`unavailable`, creation/update UTC instants, and a revision. A supplied budget
is a nonnegative integer paise amount in whole rupees; omitted or `null` at
creation means no budget stated, while zero means seeking a free item. On
update, omission leaves budget unchanged and explicit `null` clears it. A
category is validated through Listings' public catalogue boundary, never by
reading its private tables.

The discovery toggle composes open Wanted Requests separately from sale
listings. `GET /wanted-requests` and `GET /wanted-requests/{request_id}` return
only open, non-retired requests to eligible authenticated regular or temporary
callers. This is public within the signed-in marketplace; anonymous access is
not selected. Browse accepts optional `q` text over title and description,
repeated `category_code` values, optional `min_budget_paise` and
`max_budget_paise` bounds, and the shared `page`/`page_size` fields. Search uses
an optional trimmed query of at most 120 Unicode code points; whitespace-only
text means no text filter. English-normalized keyword matching requires all
query terms across the combined title and description. Repeated category codes
are deduplicated and validated against Listings' active public catalogue.
Selected categories match with OR; text, category, and budget filters combine
with AND. Budget bounds are nonnegative whole-rupee paise, inclusive; if either
is set, requests with no stated budget are excluded. The minimum must not
exceed the maximum. Filters are applied before numbered pagination. Requests
remain ordered `created_at DESC, request_id DESC`, paginated with the shared
page envelope and sizes. Browse does not accept sale-listing price, condition,
or negotiability filters. A request's category is a displayed item category,
not a view discriminator.

The owner-reviewed public response contains only `request_id`, `title`,
`description`, category code and
label, nullable `budget_paise`, `created_at`, and `updated_at`. It contains no
author ID, author display name, phone, email, UPI, or other contact value. The
title, description, category and optional budget are the author's intentionally
published request content. A Contact requester action starts a private
request-origin conversation through Conversations for a regular eligible
caller; it never returns contact details. Existing conversation participants
retain access when a request becomes unavailable, per the accepted lifecycle
decision. Unavailable requests do not appear in public browse. At
`GET /wanted-requests/{request_id}`, the eligible owner may read their own
unavailable, non-retired request as `WantedRequestOwnerView`; other callers
receive the safe `404 not_found` response. Retired requests are unreadable to
every caller, including the owner. This owner exception was confirmed by Mohit
on 2026-10-24; see the [discovery decision](../docs/decisions/wanted-request-discovery-and-response.md).

The author-only management operations create a request, list/read only the
author's own requests (including unavailable, non-retired requests), edit it
with an expected revision, and mark it unavailable or reopen it under the same
ID. Omitted fields on edit remain unchanged; nullable budget may be cleared.
Closing prevents new response conversations but does not revoke an existing
conversation. Reopening preserves request/responder uniqueness. A retired
request cannot reopen. Create/edit validate the active category through
Listings; Search owns all Wanted Request writes and closure/reopen state.
Exact close-versus-first-conversation serialization is specified with the
Conversations operation in Step 8/9.

Search also owns its retirement decision and pending-operation state. It must
not read Conversations tables from a trigger. Commit a unique pending
operation ID and its server-derived cutoff on the request before calling
Conversations; keep that exact pair so an unknown result can be retried after a
process restart with the identical request. Keep the request out of new
response-thread, edit/reopen, and discovery paths while the outcome is
unresolved. Use `get_origin_activity` only as a preflight, then call
`mark_origin_retired` for Conversations' authoritative all-or-none locked
check. A recent write returns `blocked_recent_activity`, marks no threads, and
causes Search to clear both pending fields; a later attempt uses a new ID and
cutoff. Reusing an ID for a different origin or cutoff conflicts. The API-only
lock/recheck/marker sequence is approved. It does not approve destructive
clearing of request content or objects; the Search-owned local method/order is now separately approved in the
[retirement decision](../docs/decisions/origin-retirement.md#approved-search-owned-requestreceipt-cleanup--2026-10-25).
Its implementation remains unscheduled and real provider integration pending.

Author lists use `created_at DESC, request_id DESC` with shared page sizes.
Public and owner reads apply authorization and visibility before pagination.
Responses omit all retired content; a retired record does not become a
readable empty request.

## Wanted response implementation checkpoint

`POST /wanted-requests/{request_id}/conversations` is now locally implemented.
Temporary callers cannot initiate or use this response lookup. Current eligible
regular callers use a server-resolved origin: self403; missing/retired/pending404.
Open uses bounded public create-or-existing; unavailable uses only the exact
caller's existing-pair lookup, returning404 when absent. Both201created and
200existing carry ConversationStartResult; the [approved source correction](../docs/decisions/wanted-response-contract-correction.md)
restores the previously missing200 body. There is no new operation-ID field in
Conversations; its reviewed request/responder pair defines retry uniqueness.

Search holds FOR NO KEY UPDATE on its own request across the bounded public call.
This serializes closure while allowing the separate C transaction's FK check;
no session/private table crosses the boundary. Lost/unknown results fail503 and
retry the same pair, including read-only lookup if closure happened. Actual C
provider, independent eligibility/membership/uniqueness and final race acceptance
remain pending; test doubles are explicit and never normal/browser defaults.

## Draft-title possible matches

Before submission, the UI may call `POST /wanted-requests/draft-matches` with a
required trimmed `draft_title` (1–120 Unicode code points). Matching uses only
that draft title; category and budget are not silently treated as filters.
Search forwards the title as plain text to Listings' available-sale query
boundary. The query uses the same approved English normalization and sale
availability predicate as browse, and returns at most the first 20 public
listing summaries ordered by `created_at DESC, listing_id DESC`. It neither
creates nor reserves a Wanted Request, records a draft/search history, nor
blocks submission when the result is empty. Results are possible matches, not
recommendations or guarantees. Matching output has no relevance score or
private listing data.

The SE-02 isolated implementation uses the approved Keyword query path with
explicit `created_desc`, page1 and size20; no implicit filters are added. It
validates the bounded public page and never persists draft/query history. Matching
and create are independent operations; a failed match does not reject creation.
The normal default public providers still require real integration; native tests
exercise the actual Listings browse service/SQL with controlled Identity only.

## Saved listings

Search owns save rows keyed uniquely by `(caller.user_id, listing_id)`.
`PUT /me/saved-listings/{listing_id}` saves a listing that the caller can
currently discover, confirmed through the Listings public save-target check.
Unavailable, future, ended, retired, or inaccessible listings cannot be newly
saved. A duplicate is a successful no-op that preserves the original
`created_at`. A listing that becomes unavailable after the check may still be
saved; unavailability does not delete the reference. `DELETE /me/saved-listings/{listing_id}`
removes only the caller's row and succeeds when it is already absent. Neither
operation accepts a user ID in the request body or path.

`GET /me/saved-listings` returns only the caller's rows ordered
`saved_at DESC, listing_id DESC`, with shared pagination. Search asks Listings
for current public summaries/state for the page's saved IDs; it does not join
listing tables. An unavailable but non-retired listing remains visible with
its current approved summary and unavailable state. A retired listing remains
as a content-free placeholder containing only its listing ID, save time, and
retired state. No retired title, description, price, category, image, owner,
contact, or selection detail is returned. The saved reference may remain under
the approved retention rules; it is not an indefinite-content-retention
grant.

SE-02's isolated save implementation checks live eligibility first. An existing
own pair returns its original ID/time acknowledgement without re-running target
eligibility, including after unavailability/retirement; this reveals no old
listing content. New pairs require `read_save_target`. Pair-level transaction
serialization preserves duplicate timestamps and scopes unsave to the caller.
Saved retrieval resolves only the IDs in the actual page and requires a complete,
consistent current-state response; results are reordered to the save order, never
filtered through discovery. Real Listings target/resolver integration remains
pending; explicit contract fixtures do not complete FR-09 acceptance.

## Wanted author-command implementation notes

Create retry scope is `(author_id, operation_id)`; edit/state scope includes the
request ID and command kind. Identical normalized intent replays the original
response; conflicting reuse returns409. Current eligibility, ownership,
retired/pending state are checked before replay. Empty edits and same-state
commands preserve revision; actual changes increment it. Body money and page
coordinates must be exactly representable by their documented SQL storage.

`search.wanted_command_results` retains private request/result JSON only while
content remains retained. Database guards refuse immutable outcome changes and
origin retirement with remaining receipt content. The [approved local cleanup order](../docs/architecture/wanted-request-retirement.md)
clears both receipt payloads before origin content in one transaction, retaining
content-free retry keys. Its explicit internal coordinator/store implementation
has isolated tests; real Conversations integration remains pending. No cleanup
endpoint, scheduler, startup job or shared/live-data run is enabled.

## Shared authorization, errors, transactions, and evidence

All Search operations require a valid trusted `CallerContext`; actor IDs come
from it. Open-request reads, sale discovery, saves, and wanted-request
management are available to eligible regular and temporary accounts. Starting
a Wanted Request response remains regular-only and is enforced by Conversations
as well as the UI. Owners may only manage their own requests; saved-list reads
and writes are private to the caller.

Use the shared FastAPI error envelope. Expected outcomes include `401
unauthenticated`, `403 forbidden`, safe `404 not_found` for missing or hidden
records, `422 validation_error` for invalid filters/fields, `409 conflict` for
stale revision or invalid state transitions, and `503 dependency_unavailable`
when a required Listings/Conversations operation is unavailable. Details use
safe field/code pairs and never echo values, contact data, database details, or
another user's state. Search's own database transaction owns each Wanted
Request/save write; no session is shared across domains. A required public
dependency failure must not be reported as success. Per-operation duplicate,
retry, concurrency/lock, ambiguous downstream commit, and partial-failure
semantics plus deterministic test cases are completed in Step 9. No generic
automatic write retry is implied.

## Follow-up gates

- The user reports that domain owners approved the public Wanted Request field
  set, authenticated-only marketplace visibility, and request-origin operation
  boundaries in Step 10. The acyclic call rule remains mandatory.
- Human approval of each domain's concrete destructive content/object cleanup
  mechanism/order remains required. Search's local request/receipt order is now
  approved as linked above; shared/live runs and deployment are not authorized.
  Conversations content cleanup retains its own approval gate.
- Listing search configuration/index ownership is accepted in the existing
  PD-08 decision; real query plans, data, relevance, load and NFR evidence
  remain SE-01 work.
