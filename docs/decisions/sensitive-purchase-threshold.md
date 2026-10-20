# Provisional sensitive-purchase price threshold

**Date:** 2026-10-20

**Origin:** LI-01 Step 2.

## Question

What asking price should trigger the FR-17 sensitive-purchase flag, and who owns
that setting?

## Options considered

- Choose a provisional default now so Listings can implement and test the rule,
  while keeping the value changeable.
- Leave price-based flagging disabled until a final threshold is selected.

## Selected choice

Use **₹5,000 (500,000 paise)** as a provisional, configurable default. Listings
owns the setting. A listing is price-flagged only when its asking price is
strictly greater than the threshold. Mobile phones and laptops are flagged at
any price. The threshold is a placeholder and may be changed through a reviewed
configuration update; it is not a permanent product limit.

Because valid asking prices use whole-rupee increments, the price-only boundary
examples are ₹4,900 (not flagged), ₹5,000 (not flagged), and ₹5,100 (flagged).
The category rule independently flags every mobile phone and laptop.

## Rationale

This gives LI-01 a concrete value for implementation and boundary tests without
pretending the number is final.

## Implications

LI-01 Step 6 reads the threshold from Listings configuration rather than
embedding the number in the flagging logic. Tests cover the strict boundary,
category changes, price changes, and the seller's optional unverified proof
statement. Changing the value requires updating this decision and the reviewed
configuration, then rerunning the affected boundary tests.

## Approver

Suraj (B), Listings owner, directed the provisional value on 2026-10-20.

## Supersedes

None. This records a provisional value for the previously open threshold.
