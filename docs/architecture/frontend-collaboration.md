# Frontend page inventory and collaboration map

**Status:** Human-verified frontend foundation map. It records the approved
routes, contributor roles, public feature entry points, shared-page coordination
rule, shared UI baseline, and implemented scaffold connections. These are not
completed domain features or frozen business/API contracts; current step and
verification state is recorded in the [work log](../status/work-log.md).

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
| `/account/contacts` | P11 — own contact editor | Authorized collection/update of own phone/email/UPI and safe validation/error states; return to a conversation's deliberate contact-sharing flow. General account navigation must not expose contact values. | A — Identity (ID-01) | — | FR-12; ID-01 steps 9/11; CN-02 steps 7/8 |
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
| `/sign-in` | `SignInPage` | `identity/SignIn` (temporary sign-in/registration first checkpoint; Microsoft/reset pending) | A — ID-01 |
| `/auth/callback` | `AuthCallbackPage` | `identity/MicrosoftCallback` (gated SDK flow; actual provider checks pending) | A — ID-01 |
| `/` | `DiscoveryPage` | `search/SearchPlaceholder` contains `listings/ListingsPlaceholder` for sale summaries; wanted browse is C-only | C — SE-01/SE-02; B — LI-01/LI-02 integration |
| `/listings/new` | `ListingCreatePage` | `listings/ListingsPlaceholder` contains `identity/IdentityPlaceholder` for eligibility | B — LI-01/LI-02; A — ID-01 integration |
| `/listings/:listingId` | `ListingDetailPage` | `listings/ListingsPlaceholder` contains `search/SearchPlaceholder` save action and `conversations/ConversationsPlaceholder` start/reopen action | B — LI-01/LI-02; C — SE-02; D — CN-01 integration |
| `/listings/:listingId/edit` | `ListingEditPage` | `listings/ListingsPlaceholder` | B — LI-01/LI-02 |
| `/my/listings` | `MyListingsPage` | Local view switch; sale view uses `listings/ListingsPlaceholder` with a `conversations/ConversationsPlaceholder` seller-inbox connection; wanted view uses `search/SearchPlaceholder` with a listings match placeholder | B — LI-01/LI-02; C — SE-02; D — CN-02 integration |
| `/saved` | `SavedListingsPage` | `search/SearchPlaceholder` contains `listings/ListingsPlaceholder` summaries/availability | C — SE-02; B — LI-01/LI-02 integration |
| `/my/conversations` | `ConversationsPage` | `conversations/ConversationsPlaceholder` contains `listings/ListingsPlaceholder` context | D — CN-01/CN-02; B — LI-01 integration |
| `/my/conversations/:conversationId` | `ConversationDetailPage` | `conversations/ConversationsPlaceholder` contains listing selection/availability and identity contact-option placeholders | D — CN-01/CN-02; B — LI-01 and A — ID-01 integration |
| `/account/contacts` | `AccountContactsPage` | `identity/ContactsEditor` (own-source editor; human verification pending) | A — ID-01 |
| `/wanted/:requestId` | `WantedRequestPage` | `search/SearchPlaceholder` contains identity eligibility and conversations contact-requester placeholders | C — SE-02; A — ID-01 and D — CN-01/CN-02 integration |

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
must be coordinated with affected consumers and reflected in this map. The
only scaffold interaction is local selection of the two approved view toggles.
There is no API call, authentication result, save, message,
contact, offer, or other simulated domain success. Feature `.gitkeep` markers
remain tracked alongside these placeholders for the later owners' handoff.

Page-composition ownership is intentionally unassigned. When an integration
requires a shared page edit, the available integrator/merger coordinates it and
becomes the current writer for that edit. Only one person edits a given page
composition at a time; feature contributions remain in their owning feature
roots. The current writer records the affected page and coordinates with the
involved domain contributors before changing a public component connection.

App composition lives in `src/app/` and `src/pages/`. Pages import feature
components only through these public entry points:

- `src/features/identity/index.ts` — A / Identity and notifications.
- `src/features/listings/index.ts` — B / Listings and images.
- `src/features/search/index.ts` — C / Search, Wanted Requests, and Saved Listings.
- `src/features/conversations/index.ts` — D / Conversations and Offers.

Each domain owns its feature implementation and exports only components
intended for page composition from its entry point. A feature must not import
another feature's private files. Pages may compose several public components,
including through a supplied action/child area, so a save or contact action can
appear in a listing/request view without moving ownership into that feature.
Exact prop, event, data, session, and refresh contracts remain with DL-00 and
the domain tasks; the entry-point paths do not freeze business APIs.

PD-07 creates a tracked `.gitkeep` in each of the four feature roots. Each
feature marker records a later owner's implementation boundary; it remains in
the PD-07 handoff even when scaffold placeholder files are added. At the first
authorized implementation write, that feature's owner removes only their own
marker. Do not remove another domain's marker or treat the markers as feature
implementations.

A owns the cross-cutting app shell/navigation and shared presentation area:
`src/shared/ui/` and `src/shared/styles/`. The initial controls are `Button`
(primary/secondary presentation, native disabled state, and button type defaults
to `button`), `PageFrame` (shared main-content width and spacing), and
`SegmentedControl` (a controlled single-choice switch whose caller owns the
selected value and content). They are exported from `src/shared/ui/index.ts`.
`src/shared/styles/tokens.css` defines the common typography, spacing, color,
content-width, and control-radius values. `global.css` applies those values,
base document styling, and visible keyboard focus. Shared controls/styles have
one maintained source so a central change reaches all consumers. Detailed
screen behavior and styling remain with the features.

For a bounded shared UI/interface edit, the current writer identifies affected
consumers and gets review from the relevant feature contributors. A page or
route addition still requires human approval. No contributor edits another
feature's private implementation as an integration shortcut.

## Significant cross-domain connections

This table identifies the connection and its eventual contract work. It does
not define final component props, API signatures, caches, or event payloads.

| Connection | Feature responsibilities and user-visible result | Contract / state question to resolve later |
|---|---|---|
| Discovery/saved/match result → listing summary/detail | C owns the query or saved state; B owns authoritative listing/availability/images. The page arrangement must provide a declared display connection without reaching into a feature's private code. | DL-00 chooses supported listing reads or the approved Search projection and synchronization. Listing-summary display boundaries are verified in PD-07 Step 3. |
| Listing detail/result → save action | C owns save/unsave while B supplies listing context. The same saved state must remain coherent across detail, discovery, and saved view. | DL-00 assigns UI state ownership, refresh/invalidation, response/errors, idempotency and expired-session behavior; SE-02 implements it. |
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

## ID-01 Step11 first UI checkpoint

Aditya is the reserved current writer on task/id-01-identity for Identity feature
exports and bounded Identity page/shell composition. `/sign-in` now uses public
`SignIn`; `App` supplies public `IdentityProvider` and the shell uses public
`IdentitySessionControl`. The existing IdentityPlaceholder export remains for
unchanged marketplace compositions. No route/private feature boundary changes.
The first visible increment supplies temporary sign-in/registration/OTP and
session/logout controls. `/auth/callback`, password reset and `/account/contacts`
remain original Step11 pending checkpoints. Human desktop/phone-layout checks
are pending; actual-phone keyboard/provider/deployed acceptance remains open.

The explicit development-only identity-preview mode uses a fixed loopback proxy
and synthetic test inbox with actual disposable Identity SQL/HTTP. It rejects
build/deployment of that mode; normal builds eliminate the test inbox module.
Normal development does not enable this proxy; unconfigured backend main is
still health-only. See [first checkpoint evidence](../evaluation/identity/id-01-step-11/README.md).

### ID-01 Step11 recovery increment

After Aditya verified the first sign-in screen, the same reserved Identity writer
adds forgot-password/request-code/reset states inside `/sign-in`; no new route,
page composition or public feature prop change. API requests use the reviewed
reset-specific operations, generic acknowledgement and single-use proof; reset
issues no new session. Human recovery/portrait/landscape verification remains
pending. Microsoft callback and private contact editor remain later Step11 work.

### ID-01 Step11 private contact editor increment

Aditya continues as sole reserved Identity/page writer after verified recovery
checkpointbcfff32. AccountContactsPage now composes public ContactsEditor on its
existing route. Existing Identity placeholder/props/session exports remain
compatible; other feature/private/page connections are unchanged. Contact values
stay inside an actor-keyed own editor, with CSRF writes and confirmed refetch;
known logout/account changes unmount private drafts and fence late responses.
There is no general profile/directory or Conversation contact-sharing endpoint
or client bypass. Actual CN-02 deliberate sharing remains its original gate.
Human contact-editor desktop/phone/browser verification is pending.

### ID-01 Step11 Microsoft UI increment

Aditya remains reserved Identity/shared-page writer. SignIn composes its private
Microsoft button through the shared submission guard; AuthCallbackPage now uses
public MicrosoftCallback. Existing public feature exports and all approved routes
remain. New own-controller lazily selects only the real pinned SDK, with explicit
origin/build activation and unconditional synthetic-preview disablement. Callback
success requires one server exchange; safe status recovery uses IdentityProvider's
generation fence. The provider refresh result now returns a current SessionView
or null while existing callers may ignore it. No other feature private imports.
The app's no-referrer HTML metadata protects redirect material; shared-owner/peer
review remains before integration. Live provider activation is separately gated.
