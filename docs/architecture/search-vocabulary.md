# Curated listing-search vocabulary — version 1.0.0

**Origin:** SE-01 hybrid amendment checkpoint 2 / [DEC-13](../decisions/hybrid-listing-search.md).
**Status:** Mohit verified checkpoint 2 and authorized checkpoint 3. Not wired
into live search. Mohit confirms Suraj approved the amendment; native query
verification remains pending.

The controlled artifact is
[`search_vocabulary.json`](../../apps/api/app/domains/listings/search_vocabulary.json).
[`vocabulary.py`](../../apps/api/app/domains/listings/vocabulary.py) validates its
shape, alias ownership, one-way edges, absence of cycles and expansion budgets,
then exposes immutable records and a canonical-content SHA-256 fingerprint.
`load_vocabulary` reads only the adjacent checked-in artifact. The new
compiler uses it only through an explicit native-test store opt-in. Public
requests retain plain matching; no tagging or model calls are performed.

## Initial concepts

Aliases below are matching conveniences, not category assignments or statements
that the terms are equivalent in every context. Exact original query matching
must remain one of the alternatives. Vocabulary changes require version and
fingerprint updates and affected tests/review; never learn edits from users or
final evaluation judgments automatically.

| Concept | Aliases | Direct narrower concepts |
|---|---|---|
| vehicle | — | bicycle, motorcycle, car, scooter |
| bicycle | cycle | — |
| motorcycle | motorbike | — |
| car | automobile | — |
| scooter | — | — |
| book | — | textbook |
| textbook | text book | — |
| furniture | — | chair, table, desk, bed, wardrobe |
| chair | — | — |
| table | dining table | — |
| desk | study desk | — |
| bed | — | — |
| wardrobe | — | — |
| electronics | — | phone, laptop, tablet, monitor |
| phone | mobile phone, cellphone, smartphone | — |
| laptop | notebook computer | — |
| tablet | — | — |
| monitor | computer monitor | — |
| appliance | — | refrigerator, washing machine, microwave |
| refrigerator | fridge | — |
| washing machine | — | — |
| microwave | microwave oven | — |

**Ambiguity proposal:** `bike`, `notebook` and `display` remain ordinary literal
terms, without curated expansion. A bike might be pedal- or motor-powered; a
notebook might be paper or a computer; a display might be a screen or furniture.
The longer phrase `notebook computer` can identify the laptop concept. `book`
includes textbooks, but textbook does not broaden to all books. No new category
codes, seller fields or evaluation labels are introduced.

## Expansion rules for checkpoint 3

1. Recognize complete words/phrases, ignoring case. Align inflection matching
   with the same PostgreSQL English normalization as the stored vector; do not
   add a competing Python stemmer. Preserve unknown terms and the existing
   plain-text/stop-word behavior. Do not interpret raw user tsquery syntax.
2. Prefer the longest recognized phrase, consuming its words once. Each alias
   identifies its one owning concept. Thus `notebook computer` is recognized
   together, whereas `notebook` alone is literal. Matching is token-based, not
   substring replacement: `bookcase` must not trigger `book`.
3. For one recognized concept, OR the original input, canonical term and aliases
   with its direct narrower terms and their aliases. No recursive expansion or
   reverse broader lookup. All members of an alias group use the same narrower
   relationships. An unrelated concept remains an independent AND group.
4. Keep multiword alternatives as phrases with PostgreSQL phrase normalization;
   do not flatten `washing machine` into a choice of `washing` OR `machine`.
   Retain original input as an alternative, so expansion adds matches without
   replacing the user's lexical intent. Verify phrase inflection/token behavior
   with PostgreSQL rather than a fake in-memory matcher.
5. Bounds: at most 12 independent query groups, 16 alternatives per group and
   48 alternatives overall after deduplication; artifact phrases have at most
   three words and all original query inputs retain the 120-code-point limit.
   These are expansion budgets, not new limits on accepted lexical queries.
   If a query would exceed a budget, use the complete original plain-text query
   without curated expansion; never drop terms or expand only a partial prefix.
   Record a content-free internal expansion outcome, not raw query text.
6. Bind all text parameters. SQL operators and configuration paths never come
   from the vocabulary/user input as executable SQL. The validator rejects
   duplicate/ambiguous aliases, unknown/self/cyclic edges and oversized groups.
7. Record vocabulary version/fingerprint with evaluation configuration. Native
   SQL and matching tests must cover actual English stemming collisions and
   stop-word/phrase behavior before activation; syntactic validation cannot
   establish those properties. Curated expansion is not semantic inference.

## Query-planning acceptance cases (pending native implementation)

These specify expected expansion, not human relevance judgments or passed search
checks. Checkpoint 3 must turn them into planner/native matching tests.

| Query | Expected behavior |
|---|---|
| `vehicle` | OR vehicle with bicycle/cycle, motorcycle/motorbike, car/automobile, scooter |
| `cycle` | bicycle/cycle; no car, motorcycle or vehicle-parent expansion |
| `books` | English-normalized book plus textbook/text book; preserve original input |
| `textbook` | textbook/text book; no broadening to every book |
| `bike` | Literal only; no forced bicycle or motorcycle interpretation |
| `notebook computer` | Longest phrase maps to laptop alternatives |
| `notebook` | Literal only |
| `red mobile phone` | red AND the phone-alternative group; red is never discarded |
| `washing machine` | Phrase group; matching “washing” alone is insufficient |
| `book chair` | Book group AND chair group; not one large OR |
| `bookcase` | No substring-triggered book expansion |
| `vehicle helmet` | Vehicle alternatives AND literal helmet |
| operator-like/plain unknown input | Original plain-text semantics; never raw tsquery execution |
| over-budget expansion | Complete original query fallback, with no missing independent terms |

## Checks and remaining gates

`test_vocabulary.py` checks the actual artifact, directional configuration,
multiple domains, ambiguous exclusions, phrase aliases, deterministic fingerprints
and refusal of malformed configuration. It does not compile queries, match
listings or prove PostgreSQL functionality. No package dependencies are added.

Mohit verified these words/rules and confirms Suraj approved the amendment.
Before activation, native PostgreSQL tests must pass (currently no Docker/
PostgreSQL on this machine). Semantic model/storage/fusion remain later gates.
Final 20+ human-reviewed queries and real NFR-04 evaluation remain separate.

## Checkpoint 3 compiler preparation

`lexical_expansion.py` collects vocabulary/query tokens and asks the connected
PostgreSQL instance to normalize them with `plainto_tsquery` using the existing
English configuration. The planner compares those serialized normalizations for
longest-phrase recognition and refuses incomplete or colliding mappings. It
returns code-owned SQL plus bound parameters and content-free outcome/fingerprint
metadata; it implements no matching engine or relevance scoring.

Conservative parser boundary: only alphabetic ASCII words separated by whitespace
are expanded. Punctuation, digits, non-ASCII text and operator-like input keep the
complete original PostgreSQL plain-text query. This avoids silently introducing
a conflicting parser for compounds, Unicode or raw query syntax. This is a
whole-query fallback, not an input rejection. Unknown alphabetic terms remain
independent AND groups; stop words normalize to empty and add no AND constraint.

The entire original plain query is an additional OR branch, preserving all
previous lexical matches, including nonadjacent original phrase words. Added
multiword alternatives use `phraseto_tsquery`; they cannot match one word alone.
Budgets count alternative occurrences after deduplication within each group;
inflected original spellings also count. Complete original-query fallback applies
if any budget would be exceeded. No runtime query text or normalization is logged.

`browse_statement` accepts the owned compiled expression; `read_browse_page`
exposes `expanded_search=False` solely as an explicit native-test opt-in. The
production `PostgresListingsStore` never enables it. All original availability/
filter predicates, stable sorts, offset and lookahead remain outside and around
the same text predicate. No public mode, environment flag, UI change or migration
activates expansion. Incomplete/malformed configuration fails rather than
pretending expanded retrieval succeeded.

`test_lexical_expansion.py` scripts normalization values only to test planning,
SQL binding, bounds and failure behavior; these checks prove no English stemming
or retrieval. The existing disposable database suite now calls
`exercise_expanded_text`: actual vocabulary normalization, vehicle/cycle/book
directionality, phrase/unknown/ambiguous matching, description edits, exclusion of
hidden rows, all page sizes with filters and a GIN-eligibility diagnostic. These
checks subsequently passed in the native PostgreSQL 18.6 checkpoint; public
activation is still pending human verification and its integration step.
Use the existing registered `uv run --locked python scripts/check_database.py
--listings-store` on a supported prepared environment. A forced index-eligibility
plan is not a latency or natural-planner-choice result. No native pass is claimed.

## Native query verification follow-up

The [native checkpoint](../evaluation/domain/se-01/native-postgres/result.json)
now verifies real English normalization/expansion, directional vehicle/cycle and
book/textbook matching, phrases, ambiguity/unknown cases, updates, visibility,
filters and all page sizes. GIN eligibility is checked against the compiled text
predicate; the full browse query may correctly choose recency for a broad set.
Public routes retain plain matching until the separate activation increment.

## Known-vocabulary typo follow-up

Mohit selected bounded typo alternatives after calibration. Exact normalized
terms and the artifact's ownership/taxonomy/literal rules retain precedence.
The [versioned spelling policy](search-typo-tolerance.md) adds unique near-known
concepts without changing this artifact/version, keeps complete original matches
and independent AND groups, and bounds work/corrections. Ambiguous/short cases
stay literal; near real words can add an unintended alternative. Native checks
are source-bound separately, and public expansion/typo activation remains off.
