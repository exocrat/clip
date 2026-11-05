# NEXT-03 — visual feedback and agreed correction scope

**Current disposition (2026-11-05 15:26:56 UTC): Aditya marks NEXT-03 complete. Earlier pending/checkpoint statements below are historical; this status update records his direction and does not add new execution evidence.**

**Source:** Suraj's desktop inspection feedback, including four screenshots and
his follow-up about My Listings card consistency, search, identity, optional work
and an unattended overnight correction batch, 2026-10-28 UTC; mobile visual
inspection feedback and the global width constraint, 2026-10-29 UTC.
**State:** The full NEXT-03 correction batch, including the Step 0.5 layout fixes,
is committed at `6700cb2`; Suraj confirms the functional Conversations demo and
has visually approved A21 (desktop navigation, reserved Original price row, and
left-aligned conversation context/thread/offers with spacing). Suraj confirms
the complete NEXT-03 visual walkthrough is done (2026-10-29). The full remaining correction list
is authorized by Suraj’s latest “Do everything until my visual inspection in
one go” instruction, including Buying/Selling modes, group pagination, unread
counts/positioning and unique Handle migration. Cloud deployment/configuration
and optional OPT-04/OPT-05 remain deferred. This batch ends at an updated, tested
local inspection handoff for Suraj, not a cloud operation.

**Current execution scope:** Suraj's first visual inspection found that several
implemented behaviors still fail the requested presentation and that account
key setup needs a clearer missing-key entry flow. NEXT-03 is reopened for the
post-inspection corrections below. The inspection server at
http://127.0.0.1:5176/__inspection remains the intended final visual review
surface, but must be rebuilt/reseeded after corrections. Cloud work and
unselected optional work remain deferred. All content remains bounded on
ultrawide screens; mobile is the primary layout target. Raw email and UUIDs are
not participant display labels.

## Mandatory execution discipline

Before **every implementation step**, reopen this plan and its decision table,
identify the applicable group and acceptance items, and check the latest work-log
checkpoint. Do this again after a context reset or handoff; do not rely on memory.
Before reporting a step complete, reread its items, verify the observed behaviour
and update the checkpoint/coverage evidence. Every new correction must trace to
this plan or explicit subsequent user direction. Preserve the grouped scope;
there are no intermediate human confirmation stops during the authorized batch.
The final stop is a rebuilt, checked, seeded environment ready for human visual
inspection. Keep the per-task status ledger below current; after each task, update
both this plan and the work-log checkpoint before moving to the next one.

## Per-task status ledger

Statuses reflect current implementation and evidence. A task marked done may
still receive regression coverage when a related shared surface changes. Update
each row when work begins and when it is complete.

| ID | Feedback task | Current status | Scope note |
|---|---|---|---|
| A1 | Fix multi-select checkbox/label layout, scrolling and phone sizing | implemented, locally checked, and visually verified by Suraj | Sale/Wanted category controls now keep checkbox/text on one row; 44px row targets and viewport-bounded scrolling menus. Old conversation origin/partner pickers are addressed in D3. |
| A2 | Reuse sale card in Discover, Saved, My Listings, preview and matches | implemented, locally checked, and visually verified by Suraj | The shared component is wired, but screenshots show My Listings width/visual density still needs to match Discover. A12 owns the compact responsive geometry. |
| A3 | Align Wanted card/detail styling, price placement, compact/clamped description | implemented, locally checked, and visually verified by Suraj | Neutral treatment and budget hierarchy are implemented; recheck compactness and consistency with sale cards under A12. |
| A4 | Make sale/Wanted cards navigate from their main area safely | implemented, locally checked, and visually verified by Suraj | Sale/Wanted title anchors cover their card body; action areas stay above the link. Conversation origin groups link across the box; row buttons still open threads. |
| A5 | Bound wide forms and improve responsive spacing/buttons | implemented, locally checked, and visually verified by Suraj | Wanted/key/offer/contact forms received bounds and spacing, but A11 now applies the maximum-width rule globally and A15 covers button sizing/alignment. |
| A6 | Clean navigation and place account controls well | implemented, locally checked, and visually verified by Suraj | Desktop route set and account placement remain; A16 adds a sticky collapsible mobile navigation. |
| A7 | Add symmetric New Listing action in sale discovery | implemented, locally checked, and visually verified by Suraj | Sale discovery accepts the composition-supplied New Listing action; the route supplies it only for an eligible regular seller. |
| A8 | Preserve Best Match only for nonblank text search | implemented, locally checked, and visually verified by Suraj | Existing logic and URL behavior are implemented; add no unrelated sort change. |
| A9 | Modest conversation/key/contact/offer presentation pass | implemented, locally checked, and visually verified by Suraj | Key/contact/offer spacing exists, but Suraj reports that the thread and inbox still look poor; revisit the compact responsive hierarchy under D8 without expanding into NEXT-09. |
| A10 | Consider small token-based dark mode | implemented, locally checked, and visually verified by Suraj | A compact `prefers-color-scheme: dark` override switches the shared color tokens and native control scheme; final browser review will check real screens and contrast. |
| A11 | Bound page content and layouts on very wide screens | implemented, locally checked, and visually verified by Suraj | No page, form, card, reading column or action row should stretch indefinitely with viewport width. Use a shared maximum content width and responsive grids; preserve usable widths on phones. |
| A12 | Compact horizontal listing and Wanted cards with responsive multi-column browse | implemented, locally checked, and visually verified by Suraj | Use a larger, useful image at the left and title/price/status/actions at the right on phones; use multiple cards per desktop row. Keep My Listings on the same card/grid geometry as Discover, Saved and preview. |
| A13 | Close multi-choice dropdowns on outside click | implemented, locally checked, and visually verified by Suraj | Any pointer/touch outside the open dropdown closes it; Escape closes it too. Clicking an option still changes the selection, and closing does not clear selected values. |
| A14 | Let people collapse search and filter controls | implemented, locally checked, and visually verified by Suraj | Expanded on first visit. After search/filtering, allow explicit hide/show while keeping a visible Search & filters label and readable active-query/filter summary. Do not erase or silently change the URL-backed search state. |
| A15 | Make links and creation actions visually consistent | implemented, locally checked, and visually verified by Suraj | All navigational links use the agreed button-like styling while remaining links semantically; New Listing and New Wanted Request use matching compact sizing. Put actions side by side whenever the available width supports it. |
| A16 | Replace the tall mobile navigation wrap with a sticky menu | implemented, locally checked, and visually verified by Suraj | On narrow screens, keep a compact sticky menu button available during scroll and reveal navigation on demand. Keep the full desktop navigation at wider sizes. |
| A17 | Present listing details as compact labelled facts | implemented, locally checked, and visually verified by Suraj | After the description, lay out remaining facts in a visibly divided, table-like responsive presentation: multiple labelled columns where they fit and stacked rows on phones, preserving definition-list semantics. A19 records the post-inspection correction. |
| B1 | Original price on all approved sale surfaces | implemented, locally checked, and visually verified by Suraj | Create/edit, browse and detail/My Listings are implemented and checked. |
| B2 | Browse Save and Contact actions | implemented, locally checked, and visually verified by Suraj | Sale cards now compose compact Save/Unsave and Message seller actions; Wanted cards provide Contact requester for eligible regular sessions. Existing APIs remain authoritative and no email is exposed. The integration test scopes message-action errors to their own control when owner-controls errors are also present. |
| B3 | Owner edit/availability actions on sale detail | implemented, locally checked, and visually verified by Suraj | Load owner-only management state for the signed-in account; show actions only after ownership is confirmed. |
| B4 | Owner availability/edit actions on Wanted detail | implemented, locally checked, and visually verified by Suraj | Confirm ownership through the caller's private Wanted pages before showing Edit, Mark unavailable or Reopen; never trust the public detail ID. |
| B5 | Show Possible campus matches before Wanted submission | implemented, locally checked, and visually verified by Suraj | Reuse sale-card presentation; suggestions now appear before Publish and preserve draft/error behavior. |
| B6 | Move Possible campus matches above description with a hide/show control | implemented, locally checked, and visually verified by Suraj | B5 moved matches before Publish but did not meet the requested prominence. Show them above Description by default when available; keep a labelled match count/control visible when collapsed and preserve the draft. |
| B7 | Simplify the buyer-facing Original price qualifier | implemented, locally checked, and visually verified by Suraj | On browse cards and listing details, show the concise label `Seller Provided`; remove the repeated “unverified” qualifier there. Do not change the separate proof-of-purchase meaning. |
| C1 | First-device encryption setup and account-isolated key storage | done | Committed and real-browser checked; Suraj confirms the functional demo. |
| C2 | Private buyer tracking separate from availability/done deal | done | Committed migration and local workflow checks; no cloud apply. |
| C3 | Unique Handle capture, uniqueness and migration | implemented, locally checked, and visually verified by Suraj | Previously excluded from the earlier correction batch. This remains on the task list: capture required Handle during first setup; edit it later; enforce trimmed 3–30 ASCII letters/digits/underscore and case-insensitive uniqueness in API and database; safely transition legacy/colliding accounts without changing IDs; verify concurrent claims, migration/reapply/rollback on disposable PostgreSQL; expose Handle through a reviewed Identity participant projection for conversation and selected-buyer context. |
| C4 | Temporary-account conversation marker | implemented, locally checked, and visually verified by Suraj | Suraj clarified the existing identity rule: a verified peer email outside the exact `iisc.ac.in` domain identifies a temporary account. Use authoritative Identity account class or a server-computed safe class based on that validator; expose only the Temporary badge, never the email. ConversationSummary now carries safe participant Handle/class from Identity’s public participant_profiles projection; private Identity tables are not read. |
| C5 | Contact settings setup/return path and encrypted selective sharing | done | Committed and covered by functional checks; retain regression coverage. |
| D1 | Recognizable conversation origin, contextual links and modest layout | implemented, locally checked, and visually verified by Suraj | Titles/prices/photos and origin links are wired, but screenshots show the groups lack distinct boxes, have excess vertical space and undersized sale photos. A12 and D8 require compact recognizable group cards. Show participant Handle after C3 and the Temporary badge after C4 projection; keep IDs internal. |
| D2 | Buying/Selling and Item/Person conversation modes | implemented, locally checked, and visually verified by Suraj | Newly included in the full remaining batch. Implement All/Buying/Selling semantics and Item/Person grouping from the settled D4 decision; derive roles from trusted membership/origin context and retain server authorization. |
| D3 | Remove visible origin/partner multi-selects; compact existing controls | implemented, locally checked, and visually verified by Suraj | Visible pickers and the empty disclosure are removed. A working Clear saved filters control remains only for legacy filter state; default recent-activity ordering is preserved. |
| D4 | Group-preserving inbox pagination and advanced grouping redesign | implemented, locally checked, and visually verified by Suraj | Page origin/person groups as units; initially show five conversation rows per group with independent Show more/Hide controls. Keep message-history pagination separate. Define stable activity ordering, counts and page resets in reviewed contracts/tests. |
| D5 | Enter sends; Shift+Enter newline with IME/readiness/retry safeguards | implemented, locally checked, and visually verified by Suraj | Enter sends through the existing encrypted send path; Shift+Enter, IME composition, repeat keys, unready state and concurrent sends are guarded. Failed sends retain their stable retry operation. |
| D6 | Navigation unread count and unread message positioning | implemented, locally checked, and visually verified by Suraj | Keep the authorized account-scoped count and display-based acknowledgements. Open with the preceding text message when available, then the `X unread messages` divider; count contact-sharing entries, remove the opening divider after the current user sends, and use one centered date separator per day plus compact time-only message labels. Keep bounded history and do not force jumps while reading older messages. D11 records the refined behavior. |
| D8 | Distinct, compact conversation group cards | implemented, locally checked, and visually verified by Suraj | Give each origin a bounded card surface with a clear title, larger useful sale image, price/budget, origin action and contained conversation rows; remove the large empty gaps. Show selected buyer Handle/current offer/thread action once C3 is available. Wanted groups need equally clear title/budget and visual separation without a fake photo. |
| D7 | Offer and seller-selection presentation/actions | done | Core flow, seller context and availability separation are committed and browser checked. |
| A18 | Correct post-inspection browse-card density and badges | implemented, locally checked, and visually verified by Suraj | Shared cards now keep the image/details side by side on phones, use content-sized chips, and place the centered Save/Message/View actions below the full card content. Phone/desktop Chromium measurements confirm one action row at 360px, 390px and 1440px without horizontal overflow. |
| A19 | Make listing facts visibly tabular after description | implemented, locally checked, and visually verified by Suraj | Uses a labelled, divided fact layout with responsive columns/rows; the 390px browser check confirms it has no horizontal overflow. |
| C6 | Make Account handle missing encryption-key state first | implemented, locally checked, and visually verified by Suraj | Rename Contact settings to Account. On login/device use, detect absent local key material and make key setup the first required account action before marketplace features; hide marketplace navigation while the gate is active. Explain that a lost key cannot restore old encrypted data. Allow creating a fresh key when absent without claiming it restores old threads. Keep Handle setup in first-account onboarding and provide account-level key creation when absent. |
| D9 | Clarify conversation mode/group controls and compact per-group rows | implemented, locally checked, and visually verified by Suraj | View and Group by remain separate, groups are distinct and collapsed by default, expansion begins with five rows, and separators are thicker with more space. Inbox unit tests verify the collapsed header and expansion behavior. |
| D10 | Compact phone pagination controls | implemented, locally checked, and visually verified by Suraj | Previous, Page and Next remain in one responsive row; the 390px browser check measures a single 40px-high row. |
| D11 | Refine unread boundary and message timestamps | implemented, locally checked, and visually verified by Suraj | The preceding-message/unread boundary, send-to-clear behavior, contact-share unread count, centered date separators and compact time labels are covered by the prior browser and current full-suite checks. |
| S1 | Make inspection data cover buyer-owned records | implemented, locally checked, and visually verified by Suraj | The fresh launcher seeds buyer-owned sale and Wanted records; its current sweep confirms 29 sale listings, 27 Wanted Requests and the buyer-owned request in My Wanted Requests. The checklist asks Suraj to verify both My Listings tabs. |
| A20 | Put sale-card actions in one centered row beneath the image and details | implemented, locally checked, and visually verified by Suraj | Save, Message (compact phone label with the accessible name “Message seller”) and View listing sit together in one centered full-card row below the photo and listing details. This keeps all three labeled actions on one line at 360px, 390px and desktop width, replacing the former two-row phone stack and saving a row of vertical space. |
| A21 | Finish desktop navigation, sale-card price-row alignment, and conversation detail alignment | implemented, locally checked, and visually approved by Suraj on 2026-10-29 | Added by Suraj after reviewing the local handoff on 2026-10-29. Center desktop navigation links within the full bounded shell width; reserve the Original price row when absent so descriptions align; place listing context, thread, tools and offers in one left-aligned route column with visible context spacing. Suraj approved these corrections in the refreshed synthetic inspection app. |
| D12 | Start item/person conversation groups collapsed | implemented, locally checked, and visually verified by Suraj | Groups default closed; the header remains visible, and opening one starts with five rows. The inbox UI tests cover the default and expansion. |
| D13 | Show each group’s total unread messages while collapsed | implemented, locally checked, and visually verified by Suraj | The summary contract returns the authorized group aggregate across all conversations before the per-group 20-row display cap. A fresh PostgreSQL regression seeds 21 unread conversation rows and verifies all 20 returned rows report the full total of 21. The inbox badge stays in the visible header when collapsed. |
| D14 | Scroll the thread to a newly sent message | implemented, locally checked, and visually verified by Suraj | A successful send scrolls the transcript to its bottom after updated entries render; the same is done after a successful retry. Failed sends keep the draft/position and existing retry behavior. A focused UI test verifies the new entry is in view; after integration it waits for the React scroll effect instead of asserting before that effect has run. |
| E1 | Keep search qualification stable under sort and verify cutoff behavior | done | Existing tests and programmatic search checks passed. |
| E2 | Search relevance refinement/common-word tuning | deferred | OPT-05 is unselected; fix only a demonstrated correctness defect. |
| G1 | Cloud deployment/readiness actions | deferred | User explicitly said leave cloud deployment now. |

## A. Shared presentation and mobile layout

- Fix every multi-select: checkbox and left-aligned text on one row, consistent
  spacing, accessible labels, touch targets, scrolling and narrow-screen sizing.
  Clicking/tapping outside closes an open picker; Escape closes it too. Preserve
  selections when the panel closes. Restyle remaining consumers; do not retain
  obsolete inbox multi-selects just to restyle them (D supersedes their earlier
  inclusion).
- **Global width rule:** no page, form, card, text line, filter panel or action row
  should expand indefinitely on an ultrawide display. Use a shared maximum content
  width and responsive multi-column layouts. Keep individual cards/forms bounded
  within that frame, use available width side by side, and avoid horizontal page
  scrolling on narrow screens. Review every route, not just discovery.
- Share the core sale card across Discover, Saved, My Listings, draft preview and
  possible matches. Owner views may add status/actions without a separate design.
- Align Wanted cards/details with sale styling; remove garish blue treatment;
  place budget or Budget not stated in the amount position. Use a compact
  horizontal phone card with photo on the left and details/actions on the right;
  use multiple cards per desktop row. Keep My Listings at the same card/grid width
  as Discover. Clamp long descriptions and retain condition, price and status.
- Make the main area of cards/groups navigate, with independently usable action
  buttons and keyboard access; avoid nested interactive elements or accidental
  navigation on Save/Contact. Every navigational link should look like the agreed
  button style while retaining link semantics, open-in-new-tab and browser history;
  do not leave underlined text links where the agreed button-like treatment applies.
- Keep New Listing and New Wanted Request actions visually symmetric and compact.
  Put independent actions side by side whenever the viewport has room; let them
  wrap cleanly on a phone instead of stretching one CTA across the page.
- Keep search and filters expanded on initial discovery. Let users collapse them
  after searching, with a clear persistent “Search & filters” control and a
  visible summary of the active query/filter state while collapsed. The hidden
  state must not hide or reset the search itself.
- On phones, replace the tall wrapping navigation with a compact sticky menu
  button available during scroll. Its expanded menu must be easy to dismiss and
  must not consume the whole screen after selection. Retain the normal desktop nav.
- Bound listing detail content. After the full description, use compact responsive
  labelled key/value rows for remaining facts: columns where they fit, stacked on
  phones. Prefer definition-list semantics to a literal table.
- Bound Wanted form widths like sale forms. Review all over-wide forms, large
  full-width buttons, excessive spacing and headers. Mobile is the primary target;
  verify portrait/landscape, tablet and desktop without reducing usable tap sizes.
- Move Sign out/account controls to the top right. Remove sample ID/detail links.
  Agreed navigation: Discover, New Listing, New Wanted Request, My Listings,
  Saved, Conversations, Account; Sign in only when signed out. Auth
  callback remains a route without a navigation item. Saved access is retained (D6).
- Add New Listing within the sale discovery view, parallel to New Wanted Request.
- Best Match remains relevant only for nonblank search; retain the approved query/
  filter/sort transitions. No speculative change is needed just to expose it early.
- Follow-up screenshots: account encryption setup needs the same bounded page
  frame/margins as the rest of the app, not content flush against the viewport.
  Put consent text, checkbox and creation action in a clear form layout rather
  than appending a button immediately after a sentence. Offer amount/actions need
  consistent input sizing, label spacing, button gaps and responsive wrapping.
  Contact-sharing choices need readable checkbox rows and separated actions.
- Give the chat page a modest usability pass now (A9): clear message/composer/offer/
  contact hierarchy, comfortable margins and spacing, readable message bubbles/
  timestamps and usable small-screen composition. Keep effort bounded; the wider
  final visual refresh is NEXT-09 (NEXT-10 is optional-work review). Do not turn
  this checkpoint into an unbounded redesign or sacrifice mobile usability.
- Dark mode is a convenience only if a small change using existing colour tokens
  suffices; otherwise defer and record it, without delaying functional fixes.

## B. Listing and Wanted actions

- Investigate missing Original price on sale detail; verify optional/present/
  changed/cleared values on every approved surface, including My Listings.
- Add frequent browse actions: Save/Unsave and Contact seller/requester, subject
  to real eligibility/ownership. Keep complete actions on details; compact owner
  menus may expose Edit and availability from browse without overcrowding cards.
- Owner detail should expose Edit and availability controls, with consistent
  authoritative refresh across Discover/My Listings/Conversations.
- There is no Remove, deletion or archive feature in this batch. Provide Mark
  unavailable/Reopen and preserve owner history, conversations and safe saved
  references (D3). Apply relevant owner actions to Wanted details as well.
- Move Possible campus matches to a visible pre-submission position during Wanted
  composition, above the description, using the shared sale card. Show matches
  expanded when available and provide an explicit, labelled hide/show control;
  retain the match heading/count while collapsed. Preserve unsaved input and
  valid submission after match errors. Align Wanted/detail/creation styling and
  budget.
- On buyer-facing browse cards and listing detail, label Original price simply
  **Seller Provided**. Remove the repeated unverifiable qualifier from that public
  label; do not change the separate proof-of-purchase declaration.

## C. Identity, encryption and contacts — functional blocker

- Reproduce seller's Encryption is not ready failure and buyer's waiting-for-peer
  state with separate browser profiles. Diagnose actual key/session/IndexedDB/
  directory/SDK behaviour and fix the cause; cloud deployment is not a presumed
  fix. Prove both roles can actually send/read encrypted messages. Once a peer
  has completed setup/published keys, sending must not require that peer to have
  the thread open or be online. Check initial key publication, prekey availability,
  browser/profile isolation and explicit missing-key/recovery states.
- Distinguish the reported availability failure: selection was initially usable;
  the suspected defect arose after marking a listing available again. Check
  authoritative state, reload/polling, retries, revision conflicts and stale UI.
- Establish encryption keys during first-sign-in account setup, with the existing security/
  key-loss acknowledgement and optional contact setup. Define migration prompts
  for existing members who have not completed setup; do not repeat onboarding on
  ordinary subsequent sign-ins. A new browser/cleared local keys still needs an
  explicit device/recovery flow. Never silently replace keys or invent server-held keys.
- Reuse existing `display_name` as the **Handle**, not a second display-name field.
  It becomes required for completed first-sign-in setup and editable in profile/
  contact settings. Accepted rules: 3–30 ASCII letters, digits or underscores;
  trim surrounding whitespace; uniqueness is case-insensitive and enforced by
  the database as well as the API, including concurrent claims and edits.
- Review/update API validation, profile/session and participant projections,
  generated contracts, forms and errors consistently; UI wording says Handle.
  Preserve account IDs and all existing listings/conversations. Handle legacy
  missing, invalid, case-colliding and duplicate names through an explicit staged
  migration/setup transition; do not fabricate public handles or make existing
  accounts un-sign-in-able. Required final behaviour must not leave an optional
  handle for users who complete onboarding. Test migration and rollback/reapply
  only in disposable databases; shared/cloud apply remains separately gated.
- Show approved participant handle/account class instead of IDs. Public email
  disclosure was not approved and is not needed to implement this identity choice.
- Show a Temporary account badge in the relevant conversation context.
- If contacts are absent, provide Set up contact details and a safe return to the
  originating conversation. Verify selection/review/cancel/confirm, encrypted
  delivery, selected-fields-only and failures after messaging is working.

## D. Conversations, grouping, offers and selected buyers

- Replace user-visible UUID labels with origin title, suitable thumbnail/price
  and participant handle. Keep IDs as internal keys. Handle unavailable,
  retired, missing origin and pending legacy handles without leaking scrubbed content.
- Link each origin group and conversation back to its listing/request detail.
- Replace the old participation/type controls as the primary navigation with
  compact **All / Buying / Selling** mode buttons. These express marketplace
  intent, not who initiated a thread:
  - Buying = contacting someone else's sale listing OR owning the Wanted Request.
  - Selling = owning the sale listing OR responding to someone else's Wanted Request.
  - All includes both. Derive filters from trusted membership/origin context and
    retain server authorization independently. The old initiated/origin_owner
    API modes do not implement these meanings; update/add contracts deliberately.
- Group by **Item / Person** using a compact button switch; default Item shows
  recognizable origin boxes. Sale/Wanted become contextual origin labels, not
  another permanent primary selector competing with Buying/Selling. Each box/
  conversation must visibly identify origin title and counterpart handle, plus
  sale thumbnail/price where available. Do not substitute UUIDs for recognizable
  context or expose private email. Preserve safe unavailable/retired states.
- Remove origin and partner multi-selects from the visible inbox. Keep existing
  API query compatibility unless an explicit contract retirement is reviewed.
  Do not show an empty **Sort & Filter** control. If an audit finds real, useful
  controls to retain, put them behind a collapsed disclosure; on phones avoid a
  control panel pushing the chats below the fold.
  Audit existing controls and keep only justified ones: default recent activity;
  seller offer comparisons (status/highest/lowest) only where meaningful for a
  seller's sale-listing box. Do not carry every existing control into the new UI
  merely because the API supports it. Remove redundant old participation/type
  selectors and unnecessary global offer bounds from the visible UI.
- Correction of an earlier assistant claim: title/handle conversation search and
  an Unread filter **do not currently exist**. Neither is selected for addition
  by this feedback. The requested unread indicator is separate from filtering.
- Current ordering is already most-recent activity first (stable ID tie-break).
  Preserve this default. Group ordering should use latest matching conversation
  activity; offer sorting changes relevant rows within a sale box, not unrelated
  item-group priority. Filters refine conversations before grouping; keep private
  selected-buyer context understandable without silently overriding filters.
- Pagination has three layers. Current inbox pages flat conversations and then
  groups that page, which can split a box; replace it with paging over the boxes
  themselves. Initially show five rows per large box with independent Show more
  and Hide conversations controls. Message
  history within one thread is separately paginated; keep bounded loading of older
  history. Do not fetch all groups, all conversations or all message history to
  fake complete grouping. Stable ordering, changed-mode/filter page resets and
  authorized counts belong in the API/contract and regression checks.
- **Enter sends; Shift+Enter adds a newline.** Do not send during IME composition,
  on key repeat, when encryption is unready or while a send is pending. Keep the
  visible Send action for touch/accessibility and preserve existing stable retry
  operation/ciphertext behaviour. Phone keyboard behaviour needs actual inspection.
- Show an unread indicator/count in the main Conversations navigation in addition
  to existing per-conversation counts. Existing per-thread counts are not a global
  badge or an Unread filter. Use a clearly labelled unread-message count with
  the existing message/read-watermark semantics, not a count of groups/pages or
  offer/protocol events. Fetch it through an
  authorized aggregate/read contract (not just the current inbox page), bound its
  refresh, and clear private state on logout/account change.
- Open a thread around the first unread message, starting at the preceding text
  when available, with an **X unread messages** divider before the first unread
  entry. If fully read, open at the latest messages. Capture a stable opening
  read boundary so acknowledgements do not move the divider or jump the viewport.
  Hide the opening divider after the user sends a message. Contact-sharing entries
  count as unread. Show one centered date per local calendar day and only hour,
  minute and AM/PM for individual entries.
  Acknowledge only actually displayed entries. Do not auto-scroll someone reading
  older history when a new message arrives. Load the necessary bounded message
  window around unread state, including more than one page of unread messages;
  do not load the entire transcript to find the anchor. Test no unread, long
  unread backlog, arrivals during reading, reload, mobile and retention tombstones.
- Verify actual offer submit/revise/withdraw/resubmit, seller read, stale revisions,
  uncertain-write retries and unavailable-origin behaviour in the browser path.
- Existing approved selection behaviour atomically makes a listing unavailable:
  see [offer lifecycle](../decisions/offer-lifecycle.md), including its 2026-10-27
  selection clarification. Suraj has now approved replacing that coupling (D2).
  Update the canonical decision, contracts, persistence, APIs and UI/tests before
  depending on the new behaviour; preserve the earlier decision history.
- Approved replacement: selection is private seller tracking, highlights that
  buyer and their current offer (or no/withdrawn offer), sends no buyer signal,
  never changes availability, and is changeable/clearable even while unavailable
  if the origin/thread remains valid and non-retired. Preserve it across reopen.
  Surface the selected handle/current offer and a direct thread action in the
  seller group, not merely inside its thread. Selection must not create buyer
  notifications, acceptance markers or unread events.
  Mark as done deal alone makes unavailable, regardless of selection; no payment,
  reservation, offer-acceptance or handover claim is added.

## E. Search verification and deferred improvements

Verified in `app/domains/listings/hybrid_read.py`: a listing qualifies through an
original text match OR expanded text match OR semantic_score >=0.35. Semantic
score blends title0.35 and description0.65. Qualification precedes pagination,
and Newest/price use that same predicate. Lexical expansion preserves all query
term groups; it is not a simple any-word match. Common synthetic words can affect
semantic similarity, but the exact reason each observed card appeared has not
been measured. Do not claim that the word Inspection alone proved the cause.

Absence of the literal word does not guarantee exclusion: Hybrid intentionally
supports meaning-based matches. A below-cutoff listing with no original/expanded
match is excluded. Wanted uses its separate strict all-terms text rule.

The existing disposable PostgreSQL suite was rerun for this question: 22 passed,
three explicitly gated native/model/calibration cases skipped, with full migration/
rollback/reapply checks passed. Its Hybrid SQL scenarios exclude a nonlexical result scoring 0.315 (below
0.35) and retain the same four qualifying results under relevance, Newest and
both price directions. This verifies the eligibility
mechanism; it is not a relevance-quality judgement on every observed preview card.

Suraj permits deferring relevance improvements if exclusion exists. Track tuning,
common-word handling, meaningful no-results and labelled comparisons in OPT-05.
Any demonstrated failure to preserve eligibility under sorting remains a bug in
this correction batch; do not defer a correctness defect as optional tuning.

## F. Deferred optional work

- Chat images are not implemented in the current thread UI. OPT-04 defines their
  future actual E2EE/storage/UI/security/retention work; defining it does not
  authorize implementation in this correction batch.
- OPT-05 records relevance/inclusion refinement for later. Existing OPT-01 weekly
  digest, OPT-02 Wanted-match alerts and OPT-03 image-aware search remain distinct
  and unselected. Optional selection requires its own capacity/cost approval.
- Dark mode follows A's small-change-only rule; record deferral if it is not small.

## G. Deferred cloud-readiness audit — recorded, not current execution

Suraj explicitly deferred cloud deployment/configuration for now. The target
remains the complete app at https://clip-iisc.site except Notifications for this
scope. This section preserves the read-only repository findings; it does not
assert live AWS state or authorize configuration, secret access, migration apply,
image deployment, paid runs or removal of production safeguards.

- The normal application factory mounts Conversations/Identity/domain routes and
  same-origin /api; the synthetic inspection launcher is not the deployment path.
- Hosted real Identity bindings for the exact HTTPS origin already exist in
  `identity/runtime_configuration.py` and the shared ECS service configuration.
  Current application settings deliberately allow this as a controlled test
  profile, reject production Microsoft integration, and restrict SES/Resend to
  a small approved recipient list. Test mode here can use real providers; it does
  not imply fake authentication/email.
- Suraj reports **SES production access granted on 2026-10-28**. This removes the
  reported AWS sandbox blocker but does not change the application's separate
  allowlist/environment checks. Preserve the working real email/OTP implementation;
  a later reviewed promotion must retain verification, abuse/rate limits, safe
  secret handling and failure behaviour. Do not simply delete guards now.
- The base API Docker build defaults Microsoft's frontend enable flag to false;
  the actual release must deliberately build the enabled configuration. Actual
  deployed image settings were not inspected in this audit.
- `apps/api/Dockerfile.hybrid` already provides pinned interpreter/model and real
  offline inference checks. Select/verify this release path and the activated
  database vector pipeline, resource limits and same-target domain grants; the
  ordinary API image alone does not provide that model runtime.
- Identity requires HTTPS request semantics. Verify TLS termination, the exact
  browser origin, secure cookies/CSRF, restricted trusted-proxy handling, public
  routing, CSP/browser crypto and static assets. The checked-in private shared
  service does not by itself establish the full public HTTPS route. Do not trust
  arbitrary forwarded headers to make this work.
- Apply reviewed forward migrations before the matching application release and
  verify least-privilege roles for all integrated domains. The pinned Identity17
  owner review and exact shared/cloud apply gates remain separate.
- Browser keys stay client-side; HTTPS supplies a secure context. Localhost and
  clip-iisc.site have separate origin storage, so cloud users perform first setup
  there. Do not copy local private keys to the server or silently replace them.
  Preserve stable account IDs and existing same-origin keys across releases;
  verify send/read/reload/contact flows in actual deployed browsers afterward.
- Live AWS configuration, credentials, deployed grants/image, public proxy wiring
  and end-to-end hosted behaviour remain unverified. Code/configuration components
  are largely present, but deployment readiness is not certified by local success.

## Recorded product decisions

| ID | Question | Decision/status |
|---|---|---|
| D1 | What identity replaces email/UUID labels? | Settled: Handle only, reusing `display_name`; required at first setup and editable in profile/contact settings. 3–30 ASCII letters/digits/underscores, surrounding whitespace trimmed, case-insensitive database-enforced uniqueness. No separate display name or new username field; preserve IDs/references and provide a safe legacy setup transition. No public email disclosure. |
| D2 | What exactly does Select buyer mean? | Private tracking only, no availability change or buyer notification/disclosure; pin/highlight selected buyer and live offer; allow change/clear for valid non-retired origins before/after done deal; retain on reopen. Only Mark as done deal changes availability. |
| D3 | What should Remove listing do? | Settled by Suraj: no removal/deletion/archive feature. Mark unavailable/Reopen only; preserve history and conversations. |
| D4 | Inbox modes, grouping and controls? | Revised by later feedback: All/Buying/Selling buttons (Buying=sale initiator or Wanted author; Selling=sale owner or Wanted responder), compact Item/Person grouping, default recent activity, recognizable origin/handle context. Remove visible origin/partner multi-selects and redundant participation/type selectors. Remove Sort & Filter while empty; only show it collapsed when real, useful controls exist. No new title/handle search or Unread filter. Page boxes and bound expanded rows; message-history paging stays separate. |
| D5 | When must encryption setup finish? | Settled: first-sign-in setup, not repeated at every login. Require ready keys before publishing a sale or starting/responding in chat; contacts optional. Existing incomplete accounts get a setup prompt; missing device keys require explicit recovery/setup, never silent replacement. |
| D6 | Keep access to Saved? | Keep Saved in navigation (compact icon/button allowed); remove sample links and hide Auth callback from navigation while retaining its route. |
| D7 | Execution scope and operating rules? | Current batch authorization (2026-10-28), expanded by the screenshot follow-up (2026-10-29): complete the listed non-deferred visual and functional corrections, perform local verification, prepare inspection data/instructions and stop for Suraj's visual review. C3 Handle, D2 modes, D4 box pagination and D6 unread/first-unread were included by the later full-batch authorization and are now implemented and locally checked. Consult this plan before every implementation task and update its status plus the work-log checkpoint after each. No intermediate confirmations. No cloud, paid work, merge or deployment. |
| D8 | Chat interaction and unread presentation? | Enter sends, Shift+Enter newline with IME/pending-send safeguards. The navigation unread indicator, first-unread opening anchor and stable X unread messages divider are implemented as D6 using display-based read acknowledgement, latest position when fully read and no forced jump during older reading. Add modest chat/onboarding/offer/contact spacing now; broader final polish remains NEXT-09. |
| D9 | Cloud/SES work now? | Deferred at Suraj’s instruction. SES production access is user-reported as newly granted; application restrictions still need later reviewed promotion. Preserve G’s audit findings and real email behaviour, but perform no cloud/configuration/deployment changes in this batch. |

## Full remaining task list and status

This list keeps the already-authorized visual corrections and the three
higher-reasoning follow-ups visible together. “Corrective visual pass requested”
means code exists but the screenshots showed a specific gap; it is not considered
verified until corrected and inspected. “Queued” means the task remains required
in this plan but was excluded from the earlier batch. The newest screenshot
feedback expands the pending work; it does not mark any new visual item complete.

### 1. Shared layout, cards, forms and navigation — A1–A17

- **A1** Fix every multi-select row layout, touch sizing, scrolling and mobile
  behavior; close on outside click or Escape without clearing selections.
- **A2–A4** Use the same sale card across Discover, Saved, My Listings, preview
  and matches; align Wanted cards/details; make card bodies navigate while
  keeping their Save/Contact/owner actions independently usable.
- **A5, A11** Bound every route, form, card, reading column, filter area and
  action row with a shared maximum content width so ultrawide screens never
  create indefinitely long lines. Reflow gracefully on narrow screens without
  horizontal page scrolling.
- **A12** Make cards compact and horizontal on phones, with a useful left image
  and right-side details/actions; show multiple cards per desktop row. Match My
  Listings geometry to Discover, Saved and preview; clamp long descriptions and
  retain price, condition and status.
- **A6, A16** Clean the desktop navigation/account placement and replace the
  tall mobile link wrap with a compact sticky, dismissible navigation menu.
- **A7, A15** Give New Listing and New Wanted Request matching compact actions;
  place them side by side when there is room. Style all navigational links as
  buttons while preserving link semantics/history and make action spacing
  consistent.
- **A8** Keep Best Match available only for nonblank searches and preserve
  search/filter/sort state transitions.
- **A14** Keep search and filters open initially; let users collapse them later
  while the control and active query/filter summary remain visible.
- **A17** Put listing detail facts after the description in an accessible,
  responsive labelled definition-list/grid, with columns when space permits.
- **A9** Improve chat, encryption setup, offer and contact-sharing presentation
  with clear hierarchy, margins, readable controls and mobile wrapping.
- **A10** Check the implemented token-based dark mode for contrast; keep it only
  if it remains a small, usable change, otherwise defer it.
- Review bounded forms, headers, account/key setup, offers and contacts; place
  independent controls side by side whenever the viewport has room. Keep mobile
  the primary target. Check dark mode only if it remains a small token-based
  change (A10); otherwise defer it.

### 2. Sale listing and Wanted Request surfaces — B1–B7

- **B1, B7** Keep Original price optional through creation/editing and visible
  on browse and detail surfaces. Its concise buyer-facing label is **Seller
  Provided**; do not imply proof or independent verification.
- **B2–B4** Provide eligible Save/Unsave and Contact actions on browse cards;
  provide owner Edit and availability actions on sale and Wanted details, with
  authoritative ownership checks and consistent state refresh. There is no
  remove/delete/archive feature; use Mark unavailable/Reopen.
- **B5–B6** Show possible campus matches as shared sale cards above the Wanted
  description by default. Add a labelled hide/show control that retains the
  match heading/count when collapsed and preserves the draft through errors.

### 3. Identity, encryption and contact sharing — C1–C5

- **C1, C5** Preserve first-device encrypted messaging setup, account-isolated
  keys, optional contact setup, selective encrypted sharing, and a direct setup
  route back to the conversation when contact details are missing.
- **C2** Preserve private selected-buyer tracking separately from availability;
  only Mark as done deal changes listing availability.
- **C3 — implemented high-reasoning task:** reuse `display_name` as a required,
  editable Handle; enforce the approved validation and case-insensitive unique
  database/API constraint; stage legacy accounts safely without changing IDs;
  expose it through a reviewed Identity participant projection. Verify
  concurrency and migration/rollback/reapply on disposable PostgreSQL.
- **C4** Add a Temporary account marker using the authoritative Identity
  participant classification/projection. Show only the badge, never peer email;
  do not query private Identity tables from Conversations.

### 4. Conversations — D1–D8

- **D1, D8** Make each listing/request origin a distinct compact bounded box with
  recognizable title, useful sale image and price/budget, origin-detail action,
  counterpart Handle when C3 is available, and clear contained thread rows.
  Remove excessive whitespace; Wanted boxes should be distinct without a fake
  photo. Keep IDs internal. Place selected buyer and current offer/thread action
  in the seller's relevant box.
- **D2 — implemented high-reasoning task:** add **All / Buying / Selling** modes with
  the approved sale and Wanted role meanings, plus **Item / Person** grouping.
  Derive roles from trusted origin and membership context; keep authorization
  server-side. The mode and grouping controls should be compact buttons.
- **D3** Remove the currently empty Sort & Filter disclosure and the old visible
  origin/partner multi-selects. Preserve most-recent-activity ordering. Add a
  collapsed sort/filter area only if it contains real, useful, working controls.
- **D4 — implemented with D2:** paginate origin/person boxes as units, bound the
  conversation rows inside a large box, and keep message-history pagination
  separate. Define stable ordering, counts and reset behavior in reviewed
  contracts; do not fetch every conversation/history entry to fake grouping.
- **D5** Keep Enter-to-send and Shift+Enter newline behavior with IME, readiness,
  retry and pending-send safeguards.
- **D6 — implemented high-reasoning task:** show an authorized global unread count in
  navigation and open a thread at its first unread message with a stable **X
  unread messages** divider, bounded history loading and display-based read
  acknowledgement. Do not add an Unread filter or force-scroll someone reading
  older history.
- **D7** Keep offer submit/revise/withdraw/resubmit and seller selection usable;
  selection is private tracking, sends no buyer notification and does not change
  availability. Only Mark as done deal does that.

### 5. Search behavior and optional work — E1–E2, F

- **E1** Preserve verified qualification/cutoff behavior when sorting sale
  results; Wanted search remains its own strict all-terms behavior. Search quality
  can be revisited later if this remains a relevance-tuning issue.
- **E2 / OPT-05** Defer search relevance/common-word refinement. Keep the measured
  cutoff and sorting evidence recorded above; a reproduced correctness failure
  is still a required fix, not optional tuning.
- **OPT-04** Chat image sharing is not implemented. Keep it as future work with
  actual end-to-end encryption, storage, UI, limits, retention and failure-state
  requirements; it is not part of the current correction scope.
- **G1** Cloud deployment/readiness remains deferred. No cloud changes, migration
  applies or paid experiments are authorized by this plan update.

### 6. Final local visual inspection handoff

After the authorized implementation and verification work, create or refresh
sample data that exercises all relevant surfaces and provide a step-by-step
visual checklist covering responsive discovery and cards, filters/search state,
sale and Wanted creation/detail/ownership actions, Original price, possible
matches, key/contact setup, both conversation roles, offers, buyer tracking,
availability, unread presentation and navigation. Stop for Suraj's inspection;
do not treat programmatic checks as visual approval. The three higher-reasoning groups above are now implemented and locally verified; their visual behavior is included in this same human inspection.

## Execution contract — Conversations first, remaining batch afterward

Preserve existing changes and the current branch; keep the work log current.
Use reviewed public feature/domain boundaries and forward migrations where needed;
never apply to a retained/shared/cloud database. Update generated contracts from
canonical sources. Preserve real email verification/provider code unless a
reproduced bug requires a justified, tested change. Test with real local SQL,
real crypto and the pinned Hybrid model; synthetic external ports stay isolated.
Reproduce the encryption failure programmatically with actual clients where
possible, not only mocks. Verify seller reopen state and selected-buyer effects.

Run relevant focused checks after fixes, then the agreed full verification and
migration checks on the final code. Rebuild the actual app and regenerate data
that exercises every group, including messaging/contact/offer flows, stale and
retry states, mobile layouts and corrected fixture categories. Supply the live
URL, exact account/profile steps, sample downloads, expected results and cleanup.
Human visual inspection remains required; do not mark it passed automatically.

Suraj settled the handle decision and accepted the correction scope. Conversations
functional repair was authorized and performed, with human verification pending.
Suraj released the full remaining list through the local visual-inspection handoff. Routine implementation,
reversible fixes and local tool setup are within that released batch.
Consult this plan before every step and after every context reset. Investigate
unexpected failures and continue independent work rather than waiting on routine
choices. If a genuinely new
product/security/contract decision cannot be resolved from the approved choices,
record the precise blocker, preserve a safe state and continue unaffected work;
do not invent approval or weaken crypto/privacy. Unexpected issues cannot be
ruled out in advance. Independent peer review/exact merge and cloud/provider
approvals retain their separate gates. The eventual NEXT-04 target remains the
whole functional app at https://clip-iisc.site except Notifications for this scope.

## Coverage audit against Suraj's feedback

The audit checked the original visual-feedback message, the added My Listings
card observation, the search/optional-work follow-up and all later decisions.
No reported item is intentionally dropped. This is scope coverage, not evidence
that any defect has been fixed. The audit corrected stale references to optional
display names, an undecided removal feature, pending Saved navigation and pending
buyer-selection approval; it also made offline-peer messaging, group-level
selected-buyer tracking and chat-image deferral explicit.

| Original feedback/clarification | Accounted for |
|---|---|
| Checkbox labels below boxes in every multi-select | A: shared row layout, all consumers/mobile/accessibility |
| Bicycle text results differ from category results; broad Inspection/campus results; cutoff and Newest concerns; Wanted search concern | E: verified exclusion and all-terms rules; same candidates under sorts; semantic literal-word caveat; correctness defects required, tuning deferred OPT-05 |
| Owner Edit/availability on detail; possible browse owner actions; later no removal clarification | B and D3: owner actions on sale/Wanted surfaces, compact menus, unavailable/reopen only |
| Original price absent on detail | B: diagnose and verify all shared surfaces and optional/present/cleared persistence |
| Possible campus matches too low/below Publish, should look like browse | B: visible while composing, pre-submission shared card, nonblocking safe failure |
| Budget not stated above title; Wanted blue card and inconsistent detail styles | A/B: shared visual hierarchy, amount position and consistent cards/details |
| Contact seller/requester and Save directly from browse | B: eligibility-aware contact/save/unsave actions, complete details and independent clicks |
| IDs should become titles, item thumbnail/price and person identity | C/D/D1: origin context, unique editable required handles, internal-only IDs; privacy-safe projections |
| Seller encryption error and buyer waiting-for-key; cannot test messaging/contacts/offers | C/D: fix actual crypto path, test both clients, shared failure/retry, contacts and offers |
| Key setup should happen at account setup, first sign-in only; optional contacts | C/D5: first setup, incomplete legacy transition, explicit exceptional device recovery, no routine repeats |
| Temporary-account marker | C: participant account-class badge |
| Missing contacts need direct settings action instead of relying on header | C: Set up contact details with safe return and full consent/delivery verification |
| Original Sale/Wanted modes, later revised to Buying/Selling; item/person boxes and controls | D/D4: marketplace-intent mode buttons replace primary Sale/Wanted/participation selectors; recognizable Item/Person boxes; remove visible origin/partner multi-selects; collapsed useful controls; correct bounded group/row/message pagination |
| Navigate to listing/request from thread and its group | D: origin navigation from both |
| Initially working selection seemed stale/unavailable after reopening | C: precise reproduction and refresh/revision/polling regression, distinct from D2 semantics |
| Buyer selection private, meaningful seller tracking/current offer; should not hide listing; done deal controls availability | D/D2: accepted decoupling, selected group summary/thread shortcut, no buyer notification/disclosure |
| Remove sample header links; callback/link usefulness; Sign out placement | A/D6: clean navigation, retained Saved, hidden technical callback, top-right account controls |
| Cannot test creation of offers | D: actual buyer submit/revise/withdraw/resubmit and seller visibility after crypto fix |
| Are chat images implemented? Add as optional | F and OPT-04: absent now, comprehensive future task, not selected for overnight |
| Cards too horizontal/vertical, long descriptions, full-card clicks and visible condition | A: compact responsive shared cards, clamping, independent actions and keyboard navigation |
| My Listings looks different from Discover | A: one core sale card across both plus Saved/preview/matches; owner extras only |
| New Wanted action exists in its tab, equivalent New Listing missing | A: symmetric discovery creation actions |
| Huge horizontal buttons, hyperlinks, headers, dark mode only if easy | A/F: bounded styling, button appearance with correct semantics, conditional dark-mode/defer |
| Wanted form too wide compared with sale form; mobile primary everywhere | A: bounded forms and desktop/tablet/mobile portrait/landscape review |
| Existing real email verification should keep working | Execution contract: preserve real provider behaviour; synthetic inspection delivery is isolated |
| Persist feedback, group work, settle decisions, unattended batch through rebuilt inspection | This document, settled decision table, mandatory per-step consultation, execution contract and work-log checkpoint |

### Follow-up screenshot and control audit coverage

| Follow-up feedback | Accounted for |
|---|---|
| Encryption setup flush left and action appended to text | A/D8: bounded page margins, clear consent/action layout |
| Offer buttons/input have no gaps | A/D8: sized controls, spacing and mobile wrapping |
| Contact checkboxes/actions crammed together | A/D8: readable rows, spacing and separate actions |
| Enter should send rather than require mouse | D/D8: Enter/Shift+Enter, IME/repeat/readiness and retry safeguards |
| Somewhere show unread chats/messages | D/D8: authorized global navigation indicator plus existing thread counts; not a new filter |
| Open at first unread with X unread divider | D/D8: stable read-boundary anchor, bounded history window and display-based acknowledgement |
| Chat page needs a small improvement now, full polish later | A/D8: bounded current usability pass; broader refresh NEXT-09 |
| Buyer/seller intent is clearer than origin ownership/initiator | D/D4: exact sale/Wanted role combinations and mode buttons |
| Origin/partner multi-selects are unnecessary; phone controls crowd chats | D/D4: remove visible pickers, compact modes, collapsed Sort & Filter |
| Title/handle search and Unread filter were mistakenly described as existing | D: explicitly absent; neither added by default |
| Is recent activity ordering implemented? | D: verified current last_activity_at DESC with stable tie-break; preserve default |
| Is pagination for boxes, rows or messages? | D/D4: all three explicitly distinguished; replace current flat inbox paging |
| Groups must immediately identify the item/person | D: title, sale photo/price, handle and unread/selected context; no raw UUID labels |
| Audit local-to-cloud compatibility, especially encryption | G: repository findings, implemented components and exact unverified deployment gates |
| SES production access was granted today; defer cloud now | G/D9: user-reported access recorded, separate app guard promotion deferred, no cloud actions |

### 2026-10-29 screenshot-feedback audit

| New feedback | Accounted for |
|---|---|
| Multi-select dropdown options align checkbox and text; click outside should close | A1/A13: one-row options, outside pointer/touch and Escape dismissal, retained choices |
| Search should be collapsible after use but visible by default | A14: initially expanded, labelled reopen control and active-state summary |
| Sale cards are too tall/space-heavy; My Listings differs from Discover; use a product-style horizontal card, but not one card per desktop row | A2/A12: shared responsive card, larger useful left image on phones, multi-column desktop grid, My Listings parity and clamped descriptions |
| Never let page content grow without bound on ultrawide screens; use side-by-side layout when there is room | A11/A15/A17 and the global width rule: shared maximum content width and responsive columns/action rows, while remaining mobile-friendly |
| Wanted creation CTA is oversized/asymmetric | A15: matching compact New Listing/New Wanted actions, side by side when possible |
| Mobile navigation consumes too much space | A16: compact sticky menu available while scrolling |
| Original price label should be “Seller Provided” | B7: concise public-facing label; no change to evidence/proof meaning |
| Listing details facts could be tabular after description | A17: accessible responsive definition-list/grid, columns where useful rather than a rigid table |
| Possible matches should be above description and hideable | B6: above description, open by default, labelled collapse/show and retained count |
| Conversation groups need real boxes, useful image size, less empty space and origin detail navigation | D1/D8: compact bounded origin cards, contextual link, image/price or Wanted title/budget, distinct thread rows |
| Temporary status can use the existing verified-email classification, without exposing email | C4: authoritative safe Identity classification; badge only, no private email/table access |
| Participant Handle should appear when the unique Handle work is ready | C3/D1/D8: Handle and the safe participant projection are implemented and wired into the inbox, thread and selected-buyer context |
| Empty Sort & Filter is confusing; mode buttons are enough until real controls exist | D3/D4: remove empty disclosure; do not retain controls merely because APIs support them |
| General layout should use two columns/side-by-side controls when space allows | A11/A12/A15/A17: bounded responsive grid and row behavior; no unbounded horizontal stretch |
| Previously deferred high-reasoning tasks should remain on the plan | C3, D2, D4 and D6 are included, implemented and locally checked; human visual review is pending |

### Active full-batch checkpoint — 2026-10-29 04:25:25 UTC

Suraj authorized all remaining tasks through the visual inspection handoff, including C3, D2/D4 and D6. The earlier batch exclusions are historical, not current authorization limits. Presentation changes now include outside-click/Escape dropdown dismissal, compact shared horizontal sale cards, bounded page content, mobile menu, collapsible discovery controls, matches above description, simplified Original price labels, distinct inbox group cards and thread spacing. Frontend lint, 488 tests, type checking and production build passed (3 tests skipped); the overall task remains in progress. Handle/participant projection, modes/group pagination, unread behavior, comprehensive final verification and refreshed inspection handoff remain pending.

Presentation verification update: `npm run check` passed with 489 tests passed and 3 skipped after adding outside-dismissal/Escape coverage. A full `make check` run was started with local socket permission after a sandbox-denied formatter attempt; its output is `/tmp/clip-full-visual-check.log` and no final result has yet been recorded. These are intermediate checks, not full-batch completion.

### Full-batch implementation checkpoint — 2026-10-29 05:05:29 UTC

Implemented staged Handle claims and safe participant projection with regenerated contracts, required onboarding/editing, account-change cancellation, participant Handle/Temporary labels and selected-buyer Handle. Implemented All/Buying/Selling and Item/Person inbox controls, SQL group-first pagination with bounded group continuations, authorized aggregate unread navigation, stable first-unread divider/positioning and bounded history windows with earlier/newer controls. Added real PostgreSQL role/group/unread tests, concurrent case-insensitive Handle claims, schema/boundary regressions and frontend onboarding/divider tests. Latest frontend run passed 493 tests (3 skipped); the expanded focused Identity/contract run passed 183 tests with one obsolete operation-count assertion subsequently fixed. PostgreSQL full migration/rollback/reapply passed. Final full check and refreshed live action sweep are running; no final handoff is yet claimed.

### Local visual-inspection handoff — 2026-10-29 05:35:44 UTC

All authorized A–E corrections, including previously queued C3/C4, D2/D4 and D6, are implemented and locally checked. `make check` passed all 12 stages (Python 1,936 passed/155 skipped; data 94 passed; web 493 passed/3 skipped; 168 PostgreSQL Conversations tests). Final frontend check including the new unread isolation regression: 494 passed/3 skipped. Supplemental PostgreSQL checks passed for legacy Handle staging/collisions/rollback/reapply and least-privilege public projection; added unread-backlog regression brings the focused Conversations suite to 169 passed. Chromium checked responsive widths, 20-to-24 group continuation, required/taken Handle setup, actual encrypted Enter-send/read, unread count/divider and selected encrypted contacts. The previous browser-test database was removed. Clean human inspection data is serving at http://127.0.0.1:5176/__inspection (PID 2833284): 23 action groups passed; 28 sale fixtures, 26 Wanted Requests, 77 threads, six main actors and downloadable photos. Human visual approval, owner/peer review and cloud release are not inferred.
