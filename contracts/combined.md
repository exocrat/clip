# DL-00 combined operation contract

**Status:** Steps 9–10 operation registry assembled from the four reviewed
domain contracts. The user reported that domain owners reviewed and approved
the documents on 2026-10-20. The human-readable domain behavior remains in
[identity.md](identity.md), [listings.md](listings.md),
[search.md](search.md), and [conversations.md](conversations.md). Step 11
generates declarations from these accepted contracts. The exact origin-cleanup
order still needs separate human approval before implementation or a destructive
run. No feature implementation, provider or cloud change is authorized here.

## Shared wire models and operation rules

| Type | Contract |
|---|---|
| Entity IDs | JSON string containing a server-generated UUIDv4 in lowercase hyphenated form. IDs are opaque, carry no permissions and are never supplied as actor identity. |
| Instants | Offset-required RFC 3339 inputs normalized to UTC; outputs use exactly six fractional digits and Z. Naive timestamps are invalid. |
| Money | Integer INR paise only; reject booleans, floats, negatives where not allowed, and values not divisible by 100 for whole-rupee listing/offer/budget fields. Zero is distinct from absent. |
| Caller | CallerContext(user_id, account_class, valid_until) is server-created and internal only. It is never an HTTP request model. Authenticated routes reject missing, invalid, expired or revoked contexts with 401. |
| Numbered page | PageRequest(page=1, page_size=20); page is positive and size is 20, 50 or 100. HTTP uses PageResult[T] = {items, page, page_size, has_next}; internal Python callers use the equivalent app.core.pagination.Page[T]. Filtering and authorization occur before offset slicing; stable owner-defined sort includes a unique ID tie-break. |
| Conversation entries | The per-thread committed sequence is the incremental cursor; it is not replaced by numbered page offsets. Read sequence > after_sequence in ascending order with a bounded page_size of 20/50/100. |
| Error response | Shared {error:{code,message,details?},request_id?} envelope. details contain only safe {field,code} pairs. Do not serialize rejected values, exception text, private records, secrets or provider responses. |
| HTTP status map | 400 bad_request; 401 unauthenticated; 403 forbidden; 404 not_found; 409 conflict; 422 validation_error; 429 rate_limited; 500 internal_error; 503 dependency_unavailable. Keep applicable protocol headers. |
| Retry behavior | No arbitrary automatic write retries or universal idempotency store. Each operation below declares whether retries are safe, its duplicate/concurrency result, and any operation-specific key scope/lifetime. If a key is needed, same key plus identical intent returns the original result; conflicting reuse returns 409, with persistence atomic in that owner. Cross-domain transactions are not allowed. |
| Internal service contexts | `OriginOwnerContext` and `NotificationWorkerContext` are server-injected, in-process contexts, never HTTP models. Owner review accepted the intended origin/worker call paths; the Python type itself is not authentication. Server composition and CN-03 wiring must supply only authorized contexts. |

For PATCH, omitted means unchanged; null is accepted only where the field is
explicitly nullable and means clear/reset as described below. Required fields
reject missing, null, and empty values. Whole-resource create/replace validates
the complete resulting live state. Invalid pagination/filter/body inputs use
422 and safe field codes. A downstream timeout after a possible commit is
ambiguous: follow only that operation's declared idempotency-key or stable-pair
lookup path; never assume rollback or issue an unguarded retry.

The HTTP operation IDs below are registered in each owner's `HTTP_OPERATIONS`
declaration and generated into OpenAPI. They are not Python functions in the
public module; route handlers are implementation work for the named domain
task. Internal callables are separately declared Python functions and never
become HTTP or OpenAPI operations by inference. Every operation below has success,
unauthorized/forbidden, invalid, duplicate/retry and relevant partial-failure
checks assigned to the named implementation task; isolated doubles do not
count as real integration.

## Identity HTTP operations

Session transport details (cookie attributes, CSRF binding, lifetime and
provider credentials) remain the ID-01 authentication/session design gate.
Responses never return a bearer/session secret in JSON. Successful sign-in
returns the public SessionView and establishes a server-managed session;
logout revokes it. ID-01 must finish provider/abuse settings before real
provider use.

| Method and route / operation ID | Input → output | Authorization, state, errors, retries and required cases |
|---|---|---|
| POST /auth/microsoft/sessions — identity_create_microsoft_session | MicrosoftSessionRequest{id_token: SecretStr} → SessionView{user_id,account_class=regular,valid_until,display_name?} | Public credential exchange. Identity validates signature, issuer, audience, expiry, claims and approved IISc domain; atomically get/create by verified issuer/subject. Invalid token/domain is generic 401; provider unavailability 503. No raw token logging/storage. Account identity is unique by verified issuer/subject; a repeated valid exchange may establish another session, and the provider-state anti-replay/session replacement policy remains ID-01 review. Do not automatically retry an ambiguous exchange. Test valid, expired, wrong issuer/signature/audience/domain, duplicate callback and provider failure. |
| POST /auth/temporary/registration-challenges — identity_start_temporary_registration | RegistrationChallengeRequest{email,operation_id} → ChallengeAccepted{challenge_id,expires_at} (202) | Public; normalize email and return indistinguishable acceptance for enrolled/ineligible addresses. Send one purpose-bound OTP through Identity; challenge/attempt state belongs to Identity. Rate limit 429; provider error is safe and cannot pretend delivery succeeded. Same `(purpose,normalized email,operation_id)` and intent returns the same challenge without another send; deliberate resend uses a new UUIDv4 operation ID and replaces the prior unconsumed challenge within approved limits. It never extends a verified account. Test same-key retry, deliberate resend, enumeration, expiry, attempt cap and provider timeout. |
| POST /auth/temporary/accounts — identity_activate_temporary_account | ActivateTemporaryRequest{challenge_id,code,password} → temporary SessionView (201) | Public OTP exchange. Verify challenge once, then atomically create/activate the account, set activated_at, set exact expires_at=activated_at+14 days, and create session. Preserve the service-lifetime enrollment guard; no self-renew. Invalid/expired/consumed challenge is generic 422; already-enrolled conflict is non-enumerating. If a successful response is lost, replay is rejected and the user may sign in with the chosen credentials; the account/session write is atomic. Test wrong/replayed OTP, ambiguous response followed by login, concurrent activation and no renewal. |
| POST /auth/temporary/sessions — identity_create_temporary_session | TemporarySessionRequest{email,password} → temporary SessionView (200) | Public credential exchange; only verified, active temporary account. Generic 401 for incorrect/expired/revoked credentials; 429 for abuse controls. Each successful explicit login may create a session; do not automatically retry an ambiguous response. No account/password-state oracle. Test correct/incorrect password, expiry, revocation, duplicate explicit login and concurrent reset/login. |
| POST /auth/temporary/password-reset-challenges — identity_start_password_reset | PasswordResetChallengeRequest{email,operation_id} → ChallengeAccepted{challenge_id,expires_at} (202) | Public; same generic response for unknown/ineligible address. Identity owns challenge/provider effects. Same `(purpose,normalized email,operation_id)` and intent returns the same challenge without another send; deliberate resend uses a new UUIDv4 operation ID and replaces the prior unconsumed challenge within approved limits. Rate limit 429; provider failure safe. Reset never renews an account. Test same-key retry, deliberate resend, enumeration, expiry, replay, and provider failure. |
| POST /auth/temporary/password-resets — identity_reset_temporary_password | ResetTemporaryPasswordRequest{challenge_id,code,new_password} → empty 204 | Public OTP exchange. One owner transaction changes hash, consumes challenge and revokes all sessions. Expired/revoked accounts remain expired/revoked. Invalid/consumed challenge 422, eligible state race 409; after an ambiguous committed reset, user signs in with the new password. Test atomicity, replay, ambiguous response/login, simultaneous reset and old-session rejection. |
| DELETE /auth/session — identity_logout | No body → empty 204 | Current authenticated session only; revoke current server session idempotently. Missing/expired session 401. Test repeated logout and subsequent protected-route denial. |
| GET /me — identity_read_me | No body → SessionView | Current authenticated user only; no contact fields. Identity rechecks session/account state; 401 if expired/revoked. Test regular/temporary shape and revoked session. |
| PATCH /me/profile — identity_update_own_profile | ProfilePatch{display_name?: Optional[str]} → ProfileView | Current caller only. Owner-reviewed display-name rule: trimmed 1–80 Unicode code points; omission leaves unchanged, null clears, empty string invalid. Identity transaction, no other profile lookup; concurrent explicit updates are last-commit-wins. Repeating the same patch is safe. Invalid input 422; test missing/null/empty, own-only, retry and concurrent updates. |
| GET /me/contacts — identity_read_own_contacts | No body → OwnContacts{email?,phone?,upi_id?} | Current caller only; returns only that user's shareable source contacts, never in GET /me. Test own access, empty fields and redacted errors/logs. |
| PUT /me/contacts/{contact_kind} — identity_set_own_contact | Path kind email, phone, or upi_id; ContactValueRequest{value} → empty 204 | Current caller only. One field at a time; value is trimmed, validated and stored by Identity. Owner-reviewed formats: email <=254 chars; phone E.164 + and 8–15 digits; UPI VPA local-part@handle, 3–100 ASCII characters. Invalid field 422; update is idempotent. Test each accepted/rejected format and ensure no value in errors/logs. |
| DELETE /me/contacts/{contact_kind} — identity_delete_own_contact | Path kind email, phone, or upi_id → empty 204 | Current caller only; immediate future reads no longer return the field. Idempotent if absent. Existing encrypted shares retain their separate 30-day policy. Test repeated delete and prior-share non-mutation. |

The Identity/contact values above were owner-reviewed, as reported by the user.
That review does not configure a provider/session or settle the remaining
password/OTP and provider-safety gates before real provider setup.

## Identity internal callables

All four functions are private in-process domain calls from trusted server
code. They do not appear in OpenAPI. CallerContext identifies the actor;
target user IDs come from an owning domain's relationship, never a browser
parameter.

| Import path and signature | Allowed caller / result and failure behavior |
|---|---|
| app.domains.identity.public.check_account_eligibility(user_id: UserId, required_class: Optional[AccountClass] = None) -> AccountEligibility | Listings, Search, Conversations. Returns only eligible true/false for current state and optional class requirement; no profile, contact, login or reason. Identity unavailable fails closed. Test active, wrong-class, expired, revoked, missing and dependency failure. |
| app.domains.identity.public.get_shareable_contact_options(caller: CallerContext, conversation_id: ConversationId) -> ShareableContactOptions | Conversations only after participant/consent-flow check. Returns the actor ID and three availability booleans, never values. Non-actor/invalid context denied. Read-only/no transaction. |
| app.domains.identity.public.get_selected_own_contacts(caller: CallerContext, conversation_id: ConversationId, fields: frozenset[ContactField]) -> SelectedOwnContacts | Conversations only after membership and explicit confirmation. fields is nonempty and contains only supported contact kinds; returns only requested, still-present values as required nullable fields. No storage write; values are ephemeral and repr/log/error redacted. Invalid/removed fields fail safely. |
| app.domains.identity.public.resolve_notification_recipient(context: NotificationWorkerContext, recipient_id: UserId) -> Optional[NotificationRecipient] | CN-03 delivery path only, with server-injected worker context. Returns only the currently eligible account's verified delivery destination; returns none for ineligible/removed recipients. No contact-profile fields and no persistence. Identity outage yields retryable dependency failure; no address is copied into Conversations. |

Password minimum/maximum, OTP digits/validity/attempt/resend limits, provider
safety and session transport remain Identity implementation gates in ID-01;
the API fields and failure privacy are fixed here, but no provider is configured.

## Listings HTTP operations

ListingSummary is the Listings-owned public display view (title, description,
category/condition codes and labels, asking price paise, negotiable, pickup
area, availability window, computed sensitive flag and controlled image
references). Public responses omit owner ID, selected buyer, upload state,
object key and all contacts. ListingDetail adds the optional unverified proof
declaration and detail image references. Owner-management output may include
only that owner's availability and selection state.

| Method and route / operation ID | Input → output | Authorization, state, errors, retries and required cases |
|---|---|---|
| GET /listings — listings_query_available | Search filters/page from search.md → PageResult[ListingSummary] | Eligible authenticated regular/temporary caller. Listings applies current availability/window, filters and stable sort before page slicing. Read-only. 422 invalid filter/page; 503 query dependency. Test every filter, exact time boundaries, auth, tie/pagination and unavailable exclusion. |
| GET /listings/{listing_id} — listings_read_detail | UUID path → ListingDetail | Eligible caller reads discovery-eligible listing; owner may read own unavailable, non-retired record. Hidden, missing or retired returns safe 404. Read-only. Test owner/non-owner, retirement and no sensitive fields. |
| GET /me/listings — listings_list_mine | page,page_size → PageResult[ListingManagementView] | Eligible regular caller; only own non-retired records, including unavailable/past-window. Sort created_at DESC,id DESC. Read-only. Test owner isolation, paging and retired tombstone policy. |
| GET /catalogue — listings_read_catalogue | No body → CatalogueView{categories,conditions} | Eligible authenticated caller. Read-only, deterministic code order. Search uses the internal public callable below for category validation. Test auth denial, active/inactive values and stable order. |
| POST /image-uploads — listings_create_image_upload | ImageUploadRequest{media_type,size_bytes,operation_id} → UploadInstruction{upload_id,upload_url,required_headers,url_expires_at} | Eligible regular account; creates owner-bound pending intent with generated opaque key and original 24-hour intent deadline. Accept JPEG/PNG/WebP and 1–10,485,760 bytes; validates claimed metadata before issuing upload. External object write is not yet an authoritative image. Same operation ID/intent returns the same intent and deadline; a refreshed upload URL cannot extend that deadline. Conflicting reuse 409; storage error 503. Test limits, wrong owner, duplicate/timeout and no key/URL in logs. |
| POST /image-uploads/{upload_id}/confirm — listings_confirm_image_upload | UUID path → ConfirmedImage{upload_id,media_type,size_bytes} | Owner only. LI-02 inspects actual object/type/size; atomically confirms intent metadata. Duplicate identical confirm returns same result; conflicting/missing object is safe conflict/404; storage timeout is retryable and never reports confirmed. Test wrong owner, invalid actual content, duplicate, missing object and timeout. |
| DELETE /image-uploads/{upload_id} — listings_cancel_image_upload | UUID path → empty 204 | Owner only; cancels/removes only unattached intent, then safe object cleanup per LI-02. Repeated cancel succeeds. Failed/ambiguous object deletion retains cleanup metadata and reports safe failure; cleanup mechanism/order remains gated. Test wrong owner, attached intent, repeat and failed/ambiguous delete. |
| GET /images/{image_id}/delivery — listings_get_image_delivery | UUID path → ImageDelivery{url,url_expires_at} | Eligible caller who can view the attached image (public discovery-eligible listing or owner where permitted). Listing remains authoritative; no public bucket. Owner-reviewed URL lifetime is at most 5 minutes; LI-02 must implement and validate actual signing/storage behavior. Missing, hidden, retired or deleted content is safe 404; storage outage 503. Test ownership, expiry, revoked/unavailable access and URL redaction. |
| POST /listings — listings_create | CreateListingRequest{title,description,category_code,condition_code,asking_price_paise,negotiable,pickup_area,available_from?,available_until?,proof_available?,image_upload_ids[1..8],operation_id} → ListingDetail (201) | Eligible regular caller only. Server assigns owner/ID/time/default start; active catalogue and confirmed unattached upload intents are validated; listing and images publish atomically. Required title 1–120, description 1–5000, pickup 1–120 Unicode code points; price >=0 whole-rupee paise; window end > start. Duplicate operation returns original; different intent 409. Test temporary denial, fields, zero, missing/foreign/unconfirmed images and transaction rollback. |
| PUT /listings/{listing_id} — listings_replace | UUID path; full ListingReplacement{expected_revision,fields...,image_upload_ids[1..8],operation_id} → ListingDetail | Owner only, active/non-retired listing. Full resulting record validation and serialized image invariant; omission of optional available_until/proof_available means explicit null as defined by replacement schema. Atomic owner transaction. Stale revision 409; invalid values 422; image dependency failure 503. Test owner, stale update, concurrent last-image removal and partial failure. |
| PUT /listings/{listing_id}/availability — listings_change_availability | AvailabilityChange{expected_revision,availability,available_from?,available_until?,operation_id} → ListingDetail | Owner only. `available` or `unavailable` is independent of time window and selection; omitted start preserves current value, null end clears end; successful reopen resets retirement eligibility anchor. Seller-unavailable reads remain out of discovery. Stale 409; no implicit selection change. Test non-owner, exact boundaries, reset, repeated operation and concurrent edit. |
| POST /listings/{listing_id}/conversations — listings_start_conversation | StartListingConversationRequest{operation_id} → ConversationStartResult{conversation_id,created} (201/200) | Eligible caller may initiate as buyer only while the listing is discoverable; owner cannot start a buyer thread with self. Listings resolves owner, locks its own record, then calls Conversations. Unique buyer/listing pair returns existing thread; retries after unavailability resolve only that pair. C dependency timeout 503 may be ambiguous; same pair retry is safe. Test owner-self denial, concurrent create, stale/hidden listing and downstream timeout. |
| PUT /listings/{listing_id}/selection — listings_set_selected_buyer | SelectionChange{buyer_id: Optional[UUID],conversation_id: Optional[UUID],expected_revision,operation_id} → ListingOwnerView | Eligible listing owner only. Set requires both IDs, eligible buyer membership confirmed by Conversations, and currently available/in-window listing. Clear requires both null and is allowed while ordinarily unavailable, never after retirement. Listings serializes state/write; retry returns same; stale selection 409. Test non-owner, no-offer participant, nonparticipant, wrong listing, race and failed Conversations call. |
| PUT /listings/{listing_id}/conversations/{conversation_id}/offer — listings_submit_offer | OfferRevisionRequest{amount_paise,note_envelope?:CipherEnvelope,expected_revision?:int,operation_id} → OfferView | Eligible listing-conversation buyer only. Listings resolves authoritative listing/buyer and serializes current available-window check before calling Conversations. Create/revise/resubmit only while available/in-window; integer paise >=0, multiple of 100; amount/status structured, note encrypted. Duplicate identical key returns original; stale revision 409. No reservation/payment. Test role, price, encryption metadata, availability race and timeout. |
| POST /listings/{listing_id}/conversations/{conversation_id}/offer-withdrawals — listings_withdraw_offer | OfferWithdrawalRequest{offer_id,expected_revision,operation_id} → OfferView | Eligible offer buyer only. Listings confirms owner/origin and calls Conversations. Allowed after ordinary unavailability but not retirement; appends withdrawn revision with previous amount and no note. Idempotent retry; stale revision 409. Test wrong buyer, duplicate, unavailable and retired listing. |

The sensitive-price threshold remains an LI-01 Step 2 gate; the sensitive flag
is always computed from the approved category/threshold and never accepted
from clients. Owner review approved selection visibility for the listing owner
and participants in the selected conversation; it remains private from
discovery and other buyers.
The owner-reviewed 5-minute image-delivery URL lifetime is not authorization to
configure or use storage; LI-02 must verify the actual resource/policy and
cleanup path.

## Listings internal callables

| Import path and signature | Caller / state / retry / failures |
|---|---|
| app.domains.listings.public.query_available_listings(caller: CallerContext, request: AvailableListingQuery) -> Page[ListingSummary] | HTTP GET /listings and Search draft matching. Listings owns authoritative current-time predicate, FTS and indexes. Read-only; no cross-domain table access. |
| app.domains.listings.public.read_save_target(caller: CallerContext, listing_id: ListingId) -> SaveTargetResult | Search only before a new save; returns discoverable/not-found without exposing owner/private fields. Read-only. A race to unavailable after the check is allowed because saved references survive later unavailability. |
| app.domains.listings.public.read_saved_listing_summaries(caller: CallerContext, listing_ids: tuple[ListingId,...]) -> tuple[SavedListingState,...] | Search only with IDs it already read from the same caller's save page; max 100 IDs; returns approved current summary for non-retired unavailable records or content-free retired marker. No Search-table reads. Dependency error fails the page, not stale-cache success. |
| app.domains.listings.public.read_active_categories() -> tuple[Category,...] | Search create/edit validation; active code/label only, deterministic code order. |
| app.domains.listings.public.read_category_display(codes: tuple[CategoryCode,...]) -> tuple[CategoryDisplay,...] | Search only; resolves labels for existing assigned codes, including inactive catalogue values, without allowing new assignment. Read-only and deterministic; Listings failure returns dependency error, not missing labels. |

The other Listings entries in this table are public callables consumed by
Search. HTTP handler names in the preceding table are independently exposed
through the same `listings.public` module; the downstream Conversations
callables are owned by Conversations and appear below. Upload/image operations
are HTTP capabilities owned by Listings; they do not permit direct object-store
calls from Search or Conversations.

## Search HTTP operations

Search owns Wanted Request rows and saved references. Public Wanted Request
fields are the non-identifying set: request ID, title, description, category
code and label, optional budget, and created/updated instants. No author
ID/name or contact value is returned. “Public” means any eligible signed-in
marketplace member, including temporary accounts; anonymous reads are not
selected. This matches the approved Wanted Request clarification and
`contracts/search.md`.

| Method and route / operation ID | Input → output | Authorization, state, errors, retries and required cases |
|---|---|---|
| GET /wanted-requests — search_list_open_wanted_requests | page,page_size → PageResult[WantedRequestPublic] | Eligible regular or temporary caller; open and non-retired only. Order created_at DESC,request_id DESC. Read-only, safe empty page. Test both classes, closed exclusion, stable tie/page, Listings category-label dependency failure. |
| GET /wanted-requests/{request_id} — search_read_wanted_request | UUID path → `Union[WantedRequestPublic,WantedRequestOwnerView]` | Eligible caller. Public response for open; owner-only view may read own unavailable non-retired record. Others and retired content receive safe 404. Test owner/non-owner, open/unavailable/retired. |
| POST /wanted-requests — search_create_wanted_request | CreateWantedRequest{title,description,category_code,budget_paise?: Optional[int],operation_id} → WantedRequestOwnerView (201) | Eligible regular or temporary caller. Title 1–120, description 1–5000 code points, active category required. Omitted/null budget means unstated; zero is free-item intent; other values nonnegative whole-rupee paise. Actor from CallerContext. One Search transaction; duplicate operation returns original, conflicting reuse 409. Test field/ownership/category/dependency and omitted/null/zero. |
| GET /me/wanted-requests — search_list_my_wanted_requests | page,page_size → PageResult[WantedRequestOwnerView] | Eligible caller, own only including unavailable/non-retired. Order created_at DESC,request_id DESC. Read-only. Test cross-user isolation and paging. |
| PATCH /wanted-requests/{request_id} — search_update_wanted_request | UUID path; WantedRequestPatch{expected_revision,title?,description?,category_code?,budget_paise?: Optional[int],operation_id} → WantedRequestOwnerView | Author only, non-retired. Omitted preserves; budget null clears; title/description/category null invalid. Category check via Listings public interface. Search transaction and revision compare; stale 409, invalid 422, dependency 503. Test no-op/clear/invalid/stale/retry and non-owner. |
| PUT /wanted-requests/{request_id}/availability — search_change_wanted_request_state | WantedRequestStateChange{expected_revision,state: open or unavailable,operation_id} → WantedRequestOwnerView | Author only; reopen under same ID allowed unless retired. Close blocks new response conversations but existing thread access remains. Search locks own row and serializes response creation. Stale 409; retired reopen 409. Test concurrent close/create, duplicate, reset of closure anchor and non-owner. |
| POST /wanted-requests/draft-matches — search_match_draft_title | DraftMatchRequest{draft_title} → DraftMatchResult{items: ListingSummary[],has_more} | Eligible regular or temporary caller. Trimmed title 1–120 code points; title only, no budget/category implicit filter. Calls Listings available query; return first 20 by created_at DESC,listing_id DESC. Read-only/no draft history; no result does not block submission. Dependency failure 503. Test match/non-match, unavailable exclusion, limit and no persistence. |
| POST /wanted-requests/{request_id}/conversations — search_start_wanted_response | StartWantedResponse{operation_id} → ConversationStartResult{conversation_id,created} (201/200) | Eligible regular caller only. Search resolves author, locks its own open request and calls Conversations; responder is CallerContext user and need not own a listing. Pair uniqueness handles duplicate/concurrent retries. Closed request cannot create; retry resolves only same actor's already-existing pair via read-only Conversations lookup. No private contact returned. Dependency timeout 503 is ambiguous but pair retry is safe. Test temporary denial, duplicate, close/create race, closed/no-existing, existing after close and timeout. |
| GET /me/saved-listings — search_list_saved_listings | page,page_size → PageResult[SavedListingView] | Eligible caller; only caller-owned rows. Order saved_at DESC,listing_id DESC. Search reads its own IDs then calls Listings saved-summary resolver; unavailable non-retired records remain visible with current approved summary, retired records are content-free placeholders. Any dependency failure fails the page rather than serving stale details. Test private scope, availability transition, retirement privacy, pagination and Listings outage. |
| PUT /me/saved-listings/{listing_id} — search_save_listing | UUID path; SaveListingRequest{operation_id} → SavedListingAck | Eligible caller only. Listings must confirm currently discoverable non-retired target; Search writes its own row. Existing pair is successful no-op preserving original saved_at. If availability changes after check, saved reference remains valid. Missing/inaccessible target safe 404; dependency error 503 and no write. Test duplicate, race, invalid target and cross-user reads. |
| DELETE /me/saved-listings/{listing_id} — search_unsave_listing | UUID path → empty 204 | Eligible caller only; deletes only caller's row and succeeds if absent, regardless of current listing state. Search transaction; inherently idempotent. Test other user's row untouched, repeated delete and retired target. |

Search manages request revisions, saved rows and their transactions. It never
joins Listings tables. Category assignment validates active code through
Listings; public request display resolves the retained code/label through the
Listings display-only boundary even if a catalogue value later becomes
inactive. Open browse is separate from owner management. Search invokes
Conversations to create or look up Wanted Request response threads and read
minimal request-origin activity. The retirement-marker operation is gated on
separate human approval of the exact cleanup order. Conversations never calls
back into Search.

Search owns the HTTP operations above. It exposes no separate internal
business callable to another domain in this contract; for cross-domain work it
consumes public interfaces from Listings, Conversations, and Identity. It never
shares a session or accesses their tables:

| Import path and signature | Purpose |
|---|---|
| app.domains.listings.public.read_active_categories() -> tuple[Category,...] | Validate create/edit assignment; active codes only. |
| app.domains.listings.public.read_category_display(codes: tuple[CategoryCode,...]) -> tuple[CategoryDisplay,...] | Display historical assigned codes/labels, including inactive rows, without granting new assignment. |
| app.domains.listings.public.query_available_listings(caller: CallerContext, request: AvailableListingQuery) -> Page[ListingSummary] | Draft-title matches against authoritative current sale data/index. |
| app.domains.listings.public.read_save_target(caller: CallerContext, listing_id: ListingId) -> SaveTargetResult | Verify a new save is currently discoverable. |
| app.domains.listings.public.read_saved_listing_summaries(caller: CallerContext, listing_ids: tuple[ListingId,...]) -> tuple[SavedListingState,...] | Resolve only IDs from this caller's Search-owned saved page. |

Each callable is an in-process typed function; none is an HTTP route by
inference. All inputs/outputs above are typed models in the owning public
module. Dependency failures fail closed and do not turn into empty/success
responses.

## Conversations HTTP operations

Conversation payloads use opaque protocol-tagged encrypted envelopes. JSON
transports envelope and public-key bundle bytes as standard padded Base64; the
1–16 KiB key-bundle and 1–64 KiB envelope limits apply after decoding. This
does not choose an E2EE protocol, algorithm, nonce format, or client key-storage
method; CN-01 Step 2 must approve those before implementation. Plaintext
message, offer-note, or contact values are never accepted by these operations.

The actor and both members are derived from trusted server context and the
stored thread. `origin_kind` is `sale_listing` or `wanted_request`; only the
origin owner creates its own thread through its internal call below. Offer
filters apply only to Sale Listing threads. An explicit offer filter omits
threads without an offer; amount sorting retains them and places no-offer
threads last. List queries return only the caller's memberships, filter before
page slicing, and use stable tie-breakers. An origin ID or conversation ID
that is absent or outside the caller's membership yields a safe 404.

Shared response shapes are `ConversationSummary{conversation_id,origin_kind,
origin_id,initiator_user_id,caller_role,counterparty_user_id,last_activity_at,
own_last_read_sequence,unread_count,current_offer?}` where `caller_role` is
`initiator` or `origin_owner` and `current_offer` is an optional
`CurrentOfferSummary{offer_id,revision,amount_paise,status,updated_at}`;
`ConversationEntry{entry_id,sequence,kind,sender_user_id,created_at,envelope?}`;
and `CipherEnvelope{protocol_id,protocol_version,envelope_version,
sender_key_version,recipient_key_version,payload_base64}`. An entry after
purge retains its ordering/header metadata and sets a content-deleted marker
instead of an envelope. The server supplies actor/sender IDs, recipient IDs,
sequence and timestamps. Payload/base64 fields are required and nonempty;
unknown protocol metadata, null IDs, empty payloads, booleans-as-integers and
oversized decoded bytes are rejected. Client writes carry a required UUIDv4
`operation_id` only on operations whose row declares it; it is a UUIDv4.
Read operations and monotonic read acknowledgements do not need an
idempotency key. For keyed writes, equality means the same normalized typed
intent and the same opaque ciphertext bytes after transport decoding, without
decrypting or interpreting the payload. Once content is purged, its
content-free key/sequence marker remains reserved; any replay returns 409
`write_expired` and cannot recreate payload or notification work. The marker
does not retain ciphertext or a payload hash.

For query strings, omission uses the documented default, while empty strings,
null enum values, unknown enums, and min amount greater than max amount are
422 validation errors. All conversation member operations require a current
trusted context and membership: missing/expired/revoked is 401, authenticated
ineligible action is 403, and missing/nonmember private resources are safe
404. State/idempotency/revision races use 409, malformed or unsupported fields
use 422, throttling uses 429, and required dependency failures use 503, in the
shared error envelope. Safe field codes never echo submitted values.

| Method and route / operation ID | Input → output | Authorization, state, errors, retries and required cases |
|---|---|---|
| GET /conversations — conversations_list_mine | `view=initiated\|origin_owner\|all` (default all), `origin_kind?`, `origin_id?`, `counterparty_user_id?`, `offer_status?` (`submitted\|withdrawn`), `offer_min_paise?`, `offer_max_paise?`, `sort=last_activity_desc\|offer_amount_asc\|offer_amount_desc`, page/page_size → `PageResult[ConversationSummary]` | Eligible caller; only own memberships. Default sort `last_activity_at DESC, conversation_id DESC`; amount sort uses current offer amount then last activity DESC and ID DESC, with no-offer threads last. Filters run before pagination; amount bounds are nonnegative whole-rupee paise. Reads only conversation/membership/current-offer summary state; no origin-domain lookup. Empty filters omitted; empty/unknown values and invalid ranges are 422. Storage failure is 503. Tests verify owner/initiator views, ID substitution, filters, no-offer behavior, tie ordering, pages, and outages. |
| GET /conversations/{conversation_id} — conversations_read_summary | UUID path → `ConversationSummary` | Eligible member only. Reads thread/member summary and current authorized offer summary; never loads origin records. Same safe 404 for missing/nonmember. Read-only and no activity renewal. Tests participant, nonparticipant, expired/revoked account, and redacted response. |
| GET /conversations/{conversation_id}/entries — conversations_read_entries | UUID path; `after_sequence` nonnegative default 0; `page_size` 20 default, allowed 20/50/100 → `EntryPage{items,last_sequence,has_more}` | Eligible member only. Returns committed entries with sequence greater than cursor in ascending sequence; entries contain sender, kind, timestamp, and encrypted envelope or content-deleted marker. Empty page leaves cursor unchanged. No acknowledgement or activity write. Tests ordering, empty/end pages, limits, purge markers, retry cursor and nonmember denial. |
| POST /conversations/{conversation_id}/messages — conversations_submit_message | `MessageRequest{envelope: CipherEnvelope,operation_id}` → `ConversationEntry` (201; identical retry 200) | Eligible member only; text envelope only, 1–64 KiB opaque encoded bytes after transport decoding, supported protocol metadata and key versions must match this thread's members. Actor/sender and recipient are server-derived. Atomically stores the next sequence, advances participant activity, and writes/updates one reminder intent per unread episode: due 15 minutes after the first unread text, with later messages updating its target but not postponing due time. `(conversation_id,sender_id,operation_id)` identical retry before purge returns original sequence; conflicting reuse 409. After purge, a content-free marker returns HTTP 409 `conflict` with safe detail `{field: operation_id, code: write_expired}`; it never recreates payload or intent. 422 malformed/unsupported envelope, 503 database failure; no false success on partial transaction. Tests two-client exchange, bad/tampered/wrong-recipient metadata, limits, duplicate/concurrent send, notification atomicity, rollback and dependency timeout. |
| GET /conversations/{conversation_id}/read-state — conversations_read_state | UUID path → `ReadState{own_last_read_sequence}` | Eligible member only. Returns only the caller's watermark. Peer receipt, `read_at`, online/presence and unrelated activity are not exposed in the MVP; the server still reads the recipient watermark for notification suppression. Read-only/no timer renewal. Tests membership and watermark isolation. |
| PUT /conversations/{conversation_id}/read-state — conversations_acknowledge_read | `ReadAcknowledgement{last_read_sequence}` nonnegative → `ReadState` (200) | Eligible member only and only through the greatest committed sequence. Monotonic atomic max; older/equal repeats succeed without decreasing state. Does not count as participant activity and does not create a notification. Invalid/future sequence 422; unknown thread/nonmember safe 404. Tests repeated/out-of-order ack, future cursor, parallel ack and notification suppression read. |
| GET /conversations/{conversation_id}/offer — conversations_read_offer | UUID path → `Optional[OfferView]` | Eligible member only. Current offer/revision metadata and optional encrypted note envelope for Sale Listing origin; null for no offer or Wanted Request origin. Reads do not renew activity. Offers are never inferred as payment/reservation. Tests buyer/seller, no offer, wanted origin, note redaction boundaries, purge marker and nonmember denial. |
| GET /conversations/{conversation_id}/keys — conversations_read_member_keys | UUID path → `MemberKeyBundles{members:[{user_id,active_bundle,referenced_history_bundles}]}` | Eligible member only. Returns only current thread members' public bundles required by retained entries, with version/protocol metadata; never private keys. Read-only. Unknown/incompatible key reference fails safely instead of returning a misleading partial history. Tests member scope, historical references, replaced keys and missing bundle. |
| PUT /me/conversation-key — conversations_register_own_key | `PublicKeyBundleRequest{protocol_id,protocol_version,bundle_base64,operation_id}` → `PublicKeyBundleView` | Eligible caller registers/replaces only own public bundle. Decoded opaque bundle is 1–16 KiB. Conversations allocates increasing version and keeps referenced historical public versions while retained content needs them. Protocol allowlist and rotation/replacement behavior remain CN-01 Step 2 gates. Same operation retry is idempotent; stale/incompatible version 409; malformed size/metadata 422; storage failure 503. Test own-only, duplicate, race, replace/history retention and private-key absence. |
| GET /conversations/{conversation_id}/contact-options — conversations_read_contact_options | UUID path → `ContactOptionsView{email_available,phone_available,upi_available}` | Eligible member only. Conversations checks membership, then calls Identity for the caller's own availability flags; does not return values or the peer's options. Identity outage is 503 and never becomes empty options. Tests each member, nonmember, no-contact profile and dependency failure. |
| POST /conversations/{conversation_id}/contact-preparations — conversations_prepare_own_contact_share | `ContactPreparationRequest{fields: ContactField[1..3]}` → `SelectedOwnContacts` | Eligible member only; fields are nonempty, distinct, and supported. The UI submits only after explicit user confirmation; the server derives actor identity from CallerContext and never treats a client confirmation flag as authorization. Conversations calls Identity for only selected, current own values, returns them ephemerally to the actor for client-side encryption, and persists nothing. Removed value is a safe validation result; Identity failure 503. Redact body/value from logs and errors. Tests selected subset, actor binding, removed field, outage and no storage mutation. |
| POST /conversations/{conversation_id}/contact-shares — conversations_submit_contact_share | `ContactShareRequest{envelope: CipherEnvelope,operation_id}` → `ConversationEntry` (201; identical retry 200) | Eligible member only; server derives the other member and checks compatible protocol/key versions. Stores only encrypted envelope and content-free entry metadata; selected field labels remain inside ciphertext. Atomic sequence/share write, advances participant activity, retains a content-free idempotency marker, and creates no email intent. Server cannot prove ciphertext contains only the selected values. Identical retry before purge returns original; conflicting reuse 409; after purge any replay returns HTTP 409 `conflict` with safe detail `{field: operation_id, code: write_expired}`. Invalid envelope 422; DB failure 503. Tests actor/member/key binding, duplicate, tamper metadata, ciphertext-only persistence, retry after purge and partial failure. |

`PUT /conversations/{id}/offer` and offer-withdrawal routes are deliberately not
public Conversations HTTP operations. Browser offer commands use the
Listings-owned routes in the Listings table; Listings checks authoritative
availability/window/eligibility and then calls the Conversations persistence
function. This prevents a direct client path around the Listings command gate.

## Conversations internal callables

These are typed in-process calls exposed only through
`app.domains.conversations.public`. They are not FastAPI routes or OpenAPI
operations. User actors use trusted `CallerContext`; an origin owner supplies
server-resolved origin and member context. Notification worker context is
injected by the worker boundary and is not constructible from an HTTP model.
The exact worker authorization/configuration remains CN-03 work; a Python type
alone is not proof of authorization.

| Import path and signature | Allowed caller / state / retry / failures |
|---|---|
| `app.domains.conversations.public.open_or_create_listing_conversation(caller: CallerContext, request: ListingConversationContext) -> ConversationStartResult` | Listings only. `request` supplies the server-resolved listing ID and owner; caller is the buyer. Check both account eligibilities with Identity, reject self-conversation, persist unique `(listing_id,buyer_id)` thread and initial notification intent atomically. Initialize `last_activity_at` at creation. Existing pair is returned with `created=false` on retry/concurrent create; no duplicate notification. Identity/storage failure fails closed; timeout is ambiguous and retry by pair is safe. |
| `app.domains.conversations.public.open_or_create_wanted_conversation(caller: CallerContext, request: WantedConversationContext) -> ConversationStartResult` | Search only. Caller is a regular responder; request supplies the server-resolved open request ID and author. Check both participants through Identity, reject self-conversation, persist unique `(request_id,responder_id)` thread and notification intent. Search serializes against closure. Initialize `last_activity_at` on creation; existing pair returns with `created=false` and no duplicate notification. Identity/storage failure fails closed. |
| `app.domains.conversations.public.find_existing_wanted_conversation(caller: CallerContext, request: ExistingWantedConversationLookup) -> Optional[ConversationStartResult]` | Search only after an ambiguous retry or request closure. Read-only exact request/responder pair lookup; never creates a thread. Does not reveal any other pair. Identity/storage failure remains an error, not `None`. |
| `app.domains.conversations.public.check_listing_thread_participant(caller: CallerContext, request: ListingThreadParticipantCheck) -> ParticipantCheck` | Listings only for its seller-selection command. Check that caller is a member in the owner role and candidate is the other member of this exact Listing-origin thread. Return boolean only; no messages/offers. Wrong origin/member returns false or safe denial. Read-only/no activity renewal. |
| `app.domains.conversations.public.persist_listing_offer(caller: CallerContext, request: ListingOfferCommand) -> OfferView` | Listings only after its own serialized availability/window/eligibility check. Caller is the buyer; request carries server-resolved listing/thread/offer identity and command revision. Conversations rechecks thread membership and both account eligibilities, atomically appends revision/current pointer, advances participant activity and records the operation-specific idempotency outcome. Offer revisions create no email intent. No cross-domain transaction or Listings-state read. Identical retry returns original; stale revision 409; timeout is ambiguous and safe to retry by operation ID. |
| `app.domains.conversations.public.get_origin_activity(context: OriginOwnerContext, request: OriginActivityRequest) -> OriginActivityResult` | Listings/Search cleanup path only for its own origin kind. Request is `{origin_kind,origin_id}`; result is `{thread_count,latest_participant_write_at}`. Read every retained associated thread reference; latest time is null for zero threads. No thread/member IDs or content. Unknown/incomplete state or unavailable storage is a dependency failure, never zero activity. The server must inject a context for the owning origin; the Python type is not authentication. Call direction remains origin owner → Conversations. |
| `app.domains.conversations.public.mark_origin_retired(context: OriginOwnerContext, request: OriginRetirementCommand) -> RetirementMarkerResult` | Listings/Search only, after the concrete Step 10 lock/recheck/order approval. Request is `{origin_kind,origin_id,cutoff_utc,operation_id}`; result is `{marked_count,already_retired}`. Atomically checks every associated thread is at or before cutoff and marks it no-write while preserving participant access to retained history and content-free uniqueness. Idempotent by operation ID. Partial/unknown results fail closed. No implementation or destructive cleanup is authorized by this declaration. |
| `app.domains.conversations.public.claim_due_notification_intents(context: NotificationWorkerContext, request: NotificationClaimRequest) -> NotificationClaimResult` | CN-03 worker only. Request is `{now_utc,max_items}`; owner-reviewed max_items default 20, range 1–50. Result contains claims with intent/conversation/recipient IDs, event kind, due time, optional target sequence, fencing token and lease expiry. Atomically lease due intents; no address/message/contact/ciphertext. Lease duration/auth details remain CN-03 gates. Expired/unknown leases cannot authorize dispatch. |
| `app.domains.conversations.public.read_notification_dispatch_context(context: NotificationWorkerContext, request: NotificationDispatchCheck) -> NotificationDispatchContext` | CN-03 worker only, immediately before dispatch. Request is `{intent_id,lease_token,now_utc}`; result is `{decision,recipient_id?,target_sequence?}` where decision is send, suppress, or defer. Validate current fencing token/deadline, recheck authorized read watermark and due target, and return recipient UUID only when sending is authorized. Worker resolves destination through Identity; no address is copied into intent. Read/suppression does not advance activity. Unknown read state suppresses safely; Identity outage means no send and a retryable outcome. |
| `app.domains.conversations.public.record_notification_attempt(context: NotificationWorkerContext, request: NotificationAttemptResult) -> NotificationIntentState` | CN-03 worker only. Request is `{intent_id,lease_token,outcome,attempted_at}`; outcome is delivered, transient_failure, terminal_failure, or ambiguous. Fencing token guards state change; apply 5-attempt/backoff/24-hour policy and terminal 30-day retention. Do not persist provider body or address. Stale lease cannot overwrite a newer attempt; duplicate result is idempotent. Provider delivery is not exactly once and never rolls back the originating write. |

## HTTP, internal, and frontend connection map

An HTTP operation ID identifies the route declared in its owner's
`HTTP_OPERATIONS` registry. The eventual route handler belongs to that domain;
internal function names above are separate callable capabilities. Where HTTP
enters an origin owner's boundary, the handler calls the downstream public
interface as shown below. No browser operation calls another domain's private
code, and the graph has no cycle:

```text
Search → Listings → Conversations → Identity
   └──────────────→ Conversations
   └──────────────→ Identity
Listings ───────────────────────→ Identity
```

`POST /listings/{id}/conversations` maps to the Listings HTTP operation
`listings_start_conversation`, which calls
`app.domains.conversations.public.open_or_create_listing_conversation`;
`POST /wanted-requests/{id}/conversations` maps to Search's
`search_start_wanted_response`, which calls
`open_or_create_wanted_conversation` (or the read-only exact-pair lookup after
closure). Listing offer/withdrawal HTTP commands map to Listings and then
`persist_listing_offer`; seller selection maps from Listings to
`check_listing_thread_participant`. Listing and request retirement services
call `get_origin_activity`, then the separately gated `mark_origin_retired`.
Conversations never calls Listings/Search to revalidate origin state. Its
Identity calls are only eligibility, selected-own-contact, and
notification-recipient operations.

| Page | Frontend data/action interface | Server-authoritative state owner | Refresh and visible states |
|---|---|---|---|
| P01 `/sign-in` | Microsoft session create; temporary challenge, activation, login and reset challenge/reset; bootstrap with `GET /me` | Identity owns credentials, sessions, expiry, profile and account class | Show pending, generic acceptance, validation, rate-limit and dependency error. Successful session creation triggers `GET /me`; never trust a client account-class flag or store a returned secret in app state. |
| P02 `/auth/callback` | Read callback result, then `GET /me`; no provider-specific contract is frozen here | Identity owns session/callback validation | Pending/success/error; expired/revoked becomes signed-out. Exact cookie/CSRF/redirect details remain ID-01 review. |
| P03 `/` | Sale toggle calls Listings `GET /listings`; Wanted toggle calls Search `GET /wanted-requests`; both use numbered pages and stable owner sort | Listings owns sale availability/query/index; Search owns Wanted Requests | Loading/empty/denied/error; filter changes reset page to 1. Refresh current query on filter/sort change, mutation completion, or browser focus; do not infinite-scroll. |
| P04 `/listings/new` | Listings create and image-intent operations; read Identity session/capability for display, with server authorization decisive | Listings owns listing/images; Identity owns eligibility | Pending upload/create, validation, unavailable/dependency states. Refresh own listings/discovery after confirmed create; failed image confirmation never presents listing as published. |
| P05 `/listings/:listingId` | Listings detail/image delivery; Search `PUT /me/saved-listings/{id}`; Listings start-conversation command | Listings owns detail/availability/images; Search owns saved row; Conversations owns thread | Refresh listing detail on mutation result/focus; save action reflects server ack and refreshes saved state; conversation result navigates to returned conversation ID. Hidden/missing is safe not-found. |
| P06 `/listings/:listingId/edit` | Listings owner detail, full replacement, availability, and image-intent operations | Listings owns editable listing/image state | Keep edits pending until committed response; on 409 reload authoritative record; on image failure retain safe draft/error. Success refreshes detail, own-listings and discovery query. |
| P07 `/my/listings` | Listings `GET /me/listings`; Search own Wanted Request list/create/update/availability and draft-title matching; Conversations list link scoped by origin ID | Each origin domain owns its posts; Conversations owns thread/inbox | After each successful mutation, refetch only affected own list, discovery and match queries. Draft matching is read-only and never blocks create. Loading/empty/denied/error are feature states. |
| P08 `/saved` | Search `GET/DELETE /me/saved-listings`; Listings provides authorized summaries through its public resolver | Search owns saved rows; Listings owns current summary/availability | Refetch saved page after save/remove and on focus; unavailable item keeps current allowed summary, retired item is content-free. Listings dependency outage is visible error, not stale-success. |
| P09 `/my/conversations` | Conversations `GET /conversations`; query filters/sorts include origin, participant and current offer fields; fetch listing/request context separately from origin owner | Conversations owns thread, membership, offer summaries; Listings/Search own origin context | Refetch inbox after a thread/message/offer/share mutation and on active-page polling/focus. No-offer threads stay in amount-sorted results at the end. Loading/empty/denied/error; filter and stable numbered pagination. |
| P10 `/my/conversations/:conversationId` | Conversations summary, entries, own key registration/member-key lookup, read-state, message and contact-share operations; offer/selection mutations go through Listings | Conversations owns entries/read state/keys/offers/shares; Listings owns availability/selection; Identity owns source contacts | Read entries incrementally by committed sequence; acknowledge only after display. Fetch immediately on focus and after writes; poll every 2 seconds while visible/active, suspend while hidden, and back off on failures. The short interval leaves delivery/render time within NFR-05's 5-second target; acceptance still requires measurement. Refresh entries/inbox after committed writes. No optimistic success on ambiguous commit; retry with the same operation ID. Show expired-key, denied, conflict, validation and dependency states without sensitive payloads. |
| P11 `/account/contacts` | Identity read/set/delete own contacts | Identity owns contact values; Conversations owns only explicit encrypted shares | Refetch own contacts after update/delete. Return to conversation preparation only after explicit selection/confirmation; never populate general profile/session responses with contact values. |
| P12 `/wanted/:requestId` | Search read public request; eligible regular caller invokes Search response-conversation operation | Search owns request visibility/availability; Conversations owns resulting thread; Identity owns eligibility | Safe not-found for hidden/closed; submission shows pending/result/error. Existing pair is reopened on retry/after close; new response after closure is denied. Success navigates to conversation ID. |

All view state is disposable client cache; server responses remain authoritative.
After a successful mutation, the initiating component consumes the returned
typed result and tells its page composition which affected queries to refresh;
there is no global cross-feature event bus. A `401` clears session state and
returns to sign-in, `403` shows denied, safe `404` shows unavailable/not found,
`409` reloads the affected authoritative record, `422` binds safe field codes,
`429` respects `Retry-After`, and `503` offers a bounded retry. Do not include
request bodies, keys, contacts, plaintext, ciphertext, or provider details in
frontend logs or error presentation.

The two-second active polling interval is a concrete recommendation, not a
product decision: it targets the PRD NFR-05 requirement that at least 95% of
messages appear within five seconds while both clients have the thread open.
The focused NFR test must measure sender-submit through recipient-display; the
interval alone is not evidence of NFR success.

## Step 10 cross-contract review and cleanup-order proposal

This coordinator audit reconciles the combined registry with the four domain
contracts, approved decisions, schema, and frontend map. The user reported that
affected domain owners reviewed and approved these documents on 2026-10-20; no
person is inferred from a role label. Separate human approval of the exact
destructive cleanup mechanism remains required before implementation.

| Surface | Audited contract / recommendation | Affected review |
|---|---|---|
| Call graph | Preserve Search → Listings → Conversations → Identity, with Search → Conversations/Identity, Listings → Conversations/Identity, and Conversations → Identity. Identity calls no domain; Conversations never calls Listings/Search. No cycles or private-table/session sharing. | B, C, D; approved (user-reported) |
| Wanted Request visibility | Signed-in eligible regular and temporary members; anonymous access excluded. Return only request ID, title, description, category code/label, budget and timestamps; no author identity/contact. | C, D; approved (user-reported) |
| Retries | Keep operation-specific behavior. No arbitrary automatic write retries or universal idempotency store; same operation key + same intent returns the prior result, conflicting reuse is 409; ambiguous cross-domain writes use only the declared key or stable-pair lookup. | All affected domains; approved (user-reported) |
| Identity/contact | Keep the trimmed display name (1–80 code points), email ≤254 chars, E.164 phone, and bounded ASCII UPI VPA validation. Same-key OTP retry does not send again; deliberate resend needs a new operation ID. Do not automatically resend after an ambiguous provider outcome. | A; approved (user-reported) |
| Participant identity | Keep counterparty UUID for scoped conversation filtering only. Do not add global profile/name lookup; render role and origin context. Historical offer revisions remain participant-only; only current offer summary is exposed by the summary operation. | A, D; approved (user-reported) |
| Selection / receipts | Selection state is visible only to the listing owner and the participants in the selected conversation, never public discovery or other buyers. Expose only the caller's read watermark; do not expose peer read sequence, timestamps, or presence. | B, D; approved (user-reported) |
| Images / transport | Use five-minute image delivery URLs, with actual signing/storage behavior left to LI-02. Use standard padded Base64 for opaque encrypted envelope and public-key bundle bytes; crypto protocol/library remains CN-01 Step 2. | B, D; approved (user-reported) |
| Polling | Keep immediate fetch on focus and after writes, 2-second active polling, pause while hidden, and back off after failure. A 5-second interval would consume the full NFR-05 delivery budget before network/render time; 2 seconds is the better starting point, subject to measurement. | D; approved (user-reported) |
| Internal contexts / notifications | Construct origin-owner and worker contexts only in server composition/worker wiring, never bind them from HTTP. Check origin kind against caller capability. Keep notification claim default 20/max 50; lease duration, worker identity and dispatch recovery stay CN-03 implementation gates. | A, D; approved (user-reported) |

### Proposed origin-retirement sequence

This is a reviewable design only; it does not authorize cleanup code or a
destructive run.

1. Listings or Search starts a short transaction on its own origin row. After
   rechecking the approved continuous-retirement predicate, it sets a proposed
   nullable `retirement_pending_operation_id` to the operation UUID. A
   non-null marker blocks new origin threads/edits/reopen and hides the origin
   from discovery; the transaction commits before any Conversations call. The
   marker clears with `retired_at` after successful content cleanup. No
   cross-domain transaction or shared database session is used.
2. The origin owner calls `get_origin_activity`. Unknown/incomplete results or
   dependency failures fail closed and leave content intact.
3. The origin owner calls `mark_origin_retired` with the stable operation ID.
   Conversations locks every associated thread in UUID order, rechecks all
   participant-write times against the cutoff, and atomically marks all
   eligible threads no-write. If any thread is too recent, none are marked.
   A repeat with the same operation ID returns the recorded outcome. The
   all-or-none lock is the simplest safe MVP design; owners should reassess it
   if measured thread counts make the transaction too large.
4. If activity is too recent, the origin owner clears the pending operation ID
   without deleting content. If the result is ambiguous, keep the origin
   pending/hidden and retry or look up the same operation; never unhide or
   delete on an unknown outcome. This avoids cross-domain rollback.
5. Only after a confirmed Conversations marker does the owning domain clear
   its own origin content in its own transaction. Image objects are handled
   separately; cleanup metadata remains until deletion/absence is confirmed.
6. Conversations purges history under its own thread lock and final inactivity
   recheck. Suppress all nonterminal intents that cannot remain deliverable and
   clear entry targets before payload cleanup; remove contact-share links
   before their entries' payloads; set `offers.current_revision = NULL` and
   `history_deleted_at` before deleting revisions; then remove encrypted
   payloads and mark entries content-deleted.
   Preserve entry sequence/operation markers, unread-episode/replay guards,
   offer ID/pair/revision counter, thread, members, and origin uniqueness.
   Terminal notification rows expire only after 30 days, with replay protection
   retained as required. Use restrictive FKs and no broad cascade.

The user reports that domain owners reviewed the cleanup document. Human
approval of this exact destructive cleanup mechanism/order remains required
before implementation. No provider setup, cloud change, destructive execution,
or domain feature code is authorized here.
