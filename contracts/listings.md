# Listings contract

**Status:** The original Step 10 contract review is reported approved by the
user. The LI-01 create-retry behavior after retirement is a proposed amendment
and awaits affected-owner review. Step 11 typed declarations are generated from
the canonical source and the [combined registry](combined.md). Listings
implementation and migrations remain with LI-01/LI-02.

## Scope and authoritative data

Listings owns sale-listing records, the item-category/condition catalogues,
images/references, seller-controlled availability, the selected buyer, and the
listing search index. It owns the listing-side command boundary for seller
selection and listing-based offers. Conversations owns conversation and offer
records; Listings calls Conversations through its public interface when a
participant check or offer write is required. Search calls Listings' public
read/query contract and never reads Listings tables.

No Listing operation accepts a client-supplied owner as proof. The acting user
comes from trusted `CallerContext`; the listing owner comes from the Listing
record. Listings uses Identity's declared eligibility operation when a rule
depends on current account status. It does not expose contact values or
conversation content.

## Fields and shared values

| Field | Contract behavior |
|---|---|
| Listing ID | Server-generated UUIDv4, exposed as the shared canonical UUID string. It is opaque and conveys no permission. |
| Title | Required on every live listing; trim outer whitespace and allow 1–120 Unicode code points. |
| Description | Required on every live listing; trim outer whitespace and allow 1–5,000 Unicode code points. Preserve internal whitespace. |
| Item category | Required stable active category code from the Listings-owned catalogue: `mobile_phone`, `laptop`, `electronics`, `furniture`, `books`, `bicycles`, `appliances`, or `other`. It is independent of the Sale Listings/Wanted Requests view toggle. |
| Condition | Required active seller-declared code: `new`, `like_new`, `good`, or `fair`. It is not a platform quality/functionality guarantee. |
| Asking price | Required nonnegative integer paise, a multiple of 100. Zero is valid; floats and fractional-rupee amounts are rejected. No upper monetary cap is selected here. |
| Negotiable | Required boolean, independent of price. Missing and `null` are invalid for a live listing. |
| Pickup area | Required trimmed text of 1–120 Unicode code points. It is a pickup-area description, not an exact address or contact channel. |
| Availability window | `available_from` defaults to the server creation instant when omitted. `available_until` is nullable and, when present, must be later than the start. Both use shared UTC instants. |
| Seller availability | `available` or `unavailable`, changed only by the owner. It is separate from the time window and selected buyer; the end instant does not rewrite seller status. |
| Sensitive flag | Computed, never client-authoritative: sensitive category OR asking price strictly greater than the configured threshold. `mobile_phone` and `laptop` are sensitive categories at every price. The provisional configurable default is ₹5,000 (500,000 paise), owned by Listings; see the [threshold decision](../docs/decisions/sensitive-purchase-threshold.md). It may be changed through a reviewed configuration update. |
| Proof declaration | Optional nullable seller statement. It is displayed as unverified and never implies platform authentication or inspection. |
| Images | A live/publishable listing has 1–8 confirmed usable images. Accept JPEG, PNG or WebP, positive size and at most 10 MiB each. Only controlled image references are exposed; object keys, upload credentials and provider details are not. LI-02 owns upload, actual-object validation and delivery; this contract does not invent a URL, CDN or storage credential shape. |

The schema may clear content fields only after approved retirement. For every
non-retired row, the required live fields and image minimum still apply. Do not
use retirement nullability to permit incomplete create/edit operations.

Listings owns its retirement decision and pending-operation state. It must not
read Conversations tables from a trigger, including to check participant
activity or validate the buyer/conversation relationship. For a seller's
selection, call Conversations'
`check_listing_thread_participant` with the listing ID, conversation ID, and
candidate buyer ID; this exact-pair check is read-only and never creates a
thread. For retirement, commit a unique pending operation ID and its
server-derived cutoff on the listing before making a Conversations call. Keep
that exact pair so an unknown result can be retried after a process restart
with the identical request. Call `get_origin_activity` as a preflight, then
`mark_origin_retired` for the authoritative locked check. If the result is
`blocked_recent_activity`, clear both pending fields and stop; a later attempt
uses a new ID and cutoff. A different request using the same ID conflicts.
Only a confirmed marker permits the later local-retirement stage; deletion of
listing content or image objects still requires its separate approved cleanup
method and order. Keep the pending listing out of public read/discovery,
edit/reopen, selection and offer paths while its outcome is unresolved; keep a
content-retained pending listing visible in the owner's management list.

## Availability, discovery and read models

A sale listing is discovery-eligible only when it is not retired, seller status
is `available`, the current instant is at or after `available_from`, and it is
strictly before a non-null `available_until`. Unavailable listings remain
visible in the owner's management view and may remain as saved references, but
are excluded from public discovery. Reopening or changing a window does not
change the selected buyer; a retired listing cannot reopen.

Discovery and public-facing listing summaries contain only approved listing
display fields and controlled image references. They require an eligible
authenticated caller; no anonymous browse/read capability is implied here.
They do not expose owner IDs, private contacts, selected-buyer state, upload
state, private operational columns, or object-store keys. Detail responses
follow the same privacy rule. The detail response includes the computed
`is_sensitive_purchase` flag and, when supplied, the seller's optional proof
declaration with clear unverified wording. A summary may include the same
computed flag for its badge. Owner-only management reads may also include the
owner's own availability and selection state. Selected-buyer visibility is
limited to the listing owner and relevant conversation participants, as
owner-reviewed in Step 10. It is never public discovery data.

Listings owns an available-sale query over its own authoritative state
and indexed fields. Search uses that interface for browse, text search and
filters; it does not create a private-table join or an unsynchronized
projection. Search defines its query/response semantics in Step 7. Listing
queries authorize and apply filters before pagination, use the shared page
envelope, and provide deterministic query order with a unique ID tie-breaker.
The availability predicate is evaluated against the request-time clock, not a
stale client flag or cache.

Search's private save operation first uses a Listings-owned save-target check
to confirm that the caller can currently discover the requested listing, then
stores only its own `(user_id, listing_id)` reference. Search also uses an
internal Listings-owned saved-summary resolver for IDs it has already read
from that caller's own saved rows. The resolver returns the current approved
summary for a non-retired listing even after seller unavailability or window
expiry, and a content-free retired state after origin retirement. These are
server-to-server capabilities, not public routes; Search never reads Listings
tables and never supplies IDs outside the caller's saved page.

## Listing operations and authorization

Logical operation names below identify capabilities. Step 9 records exact
callable names/import paths, HTTP mappings, inputs/outputs, error codes,
transactions, retry behavior and tests.

| Capability | Caller and owner rules |
|---|---|
| Create listing | Eligible regular account only. Derive `owner_id` from `CallerContext`; reject temporary callers. Validate all required fields and the publishable-image invariant. No listing is published on a partial image failure. |
| Read listing/detail | Eligible authenticated callers use the available-sale query. The owner can read their own unavailable listing. Missing, retired and otherwise inaccessible content must not leak private state. |
| Edit listing | Owner only. Validate the complete resulting live record, including image count, price, category and availability window. Use an expected revision or equivalent concurrency guard; stale writes return a stable conflict. |
| Change availability/window | Owner only. `available`/`unavailable` and the time window are separate. An update never assigns or clears a buyer implicitly. A successful reopen clears the continuous-retirement eligibility anchor; exact transitions follow the approved retirement decision. |
| Read catalogue | Return active category/condition values with stable codes and labels. Listings owns updates; Search reuses category codes through this public boundary. |

Create commands save the validated request and original response atomically
with listing and image publication. The retry key is `(owner_id, operation_id)`;
while listing content is retained, the same key and request replay the original
`ListingDetail`, and changed input returns 409. When the listing retires,
Listings clears the saved request and response but keeps only owner, operation,
and listing IDs. Any later use of that key returns 409 without exposing old
content or creating another listing. This post-retirement behavior is a proposed
amendment awaiting affected-owner review.

Availability and selection commands save the validated request and original
response in the same Listings transaction as the state change. The retry key is
scoped by listing, command type, and operation_id. An identical retry returns
the saved response; reusing the key for different input returns 409. When a
listing is retired, Listings deletes its saved command requests and responses
along with the listing content. A later retry receives the normal retired-state
conflict and never replays the old content. Offer retry records remain owned by
Conversations, which persists offer results in its own transaction.

## Selection and listing-based offer commands

Listings is authoritative for `selected_buyer_id` and selection changes. An
eligible seller may select an eligible buyer from an existing listing
conversation, even without a submitted offer, only while the listing is
available and inside its window. Listings uses Conversations' participant
check rather than trusting a client-supplied buyer/conversation relationship.
The seller may clear or replace the selection through Listings. Selection is
not offer acceptance, a reservation, a payment state or a handover guarantee;
it does not change availability. Withdrawing an offer does not clear selection.
The selection's visibility is restricted to the owner and relevant
conversation participants; it is never part of public listing discovery.

Listing-origin offer create/revise/resubmit and withdrawal enter through a
Listings-owned command. Listings resolves the listing from the verified
conversation context, serializes with availability/retirement changes, checks
current account eligibility, then asks Conversations to persist its own offer
record. Create/revise/resubmit require the listing to be available and within
its window. The buyer may withdraw after ordinary unavailability, but not after
retirement. Conversations never calls Listings to inspect current state.
Offer amount/revision/note rules remain the Conversations-owned offer contract;
the shared contract uses integer paise in whole rupees and client-encrypted
optional notes.

The short caller transaction and Conversation write use separate owner
transactions; no raw database session is shared. A downstream failure must not
produce a successful selection/offer response. Exact timeout and ambiguous
commit recovery semantics are finalized per operation in Step 9 and tested
against the reviewed Conversations contract. This draft does not imply a
distributed transaction or rollback.

## Retirement and retained references

Retire Sale Listing content only after 180 days continuously unavailable or
past its availability end and at least 90 days without a participant write in
every associated conversation. Reads, polling, workers and account expiry do
not renew that conversation timer. Reopening/window changes that restore
eligibility reset the continuous-inactivity anchor. Listings obtains the
minimal public activity result from Conversations; it never reads private
conversation tables.

Listings owns clearing its content, image references and selection details. After
Conversations confirms its no-write marker, Listings uses one database
transaction to mark the listing retired, clear its user-entered content,
availability end and buyer selection, scrub saved create request/result
payloads, delete seller-command receipts, and mark attached images retired.
Keep the listing, owner, saved-reference, and content-free create-operation IDs
needed for their approved uniqueness lifetimes. Saved references may remain but
must expose no retired content. Do not cascade into Conversations or Search,
offer a public delete endpoint, or remove object-store cleanup metadata before
object deletion/absence is confirmed.

The retired image rows and their upload rows hold the object keys as durable
cleanup work. A Listings-owned worker calls the storage adapter for each exact
key. A confirmed deletion or confirmed absence lets the worker delete the image
row and upload row in one database transaction. A failure or unknown result
keeps both rows so a retry can safely call deletion again. The cleanup query is
limited to images whose parent listing is retired. The Listings worker does not
purge Conversations content; Conversations owns that separate retention work.
The seller's My Listings view continues to show unavailable listings while
their content is retained. Retired listings remain omitted from that view under
the current contract; the possible content-free retired marker remains a
recorded follow-up question.

## Shared errors, privacy and operational limits

Use the shared FastAPI error envelope and stable codes. Invalid field values
use safe 422 details; unauthenticated and forbidden are distinct where safe;
stale revision/state conflicts use 409; unavailable dependencies use 503.
Messages never include submitted values, contact details, storage keys, SQL or
provider responses. Logs use only the shared allowlisted metadata. Domain
operations specify operation-specific idempotency, duplicate results,
concurrency, partial failure and test cases in Step 9; the core adds no
automatic write retry.

No payment, reservation, transaction verification, item-quality verification,
collection, delivery or handover capability is implied.
