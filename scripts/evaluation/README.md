# Search evaluator preparation — SE-01 Step 9

`search.py` validates the existing [label format](../../data/formats/query-labels.md)
and prepares Success@5 arithmetic. It makes no network/database calls and writes
no files. No final relevance evaluation or readiness acceptance is available.

- `validate_labels` checks exact fields, canonical IDs, revisions, UTC review
  time, inclusion decisions, query contexts and dataset/eligibility references.
  Draft judgments remain null. Reviewed input requires at least 20 included cases
  and a separately verified non-preview `DatasetBinding`; metadata text alone
  never proves human review. The binding is a future adapter boundary, not a
  manifest validator or a substitute for count/FK/schema/index/data checks.
- `safe_reference` confines label/evidence references to their repository trees
  and rejects traversal and symlinks. It never executes referenced content.
- `score_preview` calculates hits among the first five ordered IDs. Included
  empty-relevance, missing, failed and invalid-result cases remain in the
  denominator. Exclusions require an explicit reason. Duplicate/unknown IDs or
  oversized result pages are visible failures. Every result says `preview_only`,
  `nfr04_accepted: false`, and `human_review_verified: false`, including 100% hits.
- `self_check` supplies synthetic arithmetic cases only. It does not implement
  retrieval, ranking, corpus generation or human relevance judgments.
- `main` exposes only template validation and the arithmetic self-check, with
  fixed failure diagnostics and code/label fingerprints. CLI cannot construct
  a final binding or run final scoring.

From the repository root, with the locked project environment:

```sh
uv run --locked python -m scripts.evaluation.search validate-labels --labels data/evaluation/query-labels.template.json
uv run --locked python -m scripts.evaluation.search self-check
uv run --locked python -m pytest tests/evaluation -q
```

The first command reports format validity and `scoring_allowed: false`. The
second reports four included synthetic cases, one hit (0.25), one explicit
exclusion and one timeout. Neither is an actual search result or human label set.
Tests construct their own explicitly synthetic adapter bindings in temporary
folders; they never populate the canonical final labels.

Still pending: actual ID-READY/LI-CORE, real final corpus and integrity/index/
availability/image checks, retained final manifest, agreed representative-query
selection/default-context/inclusion policy, 20+ human-reviewed included queries,
and exact data/code/contract/label freeze. The real runner must verify those
inputs independently and use actual native retrieval before Step 11 NFR-04.
No final `data/evaluation/query-labels.json` is supplied by this preparation.


## Step10 isolated load-runner preparation

[The pinned local k6 runner](k6/README.md) now implements capped loopback arrival
cohorts, exact HTTP counting, response/oracle validation, drops/failures/timeouts,
separate warm-up, R7percentiles and safe local raw artifacts. Failure fixtures and
an actual native SQL/model pilot pass; no real NFR or SE-CORE acceptance is
available. The future full-rate profiles/manifests remain unapproved and cannot
execute through this local-only entry point. Real auth/final data/deployment and
remaining task gates are retained; no final labels are generated.
