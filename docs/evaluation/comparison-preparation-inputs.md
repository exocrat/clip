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

From the repository root, prepare a new corpus (the output path must not exist):

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_ordered_results path/to/reviewed-reference.json --output path/to/new-case-corpus.json
```

The command checks the archive hash and its A/B synthetic records, dataset
fingerprint and schema, query IDs/text, search-contract revision, model revision,
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
runtime behavior before changing the unverified report flag. No build, runtime
verification or measurement is authorized by the prototype.

At the immediate burst transition, warm-up requests may finish during the first
five seconds of measured arrivals. The k6 VU limit is per scenario, so both
burst cohorts can jointly use up to twice the supplied per-scenario maximum.
The future generator plan must account for this combined maximum and establish
that its approved host, concurrency and resource limits are respected.
