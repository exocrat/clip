# NEXT-03 pre-PR package

**Draft title:** Complete marketplace controls, visual feedback and planning handoff

**Target:** `main` at fetched base `a60c83f`. The source branch is
`task/integrated-marketplace-rollout`; its origin integration is resolved in
the staged index, but the merge commit is pending human approval under
`CONTRIBUTING.md`. The reviewed staged comparison is 666 paths (12,107
insertions, 49,574 deletions), including the earlier planning/docs cleanup
described below. There is no PR head or hosted CI yet. Refresh `origin/main`
and update the exact head before opening the PR.

## Draft PR description

NEXT-03 makes the main marketplace flows usable across discovery, listings,
Wanted Requests, accounts and private conversations, and incorporates the
complete local visual-feedback batch.

- Align the nine-category catalogue and dataset labels. Add forward migrations
  for catalogue changes, wanted text search, optional seller-provided Original
  price, the price/budget cap, private buyer selection and unique Handles.
- Support multi-select category/condition discovery filters, shareable URL and
  history state, and page resets. Keep Hybrid as the product search, with Best
  Match for nonblank queries and newest/price choices; show Negotiable or Fixed
  price on cards while removing the negotiability filter from the website.
- Complete Wanted create/edit/discovery and owner availability controls, keyword
  and category search, inclusive budget bounds, pagination and draft-preserving
  campus matches. Add owner edit/availability controls on sale details and
  quick Save/Message and Contact actions in discovery. Original price remains
  optional seller-provided information. Selecting a buyer is private tracking;
  Mark as done deal changes sale availability.
- Collect and edit a case-insensitively unique Handle, preserving legacy account
  IDs and staged legacy names. Use a limited participant projection for Handles
  and Temporary badges without exposing email or private Identity tables. Gate
  marketplace navigation on first-device encryption-key setup, explain lost-key
  limitations, and retain selective encrypted contact sharing.
- Add All/Buying/Selling conversation views, Item/Person grouping, recent-activity
  sorting, collapsed groups, group pagination and group-wide unread counts even
  beyond the initial page. Show compact listing/request context, offer and seller
  controls; support first-unread positioning, date dividers, Enter to send,
  Shift+Enter for a newline and scrolling after successful sends and retries.
- Apply the visual feedback across desktop and phone: responsive shared sale
  cards and Wanted cards, centered card actions, a reserved empty Original price
  row, balanced desktop navigation and sticky mobile menu, bounded page widths,
  compact labelled listing facts, consistent links/buttons and dark tokens,
  dismissible multi-select controls, collapsible search filters and matches,
  improved inbox grouping/pagination, and aligned conversation context, thread,
  contact and offer areas with spacing after Open listing. Suraj confirms the
  full NEXT-03 visual walkthrough is complete.
- Reconcile current main's Identity tests with the changed listing and Handle
  contracts, run historical migration-guard tests against their pinned 23-file
  candidate, retain the historical receipts those tests need, and test the
  participant-view grant locally. The live migration and grant guards remain
  separate deployment approvals.
- Include the earlier NEXT-00/NEXT-01 planning handoff and NEXT-02 documentation
  cleanup already on this branch. The cleanup removes a large set of historical
  evaluation artifacts from the working tree; their history remains in Git.
  Links reintroduced by newer main records point to their exact historical base
  revision, and two receipts needed by current Identity tests were restored.

The detailed behavior ledger and file inventory are in
[the visual-feedback plan](next-03-visual-feedback-plan.md) and
[implementation report](next-03-visual-feedback-implementation-report.md).
Notifications, chat-image attachments and optional relevance tuning are excluded.

## Checks and review gates

- Post-integration pinned `make check` passed locally: Python 2,019 passed/156
  skipped; data 94 passed; web 496 passed/3 skipped across 45 passing and 2
  skipped files; Biome lint clean on 142 files; TypeScript and production build
  passed; Black 316 files unchanged; zero boundary violations; all eight
  contracts current; mypy two source files passed; database safety 35 passed;
  disposable PostgreSQL 18.6 migration lifecycle passed; Conversations
  retirement 169 passed; Gitleaks 8.30.1 passed. Vite emitted its large-chunk
  advisory. The native macOS migration check was syntax-checked but not run on
  WSL. Hosted CI and hosted production/browser behavior remain unverified; bind
  CI evidence to the final PR base/head after publication.
- Obtain affected-owner review from Aditya (Identity), Suraj (Listings), Mohit
  (Search/Wanted/Saved), and Rahul (Conversations); designate an independent
  human peer reviewer who is not the author. Suraj says Aditya will review the PR;
  that review is still pending. Supply
  [the peer-review prompt](../prompts/peer-review-prompt.md), resolve findings,
  and record approvals against the final revision.
- The 17-file Identity live package needs separate owner review; an exact
  29-migration deployment package must be prepared and reviewed. Category/Handle migrations and participant-view grants
  have only local evidence; no shared database apply is authorized.
- Production SES general-recipient Identity support is deferred by Suraj.
  DNS/HTTPS, current Terraform drift, Hybrid model/worker and automatic vectors,
  runtime grants, operations and hosted end-to-end checks remain deployment
  gates. No cloud deployment or live email is implied by this PR.
- Human approval of the exact staged diff is required before the integration
  commit under `CONTRIBUTING.md`; task authorization alone does not grant it.
  A separate explicit authorization of the exact reviewed PR revision is
  required before merge.
