# Hybrid search development calibration — provisional

SE-01 Step4 hybrid amendment calibration checkpoint. Mohit verified this scoped
plan after the private DB/helper bridge. This report proposes settings; it does
not freeze or activate them. The earlier public-contract, real-upstream, final
corpus/labels, Linux/resource, independent review and NFR gates remain.

## Method and provenance

Eight [synthetic listings and eleven development queries](../../data/evaluation/development/hybrid-search-v1.json)
are versioned separately from final evaluation labels. Relevant keys are
fixture-author intent, not accepted human judgments. There are ten positive
queries and one intended empty query. The same cases are compared under every
setting, including failures; none are removed after seeing scores.

`calibration.py` uses the existing real helper with the pinned model, complete
254-token/32-overlap title/description windows and full source coverage. It writes
only fresh session-temporary fixture tables on the guarded disposable database.
PostgreSQL constructs the same English title/description vector as the baseline,
executes `plainto_tsquery` and the actual `compile_expansion`, and computes title
and maximum-description cosine with the reviewed native scoring function over
all eight rows. No private listing/job source or final data is used. The native
test checks base-domain counts unchanged, temporary cleanup and preservation of
a pre-existing session-table sentinel on a name collision.

Analysis then compares a predeclared90-setting grid, without additional model
calls: title-only, max(title,max-description), and35/65 title/max-description;
thresholds0.25/0.35/0.45/0.55/0.65; tiered versus additive lexical boosts; and
semantic candidate caps none/3/5. Every original/expanded lexical candidate stays
in the union regardless of threshold/cap. Semantic caps apply to the whole corpus
before union/ranking, never per page. Stable UUID is the final tie-breaker.

Tiered orders original-term matches, expanded-only matches and semantic-only
matches, then semantic score. Additive comparison uses similarity+.25 for
original terms or+.10 for expanded-only, without guaranteed tier dominance.
These are explicit experimental rules, not production SQL or public API behavior.
The separate keyword baselines order by UUID solely for membership diagnostics;
they are not measurements of the public route's default recency ordering.

## Observed result

| Development path | Positive queries with intended item in top5 | Intended empty guitar query | Candidate precision | Candidate recall |
|---|---:|---|---:|---:|
| Literal keyword | 3/10 | Empty | 3/3 | 3/10 |
| Curated expansion | 6/10 | Empty | 6/7 | 6/10 |
|35/65 blend,0.35,tiered,no semantic cap | 9/10 | Empty | 9/11 | 9/10 |

The complete denominator is eleven queries. The proposed comparison has9hits
in those11cases; the empty-intent case has no possible relevant hit and is also
reported separately. These are development counts, **not NFR-04 Success@5**.
[All90comparisons and query outcomes](../evaluation/domain/se-01/calibration/analysis.json)
and [native score matrix](../evaluation/domain/se-01/calibration/matrix.json)
retain unwanted matches and misses.

Threshold0.25 admits a phone for the absent guitar. Threshold0.45 and above miss
`keep food cold`→fridge, leaving8/10positives. At0.35,max aggregation also admits
the room bundle for furniture; the blend removes that extra match. But the blend
fridge score is only0.3526915098, close to0.35: this tiny corpus does not establish
a robust general threshold. The two fusion choices and all three caps produced
the same returned order on this set. Their practical effects therefore remain
unmeasured; unit arithmetic demonstrates their distinct rules, not superiority.

The bicycle poster remains an unwanted expansion match for vehicle. Bicycle is
also an unwanted semantic addition to `bicycle poster`. Preserving keyword union
and adding semantic similarity cannot promise exact item intent or negation
understanding. The intended result is first for9/10positive queries here, but
that is not a general ordering guarantee.

## Known long-description failure

`watch stars at night` does not retrieve the telescope buried in903tokens of
mostly repeated filler. All four chunks are actually encoded/scored; no ending
was truncated. For that query the telescope's best-description score is negative;
max(title,description) reaches only about0.159. Literal `telescope` still finds it
through native full-text search, including the ending. Coverage is correct while
semantic relevance is inadequate in this controlled case. Lowering a global
threshold enough to rescue weak similarity would introduce unrelated results.

## Proposal requiring verification

1. Keep35/65 title/maximum-description blend with threshold0.35 as a **development
   reference**, not a frozen production choice. Require similarity>=threshold
   only for semantic additions; retain original/expanded keyword membership.
2. Prefer explicit original>expanded>semantic tiers, then score descending and
   UUID ascending for relevance. This is a predictable keyword preference,
   not an empirically demonstrated winner over additive weighting on this set.
3. Use no pre-pagination semantic candidate cap in the next correctness prototype.
   No cap was justified by this tiny set; later full-corpus plans/resources must
   establish feasibility. Public page limits remain separate and unchanged.
4. **Do not freeze/activate this model policy yet.** Investigate shorter/alternative
   overlapping chunks on a separately reviewed encoding version and broader
   development cases before deciding whether to revise the pipeline. Do not change
   the current model/config, reinterpret the failed label or tune final labels.

That follow-up is a preview and requires its own step understanding verification.
Changing chunking would require new pipeline identity, coverage/storage/runtime
validation and later reviewed rollout; no such change occurs in this checkpoint.
The public single-statement coverage/503 guard, filter-before-score/pagination,
mode/sort/generated-type/UI work and dispatch/bootstrap remain later gates.

## Reproduction and evidence limits

[Command registry](../environment/commands.md) records the explicit native flag
and analysis-only CLI. The fresh native runner performs migration/smoke/down/
reapply checks, then the calibration case. Bounds: one live helper,30model windows,
10minutes,512MiB sampled test-host/helper RSS,3s SQL statements/1s lock waits.
The model is already local; no download/install/global setting changes occur.
Safe output contains fixture IDs, flags, scores and aggregate metrics, never
vectors/customer queries. [Evidence manifest](../evaluation/domain/se-01/calibration/result.json)
binds code/data/model/vocabulary and exact retained runs. Host sampling is not
production cgroup/NFR evidence. The comparison analyzes measured native scores;
it is not a production hybrid read implementation or full-corpus benchmark.

## Subsequent human direction

Mohit accepts this particular telescope/stargazing miss as vague enough to remain
a limitation. It no longer requires a separate long-description investigation
before proceeding on his behalf. The current encoding remains unchanged; this
does not imply final human-label/NFR acceptance or scoring-policy freeze. He
instead selected the [vocabulary-only typo checkpoint](search-typo-tolerance.md).

## Verified implementation reference

Mohit subsequently verified the proposed35/65blend,0.35cutoff, explicit keyword
tiers/no semantic cap and controlled503 plan for the private SQL reader. That
reference is now versioned as hybrid-blend-v1 in the
[private read contract](hybrid-listing-read.md). Historical calibration flags remain
unmodified: they describe unreviewed development measurements at that earlier
source revision, not final labels/NFR acceptance. This later verification does
not activate a public API/UI or eliminate the recorded relevance limitations.
