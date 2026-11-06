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

The route/page composition files connect public feature exports; domain behavior
stays in feature-owned components and APIs. Current paths are `src/app/router.tsx`,
`src/app/AppShell.tsx`, `src/pages/ScaffoldPages.tsx`,
`src/pages/ConversationRuntime.tsx`, and `src/pages/ConversationOffers.tsx`.

### Public feature entry points

| Owner | Public entry point | Examples of exported behavior |
|---|---|---|
| A — Identity | `src/features/identity/index.ts` | Sign-in/session, contacts, seller eligibility, account boundary, Handle setup/editor |
| B — Listings | `src/features/listings/index.ts` | Listing create/detail/edit, owner listings, authorized image preview and listing actions |
| C — Search | `src/features/search/index.ts` | Sale discovery/cards, Wanted browse/management/detail, Saved listings |
| D — Conversations | `src/features/conversations/index.ts` | Inbox/thread pages, encryption/session, read acknowledgements, unread count and listing-selection ports |

Import these public indexes across feature boundaries. Pages compose the
features; they do not reach into another feature's private implementation. A
shared page, API or style edit needs one named writer and review from affected
owners under `CONTRIBUTING.md`.

## Cross-domain boundaries

- Identity owns authentication, current account capabilities and private
  contact editing. A visible control is never authorization; the server checks
  current trusted session state.
- Listings owns listing state, availability and image storage/delivery. Search
  consumes Listings' public summary/image interfaces and never reads its tables.
- Search owns discovery, Wanted Requests and Saved state. Conversation creation
  and persistence belong to Conversations and are reached through its public
  operation.
- Conversations owns private messages, offers, read acknowledgements and
  notification event/read-state interfaces. Contact values come from Identity
  only after deliberate participant selection; notification email is handled
  through the reviewed public provider boundary.
- Keep payment, item quality, delivery and handover claims out of the UI. CLIP
  does not verify them. The optional notification centre and optional search
  enhancements are not part of the selected required scope.

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

## Current status and maintenance

The page inventory above records the approved route surfaces and domain owners.
The [work log](../status/work-log.md) is the status source; the
[domain task list](../tasks/domain-task-list.md) and current contracts own
behavior and acceptance details. This map carries no active writer reservation
or historical task gate. Refresh actual code and owner assignments before a
future shared-page change.
