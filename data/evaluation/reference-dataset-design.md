# Proposed reference dataset for NFRs and the architecture comparison

**Status:** NEXT-06/DATA-READY is marked complete in the [work log](../../docs/status/work-log.md) and the [task-wide review](../../docs/evaluation/domain/next-06/task-wide-review.md). This file preserves the accepted corpus design and reproducibility requirements; its old preparation gates are historical, not current task status or permission to rebuild/load data.

## Reproducible inputs

- Use seed **42** and logical time `T` at UTC midnight on generation day.
  **Evaluation amendment approved by Mohit (recorded 2026-10-30 12:26:18 UTC):** the
  benchmark window is `[T + 1 hour, 2026-12-01T00:00:00Z)`. The reference corpus
  has 5,000 regular users; temporary-account permission fixtures are separate and
  retain the actual 14-day lifetime. Listing states stay stable throughout November.
  Material schema/code/configuration changes still require revalidation; this
  amendment avoids expiry-driven regeneration, not all possible revalidation.
  Record exact source/schema/config/image/model state and freeze before matched
  measurements. Both architectures use the same logical corpus and settings.
- Reuse the existing stable synthetic identifiers and canonical fingerprinting
  from `data/generators/`. IDs, content and assignments must be deterministic for
  the same seed, `T`, source, schema and configuration. Generate twice in fresh
  run locations and compare the logical fingerprint. Exclude generation/audit
  timestamps and credentials from the logical fingerprint.
- Use hash-based deterministic permutations for independent assignments of
  category, condition, price, listing availability, owner and optional fields;
  verify exact counts after assignment. This avoids an accidental rule such as
  all low-priced items having the same condition. Use the same inputs for both
  architectures and freeze the final data, indexes and model pipeline.
- For each listing assignment, sort the 1,000 stable listing IDs by the bytes
  of `SHA-256("42:<assignment-name>:<listing-id>")`, breaking a digest tie by
  ID. Use assignment names `category`, `condition`, `price`, `negotiable`,
  `proof` and `availability` respectively. Partition that order into consecutive
  groups of the specified sizes in table order. Use the approved NEXT-03
  category codes and verified counts below. Record final counts and item
  mapping before data generation.
  Sort the 5,000 regular user IDs using
  `SHA-256("42:owner:<user-id>")` and assign the first 1,000 in order to
  listing IDs sorted using `SHA-256("42:listing-owner:<listing-id>")`.

## Users and real test sessions

Generate **5,000 active regular synthetic users**, created at `T - 1 day`,
with valid unique claimed Handles and no activation/expiry dates. This supersedes
only the original 4,800/200 reference mix. Temporary accounts are tested separately
with fresh authorized fixtures and their unchanged 14-day product policy; those
mutations are outside the frozen comparison corpus. No long-lived temporary user
or future-dated activation is invented. Addresses, if required by another fixture,
use `example.invalid`. Do not create passwords, OTPs, real contacts, private keys,
fabricated sessions or outbound sends in bulk reference data.

The 5,000 generated users establish reference-data scale; they do **not** by
themselves establish valid sign-in sessions. The PRD does not require 50 signed-in
test accounts. Use the smallest practical number of existing authorized accounts
for the measured reads, initially one regular account, with sessions established
outside the timing window. Two legitimate participants are needed for the separate
chat check. Confirm that the selected accounts and sessions work under the real
rate limits; if the actual configuration prevents the intended test, report the
result and review the smallest practical solution. Do not fabricate tokens, bypass
verification or change limits merely to pass. Record the number/classes used and
their effect on interpretation; do not put credentials or private personal data
in retained evidence.

## Sale listings

Generate **1,000 live listing records**, each with one valid confirmed image
and a distinct synthetic ID. Suraj verified the category list, balanced test
counts and proposed item topics below on 2026-10-28. The mix is not a claim
about marketplace demand. NEXT-06 still generates and validates the data;
search relevance labels receive their separate human review.

| Category code | Five verified proposed item descriptions and synonym text |
|---|---|
| `mobile_phone` | Android smartphone → Android cell phone; iPhone → Apple mobile phone; basic mobile phone → simple cell phone; dual-SIM smartphone → dual SIM cell phone; refurbished smartphone → used mobile phone |
| `laptop` | Student laptop → student portable computer; office laptop → work portable computer; compact laptop → small portable computer; refurbished laptop → used portable computer; gaming laptop → gaming portable computer |
| `electronics` | Desk monitor → computer display; headphones → personal audio headset; speaker → audio loudspeaker; camera → digital photo camera; projector → video display projector |
| `furniture` | Study desk → study work table; office chair → work seating; bookshelf → book storage shelf; bed frame → sleeping bed base; dining table → eating table |
| `books` | Linear algebra textbook → mathematics book; chemistry textbook → science study book; biology textbook → life science book; economics textbook → economics study book; computing textbook → computer science book |
| `bicycles` | Campus bicycle → two wheeled vehicle; commuter bicycle → daily travel cycle; mountain bicycle → off road cycle; road bicycle → road riding cycle; folding bicycle → folding cycle |
| `appliances` | Electric kettle → kitchen water boiler; toaster → kitchen bread toaster; rice cooker → kitchen rice appliance; table fan → desktop cooling fan; kitchen mixer → food mixing appliance |
| `sports_fitness` | Badminton racket → racket sports equipment; yoga mat → exercise floor mat; dumbbells → hand weights; football → sports ball; tennis racket → tennis equipment |
| `other` | Backpack → student carrying bag; umbrella → rain cover; water bottle → reusable drink container; stationery kit → pens and notebooks; storage box → plastic storage container |

For each item, construct a title `Synthetic <item description> <four-digit
ordinal>` and a description `Synthetic <item description>. <synonym text>.
Condition: <condition label>. For campus use.` using the corresponding table
values and final approved condition label. Store these 45 verified proposed
text/synonym pairs as versioned generator input; do not pull uncontrolled real
listings. Use the same text for both versions.
Apply the current 120-character title and 5,000-character description limits.
Review the proposed topic/synonym set and mapping against the approved NEXT-03
categories, then freeze the exact set and counts with the dataset. Avoid
claiming that any proposed synonym is a human relevance judgment.

Assign independently, with exact totals. Suraj verified the category mix below
on 2026-10-28. It is a balanced test corpus, not a claim about real marketplace
demand. Its one-item remainder is assigned to Mobile phones so the recipe is
deterministic.

| Category code | Approved listing count |
|---|---:|
| `mobile_phone` | 112 |
| `laptop` | 111 |
| `electronics` | 111 |
| `furniture` | 111 |
| `books` | 111 |
| `bicycles` | 111 |
| `appliances` | 111 |
| `sports_fitness` | 111 |
| `other` | 111 |

These counts sum to 1,000 and give every category at least 111 listings for
filtered-browse and query cases.

Assign the other attributes independently, with exact totals:

| Attribute | Proposed distribution |
|---|---|
| Condition | 250 each of `new`, `like_new`, `good`, `fair`, subject to the final approved catalogue. |
| Price | 100 listings each at ₹0, ₹250, ₹500, ₹1,000, ₹2,000, ₹3,000, ₹5,000, ₹8,000, ₹12,000 and ₹20,000; store whole rupees as integer paise. |
| Negotiable | 500 true and 500 false; retain it as a listing property, not a search filter. |
| Proof declaration | 334 omitted, 333 yes, 333 no where the final schema permits; verify sensitive flags against the actual configured threshold and categories. |
| Availability | 800 available at the comparison time, 100 explicitly unavailable, 50 future and 50 expired. |

Let `C = 2026-12-01T00:00:00Z`. For the 800 available and 100 unavailable
listings use `[T - 1 day, C + 30 days)`; mark the 100 unavailable explicitly.
For 50 future listings use available state with `[C + 1 day, C + 30 days)`.
For 50 expired listings use available state with `[T - 30 days, T - 1 day)`.
Thus all four cohorts remain stable throughout November. Keep records non-retired
and verify actual cleanup settings rather than bypassing retention.
Set created and updated timestamps to `T - 2 days`, with a deterministic ID
tie-breaker; verify pagination across ties. Assign pickup areas `Synthetic Zone A`,
`Synthetic Zone B`, `Synthetic Zone C` and `Synthetic Zone D` in equal groups of
250 using the `pickup` hash assignment. Recheck these values against the final
schema; no pickup location represents a real address. Recheck all
constraints and the approved category mapping before data generation; do not
silently map an obsolete category or use unreviewed category counts.

## Images, indexes and search model

Create **1,000 distinct confirmed image records and object keys**, one for each
listing, backed by valid image objects in the approved test bucket.

**Real-photo amendment (Mohit; recorded 2026-10-30 11:27:31 UTC):** replace the earlier eight
256×256 solid-colour swatches with45user-supplied product photos, one for each
approved item topic above. Mohit supplied the folder and replaced two AVIF inputs
with JPEGs. [The source inventory](reference-image-inputs.json) binds each topic
and category to a relative source path, exact bytes/digest, type and dimensions.
The dual-SIM filename typo is an explicit mapping; do not rename source files or
infer further aliases. Original input files remain external to Git. JPEG/PNG/WebP
are accepted only within the current10MiB/file limit. Preserve source bytes and
freeze their digests; the photos are reused across matching item-topic listings
with distinct per-listing records/keys. This does not require1,000unique photographs.

All other counts, distributions, seed42, timestamps and review requirements remain
unchanged. The exact deterministic topic assignment and resulting1,000-object
manifest are Step2 outputs. Verify every referenced object through the real
authorized image path in Step3, including its byte digest and owner linkage.
Source-folder metadata checks do not establish full decode/visual validation,
object upload, application confirmation/delivery or cloud readiness. Earlier
metadata-only previews remain insufficient. Review exact storage/upload volume,
cost and cleanup with the later cloud plan before uploading anything. Image-body
transfer stays outside browse latency measurement.

Apply the accepted migrations and final catalogue; verify counts, foreign keys,
availability windows, allowed users, image records and the indexed text search
path. Run the approved real Hybrid preparation/queue/worker/activation workflow;
verify the selected pipeline and current source coverage for every eligible
listing. Record model, tokenizer, vocabulary, pipeline and index versions and
fingerprints. Do not copy unrelated embeddings, treat generated vectors as a
relevance pass, or silently switch search modes. The exact operator commands are
the existing registered commands only after their target and later plan are approved.

## Search cases and human review

Propose these **22 query texts** as initial examples, two per category plus
four broader cases. Review them against the approved categories and proposed
dataset content before they are frozen. The rows
use no category filter unless an explicitly reviewed context says otherwise:

| Category | Queries |
|---|---|
| Mobile Phones | `android smartphone`; `mobile phone` |
| Laptops | `student laptop`; `portable computer` |
| Electronics | `desk monitor`; `computer display` |
| Furniture | `study desk`; `work table` |
| Books | `linear algebra textbook`; `mathematics book` |
| Bicycles | `campus bicycle`; `two wheeled vehicle` |
| Home Appliances | `electric kettle`; `water boiler` |
| Sports & Fitness | `badminton racket`; `sports racket` |
| Other | `backpack`; `student carrying bag` |

The four broader cases are `student computer`, `folding cycle`, `kitchen
appliance` and `study furniture`. These are proposed inputs, not claims that
the current model retrieves relevant results. A human reviews relevant listing
IDs from the fixed corpus independently of the measured top-five results,
records inclusion decisions and review metadata using the existing
[label format](../formats/query-labels.md), and freezes the final file at
`data/evaluation/query-labels.json`. At least 20 included cases must have their
actual reviewed judgments; preserve unsuccessful cases and exclusions. An
included case with no relevant item remains a failed query under that format.

Build fixed, separately reviewed browse, filtered browse, search and detail
reference cases using the actual final public API contract. Include first and
later pages, unavailable exclusion, tied ordering, category filtering, direct
word matches and related/meaning-based searches. Retain expected IDs, expected
order where deterministically specified, non-sensitive response fields and case
fingerprints. Review the expected results independently of final measurements;
do not manufacture a full ranking from relevance labels or adjust references to
make a particular architecture pass. Step 4's generator cycles through these
cases using the same recorded seed and order for both alternatives.

## Other NFR fixtures and validation

NFR-05 needs a real two-client encrypted conversation and fresh controlled test
messages; its detailed sample count, participant accounts, setup and cleanup
belong to NEXT-01 Step 6/CN-01, not fabricated plaintext or fake keys in this
corpus. NFR-03's integrated read/write fixture needs likewise follow Step 6 and
INT-01. Run any such fixture mutations outside frozen comparison windows and
revalidate the final data/index/model state before comparative measurements.
NFR-06/07 use their separately approved recovery/restore targets; this recipe
does not authorize cloud writes or destructive reset.

SE-01/NEXT-06 must produce a manifest and checks showing exact requested and
observed counts, reproducible logical fingerprint, schema and source revision,
category/condition/price/state distributions, regular-owner relationships,
constraints, image-object coverage, index/model readiness, reviewed label
revision and 20+ included cases. Recheck the same logical dataset and relevant
settings before each A/B pair. Existing `search_preview` and its local loader
provide reusable scaffolding, but are preview-only: they do not create real
sessions, real image objects or final reviewed relevance labels. Final commands
and acceptance evidence are created and registered by the owning tasks; no
unimplemented command is implied here.

## NEXT-06 Step2 implementation binding

The versioned topic/configuration input is [reference-recipe.json](reference-recipe.json).
It preserves the approved45topic/synonym pairs and exact table counts. Category
and other approved assignment hashes remain unchanged. Within each assigned
category, order listing IDs using
`SHA-256("42:topic:<category-code>:<listing-id>")` with ID ties, then cycle its
five topics in their versioned table order, giving22or23records per topic. Each
listing takes the exact photo matched to its category/topic in the source inventory.

The local generator and commands are documented in [the data guide](../README.md#next-06-reference-inputs-and-local-loading).
Its per-listing relative image keys and unique image/upload/operation IDs are
planned inputs, not evidence of confirmed rows or uploaded objects. Actual approved
bucket/prefix binding, storage transfer, image confirmation and SQL validation
remain Step3. Local output has phase generated-unloaded and all acceptance flags
false. Final source acceptance, model coverage, reviewed labels, reset/reload and
freeze remain required.
