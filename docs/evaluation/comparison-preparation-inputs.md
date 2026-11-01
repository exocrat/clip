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
from the verified archive and ordered reference, and compares the complete
objects. The reference's search implementation revision must equal the planned
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
four telemetry references, cost source, raw k6 output and derived report in a
captured manifest point to local files with the recorded SHA-256 values:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_artifacts path/to/captured-manifest.json path/to/telemetry-metadata.json --evidence-root path/to/local-evidence-directory
```

It reuses manifest and telemetry metadata validation, requires telemetry and
cost windows to cover the run, and hashes all seven files under the selected
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

The [experiment log](experiment-log.md#2026-11-01-195033-utc--exp-02-proposed-timing-protocol-revision)
contains a proposed change. The approved monotonic rule remains in force until
the applicable design owners approve a revision. NFR-05 measures chat submission
to recipient display and is not replaced by these HTTP phases.

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
`Date.now`, which does not satisfy the approved monotonic-clock requirement.
Choose and independently verify a supported end-to-end monotonic timing method
before preparing a real-target measurement runner. No local inspect probe sends
requests or demonstrates performance.

A candidate is a [k6 JavaScript extension](https://grafana.com/docs/k6/latest/extensions/create/javascript-extensions/)
with a separate timer object per virtual user. A proposed `start()` retains a
Go `time.Time` with its monotonic reading; `stop()` returns elapsed milliseconds
and clears that start. A second start while active or a stop without a start
must fail. The workload would bracket exactly one synchronous HTTP call and
retain a duration for timeouts and exceptions without recording private data.
The disconnected prototype under `scripts/evaluation/k6/monotonic/` implements
this contract against the pinned upstream k6 v2.3.0 Go module; it is not selected
or verified for measurements. Review k6 and extension sources and build provenance; test VU isolation,
invalid call ordering, exception/timeout handling and boundary placement with
injected clocks and doubles; then independently verify the resulting binary and
runtime behavior before changing the unverified report flag. A temporary custom
binary passed the initialization-only `monotonic/inspect_bridge.js` check; this
does not establish request boundaries, concurrency behavior or reproducibility.
The prototype does not authorize measurement.

At the immediate burst transition, warm-up requests may finish during the first
five seconds of measured arrivals. The k6 VU limit is per scenario, so both
burst cohorts can jointly use up to twice the supplied per-scenario maximum.
The future generator plan must account for this combined maximum and establish
that its approved host, concurrency and resource limits are respected.
