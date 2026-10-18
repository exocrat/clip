# Listing type, availability window and saved visibility

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 Listings/Search review.

## Question
What do listing type and availability dates mean for discovery and saved listings?

## Options considered
- Use the approved Sale Listing/Wanted Request distinction, with independent seller status and time-window filtering.
- Add another listing-type taxonomy or collapse time eligibility, seller availability and selection into one state; this would introduce behavior not established by the current sources.

## Selected choice
- The listing-type filter means Sale Listing versus Wanted Request, matching the approved discovery toggle. Free items are Sale Listings with asking price zero; no extra free-item object/type is introduced.
- Sale Listings have a required start instant and optional end instant. They are excluded from discovery before the start and at/after the end. A supplied end must follow the start.
- Seller-controlled available/unavailable status is independent from the availability window and buyer selection. Passing the end does not itself rewrite the seller's status; both status and current time determine discovery eligibility.
- Saved references survive seller unavailability and the end of the availability window. Access/account rules still apply; this is not indefinite-retention approval.
- If the start is omitted, use the server creation instant. Owners may edit a valid window and toggle availability; neither action reassigns selected buyer. Retired origins cannot reopen. Content retirement and retained-reference lifetime follow the separate origin-retirement decision.

## Rationale
The distinction matches existing discovery composition while preserving authoritative seller state and references to previously saved items.

## Implications
PD-08 represents distinct Sale Listing/Wanted Request tables and time/status/retirement fields. No additional stored listing-type column is needed on either table. LI-01/SE-01/SE-02 must apply the same request-time predicate and preserve saved references; Listings owns sale queries/indexes. DL-00 defines public filter spellings, authorization and boundary-time tests. Retirement must never weaken the mandatory price/image/field rules for live listings.

## Approver
Mohit (C), explicit approval of the four proposed interpretations. Listings/affected-owner schema review remains pending.

## Supersedes
None; clarifies FR-04/07/09 and the existing discovery toggle without modifying the submitted PRD.
