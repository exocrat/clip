# Known-vocabulary typo alternatives — version1

**Origin:** SE-01 Step4 hybrid amendment; Mohit verified vocabulary-only typo
scope after development calibration. This is prepared/private behavior. The
ordinary public browse store still does not enable expansion or typo alternatives.
No new public fields, packages, database extensions, migrations or model changes.

## Scope and ordered behavior

`typo_tolerance.py` defines `known-vocabulary-typos-v1`, deterministic bounded
spelling operations and content-free query budgets. `lexical_expansion.py` calls
it only after every possible exact PostgreSQL-normalized phrase failed at the
current position. All current exact/inflected matches therefore take precedence.

1. Preserve the existing ASCII-word/whitespace expansion boundary. Punctuation,
   digits and non-ASCII queries retain the complete original plain-text path.
   Normal browse validation still trims and limits queries to120code points.
2. Prefer longest exact normalized phrases. If none match, compare same-width
   canonical terms/aliases from the reviewed vocabulary, longest phrase first.
   PostgreSQL-normalized equivalent words cost zero; Python supplies no stemmer.
3. Correct at most one changed word in a phrase. Require input length>=5letters,
   target length>=4, matching initial letter and <=32characters per compared word.
   Permit one insertion/deletion/substitution/adjacent swap, or up to two edits
   when both words have>=7letters. A swap counts once and overlapping repeated
   transpositions are not generalized. `bycicle` needs two substitutions and
   `bicyle` needs one insertion. Initial-letter mistakes are deliberately outside
   this conservative rule.
4. Require a unique nearest **concept owner**. Equidistant aliases of the same
   owner agree; equal best owners are ambiguous and add nothing. Thus `tablex`
   cannot choose table versus tablet. Literal-only names remain non-targets;
   `notbook computer` can identify the explicitly disambiguated laptop phrase,
   while notebook alone never becomes laptop. A shorter fuzzy prefix is not tried
   after an ambiguous longer fuzzy candidate. Existing exact parsing remains.
5. Add the concept/aliases and existing direct narrower terms using the same
   bounded compiler. No reverse/recursive taxonomy or arbitrary listing/brand
   dictionary is introduced. Retain AND between independent concepts and phrase
   semantics for added multiword alternatives. Keep the full original query ORed
   in so original/nonadjacent matches are preserved, not silently rewritten.
6. At most2corrected groups and512candidate-phrase comparisons per query, with
   the existing12group/16per-group/48total alternative limits. Any overflow falls
   back to the complete original query, never a partially corrected prefix.
   Fixed outcomes are `typo_expanded` or `typo_budget`; no source text is logged.

`edit_cost` uses bounded dynamic-programming rows. `find_typo` selects owners and
consumes a `TypoBudget` scoped to that query; no mutable global cache/dictionary or
additional SQL lookup is added. Existing bound English-normalization SQL supplies
all words; existing parameterized tsquery expressions remain GIN-eligible. There
is no listing scan to build a spelling dictionary and no query-derived SQL code.
Record this policy version, compiler source and vocabulary fingerprint alongside
future final ranking/evaluation configuration. Old calibration evidence remains
bound to its earlier compiler source and is not silently relabeled as typo-tested.

## Examples and limits

| Input | Prepared behavior |
|---|---|
| bicyle / bycicle | Bicycle/cycle alternatives, with original input retained |
| vehicel | Vehicle plus its existing direct narrower concepts |
| red mobile phnoe | Red required; phone aliases may match |
| washing machnie | Washing-machine concept; not washing-room alone |
| notbook computer | Laptop aliases; not a paper notebook |
| boook | Book plus existing narrower textbook relation |
| tables | Exact English-normalized table; no fuzzy tablet alternative |
| tablex | Tied table/tablet owners; original only |
| fone / deks / carx | Short input; original only |
| bicyle boook phnoe | Third correction exceeds budget; complete original fallback |

This recognizes near spellings of known targets, not whether a query is actually
misspelled. `chain` is one change from chair: original chain matches remain, and
chair may be an extra match. Unknown real words can collide with the small
vocabulary. New native fixtures deliberately retain this case instead of claiming
perfect false-positive rejection. First-letter, short-word, multiple-error phrase,
Unicode and unfamiliar brand/listing-word corrections are not promised.
Semantic tolerance of misspellings is still unmeasured and is not a substitute
for these deterministic rules. The semantic query text is not rewritten here.

## Checks, activation and remaining gates

`test_typo_tolerance.py` checks edit types/limits, unique/ambiguous owners, exact
priority/direction, original/AND/phrase preservation, budgets and the real-word
collision. `test_browse_postgres.py` exercises actual English normalization on
authoritative rollback-only fixtures, including table/tablet/chain/chair controls,
original misspelled source and nonadjacent phrase matches, visibility, price/
negotiability filters, UUID-stable pages at20/50/100 and GIN eligibility.
Existing expansion/vocabulary tests remain regression evidence.

The native/unit/source receipt is in Git history; see the
[evaluation retrieval guidance](../evaluation/README.md). The first native run
found a test-fixture reset omission: selective price/negotiable
checks correctly hid two rows from the later all-row pagination check. Resetting
those fields before that matrix fixed the fixture; no product filtering or test
expectation was weakened. Failed and subsequent successful runs remain retained.

The native store's `expanded_search=True` is still owned test-only invocation;
public `PostgresListingsStore` never supplies it. Public activation/relevance/
hybrid coverage/filter/scoring/pagination contracts, real upstream integration,
full corpus/20+human-reviewed labels, Linux/resources, full CI/secret scan and
independent peer/exact revision review remain. No FR/NFR/readiness is accepted.
See [commands](../environment/commands.md) and [DEC-13](../decisions/hybrid-listing-search.md).
