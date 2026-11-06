# Initial catalogue and listing field limits

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 catalogue/limit review.

**Revised:** 2026-10-21, LI-01 Step 7 pickup-area correction by Suraj (B).

**Revised:** 2026-10-28, NEXT-03 Steps 7 and 9 by Suraj (B).

## Question
Which category/condition values and text/image limits should the initial schema support?

## Options considered
- Stable catalogue rows with editable labels and active flags, reused through public interfaces.
- Hard-coded database enums or unrestricted free-form category/condition values, complicating catalogue evolution or consistent filtering.

## Selected choice
Mohit approved the catalogue and limits in this decision; the installed seed and forward changes are the ordered [database migrations](../../database/migrations/).

- Category codes: `mobile_phone`, `laptop`, `electronics`, `furniture`, `books`, `bicycles`, `appliances`, `sports_fitness`, `other`. Labels are Mobile Phones, Laptops, Electronics, Furniture, Books and Study Materials, Bicycles, Home Appliances, Sports & Fitness, Other. Electronics excludes mobile phones, laptops, and household appliances. Mobile phones and laptops carry the FR-17 sensitive-category flag; the independent price-threshold rule still applies to every category.
- Condition codes: `new`, `like_new`, `good`, `fair`, with the seller-declared meanings in the schema. These are not platform quality/functionality guarantees.
- Titles: 1–120 Unicode code points after outer whitespace trimming. Pickup area is optional; when supplied it uses the same 1–120 limit. Descriptions: 1–5,000 under the same counting rule. Shared title/description bounds apply to both Sale Listings and Wanted Requests.
- Publishable listings: 1–8 usable images, each positive-sized and at most 10 MiB (10,485,760 bytes); JPEG, PNG and WebP only. Actual-object validation and race-safe count enforcement are required.
- Listings owns catalogue writes/public read-validation; Search reuses the categories through the reviewed boundary. Deactivation prevents new assignment while retaining historical references; deletion remains restricted pending retention review.
- Asking prices, optional seller-stated Original price, Wanted budgets, and their discovery filter bounds use whole rupees from ₹0 through ₹1,00,00,000 inclusive. Original price, when supplied, must be positive. The ceiling keeps browser/API/database amounts exact while rejecting implausibly large typos.
- Sale Listings may include an optional Original price supplied by the seller to give buyers context alongside the asking price. CLIP does not verify it or infer a discount; blank means no value is shared. Retired listings clear it with the rest of their content.

The PR #5 reviewer clarified that **item category** is the maintained name for this catalogue: it describes what the item is, independently of the Sale Listings/Wanted Requests view. This does not add another category field or filter.

On 2026-10-28, Suraj (B) approved the NEXT-03 catalogue: retain the existing stable codes and add `sports_fitness`; keep `electronics` as Electronics and label `appliances` Home Appliances. Keep existing `other` records as Other unless their owner explicitly reclassifies them; do not infer a real listing's category from its text.

For NEXT-03 Step 2, Suraj directed title-case display labels throughout the
catalogue, including **Like New**. Forward migration
`20261028100100_marketplace_title_case_labels.sql` changes display text only;
codes and existing category/condition assignments stay the same. Its rollback
restores the labels from the preceding catalogue revision.

Pickup-area optionality was corrected by Suraj during the LI-01 browser check.
Create omission or null means not provided; full replacement requires a nullable
field, with null clearing a previous value. Empty/whitespace-only API strings
remain invalid; the browser maps a blank field to omission on create. Store
absence as SQL NULL and display it as Not specified. Existing provided areas
remain valid. This changes no category/condition values or other required fields.

## Rationale
Provides a small shared initial vocabulary, explicit mobile/laptop classification, and bounded text/image inputs without embedding catalogue labels in PostgreSQL enum types.

## Implications
LI-01/LI-02/SE-01/SE-02 and DL-00 must preserve consistent validation/filter semantics. NEXT-03's forward migration `20261028120000_sale_original_price_and_marketplace_amount_cap.sql` stores the optional Original price and enforces the same inclusive ₹1 crore cap on sale asking prices and Wanted budgets. No ciphertext limit, image decoding/dimension policy, sensitive-price threshold, provider choice or deployment is approved by this decision.

## Approver
Mohit (C), explicit approval of the presented catalogue and field-limit proposal. The user later confirmed the PD-08 affected-owner schema gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). This records the gate status without inferring a reviewer identity.

The pickup-area correction was directed by Suraj (B), 2026-10-21. The work log records the affected consumer/schema review and LI-01/NEXT-03 completion; this decision is not a live schema-state check.

## Supersedes
None.
