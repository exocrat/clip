# Required seller asking price and optional buyer budget

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 amount/optionality review.

## Question
Which price/budget values are mandatory, and how is negotiability represented?

## Options considered
- Require a Sale Listing asking price and retain a separate negotiable flag; make the Wanted Request budget optional, preserving absence as null.
- Treat a negotiable listing as having no stated price, or replace absent buyer budgets with zero; both lose the distinction clarified by Mohit.

## Selected choice
The seller must give an asking-price value. Store it in non-null `asking_price_paise`; zero remains allowed under FR-04 and the approved free-listing rule. `negotiable` is a separate boolean, and setting it to true does not remove the required price. A buyer may optionally state a Wanted Request budget: store a supplied value in `budget_paise` and absence as SQL NULL, never an automatic zero. All money follows the existing whole-rupee/integer-paise convention.

Zero offers are valid, supporting free-item exchanges. An explicitly entered zero Wanted Request budget means the buyer seeks a free item. An absent budget remains “no amount stated”; it does not imply a zero budget. Negative amounts are invalid.

## Rationale
Preserves a concrete seller price, independent permission to negotiate, and the distinction between an unstated buyer budget and an explicitly entered amount.

## Implications
PD-08 retains the proposed non-null seller price/boolean and nullable request budget, allowing nonnegative whole-rupee values for asking prices, offers and supplied budgets. LI-01/SE-02/CN-02 and DL-00 must preserve these distinctions in validation, public types and UI. On 2026-10-28, NEXT-03 selected an inclusive ₹1 crore cap for listing asking prices, optional Original price, Wanted budgets, and their discovery bounds; offers retain their existing separate bound. The storage type's representable bound does not itself select a product cap.

## Approver
Mohit (C), explicit seller/buyer clarification followed by approval of zero offers, zero-budget-as-free-item and absent-budget-as-unstated rules. The user later confirmed the PD-08 affected-owner schema gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence).

## Supersedes
None; clarifies existing FR-04/08 and the shared optionality convention.
