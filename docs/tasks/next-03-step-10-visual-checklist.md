# NEXT-03 — ready-for-inspection walkthrough

This walkthrough uses the normal built application, real cookie/CSRF sessions,
real PostgreSQL domain stores, the pinned Hybrid model/worker, and real browser
conversation encryption. The launcher substitutes only external Microsoft signing,
email transport, and S3 with explicit synthetic providers. Notifications are excluded.
The synthetic account switch and fixture endpoints exist only in this launcher;
they are absent from the normal application and deployment image.


## Current checkpoint: Conversations functional repair

Suraj requested this checkpoint before the handle migration and broader visual
redesign. The fresh demo remains **http://127.0.0.1:5174/__inspection**. Use this
sequence first; existing card/layout/handle feedback is still pending.

1. In one browser/profile choose **seller**. Complete the first-time messaging
   setup: read the warning, tick acknowledgement, click Create encryption key.
   Go back to the inspection controls and open the first prepared conversation
   (the bicycle). Ordinary subsequent visits must not ask to create keys again.
2. In a **different browser/profile** choose **buyer**, complete setup and open
   that same first conversation. Two ordinary tabs share a session cookie and
   cannot be two simultaneous actors. A private window is temporary: closing it
   destroys its local keys. Use persistent profiles/browsers for retained history.
3. Send a synthetic message each way. Reload both pages and check both sent and
   received history remains. Once setup is complete, one participant can stay on
   Discover or close the thread while the other sends; opening the thread later
   must show the message. Never clear site storage to work around an error.
4. As seller choose contact details, select Email, Review, Confirm and send.
   Buyer should receive only the synthetic selected email. For an account with
   no contacts, Set up contact details leads to settings and Back to conversation
   returns safely. Check cancel once before confirming. As buyer update/withdraw/
   resubmit an offer; seller can Refresh offer to see it.
5. As seller Select this buyer. **Availability must stay unchanged**; this is
   private tracking, with no buyer notification. Clear/change it if desired.
   In the inbox the seller group shows Selected buyer, current/no/withdrawn offer
   and an Open selected conversation shortcut. Origin links exist on groups/threads.
6. Use Mark as done deal on that seller group: only this action makes unavailable.
   Reopen the same item in My Listings, then return to the existing inbox/thread.
   Focus/visible polling must update seller controls without a manual reload.
   Selection remains usable on valid unavailable records and survives reopening.

The account-specific store preserves matching legacy keys/history and keeps new
accounts in separate namespaces. Missing keys for an already-registered account
are reported; keys are never silently replaced. Fresh fixture accounts have no
pre-generated private keys, so complete setup in your chosen profiles.

The verified browser regression used actual Chromium/IndexedDB, real SDK crypto,
real local SQL/session APIs and synthetic external providers. It passed both-way
and offline-recipient messaging, encrypted selected-field contact delivery,
offer changes, private selection, live reopen, account switching and reload.
Final conversation-repair `make check` passed: Python1,934/154 skipped; data94;
web475/three skipped; Conversations167; contracts/types/lint/build/database safety,
full disposable migration/rollback/reapply and secret gates passed. Separate
store checks:22 passed/three gated skips. No shared/cloud DB apply occurred.

This is not human visual verification. Handle collection/uniqueness/migration,
new group pagination/People mode, participant naming and the general UI refresh
remain in the following batch. Chat images remain optional OPT-04.

## Open the prepared environment

Open **http://127.0.0.1:5174/__inspection**. The prepared session is running (2026-10-28 UTC), process **2346525**.
The page provides account-switch buttons, useful record links, all synthetic IDs,
and the current sample-photo path. All pages use this one origin. Use this exact
address rather than mixing `localhost` and `127.0.0.1`, which have separate cookies.

The inspection page offers these synthetic accounts:

| Button | Use |
|---|---|
| seller | Owns the bicycle, the kettle, sale history and Wanted Requests; select buyers, mark deals unavailable, and share test contacts. |
| buyer | Has conversations with both sellers and responds to Wanted Requests; can save listings and submit/revise/withdraw offers. |
| other-seller | Provides a second listing/request owner and a second partner for filtering. |
| other-buyer | Has a second conversation about the bicycle; compare and select buyers. |
| temporary | A real temporary-account session created through synthetic OTP delivery; can browse, save, and create Wanted Requests, but cannot publish sale listings or respond to Wanted Requests. |

Clicking a button issues a real local session and opens Discover. The banner on
application pages links back to the inspection controls. Switching accounts resets
private application state. For simultaneous encrypted chat, use **two separate
browser profiles** (for example a regular window and one private window), with
seller in one and buyer in the other. Two ordinary tabs share one account cookie.
Keep each actor in its own profile while testing chat to preserve device keys.

The prepared data contains **28 sale listings** (27 available and one unavailable),
**26 Wanted Requests**, and **54 conversations** across sale and Wanted origins.
It includes all approved categories/conditions, both negotiability badges,
Original price present/absent, zero and absent budgets, multiple partners, an
existing offer, real photos, and enough results for page 2. No opaque fake message
keys are seeded: first opening a conversation initializes the real browser crypto.

## Inspect Discovery and listings

Use **buyer** initially. Tick each item only after observing its result.

1. [ ] Open `/`. Verify Sale Listings and Wanted Requests views, New listing,
   New Wanted Request, Saved, My Listings and Conversations navigation. Open
   New Wanted Request and confirm it opens the existing creation form directly.
2. [ ] In Sale Listings, search **Inspection campus bicycle**. The bicycle should
   appear. Then search **wheeled vehicle**; it should appear through Hybrid search.
   Try **zzzxqnevermatchzzzxq** and verify an empty result state.
3. [ ] Verify **Best Match** is the title-cased default for nonblank searches.
   Choose Newest, then a price sort. Apply another filter to the same query:
   the chosen sort stays. Change the search text: Best Match returns. Empty
   browsing defaults to newest order. No search-mode picker is required.
4. [ ] Clear the search. Select **Books** and **Bicycles** together in categories.
   Both categories can appear. Clear that dropdown and verify the restriction
   goes away. Repeat with two independent conditions; there is no condition rank.
   Combine categories and conditions: OR inside either dropdown, AND between them.
5. [ ] Try minimum and maximum asking price, including equal endpoints. Whole
   rupees are required. Try a reversed range and an amount over ₹1,00,00,000;
   verify readable errors. Clear the bounds and verify full results return.
6. [ ] With filters cleared, move to page 2, then apply a filter: page 1 returns.
   Check numbered navigation and change page size where offered. Use browser
   Back/Forward after applying different searches/filters and check restored state.
7. [ ] Check ascending/descending price order and Newest. Inspect cards with
   **Negotiable** and **Fixed price** badges; there must be no negotiability filter.
   The bicycle has seller-provided Original price; the kettle omits it. No empty
   Original price row or inferred discount should appear on the omitted case.
8. [ ] Open the bicycle and kettle from the inspection page links. Check their
   detail values and photo against their cards. Save the bicycle, open Saved,
   verify the shared card, remove it, and confirm it disappears. Save it again
   if you want to inspect unavailable saved state later.
9. [ ] Switch to **seller**. Open My Listings. Verify the unavailable history
   record is retained although it is absent from public discovery. Verify
   Original price present/omitted cases and the edit links. Switch the My Listings
   view between Sale Listings and Wanted Requests: this remains single choice.

## Inspect creation, photos, preview and editing

Use **seller**. Download the sample files from **Download sample files** on
`/__inspection` into your usual Downloads folder. The current sample-photo directory also appears on `/__inspection`
under “All synthetic record IDs and sample-photo path”. It contains:
`inspection-photo.png`, `photo-1.png` through `photo-9.png`, `progress-photo.png`,
and `invalid-photo.txt`. The server copies are temporary and synthetic; your downloaded copies remain
until you delete them. Use those downloads in the browser file chooser.

10. [ ] Open New listing. Check required/whitespace errors, the title/description/
    pickup-area counters, Unicode text, asking price and optional Original price.
    Category and condition each assign **one** value. Check the updated catalogue
    labels, including Like New, and the Sports & Fitness category.
11. [ ] Add a prepared PNG. Inspect its local preview and plain photo status/count.
    Add more files, reorder them if that control is offered, and remove one.
    Try selecting nine photos: no more than eight may be attached. The invalid
    text file should be rejected even if you override the file-picker filter.
12. [ ] Use `progress-photo.png` with browser network throttling to see upload and
    confirmation states. For a deliberate retryable failure, use DevTools request
    blocking for `*://127.0.0.1:5174/__listings_demo/storage/*`, select a new photo,
    and observe failure. Remove the block and click Retry. The same intent should
    recover. Remove an unneeded photo and confirm the remaining count is correct.
13. [ ] Open the draft preview. Change title, condition, price, negotiability,
    Original price and the first photo. Verify the preview updates and has the
    same sale-card presentation as Discover/Saved. Use the small bicycle diagram
    and the large noise image as visibly different first photos. Previewing must not publish.
    A listing cannot be published with no confirmed photo.
14. [ ] Publish a new listing with Original price, inspect its detail, and edit it.
    Change Original price, save and check My Listings, detail and Discover. Then
    clear Original price, save again, and verify the row disappears everywhere.
    Refresh after a save to confirm the persisted value. Check an already prepared
    omitted-price listing as well. Asking price remains a separate required field.
15. [ ] Change the created listing's availability. It should leave public browse
    when unavailable, remain in My Listings, and return when reopened. Inspect
    any future availability window controls and their validation if you use them.

## Inspect Wanted Requests

16. [ ] As seller, use New Wanted Request. Enter **Inspection campus bicycle** as
    the draft title: the available bicycle should appear among possible matches.
    Enter **zzzxqnevermatchzzzxq**: no matches should appear. Editing the draft
    must not save a request. Block `*/api/wanted-requests/draft-matches*` in DevTools,
    change the title, and verify an error preserves the draft and does not block
    otherwise valid submission. Remove the block afterward.
17. [ ] Check Wanted required text, counters, whitespace, Unicode, category single
    assignment and optional budget. Create a request, edit it in My Listings →
    Wanted Requests, then mark it unavailable. It leaves public results but remains
    in your history. Reopen it and confirm it returns.
18. [ ] In Discover → Wanted Requests, search **physics textbook**: both words must
    occur across title and description. Try a no-match phrase. Select two categories
    together, then combine with text and inclusive minimum/maximum budgets. Equal
    budget endpoints must work. A budget bound excludes requests without a budget.
    Clear filters and verify unbudgeted requests return. No condition or
    negotiability controls should appear here.
19. [ ] Clear Wanted filters, move to page 2, then apply a filter and check reset to
    page 1. Test Back/Forward, and switch Sale/Wanted views: each view keeps its own
    applied URL filter state. Verify page-size controls where present.
20. [ ] Open a public request as buyer. It must not reveal private author contacts.
    Contact requester opens/reopens a private conversation. As the temporary
    account, browsing is allowed but responding is denied; check the explanation.

## Inspect Conversations, offers, buyer selection and contacts

These are the normal `/my/conversations` pages. Do **not** add
`?demo=conversations`; that old presentation fixture is not used by this walkthrough.
The inspection page provides direct links to the first conversations. The first
is buyer ↔ seller about the bicycle, the second is about the kettle, and a separate
other-buyer conversation also concerns the bicycle. IDs are shown because current
inbox labels use shortened IDs; the inspection page maps full actor/record IDs.

21. [ ] As buyer, open Conversations. Check buyer/responder context. As seller,
    check seller/request-author context. Participation is single choice; Type is
    single choice. Sale and Wanted origins should group appropriately.
22. [ ] Select multiple Listing or request values and multiple Conversation partner
    values. Apply them together: OR within either selection and AND between them.
    Clear them. Check offer status, minimum/maximum offer and amount sorting for
    sale conversations; switching to Wanted disables/clears inappropriate offer
    controls. Page through the prepared inbox and check a changed filter resets
    to page 1. Refresh must preserve the applied filters.
23. [ ] Open the bicycle conversation as seller and buyer in separate profiles.
    Follow the explicit first-device key-registration acknowledgement. If it says
    the other participant has no key yet, open that conversation in the other
    profile, finish registration there, then refresh the first. Check loading,
    retry and key-state messages rather than assuming the composer is ready.
24. [ ] Send a synthetic message in each direction. Verify ordering, refresh and
    persistence. Keep the recipient inbox open while a new message arrives to
    inspect unread counts, then open/display the thread and confirm read state.
    Reload the same profiles and check history. Do not clear browser storage
    during this check; loss of local keys intentionally has a separate warning.
25. [ ] As buyer, inspect the bicycle's prepared offer. Change its whole-rupee
    amount and submit, refresh the seller's offer panel, and confirm the amount.
    Withdraw it, inspect Withdrawn on the seller side, then resubmit. Seller can
    read offers but cannot submit a buyer offer. Wanted conversations have no
    offer panel. Offers do not confirm payment, handover or an accepted deal.
26. [ ] As seller, open the bicycle conversation and **Select this buyer**. Confirm
    the buyer is selected privately and availability stays unchanged. Selection
    alone must not remove it from discovery; existing conversations stay readable.
    You can change/clear selection before or after making it unavailable. This is
    independent of accepting an offer or confirming payment.
27. [ ] In the seller inbox, use the kettle group's **Mark as done deal** action.
    Confirm it marks that listing unavailable without inventing a selected buyer.
    Existing conversations remain open. Buyer and Wanted groups must not show
    that seller action. Reopen through My Listings if repeating this check.
28. [ ] Open Account contacts as seller. A synthetic example email is prepared;
    add a synthetic phone such as `+919876543210` if desired. Save/delete fields
    and inspect validation. In a ready conversation, open contact-sharing options,
    choose only the email, review/confirm, and verify the buyer receives only that
    selected field. Cancel once before confirming: cancellation must not publish.
    Messages and contact shares use the real browser encryption/session path.
29. [ ] Log out. Private conversations, contacts and owner records must disappear
    or require sign-in. Old pages must not authorize new writes. Switch to
    temporary from the inspection controls: check browsing/saving/Wanted creation
    and the sale-publication/response restrictions. The actual temporary
    registration, password login and logout routes were also exercised by the
    programmatic sweep with a captured synthetic mailbox.

## Narrow layouts and reporting observations

Repeat the important discovery/filter, create/edit/photo, Wanted, inbox and thread
steps at **1280×800**, **768×1024**, **390×844**, **360×800**, and **844×390** CSS pixels.
In Firefox use Ctrl+Shift+M (Cmd+Option+M on macOS). Look for clipped labels,
overlap, horizontal page scrolling, unreachable controls, unreadable errors and
awkward open dropdowns. Record the browser and viewport actually checked.
Responsive emulation does not establish actual phone keyboard/camera behavior;
that needs the later approved reachable cloud environment.

Report a checklist number, account, action, expected result and observed result.
You can request changes at this point. NEXT-03 remains open pending this review.

## Restart and cleanup

For this session, **`kill -INT 2346525`**
from another terminal stops the server, removes only its own disposable PostgreSQL
container, and deletes its temporary photos/records. Browser IndexedDB/local keys
remain until you clear site data for `http://127.0.0.1:5174`; clear those only after
finishing the inspection. No retained developer database is reset.

To recreate the entire dataset and run the sweep before serving it again:

```bash
cd /home/suraj/src/clip-planning-main
CLIP_ENVIRONMENT=test .venv/bin/python scripts/marketplace_inspection.py --synthetic-inspection
```

Ctrl+C stops a foreground restart. To run the sweep and clean up immediately,
add `--check-only`. IDs and temporary photo paths change on each launch; use the
new inspection page. The already built web bundle is used. If source changes,
rebuild with the pinned Node/npm tools before restarting. The command requires
local Docker and the pinned local semantic model/interpreter.

## Earlier full-walkthrough verification (before the Conversations repair)

- `make check` passed: Python 1,932 passed / 154 skipped; data 94 passed; web
  468 passed / 3 skipped across 38 passing and two skipped files; contracts
  (eight artifacts), boundary/type checks, lint/build, 35 database safety cases,
  disposable migration clean/head/repeat/seven smokes/Identity rollback/full
  reapply, Conversations PostgreSQL 167 passed, and Gitleaks 8.30.1.
- The new launcher safety/photo tests were added after aggregate collection and
  run separately: `pytest apps/api/tests/test_marketplace_inspection.py -q -W error`
  — two passed. Final Black: 299 files unchanged.
- `python scripts/check_database.py --listings-store` passed: 22 passed / three
  skipped, plus the complete disposable migration/rollback/reapply workflow.
  The three skips are explicit native/model/calibration probes; the inspection
  sweep independently runs real Hybrid inference, worker-generated vectors and
  exact/semantic HTTP queries. Calibration/NFR measurement is later work.
- The normal web aggregate skips its opt-in HTTP scenarios when their fixtures
  are absent; the signed Python/browser transport integration and this actual
  authenticated HTTP sweep provide separate integration evidence. Skips are
  retained as skips, not counted as passes.
- The launcher passed 21 actual-app action check groups, including current real
  vector generations for all 28 listings. A live HTTP smoke passed account
  switching, real paginated inbox, normal SPA routes, compiled seller/offer
  controls, sample downloads and rejection of nonfixture file requests.
- Final source secret scan and `git diff --check` passed. Vite retains its
  informational large-bundle warning. No shared/cloud database apply, real
  provider call, paid experiment, deployment, or notification action occurred.

These are automated/programmatic results. Human visual observations are pending.
