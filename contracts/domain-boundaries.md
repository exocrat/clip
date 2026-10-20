# Domain ownership and call boundaries

**Status:** DL-00 Step 3 design; affected-domain review remains Step 10. This
records contract ownership and allowed call direction. It does not implement
domain behavior or settle the still-pending cleanup protocol.

## Boundary rule

Domain code calls another domain only through that domain's generated
`public.py`. It does not read or write another domain's tables or pass database
sessions across the boundary. The call graph stays acyclic. The user confirmed
that DL-00 must preserve the shared no-call-cycles rule.

Arrows below mean caller → callee:

| Caller | Callee | Purpose |
|---|---|---|
| Search | Listings | Available-listing query and listing details under the approved listing-data boundary. |
| Listings | Conversations | Create/reopen listing-origin threads; confirm a buyer's thread participation for seller selection; validate and persist listing-based offer mutations; read the minimal conversation-activity result for retirement. |
| Search | Conversations | Create/reopen Wanted Request response threads; read the minimal conversation-activity result for retirement. |
| Conversations | Identity | Check account eligibility; retrieve only the actor's selected own-contact fields; resolve an authorized notification recipient. |
| Listings | Identity | Check caller/account eligibility where an operation requires it. |
| Search | Identity | Check caller/account eligibility where an operation requires it. |

There are no reverse calls from Conversations to Listings or Search, and no
business-domain calls from Identity to another domain. In particular,
Conversations does not fetch origin state or perform seller selection. The
allowed graph is acyclic: Search → Listings → Conversations → Identity, with
Search also calling Conversations and Identity, and Listings also calling
Identity.

An internal typed argument is not authorization by itself. `CallerContext`
comes from the trusted authentication path. The origin-owning domain resolves
origin state and participant identities from its own records, then supplies
server-derived context to Conversations. Browser-supplied owner or participant
IDs are never authoritative. A conversation operation that cannot establish
the required trusted origin context or caller eligibility fails closed.

## Record and write ownership

| Records and behavior | Authoritative owner | Boundary notes |
|---|---|---|
| Accounts, authentication identities, profiles, source contacts, eligibility | Identity | Other domains use only the declared identity and contact functions. Contact values are returned only for the authorized actor and selected fields. |
| Sale listings, catalogue, images, availability, selected buyer, listing search index | Listings | Listings owns availability and selection writes, including selection reached from a Conversations screen. Listings also owns the availability-gated command path for listing-based offer mutations; Conversations remains the authoritative offer-record owner. Search consumes the approved Listings query; it does not read listing tables. |
| Wanted Requests, saved listings, Wanted Request discovery and draft matching | Search | Search owns request availability/closure and saved-list state. It invokes Conversations for response-thread creation. |
| Conversations, participants, keys, messages, read state, offers, contact-share envelopes, notification intents | Conversations | Conversations owns all writes and retention for these records. Notification intents are written in the same Conversations transaction as the originating thread/message action. |

The CN-03 task owner remains responsible for its assigned delivery work. That
does not transfer notification-intent records or their state transitions out
of Conversations. Delivery uses the Conversations-owned intent boundary and
Identity's separate recipient-resolution function; it does not create an
Identity → Conversations call. The exact worker implementation and affected
owner review remain in CN-03/DL-00 Step 10.

## Origin orchestration and race handling

Listings and Search own the user-facing operation that starts a thread from
their origin. Each checks its own origin state, resolves the actor and other
participant from trusted server data, then invokes the Conversations public
create/reopen operation. Conversations owns thread persistence and enforces
the stable origin/participant uniqueness rule; retries return the existing
thread rather than creating another one. Conversations does not call back to
verify the origin.

Recommended serialization for the later operation contracts is:

- Search serializes response creation with closing/mark-unavailable of the
  Wanted Request by locking its own request record while it validates and
  makes the short Conversations call. If close wins, a new response is denied;
  if creation wins, that thread is committed before close proceeds and remains
  an existing thread. The unique `(request_id, responder_id)` guard makes
  retry safe if the caller loses the response after commit.
- Listings serializes listing-thread creation and seller-selection eligibility
  with availability/selection changes using the Listings record as the
  authoritative lock. Conversations persists its own thread independently;
  no database session is passed between domains. A retry after an ambiguous
  result resolves through the listing/buyer uniqueness guard.
- Listings owns selection. It may call Conversations to confirm that the
  selected buyer participates in the relevant thread, then writes its own
  selected-buyer state. Conversations never calls a Listings selection API.
- Listing-based offer create/revise/resubmit and withdrawal enter through a
  Listings-owned command. Listings checks the current listing window and
  actor/participant eligibility while serializing against availability and
  retirement changes, then calls Conversations to write the authoritative
  offer record. Buyer withdrawal remains allowed after ordinary unavailability
  as specified by the offer decision; a retired listing rejects offer changes.
  Conversations owns offer revisions and never calls Listings to check state.

These are contract proposals for owner review, not tested concurrency behavior.
Operation timeouts, exact error mapping, idempotency keys, and owner-specific
locking/tests are frozen in Steps 8–10. No cross-domain transaction or
distributed rollback is assumed.

## Retirement, cleanup, and activity

Each record-owning domain performs retention/retirement cleanup for its own
content. Listings/Search decide whether their origin records meet the approved
retirement criteria. Conversations supplies a minimal activity result for all
threads associated with an origin; the result does not expose private content.
Reads, polling, delivery workers, and other non-participant actions do not
count as participant writes. Conversations owns conversation/message/offer/
disclosure cleanup and preserves the approved content-free identifiers.

The precise multi-owner lock, recheck, and cleanup order remains open for the
activity/retirement contract in Step 8 and affected-owner review in Step 10.
No cleanup sequence, cascade, or destructive implementation is authorized by
this Step 3 boundary record.

## Frontend connections and authoritative state

The UI composition map assigns presentation roles; this table maps those
connections to server owners without making the browser an authorization
boundary. Pages may compose responses from the named APIs; domain services do
not call one another except along the graph above.

| Frontend surface | Presentation connection | Authoritative data/action owner |
|---|---|---|
| `/` discovery | Search presents the Sale Listing/Wanted Request toggle; sale results come from Listings and open requests from Search. | Listings owns sale state/index; Search owns request state and discovery. |
| `/listings/new`, `/listings/:listingId`, `/listings/:listingId/edit` | Listings pages use Identity eligibility; detail offers Search save and Conversations start/reopen actions. | Listings owns listing/image/availability; Search owns saves; Conversations owns threads. |
| `/my/listings` | Composes the user's sale listings and Wanted Requests; seller inbox links navigate to Conversations. | Listings owns sale posts; Search owns requests; Conversations owns inbox/thread data. |
| `/saved` | Search presents saved records with current listing availability/details supplied by Listings. | Search owns saves; Listings owns listing state. |
| `/my/conversations` | Conversations presents threads/offers; listing or request context is obtained from its origin owner, not by a Conversations-to-origin call. | Conversations owns threads/offers; Listings owns sale context; Search owns request context. |
| `/my/conversations/:conversationId` | Conversations handles private messages; offer mutations and seller selection invoke Listings-owned commands; deliberate contact selection uses Conversations with Identity's authorized own-contact operation. | Conversations owns thread/message/offer/share records; Listings owns availability checks and selection; Identity owns source contacts. |
| `/account/contacts` | Identity edits own contacts and returns to the conversation sharing flow. | Identity owns contact values; Conversations owns any encrypted share event. |
| `/wanted/:requestId` | Search displays an open request and invokes Conversations for an eligible Contact requester action. | Search owns request visibility/state; Conversations owns the resulting thread. |

The remaining `/sign-in` and `/auth/callback` surfaces are Identity-owned; they
do not introduce a cross-domain business call. These connections correspond to
the approved routes in `docs/architecture/frontend-collaboration.md`; exact
HTTP routes, UI events and response shapes remain in each domain contract.
