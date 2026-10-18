# Initial catalogue and listing field limits

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 catalogue/limit review.

## Question
Which category/condition values and text/image limits should the initial schema support?

## Options considered
- Stable catalogue rows with editable labels and active flags, reused through public interfaces.
- Hard-coded database enums or unrestricted free-form category/condition values, complicating catalogue evolution or consistent filtering.

## Selected choice
Mohit approved the catalogue and limits detailed in the [schema document](../architecture/mvp-database-schema.md):

- Category codes: `mobile_phone`, `laptop`, `electronics`, `furniture`, `books`, `bicycles`, `appliances`, `other`. Labels are Mobile phones, Laptops, Other electronics, Furniture, Books and study materials, Bicycles, Appliances, Other. Mobile phones and laptops carry the FR-17 sensitive-category flag; the independent price-threshold rule still applies to every category.
- Condition codes: `new`, `like_new`, `good`, `fair`, with the seller-declared meanings in the schema. These are not platform quality/functionality guarantees.
- Titles and pickup areas: 1–120 Unicode code points after outer whitespace trimming. Descriptions: 1–5,000 under the same counting rule. Shared title/description bounds apply to both Sale Listings and Wanted Requests.
- Publishable listings: 1–8 usable images, each positive-sized and at most 10 MiB (10,485,760 bytes); JPEG, PNG and WebP only. Actual-object validation and race-safe count enforcement are required.
- Listings owns catalogue writes/public read-validation; Search reuses the categories through the reviewed boundary. Deactivation prevents new assignment while retaining historical references; deletion remains restricted pending retention review.

The PR #5 reviewer clarified that **item category** is the maintained name for this existing catalogue: it describes what the item is, independently of the Sale Listings/Wanted Requests view. This does not add another category field or filter.

## Rationale
Provides a small shared initial vocabulary, explicit mobile/laptop classification, and bounded text/image inputs without embedding catalogue labels in PostgreSQL enum types.

## Implications
PD-08 Step 3 may implement these after the required schema/affected-owner review. LI-01/LI-02/SE-01/SE-02 and DL-00 must preserve consistent validation/filter semantics. No ciphertext limit, image decoding/dimension policy, monetary cap, sensitive-price threshold, provider choice or deployment is approved by this decision.

## Approver
Mohit (C), explicit approval of the presented catalogue and field-limit proposal. B/C affected-owner schema review remains pending; no independent approval by Suraj is inferred.

## Supersedes
None.
