# Frontend page inventory and collaboration map

## Shared page and interface edits

Suraj is the current writer/operator for the hosted functional repair, including
the shared HTTP batching utility and affected public Listings/Search consumers.
The scope is [recorded here](../decisions/hosted-functional-repair.md); ownership
and other domain-private import boundaries remain. Generated contract changes
come from their canonical sources.

This file records approved routes, feature owners and public entry points; it
does not hold an active writer reservation. Before a shared page/interface edit,
check the current task and work-log checkpoint, name one writer, and coordinate
affected feature owners. Historical reservations and walkthroughs are omitted.

## Sources and interpretation

- [Submitted PRD](../source/ICC_Project_PRD_FINAL.pdf), especially page 2
  (workflows and FR-01–07), page 3 (FR-08–17), page 5 (privacy/device/notification
  constraints), and page 7 (MVP).
- [Product reference](../product/product-reference-and-architecture-decisions.md),
  §§1–5 and 7–9: required scope, exclusions, requirement summaries, and decisions
  deferred to their owning tasks.
- [Wanted-request discovery decision](../decisions/wanted-request-discovery-and-response.md):
  public request discovery, regular-member responses, author management, and the
  temporary-account restriction.
- [Frontend ownership and composition decision](../decisions/frontend-ownership-and-composition.md):
  primary/integration contributors, public feature entry points, shared-page
  coordination, and shared UI/style ownership.
- [Web route scaffold decision](../decisions/web-routing.md): React Router
  declarative routing for the approved scaffold, with no domain loaders/actions.
- [Domain task list](../tasks/domain-task-list.md), DL-00 and ID-01 through CN-03:
  implementation obligations and cross-domain ownership.
- [Contribution rules](../../CONTRIBUTING.md) and the
  [roster](../status/work-log.md): A/Aditya owns Identity and notifications;
  B/Suraj owns Listings and images; C/Mohit owns Search/Wanted/Saved;
  D/Rahul owns Conversations and offers.
- [Shared conventions](../conventions/shared-conventions-and-cross-domain-contract-rules.md):
  trusted authorization, domain boundaries, private contact access, and reviewed
  contracts. [Build tooling](../decisions/web-build-tooling.md) supplies only the
  current technical app mount point.

The PRD specifies capabilities and workflows, not exact browser URLs or screen
counts. The verified routes and groupings below are the approved frontend
presentation plan for those capabilities. Browser route parameters are
placeholders, not frozen API types.
Business request/response/event/session contracts remain DL-00 outputs;
PD-11 supplies generation tooling. No dependency double is used for this inventory.

The submitted PDF was read directly by extracting all eight pages with temporary
local pypdf 6.21.0 tooling. Its SHA-256 remains
`8ac241d1e72472a5dc77edad18579ec5d2ca3ff2ac8fd454cbc6e9627abf4ad1`.
The extraction and tooling stay outside the repository; they are not application
dependencies or replacements for the PDF.

## Approved page and route inventory

These twelve routes and their page-level contributor roles were verified in
PD-07 Steps 2–3. “Primary” means the domain owns the main feature content and
behavior for that page or tab. “Small integration” means the domain supplies a
bounded component/action or display connection needed by that page. Neither role
assigns a permanent page-composition owner.

| Page path | ID / surface | Significant sections and actions | Primary contributor(s) | Small integration contribution(s) | Requirement basis |
|---|---|---|---|---|---|
| `/sign-in` | P01 — sign-in and temporary onboarding | Microsoft sign-in; personal-email registration; OTP verification/resend; eligibility, expiry, and safe error states. Registration/OTP are states of this page rather than extra routes. | A — Identity (ID-01) | — | FR-01–03; ID-01 steps 5–7/11 |
| `/auth/callback` | P02 — technical identity return | Pending/success/error handling for the approved identity redirect flow. Provider details and registered redirect URLs are finalized by ID-01; this proposal does not call a provider. | A — Identity (ID-01) | — | FR-01; ID-01 steps 2/4/11 |
| `/` | P03 — public discovery | Toggle between available Sale Listings and open Wanted Requests; search, filters, sort, pagination, summaries, and detail links for the selected view. **Item category** identifies the kind of item (phone, bicycle, furniture, etc.) using the existing Listings-owned category catalogue; it is separate from the Sale Listings/Wanted Requests view toggle. See the [clarified discovery decision](../decisions/listing-discovery-semantics.md). | C — Search/Wanted/Saved (SE-01, SE-02) | B — listing summaries (LI-01/LI-02) | FR-03/06/07/08; PRD page 2 buyer workflow; SE-01 steps 3–8; clarified wanted-request discovery requirement |
| `/listings/new` | P04 — create sale listing | Required listing fields, zero-price support, images/upload feedback, sensitive-purchase declaration, validation, and publication state. Restricted to eligible regular sellers. | B — Listings (LI-01/LI-02) | A — account eligibility (ID-01) | FR-03–05/14/17; LI-01 step 7; LI-02 step 9 |
| `/listings/:listingId` | P05 — listing detail | Images and listing information; availability and unverified proof declaration; buyer save and start/reopen-conversation actions; authorized seller controls. | B — Listings (LI-01/LI-02) | C — save action (SE-02); D — start/reopen conversation (CN-01) | FR-04/05/09/10/14/15/17; LI-01 step 7; PRD page 2 buyer workflow |
| `/listings/:listingId/edit` | P06 — edit sale listing | Owner-only listing/image edit, validation, partial-upload failures, availability controls, and current publication state. | B — Listings (LI-01/LI-02) | — | FR-04/05/14/17; LI-01 step 7; LI-02 step 9 |
| `/my/listings` | P07 — own marketplace posts | Owner-only toggle between Sale Listings and Wanted Requests. Sale view shows active and unavailable/past records with status and create/edit/detail/availability actions; wanted view creates/manages only the user's requests, shows draft sale matches, and lets the author mark a request unavailable. | B — Sale Listings (LI-01/LI-02); C — Wanted Requests (SE-02) | D — seller-inbox link for a sale listing (CN-02) | FR-05/08/09/15; LI-01 step 7; SE-02 steps 3/4/7; CN-02 step 4; Suraj's PD-07 clarification |
| `/saved` | P08 — private saved sale listings | Own saved records; unsave; listing-detail links; visibly unavailable records retained after availability changes; permitted actions reflect current state. | C — Search/Wanted/Saved (SE-02) | B — listing summaries and availability (LI-01/LI-02) | FR-09; SE-02 steps 5–7 |
| `/my/conversations` | P09 — user's conversations and seller overview | Buyer vs selling/request-response views. Seller view scoped/grouped by an owned listing or wanted request, including current offers and no-offer conversations. Filter/group by listing/request and conversation partner; sort/filter offers by amount where applicable. My Listings can open the seller view for a chosen listing. Exact query and ordering contracts remain DL-00/CN-02 work. | D — Conversations/Offers (CN-01/CN-02) | B — listing context for the seller view (LI-01) | FR-10/11; PRD page 2 workflows; CN-02 step 4; clarified inbox scope; DL-00 contract work |
| `/my/conversations/:conversationId` | P10 — private conversation | Encrypted message thread/composer; send/pending/retry and key states; structured offers/revisions/withdrawal; seller selection/availability flow; deliberate selected contact sharing. Only the participants may enter. | D — Conversations/Offers (CN-01/CN-02) | B — listing selection/availability (LI-01); A — contact options (ID-01) | FR-10–13/15/16; CN-01 steps 5–8; CN-02 steps 3–8 |
| `/account/contacts` | P11 — Account | Own Handle and contact editor; default-on conversation-email preference; authorized collection/update of phone/email/UPI and safe validation/error states; return to a conversation's deliberate contact-sharing flow. Account navigation must not expose contact values. Missing encryption keys are gated by the shared account setup before this page is reachable. | A — Identity (ID-01/CN-03) | D — private-messaging key readiness/creation gate | FR-12/13; ID-01 steps 9/11; CN-02 steps 7/8; CN-03 step 7; NEXT-03 correction |
| `/wanted/:requestId` | P12 — public wanted-request detail | Public details for an open request and a Contact requester action for eligible regular members. The action starts a private conversation associated with that request; do not reveal the author's contact details on the page. The author can mark a request unavailable from `/my/listings`. | C — Search/Wanted/Saved (SE-02) | D — contact-requester action (CN-01/CN-02); A — response eligibility (ID-01) | FR-08/10; clarified wanted-request discovery and response behavior; DL-00 contract required |

P04's static `new` segment must not be mistaken for P05's listing ID. The selected
router and Step 8 route checks must cover that distinction. Unknown paths,
unauthorized access, expired sessions, and missing/unavailable records need the
appropriate shared or feature state; they do not by themselves require extra
product routes.

The `/my/` prefix communicates that a page contains the signed-in user's own
records. It does not authorize access. The route guard is only a navigation aid;
the Conversations API must derive the actor from trusted session/auth context
and authorize every read and write against conversation participation, including
requests made by typing or substituting an ID. CN-01 explicitly requires
nonparticipant denial on every route, including direct ID substitution. Use the
shared safe error behavior so a caller cannot use guessed IDs to read private
messages or probe other users' conversations. The exact error response is a
DL-00 contract decision.

The shared shell provides navigation, sign-in/logout/session status, and the
app frame. A owns the shell/navigation and Identity contribution under PD-07's
recorded later ownership; consumers apply server-authoritative capabilities.
Expired/revoked temporary sessions lose access even if the old screen is open.
Detailed session transitions and return-navigation behavior need the reviewed
Identity contract. UI hiding alone never authorizes a request.

## Composition ownership and public component boundaries

### Directory responsibilities

All paths below are relative to `apps/web/`:

| Directory | Purpose | Responsibility |
|---|---|---|
| `src/app/` | Router, application providers, and the site shell/navigation. | Cross-cutting; A maintains the shell/navigation. |
| `src/pages/` | Route-level composition of feature components. Pages connect public feature exports but do not take over their business behavior. | Composition owner stays open; the available integrator coordinates a shared edit as its sole current writer. |
| `src/shared/ui/` | Reusable presentation controls used across pages, such as a button and page frame. No domain business rules. | A maintains the common source; affected consumers review shared changes. |
| `src/shared/styles/` | Shared typography, spacing, colors, focus/disabled states, and the conventions feature styles follow. | A maintains the common baseline; feature owners keep detailed feature styling in their roots. |
| `src/features/identity/` | Identity, account, and notification UI. | A / Identity and notifications. |
| `src/features/listings/` | Sale listing and image UI. | B / Listings and images. |
| `src/features/search/` | Search, Wanted Request, and Saved Listing UI. | C / Search, Wanted, and Saved. |
| `src/features/conversations/` | Private conversation and offer UI. | D / Conversations and Offers. |

The four feature roots have `.gitkeep` handoff markers. Each remains in the
PD-07 handoff and is removed only by that feature's owner at their first
authorized implementation write. The markers in `src/app/`, `src/pages/`,
`src/shared/ui/`, and `src/shared/styles/` only make those currently empty
directories visible to Git; remove each ordinary marker when its first real
file is added. No separate marker is needed for the `src/shared/` parent because
Git records it through its tracked child directories.

### Step 6 scaffold paths and connections

The route table above is defined in `src/app/approvedRoutes.tsx` and mounted by
`src/app/router.tsx`; every route uses the shared shell in
`src/app/AppShell.tsx` and a page composition component in
`src/pages/ScaffoldPages.tsx`. The shell navigation includes all twelve routes;
the `example` values in dynamic-route preview links are route samples only and
do not identify real records. The catch-all renders a local not-found message;
it is not an additional product route.

| Page path | Page component | Public feature placeholders and connections | Owning task(s) |
|---|---|---|---|
| `/sign-in` | `SignInPage` | `identity/SignIn` (Microsoft and temporary registration/login/reset; real local provider smoke verified) | A — ID-01 |
| `/auth/callback` | `AuthCallbackPage` | `identity/MicrosoftCallback` (real local IISc success/non-IISc denial verified; cloud/device acceptance pending) | A — ID-01 |
| `/` | `DiscoveryPage` | `search/SaleDiscovery` renders reviewed public sale summaries, displays the first attached photo via Listings' public `ListingImagePreview`, and links to B's detail route; `search/WantedBrowse` renders open requests | C — SE-01/SE-02; B — public summary/image delivery integration |
| `/listings/new` | `ListingCreatePage` | public `identity/SellerEligibilityGate` wraps `listings/CreateListing`; mounts only for a current regular session, blocks temporary/loading/missing/expired/unavailable states | B — LI-01/LI-02; A — ID-01 integration |
| `/listings/:listingId` | `ListingDetailPage` | `listings/ListingDetail` composes Search's `SaveListingAction` and public `listings/StartListingConversationAction`; the latter invokes Listings' guarded start/reopen HTTP command and navigates to the validated returned conversation ID | B — LI-01/LI-02; C — SE-02; D — CN-01 integration |
| `/listings/:listingId/edit` | `ListingEditPage` | public `identity/SellerEligibilityGate` wraps `listings/ListingEdit`; server enforces regular seller/owner checks | B — LI-01/LI-02 |
| `/my/listings` | `MyListingsPage` | Local view switch; public `listings/MyListings` and `search/MyWantedRequests` with draft matching; public Identity account boundary resets private state on actor changes; Conversations integration pending | B — LI-01/LI-02; C — SE-02; D — CN-02 integration |
| `/saved` | `SavedListingsPage` | `search/SavedListings` uses the same `SaleListingCard` as Discover, including the Listings public photo renderer, current availability and Remove action; retired records remain content-free | C — SE-02; B — LI-01/LI-02 integration |
| `/my/conversations` | `ConversationsPage` | `ConversationRuntime` provides the authenticated Conversations API to `ConversationInboxPage`. The member-scoped inbox has buyer/seller/requester/responder roles, origin grouping, partner/offer filters, amount sorting and bounded paging. Until owner interfaces expose display names, group/partner labels use shortened IDs; details and message content are not fetched for the inbox. | D — CN-01/CN-02; B — listing display context remains a small integration |
| `/my/conversations/:conversationId` | `ConversationDetailPage` | `ConversationRuntime` provides the authenticated Conversations API to the private encrypted thread view. Message/key/read states, seller selection, deliberate contact sharing, and the amount-only offer panel are connected. `pages/ConversationOffers.tsx` composes authorized Conversations reads with public Listings submit/withdraw exports; only buyers submit/revise/withdraw. Seller group done-deal actions use the Listings availability port. Real provider/cloud acceptance remains separately gated. | D — CN-01/CN-02; B — listing selection/availability; A — Identity contact options |
| `/account/contacts` | `AccountContactsPage` | `identity/ContactsEditor` (own-source editor; human verification pending) | A — ID-01 |
| `/wanted/:requestId` | `WantedRequestPage` | public `search/WantedDetail` reads `/me`, disables responses for temporary/expired sessions and calls the response API; real Conversations provider pending | C — SE-02; A — ID-01 and D — CN-01/CN-02 integration |

Public wrappers are `src/features/identity/IdentityPlaceholder.tsx`,
`src/features/listings/ListingsPlaceholder.tsx`,
`src/features/search/SearchPlaceholder.tsx`, and
`src/features/conversations/ConversationsPlaceholder.tsx`, exported through
each respective `index.ts`. All wrappers delegate to
`src/shared/ui/ScaffoldPlaceholder.tsx`, which labels the unfinished section
and owner and provides an explicit `children` slot for page-level composition.
That slot is a presentation boundary, not a finalized cross-domain data/event
contract. Domain owners may replace the implementation behind their public
entry point; changes to a public export or cross-domain prop/event connection
must be coordinated with affected consumers and reflected in this map.
The foundation scaffold has only local selection of the two approved view
toggles. LI-01 Step 7's first increment replaces the Listings create/detail
placeholders with API-backed public exports from the same Listings entry point.
It preserves the existing A/C/D child slots and adds no cross-domain data/event
props. Its isolated browser harness uses real local PostgreSQL but synthetic
trusted Identity and image-confirmation metadata, explicitly labelled in the UI.
It supplies no real sign-in, photo upload/delivery, save-to-favourites, chat,
contact or offer behavior. Edit/My Listings remain placeholders at this checkpoint.
Listings removed its own `.gitkeep`; other feature markers remain with their owners.

Page-composition ownership is intentionally unassigned. When an integration
requires a shared page edit, the available integrator/merger coordinates it and
becomes the current writer for that edit. Only one person edits a given page
composition at a time; feature contributions remain in their owning feature
roots. The current writer records the affected page and coordinates with the
involved domain contributors before changing a public component connection.

## Significant cross-domain connections

This table identifies the connection and its eventual contract work. It does
not define final component props, API signatures, caches, or event payloads.

| Connection | Feature responsibilities and user-visible result | Contract / state question to resolve later |
|---|---|---|
| Discovery/saved/match result → listing summary/detail | C owns the query or saved state; B owns authoritative listing/availability/images. Discover and Saved use the same Search sale-card presentation. Both receive photo IDs from the reviewed sale summary and call the Listings feature's public `ListingImagePreview`, which requests authorized image delivery; Search does not read Listings internals or storage. | DL-00 chooses supported listing reads or the approved Search projection and synchronization. Listing-summary display boundaries are verified in PD-07 Step 3; photo display uses the existing Listings delivery operation. |
| Listing detail/result → save action | C owns save/unsave while B supplies listing context. The detail action reads the caller's private saved pages before offering Save, then displays the existing saved state; the server's idempotent write remains the race-safe fallback. Saved sale cards share Discover's presentation. | DL-00 assigns UI state ownership, refresh/invalidation, response/errors, idempotency and expired-session behavior; SE-02 implements it. |
| Listing detail → start/reopen conversation | The Listings-owned action validates current listing/owner state and invokes Conversations to create or return the thread; Conversations owns thread persistence. Identity supplies trusted eligibility. One buyer/listing pair has at most one conversation. | DL-00 freezes create-or-existing behavior, failures, participant derivation, and stale/unavailable-listing rules. |
| Wanted-request discovery/detail → contact requester → private conversation | Search owns public wanted-request browse/detail and request state; its Contact requester action invokes Conversations to create or return the thread. Conversations owns thread persistence; Identity supplies trusted account capability. Temporary accounts can browse but cannot respond because they are new freshers without items to sell. Public request details do not expose contact information. | DL-00/SE-02/CN-01 define request visibility, response eligibility, request association, duplicate/retry behavior, participant authorization, and behavior if the author closes the request. The existing one-buyer/one-listing conversation rule does not define uniqueness for request responses. |
| My Listings → seller overview → conversation | B's owned listing record links to D's view of that listing's conversations/current offers under `/my/conversations`. D keeps private conversations isolated. The inbox has buying vs selling/request-response views and candidate grouping/filtering by listing or wanted request, person, and offer amount. | DL-00/CN-02 define authorization, grouping, available filters/sorts, offer semantics, and how request-origin conversations appear. |
| Conversation → selected buyer and availability | The conversation screen presents the action and invokes the Listings-owned selection operation through the frontend/API boundary. Listings remains authoritative and may call Conversations to confirm thread participation; the seller sees confirmed results or an actionable failure. | DL-00 decides selection/availability relationship, permissions/visibility, retry/concurrency, and cross-view refresh. Selection, availability, payment and handover must remain distinct. |
| Conversation → listing offer mutation | The conversation screen submits create/revise/resubmit/withdraw through a Listings-owned command. Listings serializes current availability/eligibility and asks Conversations to persist the offer; Conversations remains the offer-record owner. | DL-00/CN-02 freeze eligibility, retry/concurrency and failure behavior. Buyer withdrawal after ordinary unavailability follows the approved offer decision. |
| Conversation → own contact options/editor → deliberate reveal | A owns private contact editing/options; D owns the per-conversation selection/confirmation/reveal flow. Only the actor's selected fields reach the relevant participants. | DL-00 freezes authorized contact retrieval and encryption/exposure/retention; ID-01 and CN-02 bind the real interfaces and failure handling. |
| Listing form → image handling → publishable listing | B owns both LI-01 and LI-02. The form must display pending/rejected/retry states without falsely publishing an image-backed listing. | Reviewed listing/image contracts define publication, upload limits, confirmation, partial failure and retry. |
| Wanted editor → possible sale matches | C owns the draft and matching UI; B supplies active sale data through the approved boundary. Suggestions appear before submission and do not block it. | DL-00/SE-02 define bounded matching inputs/results, draft-update behavior, unavailable exclusion, and safe failures. |
| Identity/session → every protected feature | A owns trusted account/capability/session interfaces; each domain owns its own authorized operation. | DL-00 freezes session/provider placement, capability/error shapes, expiry/revocation handling and refresh responsibilities. |
| Conversation display/read acknowledgement → notification suppression | D acknowledges messages actually displayed; CN-03's delivery worker uses the Conversations-owned read-state/intent contract and Identity's recipient interface. Email failure does not fail a successful marketplace write. | DL-00 freezes read-watermarks, events and producer transaction; CN-01/CN-03 implement the real path. Notification email destinations should reuse approved routes without leaking private content. |

## Product constraints carried into the proposed surfaces

- My Listings retains the seller's active and unavailable/past listing records
  with status. This agreed interpretation provides listing history, not a new
  order record or a claim of verified payment/handover. The concrete status model
  remains the Listings contract's responsibility.
- No separate notification centre is required by FR-13: its required delivery is
  asynchronous email. The optional weekly wanted-request digest may link to public
  request details; wanted-match alerts and image-aware search do not add routes
  unless their tasks are explicitly selected and reviewed.
- Sensitive-purchase flags and any proof declaration remain unverified seller
  information. Account/device/key-loss states must preserve the one-active-browser
  MVP and no server key recovery.
- Every data surface eventually needs its relevant loading, empty, invalid,
  denied/expired, retry/error, and unavailable states. The scaffold will identify
  incomplete sections without pretending domain actions succeeded.
- No payment, order-processing, delivery, rating, moderation dashboard, or optional
  feature pages are derived from the current required scope.

## Verified product clarifications and deferred contracts

Suraj verified the public Sale Listings/Wanted Requests toggle on `/`, an
owner-only Sale Listings/Wanted Requests toggle on `/my/listings`, public wanted
request details, and a private conversation started by an eligible regular
member who wants to respond. The author can mark a request unavailable after it
is no longer wanted. Temporary accounts may browse but cannot respond because
they are new freshers with nothing to sell. Request pages must not expose the
author's private contact information.

Suraj also verified buyer/seller inbox views and filters/grouping by listing or
request, conversation partner, and offer amount where applicable. Exact queries,
ordering, request-conversation association, and duplicate behavior remain DL-00
and domain-task contract work; this map does not invent them. The public post
type taxonomy and schema are owned elsewhere and are outside this frontend map.
The weekly wanted-request digest remains optional and should link to public
request details without including private conversation/contact data.

## Review checkpoints

Steps 2–3 verified the page inventory, contributor roles, public feature entry
points, shared-page coordination rule, and shared UI baseline. No page/route/
feature stubs are created by these planning steps. DL-00 and the domain task
lists must define the business contracts before implementation depends on them.
Step 9 updates downstream task and agent instructions to the implemented
scaffold and reviewed contracts.

## Current integration status

Use the [domain task list](../tasks/domain-task-list.md) for required feature
behavior and the [work log](../status/work-log.md) for current owners, checkpoints
and verification. The Search product has no visible mode selector and defaults
to Hybrid; legacy Keyword URLs/API handling remain for compatibility. Current
Conversations and Identity integration details are in their retained
[CN-01 handoff](../evaluation/domain/conversations-integration.md),
[CN-02 handoff](../evaluation/domain/conversations-offers.md), and
[ID-01 provider guide](../environment/identity-provider-setup.md). No historical
reservation below should be treated as current authorization.

### NEXT-03 inspection composition

Suraj is the sole writer for the `ScaffoldPages.tsx`/`ConversationOffers.tsx` integration increment authorized by the user on 2026-10-28. The normal conversation routes expose inbox multi-selection, buyer selection and seller done-deal actions; the old development-only presentation demo is not the inspection route. `scripts/marketplace_inspection.py` serves the normal built UI and application factory with real local sessions/domain stores and explicit synthetic external provider ports. Its actor controls are test-only and never installed by normal startup. Shared page editing is complete for this increment; affected-owner and independent PR review remain required.

### Conversations-first functional correction — 2026-10-28

Suraj is the sole writer for AppShell/account-key setup, ConversationRuntime/page
composition and the safe contact-settings return link for this verified scope.
The public Conversations entry point exposes ConversationKeySetup; AppShell
mounts it for authenticated accounts before marketplace pages. Matching legacy
keys are retained, new accounts have separate IndexedDB namespaces, and ordinary
returning logins resume without key consent again. The SDK13.0.0 compatibility
adapter configures database/lock identity before initialization and fails closed
if its pinned adapter shape changes; real-browser regressions are required on
SDK upgrades. No shared global IndexedDB factory is changed and no private key
is copied between accounts. Identity handle/schema work remains later.

### NEXT-03 full visual-feedback follow-up — 2026-10-29

Suraj remains the sole writer for the authorized integrated correction through local visual inspection. Identity's public entry exports `HandleSetup` and `HandleEditor`, reused by AppShell and account settings; Conversations exports `ConversationUnreadBadge`, keyed by authenticated account, and accepts the public origin-context renderer on both inbox and thread. The composition page supplies that renderer using only Listings/Search public reads. The inbox uses reviewed marketplace modes and group-first pagination; participant identity comes only from Identity's public `participant_profiles` projection through member-authorized Conversations summaries. Handle/database, modes/pagination and unread work were explicitly included by the later full-batch authorization; earlier exclusions are historical. Independent owner/peer review and cloud gates remain separate.
