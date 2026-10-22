# Conversations contract

**Status:** Step 10 domain-owner documentation review is reported approved by
the user. Step 11 typed declarations are generated from this contract and the
[combined registry](combined.md). This contract does not select an E2EE
library/protocol, configure a provider, implement a worker, or authorize
destructive cleanup.

## Ownership and acyclic calls

Conversations owns conversation threads/membership, public-key version
metadata, ordered entries and ciphertext envelopes, read watermarks, offer
records/revisions, contact-share entries, notification intents and every
durable notification-intent state transition. It owns retention cleanup for
those records. Listings/Search own their origin records and lifecycle; Identity
owns account eligibility and source contacts; CN-03 implements notification
delivery work behind the Conversations boundary.

The allowed calls are:

| Caller | Conversations capability | Constraint |
|---|---|---|
| Listings | Create/reopen listing-origin thread; check that a buyer participates in a specified listing thread; persist a Listings-authorized offer mutation; read minimal listing-origin activity. | Listings resolves listing/owner state and serializes its own availability/selection changes. It supplies server-derived origin/participant context. |
| Search | Create/reopen Wanted Request-origin thread; read minimal request-origin activity. | Search resolves author/request state and serializes response creation against closure. It supplies server-derived origin/participant context. |
| Identity | None. | Identity never calls Conversations. Conversations calls Identity for the actor/participant eligibility checks and the authorized contact/notification-recipient capabilities. |
| CN-03 worker | Claim/complete delivery work and read the authorized recipient/read-state facts required for a due event. | Conversations keeps ownership of intent records and state transitions. Worker/provider failure never reverses the primary thread/message write. |

Conversations never calls Listings or Search, reads their tables, or uses their
private implementation code. No raw database session or cross-domain
transaction crosses a boundary. The resulting graph remains acyclic. Every
user-facing operation derives its actor from trusted `CallerContext`; internal
origin context is server-derived by the origin owner and cannot be constructed
from browser-supplied owner/participant IDs.

## Thread identity, origin, and authorization

A thread has exactly two distinct members and exactly one origin:

| Origin | Initiator | Counterparty | Stable uniqueness |
|---|---|---|---|
| Sale Listing | Eligible buyer | Listing owner resolved by Listings | At most one thread per `(listing_id, buyer_id)`; initiator is the buyer. |
| Wanted Request | Eligible regular responder | Request author resolved by Search | At most one thread per `(request_id, responder_id)`; initiator is the responder. |

The origin owner checks its own record, current state and actor/other-member
relationship, then supplies a typed server-derived context to Conversations.
Conversations checks account eligibility with Identity, enforces distinct
participants and membership uniqueness, and persists its own thread. A
client-supplied origin owner or counterparty is never proof. Temporary
accounts may initiate listing-origin conversations but not Wanted Request
responses. A responder need not own a sale listing.

Listings and Search serialize create/reopen against their own origin-state
changes. The selected contract pattern is a short owner transaction that holds
the origin row lock while making a bounded Conversations call; no session is
shared. If closure/unavailability wins first, no new thread is created. If
thread creation wins first, closure may proceed after that thread is committed.
Same-pair retries and concurrent creates resolve to the unique existing thread
and never create a second one. The stable origin uniqueness record remains
after content cleanup while its approved lifetime applies.

An unavailable/closed origin blocks new threads but does not revoke the
existing participants' thread access. Existing listing/request threads remain
participant-authorized subject to current account eligibility and independent
content-retention rules. A retired origin cannot start a new thread, reopen,
or accept a listing offer. Owner review accepted authorized reads of retained
thread content and rejection of new participant writes after retirement.
Enforcing that boundary without Conversations calling back to an origin owner
requires Listings/Search to publish retirement through a Conversations-owned
operation before clearing origin content. The exact lock/recheck/order and
failure recovery are approved for implementation as specified in the
Conversation activity and content retention section below. This approval does
not select or authorize the separate destructive content/object cleanup
mechanism.

Every public thread, entry, offer, key and read-state route checks both current
caller eligibility and membership at the owning operation. Direct ID
substitution by a nonparticipant returns a safe not-found result and reveals
neither thread existence nor peer data. The private inbox returns only threads
where the caller is one of the two members; it is ordered by
`last_activity_at DESC, conversation_id DESC` and uses shared numbered pages
(page 1, default size 20, sizes 20/50/100). It returns origin kind/ID and
minimal participant/read-summary metadata only; frontend pages obtain listing
or request details from the corresponding origin owner.

## E2EE key and envelope boundary

The client encrypts/decrypts message text, optional offer notes and
contact-share field names/values. Conversations stores/relays encrypted
payloads and the SDK's unencrypted retry-control metadata; it never stores
message plaintext, note plaintext, contact values, or private/decryption keys.
The retry control is not chat content and is routed only to the other
authorized member. The server cannot recover a lost private key. MVP supports
one active browser device/key bundle per user.

The approved storage ceilings are 1–16 KiB for an encoded public-key bundle
and 1–64 KiB for the decoded OpenE2EE payload bytes. Each relay envelope is
tagged with an allowlisted protocol ID, positive envelope version, SDK message
type and client timestamp. Encrypted message types name the sender and
recipient public-key versions; retry controls have no key-version claims. The
client protocol must bind
conversation, payload kind, sender, recipient and key versions, reject
tampering/wrong-recipient use, and preserve history according to the
human-approved key-change behavior. Key references must belong to the actual
members and use a compatible protocol. Keep referenced historical public
versions while ciphertext needs them. The byte ceilings are not plaintext
character limits or an algorithm choice.

The team selected `@open-e2ee/signal-protocol-sdk` 13.0.0 for the client
protocol, subject to recording the team source/dependency review before
runtime adoption. The client keeps SDK protocol state in IndexedDB and caches
decrypted history locally for the user's normal chat experience; the server
stores encrypted message envelopes, unencrypted retry-control metadata, and
public-key/prekey material. Retry controls contain no chat content and are
never logged. Neither keys nor plaintext history are backed up by CLIP.
Browser-data loss can therefore make retained history unreadable. This
selection does not mean the runtime crypto, browser UI, or server relay has
been implemented.

The application message payload is versioned independently of the server
envelope. Its v1 plaintext payload contains the authenticated application
context and message content; after SDK decryption, the receiving client checks
that the context matches the outer conversation, kind, sender, recipient, and
key-version fields. The server can reject mismatched claimed routing metadata,
but only the receiving client can verify the decrypted context. SDK-produced
protocol ciphertext remains opaque. Public key bundles use typed JSON fields
matching OpenE2EE 13.0.0's `PreKeyBundle`: a v1 composite identity, registration
and device IDs, an EC signed prekey, a reusable KEM last-resort prekey, and
separately selected one-time prekeys. Public byte fields are canonical
standard-padded Base64 and are decoded to bytes by the client adapter; CLIP
does not invent another key format or cryptographic primitive. The reviewed
browser security policy still applies: no third-party runtime scripts on the
conversation origin, strict CSP and safe rendering, and review of every bundled
runtime dependency.
The reviewed browser security policy still applies: no third-party runtime
scripts on the conversation origin, strict CSP and safe rendering, and review
of every bundled runtime dependency.

Conversations exposes own-key registration and prekey publication only for the
authenticated account, plus member-scoped public-key lookup and a separate
prekey-bundle operation. The server allocates a strictly increasing key
version and permits one active browser-device bundle per user; a caller cannot
register or replace another user's key. Registration and lookup use the same
explicit public fields: protocol ID/version, registration ID, fixed device ID
`1`, composite identity (32-byte X25519 and 32-byte Ed25519 public keys), EC
signed prekey (32-byte public key and 64-byte signature), and KEM last-resort
prekey (1569-byte tagged ML-KEM-1024 public key and 64-byte signature).
One-time prekeys are uploaded separately. The service validates canonical
Base64 and expected byte lengths, but does not claim to cryptographically
verify prekey signatures; the SDK verifies them during session setup. The
service keeps referenced historical public versions while retained ciphertext
needs them and never transfers or recovers private keys.

One-time prekey publication is idempotent by `(authenticated_user,
operation_id)`. Repeating the same operation and exact batch returns its
original result; reusing the operation ID with a different key version or
batch is a stable conflict. A batch contains 1–200 unique `(key_type,key_id)`
pairs for the active key version. EC one-time prekeys carry public bytes only;
KEM one-time prekeys also carry their identity signature. Inventory exposes
only counts for the caller's active version, never key bytes. A consumed bundle
is requested only for an authorized conversation member; Conversations
determines the peer from the stored thread and atomically reserves that peer's
available one-time prekeys. Its retry key is scoped to the authenticated
caller and conversation: an identical retry returns the same reserved public
bundle without consuming another key, while changed-target reuse conflicts.
The response contains the peer's typed public identity bundle, registration
ID, fixed single-device ID `1`, and any selected EC/KEM one-time public keys.
These fields map to the SDK's `PreKeyBundle` fields after Base64 decoding. If
the optional EC one-time key is exhausted, the signed EC prekey may be used;
the KEM one-time field is returned when reserved, otherwise the stored signed
KEM last-resort field is used. The adapter places exactly one of
`kem_one_time_prekey` or `kem_last_resort_prekey` in the SDK bundle. Private
material is never returned. These operations do not create a conversation or
imply that the server can decrypt messages.

## Ordered conversation entries and messages

Conversation sequence is allocated by Conversations under a thread lock and
is the authoritative order. A participant message write atomically stores a
content-free entry header, its encrypted envelope, the next sequence and
`last_activity_at`; a text message also creates/updates its durable unread
notification intent in the same transaction when policy requires it. Only the
two members can submit a message. The sender and recipient/key references are
derived/validated against the thread, not trusted from arbitrary IDs. Reject
plaintext message fields and malformed/unsupported envelope metadata. A
write that cannot atomically persist required primary records returns failure;
no success is reported for a partial message.

`CipherEnvelope` carries the OpenE2EE relay fields needed to reconstruct an
incoming SDK `Envelope`: `sdk_message_type`, `client_timestamp_ms`, and
`payload_base64`, alongside CLIP's protocol/version fields. For encrypted
`ciphertext` and `prekey_bundle` messages, both key-version references are
required. The client timestamp is milliseconds, is set before encryption,
and must match the SDK timestamp and the timestamp bound into the encrypted
message. It exists only for SDK replay/retry matching; it is not authoritative
for sequence, participant activity, retention, or authorization. CLIP's
`operation_id` is the SDK `clientMessageId`, so retries reuse both exactly.
The server supplies the SDK envelope's sender, recipient, entry ID, and
server-received timestamp from authenticated membership and the stored entry.

OpenE2EE `retry_request` is a protocol control envelope, not an encrypted
chat message. It is accepted through the same member-only message submission
operation and ordered entry stream, but returned with `kind=protocol_control`;
the server routes it only to the other thread member, does not create unread
text counts or notification intents, and does not parse its opaque
`payload_base64`. Its key-version fields are null. Its SDK payload is
unencrypted and may contain protocol retry metadata, so it is treated as
sensitive: never log or expose it outside the two members. The control entry
uses the normal server sequence and server activity timestamp, is subject to
the same no-write marker, rate limiting and content-retention rules, and is
not presented as a user message. Clients pass it to the SDK's retry-request
receive path rather than decrypting or rendering it. `sender_key` and
`unidentified_sender` are not accepted by CLIP's one-device, 1:1 MVP.

For every OpenE2EE message or retry-control send, the client generates a fresh
UUIDv4 `operation_id` that is globally unique for that sender across
conversations and SDK message types; it reuses that ID only for an identical
retry. Reuse for another conversation, type, timestamp, or payload is a
conflict. Non-SDK writes such as offer revisions retain their separately
declared idempotency scopes.

Messages are retrieved only by a member, in ascending sequence order, using
incremental `sequence > after_sequence` retrieval rather than numbered pages.
The cursor is a nonnegative committed sequence (default zero); the response
includes entries, the last returned sequence and `has_more`, with a bounded
page size of 20 by default and 20/50/100 allowed. An empty page does not
advance the cursor. Each entry exposes only the metadata needed to render the
authorized thread: ID, sequence, kind, sender, creation instant and either the
opaque SDK transport envelope (encrypted message or unencrypted retry
control) or a content-deleted marker. It never exposes an
envelope to a nonparticipant or content after its approved purge.

Every participant write carries a client-generated UUID operation ID for
retry deduplication. OpenE2EE sends require that ID to be globally unique per
sender across conversations and SDK envelope types; identical retries return
the original entry/sequence, while reuse with different intent or scope
returns a stable conflict. After retained content is purged, an operation ID
remains reserved and retry cannot recreate the expired payload. Step 9 records
exact opaque-byte retry equality and an owner-reviewed 409 conflict after
content purge in the [combined registry](combined.md).
Reads, polling, key lookup, acknowledgements and workers do not advance
`last_activity_at`.

## Read acknowledgements and receipts

Each member has a monotonic `last_read_sequence` watermark. The client sends an
acknowledgement only after the entries have actually been displayed; merely
fetching or polling never acknowledges them. Conversations checks membership,
requires a nonnegative sequence no later than the greatest committed sequence,
and atomically advances the caller's watermark without decreasing it. Repeating
the same/older acknowledgement succeeds idempotently. It does not count as a
participant write and does not reset thread-retention timing.

The notification boundary can read the target member's authorized watermark
to decide unread suppression. For the MVP, expose only the caller's own read
watermark; do not expose the peer's sequence, a `read_at` timestamp, or
online/presence status. No product requirement needs a participant-facing read
receipt, so the smaller interface avoids disclosing reading activity. A
recipient can never update the other member's watermark.

## Listing and Wanted Request thread operations

`open_or_create_listing_conversation` is callable only by Listings with
server-resolved listing ID, buyer actor and owner. Listings requires a
currently eligible sale listing for a new thread; retries may resolve the
existing buyer/listing thread even after ordinary unavailability. This
operation does not expose listing-private fields or selection state.

`open_or_create_wanted_conversation` is callable only by Search with an open,
non-retired request, regular eligible responder and server-resolved author.
It returns an existing request/responder thread when the pair already exists
and never creates a second one. A retry after request closure uses a separate
Search-authorized `find_existing_wanted_conversation` read, which may return
only that request/responder pair's already-existing thread; it cannot create a
thread. If no matching thread exists after closure, the request fails safely.
Existing threads remain accessible subject to membership and account checks.
Search performs the owner-side close/create serialization described above;
Conversations never re-reads Search state.

These internal operations are not browser routes. HTTP contact actions first
invoke the Search-owned response operation, which validates caller capability
and request state. Exact call/import signatures and error mapping are
completed in Step 9.

## Offer records and listing-owned commands

Structured offers are supported only in Sale Listing conversations. A buyer
has at most one logical offer per thread. Conversations owns offer IDs,
immutable revisions, current revision and statuses `submitted`/`withdrawn`;
amounts are nonnegative integer INR paise and must be multiples of 100. Zero
is valid. Amount/status/time are server-readable to support the authorized
seller overview; optional notes are client-encrypted. Offer notes are not
searchable, logged or included in email.

The browser uses Listings-owned commands for listing-origin create/revise,
resubmit and withdrawal. Listings resolves the thread's authoritative listing
and buyer, serializes against current availability/window/retirement and
eligibility, then calls Conversations to write its offer record. Create,
revise and resubmit require a currently available, in-window non-retired
listing and eligible participants. Buyer withdrawal is allowed after ordinary
unavailability but not after retirement. Conversations never calls Listings
and cannot bypass its command gate through a public offer-write route.

For seller selection, Listings may call an internal participant-check
operation with its server-resolved listing ID, conversation ID and candidate
buyer ID. Conversations returns only whether that buyer is a member of that
listing-origin thread; it returns no message, offer or other participant data.
Listings remains responsible for checking that the caller owns the listing,
the candidate is eligible, and selection is still allowed under its current
serialized listing state.

Only the buyer who owns an offer may mutate it. Create/revise/resubmit appends
a new submitted revision using an expected current revision; stale changes
conflict. A withdrawal appends a withdrawn revision with the prior amount; it
does not clear seller selection. A later resubmit reuses the same offer ID and
appends another submitted revision. Each command has an idempotency operation
UUID: identical retries return the original result; conflicting reuse returns
a conflict. One offer per buyer/thread is a database-backed invariant. Seller
selection is a separate Listings action, not offer acceptance, reservation,
payment, or handover verification. Wanted Request response threads do not
support structured offers; adding them requires a new reviewed decision.

Participant offer reads remain inside that thread. Seller overview can include
no-offer threads, current offer status/amount, and request-response threads in
the caller's own member scope; it must not reveal unrelated conversation
content. Content/history removed under retention is represented only by the
approved content-free state, never reconstructed from retries.

## Deliberate contact sharing

The participant may share only their own available `email`, `phone`, and/or
`upi_id` through the separate confirm-and-share flow. Conversations first
checks that the caller is a member, then uses Identity's own-contact options
and selected-contact operations bound to that same trusted actor. The user
selects exact fields and confirms before selected values are returned to that
user's client for encryption. Unselected values are never returned. Only the
other thread member is the share recipient; caller and recipient IDs are
resolved from membership, not arbitrary request data.

The client submits a contact-share envelope addressed to the other member
using the approved protocol. Conversations stores only its entry kind, key
references and encrypted envelope; selected field labels are inside the
ciphertext and are not stored as plaintext columns or notification metadata.
Only the two members can retrieve it. If Identity retrieval or conversation
storage fails, no contact-share entry is reported as successful or partly
published. Contact-share payloads and encrypted field labels are removed 30
days after each share; retain only the content-free ordering marker until
thread-history cleanup. Source contacts retain Identity's separate policy.

Because Conversations cannot decrypt an E2EE envelope, the server cannot prove
that the opaque payload contains only selected own-contact values. The
approved flow guarantees actor/recipient authorization and the client UX
selection path; it does not claim server inspection of encrypted content.
General messages, logs, analytics, notifications, errors, screenshots and
evidence must not intentionally include contact values. The product UI uses
the deliberate contact-share flow rather than pre-filling contact details in
message text.

## Durable notifications and CN-03 boundary

Conversations owns notification intents and every durable state transition.
The intent is written atomically with its originating thread/message
transaction; provider delivery occurs after commit. New-conversation email is
eligible for the other member immediately after the thread commits. The only
other required email is one unread-message reminder per unread episode, due 15
minutes after its first unread text message. Later unread text messages update
the episode's target sequence but do not postpone its original due time.
Offer/contact-share writes do not independently send email.

Before sending a reminder, CN-03 reads the authorized recipient watermark and
asks Identity for that currently eligible recipient's delivery destination.
Suppress the event when the recipient has acknowledged all currently unread
messages. Recheck eligibility and read state immediately before dispatch.
Intents store recipient UUIDs, event/routing metadata and required sequence
references only; never copy an email address, message, contact value or
ciphertext into the intent or email. A generic new-conversation/reminder
message and safe conversation link are the proposed template; no listing title,
message preview, contact value or other sensitive listing detail is included.

At most five total delivery attempts are allowed. After transient failures,
wait 1 minute, 5 minutes, 15 minutes and 1 hour; stop at 24 hours after the
immutable original due time. A terminal provider failure stops immediately.
Provider delivery is not exactly-once; an ambiguous send may be retried within
the approved bound, using provider idempotency if later selected. A failed
provider attempt never reverses a successful conversation/message write.
Terminal intent rows are retained for 30 days after terminal completion, then
deleted while a separately reviewed bounded replay guard preserves episode
and deadline semantics. No immediate mail for each message, offer or share;
no digest, match alert, provider, schedule, or new cloud resource is implied.

CN-03 calls a Conversations-owned delivery interface to claim due intents and
record outcomes using lease fencing. Conversations rechecks/suppresses read
episodes and maintains retry/deadline/deduplication state. The exact lease
duration, worker authorization/configuration and provider idempotency remain
CN-03 implementation/owner-review gates. Missing/unknown read state, expired
lease, unknown worker outcome, or unavailable Identity recipient resolution
must never be interpreted as permission to send or as successful delivery;
leave the intent pending/retryable or report a bounded safe failure. The
primary user action remains successful if only asynchronous delivery fails.

## Conversation activity and content retention

`get_origin_activity` is an internal Conversations operation used only by
Listings and Search. Given an origin kind and server-owned origin ID, it
examines every retained thread reference for that origin and returns only the
conversation count and latest `last_activity_at`; it does not return thread
IDs, member IDs, messages, offers, receipts or notification state. The
timestamp is initialized when a thread is created and advances only for
participant message, offer-revision/withdrawal or contact-share writes.
Each participant-write timestamp comes from the server after the write holds
the Conversations thread lock. Callers cannot supply an activity timestamp.
Reads, polling, key lookup, notifications and cleanup never advance it.

For zero associated threads, count is zero and latest activity is null. For
one or more threads, the origin owner compares the returned maximum with its
server-derived cutoff. This is only a preflight: if completeness/state is
unknown or Conversations is unavailable, return a safe dependency failure and
the origin owner must defer retirement. Never treat an error or missing result
as zero activity. The public call exposes no content and grants no private
table access.

After that preflight, Listings or Search calls `mark_origin_retired` with the
same stable operation ID and cutoff. Conversations locks every associated
thread in ascending thread-ID order, rechecks each server-recorded latest
participant-write time against the cutoff, and marks all threads no-write in
one transaction. A write after the cutoff blocks retirement; if any thread is
too recent, none are marked. A message and the marker contend on the same
thread lock: whichever acquires it first determines the result. Messages,
offer revisions/withdrawals, and contact shares all check the local marker
under that thread lock before writing or advancing activity. The marker does
not prevent authorized reads of retained history and does not delete content.

The result is `{outcome,marked_count}`, where `outcome` is `marked`,
`blocked_recent_activity`, or `already_marked`. `marked` with count zero means
the origin has no associated threads; `blocked_recent_activity` marks none;
`already_marked` means all associated threads were already marked before this
operation, and `marked_count` reports the number of those existing markers. A
mixture of marked and unmarked threads is an inconsistent state:
stop and reconcile through the Conversations API rather than partially
proceeding. Operation IDs are globally unique. Repeating the same ID with the
same origin and cutoff returns its stored result; reusing it for a different
origin or cutoff returns a stable conflict without changes. Unknown outcomes
keep the origin pending; retry the same operation ID and never clear content
on an unknown result. After a blocked result, the origin owner may clear its
pending state without clearing content; a later attempt uses a new ID.

The origin owner sets pending state in its own transaction before calling
Conversations, blocking new origin work while the call is in progress. It may
clear its own content only after a confirmed marker, in its own transaction.
Listings and Search do not hold an origin lock across a Conversations call.
Conversations never queries or updates Listings or Search business tables;
origin owners validate their own state and use these public operations.

After 90 days without participant writes, purge message content, encrypted
offer notes and structured offer revisions together under the approved
retention policy. Contact-share payloads/labels are removed after 30 days.
Keep only content-free ordered markers and minimal origin/thread/member and
offer uniqueness guards for their approved lifetimes. Reads, polling, workers,
account expiry and cleanup do not restart the 90-day timer. The origin marker
order above is approved for implementation. Physical content/object cleanup
and the post-retirement My Listings display remain separate decisions; do not
infer a deletion mechanism from the marker operation.

## Shared errors and safe operations

Use the shared FastAPI error envelope and stable codes. Expected classes are
`401 unauthenticated`, `403 forbidden`, safe `404 not_found` for missing or
nonparticipant resources, `409 conflict` for uniqueness/state/revision or
idempotency conflicts, `422 validation_error` for malformed fields or
unsupported envelope metadata, `429 rate_limited`, and `503
dependency_unavailable` for Identity/origin/required storage failures. Never
echo ciphertext, plaintext, contacts, keys, provider response bodies, SQL or
another user's membership/record state. Logs contain only allowlisted
request/operation/entity IDs and safe outcome codes; neither ciphertext nor
key material is logged or attached to traces/evidence.

The required deterministic checks are assigned in Steps 9/12 and CN-01/02/03:
two-client ciphertext exchange, SDK prekey/ciphertext relay reconstruction,
retry-request control routing without unread/notification side effects, and
tampering/wrong-key failure; participant
and ID-substitution denial; origin-pair duplicate/concurrent creation and
close/create races; ordered/incremental reads and retry; monotonic read
acknowledgements; listing availability-gated offer writes and revisions;
selected-own-contact authorization and encrypted-only persistence; durable
notification atomicity, read suppression, retry/failure bounds; activity
aggregation/unknown-state fail-closed behavior; and 30/90-day content-marker
retention. Isolated stubs cannot establish real cross-domain acceptance.

## Explicit review items

- CN-01 Step 2 selected OpenE2EE 13.0.0 and the envelope fields above; runtime
  adoption remains gated on recording the team source/dependency review and
  implementing the browser storage, key-change and key-loss behavior.
- The user reports that affected owners reviewed origin create/close locks,
  activity completeness, read-receipt visibility, no-write behavior after
  origin retirement and the retirement-marker operation, notification
  ownership/FK ordering and failure semantics.
- Explicit human approval of the concrete destructive retention mechanism/order
  is still required before cleanup implementation. No cleanup or cascade is
  authorized here.
- CN-03 must settle lease duration, worker authentication/configuration,
  provider setup/idempotency limits and live-send approval in its own gates.
- The [combined Step 9 registry](combined.md) records route/callable names,
  typed signatures, result/error shapes, retry behavior, focused tests and
  frontend connections. Step 10 owner review is reported approved. NFR-05 requires
  the real two-client path and CN-03 producer/delivery integration.
