# NEXT-03 — visual feedback and agreed correction scope

**Source:** Suraj's desktop inspection feedback, including four screenshots and
his follow-up about My Listings card consistency, search, identity, optional work
and an unattended overnight correction batch, 2026-10-28 UTC.
**State:** Suraj authorized Conversations functional repair first, a live demo for
his inspection, then a commit after verification. The handle/database change and
remaining visual batch follow afterward when released. Later screenshots added
chat presentation, keyboard/unread behaviour and simpler buying/selling controls.
This increment updates documentation only; do not resume application or cloud
changes. Functional-demo human verification and the commit checkpoint remain pending.

**Current checkpoint scope:** repair actual encryption/account-store and message
history failures, first-device setup, contact sharing/navigation, offers, private
buyer selection, selected-offer context and reopened availability freshness.
Handle-dependent participant naming and the broader inbox grouping/presentation
redesign remain in the subsequent batch. Preserve and consult all groups below
before every step; do not claim those remaining UI items are complete.

## Mandatory execution discipline

Before **every implementation step**, reopen this plan and its decision table,
identify the applicable group and acceptance items, and check the latest work-log
checkpoint. Do this again after a context reset or handoff; do not rely on memory.
Before reporting a step complete, reread its items, verify the observed behaviour
and update the checkpoint/coverage evidence. Every new correction must trace to
this plan or explicit subsequent user direction. Preserve the grouped scope;
there are no intermediate human confirmation stops during the authorized batch.
The final stop is a rebuilt, checked, seeded environment ready for human visual
inspection. The current stop for this increment is the Conversations demo for human
verification, before committing or starting the remaining batch.

## A. Shared presentation and mobile layout

- Fix every multi-select: checkbox and left-aligned text on one row, consistent
  spacing, accessible labels, touch targets, scrolling and narrow-screen sizing.
  Restyle remaining consumers; do not retain obsolete inbox multi-selects just
  to restyle them (D supersedes their earlier inclusion).
- Share the core sale card across Discover, Saved, My Listings, draft preview and
  possible matches. Owner views may add status/actions without a separate design.
- Align Wanted cards/details with sale styling; remove garish blue treatment;
  place budget or Budget not stated in the amount position. Compact cards in both
  dimensions; clamp long descriptions and retain condition, price and status.
- Make the main area of cards/groups navigate, with independently usable action
  buttons and keyboard access; avoid nested interactive elements or accidental
  navigation on Save/Contact. Navigation can be styled as a button while retaining
  link semantics, open-in-new-tab and browser history.
- Bound Wanted form widths like sale forms. Review all over-wide forms, large
  full-width buttons, excessive spacing and headers. Mobile is the primary target;
  verify portrait/landscape, tablet and desktop without reducing usable tap sizes.
- Move Sign out/account controls to the top right. Remove sample ID/detail links.
  Agreed navigation: Discover, New Listing, New Wanted Request, My Listings,
  Saved, Conversations, Contact Settings; Sign in only when signed out. Auth
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
- Give the chat page a modest usability pass now: clear message/composer/offer/
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
  composition, using the shared browse card. Preserve unsaved input and valid
  submission after match errors. Align Wanted/detail/creation styling and budget.

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
  Show any retained advanced controls behind **Sort & Filter**, collapsed by
  default; on phones avoid a control panel pushing the chats below the fold.
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
  themselves. Bound rows within a large box with Show more/load-more. Message
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
- Open a thread at its **first unread message**, with an **X unread messages**
  divider. If fully read, open at the latest messages. Capture a stable opening
  read boundary so acknowledgements do not move the divider or jump the viewport.
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
| D4 | Inbox modes, grouping and controls? | Revised by later feedback: All/Buying/Selling buttons (Buying=sale initiator or Wanted author; Selling=sale owner or Wanted responder), compact Item/Person grouping, default recent activity, recognizable origin/handle context. Remove visible origin/partner multi-selects and redundant participation/type selectors. Retained useful controls behind collapsed Sort & Filter; no new title/handle search or Unread filter. Page boxes and bound expanded rows; message-history paging stays separate. |
| D5 | When must encryption setup finish? | Settled: first-sign-in setup, not repeated at every login. Require ready keys before publishing a sale or starting/responding in chat; contacts optional. Existing incomplete accounts get a setup prompt; missing device keys require explicit recovery/setup, never silent replacement. |
| D6 | Keep access to Saved? | Keep Saved in navigation (compact icon/button allowed); remove sample links and hide Auth callback from navigation while retaining its route. |
| D7 | Execution scope and operating rules? | Settled scope: execute A–D, E correctness checks and F/G deferrals in one batch; fix failures, run agreed checks, refresh all inspection data/instructions and stop ready for human inspection. Consult this plan before every step and again before reporting completion. No intermediate confirmations. Dark mode only if small; OPT-04/05 planning only. No cloud, paid work, merge or deployment. Current instruction: documentation updates only. Priority when resumed: Conversations functional checkpoint first, live human demo and verification, then commit; remaining batch awaits release. |
| D8 | Chat interaction and unread presentation? | Enter sends, Shift+Enter newline with IME/pending-send safeguards. Add navigation unread indicator, first-unread opening anchor and stable X unread messages divider; display-based read acknowledgement, latest position when fully read, no forced jump during older reading. Add modest chat/onboarding/offer/contact spacing now; broader final polish remains NEXT-09. |
| D9 | Cloud/SES work now? | Deferred at Suraj’s instruction. SES production access is user-reported as newly granted; application restrictions still need later reviewed promotion. Preserve G’s audit findings and real email behaviour, but perform no cloud/configuration/deployment changes in this batch. |

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
The latest instruction authorizes this documentation update only; resume code
work only when Suraj releases the next increment. Routine implementation,
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
