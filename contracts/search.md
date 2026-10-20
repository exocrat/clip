# Search contract

**Status:** Step 10 domain-owner documentation review is reported approved by
the user. Step 11 typed declarations are generated from this contract and the
[combined registry](combined.md). Search implementation and migrations remain
with SE-01/SE-02.

## Ownership and dependency boundary

Search owns Wanted Request records and private saved-listing references.
Listings owns sale-listing records, their availability, catalogue, public
summaries, and the authoritative title/description search index. Search does
not read Listings tables or maintain a listing projection. Search clients use
the Listings-owned browse/detail HTTP operations directly; Search's draft-match
and saved-list operations call only Listings' reviewed public query/summary
operations. Search calls Conversations only to start a response to an open
Wanted Request. Conversations never calls Search or Listings. This preserves
the reviewed acyclic graph.

The chosen listing boundary is the Listings-owned query backed by PostgreSQL
native full-text search, using `pg_catalog.english` for both the stored vector
and query normalization. Listings owns its GIN and supporting indexes; no
Search projection, backfill, synchronization job, or separate search service
is part of the MVP. Search never interprets a cached availability flag as
authoritative.

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
| `q` | Optional trimmed plain-text query, at most 120 Unicode code points. Omitted or whitespace-only means browse without text matching. A nonempty query uses `plainto_tsquery('pg_catalog.english', q)` against the combined title/description vector; all normalized terms must match. A query normalized to no terms returns no rows. Raw tsquery syntax is not accepted. |
| `category_code` | Optional active Listings category code; kind of item, not the Sale Listings/Wanted Requests view. Unknown/inactive codes return `422 validation_error`. |
| `min_price_paise`, `max_price_paise` | Optional inclusive nonnegative integer paise values, each a multiple of 100. If both are supplied, minimum must not exceed maximum. |
| `condition_code` | Optional active condition code (`new`, `like_new`, `good`, `fair`). Unknown/inactive values return `422 validation_error`. |
| `negotiable` | Optional boolean; true and false are distinct filters. |
| `sort` | `created_desc` (default), `price_asc`, or `price_desc`. |
| `page`, `page_size` | Shared numbered pagination: page defaults to 1; size defaults to 20 and may be 20, 50, or 100. |

Apply current availability/window, authorization, text and supplied filters
before pagination. Sale results exclude retired listings, seller-unavailable
listings, future listings, and listings whose end instant has arrived. Include
the Listings-owned public listing summary and the shared page envelope
`{items, page, page_size, has_next}`. Order `created_desc` by
`created_at DESC, listing_id DESC`; `price_asc` by
`asking_price_paise ASC, listing_id ASC`; and `price_desc` by
`asking_price_paise DESC, listing_id DESC`. Each order has a unique ID
tie-breaker. Offset pages are deterministic for a fixed result set; concurrent
changes may move rows between page requests, as accepted by the shared page
decision. Empty `q` is treated as absent only after trimming, as explicitly
defined above.

The detail response and public fields are owned by the Listings contract. They
must not include owner IDs, private contacts, selected-buyer state, upload
state, private operational fields, or storage keys. Search does not expand
that response when composing discovery.

## Wanted Request public discovery and author management

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
not selected. Browse is ordered `created_at DESC, request_id DESC`, paginated
with the shared page envelope and sizes, and does not accept sale-listing price,
condition, or negotiability filters. A request's category is a displayed item
category, not a view discriminator.

The owner-reviewed public response contains only `request_id`, `title`,
`description`, category code and
label, nullable `budget_paise`, `created_at`, and `updated_at`. It contains no
author ID, author display name, phone, email, UPI, or other contact value. The
title, description, category and optional budget are the author's intentionally
published request content. A Contact requester action starts a private
request-origin conversation through Conversations for a regular eligible
caller; it never returns contact details. Existing conversation participants
retain access when a request becomes unavailable, per the accepted lifecycle
decision. Unavailable and retired requests do not appear in public browse or
detail.

The author-only management operations create a request, list/read only the
author's own requests (including unavailable, non-retired requests), edit it
with an expected revision, and mark it unavailable or reopen it under the same
ID. Omitted fields on edit remain unchanged; nullable budget may be cleared.
Closing prevents new response conversations but does not revoke an existing
conversation. Reopening preserves request/responder uniqueness. A retired
request cannot reopen. Create/edit validate the active category through
Listings; Search owns all Wanted Request writes and closure/reopen state.
Exact close-versus-first-conversation serialization is specified with the
Conversations operation in Step 8/9. The reviewed retirement policy applies;
the cleanup mechanism and destructive ordering remain Step 10's human gate.

Author lists use `created_at DESC, request_id DESC` with shared page sizes.
Public and owner reads apply authorization and visibility before pagination.
Responses omit all retired content; a retired record does not become a
readable empty request.

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
- Human approval of the concrete destructive retirement mechanism/order is
  still required before cleanup implementation. This contract does not
  authorize cleanup.
- Listing search configuration/index ownership is accepted in the existing
  PD-08 decision; real query plans, data, relevance, load and NFR evidence
  remain SE-01 work.
