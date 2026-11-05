# SE-01 public search mode and relevance proposal

**Current disposition (2026-11-05 15:26:56 UTC): Aditya confirms Hybrid/search mode lifecycle and UI acceptance complete. Earlier pending browser/lifecycle checklist wording is historical and superseded for task status.**

**Status:** Mohit-verified specification; source/generated API checkpoint implemented,
API result verified by Mohit. Frontend controls/URL/request handling implemented
and automated-tested; human browser verification and application lifecycle remain pending. Mohit selected Keyword as the
initial mode, switching both ways with short explanations, and relevance sorting
in **both** modes. Mohit verified the proposal and clarified that
search implementation decisions are his. Shared compatibility and independent
review follow the normal PR process, not a separate implementation approval. This document specifies the registered query amendment; it grants no deployment
or merge permission. Frontend controls are a separate checkpoint.

**Owner:** Mohit (Search); Listings owns the query/data boundary. Primary affected
reviewer: Suraj; retain Identity review for caller eligibility. This continues
SE-01 amendment checkpoint5, not SE-02 or a new search endpoint.

## Audit and implementation sequence

The existing endpoint is `GET /listings`, operation `listings_query_available`.
`contracts/source/types.py:ListingQuery` is also aliased as
`AvailableListingQuery` for the internal Listings public callable. Responses stay
`ListingSummary` and `{items,page,page_size,has_next}`. Reviewed source is the
single input to the registered generator; never hand-edit generated files.

Two ordering issues must be resolved before registration: current keyword SQL
has no relevance rank, and the existing HTTP validator inherits generated query
types. Regeneration alone would accept new fields/sorts before dispatch is ready.
The earlier hybrid-only-relevance suggestion is superseded by Mohit's selection
of both-mode relevance. No other task-definition gap was found for this proposal.

Required sequence after this documentation checkpoint:

1. Mohit verifies search semantics and each implementation checkpoint. Shared
   compatibility and independent review remain required in the normal PR process;
   they are not a separate Suraj-permission gate before implementing search.
2. Explain/verify and implement the private keyword-rank checkpoint, with native
   checks and no model dependency. It is performed and verified by Mohit. This preparation does not activate a public input.
3. Explain/verify registered source/type/API work. Generate from source together
   with validation/dispatch/fail-closed guards and compatible consumer checks, so
   no widened validator can reach an unsupported sort or silently ignore a mode.
4. Explain/verify Search feature UI and test-only preview work against the
   reviewed generated contract; pause for human desktop/responsive/error checks.
5. Perform actual upstream/runtime/platform/data/evaluation/review gates before
   readiness or live activation. Application helper lifecycle/dispatch/bootstrap
   need their own verified implementation and resource/target approvals. This
   proposal does not enable workers or bypass unavailable ID-READY/LI-CORE.

## Exact proposed request surface

Add to the existing `ListingQuery` declaration, and hence its existing internal
alias and GET query schema:

| Field | Proposed definition | Rule |
|---|---|---|
| `search_mode` | Optional enum `keyword`, `hybrid`; default `keyword` | Omission uses Keyword. Values are case-sensitive; empty/unknown values return422. |
| `sort` | Enum `created_desc`, `price_asc`, `price_desc`, `relevance`; default `created_desc` | Relevance is valid in either mode when trimmed text is nonblank. |
| `q` | Existing optional trimmed plain text, <=120 Unicode code points | Omitted/blank means ordinary browse. Do not rewrite displayed/sent text to a spelling guess. |
| Other fields | Existing category/condition/negotiability/exact-paise/page fields | Existing validation, filters, page sizes20/50/100 and numbered-page bounds remain. |

No new route, response fields, scores, suggestions, model IDs or error vocabulary.
No new account permissions: eligible regular and temporary callers retain the
same access, and eligibility precedes retrieval/model work. No anonymous access.

Default ordering remains **Newest first** in either mode. Selecting Hybrid does
not implicitly select Relevance. Existing recency/price field and UUID tie rules
are retained over the selected mode's matching set.

| Trimmed `q` | Mode | Sort | Proposed behavior after auth/validation |
|---|---|---|---|
| Absent/blank | Either valid mode | Recency or price | Ordinary filtered browse; no semantic helper/coverage requirement. |
| Absent/blank | Either valid mode | Relevance |422validation_error. |
| Nonblank | Keyword | Any of the four | Keyword/vocabulary/typo matching; native keyword relevance when requested. |
| Nonblank | Hybrid | Any of the four | Keyword/vocabulary/typo plus semantic union; required capability/coverage must be ready, otherwise503. |
| Any | Invalid enum/filter/value | Any | Existing safe422validation_error; ignoring mode for blank text does not make invalid enum values valid. |

Nonblank text normalized by English full-text processing to zero lexemes gives
no Keyword matches. It is not the same as blank text: Hybrid may still perform
semantic matching on the original nonblank query. Raw tsquery syntax is never
accepted. Invalid sort/mode values are rejected, not silently defaulted.

## Keyword matching and relevance — proposed keyword-relevance-v1

Keyword mode enables the prepared bounded vocabulary/typo compiler while keeping
all original English full-text matches. It never consults model readiness,
embedding generations, helper capacity or downloaded model/interpreter files.
The keyword path still needs its normal Identity/database/catalogue dependencies;
this is not a promise to work during a general backend outage.

For relevance, filter eligible rows and match the whole original/expanded query
before ordering or pagination:

1. Original-query matches first, using `plainto_tsquery` with the same stored
   English configuration and combined title/description vector. This means
   normalized word matching, not a literal exact-title guarantee.
2. Expanded/typo-only matches next, under the existing one-way vocabulary,
   ambiguity/work limits and independent-AND/added-phrase semantics.
3. Within the original tier, order by
   `ts_rank_cd(search_vector, original_query, 0)` descending. Within the
   expanded-only tier, use `ts_rank_cd(search_vector, expanded_query, 0)`
   descending. Use the existing positional vector/default weights; no new
   title-weight/index migration is selected. Zero-rank matches are retained.
4. Ascending listing UUID is the final tie-breaker. No keyword rank cutoff,
   candidate cap or per-page reranking. Numeric ranks remain internal and are
   not comparable to semantic cosine scores across modes/queries.

This rule is now [implemented and native-tested privately](../docs/architecture/keyword-listing-relevance.md),
with its result verified by Mohit. Public source/type/validation/dispatch work
is now performed; its result awaits verification. Native
`ts_rank_cd` accounts for term proximity using stored positions; normalization0
adds no document-length normalization. See
[PostgreSQL18 ranking documentation](https://www.postgresql.org/docs/18/textsearch-controls.html#TEXTSEARCH-RANKING).
No extension or Python stemmer is needed for this proposed PostgreSQL operation.

Short/ambiguous/unknown vocabulary inputs and real-word collisions retain the
limits in the [typo policy](../docs/architecture/search-typo-tolerance.md).
Original matches are retained, but extra matches intentionally broaden results.
Do not promise arbitrary brand spelling correction or semantic typo tolerance.

## Hybrid matching and relevance — existing private hybrid-blend-v1

Retain the human-verified private rule: original/expanded/typo union plus semantic
additions at35%title+65%maximum-description cosine>=0.35. Original matches rank
above expanded/typo matches above semantic-only matches; descending blended
score and ascending UUID break ties. Keyword matches remain even below cutoff.
No pre-pagination semantic cap. Recency/price sorts operate on this same union.

The [private reader](../docs/architecture/hybrid-listing-read.md) requires the
supported serving space and complete current vectors for every eligible filtered
listing in the same snapshot as scoring/page construction. A nonmatching eligible
listing awaiting vectors can still cause503; a filter may exclude that listing
and permit a complete result. No hybrid page silently drops uncovered sources.
The accepted telescope limitation remains recorded, not relabeled or removed.

Keyword relevance and Hybrid relevance intentionally use different within-tier
scores. Switching modes may change matches and order; both are explicitly called
Relevance for the selected mode. Neither is final measured usefulness acceptance.

## Failure, privacy and compatibility

- Use existing `503 dependency_unavailable` / `Required dependency unavailable`
  for missing hybrid capability, queue capacity, timeout, unsupported serving
  model or eligible-source coverage gaps. No partial hybrid page and no automatic
  keyword-only success labelled Hybrid.
- Keep existing safe401/403/422and other common errors. Invalid active catalogue
  filters retain422 rather than being disguised as coverage503. Never return raw
  database/helper traces, embeddings, source hashes, private owner/selection data
  or rank/coverage internals. Keep required private/no-store response behavior,
  including availability failures; verify headers at the owned HTTP composition.
- Keyword remains independent of semantic failure. Switching modes is an explicit
  user action and a new request; a general database/auth outage can affect both.
- Old request/response **shapes** remain compatible: omitted mode is Keyword and
  omitted sort remains created_desc. Keyword matching now intentionally adds
  curated/typo results, so result membership/page positions can broaden. Do not
  promise identical old result sets. Empty-text browse remains unchanged.
- `AvailableListingQuery` remains an alias, not a duplicate model. Verify internal
  callers and owned doubles as well as generated OpenAPI/Python/TypeScript.
  Test doubles prove contract consumption only, never model/query correctness.

Examples below describe the registered API inputs (nonblank Hybrid needs
explicit managed capability; normal startup has none):

```text
GET /listings?q=bicyle
GET /listings?q=vehicle&search_mode=keyword&sort=relevance
GET /listings?q=keep%20food%20cold&search_mode=hybrid&sort=relevance
GET /listings?search_mode=hybrid&sort=price_asc
GET /listings?search_mode=hybrid&sort=relevance       ->422(blank text)
GET /listings?q=book&search_mode=semantic            ->422(unknown mode)
```

## User controls and exact proposed short copy

Initial mode is Keyword when the browser URL has no explicit mode. A valid
Hybrid URL/bookmark preserves that explicit selection. No account preference,
local-storage default, automatic query-based switch or model-triggered switch is
selected. Users can switch either way while loading, after success or after error.

| Control | Proposed short explanation |
|---|---|
| Keyword | “Matches words and known item terms, with limited typo tolerance.” |
| Hybrid | “Adds related meanings to keyword matches.” |
| Relevance | “Orders matches using the selected search mode.” |

Use visible associated help text or an accessible focus/touch explanation, never
hover-only information. Keep the selector enabled for blank text; explain that
Hybrid takes effect when search text is entered. Relevance is unavailable without
text. When a user clears text through the form, choose Newest first rather than
sending an invalid relevance request; manually invalid URLs still show validation.

Mode changes immediately rerun the **currently applied** query, preserve applied
filters/sort/page size, and reset page1. They must not silently apply or discard
unsaved filter-form edits. Keep those drafts separate from the immediate selector.
Normal Apply/reset behavior remains explicit. A mode change cancels/invalidates
the previous request; late results cannot overwrite the new selection or be
mislabelled. URL serialization omits default Keyword/created_desc and preserves
nondefault mode, sort and applied query for reload/back/forward.

For a failed nonblank Hybrid request, show:
**“Hybrid search is temporarily unavailable. Retry or use Keyword.”**
Keep the search/mode controls usable. Retry repeats the same applied request;
Use Keyword changes mode explicitly, retains applied inputs/sort/page size and
resets page1. Hide the stale result page on loading/error; never present old
Keyword results as a successful Hybrid page. Keyword failures use the ordinary
retry/error flow.503is a controlled response, not a website crash. No user-facing
model/pipeline/embedding/version/resource details are needed in this flow.

## Review packet, downstream file map and acceptance checklist

The actual shared-source edit will be `contracts/source/types.py`; verify its
use in `contracts/source/listings.py` rather than adding a new endpoint/callable.
Regenerate all registered outputs with the existing generator. Expected runtime
surfaces are the owned browse validation/service/store and private hybrid adapter;
Search UI/query/parser/API tests live under the existing public Search feature
entry point. No Listings private frontend import or shared page rewrite is needed
for mode controls. Reserve any shared composition/error file before editing it.

Before registering/activating the new interface, require:

- [x] Mohit selected/verified the search proposal and private keyword-rank plan.
- [ ] Shared signature compatibility and independent review complete in the normal
  PR process before merge; this is not extra permission to implement the domain.
  Identity eligibility/privacy boundaries remain required.
- [x] Private native keyword relevance checks performed and verified by Mohit: membership, original-before-expanded
  tiers, rank order/proximity, stable ties/pages at20/50/100, safe bounds/filters,
  zero-lexeme behavior and independence from missing/failed semantic capability.
- [x] Source, generated schemas/types, actual HTTP validation/dispatch and consumer
  models agree on all mode/text/sort combinations. Unknown modes/blank relevance
  produce422, unavailable hybrid503, and no unsupported sort reaches legacy SQL.
- [ ] Both modes authorize and filter before pagination; Hybrid retains its
  one-statement coverage/read guard and existing private-model checks.
- [ ] Browser URL/form/API controls, visible help, switching, abort/late responses,
  retry/keyword action and blank text are verified with contract/interaction tests
  and human desktop/narrow portrait/landscape checks. Device gaps stay explicit.
- [ ] Actual upstream schemas/auth/images, full data/final20+human labels, Linux/
  resources/runtime lifecycle, full CI/secret scan, independent exact-code review
  and original FR/NFR/readiness gates pass at their assigned checkpoints. A
  reviewable proposal or isolated UI must not claim them complete.

This document introduces no executable code or configuration and requests no
cloud/hosting/commit/push/merge action. Those keep their separate approvals.

## UI-only default amendment — 2026-10-26

Mohit approved making Hybrid the Search UI default and removing the visible
mode selector/Keyword recovery button. API omission still means Keyword; the
frontend explicitly sends its selected mode on every read. Its clean URLs omit
the Hybrid default and retain explicit Keyword URLs for compatibility. Both
backend modes, sort choices and generated contracts remain unchanged. See the
[decision amendment](../docs/decisions/hybrid-listing-search.md).
