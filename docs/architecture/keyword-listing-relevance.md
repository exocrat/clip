# Private keyword listing relevance — keyword-relevance-v1

**Origin:** SE-01 public mode/both-mode relevance proposal, verified by Mohit.
**State:** Private option implemented and verified. Public API now maps
`sort=relevance` to this flag in Keyword mode; UI controls remain pending.
Mohit owns search behavior. Shared-interface compatibility and independent review
remain normal PR responsibilities, not a separate permission gate for this work.

## Interface and ordering

`browse_store.py` adds `keyword_relevance=False` to `browse_statement` and
`read_browse_page`. The default preserves prior SQL/recency/price behavior. The
flag is a trusted private argument, not a registered HTTP field. True requires
nonblank normalized text; blank is422. Invalid flag types or a compiled plan
bound to another query/vocabulary are refused. Caller eligibility remains the
owning service's upstream precondition.

The private reader automatically compiles vocabulary/typo expansion for relevance,
without requiring the separate expanded_search flag. Exact original English
matches remain in the union. After current visibility and all supplied filters:

1. Original-query matches precede expanded/typo-only matches.
2. Original matches use `ts_rank_cd(search_vector,original_query,0)` descending;
   expanded-only matches use the same function on the compiled expanded query.
   The existing stored positional vector/default weights are unchanged.
3. Ascending listing UUID resolves ties across the whole matching set, before
   offset and size+1. No rank cutoff, candidate cap or per-page reranking.

Both the full query and alternatives remain bound parameters in membership and
ORDER BY. Repeated rank expressions do not widen the compiler's alternative
budget. The original query/vocabulary binding is checked before using the private
rank. No rank/boolean/tier metadata is added to the existing public summary.
Recency and price sorts retain their prior order when relevance is false.
Zero-rank matches are not intentionally discarded: membership contains no rank
predicate. No stripped/corrupt generated-vector fixture is introduced to fake
that condition. PostgreSQL remains the actual matching/ranking implementation.

The native function's documented positional/proximity behavior is described in
[PostgreSQL18 text ranking](https://www.postgresql.org/docs/18/textsearch-controls.html#TEXTSEARCH-RANKING).
These internal keyword ranks are not semantic cosine and are not comparable
across search modes/queries. Hybrid keeps its existing separate selected rule.

## Model independence and scope

The keyword path imports no model client, reads no embedding pipeline/generation/
chunk data and checks no helper/artifact readiness. It uses existing PostgreSQL,
owned catalogue/source/image data and the local static vocabulary only. Real
Identity/database availability is still required. No new package, extension,
index, migration, worker/startup switch or model call is introduced.

This internal option does not register public `sort=relevance` or search_mode.
The [public proposal](../../contracts/search-mode-proposal.md) remains the target
for the next verified source/generation/dispatch stage. Keyword will use this
native rule; Hybrid relevance remains model-based. Mode controls and public
error/switch behavior still need their separate implementation/browser checks.

## Actual checks and limits

`test_keyword_relevance.py` checks bound SQL, matching/filter preservation,
original/expanded rank selection, no rank in projection/WHERE, defaults, query/
vocabulary bindings, private-flag/blank guards, unsafe text parameters and no
semantic-client construction. Its scripted normalization/driver receipts do not
claim PostgreSQL scoring or relevance quality.

`test_browse_postgres.py::exercise_keyword_relevance` uses the existing guarded
rollback-only65-visible/5-hidden fixture set and actual generated vectors:

- Original single occurrence outranks expanded-only25occurrences despite the
  latter's independently checked higher raw native rank. Within the original
  tier, repeated matching words affect native order.
- A misspelled original source remains ahead of corrected alternatives. Adjacent
  red/bicycle ranks above the same words separated by12filler words.
- Match membership agrees with the existing expanded query; hidden sources stay
  excluded. Category/condition/price/negotiability, unknown catalogue422, blank
  relevance422, stopword-only/unmatched/late empty pages are checked.
- Equal-rank65-row pages use UUID ascending, with no duplicate/missing rows at
  20/50/100and size+1has_next behavior.
- In a nested rollback scope, the default pipeline is building with no serving
  space and current fixture jobs marked failed. Keyword still returns the same
 65rows. No inference/model artifact is used; failed metadata is test setup only.

[Source-bound native/unit evidence](../evaluation/domain/se-01/keyword-relevance/result.json)
and [commands](../environment/commands.md). This is not final usefulness, full-
corpus latency/concurrency, real Identity integration, browser or FR/NFR/readiness
acceptance. No public website mode control is activated by these private checks.
