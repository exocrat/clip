# NEXT-03 — ready-for-inspection walkthrough

This walkthrough uses the normal built application, real cookie/CSRF sessions,
real PostgreSQL domain stores, the pinned Hybrid model/worker, and real browser
conversation encryption. The launcher substitutes only external Microsoft signing,
email transport, and S3 with explicit synthetic providers. Notifications are excluded.
The synthetic account switch and fixture endpoints exist only in this launcher;
they are absent from the normal application and deployment image.


## Current checkpoint: post-inspection corrections implemented, awaiting a second human inspection

The corrected build includes compact shared sale cards with Save/Message/View in
one centered row below the photo and listing details, visibly tabular listing facts, separate
View/Group by conversation controls, collapsed item/person groups with a visible
group unread badge, stronger conversation separators, five-row per-group
expansion, horizontal phone pagination, date separators, revised unread
positioning and scroll-to-bottom after a successful send.
Account setup gates marketplace use when this browser lacks an encryption key
and offers an explicit new-key action with a data-loss warning. `inspection_buyer`
owns a photo-backed listing and Wanted Request for My Listings review.

Use the fresh environment at **http://127.0.0.1:5176/__inspection**. Browser
verification uses a separate disposable run; the final handoff starts with clean
server key state so your own browser can perform first-device encryption setup.
No chat images or Notifications are included. Cloud deployment remains separate.

## Open the prepared environment

Open **http://127.0.0.1:5176/__inspection**. The launcher PID and photo directory are printed in the latest handoff. Use the download links on the page. IDs and paths change on restart.
The page provides account-switch buttons, useful record links, all synthetic IDs,
and the current sample-photo path. All pages use this one origin. Use this exact
address rather than mixing `localhost` and `127.0.0.1`, which have separate cookies.

The inspection page offers these synthetic accounts:

| Button | Use |
|---|---|
| seller | Owns the bicycle, the kettle, sale history and Wanted Requests; select buyers, mark deals unavailable, and share test contacts. |
| buyer | Has conversations with both sellers and responds to Wanted Requests; can save listings and submit/revise/withdraw offers. Also owns a photo-backed desk-lamp listing and a Wanted Request for checking both My Listings tabs. |
| other-seller | Provides a second listing/request owner and a second partner for filtering. |
| other-buyer | Has a second conversation about the bicycle; compare and select buyers. |
| new-member | Deliberately incomplete regular account: verify required unique Handle collection, then first-device encryption setup. |
| temporary | A real temporary-account session created through synthetic OTP delivery; can browse, save, and create Wanted Requests, but cannot publish sale listings or respond to Wanted Requests. |

Each main actor must have encryption ready in that browser before normal
marketplace pages appear. New actors first ask for consent and **Create
encryption key**. If an actor has a server key but this browser has lost its local
key, Account setup explains that CLIP cannot restore old messages and offers an
explicitly acknowledged **Create a new encryption key** action. Complete
**new-member** to check required Handle setup after key setup; returning accounts
with a present key go straight to the marketplace.

Clicking a button issues a real local session and opens Discover. The banner on
application pages links back to the inspection controls. Switching accounts resets
private application state. For simultaneous encrypted chat, use **two separate
browser profiles** (for example a regular window and one private window), with
seller in one and buyer in the other. Two ordinary tabs share one account cookie.
Keep each actor in its own profile while testing chat to preserve device keys.

The prepared data contains **29 photo-backed sale fixtures** (including the
buyer-owned desk lamp and deliberately unavailable/retired seller cases),
**27 Wanted Requests** (including the buyer-owned request), and **77
conversations** across sale and Wanted origins.
It includes all approved categories/conditions, both negotiability badges,
Original price present/absent, zero and absent budgets, multiple partners, an
    existing offer, real photos, and enough results for page 2. No opaque fake message keys are seeded: account setup creates real browser keys and the first conversation establishes its encrypted session. Create your own test messages using step 24; this keeps unread examples readable with your own keys.

## Inspect Discovery and listings

Use **buyer** initially. Tick each item only after observing its result.

1. [ ] Open `/`. Verify Sale Listings and Wanted Requests views, New listing,
   New Wanted Request, Saved, My Listings and Conversations navigation. Open
   New Wanted Request and confirm it opens the existing creation form directly.
    Check that New Listing is available from sale discovery, and the account and
    sign-out controls sit at the upper right. Sign in should only appear signed out.
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
    The bicycle has seller-provided Original price; the kettle omits it. Open both
    details: the bicycle's Original price appears there too, and the kettle has no
    empty row or inferred discount. Save the bicycle directly from its browse card.
    Contact the seller from that card; the action should not accidentally open the
    card. Open Saved, confirm the same sale-card presentation, and unsave it there.
8. [ ] Click the main area of a listing card and confirm it opens that listing;
    use the card's Save and Message seller controls separately. Repeat on a Wanted
    card with Contact requester. Long card descriptions should clamp while
    condition, price/budget and status stay visible. At 360px and 390px wide,
    confirm Save, Message and View listing are centered in one row below the photo
    and item details instead of adding two stacked action rows to the card.
9. [ ] Switch to **seller**. Open My Listings. Verify the unavailable history
    record is retained although absent from public discovery. Compare its sale
    card with Discover and Saved, including Original price present/omitted cases.
    Open a listing detail as its owner and check Edit and availability controls;
    open another account's detail and confirm owner controls are absent. Switch
    My Listings between Sale Listings and Wanted Requests (one view at a time).
10. [ ] Switch to **buyer**. In My Listings, confirm the desk-lamp card appears
    under Sale Listings and the lab-coat request appears under Wanted Requests.
    Open both and verify owner actions are visible only for this account. Switch
    back to seller before continuing seller-specific checks.

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
    blocking for `*://127.0.0.1:5176/__listings_demo/storage/*`, select a new photo,
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
    Possible campus matches should appear **above Description**, expanded initially, with a labelled hide/show control that retains the match heading/count. They use the same sale
    card as browsing, with image/price/status where available.
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
    Contact requester works from the browse card and detail. Open your own request
    detail as seller and check Edit, Mark unavailable and Reopen; check that they
    do not appear on another person's request. As the temporary account,
    browsing is allowed but responding is denied; check the explanation.

## Inspect Conversations, offers, buyer selection and contacts

These are the normal `/my/conversations` pages. Do **not** add
`?demo=conversations`. The first prepared conversations are buyer ↔ seller about
the bicycle and kettle; another buyer also has a bicycle conversation. The
inspection page maps generated records and provides shortcuts; application
conversation labels should not show opaque IDs.

21. [ ] Open Conversations as buyer, then seller. Recent activity is the default.
    Check sale and Wanted conversations are grouped by their origin, and the
    seller/buyer or request-author/responder context is understandable. Each group
    shows the origin title and budget/price, with a sale photo when available, and
    has a link back to its listing/request detail. Groups begin collapsed. If a
    group has unread activity, its total unread badge stays visible in the header
    while the conversation rows are hidden. No conversation, origin or
    participant UUID should appear as visible copy.
22. [ ] Check the separately labelled **View** (All/Buying/Selling) and
    **Group by** (Item/Person) choices. Pick one option in each group; both
    choices remain active. Buying means your sale enquiries or your Wanted
    Requests. Selling means your sale listings or your responses to other
    people's Wanted Requests. Switching either choice resets paging. By Item
    gives distinct origin boxes; By Person groups threads with the same Handle.
    Each item keeps its own context and detail link. Page 2 contains different
    groups rather than splitting one group across pages. Old origin/partner
    multi-selects and empty Sort & Filter panels are absent.
    Prepared regular peers show their Handles. As buyer, open the prepared
    temporary-requester conversation and check its **Temporary account** marker.
23. [ ] Open the bicycle conversation as seller and buyer in separate persistent
    browser profiles. Complete first-device key setup once for each profile. Two
    ordinary tabs share one session and cannot act as separate accounts. Never
    clear browser storage during the chat checks; local keys are not recoverable.
24. [ ] Send a synthetic message each way. Enter sends; Shift+Enter inserts a
    newline. Check the button still works on touch, spacing around the composer,
    message readability and conversation refresh. After sending, confirm the
    thread scrolls to the new message at the bottom. Keep the seller's bicycle
    group collapsed while the buyer sends several messages; the seller's group
    badge should show the total unread count without expanding it. Expand the
    group and compare with the per-thread unread indicators. Once setup is complete, a
    recipient need not keep the thread open or be online to receive a later
    message. Reload the same profiles and check history.
25. [ ] As buyer, revise the bicycle's prepared offer, submit, withdraw and
    resubmit. Refresh the seller's offer panel and check the current status and
    amount. Seller can read offers but cannot submit a buyer offer. Wanted
    conversations have no offer panel. Offers do not confirm payment or handover.
26. [ ] As seller, expand **Buyer tracking** below the composer and select a bicycle buyer and inspect the seller's listing group:
    it should surface the selected buyer Handle/current offer and a direct conversation
    action. Selection is private tracking and does not change availability or
    notify the buyer. Change/clear the selection if useful. Use Mark as done deal
    on the kettle group; that action alone makes it unavailable. Reopen in My
    Listings and return to Conversations: the seller controls should refresh,
    and selected buyer state should remain useful across the availability change.
27. [ ] Open **Account** as seller. Use the synthetic contact values only.
    In a ready conversation, expand **Share contact details** below the composer, click Choose contact details, select one contact type, Review, then Confirm and
    send. The buyer should receive only that selected field. Cancel once before
    confirming. For an account without contacts, Set up contact details should
    lead to settings and return to the same conversation safely.
28. [ ] Check Sign out at the top-right, then sign out. Private records should
    require sign-in. Switch to the temporary account from the inspection controls:
    confirm the explanatory restriction on sale creation and Wanted responses.
    Temporary registration/login/logout and authorization denials also passed in
    the programmatic sweep.

## Inspect the new feedback corrections

29. [ ] Start as **new-member**. Complete encryption setup first, then verify
    marketplace pages require a Handle.
    Try `inspection_seller`: the safe taken-name error preserves your draft. Try
    spaces/punctuation and fewer than three characters. Save `my_campus_handle`;
    the server confirms it and opens the marketplace. Reload/sign out and back in:
    normal returning use should resume. Account lets you edit the Handle later; changing only its case must
    not collide with your own claim. Do not clear browser storage during inspection.
30. [ ] On a phone-width page, the compact sticky **Menu** opens/closes navigation
    and closes after choosing a route. Account and Sign out remain at the top.
    At desktop width normal navigation is available. Try a very wide window:
    content stays bounded rather than stretching indefinitely across the screen.
31. [ ] Compare Discover, Saved, My Listings, preview and possible-match sale
    cards. Phones use compact image-left/details-right cards; desktop has several
    cards per row. Long titles/descriptions clamp; price, condition and actions
    remain visible. Wanted cards use consistent neutral styling and budget placement.
    New Listing and New Wanted Request actions have matching compact sizing.
32. [ ] Open category/condition menus. Checkbox and label share a row. Select
    several choices, then click outside or press Escape: the panel closes and
    choices remain. Search & filters starts expanded in both discovery views;
    collapse it and check that the applied query/categories/bounds remain clear.
    Reopen without losing the draft or changing the applied URL state.
33. [ ] Original price uses **Seller Provided** on cards and details. Listing
    details show facts in a divided, labelled table layout after the description,
    with columns when they fit and stacked rows on a phone. Wanted
    creation is bounded like sale creation; matches are above Description and
    can be hidden/shown without losing any draft input.
34. [ ] Inspect the chat itself: recognizable item context and peer Handle,
    readable message bubbles, usable composer, separated buttons and responsive
    offer controls. **Share contact details** and seller **Buyer tracking** are
    labelled sections below the composer. The inbox has distinct bounded origin
    boxes, useful photos and no large empty gaps. Check both light and dark mode.
35. [ ] With seller and buyer encryption set up in their separate browser
    profiles, keep seller on Discover and send three new bicycle-thread messages
    as buyer. Seller's navigation unread count should increase within about five
    seconds. Open that thread: it starts at the text immediately before the first
    unread message when available, then shows an **X unread messages** divider.
    Contact-sharing entries count as unread too. Only displayed entries are
    acknowledged; sending a message clears the opening divider. Leave/reopen after reading:
    the thread opens at the latest messages without an unread divider. While
    reading older messages, a new arrival must not force a jump. **Load earlier
    messages** retrieves bounded history; a full history window offers **Load
    newer messages**. Message pagination is separate from inbox/group pagination.
36. [ ] Each group initially shows at most five conversations. Use **Show 5 more
    conversations** and **Hide conversations** on one group without affecting
    another; rows have clear, heavier separators. The group unread total stays in
    the heading while collapsed and expanded. Previous, Page and Next stay on one line
    at phone width. In By Person, check every included item still has its own detail link and
    the correct seller controls. Selected buyer/current offer stays in the
    relevant listing context. The bicycle box has 24 threads, including 22 `pagination_XX` fixture peers. Click **Show 5 more conversations** repeatedly to reveal the remaining threads. Those peers intentionally have no browser keys; use the named main actors for real encrypted chat. The extra rows exercise pagination and waiting-for-setup states. The API regression separately verifies that the group unread total includes messages beyond the first 20 rows.
37. [ ] In a longer thread, confirm one centered date separator appears when the
    local calendar day changes. Each message shows only local hours and minutes
    with AM/PM, without repeating the date or showing seconds.
38. [ ] After completing encrypted-chat checks, clear only the seller actor's
    site data for this inspection origin and sign in again as seller. Account
    setup should explain that the local key is missing, old encrypted data cannot
    be recovered and peers may need to accept a new key. Create a fresh key only
    if you accept losing access to prior ciphertext; do not do this before chat checks.

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

For this session, use the launcher PID printed in the latest handoff or press
Ctrl+C in its foreground terminal. This stops the server,
removes only its disposable PostgreSQL container, and deletes its temporary
photos/records. Browser IndexedDB/local keys remain until you clear site data for
`http://127.0.0.1:5176`; clear those only after finishing the inspection. No
retained developer database is reset.

To recreate the entire dataset and run the sweep before serving it again:

```bash
cd /home/suraj/src/clip-planning-main
PATH=/home/suraj/src/.clip-tools/uv-0.10.7:$PATH UV_CACHE_DIR=/tmp/clip-uv-cache CLIP_ENVIRONMENT=test .venv/bin/python scripts/marketplace_inspection.py --synthetic-inspection --port 5176
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

The current 2026-10-28 run repeated all **21 action groups** against the built
app with the real local database and Hybrid model; all passed. It is serving on
5176 with fresh data. A prior attempt on 5174 also passed its action sweep but
could not bind because that port was already in use, then cleaned up its fixture.
These are automated/programmatic results. Human visual observations are pending.

## Current verification receipt

See the [file-by-file implementation and verification report](next-03-visual-feedback-implementation-report.md). The fresh handoff action sweep passed all 24 groups. The complete `make check` passed, followed by final frontend verification (495 passed/3 skipped), supplemental legacy Handle migration/privilege checks and the expanded PostgreSQL Conversations suite (169 passed). Chromium checked the three centered sale-card actions at 360px, 390px and 1440px; collapsed conversation group headers; responsive listing facts and inbox pagination; no horizontal overflow or console errors. Browser messaging/key checks used a discarded preflight database. This fresh dataset starts without browser-published encryption keys so you can inspect first-device setup yourself. Your visual review is the remaining local gate.
