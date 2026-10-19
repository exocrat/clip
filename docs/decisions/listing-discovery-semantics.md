# Item category, availability window and saved visibility

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 Listings/Search review.
**Revision:** 2026-10-18 — PR #5 reviewer-directed terminology correction.

## Question
How do item category, the Sale Listings/Wanted Requests view, and availability dates affect discovery and saved listings?

## Options considered
- Use item category for the kind of item, reusing the existing category catalogue, independently of the Sale Listings/Wanted Requests view.
- Treat the item category filter as the Sale Listings/Wanted Requests toggle. The reviewer rejected this interpretation because it contradicts the approved frontend distinction.

## Selected choice
- **Item category** means the kind of item: phone, bicycle, furniture, books, etc. It reuses the existing Listings-owned category catalogue and `category_id` references; there is one category field/filter, not an additional taxonomy.
- **Sale Listings / Wanted Requests** selects the discovery view independently of item category. Free items remain Sale Listings priced at zero. The existing separate backend objects and view toggle do not define an item category.
- Sale Listings have a required start instant and optional end instant. They are excluded from discovery before the start and at/after the end. A supplied end must follow the start.
- Seller-controlled available/unavailable status is independent from the availability window and buyer selection. Passing the end does not itself rewrite the seller's status; both status and current time determine discovery eligibility.
- Saved references survive seller unavailability and the end of the availability window. Access/account rules still apply; this is not indefinite-retention approval.
- If the start is omitted, use the server creation instant. Owners may edit a valid window and toggle availability; neither action reassigns selected buyer. Retired origins cannot reopen. Content retirement and retained-reference lifetime follow the separate origin-retirement decision.

## Rationale
The reviewer confirmed Suraj's original distinction and renamed its ambiguous term to item category. The maintained requirements use one item category filter, while the separate view chooses sale listings or wanted requests. Availability and saved-reference behavior is unaffected.

## Implications
PD-08 represents item category through `listings.categories` and the existing `category_id` columns on Sale Listings/Wanted Requests. No column, migration or second filter is added for this terminology correction. The submitted PRD stays unchanged; its earlier wording is interpreted through the maintained product reference. LI-01/SE-01/SE-02 must apply the same request-time predicate and preserve saved references; Listings owns sale queries/indexes. DL-00 defines public filter spellings, authorization and boundary-time tests. Retirement must never weaken the mandatory price/image/field rules for live listings.

## Approver
The independent human reviewer explicitly confirmed Suraj's item-category interpretation and requested this correction in the PR #5 review session on 2026-10-18. Mohit's earlier availability/window/saved-record choices remain in effect. The user later confirmed the PD-08 Listings/Search affected-owner schema gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence).

## Supersedes
Supersedes this record's earlier interpretation that the item classification filter meant Sale Listing versus Wanted Request. Git history and dated work-log entries preserve that earlier decision. No availability, saved-reference or submitted-PRD change.
