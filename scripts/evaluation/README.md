# Search label bindings and evaluator tooling — SE-01 Step 9

`reference_labels.py` now validates the actual NEXT-06 corpus against retained
load/vector/rebuild evidence and explicitly accepted source/contract revisions.
It writes or revalidates `data/evaluation/query-labels.json`:22unchanged human
judgments, exact fingerprint and the recorded acceptance time chosen by Mohit.
No network, provider, model inference or scoring occurs. See the
[Step5 result](../../docs/evaluation/domain/next-06/transfer/step-05-final-labels-result.json).

`search.py` remains the strict format validator and Success@5 arithmetic core.
Its own CLI still exposes only draft validation/synthetic checks. Reviewed data
requires the independently constructed non-preview binding from the adapter;
metadata text alone never establishes human acceptance or DATA-READY.

- `validate_labels` checks exact fields, canonical IDs, revisions, UTC review
  time, inclusion decisions, query contexts and dataset/eligibility references.
  Draft judgments remain null. Reviewed input requires at least 20 included cases
  and a separately verified non-preview `DatasetBinding`; metadata text alone
  never proves human review. The binding is an adapter boundary, not a
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

Current actual label command (existing project environment, retained payload and
original/restored photos required):

```sh
.venv/bin/python -m scripts.evaluation.reference_labels validate --image-root /absolute/path/to/clip-dataset-images
```

The initial explicit `write` action refuses existing outputs; do not regenerate
judgments or delete the canonical file to bypass it. Validation compares every
judgment and metadata field with the accepted inputs, checks committed source
blobs, rebuild/cloud hashes, dates and all800eligible IDs. The historic generated
manifest remains unmodified and truthfully says generated-unloaded; the separate
actual label-binding manifest joins it to retained real execution receipts.

Still pending: Step6 formal freeze/readiness/independent acceptance and later
SE-01 actual offline NFR-04 scoring. No score, full readiness milestone or fresh
cloud state is inferred from a valid label file. The original draft/template and
historical accepted judgment records remain unchanged.


## Step10 isolated load-runner preparation

[The pinned local k6 runner](k6/README.md) now implements capped loopback arrival
cohorts, exact HTTP counting, response/oracle validation, drops/failures/timeouts,
separate warm-up, R7percentiles and safe local raw artifacts. Failure fixtures and
an actual native SQL/model pilot pass; no real NFR or SE-CORE acceptance is
available. The future full-rate profiles/manifests remain unapproved and cannot
execute through this local-only entry point. Real auth/final data/deployment and
remaining task gates are retained; no final labels are generated.

## NEXT-06 frozen content manifest

`reference_release.py validate` rechecks both actual generated record sets, all52
archive members, the real1000object/SQLledger, physical pinned model files,
reviewed labels/source and real reset/cloud-native hash evidence. No extraction,
network, inference, SQL or scoring occurs. `freeze` exclusively creates the fixed
manifest once; a repeat refuses without changing it.

The [frozen content manifest](../../docs/evaluation/domain/next-06/frozen-dataset.json)
now exists; formal human/current-headCI/independent acceptance remains separate.
The immutable Step5label binding's earlier acceptance flags remain historical;
follow the release and later explicitly recorded acceptance rather than editing
old manifests. Run commands/limitations and reviewer handoff are in the
[task-wide review](../../docs/evaluation/domain/next-06/task-wide-review.md).

# NFR-05 offline outcome preview

`nfr05_report.py` reads a local JSON object containing only `samples`: up to 60
records with unique integer `index` values 0–59, `outcome` (`displayed`,
`failed`, or `undisplayed`), `submitted_ns`, and `displayed_ns`. Times are
nonnegative integer nanoseconds from the same host monotonic clock; displayed
records require both times, other outcomes require `displayed_ns: null`, and a
failure before submission may also use `submitted_ns: null`. Do not include
message content, ciphertext, account identifiers or credentials. For example:

```json
{"samples":[{"index":0,"outcome":"displayed","submitted_ns":0,"displayed_ns":5000000000}]}
```

This incomplete example is refused as a passing preview because 59 outcomes are
missing. Run `python -m scripts.evaluation.nfr05_report observations.json` to
print aggregate counts. At least 57 of all 60 must be displayed within five
seconds, and all outcomes must be present. `threshold_met_if_valid` is only
arithmetic; clock, browser-display events, background load, privacy and all
other NFR-05 gates still need real evidence and review. The tool cannot run a
workload or assert an NFR pass.

`nfr05_events.collect` is an in-memory adapter for simulated events with only
`index`, `event` and `time_ns`. It accepts a submission followed by an explicit
displayed, failed or undisplayed outcome; a failure may occur before submission.
An undisplayed outcome cannot be recorded before the five-second deadline and
is final, so the eventual real observer must wait until its observation window
ends before emitting it. A submission without a final outcome remains missing.
Server receipt is not display. The adapter checks ordering and rejects extra
fields, but does not observe a browser or verify events or timestamps.
