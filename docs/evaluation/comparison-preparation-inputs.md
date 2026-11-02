# Comparison preparation: ordered cases and telemetry metadata

These are offline preparation tools for EXP-02 Steps 4, 6 and 7. They do not
contact a service, authorize a run or establish DATA-READY. Actual owner review,
deployed parity, generator capacity and action approvals remain separate gates.

## Ordered Hybrid references

Start with `data/evaluation/workloads/ecs-lambda-ordered-reference.template.json`.
Use a separate copy to supply, for each of its three exact query IDs and texts,
the independently reviewed first-page listing IDs **in their reviewed order** and
the reviewed `has_next` boolean. The page size is 20; if `has_next` is true,
provide 20 IDs. The reference points to an existing non-secret, relative review
record. Do not add raw responses, credentials or real personal data. A relevance
label set is not an ordered result and must not be used to invent one.
Set `search_implementation_revision` to the full 40-character source commit
used when those exact ordered results were independently reviewed. Separately
select the intended experiment search source revision and supply it to the
command; the values must match. The latest merged main at the reconciliation
checkpoint is `1f110650d056f800e0179aec06f9b8747ad377ef`, not a verified
production deployment or evidence that any results were reviewed against it.
Later source changes require a fresh selection and reference review.

From the repository root, prepare a new corpus (the output path must not exist):

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_ordered_results path/to/reviewed-reference.json --search-revision FULL_REVIEWED_SEARCH_COMMIT --output path/to/new-case-corpus.json
```

The command checks the archive hash and its A/B synthetic records, dataset
fingerprint and schema, query IDs/text, search-contract revision, model revision,
and equality of the reference and intended search implementation revisions,
listing eligibility, duplicate IDs and page shape. It reconstructs public fields
from the frozen archive and preserves supplied order. It records a canonical JSON
SHA-256 of the supplied reference and its review-record pointer. It does not
verify that pointer, review the ranking, validate a deployed dataset, or change
the frozen manifest's DATA-READY value. Missing/invalid input or an existing
output exits 2 without starting a workload. The template is deliberately
incomplete and is rejected until filled with reviewed references.

The resulting corpus has the same `cases` entries used by the existing local
schedule. A future run profile also needs the separately reviewed sequence start,
generator capacity and other run inputs. The existing k6 load script remains
loopback-only; preparing a corpus grants no permission to invoke it. Revalidate
the frozen availability window and the current threshold, source, schema,
model and target before any future use.

## Planned comparison binding check

The existing run-capture manifest includes actual end times, telemetry and
costs, so it cannot be completed before a run. For offline input consistency,
make a separate copy of
`data/evaluation/workloads/ecs-lambda-binding-plan.template.json` and fill:

- `application_revision`: the full 40-character source commit intended for the
  application and used in the ordered-reference review.
- `dataset_fingerprint`: the full `sha256:` logical fingerprint.
- `case_corpus_sha256`: the 64-character SHA-256 of the exact case-corpus file
  bytes, without a prefix.

Then run the offline check with the complete prepared comparison corpus and its
ordered-reference input:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_binding_preflight path/to/binding-plan.json path/to/corpus.json path/to/ordered-reference.json
```

It checks the plan values and actual corpus file hash, rebuilds the full corpus
from the verified archive and ordered reference, and compares the complete JSON
values with type distinctions, so a boolean cannot replace a number. The
reference's search implementation revision must equal the planned
application revision. This exact-match rule is conservative: if a later app
commit preserves the same search implementation, owner-reviewed equivalence or
a newly bound reference is needed; the tool does not infer it. If a completed
run-capture manifest later exists, pass `--captured-manifest path/to/manifest.json`
to validate its schema and compare its application revision, dataset fingerprint
and corpus hash. A template is not a captured manifest.

The check prints no cases or reference content. Exit 0 establishes only local
input consistency, not human review, deployment identity, dataset parity,
complete run safety or approval. It is not yet wired into a real-target runner;
that future runner must enforce these and all other prerequisites before
credentials or requests. The NFR case-draft bundle is a separate non-executable
artifact and is not accepted as an EXP-02 comparison corpus by this check.

## Planned A/B run order

Before any future comparison, make a separate copy of the version-2
`data/evaluation/workloads/ecs-lambda-paired-plan.template.json`. Fill its shared
dataset/index/database-settings, schedule, case-corpus and load-script
fingerprints, plus the generator version. Choose and record one rotation seed
from 0 through 9; this is separate from the dataset seed. The approved
`increment-one-per-pair-v1` rule starts at that number and advances by one for
each of the nine pairs in cycle/condition order, wrapping from 9 to 0. Generate
the starts offline with the chosen seed, for example:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_rotation --seed 3
```

This example produces `3, 4, 5, 6, 7, 8, 9, 0, 1`; it does not select the real
seed or authorize a run. Enter the generated `sequence_start` for each pair and
distinct A and B run IDs into the copy. The plan checker rejects a missing seed,
an altered rule or any start inconsistent with the seed. A and B share each
pair's start. The editable version-3 run-manifest template also records the
rotation rule, seed and start separately from the dataset seed. A completed
capture must match both the rule and its cycle/condition; the paired check also
requires the seed to match the plan. No frozen dataset or acceptance manifest is
changed by preparing these copies. The paired-plan validator accepts version 2;
the run-manifest validator accepts version 3 and rejects earlier record shapes.

Check the local plan with:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_pair_plan path/to/paired-plan.json
```

The checker requires three cycles in A/B, B/A, A/B configuration order, with
low, normal and burst pairs in each cycle. It requires nine pairs, eighteen
unique planned run IDs and one set of nonempty shared inputs. Exit 0 means only
that the declared plan has this shape and order when no captured manifests are
supplied. It does not prove deployed data/configuration parity; a future runner
must enforce plan bindings before any session or request. Its output always
sets `measurement_authorized` to false. This check does not encode the
experiment design's proposed 300 concurrent-request figure, which the user has
clarified is non-binding.

After all runs have captured manifests, run the same command with
`--captured-manifest PATH` repeated once for each of the 18 manifest files.

The checker first applies the existing per-run manifest validator, then matches
all 18 run IDs, configuration/condition/cycle, case sequence start, and shared
dataset/index/database and workload fingerprints to the plan. It requires all
six captures in a cycle to record the same generated-profile hash, while
allowing different hashes between cycles. It also checks
the recorded UTC start and end times: each cycle must list low, normal and
burst for the first configuration, followed by low, normal and burst for the
second, with the approved A/B, B/A, A/B cycle order. Recorded runs cannot
overlap, although one may start exactly when the preceding run ends. File
argument order does not matter. It rejects an incomplete, duplicate, unexpected,
mismatched, out-of-order or overlapping manifest set.

These checks verify recorded fields only. They do not prove the timestamps are
accurate or comparable across clocks, establish the deployed service used the
settings, or hash the raw results. Investigate clock discrepancies rather than
changing timestamps to make a check pass. Use the separate artifact verifier
for the manifest's evidence files. Both checks remain offline and non-authorizing.

## Offline preparation for one planned run

The preparation stage combines the existing corpus, plan and profile checks for
one selected run. It reads local inputs only and cannot obtain a session, launch
k6 or send requests. Run it with file paths and values from the reviewed plan:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_offline_prepare \
  --binding-plan binding.json --corpus corpus.json \
  --ordered-reference ordered.json --paired-plan paired.json \
  --workload-profile profile.json --cycle 1 \
  --run-id PLANNED_RUN_ID --expected-profile-sha256 EXPECTED_SHA256
```

Omitting options lists their names as missing. An unreadable, malformed or
non-regular file is listed as invalid; the final path component cannot be a
symlink. Consistency failures or a run ID outside the selected cycle are
reported as `input_bindings_or_planned_run` without printing supplied contents.
The process exits 2 for missing or invalid inputs and 0 only when those local
checks pass. It always reports `measurement_authorized: false` and lists other
review, deployment, timing, capacity, authentication, telemetry, cost and run
approval gates. Success does not prove human review, parity, capacity, execution
of the checked bytes, or run readiness. It is not yet integrated into a
real-target runner. The expected profile hash must be sourced from the reviewed
plan; these checks do not prevent file changes after reading.

## Combined pre-request input check

Before a future comparison runner requests a session or sends a request, it must
check that the ordered-reference binding and the planned A/B runs agree. The
offline combined checker reuses the two validators above and cross-checks the
dataset fingerprint and exact case-corpus file hash between their plans:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_run_preflight \
  path/to/binding-plan.json \
  path/to/complete-case-corpus.json \
  path/to/reviewed-ordered-reference.json \
  path/to/complete-paired-plan.json
```

The binding and paired plans must both be complete; blank templates fail. The
command checks the corpus against the frozen archive and supplied ordered
reference, checks its source and dataset bindings, validates all nine pairs and
18 run IDs, and requires the paired plan's dataset and corpus fingerprints to
match the binding plan. It prints aggregate status only and always reports
`measurement_authorized: false`. It does not ask for credentials, send requests,
verify human review or deployed identity, validate target/auth/timing/caps, or
attest database equivalence. The future real-target runner is not connected yet
and must enforce this check plus all remaining reviewed run gates before any
session or request.

For an additional check of a local profile, append `--workload-profile
path/to/profile.json --cycle 1 --expected-profile-sha256 EXPECTED_SHA256` (use
cycle 2 or 3 as appropriate). Supply the lowercase SHA-256 from the separately
reviewed plan. All three options are required together. The checker compares
exact file bytes to that hash, checks the cases and starts against the plan, and
requires a five-second timeout and positive, JavaScript-representable integer
worker settings with pre-allocated workers no greater than the maximum. This
validates the settings' shape; it does not select or approve an operational cap.

When omitted, `workload_profile_checked` and `profile_hash_checked` are false.
The builder's internal check occurs before a file exists and likewise cannot
check its hash. A future runner must require both checks before credentials or
requests. Matching a supplied hash does not prove review, actual profile use,
or that the file cannot change after this check; real-run gates still apply.
The rotation rule is approved; the actual seed remains an open pre-run input.

## Generate a cycle workload profile

Once the four preflight inputs are complete, the offline builder can create one
profile for a cycle from the bound cases and the paired plan. Replace the worker
placeholders with the independently reviewed values and choose a new output path:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_profile_builder \
  path/to/binding-plan.json path/to/complete-case-corpus.json \
  path/to/reviewed-ordered-reference.json path/to/complete-paired-plan.json \
  --cycle 1 --pre-allocated-vus PREALLOCATED_VUS --max-vus MAX_VUS \
  --output path/to/new-cycle-1-profile.json
```

Repeat for cycles 2 and 3 with distinct new output paths. Reuse each cycle's
profile for its A and B configurations. The builder checks the complete bound
corpus, reviewed-reference envelope and plan before creating the file; it
derives the three starts from that cycle, uses the approved five-second timeout,
and refuses existing output files. With the same input bytes and capacity values,
it produces identical bytes. Its output reports a SHA-256 of the generated file
and `measurement_authorized: false`; it never requests a session or sends traffic.

The worker values must be positive whole numbers representable by JavaScript,
with pre-allocated workers no greater than the maximum. Those checks do not
approve the values or prove the generator can sustain the workload. `maxVUs`
is per k6 scenario, so both burst scenarios can overlap during the transition;
the independently reviewed generator plan must account for their combined use.
No numeric 300-request ceiling is imposed. The per-run manifest's
`workload.profile_sha256` identifies the checked-in schedule. Its separate
`execution_profile_reference` and `execution_profile_sha256` record a sanitized
copy of the generated profile under the local evidence root and its exact file
hash. The future real-target runner must still enforce the reviewed profile and
all other gates before credentials or requests. These recorded fields and file
checks do not prove the runner actually used that profile.

## NFR browse and Hybrid case drafts

The offline generator selects five browse and three Hybrid cases from the same
archive-checked corpus, preserving full expected fields, page data, dataset
binding and review limitations. It never emits a runnable profile:

```sh
.venv/bin/python -m scripts.evaluation.k6.prepare_nfr_cases --output path/to/new-nfr-cases.json
node scripts/evaluation/k6/nfr_cases_check.mjs nfr-01 path/to/new-nfr-cases.json
node scripts/evaluation/k6/nfr_cases_check.mjs nfr-02 path/to/new-nfr-cases.json
```

Output must be a new path. NFR-01 checks first/later pages, category coverage,
status, expected response shape, fields, availability and filters. NFR-02
checks three query classes and explicit Hybrid requests, but fails on the draft's
missing ordered responses. When independently reviewed ordered references exist,
provide `--ordered-reference path/to/reviewed-reference.json --search-revision
FULL_REVIEWED_SEARCH_COMMIT` to the generator; it invokes the existing binder
and refuses mismatched inputs. No substitute rankings are generated. The checker
uses the current clock for availability; a valid old fixture is not evidence of
current dataset availability.

These case-shape checks do not independently establish archive provenance for
an arbitrary supplied JSON bundle, human review, dataset parity, model/source
deployment, rate, timeout, a complete NFR profile or any action approval. The
generator verifies the frozen source archive, but even its valid output requires
the SE-01 owner to review the actual cases. Both commands are offline and report
`execution_permitted: false`; a future runner must validate the complete corpus
and manifest before obtaining credentials or sending requests.

## Offline per-run cost arithmetic

`comparison_cost_preview.py` calculates one run's pre-credit USD cost per
1,000 correct operations from operator-supplied values. Provide a local JSON
object with exactly these fields (the numbers below are synthetic examples):

```json
{"run_id":"synthetic-A-1","condition":"normal","cost_usd":"0.25","cost_basis":"estimated","correct_operations":500}
```

`condition` is `low`, `normal` or `burst`; `cost_basis` is `estimated` or
`billing`. Enter `cost_usd` as a nonnegative decimal string, allocated to the
measured interval before credits. The correct-operation count must come from the
matching run's independently checked results. Use a separately reviewed common
allocation and price basis for A and B, including retained ECS capacity and
applicable shared services. Record pricing, interval, billing delay, sources and
assumptions with the run evidence; the calculator does not establish any of them.

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_cost_preview path/to/cost-input.json --output path/to/new-cost-report.json
```

Before using a cost calculation, cross-check the input against a completed
captured manifest and its derived report:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_cost_binding path/to/cost-input.json path/to/captured-manifest.json path/to/derived-report.json
```

The offline check requires matching run ID and condition, verifies the report's
exact bytes against the manifest's recorded report hash, and compares the
condition's measured correct count. The report itself has no run ID; its hash
provides the recorded association, not independent proof of provenance. This
does not check whether the cost amount is for the measured interval: the manifest
cost interval can cover the whole run. Cost allocation, report accuracy and run
validity still require independent review. Templates and missing or mismatched
inputs fail; the checker does not request credentials or start a workload.

The tool writes a new file and refuses to overwrite an existing input or report.
It reports the entered total, correct count and decimal cost per 1,000; with no
correct operations, the unit cost is unavailable. A `billing` label is an input
claim, not independently verified billing. Calculate each workload separately;
normal-run values are used for the approved median score only after validity and
other scoring gates are met. The tool does not calculate total experiment costs,
verify whole-system allocation or establish a result, budget, or NFR pass.

## Three-run cost median preview

For one configuration and one condition, supply the cost input, captured
manifest and derived report for each of the three repetitions:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_cost_median \
  --run cost1.json manifest1.json report1.json \
  --run cost2.json manifest2.json report2.json \
  --run cost3.json manifest3.json report3.json --output new-median.json
```

The offline tool performs the binding check for each set, requires distinct
run IDs and repetitions 1, 2 and 3, and refuses mixed configurations or
conditions. It computes each declared per-run cost per 1,000 correct operations
and takes the middle value; it does not divide pooled cost by pooled operations.
A zero correct count makes the median unavailable. Only the normal condition
is a candidate input for the weighted cost score; the tool does not calculate
that score. It does not verify cost allocation, common price basis, actual run
validity, report provenance or eligibility. Those gates remain for human review.
The output is a new file and existing files are not overwritten.

## Timing, saturation and telemetry metadata

`data/evaluation/workloads/ecs-lambda-telemetry.template.json` specifies a
separate telemetry metadata record. It requires a run ID, clock method and its
evidence reference; peak generator CPU, RSS and virtual users; the operator's
approved limits for each; dropped iterations; and ECS, Lambda, PostgreSQL and
generator artifact references, SHA-256 values and UTC coverage windows. CPU
percent is normalized to the generator's total allocated CPU capacity (0–100).
Use the exact values and units in the approved run plan; this tool chooses no
thresholds. References are relative, non-secret paths. Use an explicit artifact
documenting non-applicability where the existing manifest requires a component
reference for a configuration that does not use that component.

Validate a completed record against its completed captured manifest:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_telemetry path/to/captured-manifest.json path/to/telemetry-metadata.json
```

It rejects missing/unknown fields, mismatched run or artifact references/hashes,
incomplete capture windows, unsafe references and malformed limits. Its result
shows whether declared peaks exceed the supplied limits, whether VU headroom
was observed, whether iterations dropped, and whether monotonic timing was
declared verified. It does **not** open telemetry artifacts, recompute their
hashes, verify that the limits were approved, independently prove monotonic
timing, assess infrastructure health, or authorize a run. A valid metadata
record alone is not evidence that the generator was unsaturated or that an NFR
passed. Both templates are intentionally invalid until real run inputs exist.

### Checking local telemetry and cost files

After a completed run, the separate offline artifact verifier checks that the
generated profile, four telemetry references, cost source, raw k6 output and
derived report in a captured manifest point to local files with the recorded
SHA-256 values:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_artifacts path/to/captured-manifest.json path/to/telemetry-metadata.json --evidence-root path/to/local-evidence-directory
```

It reuses manifest and telemetry metadata validation, requires telemetry and
cost windows to cover the run, and hashes all eight files under the selected
directory. Raw output and derived report must be distinct files, including when
two different paths are hard links to the same file. References must be relative
and cannot contain traversal or symlink components; the evidence root itself
cannot be a symlink. Each artifact is limited to 100 MB and each metadata input
to 2 MB. Missing, changed, non-regular, oversized or mismatched files fail.
Exit 0 means those checks passed; exit 2 means they failed. The files are read
for hashing and never modified or printed. A matching raw-output digest checks
it against the digest recorded in this manifest; it cannot prove that no one
changed the bytes before that digest was recorded.

Matching hashes establish only that local bytes match recorded digests. They do
not prove that a file came from the claimed provider, that its content is safe or
complete, that telemetry is accurate, that limits are approved or that timing is
valid. Use only sanitized evidence; this tool does not scan for secrets or
private content. It does not authorize a run or accept an NFR.

### Understanding connection timing

For a successful HTTP request, k6 reports `connecting` (TCP setup),
`tls_handshaking` (encrypted-session setup), `blocked` (connection acquisition)
and `duration` (sending, waiting and receiving). In the reviewed k6 v2.3.0
source, TCP and TLS setup for a successful new connection fall inside the
blocked interval. When a connection is reused, its setup phases can be zero.
The connection metrics remain useful as separate diagnostics.

For a correct response, adding that response's `blocked` and `duration` is a
candidate approximation of its connection-acquisition-plus-response time.
Calculate this for each response before finding percentiles; do not add separate
percentiles. It does not cover the exact entire JavaScript-call boundary or use
a verified monotonic clock. If connection acquisition fails, the source can
leave blocked at zero even when time was spent trying. Count failures and
timeouts separately; do not treat their apparent zero timing as proof that they
were fast. A successful response, zero blocked time or plausible duration does
not prove the clock and all boundaries were sound.

The user prefers this built-in approach to a custom timer. The [experiment log](experiment-log.md#2026-11-01-195033-utc--exp-02-proposed-timing-protocol-revision)
records the proposed rule and its limitations. The approved comparison design
still requires a verified monotonic clock; the affected owners must review the
revision before it can replace that rule. NFR-01 and NFR-02 need their own
reviewed timing decisions. NFR-05 measures chat submission to recipient display
and is not replaced by these HTTP phases.

For synthetic offline evaluation only, `comparison_phase_preview.js` can select
timing fields from the same supplied response. `comparison_phase_report.py`
accepts a local JSON array of objects with `outcome` and `timings`; a correct
record's `timings` contains exactly `blocked`, `duration`, `connecting` and
`tls_handshaking` in milliseconds, while failure records may use null. For
example, run:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_phase_report synthetic.json --output new-preview.json
```

The output must not exist. The report counts failures separately and suppresses
all candidate percentiles if any correct record has missing, invalid or
over-five-second timing. That limit is a warning, not proof of impossible data.
It never claims a verified clock or NFR acceptance, and it is not connected to
the workload or current accounting report.

The installed k6 v2.3.0 on this Linux environment was checked with `k6 inspect`:
`performance.now` was unavailable. The current local comparison script uses
`Date.now`, which does not meet the existing verified-monotonic requirement.
The user's preferred direction is built-in k6 phases, without requiring a custom
Go extension; affected-owner review of the protocol change remains open. The
existing disconnected prototype is not selected. Before a real run, settle the
timing protocol and verify the actual generator version, phase coverage, failure
accounting and clock-observation procedure. The preview and inspect check do not
establish those run conditions or demonstrate performance.

At the immediate burst transition, warm-up requests may finish during the first
five seconds of measured arrivals. The k6 VU limit is per scenario, so both
burst cohorts can jointly use up to twice the supplied per-scenario maximum.
The future generator plan must account for this combined maximum and establish
that its approved host, concurrency and resource limits are respected.
