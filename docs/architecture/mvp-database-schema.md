# MVP database schema proposal

**Origin:** PD-08 Step 2, Mohit (C), 2026-10-18.

**Current status (2026-10-20):** The user confirmed PD-08 acceptance, including carried owner/runtime checks, complete on 2026-10-19 and the previously deferred Linux AMD64/macOS checks passed elsewhere on 2026-10-20 (Asia/Kolkata). Exact other-machine architectures, commands and raw results are not retained here. The detailed review queue below records the original design/checklist scope; its historical pending wording is not a current PD-08 blocker. DL-00 owners still revalidate domain contracts against these decisions.

**Current writer:** Mohit on `predomain-database`. **Primary peer:** Suraj (B).

This document proposes the complete MVP data inventory and its relational boundaries. It creates no tables or domain behavior. Names, types, constraints and indexes below are proposals unless identified as already approved. The review gates at the end must be resolved before dependent initial migrations. After approval, versioned migrations in `database/migrations/` become the executable schema source; this document explains their intent and must stay consistent with them.

**Step 3 continuation, authorized by Mohit:** Mohit explicitly directed proceeding before remaining affected-owner review, allowing later corrections while staying within Stream 3 paths. Migrations live in [database/migrations](../../database/migrations/), with combined expected dbmate head `20261025013000`; [database/README.md](../../database/README.md) records the files and verification provenance. The additive LI-01 migrations add seller-command results, create-retry receipts, the selected-conversation reference and verified-image metadata. Migration `20261020142319` adds retirement retry/marker storage and removes cross-domain business-table access from the named triggers. The selected-conversation reference and retirement interface still require affected-owner review; image metadata awaits LI-02 verification-flow implementation. The sequencing exception did not waive required checks. The user later confirmed the carried PD-08 checks and owner acceptance complete. Historical platform evidence and its limits are recorded in the work log. This does not accept future domain contracts, cryptographic implementation, or cloud action.

Identity migrations additionally implement reviewed profile/contact bounds, OTP
transactions and session/login state; original migration histories are retained.

## SE-01 hybrid embedding addition — prepared migration

The [Listings-owned semantic storage/write plan](semantic-listing-storage.md)
proposes pipeline/generation/chunk tables, own-schema invalidation/completeness
triggers, deterministic source hashing and exact native-array scoring. Its
migration is now prepared at `20261024153316`, following Mohit's explicit plan/
derived-content implementation approval. Its scoped native migration/adapter
checkpoint subsequently passed on fresh private test databases; existing/shared/
production data remain untouched and exact-code review/final integration remain
pending. This annotation changes no existing
migration and does not mark the new objects installed or accepted.

## Sources and approved boundaries

**Continuation phase:** Mohit transferred unfinished PD-08 checks/reviews to
pre-domain integration on 2026-10-18. The
[handoff decision](../decisions/database-integration-handoff.md) preserves original
checkpoint IDs and outstanding real checks/affected-owner acceptance. Native
results remain verified; the phase change does not accept this schema or waive
PD-19/PRE-00 gates. Integration coordinates the continuation with Mohit's handoff.

- [Submitted PRD](../source/ICC_Project_PRD_FINAL.pdf), especially FR-01–17 and §§5–6; [product reference](../product/product-reference-and-architecture-decisions.md).
- [Shared conventions](../conventions/shared-conventions-and-cross-domain-contract-rules.md), [domain tasks](../tasks/domain-task-list.md), and [PD-08 procedure](../tasks/pre-domain-task-list.md).
- Mohit's approved directions: [Listings-owned search](../decisions/search-listing-data-boundary.md), [wanted conversation lifecycle](../decisions/wanted-conversation-lifecycle.md), [private payloads](../decisions/private-offer-and-contact-payloads.md), [notification durability](../decisions/notification-intent-durability.md), and [encryption storage](../decisions/encryption-storage-boundary.md).
- Step 2 Identity direction: [application-owned OTP and session storage](../decisions/temporary-authentication-storage.md), approved by Mohit; affected-owner review and detailed security policy remain pending.
- Step 2 Listings/Search direction: [item category, availability window and saved visibility](../decisions/listing-discovery-semantics.md): Mohit approved the original availability/saved rules; the PR #5 reviewer corrected item-category terminology. Affected-owner schema review remains pending.
- Step 2 price optionality: [required seller price and optional buyer budget](../decisions/asking-price-and-budget.md), confirmed by Mohit.
- Step 2 catalogue and limits: [initial category/condition values and text/image limits](../decisions/catalogue-and-listing-limits.md), approved by Mohit; affected-owner schema review remains pending.
- Step 2 offers: [single current offer with revisions/withdrawal and separate selection](../decisions/offer-lifecycle.md), approved by Mohit; affected-owner review remains pending.
- Step 2 privacy lifecycle: [retention windows and minimal integrity records](../decisions/private-data-retention.md), approved by Mohit; affected-owner cleanup/reference review remains pending.
- Step 2 notification behavior: [new-conversation email, 15-minute unread episodes and bounded retry](../decisions/notification-delivery-policy.md), approved by Mohit; affected-owner transaction/delivery review remains pending.
- Step 2 remaining lifecycle package: approved activation/reset/default/offer transitions recorded in the relevant decisions, plus [upload staging](../decisions/image-upload-staging.md), [English search configuration](../decisions/search-listing-data-boundary.md), and [origin retirement](../decisions/origin-retirement.md). All affected-owner review gates remain explicit.

Approved: UUIDv4 identifiers; aware UTC instants; integer INR paise restricted to whole rupees; separate Sale Listing and Wanted Request objects; one buyer/listing conversation; one responder/request conversation; participant-only private content; client-only private keys; asynchronous email; and authoritative seller availability/selection. Closure prevents new wanted-response conversations while preserving existing authorized participant access.

Search uses a Listings-owned public query boundary with native PostgreSQL full-text indexes. Sharing a database and foreign keys does not grant private-table access. No Search-owned listing projection is proposed. Public query signatures remain DL-00 outputs.

## Ownership and notation

Propose four PostgreSQL schemas to make ownership visible: `identity`, `listings`, `search`, and `conversations`. These are namespaces, not separate deployments or proof of authorization. Migration tooling has coordinated DDL access; application access follows reviewed public domain interfaces. Runtime database-role enforcement is a separate reviewed integration decision.

| Namespace/area | Authoritative writer | Required reviewers |
|---|---|---|
| `identity` accounts, authentication records, private contacts | Aditya (A) | Rahul (D); contact consumers |
| `listings` listings, catalogue, images, buyer selection, query indexes | Suraj (B) | Mohit (C), Aditya (A), Rahul for selection |
| `search` Wanted Requests and saved listings | Mohit (C) | Suraj (B), Rahul for request conversations |
| `conversations` origins, participants, keys, messages, offers, disclosures | Rahul (D) | Aditya (A), Suraj for selection |
| `conversations.notification_intents` | Conversations | CN-03 delivery owner, Conversations producer owner, and Identity recipient/privacy reviewer |

Notation for every table below:

- Every listed column is `NOT NULL` unless followed by `?`. Each table has the explicitly stated primary key; a UUID entity `id` is generated using the approved application helper, not accepted as an authorization claim. No PostgreSQL UUID-generation extension is assumed.
- `instant` means `timestamptz(6)`, with UTC connection/display settings. PostgreSQL retains the instant, not the original zone. The application rejects naive timestamps before binding; a database timestamp type alone cannot enforce that input rule.
- `created_at`/`updated_at` are server-controlled instants. `updated_at` is included only where listed; it is not a concurrency token. Proposed mutable resources use a positive `revision bigint` for compare-and-update semantics.
- `money` means `bigint`, constrained to a nonnegative multiple of 100. Mohit approved zero asking prices, zero offers and explicit zero budgets; zero budget means seeking a free item, while a missing budget means no amount stated. Upper product limits still need review. No floating-point storage or implicit rounding.
- Required human-readable text must contain non-whitespace content. Exact length limits, normalization and catalogue values require review rather than arbitrary schema defaults.
- Status columns are proposed text values with named `CHECK` constraints, rather than PostgreSQL enum types. Final sets and transitions require approval; a status check alone does not implement transition authorization.
- Foreign keys are explicitly named below. Default deletion proposal is `ON DELETE RESTRICT` to prevent accidental cross-domain cascades. Mohit approved the finite content/authentication retention windows below; affected-owner cleanup ordering and any explicit FK exceptions still require review. Restricted FKs are not indefinite-retention approval.
- Indexes supporting a primary/unique key are supplied by that constraint. Additional indexes below are proposed for actual access patterns; query-plan checks occur against real PostgreSQL in Step 6 and domain verification.

## Identity records — FR-01–03, FR-12, FR-16

| Table / primary key | Columns | Constraints and access indexes |
|---|---|---|
| `identity.users` / `id uuid` | `account_class text`, `status text`, `display_name text?`, `created_at instant`, `activated_at instant?`, `expires_at instant?`, `revoked_at instant?`, `profile_removed_at instant?`, `revision bigint` | Class `regular`/`temporary`; lifecycle pending/active/revoked. Optional display name is at most80 Unicode code points; null/empty semantics match the public contract. Revoked status is paired with a non-null `revoked_at` at/after creation; other statuses have no revocation timestamp. Active temporary accounts require original activation and expiry instants; regular accounts do not inherit temporary expiry. Profile removal clears display/contact content but retains approved UUID references; this is not an anonymity claim. Index temporary expiry for lifecycle maintenance. |
| `identity.external_identities` / `id uuid` | `user_id uuid`, `provider text`, `issuer text`, `subject text`, `created_at instant` | FK user; unique `(provider, issuer, subject)` for concurrent sign-in deduplication; index `user_id`. Provider mapping ID, owner UUID, provider/issuer/subject tuple and creation time are immutable after insertion; harmless no-op updates remain allowed. Persist verified stable identifiers, never raw Microsoft tokens. |
| `identity.contacts` / `user_id uuid` | `email text?`, `phone text?`, `upi_id text?`, `updated_at instant` | PK/FK user. Private own-contact source; absence differs from an empty value. Present fields are nonempty and at most254 code points, matching the public request bound. Own-contact service validates normalization/format. No general profile/search exposure. Source contacts are available to authorized Identity operations; the approved encrypted conversation share does not imply source-contact E2EE. |

Mohit approved first successful initial email verification as activation, with expiry exactly 14 × 24 hours later in UTC. Set the original activation/expiry once; registration/password entry, login, resend, repeated verification, reset and profile edits cannot extend it. A must review the stable normalized-login/enrollment guard implementation before migration acceptance. Authorization compares the current clock/account state even before maintenance marks expiry; no database `CHECK(now())` is proposed.

Mohit selected application-owned OTP challenges and sessions for the current MVP proposal. Include the following tables; their precise verifier/token design and security policies still require Identity/security review before dependent migrations. `external_identities` remains the verified external-provider mapping, not a substitute for local challenge/session state.

| Table / primary key | Proposed columns and constraints |
|---|---|
| `identity.temporary_credentials` / `user_id uuid` | PK/FK users; `login_email_key text` unique, `password_hash text`, `created_at instant`, `password_changed_at instant`, `revision bigint`. Required normalized verified-target identifier is private authentication data and separate from editable shareable contacts. Only temporary users may have this credential; enforce class binding in the reviewed service/constraint design. Encoded password hash includes its algorithm/parameters/salt; no plaintext or reversibly encrypted password. Exact hash scheme and identifier normalization await security review. |
| `identity.sessions` / `id uuid` | `user_id uuid` FK users; `token_digest bytea` unique; `created_at instant`, `expires_at instant`, `revoked_at instant?`. Expiry follows creation. Index user/revocation and expiry for authorized session management/cleanup. Never raw session tokens. Revocation and current account eligibility remain mandatory service checks. |
| `identity.otp_challenges` / `id uuid` | `user_id uuid?` FK users; `target_lookup_digest bytea`, `verifier bytea`, `purpose text`, `created_at instant`, `expires_at instant`, `consumed_at instant?`, `attempts integer`, `resend_count integer`, `last_sent_at instant?`. Purpose restricted to `initial_verification` or `password_reset`; password reset requires an existing user. Positive lifetime, nonnegative counters, and consistent consumption time. Index target/purpose/creation and expiry. Never raw OTPs. Exact target mapping/protection and verifier scheme remain security-review gates. |
| `identity.temporary_enrollments` / `id uuid` | `login_digest bytea`, `digest_key_version text`, `first_activated_at instant`, `original_expires_at instant`, `user_id uuid?`. Minimal verified-enrollment guard retained for service lifetime; unique normalized identity must remain enforced across key versions. Proposed user FK exception `ON DELETE SET NULL` preserves the guard after account retirement. Index key-version/digest lookup; final key rotation, unique-index/concurrency design and canonical 14-day expiry calculation require Identity/security review. No raw email, password or OTP. |

OTP consumption and attempt accounting must be atomic under concurrent verification; a consumed challenge cannot create multiple activations/sessions. Enforce resend/attempt policy across replacement challenges where required, not just per-row counters. The schema does not assume a plain hash protects a short OTP: a reviewed keyed-verifier design and separately managed secret may be required. The target digest does not itself provide a delivery address; the approved Identity workflow must resolve the private target from its authorized source or explicit request without logging or copying it into diagnostics.

Mohit selected password-based normal sign-in for temporary users; email OTP is limited to initial verification and forgotten-password reset. Bind verification to its exact challenge target/purpose and consume it once. A successful reset atomically updates the password hash, consumes its challenge and revokes every existing session; require normal password sign-in afterward. Review locking with concurrent sign-in/reset before implementation. An initial-verification OTP cannot serve as a reset OTP or routine login credential. Reset/login/resend cannot restart the original account lifetime or bypass expiry/revocation. No password credential is added for Microsoft-authenticated regular users. Provider credentials, approved IISc domains and Microsoft issuer/audience values belong in canonical configuration/access records, not user tables or guessed fixtures.

## Listings and catalogues — FR-04–07, FR-14–15, FR-17

| Table / primary key | Columns | Constraints and access indexes |
|---|---|---|
| `listings.categories` / `id uuid` | `code text`, `label text`, `sensitive_category boolean`, `active boolean`, `created_at instant` | Unique immutable `code`; Mohit-approved catalogue below includes mobile-phone/laptop classification; affected-owner review pending. |
| `listings.conditions` / `code text` | `label text`, `active boolean` | Mohit-approved shared listing-condition vocabulary below; affected-owner review pending. |
| `listings.sale_listings` / `id uuid` | `owner_id uuid`, `title text?`, `description text?`, `category_id uuid?`, `condition_code text?`, `asking_price_paise money?`, `negotiable boolean?`, `pickup_area text?`, `available_from instant`, `available_until instant?`, `availability text`, `proof_available boolean?`, `selected_buyer_id uuid?`, `selected_conversation_id uuid?`, `created_at instant`, `updated_at instant`, `retirement_eligible_since instant?`, `retirement_pending_operation_id uuid?`, `retirement_pending_cutoff_utc instant?`, `retired_at instant?`, `search_vector tsvector`, `revision bigint` | Pickup area is optional on live rows; the other content fields are physically nullable solely for retirement. A named live-row check requires every mandatory field when `retired_at IS NULL`, including price and negotiability. Retired rows clear content/category/price/condition/selection/proof and are unavailable. FKs owner/selected buyer/selected conversation/category/condition; buyer and conversation are both set or both clear, and selected buyer differs from owner. Availability available/unavailable; end follows start. Pending operation ID and cutoff are paired so Listings can retry the exact Conversations request after a process restart. Public reads and commands hide pending rows; the owner's management list keeps retained pending listings visible. Stored generated English vector; indexes below. The selected conversation is populated only after validation through Conversations' public participant-check operation. |
| `listings.owner_command_results` / `(listing_id, command_kind, operation_id)` | `listing_id uuid` FK sale listings; `command_kind text` (availability/selection); `operation_id uuid`; `request_payload jsonb`; `result_payload jsonb`; `created_at instant` | Listings saves the validated request and original response atomically with seller availability/selection changes. Same key and request replays the saved response; changed request with the same key conflicts. An after-retirement trigger deletes these saved results in the retirement transaction. |
| `listings.create_command_results` / `(owner_id, operation_id)` | `owner_id uuid` FK user; `operation_id uuid`; `listing_id uuid` unique FK sale listing; nullable `request_payload jsonb`; nullable `result_payload jsonb` | Listings stores the validated create request and original `ListingDetail` atomically with listing/image publication. Retirement clears both content-bearing payloads but keeps owner, operation and listing IDs. A later retry sees the retained key and must safely conflict without revealing old content or creating a second listing. This post-retirement API behavior awaits affected-owner review. |
| `listings.image_uploads` / `id uuid` | `owner_id uuid`, `object_key text`, `state text`, `created_at instant`, `expires_at instant`, `confirmed_at instant?`, `failure_code text?`, `confirmed_media_type text?`, `confirmed_size_bytes bigint?`, `cleanup_retry_after instant?` | FK owner, unique controlled object key; pending/confirmed/failed/expired states. Original unattached deadline is creation +24 hours; state/timestamp checks. Actual media type and size are nullable until LI-02 verifies the object, must be set or clear together, and are limited to JPEG/PNG/WebP and 1–10 MiB. Safe failure code only, no provider text. `cleanup_retry_after` delays only an object whose S3 deletion failed or had an unknown outcome. Index owner/state, state/expiry and expiry/ID with retry time for lookup and bounded cleanup. |
| `listings.images` / `id uuid` | `listing_id uuid`, `upload_id uuid`, `object_key text`, `position integer`, `media_type text`, `size_bytes bigint`, `created_at instant`, `retired_at instant?`, `cleanup_retry_after instant?` | FKs listing and confirmed upload; upload ID and object key unique; nonnegative position, size 1–10 MiB and approved media types. Unique live `(listing_id, position)`; 1–8 usable images for a live listing. Upload/listing owner and object-key agreement require reviewed cross-row checks. Retired image rows are cleanup metadata until actual object deletion/absence is confirmed, then removed with their intent. The cleanup due index orders retired images by retirement time and ID and carries the retry timestamp. |

Mohit confirmed that the seller must supply an asking-price value. The mandatory live-row constraint enforces non-null `asking_price_paise` even when separate `negotiable` is true. Physical nullability only permits trusted content retirement; it does not permit a missing price on create/edit/live rows. Zero remains a valid asking price.

### Initial catalogue and field limits — Mohit-approved

Mohit approved the following Step 2 catalogue and limits; no seed data or constraints have been implemented yet. Use stable catalogue codes with editable labels and an active flag, rather than PostgreSQL enums. Listings (B) owns category/condition writes and the public catalogue read/validation boundary; Search (C) uses the same categories for Wanted Requests and discovery. Code changes or sensitive-category reclassification require affected-owner review. Deactivation prevents new assignment without deleting or invalidating historical references; deletion remains restricted.

| Category code | Display label | Sensitive-category flag |
|---|---|---|
| `mobile_phone` | Mobile phones | true (FR-17) |
| `laptop` | Laptops | true (FR-17) |
| `electronics` | Other electronics | false |
| `furniture` | Furniture | false |
| `books` | Books and study materials | false |
| `bicycles` | Bicycles | false |
| `appliances` | Appliances | false |
| `other` | Other | false |

The mobile-phone/laptop branches must remain explicit for FR-17. A false category flag does not exempt a listing from the independent price-threshold rule. Category assignment is a seller declaration; no platform verification is implied.

| Condition code | Display label | Seller declaration |
|---|---|---|
| `new` | New / unused | Seller declares the item unused. |
| `like_new` | Like new | Seller declares prior use with minimal visible wear. |
| `good` | Good | Seller declares normal signs of use. |
| `fair` | Fair | Seller declares substantial visible wear. |

These are seller-declared condition labels, not a platform quality or functionality guarantee. The description must still accurately disclose defects; a condition label does not establish inspection or verified working order.

| Field | Proposed limit | Enforcing owner/boundary |
|---|---|---|
| Sale Listing / Wanted Request title | 1–120 Unicode code points after outer whitespace trimming | Listings/Search API and database `char_length` check |
| Sale Listing / Wanted Request description | 1–5,000 Unicode code points after outer whitespace trimming | Listings/Search API and database `char_length` check |
| Sale Listing pickup area | Optional; null when not provided, otherwise 1–120 Unicode code points after outer whitespace trimming | Listings API and database `char_length` check |
| Usable listing images | 1–8 per publishable listing | Listings publication/image lifecycle; reviewed serialized/deferred count check |
| Each accepted image | At most 10 MiB (10,485,760 bytes), positive size | LI-02 actual-object validation plus metadata check |
| Accepted image media | JPEG (`image/jpeg`), PNG (`image/png`), WebP (`image/webp`) | LI-02 validates actual content, not filename/client MIME alone |

Count limits apply to final retained usable references, including concurrent additions/removals; pending-upload quotas need a separate LI-02 review. API validation must match database bounds and preserve internal whitespace. Unicode code-point length differs from rendered glyph/grapheme count; do not impose byte-count limits on text under these names. The final migration must select a consistent outer-whitespace normalization rule; PostgreSQL's default trim behavior alone is not a full Unicode whitespace validator. No ciphertext/plaintext-note limits, image decoding/dimension policy, money cap or sensitive-price threshold is selected by this proposal.

Mohit's decision is recorded in the [catalogue decision](../decisions/catalogue-and-listing-limits.md). B/C affected-owner schema review remains pending. Seed data and exact length/count/type constraints belong to the reviewed migration step; no implementation or runtime acceptance is claimed here.

Only verified usable image references belong in `images`. Proposed publication invariant: a committed publishable listing has at least one image. A coordinated transaction inserts the listing and accepted image references; a deferred constraint trigger checks at commit. Image removal must also check the invariant. Step 3 must specify the locking protocol that prevents concurrent removal of the last images; a count query without serialization is insufficient. External object existence/upload authorization still require LI-02 checks and cannot be proved by a foreign key.

Mohit approved durable `image_uploads` for pending/confirmed/failed/expired state. Confirm actual owner/object/type/size before attachment. Pending or confirmed-but-unattached intents expire after 24 hours; remove abandoned metadata within a further 24 hours after expiry/failure once object cleanup is safe. Cleanup locks/rechecks attachment, makes expired unlinked intents terminal before contacting S3, and retains object keys until deletion/absence is confirmed. Each bounded pass defaults to 100 records and caps at 500; failures retain their rows and get a five-minute retry delay so older untried work can proceed. Confirmed attached records remain with their usable image until retirement. No public draft listing is introduced; B reviews the exact cross-row/locking constraints before migrations.

Mohit-approved discovery time semantics: require `available_from` (default server creation instant if omitted) and allow nullable `available_until`, with end strictly after start. Discovery requires a non-retired listing, owner eligibility, `availability = 'available'`, `available_from <= request_time`, and `(available_until IS NULL OR request_time < available_until)`. Reaching the end excludes discovery without rewriting seller status. Owners may edit valid windows or toggle state; neither reassigns selected buyer. Saved references survive unavailability/window expiry and later point only to content-free retired origins. Selecting a buyer does not change availability, reserve the item, or verify payment/handover. Affected-owner transaction review remains pending.

Sensitive flags are derived from current asking price and reviewed category configuration, with a strict `price > threshold` comparison. Propose no persisted stale boolean: compute through the Listings public read/query interface. The provisional ₹5,000 threshold and Listings ownership are recorded in the [sensitive-purchase threshold decision](../decisions/sensitive-purchase-threshold.md); runtime configuration is LI-01 work and the value may be changed through review. Proof declarations remain unverified statements.

Proposed indexes owned by Listings:

- B-tree `(owner_id, created_at DESC, id DESC)` for own-listing management.
- B-tree `(availability, created_at DESC, id DESC)` and `(availability, asking_price_paise, id)` for stable recency/price discovery; reverse scans may serve the reverse sort. Review exact descending tie direction with DL-00.
- B-tree category/condition FK lookups and `(selected_buyer_id)` where selection lookups require it. Do not add every possible filter combination without query-plan evidence.
- GIN over the stored generated title/description vector using explicitly named `pg_catalog.english`, approved by Mohit. Use null-safe concatenation (retired content yields an empty vector), and the same explicit configuration in query normalization. The earlier `simple` suggestion was never accepted. This is reviewed index intent, not a relevance/NFR result.
- B-tree on `retirement_eligible_since` for bounded inactive-content selection; final checks re-evaluate every associated thread's `last_activity_at` under the coordinated retirement lock.
- Availability time boundaries remain predicates evaluated at query time; no partial index using a volatile current-time predicate.

Reviewer-approved **item category** means the kind of item, represented by the existing Listings-owned category catalogue and `category_id` references. It is separate from the **Sale Listings / Wanted Requests** discovery view, which composes distinct public domain objects. Free items remain Sale Listings with zero asking price. This corrects the earlier contrary interpretation; no second category filter, duplicate column or free-item table is added. DL-00 finalizes public filter spelling while preserving this distinction; other filters apply only to fields supported by the selected view.

## Wanted Requests and saved listings — FR-08–09

[Approved category-reference correction](../decisions/wanted-category-code-reference.md)
aligns wanted storage with the code-based public catalogue. Existing sale-listing
UUID references are unchanged.

| Table / primary key | Columns | Constraints and access indexes |
|---|---|---|
| `search.wanted_requests` / `id uuid` | `author_id uuid`, `title text?`, `description text?`, `category_code text?`, `budget_paise money?`, `status text`, `created_at instant`, `updated_at instant`, `closed_at instant?`, `retirement_pending_operation_id uuid?`, `retirement_pending_cutoff_utc instant?`, `retired_at instant?`, `revision bigint` | FK author/user and restrictive category_code → Listings unique immutable code; validate through the public catalogue interface, never a private UUID lookup; open/unavailable status. Named live-row check requires title/description/category while non-retired; budget stays optional. Closing sets `closed_at`; reopening same ID clears it, preserves thread uniqueness and starts any later closure clock afresh. Search's pending operation ID and cutoff are paired so an unknown result can be retried with the exact request. Its API blocks conflicting edits, new response conversations and discovery while pending. Retired rows are unavailable and clear content/budget/category; cannot reopen. Index status/creation/ID, author/creation/ID, category FK and closure time. |
| `search.saved_listings` / `(user_id uuid, listing_id uuid)` | `created_at instant` | FKs user/listing; pair PK makes duplicate saves idempotent. Index `(user_id, created_at DESC, listing_id DESC)` for stable own saves; reverse listing FK index for maintenance. Availability changes do not delete saves. |
| `search.wanted_command_results` / `(author_id, scope_id, command_kind, operation_id)` | author/request UUID FKs, scope UUID, create/edit/state kind, paired nullable request/result JSON | Create scope is author; edit/state scope is request. Original outcomes are immutable except paired payload clearing. Only the matching author may own receipts; retired origins cannot retain receipt content. Retirement rejects remaining payloads; the separately approved internal cleanup clears receipt payloads before request content atomically, with real Conversations integration pending. Request FK index; restrictive references; populated migration rollback refused. |

Mohit confirmed that buyer budget is optional. A blank/omitted create-time budget is SQL NULL and means no amount was stated; do not coerce it to zero. An explicit zero budget means seeking a free item. Zero offers are also allowed. Update-time omitted/null semantics must be specified by DL-00/SE-02; these rules do not imply that wanted budgets automatically filter or rank draft matches.

Draft-title matching is a read against the Listings public query boundary; it creates no request, draft history or search-log table. Public open-request discovery returns only approved fields and no private contacts; edits/closure remain author-only. Saved state is private. Cross-domain category validation/read results come through the reviewed public interface; a category FK does not authorize Search to inspect Listings' private tables.

## Conversations and encrypted content — FR-10–12, FR-16

| Table / primary key | Columns | Constraints and access indexes |
|---|---|---|
| `conversations.threads` / `id uuid` | `listing_id uuid?`, `wanted_request_id uuid?`, `initiator_id uuid`, `counterparty_id uuid`, `created_at instant`, `last_activity_at instant`, `participant_writes_disabled_at instant?`, `next_sequence bigint` | Exactly one origin FK is non-null; user FKs, distinct participants; positive next sequence. Partial unique `(listing_id, initiator_id)` for listing origins; partial unique `(wanted_request_id, initiator_id)` for request origins. Index counterparty, each origin FK and `last_activity_at` for bounded retention selection. Participant writes lock the thread, reject when the marker is set, and otherwise advance activity using server time after taking the lock. |
| `conversations.origin_retirement_operations` / `operation_id uuid` | `origin_kind text`, `origin_id uuid`, `cutoff_utc instant`, `outcome text`, `marked_count integer`, `created_at instant` | Globally unique operation ID; store request identity and stable result so same-request retries replay and a reused ID with different origin/cutoff conflicts. Record blocked outcomes too; a later attempt after recent activity must use a new ID. This table stores only minimal IDs, cutoff and outcome, never content. Added by migration `20261020142319`; public service handling remains to be implemented and tested. |
| `conversations.members` / `(conversation_id uuid, user_id uuid)` | `last_read_sequence bigint`, `read_at instant?`, `joined_at instant`, `reminder_episode_start_sequence bigint?`, `reminder_sent_at instant?` | FKs thread/user; nonnegative watermark, positive episode start when present; sent-at requires an episode. Preserve episode state beyond terminal-job cleanup until read catch-up. Index `(user_id, conversation_id)` for private inbox lookup. Only the two thread participants may have member rows; exact member/episode/read consistency requires A/D-reviewed deferred constraints/transaction checks. |
| `conversations.public_key_versions` / `id uuid` | `user_id uuid`, `version bigint`, `public_key_material bytea`, `protocol_id text`, `created_at instant`, `retired_at instant?` | FK user; unique `(user_id, version)`, positive version; partial unique active bundle per user. Mohit-approved encoded public bundle length 1–16 KiB. Authentication, exact serialization and device/key replacement rules require A/D/security review. No private keys. |
| `conversations.entries` / `id uuid` | `conversation_id uuid`, `sequence bigint`, `sender_id uuid`, `client_operation_id uuid`, `sdk_client_message_id text?`, `kind text`, `recipient_id uuid?`, `recovery_for_entry_id uuid?`, `recovery_requester_id uuid?`, `recovery_family_id uuid?`, `recovery_attempt bigint?`, `recovery_kind text?`, `created_at instant`, `content_deleted_at instant?` | Unique thread/sequence, sender/operation and sender/SDK ID; FK sender to members. Recovery metadata is all-null or complete, immutable and bound to an original chat entry and accepted request attempt. Recovery kinds retry-request/resend/null are recipient-only protocol controls; ordinary kinds remain message/offer/contact-share. Content-free IDs/references survive payload purge. |
| `conversations.recovery_families` / `(requester_id uuid, family_id uuid)` | `conversation_id uuid`, `original_entry_id uuid`, `first_request_entry_id uuid`, `created_at instant` | Immutable content-free family binding, globally scoped per requester. Original must be a retained chat message in this thread; requester must be its recipient. The first request and binding commit atomically using a deferred check/FK. Responses require the original sender and an accepted matching attempt. No cross-domain business queries. |
| `conversations.encrypted_payloads` / `entry_id uuid` | `protocol_id text`, `protocol_version text`, `envelope_version integer`, `sdk_message_type text`, `client_timestamp_ms bigint`, `sender_key_version_id uuid?`, `recipient_key_version_id uuid?`, `envelope bytea` | PK/FK entry and FKs key versions; encoded envelope 1–64 KiB. v1 routing remains valid; v2 storage enforces SDK IDs and recovery context. Retry controls and SDK null responses have null application key references; content resends preserve the original key versions and SDK timestamp. Key ownership/protocol match thread members. No plaintext columns. |

The recovery storage migration implements the database portion of the
[approved transport revision](../decisions/conversation-recovery-transport.md).
The HTTP contracts/provider and browser recovery integration remain pending;
database support alone does not advertise or accept v2 through the current API.
Legacy SDK IDs are copied from the retained operation UUID with deferred
entry checks flushed before further DDL; ciphertext is not rewritten.

The initiator is the buyer for a listing origin and the regular responder for a request origin. Counterparty identity comes from the authoritative listing/request owner via its public operation, never request-supplied ownership. These are stable origin roles, not a claim that every request responder is a buyer. Service authorization checks live account eligibility, resource state and participant membership; foreign keys alone cannot enforce these policies.

Concurrency requirements for the reviewed implementation:

- Serialize entry sequence allocation on the thread row; entries then have a committed per-conversation ordering. Incremental reads use `sequence > watermark ORDER BY sequence`, separate from shared numbered-page APIs. Do not substitute a UUID or wall clock for committed conversation order.
- A duplicate operation key with different content is a conflict; retry with identical intent returns the original result. Server-side deduplication must not require decrypting the content. Exact payload equivalence representation and retention are reviewed before implementation.
- Read acknowledgement is sent after client display. Atomically advance, never decrease, a member's watermark; reject values beyond existing authorized entries. Fetching/polling alone does not mark read. A watermark comparison is bounded by the thread and actual entries.
- Listing/request owner and eligibility validation occurs through public
  interfaces. Listings/Search serialize their own ordinary origin state against
  thread creation; retirement uses the pending/preflight/marker protocol below,
  not an origin lock held across the Conversations call. A preflight read alone
  is insufficient. Verify these paths against real owner APIs at integration;
  this is not permission for private cross-domain SQL.
- Client encryption must bind the intended conversation, sender, recipient/key version and payload kind according to the reviewed authenticated protocol. The proposed generic envelope is not a cryptographic design or evidence of safe key distribution.

### Origin-retirement coordination — approved implementation direction

Listings owner B (Suraj) approved this sequence on 2026-10-20. The origin owner
keeps its 180-day continuous eligibility anchor and separately requires every
associated thread's latest participant-write time to be at or before
`server_now - 2160 hours`. It sets `retirement_pending_operation_id` and
commits before calling Conversations; pending Listings/Search origins reject
owner edits/reopen, invalidating selection/offer changes and new origin
conversations, and are hidden from discovery. They do not block participant
writes in existing threads before the Conversations marker.
`get_origin_activity` is a fail-closed preflight only.
`mark_origin_retired` locks all associated threads in ascending ID order,
rechecks activity and marks them all no-write or none. Every Conversations
participant write takes that thread lock, checks
`participant_writes_disabled_at`, and obtains its activity timestamp from the
server after locking. Reads, polling and workers do not advance activity.

The cutoff is computed from the origin owner's server clock after its
authoritative eligibility check, never browser input.
`conversations.origin_retirement_operations` provides durable idempotency by a
globally unique operation ID and records origin kind/ID, cutoff, outcome and
marked count. Identical retries return the stored result; different request
reuse conflicts. A blocked result clears owner pending state without clearing
content; an unknown result leaves it pending and is retried/looked up with the
same ID. Only a confirmed marker allows the owning domain to clear its own
content. Cleanup failure leaves the origin pending for retry; on success the
owner sets `retired_at` and clears the pending operation ID in one transaction.
These pending/no-write/operation-result columns and table describe required
forward-migration additions; they are not present in the historical migrations
or deployed by this documentation. The physical content/object cleanup
mechanism remains separately reviewed; this coordination is not authorization
for a destructive run.

No trigger, SQL function or migration may query another domain's business
tables, including a one-time backfill. Application services use the owning
domain's public API; PostgreSQL triggers cannot call Python. Keep local
protections such as message ordering and immutable thread identity, and keep
the approved cross-domain foreign keys. The shared forward migration writer is
Listings B in `domain/listings`; Search C and Conversations D review their
affected portions, while A coordinates real integrated verification at INT-01.
Exact-target data preflight and normal migration apply/review gates remain
mandatory.

The key/envelope review must decide how sender/recipient key-version references and authentication/nonce data are encoded and constrained, how historical entries reference retired public versions, and how key changes behave with one active browser device. Generic `bytea` alone does not close this gate. Do not add invented fixed key lengths or server key recovery. Public-key material and ciphertext are excluded from diagnostics/evidence even though public keys are not decryption secrets.

### Encrypted-envelope storage — Mohit-approved

Mohit approved the following database representation; A/D/security-owner review remains pending. It selects storage fields and exposure boundaries, not a cryptographic primitive, protocol or library:

| Area | Proposed representation |
|---|---|
| Public-key version | Keep one versioned public-key bundle row per user/version, with at most one active bundle per user. A bundle may contain only protocol-required public material. Key registration/replacement still requires authenticated owner binding. |
| Encrypted payload | `envelope bytea`, `protocol_id text`, positive `envelope_version integer`, and required `sender_key_version_id uuid` / `recipient_key_version_id uuid` references. The envelope carries ciphertext and the public nonce/tag/signature/wrapping metadata required by the later approved protocol. No private key or plaintext field. |
| Cross-row integrity | Sender key belongs to entry sender; recipient key belongs to the other thread participant; key bundle and envelope protocol identifiers agree. Preserve referenced historical public versions while their payloads are retained. Validate this with reviewed constraints/service checks; an arbitrary key FK is insufficient. |
| Bounded storage | Public-key bundle: 1–16 KiB; encrypted envelope: 1–64 KiB. These are approved encoded-byte ceilings, not selected algorithm key sizes or plaintext-character limits. Actual protocol shape and accepted versions must be allowlisted/validated before runtime use. |
| Contact-share metadata | Keep selected field names and values together inside the encrypted envelope. `contact_shares` has no plaintext `selected_fields`; its entry link identifies a share without recording whether email, phone or UPI was shared. Authorized Identity selection validation still happens before client encryption. |

The final authenticated protocol must bind conversation ID, payload kind, sender, recipient and key versions and must let the intended participants read their authorized history according to the reviewed key-change/key-loss behavior. Storage of these references does not prove those cryptographic properties. Do not infer a home-grown key agreement, permanent shared secret, algorithm identifier, serialized key format or recoverability guarantee.

The table inventory and existing encryption/private-payload decisions now reflect Mohit's approval. A/D review must still confirm this representation fits the established protocol chosen under CN-01's security design gate before dependent migration acceptance. Protocol changes that need a different representation require a reviewed schema/decision update. The 30-day contact-share retention applies to both labels and values inside its deleted envelope; a content-free marker retains neither.

## Offers and deliberate disclosures — FR-11–12

| Table / primary key | Columns | Constraints and access indexes |
|---|---|---|
| `conversations.offers` / `id uuid` | `conversation_id uuid`, `buyer_id uuid`, `current_revision bigint?`, `next_revision bigint`, `created_at instant`, `history_deleted_at instant?` | FKs thread/member; unique `(conversation_id, buyer_id)`; positive monotonically allocated next revision. Current revision is required unless a trusted retention purge removed all history and set `history_deleted_at`; keep the offer UUID/pair/counter so later resubmission does not create a second logical offer. A new revision restores current pointer and clears the history-deleted marker. Listing origins only. Index buyer; pair index serves conversation lookup. |
| `conversations.offer_revisions` / `(offer_id uuid, revision bigint)` | `entry_id uuid`, `amount_paise money`, `status text`, `created_at instant` | FK offer and unique FK entry; positive revision. Deferred composite FK from offer `(id, current_revision)` to revisions identifies exactly one current revision. Mohit-approved statuses `submitted`/`withdrawn`; acceptance/selection are not conflated. Encrypted optional note uses the corresponding entry payload when present. |
| `conversations.contact_shares` / `entry_id uuid` | No additional payload columns | PK/FK entry; labels and selected values are inside its encrypted envelope. Require the contact-share entry kind and payload while content is retained; purge the share link/envelope at 30 days, keeping only the content-free ordering marker. |

Cross-row checks must bind offer/revision entries to their offer's conversation and buyer, and contact-share/message entries to the correct kind; a simple entry FK is insufficient. A note-less offer may omit its payload; a message or contact share whose content has not been deleted must have one. A deletion marker must have no retained payload or contact-field labels. A content-retained offer requires exactly one valid current revision; a history-deleted offer requires null current pointer/no revisions and retains only its uniqueness ID/counter. This explicit conditional path allows the approved retention policy without dangling FKs or recreating a logical offer. Specify deferred checks and coordinated cleanup before migrations. Seller overviews must retain no-offer/history-expired conversations and join at most one current revision. Consider a current-amount index only after the final query plan is known.

Listings owns `selected_buyer_id` and the selection operation. The conversation screen invokes that Listings operation; Listings may ask Conversations to confirm the buyer's participation, then writes its own state. Listing-based offer mutations also enter through a Listings-owned command, which validates current listing eligibility and asks Conversations to persist the offer. Conversations does not call Listings or write listing state. The contract must validate selection/offer eligibility and handle stale/retried/concurrent actions. No separate orders, payments, reservations, transaction verification, or handover tables are proposed.

### Offer lifecycle — Mohit-approved

Mohit approved the following lifecycle, recorded in the [offer decision](../decisions/offer-lifecycle.md). Conversations/Listings-owner schema review remains pending; it is not implemented behavior:

1. One logical offer per buyer and listing-origin conversation, enforced by unique `(conversation_id, buyer_id)`. Revising the offer appends an immutable revision and atomically advances `current_revision`; it does not create another competing current offer.
2. Current status is `submitted` or `withdrawn`. Only the buyer who owns the offer may create/revise/withdraw it. The buyer may resubmit after withdrawal by appending a new submitted revision to the same offer. A revision change uses the expected prior revision to reject stale concurrent edits; retry keys return the original operation result or conflict on different intent.
3. Retain a revision record for amount/note changes and withdrawal under the approved retention/deletion policy. A withdrawal records the last amount and a new withdrawn state; it does not overwrite the historical submitted revision. Optional notes remain client-encrypted. When retention purges history, preserve the minimal offer UUID/pair/next-revision guard without old amounts/notes/status content.
4. Seller selection is a separate Listings-owned action, not an offer `accepted` status. It grants no payment/handover/reservation guarantee and does not automatically change availability. The seller can see no-offer conversations as well as current submitted/withdrawn offers, limited by the participant/owner contract.
5. Structured offers initially apply only to Sale Listing conversations, where the initiator is the buyer. Wanted Request response conversations support private discussion/contact sharing; adding structured offers there requires explicit requester/responder buyer-role and amount semantics before changing the schema/service contract.

Mohit's lifecycle approval requires current listing availability/window and both participants' eligibility for offer create/revise/resubmit. The Listings-owned command serializes those checks against listing state changes and calls Conversations to write the offer; buyer withdrawal remains allowed after ordinary unavailability. An eligible seller may select an eligible listing-conversation buyer even without an offer while the listing is available/in-window. Withdrawal does not clear selection; the seller explicitly clears/replaces it through Listings. Existing authorized discussion/contact sharing remains usable under its own account/retention rules. Affected-owner review still covers locking and real public-operation integration; no private cross-domain writes are granted.

## Notification intents — FR-13

Propose `conversations.notification_intents` with primary key `id uuid` and columns:

| Columns | Constraints / meaning |
|---|---|
| `conversation_id uuid`, `recipient_id uuid`, `trigger_entry_id uuid?` | Thread FK; composite FK to recipient membership; optional FK to originating entry, which must belong to the same thread. No copied recipient email or message/contact payload. |
| `event_kind text`, `deduplication_key text` | Event kind restricted to `new_conversation`/`unread_reminder`; unique scoped deterministic key, no content/contact values. Exact event/key construction remains a DL-00/CN-03 contract review; database uniqueness is not an exactly-once provider guarantee. |
| `due_at instant`, `state text`, `attempts integer`, `lease_until instant?`, `lease_token uuid?`, `created_at instant`, `updated_at instant`, `completed_at instant?`, `expires_at instant?` | Proposed states pending/leased/sent/suppressed/failed; nonnegative attempts. Proposed worker claim token prevents a stale worker acknowledging another claim. Finite retention/terminal timing and lease duration remain policy gates. |
| `unread_episode_start_sequence bigint?`, `unread_through_sequence bigint?` | Required only for unread reminders, absent for new-conversation intent; positive start no greater than target. Target message must belong to this thread/recipient; compare with live authorized read state. Episode first unread fixes the due time; later messages update target without postponing it. Exact cleanup/locking checks remain A/D review. |

Propose a B-tree on `(state, due_at, id)` for bounded eligible-work selection and `(conversation_id, recipient_id)` for read/reminder checks, plus missing FK indexes. Only diagnostic failure codes may be added after review; never raw provider responses, email addresses, tokens or message content.

The originating conversation/message transaction creates its notification intent atomically. Conversations owns the intent record and every durable state transition; this makes the message/thread write and intent insert one owning-domain transaction. CN-03 delivery work consumes the Conversations-owned claim/acknowledgement contract and calls Identity's separate recipient-resolution interface. Do not pass raw sessions or write Conversations tables from another domain. Provider dispatch occurs after commit; failure is retryable/observable without reversing the message. Resolve final eligibility and read-state checks immediately before sending; document the unavoidable race with an external provider rather than promising cancellation after email submission. This owner assignment preserves the acyclic call graph recorded in the [DL-00 boundary contract](../../contracts/domain-boundaries.md).

No worker technology, provider, paid service, cloud schedule or email template is selected here. Mohit approved reminder timing/coalescing, bounded attempts/deadline and finite terminal retention below. CN-03 must finalize actual recipient resolution, lease/replay behavior, provider idempotency limitations and operational tests with CN-01. No credentials are needed for PD-08 local schema checks.

### Notification behavior — approved policy; DL-00 contract review pending

| Decision | Approved policy / remaining DL-00/CN-03 contract work |
|---|---|
| Required event kinds | `new_conversation` and `unread_reminder`. Conversation creation targets the other participant and is eligible immediately. Reminders target the recipient of unread text messages. Do not add immediate emails for every message/offer/contact share or optional wanted alerts/digests. |
| Reminder window | Due 15 minutes after the first unread text message in an unread episode. Later messages coalesce into the same episode without postponing its due time; update the highest target message sequence. |
| Read suppression | If the recipient acknowledges all currently unread messages before dispatch, suppress the reminder and end the episode. A later unread message starts another episode. After sending a reminder, do not send another until the recipient catches up and a new unread episode starts. Recheck recipient eligibility and latest authorized read state immediately before provider dispatch. |
| Retry/time bounds | At most 5 delivery attempts: the initial attempt and up to 4 transient-failure retries delayed 1 minute, 5 minutes, 15 minutes and 1 hour after the preceding failed attempt. Stop attempting 24 hours after the original due time; terminal provider failures stop immediately. These values are approved; no worker/schedule is installed. |
| Producer/worker ownership | Conversations' originating conversation/message transaction writes the durable intent and owns its durable state transitions; CN-03 owns delivery work under the task assignment and uses the Conversations and Identity public interfaces. No separately committed intent, provider call inside the producer transaction, cross-domain raw session API, or copied recipient address. |
| Duplicate/replay boundary | New-conversation key uses thread/recipient/event kind. Reminder key uses thread/recipient/event kind and the episode's first unread message sequence. Keys never contain content/contact values. Trusted source/due times are immutable under retry/replay; reject a recreated event whose original delivery deadline has elapsed. Terminal rows retain the approved 30 days; deleting them must not reset the trusted original deadline. |

The inventory now includes nullable `unread_episode_start_sequence bigint` for reminder intents, required with `unread_through_sequence` only for `unread_reminder`, and unique deterministic `deduplication_key`. The read-state owner retains per-member episode state beyond a terminal row when unread messages persist, so 30-day terminal cleanup cannot start another reminder for the same unread episode. `reminder_episode_start_sequence bigint?` and `reminder_sent_at instant?` are included in `conversations.members`; exact producer/read-ack locking/checks remain DL-00/CN-01/CN-03 contract and implementation review. Suppression may remove the active episode; a new episode must follow actual new unread messages, not worker activity.

Lease duration/claim fencing and clock/timezone handling still require A/D operational review before the worker is enabled. A lease expiring after a successful external send can cause an ambiguous retry: no exactly-once email guarantee is made. Use provider idempotency where the eventual provider supports it, honor bounded attempts and record only safe outcome codes. Payload retention, 30-day terminal cleanup, read checks, episode state, dispatch deadline and source replay rejection must be tested together. This proposal does not authorize actual email, provider setup, queues/schedulers, deployment or cloud resources.

## Private-data retention and deletion — Mohit-approved

Mohit approved these durations and minimal-record exceptions in the [retention decision](../decisions/private-data-retention.md). Privacy/affected-owner schema and cleanup review remains pending; no cleanup is implemented. Access expiry and data cleanup are separate: credentials stop working at expiry/revocation even if a row has not yet been purged. Do not run destructive cleanup under this document alone.

| Data | Approved retention trigger/window | Cleanup behavior to implement/review |
|---|---|---|
| OTP challenges/verifiers | 24 hours after consumption or expiry, whichever first makes the challenge unusable | Delete the challenge row; attempt limits must still work across replacement challenges under the reviewed abuse controls. Never extend OTP validity to match retention. |
| Expired/revoked sessions | 7 days after the earlier terminal event | Delete session rows/digests; enforce revocation/expiry immediately on requests. |
| Temporary password hashes | Delete within 24 hours after permanent account expiry/revocation | Prevent later reuse; password reset cannot reactivate the account or create another 14-day term. |
| Identity source contacts/profile fields | Until the user removes a field or account expiry/permanent revocation, then at most 30 days | Remove personal contact/display fields. An active account's contact deletion takes effect immediately in future contact retrieval; old encrypted shares have their own policy. |
| Encrypted contact shares and selected-field labels | 30 days from each share | Remove the share payload and its field labels; keep a content-free entry marker for ordering until the thread-history cleanup. Later sharing creates a new share; it does not renew the old copy. |
| Conversation messages, encrypted offer notes and structured offer revision history | 90 days after the conversation's last participant write | Purge content and offer-history records together through a coordinated transaction; reads, polling, notification jobs and cleanup do not extend the timer. |
| Sent/suppressed/terminally failed notification intents | 30 days after terminal completion | Delete the delivery record; keep a separately reviewed bounded deduplication guard where producer replay is still possible. Terminal cleanup must not cause old events to be emailed again. |

Supporting storage is reflected in the table inventory; exact reference/cleanup constraints still require affected-owner review:

- `conversations.threads.last_activity_at instant`: updated atomically by a participant message, offer revision/withdrawal, or contact share. It is not advanced by reads, workers or passive key lookup. Add an index for bounded inactive-thread selection. Thread-history deletion needs a write lock and a final inactivity recheck so it cannot erase a concurrently revived conversation.
- A content-free entry marker is identified by the existing entry ID/sequence/kind and `content_deleted_at instant?`; it contains no ciphertext, note, contact values or selected-field labels. Exact marker-versus-thread-metadata retention and current-offer FK cleanup need a coordinated constraint plan; do not leave dangling `current_revision` or notification targets. Expired content is not silently re-created by request retries.
- Retain the minimal thread/origin/participant identity needed for the approved one-conversation-per-pair rule while the parent listing/request exists. Do not delete the uniqueness record and then permit a second conversation for the same origin pair. Affected owners must review eventual origin/account retirement and these minimal-reference exceptions; this proposal does not choose to retain all content indefinitely.
- `identity.temporary_enrollments`: one keyed normalized-login digest plus key version, first successful activation and original expiry, with an optional user reference. Create it only after successful initial verification and enforce unique identity enrollment atomically. Preserve this minimal no-self-renewal guard for the service's operating lifetime even when password/contact records are removed. It contains no password, OTP or raw email; a keyed identifier remains sensitive linkable data, not anonymous data. Identity/security owners must review normalization/key rotation and any permitted account upgrade before fixing the final columns/FKs.

Expired/revoked account access is never restored by retention. Public-key versions referenced by retained ciphertext remain available under the reviewed protocol; reference-safe key retirement still needs A/D review. Origin/image content retirement and service-lifetime minimal origin/thread/offer/account references are approved below. Exceptional explicit-deletion functionality is not introduced; no broad FK cascades or public delete API are authorized.

Backup copies must age out under an approved finite backup policy; live-row deletion is not proof of deletion from backups. Any restore must reapply the approved deletion/expiry state before serving traffic or dispatching queued notifications. Provider/object-store retention and recipient-held client copies are outside a database row purge; server cleanup cannot erase a participant's previously retained copy. PD-16/INT-01 and owning domain tasks must document and test the actual boundaries before deployment/recovery acceptance. The [PD-08 Step 7 planning handoff](../../database/backup-and-restore.md) records those future decisions, isolated restore sequence, ownership and NFR-07 evidence gates without implementing or authorizing cloud operations.

The table inventory and canonical retention decision now reflect Mohit's approval; review foreign-key/deferred-check cleanup ordering before migrations. Full schema acceptance still requires affected-owner review and resolution of the explicitly named remaining lifecycle/crypto/notification questions.

## Consolidated lifecycle/storage choices — Mohit-approved

Mohit approved this package; the inventory and canonical decisions now reflect it. It does not reopen earlier choices or select runtime-only security/provider parameters. Affected-owner schema/transaction/crypto review remains pending.

| Area | Approved rule |
|---|---|
| Temporary activation | Start the single 14-day lifetime at the first successful initial email-OTP verification; expiry is that UTC instant plus 14 × 24 hours. Initial registration/password entry does not start or restart the clock. Repeated verification/reset/login cannot renew it. |
| Password reset | On successful reset, atomically update the password hash, consume the reset challenge and revoke all existing sessions for that temporary account. Require normal password sign-in afterward; do not create an OTP-login alternative or reactivate expired/revoked accounts. |
| Listing start/edit/reopen | An omitted start defaults to the server's creation instant. The owner may edit a valid availability window or toggle available/unavailable. Changing the window or state never reassigns selected buyer. Wanted Requests may reopen under the same request ID; existing conversation pair uniqueness persists. Retired origins cannot reopen. |
| Offer mutation | Create/revise/resubmit only while the listing currently satisfies the approved discovery availability/window rule and both participants are eligible. The eligible buyer may withdraw an existing submitted offer after the listing becomes unavailable. Existing authorized conversation messages/contact sharing remain usable; listing closure does not delete the conversation. |
| Selection/withdrawal | An eligible seller may select an eligible buyer from an existing listing conversation even without a submitted offer. Selection requires a currently available/in-window listing. Withdrawing an offer does not automatically clear selection; the seller explicitly clears/replaces it through Listings. Selection still grants no reservation/payment guarantee. |
| Upload staging | Add a Listings-owned durable upload-intent table with pending/confirmed/failed/expired state and owner/object-key binding. Unattached intents expire after 24 hours; remove abandoned-object metadata within a further 24 hours after expiry/failure once cleanup is safe. Confirmed attached intent/image references remain until their image is retired. No public draft listing is added. |
| Search index | Use explicitly named `pg_catalog.english` for both title/description vector construction and query normalization; use a GIN index owned by Listings. English stemming supports related word forms; the earlier `simple` suggestion remains an unaccepted alternative. Any later configuration change requires an index/schema review and affected relevance/NFR revalidation. |
| Inactive origin details | After 180 days continuously unavailable or past the availability end, and at least 90 days without participant writes in every associated conversation, retire Sale Listing/Wanted Request content and image references. Remove their original title/description/pickup/offer/content fields rather than retaining private details indefinitely. Do not retire merely because an account logs out or a temporary account expires. |
| Minimal references on retirement | Preserve content-free origin/thread/account UUID references and required uniqueness guards for the service's operating lifetime. Saved references may point to a retired origin but expose no old details; no new conversation/offer/reopen is allowed on that origin. Account contact/profile/password/auth records retain their separately approved shorter windows. No new public deletion/account-recovery endpoint. |

Upload-intent storage is included in the inventory: `listings.image_uploads` with owner/key/state/deadline/confirmation/safe-failure fields; `listings.images.upload_id` is a unique FK to its confirmed intent. Confirm/attach validates actual object ownership/content/limits, not a client assertion. Confirmed-but-unattached intents retain the original 24-hour deadline; attached images are not deleted by abandoned-upload cleanup. Lock/recheck attachment to prevent deleting a concurrently confirmed usable image. Actual storage failures are observable/retryable under LI-02; cloud/object deletion retains its exact-operation approval gates.

Retirement storage is included: `retired_at` on origins/images and `profile_removed_at` on users. The latter deliberately describes profile removal rather than claiming retained UUID relationships are anonymous. Content columns are nullable only under explicit retired-row integrity checks; mandatory create/live-listing fields, asking price, negotiability and required-image publication still apply to every non-retired listing. Retired origins clear original content and selection details, accept no new writes/reopens/conversations/offers, and expose only the later contract's authorized removed-record representation. Image cleanup rows retain controlled keys only until safe object cleanup succeeds, then the image/intent rows can be removed together.

Before implementation, affected owners review conditional live/retired-image constraints, object cleanup, content-free thread/offer markers and current-revision removal, external-identity retirement, enrollment lookup across key versions and public closure/create locking. Restrictive FKs remain the default. `sale_listings.retirement_eligible_since` anchors continuous unavailability or elapsed end: state/window edits preserve it only when eligibility remains continuous, clear it when eligibility ends, and start a fresh anchor when eligibility begins. If an end elapses between writes, materialize that end instant as the anchor rather than the later cleanup execution time; before editing a previously elapsed end, account for that elapsed interval. `wanted_requests.closed_at` is its closure anchor and resets on reopen. Retirement locks/rechecks origin state and all participant-write activity before clearing content. Required ordering across public owners remains a concrete review/test obligation, not permission for private-table writes.

Search rationale/reference: PostgreSQL documents token/lexeme normalization and stemming in its [full-text introduction](https://www.postgresql.org/docs/18/textsearch-intro.html), [dictionary reference](https://www.postgresql.org/docs/18/textsearch-dictionaries.html), and [table/index guidance](https://www.postgresql.org/docs/18/textsearch-tables.html). English is Mohit-approved, not measured proof of relevance, typo tolerance or NFR acceptance. PostgreSQL runtime version selection remains Step 4; documentation links do not pin a server version.

Mohit's product/storage approval and explicit provisional Step 3 continuation are recorded. A/B/D review of the complete schema/shared boundaries remains pending before final acceptance. Full protocol/storage compatibility and later runtime/provider checks are separate evidence; no stub substitutes for those gates. Initial SQL constraint choices are provisional reviewable implementation, not approval by the other owners.

## Proposed migration ordering and integrity checks

Step 3 will select the migration tool and exact identifiers. Propose a single coordinated migration head, ordered by prerequisites:

1. Namespaces; approved catalogues and Identity base tables, temporary password credentials, application-owned sessions/challenges with reviewed security definitions.
2. Listings/catalogue references/images, with reviewed publication constraint mechanism.
3. Wanted Requests and saved-listing references.
4. Thread origins/membership and reviewed public-key/encrypted-entry tables.
5. Offer revisions, encrypted disclosures and notification intent persistence.
6. Deferred consistency checks and public-query indexes after all referenced tables exist.

Foreign keys are for integrity, not cross-domain runtime access. Catalogue data is reviewed configuration, not fabricated generator output. Multiple heads or cyclic membership/offer references require deliberate deferred constraints; do not silently disable integrity checks. No speculative down-migration may delete real data; rollback/destructive reset behavior belongs to the reviewed tool/local-only lifecycle plan.

Step 6's disposable-database verification must cover: clean migration-to-head and repeat invocation; actual catalogue/FK/check/index definitions matching this reviewed document; valid synthetic inserts; duplicate/invalid FK/null/amount/time/uniqueness rejection; both origin variants and XOR; duplicate pair concurrency; cross-conversation sender/read/offer/reference rejection; atomic publication/image removal; single-current-offer integrity; durable intent rollback with its originating write; and deterministic index-backed query examples. Domain/provider/crypto authorization and NFRs still need their real later tests. Synthetic payloads may be used for DB shape checks but are not protocol/security evidence; do not print them.

## Coverage and review gates

| Requirement | Proposed persistence coverage | Real later acceptance |
|---|---|---|
| FR-01–03 | Accounts, verified provider subjects, lifecycle, reviewed temporary-auth/session storage | ID-01 token/OTP/expiry/revocation and full consumer capability matrix |
| FR-04–05, FR-14–15, FR-17 | Listings, catalogue/condition/price/proof fields, image references, availability and selected buyer | LI-01/LI-02 owner/image/configuration/publication and discovery integration |
| FR-06–07 | Listings-owned native FTS and deterministic public-query indexes | SE-01 real supported boundary/filter/sort/pagination and NFR evidence |
| FR-08–09 | Separate Wanted Requests and private unique saves | SE-02 public open-request/owner writes, matching and unavailable-save behavior |
| FR-10, FR-16 | Origin uniqueness, two participants, ordered ciphertext entries, read state and reviewed key metadata | CN-01 authorization, two-client crypto, retry/concurrency and read integration |
| FR-11–12 | One current offer revision, structured amount/status, encrypted notes/disclosures | CN-02 ownership/selection/selected-field disclosure and failure tests |
| FR-13 | Durable intent, scheduling/read targets, bounded delivery state | CN-01/CN-03 atomic producer, real recipient/read-state, failure/suppression/provider checks |
| NFR-01–05 | Indexed reads, repeatable dataset inputs, ordered messages | Named domain workloads/evaluation; no local timing claim |
| NFR-06–08 | Ordered migration head and explicit ownership aid later recovery/cost work | INT-01, experiments and CLOSE-00; no cloud restore/provisioning here |

Human and affected-owner review queue (approved directions remain closed; only the stated refinements/reviews are pending):

1. **Identity (A/D):** application-owned password/OTP/sessions, first-verification 14-day activation, reset/all-session revocation, auth retention and minimal enrollment guard are approved. Review exact normalization/cross-key guard uniqueness, credential/session/OTP storage compatibility and reset/sign-in concurrency. Password/OTP/session runtime parameters remain ID-01 decisions before enabling the flow; the schema does not select them merely by declaring a digest/hash column.
2. **Listings/Search (B/C):** item category/view/window/default/edit/reopen/saved rules, amount/negotiability semantics, catalogue/limits, English FTS and upload staging are approved. Review conditional live/retired fields, usable-image counts, upload confirm/cleanup locking and public query/index ownership. The provisional sensitive threshold is recorded in its linked decision; upper product caps remain unselected and do not change the integer-money column type. B's original affected-owner review was included in the PD-08 acceptance that the user later confirmed complete.
3. **Conversations/privacy (D/A/B):** offer cardinality/status/revision/origin/availability/selection rules and encrypted-envelope/key-reference/byte-limit/contact-label representation are approved. Review protocol-compatible serialization/owner checks, one-device key-change/history compatibility, closure/create public locking, deletion markers/current-offer guards and real integration. Generic storage is not cryptographic evidence; no library/protocol is silently selected.
4. **Notifications/producer:** two event kinds, 15-minute coalescing/read suppression, one reminder per episode, five attempts/24-hour deadline and 30-day terminal retention are approved. Conversations owns intent records and producer/state writes; CN-03 owns delivery work through the Conversations and Identity public interfaces. Pending: exact episode/read/lease/replay locking and provider limits. Operational lease/clock/provider configuration remains CN-01/CN-03 work before delivery is enabled.
5. **All owners/privacy:** private/auth windows, 180-day inactive-origin/90-day conversation gating and service-lifetime minimal references are approved. Review continuous-inactivity anchors, conditional field clearing, exact FK/current-offer/notification-target/object cleanup and historical public-key references. Finite backup configuration/restore reconciliation remain PD-16/INT-01 cloud/recovery gates; no public deletion feature, blanket cascade or cleanup/cloud execution is introduced.

### Affected-owner review handoff

Review this consolidated document and its linked decisions using the applicable read-only review guidance in [the peer-review prompt](../prompts/peer-review-prompt.md). This is schema design review, not a ready-to-merge PR or evidence of executable DB checks. The work log identifies the exact schema file fingerprint and open checkpoint. No review request or external message has been sent by the agent.

| Reviewer | Required acceptance/findings |
|---|---|
| Aditya (A) | Identity/contacts/auth/enrollment storage and concurrency; producer/recipient/delivery ownership with D; privacy/retention integration. |
| Suraj (B) | Listings/catalogue/query/index/image staging/publication/selection/retirement boundaries and conditional constraints; independent primary peer for Mohit's schema work. |
| Rahul (D) | Origin/member/read/offer/key/envelope design and protocol compatibility; atomic notification producer/episode behavior with A; retention/uniqueness cleanup. |
| Mohit (C) | Search/Wanted Request/save/query inputs and consistency with all recorded product/storage approvals; final revision after reviewer findings. |

For each affected area, report the exact reviewed artifact, acceptance or concrete findings, and any required contract/constraint clarification. Missing public transaction/locking or crypto compatibility decisions must be resolved before dependent migration acceptance; do not substitute a fake contract. Storage review does not approve an unselected cryptographic protocol or replace CN-01's security design/tests.

Mohit authorized Step 3 before this owner review; later corrections remained in the reviewed source paths. The user subsequently confirmed PD-08 owner acceptance and executable checks complete; specific other-machine run artifacts are unavailable in this checkout. Full cryptographic protocol design/testing remains with CN-01, and cloud actions retain their separate approvals. PD-08 is user-confirmed complete; PRE-00 still requires PD-19 and the combined reviewed/main-merged PD-17–19 handoff.

## ID-01 Step3 branch-local schema verification

Aditya verified the Identity-only hardening plan on2026-10-23. Migration
20261023173439 reuses the seven Identity tables and existing useful indexes,
adding profile/contact bounds, revocation event consistency and immutable
provider mapping only. Existing UTC/UUID/336-hour lifetime/enrollment guards stay.
The branch deliberately excludes PR10 until later integration; its expected
head does not imply the full accepted-main migration chain is installed.
The new storage checks and data-preserving round trip use disposable real
PostgreSQL only, not a schema test double. Microsoft validation, normalization/
key rotation, hash/verifier design, session policy, safe cleanup and service
authorization remain their original ID-01 gates. See the database README.

## ID-01 Step5 protected challenge transaction state

Forward migration20261023192856 adds `identity.otp_key_binding`,
`identity.otp_operations`, `identity.otp_send_reservations` and
`identity.otp_verification_windows`; domain table count is27 on this isolated
branch. The existing challenge gains nullable key version, authenticated target
ciphertext and supersession time with protected-field/time checks. Legacy rows
are preserved; the new service requires reviewed adoption before existing
unbound temporary state can be used. No raw code or password is stored.

The service serializes source then target for sends, and target then account for
verification/reset eligibility. Three failures survive resends until the latest
code expires. Correct verification, consume and the later owning mutation share
one transaction; failed verification counters commit before returning an error.
Suppressed acknowledgements consume the same limits and failure budget, without
creating phantom users or persisting dummy reset verifiers. Public uniform timing
and actual activation/reset/session checks remain integration gates.

Aditya approved service-lifetime retention of minimal request markers, limited
to keyed request digest, key version, challenge ID and original expiry. Cleanup
of the separate operational state still requires the owning retention design;
no deletion job is authorized. Ordinary OTP private-data retention and immediate
access revocation remain unchanged. Occupied down migrations fail
closed under exclusive locks; review a security-state migration before rollback.

## ID-01 Step7 session/login extension

[Reviewed session/cleanup policy](../decisions/identity-sessions-and-cleanup.md)
adds nullable `sessions.last_seen_at` and three Identity tables through
migration20261023202807: `password_login_windows`, `auth_source_events`,
`microsoft_login_attempts`.30 domain tables. Raw session/attempt secrets, passwords,
assertions and source addresses are not stored. Seven-day absolute/24-hour idle
sessions, temporary-expiry cap and single-use browser-bound nonce state are
server-enforced. Legacy session activity is not backfilled; occupied down fails.

Account/session creation and reset/hash/all-session revocation compose in one
owner transaction. Lock order is source→target→user→session for temporary
credentials; final Microsoft redemption locks attempt→provider tuple→user.
Current authentication locks user→session. Cleanup rechecks under compatible
locks per candidate; it never deletes permanent user/guard/contact records.
Operational rate/attempt state ages out only after it no longer protects active
windows. Source and target failure windows remain separate from OTP's three
attempt budget. No cleanup schedule or public/cloud enablement is implied.
