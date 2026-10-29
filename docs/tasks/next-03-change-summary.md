# NEXT-03 change summary

**Updated:** 2026-10-29 UTC
**Branch at handoff:** `task/integrated-marketplace-rollout`
**Committed batch:** `6700cb2` (`feat: complete NEXT-03 marketplace correction batch`)
**Working tree:** A no-commit integration of `origin/main` at `a60c83f` is in progress, with integration fixes and handoff updates uncommitted. Inspect `git status` and the full diff before committing. Suraj confirms the complete NEXT-03 visual walkthrough is done.

This document summarizes the intended product changes and current evidence. The
[visual-feedback plan](next-03-visual-feedback-plan.md) is the detailed behavior
decision record, and the [implementation report](next-03-visual-feedback-implementation-report.md)
has the file-by-file change inventory and verification evidence. The
[walkthrough](next-03-step-10-visual-checklist.md) is the local inspection guide.

## Product and data changes

- Settled a nine-category catalogue and aligned stable codes, labels, the
  reference dataset distribution and proposed example topics. The forward
  category migration adds Sports & Fitness and updates two labels without
  reclassifying existing records. It has not been applied to a shared/cloud DB.
- Sale discovery supports multi-select category and condition filters (OR within
  each filter; AND across filters), with URL/history state and page reset when
  applied filters change. Listing creation/editing still assigns one category
  and one condition. No condition ranking was invented.
- Search is Hybrid in product use. Sale search retains Best Match for nonblank
  text, plus deliberate newest/price sorts. Negotiability was removed from user
  filters but remains visible as Negotiable or Fixed price. Relevance/result
  inclusion quality is recorded as a possible later optimization.
- Wanted Requests have create/edit, owner availability and public discovery
  search by title/description, category multi-select, inclusive optional budget
  bounds, URL/history and pagination. A budget bound excludes requests without
  a stated budget. Draft matching reuses sale discovery and preserves drafts on
  failure. New Wanted Request is reachable from the main navigation and
  Discovery.
- Original price is optional seller-provided information, distinct from asking
  price and negotiability. It appears on approved sale card/detail/owner/preview
  surfaces and is omitted when absent. Shared sale-card rendering keeps draft
  preview aligned with browse cards.
- Owner controls are available on listing and Wanted detail pages after
  ownership is confirmed. Buyer selection remains private seller tracking;
  Mark as done deal is the action that changes sale availability.

## Identity and conversations

- Required unique Handle reuses the existing display-name field. It is captured
  during setup, editable later and enforced case-insensitively in the API and
  database. A safe participant projection supplies Handle and temporary-account
  class to Conversations without exposing email or querying private Identity
  tables. A forward migration preserves account IDs and safely handles legacy
  values. The migration has passed disposable PostgreSQL upgrade/rollback/
  reapply and privilege checks; it has not been applied in cloud.
- Account setup gates marketplace use when the current browser has no encryption
  key. Users receive the key-loss warning and an explicit fresh-key path; a new
  key does not claim to recover old ciphertext. Contacts remain optional and
  selectively shared through encrypted messages.
- Conversations support All/Buying/Selling views and Item/Person grouping,
  recent-activity order, bounded group/page/history controls, five initially
  visible rows when expanded, and groups collapsed by default. Each collapsed
  group can show the total unread count across all its conversations, including
  beyond the 20-row response cap. Conversation context uses title, price/budget,
  image when available, Handle and Temporary marker rather than UUIDs/emails.
- Threads support Enter to send, Shift+Enter for a newline, unread boundary/date
  presentation, contact-sharing unread accounting, and scrolling to the bottom
  after a successful send or retry. Inbox/thread, offer, contact and key setup
  presentation was tightened for phones and bounded wide screens.

## Shared presentation and inspection

- Shared responsive sale cards serve Discovery, Saved, My Listings, preview and
  matches; browse actions are centered in one row beneath card content. Wanted
  cards/details use a more consistent treatment, with budget in the price
  position and clamped descriptions. Listing facts use labelled, divided,
  responsive rows after the description.
- Shared UI updates cover aligned multi-select labels, outside-click/Escape
  dismissal, bounded layouts, phone navigation, button/link treatment, collapsible
  search controls, dark color-token support and improved spacing.
- Step 0.5 balances desktop navigation, reserves the Original price row on sale
  cards when no price is supplied, aligns conversation context, thread and offer
  surfaces to the left, and adds spacing after Open listing.
- Local synthetic inspection provides sale/Wanted fixtures, buyer-owned records,
  photos, pagination peers and six account types. The latest clean run passed 24
  real local action groups against real sessions, PostgreSQL stores and the
  pinned Hybrid search path. Current handoff data: 29 sale listings, 27 Wanted
  Requests and 77 conversations.

## Verification and limits at handoff

The checks below predate the origin integration; current results are recorded in
the implementation report and work log.

- Full `make check` passed: Python 1,936 passed/155 skipped; data 94 passed;
  frontend 493 passed/3 skipped plus lint, typecheck and production build;
  contract, boundary, database safety and migration checks passed; Conversations
  PostgreSQL suite 168 passed; Gitleaks passed.
- Final frontend check after the compact card action change: 495 passed/3
  skipped. Expanded Conversations PostgreSQL suite: 169 passed. Supplemental
  Handle migration/privilege checks passed. Chromium checked 360px, 390px and
  1440px layouts; all three sale actions fit one centered row, inbox groups are
  initially collapsed, and there was no horizontal overflow or console error.
- Suraj confirmed the complete NEXT-03 visual walkthrough is done, including
  the Step 0.5 corrections. PR review and merge remain separate. The inspection app was handed off at
  `http://127.0.0.1:5176/__inspection`; its launcher PID and temporary photo
  directory are listed in the implementation report. Do not assume the server
  survives a session restart.
- No cloud deployment, shared/cloud database apply, paid experiment or real
  provider delivery occurred. Notifications remain excluded from this delivery.
  Chat image attachments and optional search-relevance refinement remain
  unselected optional work.
- `database/migrations/20261029043000_unique_handles_and_participant_projection.sql`
  is part of the committed NEXT-03 batch. The pinned Identity 17-migration
  live-review package is unchanged and still requires separate owner review.
  Check both migration histories against current remote `main` before preparing
  a PR or any future deployment.

## Handoff instruction

Continue with [the NEXT-03 PR and cloud-readiness handoff prompt](../prompts/next-03-pr-and-cloud-readiness-handoff.md).
