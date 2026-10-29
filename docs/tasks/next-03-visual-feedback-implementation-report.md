# NEXT-03 visual-feedback implementation and verification report

The combined correction batch is committed at `6700cb2` and integrated locally
with fetched `origin/main` at `a60c83f` in a no-commit merge. Suraj confirms the
full NEXT-03 visual walkthrough is complete, including the Step 0.5 A21 layout
corrections. The post-integration pinned `make check` passed on 2026-10-29.
Owner/independent peer review and merge remain pending. This report includes
earlier correction work as well as the full follow-up batch.

## Current inspection handoff

- URL: http://127.0.0.1:5176/__inspection
- Launcher PID: `3122258`; synthetic photos: `/tmp/clip-marketplace-inspection-nocf1mhm/`.
- Fixtures: 29 photo-backed sale listings, 27 Wanted Requests and 77 conversations, including 24 bicycle threads. Six main actor buttons include `new-member` for incomplete Handle setup; 22 `pagination_XX` peers exercise continuation/waiting-for-setup states.
- Main messaging actors start without published browser keys in this fresh run. Use separate seller and buyer browser profiles and follow the [walkthrough](next-03-step-10-visual-checklist.md). The preceding browser-test database was discarded.

## Checks actually run

The following checks were recorded before the origin integration and are
historical evidence, not substitutes for the passing post-integration aggregate
below.

| Check | Result |
|---|---|
| `make check` with pinned Node/npm and uv on PATH | Passed all 12 stages; log `/tmp/clip-feedback-final-accepted.log`. |
| Python suite within that full check | 1,936 passed; 155 explicitly gated scenarios skipped. |
| Data tests | 94 passed. |
| Frontend within that full check | 493 passed; 3 opt-in HTTP tests skipped; lint, type checking and production build passed. |
| Final `npm run check`, including unread account-isolation and compact-card action regressions | 495 passed; 3 skipped; lint/typecheck/build passed. |
| Database safety | 35 simulated-wrapper safety cases passed. |
| Disposable PostgreSQL migration checks | PostgreSQL 18.6 clean/head/repeat, seven smokes, Identity upgrade/atomicity/rollback, protected retirement rollback and full reapply passed. |
| Supplemental Handle migration and privilege checks | Legacy valid/missing/invalid/case-colliding names and IDs preserved; claim uniqueness and down/reapply passed; a consumer role could read the public view but not Identity users/contacts. Log `/tmp/clip-handle-upgrade-final.log`. |
| Conversations PostgreSQL suite | Full check: 168 passed. Added multi-page unread-backlog/read-watermark check afterward: focused suite 169 passed, log `/tmp/clip-conversations-handoff.log`. |
| Contracts, boundaries and types | All eight generated artifacts current; registry/schema, Python/TypeScript consumer and boundary checks passed. |
| Secret scan | Gitleaks 8.30.1 source snapshot passed within the full check and again after the final report/docs updates. |
| Seeded application action sweep | All 24 groups passed with actual local sessions, stores and pinned Hybrid inference. Fresh-run evidence `/tmp/clip-next03-corrections-final.log`; 29 sale listings, 27 Wanted Requests, 77 conversations. |
| Real Chromium | No horizontal overflow at 360/390/1440 pixels; three sale-card actions share one centered row at each width. All visible conversation groups start collapsed; phone pagination stays in one row; no browser console errors. Detailed measurements: `/tmp/clip-next03-visual-check-corrections.log`. |
| Real browser crypto | Encrypted Enter send, offline-peer setup/resume, global unread count, stable unread divider and selective encrypted contact delivery passed after the final chat rearrangement. Log `/tmp/clip-feedback-crypto-final.log`. |

### Post-integration pinned verification — 2026-10-29

`make check` passed on the integrated working tree after resolving origin/main
conflicts and repairing affected upstream Identity and conversation tests:

| Stage | Exact result |
|---|---|
| Python | 2,019 passed, 156 skipped in 407.64s |
| Data tests | 94 passed in 1.41s |
| CI parity / formatting / boundaries / contracts | Passed; Black 316 files unchanged, zero boundary violations, eight generated contracts current |
| Contract types | Mypy passed on two source files |
| Web lint and tests | Biome clean on 142 files; 496 passed, 3 skipped; 45 test files passed, 2 skipped |
| Web typecheck and production build | Passed; Vite reports existing large chunks above 500 kB |
| Database safety | 35 simulated-wrapper safety/wiring cases passed |
| Disposable PostgreSQL | PostgreSQL 18.6 clean/head/repeat, seven smokes, Handle legacy/collision/rollback/reapply, Identity upgrade/atomicity/rollback, protected retirement rollback and full clean reapply passed |
| Conversations retirement | 169 passed against fresh PostgreSQL 18.6 |
| Secret scan | Gitleaks 8.30.1 source snapshot passed |

Final aggregate log: `/tmp/clip-postintegration-aggregate.log`. The native
macOS migration script remains syntax-checked but not executed on this WSL host.
Hosted CI and hosted production/browser behavior are not verified by local
checks. Current staged/unstaged diff review and owner/independent peer review
are still required before opening a PR; cloud deployment gates remain open.

Intermediate failures were retained and corrected: old profile/registry/label assertions, synthetic CSRF/session/retirement setup, and supplemental-test fixture isolation. Two full frontend runs each timed out in a different existing test under unrestricted worker concurrency; the affected Microsoft test passed independently. Four-worker concurrency removed the resource contention without increasing timeouts or weakening tests; the later full check and final frontend aggregate passed. The build retains its existing large-bundle advisory.

The standard frontend skips are the two Wanted native HTTP cases and one opt-in cookie/CSRF HTTP case. Their absence is reported explicitly; the local action sweep, Python integration and real browser checks supply separate evidence rather than relabelling skipped tests as passed. Native-platform/provider/calibration cases remain gated where their prerequisites are not selected. No cloud, paid inference or live provider delivery was performed.

## Step 0.5 — follow-up visual corrections, 2026-10-29

After reviewing the local inspection screenshots, Suraj requested three small
layout corrections before Git integration: keep desktop navigation balanced,
reserve the Original price row on sale cards that have no value, and align the
conversation context, thread and offers on one left-aligned column. The Open
listing action now has visible separation from its context card. `AppShell.css`
uses the full bounded shell width and centers wrapped links; `SaleListingCard.tsx`
and `discovery.css` reserve an accessible-hidden price row; `ScaffoldPages.tsx`,
`ConversationThread.css`, and `ConversationOffers.css` compose and style the
conversation surfaces consistently. `discovery-controls.test.ts` and
`conversation-composition.test.tsx` cover the new markup and composition.

Verification on Node 24.22.0/npm 11.19.1: the targeted test run passed 12 tests;
the complete frontend `npm run check` passed lint, 496 tests (3 skipped across 2
files), both TypeScript projects, and the production build. `git diff --check` passed. Vite
still reports the existing large-chunk advisory. Suraj visually approved the
Step 0.5 desktop navigation, sale-card price-row and conversation alignment
corrections in the refreshed synthetic inspection app on 2026-10-29. The complete NEXT-03 walkthrough is confirmed done. NEXT-04 audit is scheduled after
post-integration checks and before PR preparation, per Suraj's direction.

## Code and configuration file report

Canonical `contracts/source` files were edited, then registered runtime declarations, OpenAPI and TypeScript artifacts were regenerated. Existing real email/OTP provider implementations and the pinned Identity17 runner review package are unchanged. The integrated application must receive the forward migration and public-view grants before a future release; that cloud apply is separately gated.

| File | Purpose and relationship |
|---|---|
| [apps/api/app/contracts/domain_types.py](../../apps/api/app/contracts/domain_types.py) | Regenerated from the canonical contract sources: Handle/session flags, safe participant fields, grouped query controls and the unread aggregate operation. |
| [apps/api/app/domains/conversations/public.py](../../apps/api/app/domains/conversations/public.py) | Regenerated from the canonical contract sources: Handle/session flags, safe participant fields, grouped query controls and the unread aggregate operation. |
| [apps/api/app/domains/conversations/queries.py](../../apps/api/app/domains/conversations/queries.py) | Filters authorized memberships by marketplace intent, pages groups before bounding their rows, joins only the safe Identity participant view and aggregates unread peer messages. |
| [apps/api/app/domains/conversations/routes.py](../../apps/api/app/domains/conversations/routes.py) | Registers the authenticated unread-count route before dynamic conversation IDs and validates the extended inbox query through the reviewed model. |
| [apps/api/app/domains/identity/cleanup.py](../../apps/api/app/domains/identity/cleanup.py) | Clears Handle completion when the owning Identity cleanup redacts a profile, preserving the new database invariant. |
| [apps/api/app/domains/identity/contacts.py](../../apps/api/app/domains/identity/contacts.py) | Claims/edits trimmed ASCII Handles with database-backed case-insensitive uniqueness; savepoints translate concurrent conflicts safely without lifetime changes. |
| [apps/api/app/domains/identity/http.py](../../apps/api/app/domains/identity/http.py) | Projects the Handle-completion flag in safe session responses; existing authentication, CSRF and email delivery behavior is retained. |
| [apps/api/app/domains/identity/sessions.py](../../apps/api/app/domains/identity/sessions.py) | Reads Handle completion with the locked account and carries that server truth through session creation/authentication. |
| [apps/api/tests/domains/identity/test_contacts.py](../../apps/api/tests/domains/identity/test_contacts.py) | Regression coverage for contacts: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/api/tests/domains/identity/test_contacts_http.py](../../apps/api/tests/domains/identity/test_contacts_http.py) | Regression coverage for contacts http: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/api/tests/domains/identity/test_identity_cleanup.py](../../apps/api/tests/domains/identity/test_identity_cleanup.py) | Regression coverage for identity cleanup: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/api/tests/domains/identity/test_identity_http.py](../../apps/api/tests/domains/identity/test_identity_http.py) | Regression coverage for identity http: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/api/tests/domains/identity/test_identity_security_integration.py](../../apps/api/tests/domains/identity/test_identity_security_integration.py) | Regression coverage for identity security integration: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/api/tests/test_conversation_directory.py](../../apps/api/tests/test_conversation_directory.py) | Seeds 21 unread conversations in one group and verifies the returned rows expose the full group total even though the displayed row set is capped at 20. |
| [apps/web/src/app/AppShell.css](../../apps/web/src/app/AppShell.css) | Bounds the shell and implements compact sticky mobile navigation, readable account controls and nonwrapping Sign out. |
| [apps/web/src/app/AppShell.tsx](../../apps/web/src/app/AppShell.tsx) | Composes required Handle setup, device-key setup, account controls, mobile menu and one shared unread poll for desktop/mobile badges. |
| [apps/web/src/features/conversations/ConversationContactPreparation.css](../../apps/web/src/features/conversations/ConversationContactPreparation.css) | Feature-owned responsive spacing, bounded widths, card geometry, touch targets and readable controls; uses the shared color/spacing tokens. |
| [apps/web/src/features/conversations/ConversationContactPreparation.tsx](../../apps/web/src/features/conversations/ConversationContactPreparation.tsx) | Keeps selective encrypted contact consent and retry behavior, with direct contact-settings setup/return access and clearer control layout. |
| [apps/web/src/features/conversations/ConversationInbox.css](../../apps/web/src/features/conversations/ConversationInbox.css) | Styles bounded origin groups and the persistent unread badge; strengthens group dividers and keeps group/page controls responsive. |
| [apps/web/src/features/conversations/ConversationInbox.tsx](../../apps/web/src/features/conversations/ConversationInbox.tsx) | Renders All/Buying/Selling and Item/Person modes; item/person groups start collapsed, keep context visible, and show the full unread total beside the group title. |
| [apps/web/src/features/conversations/ConversationKeySetup.css](../../apps/web/src/features/conversations/ConversationKeySetup.css) | Feature-owned responsive spacing, bounded widths, card geometry, touch targets and readable controls; uses the shared color/spacing tokens. |
| [apps/web/src/features/conversations/ConversationKeySetup.tsx](../../apps/web/src/features/conversations/ConversationKeySetup.tsx) | Keeps first-device setup explicit and account-isolated, with optional contacts access and clear key-loss/readiness states. |
| [apps/web/src/features/conversations/ConversationPages.tsx](../../apps/web/src/features/conversations/ConversationPages.tsx) | Orchestrates group/row paging, safe participant context, selected-buyer Handle/offer, bounded history windows, and passes group unread totals to the inbox. |
| [apps/web/src/features/conversations/ConversationThread.css](../../apps/web/src/features/conversations/ConversationThread.css) | Feature-owned responsive spacing, bounded widths, card geometry, touch targets and readable controls; uses the shared color/spacing tokens. |
| [apps/web/src/features/conversations/ConversationThread.tsx](../../apps/web/src/features/conversations/ConversationThread.tsx) | Adds Enter/Shift+Enter safeguards, a stable opening unread divider and one date separator per day; scrolls to the bottom after a successful send or retry while preserving failed-send retries. |
| [apps/web/src/features/conversations/ConversationUnreadBadge.tsx](../../apps/web/src/features/conversations/ConversationUnreadBadge.tsx) | Reads the authorized unread aggregate every five seconds while visible; aborts on account change and fences late responses; renders reusable count badges. |
| [apps/web/src/features/conversations/api.ts](../../apps/web/src/features/conversations/api.ts) | Preserves reviewed query serialization, adds bounded older-entry page sizing, and validates the additive group unread count while accepting older responses without it. |
| [apps/web/src/features/conversations/index.ts](../../apps/web/src/features/conversations/index.ts) | Exports the reviewed public feature components/types used by route composition; consumers do not import private feature implementations. |
| [apps/web/src/features/identity/HandleSetup.tsx](../../apps/web/src/features/identity/HandleSetup.tsx) | Requires a valid unique Handle for incomplete accounts, supports later editing, preserves drafts on conflict, refreshes session truth and aborts writes on unmount. |
| [apps/web/src/features/identity/api.ts](../../apps/web/src/features/identity/api.ts) | Identity: retains the Handle-completion session field and supports abortable protected profile requests. |
| [apps/web/src/features/identity/index.ts](../../apps/web/src/features/identity/index.ts) | Exports the reviewed public feature components/types used by route composition; consumers do not import private feature implementations. |
| [apps/web/src/features/listings/ListingDetail.tsx](../../apps/web/src/features/listings/ListingDetail.tsx) | Shows optional Original price with the Seller Provided label and owner-only management controls. |
| [apps/web/src/features/listings/ListingDetailOwnerActions.tsx](../../apps/web/src/features/listings/ListingDetailOwnerActions.tsx) | Loads authoritative owned listing state before exposing edit/availability actions and refreshes after changes. |
| [apps/web/src/features/listings/StartListingConversationAction.tsx](../../apps/web/src/features/listings/StartListingConversationAction.tsx) | Adds a compact browse-card label while keeping the accessible action name “Message seller”; listing details retain the full button label. |
| [apps/web/src/features/listings/MyListings.tsx](../../apps/web/src/features/listings/MyListings.tsx) | Composes the shared sale card and owner actions in the same bounded responsive collection geometry as discovery. |
| [apps/web/src/features/listings/index.ts](../../apps/web/src/features/listings/index.ts) | Exports the reviewed public feature components/types used by route composition; consumers do not import private feature implementations. |
| [apps/web/src/features/listings/listings.css](../../apps/web/src/features/listings/listings.css) | Feature-owned responsive spacing, bounded widths, card geometry, touch targets and readable controls; uses the shared color/spacing tokens. |
| [apps/web/src/features/search/SaleDiscovery.tsx](../../apps/web/src/features/search/SaleDiscovery.tsx) | Adds the sale-create action, shared card actions and an initially expanded collapsible search panel retaining applied query/filter context. |
| [apps/web/src/features/search/SaleListingCard.tsx](../../apps/web/src/features/search/SaleListingCard.tsx) | Provides one compact image/body/card presentation for discovery, saved, owner, matches and draft preview, with independent actions and clamped text. |
| [apps/web/src/features/search/WantedViews.tsx](../../apps/web/src/features/search/WantedViews.tsx) | Aligns Wanted cards/budgets/actions, bounds creation/editing, moves draft matches above Description with hide/show, and adds collapsible discovery controls. |
| [apps/web/src/features/search/discovery.css](../../apps/web/src/features/search/discovery.css) | Keeps sale-card badges content-sized and places Save/Message/View in one centered row below the image and item details at phone and desktop sizes. |
| [apps/web/src/features/search/index.ts](../../apps/web/src/features/search/index.ts) | Exports the reviewed public feature components/types used by route composition; consumers do not import private feature implementations. |
| [apps/web/src/features/search/wanted.css](../../apps/web/src/features/search/wanted.css) | Feature-owned responsive spacing, bounded widths, card geometry, touch targets and readable controls; uses the shared color/spacing tokens. |
| [apps/web/src/pages/ConversationOffers.css](../../apps/web/src/pages/ConversationOffers.css) | Feature-owned responsive spacing, bounded widths, card geometry, touch targets and readable controls; uses the shared color/spacing tokens. |
| [apps/web/src/pages/ConversationOffers.tsx](../../apps/web/src/pages/ConversationOffers.tsx) | Composes authorized offer reads with Listings public mutations and clearer bounded input/action presentation. |
| [apps/web/src/pages/ScaffoldPages.tsx](../../apps/web/src/pages/ScaffoldPages.tsx) | Connects public feature actions and eligibility, uses the compact Message action on sale browse cards, and composes owner controls, Handle editing and shared conversation-origin context. |
| [apps/web/src/shared/styles/global.css](../../apps/web/src/shared/styles/global.css) | Applies bounded page content, consistent navigation-link appearance and dark warning/error colors. |
| [apps/web/src/shared/styles/tokens.css](../../apps/web/src/shared/styles/tokens.css) | Feature-owned responsive spacing, bounded widths, card geometry, touch targets and readable controls; uses the shared color/spacing tokens. |
| [apps/web/src/shared/ui/MultiChoiceDropdown.css](../../apps/web/src/shared/ui/MultiChoiceDropdown.css) | Feature-owned responsive spacing, bounded widths, card geometry, touch targets and readable controls; uses the shared color/spacing tokens. |
| [apps/web/src/shared/ui/MultiChoiceDropdown.tsx](../../apps/web/src/shared/ui/MultiChoiceDropdown.tsx) | Uses native details/checkboxes with outside-pointer and Escape dismissal, focus return and retained selections. |
| [apps/web/src/shared/ui/SegmentedControl.css](../../apps/web/src/shared/ui/SegmentedControl.css) | Feature-owned responsive spacing, bounded widths, card geometry, touch targets and readable controls; uses the shared color/spacing tokens. |
| [apps/web/tests/app-shell-navigation.test.tsx](../../apps/web/tests/app-shell-navigation.test.tsx) | Regression coverage for app shell navigation: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/conversation-composition.test.tsx](../../apps/web/tests/conversation-composition.test.tsx) | Regression coverage for conversation composition: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/conversation-thread-interactions.test.tsx](../../apps/web/tests/conversation-thread-interactions.test.tsx) | Regression coverage for conversation thread interactions: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/conversation-unread-badge.test.tsx](../../apps/web/tests/conversation-unread-badge.test.tsx) | Regression coverage for conversation unread badge: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/conversations-done-deal.test.tsx](../../apps/web/tests/conversations-done-deal.test.tsx) | Regression coverage for conversations done deal: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/conversations-inbox.test.tsx](../../apps/web/tests/conversations-inbox.test.tsx) | Regression coverage for conversations inbox: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/conversations-ui.test.ts](../../apps/web/tests/conversations-ui.test.ts) | Regression coverage for conversations ui: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/discovery-controls.test.ts](../../apps/web/tests/discovery-controls.test.ts) | Regression coverage for discovery controls: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/handle-setup.test.tsx](../../apps/web/tests/handle-setup.test.tsx) | Regression coverage for handle setup: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/identity-marketplace-state.test.tsx](../../apps/web/tests/identity-marketplace-state.test.tsx) | Regression coverage for identity marketplace state: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/listing-conversation-start.test.tsx](../../apps/web/tests/listing-conversation-start.test.tsx) | Regression coverage for listing conversation start: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/listings-save-lifecycle.test.tsx](../../apps/web/tests/listings-save-lifecycle.test.tsx) | Regression coverage for listings save lifecycle: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/multi-choice-dismissal.test.tsx](../../apps/web/tests/multi-choice-dismissal.test.tsx) | Regression coverage for multi choice dismissal: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/tests/wanted-controls.test.ts](../../apps/web/tests/wanted-controls.test.ts) | Regression coverage for wanted controls: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [apps/web/vitest.config.ts](../../apps/web/vitest.config.ts) | Limits concurrent workers to four to avoid observed worker starvation; keeps every assertion, test and timeout unchanged. |
| [contracts/generated/openapi.json](../../contracts/generated/openapi.json) | Regenerated from the canonical contract sources: Handle/session flags, safe participant fields, grouped query controls and the unread aggregate operation. |
| [contracts/generated/types.gen.ts](../../contracts/generated/types.gen.ts) | Regenerated from the canonical contract sources: Handle/session flags, safe participant fields, grouped query controls and the unread aggregate operation. |
| [contracts/source/conversations.py](../../contracts/source/conversations.py) | Registers the new unread aggregate HTTP operation alongside the extended inbox query and safe summary types. |
| [contracts/source/types.py](../../contracts/source/types.py) | Defines the additive session, participant, grouping and unread models used by both server and generated client types. |
| [database/migrations/20261029043000_unique_handles_and_participant_projection.sql](../../database/migrations/20261029043000_unique_handles_and_participant_projection.sql) | Preserves all legacy names and IDs, claims only valid unambiguous Handles, enforces valid case-insensitive claims and exposes only safe participant fields; down removes its own schema additions. |
| [database/tests/native-checks.sh](../../database/tests/native-checks.sh) | Regression coverage for native checks: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [scripts/check_boundaries.py](../../scripts/check_boundaries.py) | Allows Conversations SELECTs through exactly Identity participant_profiles; still rejects private Identity tables and cross-domain writes. |
| [scripts/check_conversations_retirement.py](../../scripts/check_conversations_retirement.py) | Uses the new integrated head and runs the real disposable PostgreSQL Conversations regression suite. |
| [scripts/check_database.py](../../scripts/check_database.py) | Checks the current integrated head plus legacy missing/invalid/colliding Handle preservation, uniqueness, rollback/reapply and least-privilege projection access. |
| [scripts/identity_local_demo.py](../../scripts/identity_local_demo.py) | Grants the local integrated role access to the public participant view without granting private Identity tables. |
| [scripts/marketplace_inspection.py](../../scripts/marketplace_inspection.py) | Seeds the six main actors, incomplete onboarding, temporary requester, photos, sale/Wanted fixtures and 24 bicycle threads; runs 24 real local action groups before serving. |
| [tests/architecture/test_boundaries.py](../../tests/architecture/test_boundaries.py) | Regression coverage for boundaries: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [tests/contracts/test_domain_declarations.py](../../tests/contracts/test_domain_declarations.py) | Regression coverage for domain declarations: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |
| [tests/contracts/test_generation.py](../../tests/contracts/test_generation.py) | Regression coverage for generation: aligns approved Handle/label/schema behavior and checks the relevant authorization, state or interaction boundaries. |

## Acceptance and remaining gates

The visual-feedback plan ledger records A21 as visually approved and Suraj
confirms the complete desktop/phone walkthrough is done. Local task-wide review
covers preserved changes, public frontend/domain boundaries, generated outputs,
migration/data preservation and privilege checks, account/session isolation,
encrypted contacts/messages, fixtures, responsive layout, failure evidence and
secret scanning.

## Origin integration and cloud audit checkpoint — 2026-10-29

Fetched `origin/main` at `a60c83f` and reconciled it with this branch in a
no-commit merge. Conflicts were resolved while retaining both branch and current
upstream documentation/evidence; no migration filename conflict occurred. The
current tree contains 29 SQL migrations while the upstream Identity runner
deliberately accepts only its unreviewed exact 23-file candidate. The earlier
17-file live package still needs separate owner review. Do not apply the shared
database: owner review and a reviewed exact migration candidate are required.

The first post-integration `make check` found 31 Python failures (1,988 passed,
156 skipped); the pinned tools were then found in the recorded WSL tool directory.
Integration fixture repairs passed the affected Identity/Conversations suite
(42 tests) and migration/operator group (41 tests). A subsequent aggregate retry passed Python (2,019 passed, 156 skipped), data
(94 passed), parity, Black, boundaries, contracts, contract types and web lint,
but one D14 scroll interaction test asserted before its React effect. The test
now waits for the effect and passed its nine-test file three times; a complete
frontend check and fresh aggregate are pending. The native macOS migration script passed `bash -n` but cannot be run
on this WSL host. Both cached and unstaged `git diff --check` passed.

The renewed non-root `surajs2` profile identifies the project account. The
[read-only cloud refresh](../environment/cloud-inventory.md#next-04-read-only-refresh--2026-10-29-1208-utc)
confirms SES sending enabled, stopped API/ASG and private stopped RDS, issued ACM
certificate and private image-bucket protections. The target hostname did not
resolve here; Terraform drift, authoritative/IISc DNS and hosted behavior remain
unverified. Historical Step13 evidence records
Microsoft and temporary-account sign-in/reset flows, HTTPS and secure-cookie
checks; a separate SES test recorded a real submission and inbox receipt, while
SES production access/sending, DKIM success and a standalone test receipt were
recorded on 2026-10-28; older pending statements are stale. The current SES
route preference and effective role/recipient policy were not read. There is a
source readiness gap for general production email: `config.py` rejects SES and
Microsoft in `production`, `runtime_configuration.py` only assembles the hosted
test profile from `/clip/test/...`, and `email.py` only sends to its bounded
controlled-recipient list. No cloud setting or live send was changed.

Step14's latest closeout says Aditya reports the remaining capability matrix
verified; the earlier phrase “durable grant handling” referred to restoring two
narrow PostgreSQL grants after a clean bootstrap: UPDATE on
`listings.categories.created_at` and `listings.conditions.label`, with no
table-wide UPDATE. The live grants were applied; the guarded restoration helper
was tested on disposable PostgreSQL. Aditya's later closeout report says the
remaining matrix was verified, superseding the earlier pending checkpoint. The
formal ID-01 record still calls for independent review and current-revision
closeout; I did not independently repeat those checks. Hybrid is Search-owned
and has no positive hosted
pass; helper/model/worker and automatic vector updates remain unverified. The
latest recorded inventory says the API and ASG are
stopped, RDS is stopped, DNS deletion was user-confirmed, synthetic listing/
image and narrow catalogue grants remain, and shared NAT/storage may continue
to incur charges. These are historical records, not current-state verification.
No cloud mutation or email send occurred.

### Integration repair files

- `apps/web/tests/conversation-thread-interactions.test.tsx` waits for the
  post-render scrolling effect before asserting D14; `listing-conversation-start.test.tsx`
  scopes message-action errors to that action rather than unrelated page alerts.

- `apps/api/tests/domains/identity/test_consumer_capability_matrix.py` updates
  the listing replacement and Handle fixtures, follows the settled independent
  buyer-selection/availability behavior, and gives the disposable Conversations
  principal read access to the safe participant view.
- `apps/api/tests/domains/identity/migration_fixtures.py` copies the pinned
  23-file manifest into a temporary test directory; `postgres_fixtures.py`
  uses that directory for isolated operator tests while ordinary application
  tests still use the full branch chain.
- `tests/test_identity_bootstrap.py` and `tests/test_identity_bootstrap_review.py`
  run their 23-file candidate against that isolated copy; the catalogue-grant
  and Conversations-role tests use the same pinned disposable database. Live
  runner and operator guards are unchanged.
- Two historical Step12 JSON receipts are restored byte-for-byte from Git
  history because upstream guard/review tests import them. They record past
  evidence and do not authorize a new operation.
- `database/tests/native-checks.sh` and `database/README.md` now count and roll
  back all 29 branch migrations; the native script remains unexecuted on WSL.

The eventual NEXT-04 target remains the complete app at https://clip-iisc.site
except Notifications for this scope. Provider promotion, Identity migration and
grant review, HTTPS/origin, Hybrid worker/model/vector flow, image permissions,
and hosted-browser checks remain release gates. Arrange affected-owner and
independent peer review with [the review prompt](../prompts/peer-review-prompt.md)
before any later merge authorization.

Before this origin reconciliation, Black 26.10.1 reported 299 files unchanged;
contract check reported all eight artifacts current; final source-snapshot
Gitleaks passed; `git diff --check` passed. Those results do not replace the
missing post-integration pinned aggregate.
