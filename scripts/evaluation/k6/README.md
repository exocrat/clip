# Local k6 load-runner preparation — SE-01 Step10

## EXP-02 local comparison preparation

For offline ordered-reference binding and telemetry metadata validation, see
[comparison preparation inputs](../../../docs/evaluation/comparison-preparation-inputs.md).
These commands do not send requests or authorize measurements.

The combined pre-request input check is also offline. It requires complete
binding and paired plans, rebuilds and checks the case corpus from the supplied
ordered reference, then verifies their dataset and corpus fingerprints agree:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_run_preflight \
  path/to/binding-plan.json path/to/complete-case-corpus.json \
  path/to/reviewed-ordered-reference.json path/to/complete-paired-plan.json
```

It prints aggregate status only and always sets `measurement_authorized` to
false. A future real-target runner must call/enforce this and its other reviewed
gates before requesting a session or sending traffic; this command is not yet
wired to that runner.

To check one cycle's profile, append `--workload-profile path/to/profile.json
--cycle 1 --expected-profile-sha256 EXPECTED_SHA256` (or cycle 2 or 3). All
three options are required together. The checker compares the file's exact bytes
with the supplied hash, checks its cases and planned starts, and validates the
five-second timeout and worker settings' shape. Without these options both
profile-check flags are false. The hash does not prove review, actual use, or
that the file cannot change later; other run gates still apply.

For offline NFR-01/02 draft checks, run with the project's Node 24:

```sh
node scripts/evaluation/k6/nfr_profile_preflight.mjs nfr-01 data/evaluation/workloads/browse-nfr-draft-v1.json
node scripts/evaluation/k6/nfr_profile_preflight.mjs nfr-02 data/evaluation/workloads/hybrid-nfr-draft-v1.json
```

Both existing drafts deliberately fail: their warm-up, timeout and null IDs
are incomplete. A candidate copy must use the designed rate (20 browse or 10
Hybrid), 60-second warm-up, 300-second measured window and five-second timeout;
each case must supply an ordered ID array. Empty arrays explicitly represent an
empty expected page and are not a substitute for representative cases. Exit 0
means these limited draft checks passed; exit 2 means they failed. The tool does
not obtain a session, execute a workload, attest review, verify dataset/source
bindings, case coverage, full expected response fields, concurrency, retries or
timing. It always returns `execution_permitted: false`; the future real-target
runner must enforce all final gates before obtaining credentials or sending
requests. The existing local runner refuses all `nfr-draft` profiles.

`comparison_runner.py` runs one to ten case-shaped requests against the owned
synthetic inspection app on port 5174, 5175 or 5176. It obtains a synthetic buyer
session from that app in memory, invokes the explicitly named k6 binary with a
clean environment and temporary metrics, and prints route kinds, HTTP statuses
and correctness against supplied expected responses. It is not measurement
evidence. Start the documented synthetic inspection app first; use separately
prepared expected cases bound to that app's data. Each case has `request` and
`expected` keys: the latter is the complete expected page or detail response.
Pass the case array over standard input:
Search cases must explicitly specify `search_mode: "hybrid"`; the generated API
defaults to Keyword, so omitting the mode would test the wrong behavior. The
runner checks all cases with `k6 inspect` before creating a synthetic session.

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_runner --port 5175 --k6 /usr/bin/k6 < local-reviewed-cases.json
```

Exit 0 means all supplied cases matched; exit 1 means one or more did not; exit 2
means preparation failed. This runner refuses other ports and does not accept cloud targets or real
credentials. The installed binary's provenance and the full scheduled/checked
workload remain separate requirements. The older single-case environment input
for `comparison_smoke.js` was replaced by `CLIP_COMPARISON_LOCAL_CASES`.

This tool runs bounded loopback pilots only. It cannot execute the full-rate NFR
profiles or accept SE-CORE/DATA-READY/NFRs. The final target/auth/data/image/index/
telemetry/resource/cost/repetition plan remains a separately approved real gate.

`comparison_schedule.js` and `comparison_load.js` prepare the EXP-02 approved
sequence: one request per iteration in a 5-browse/3-Hybrid/2-detail cycle;
0.2 requests/s low, 10 requests/s normal and 50 requests/s burst; 60-second
warm-up, 300-second measurement and up to five seconds between cohorts. Burst
warms at 10 requests/s, then starts 50 requests/s immediately. Low uses one
iteration per five-second time unit. Arrival windows are sequential; burst
warm-up requests may finish draining after the measured arrivals begin, with
their own scenario tags. The configured VU maximum applies per scenario: during
that overlap the two burst scenarios can use up to twice that maximum. A future
real-run plan must explicitly budget and verify the combined generator cap. The load
script checks complete expected responses, makes one request per iteration and
accepts only a loopback target plus an explicit synthetic session. It does not
write response bodies or credentials to output. Its local profile now requires
a `sequence_starts` object with one index (0–9) per condition; warm-up and
measurement for that condition use the same index. A single legacy
`sequence_start` is insufficient. The values must match the paired plan, but
the script itself does not open or verify that plan.

The checked-in `ecs-lambda-comparison-schedule-v1.json` is a design schedule,
not an executable final manifest. Dataset-bound expected cases, their reviewed
ten-case sequence and selected rotation seed, VU caps, real authenticated-session limits,
deployed parity, run/cost caps, telemetry and cleanup approval remain open. The
full k6 script is not run until those inputs are reviewed; the separate runner
still executes only bounded local pilots. This schedule preparation creates no
performance or NFR evidence.

The version-2 editable paired-plan and version-3 per-run manifest templates
record the approved `increment-one-per-pair-v1` rule and leave the rotation
seed blank. The run template also records the generated profile's reference
and hash separately from the schedule hash.
To print the nine starts for a synthetic example seed without running k6:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_rotation --seed 3
```

The generator is offline and does not choose the real seed or authorize a run.
The paired-plan and run-manifest validators check each start against its seed.
The validators reject older shapes for their respective templates.

`comparison_profile_builder.py` can create a new workload profile for each
cycle from a complete bound corpus and paired plan, with worker limits supplied
by the operator. Use the same cycle profile for A and B. The command and its
remaining evidence/generator-capacity gates are in the [preparation guide](../../../docs/evaluation/comparison-preparation-inputs.md#generate-a-cycle-workload-profile).
It does not run k6 or authorize a measurement.

`comparison_report.py` reads k6's JSON output without modifying it and writes a
separate derived report. It reports scheduled, issued, HTTP, dropped, incomplete,
correct and failed counts; timeouts and 429 throttles; offered and correct
throughput; and R7 p50/p95/p99 latency by cohort and route. Accounting mismatches,
missing samples, drops and wall-clock anomalies remain visible and make the
corresponding accounting/delivery flag false. Its infrastructure section says
`not_collected_local_preparation`; deployed ECS, Lambda and PostgreSQL telemetry
must be attached separately before a real run is assessed.

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_report path/to/raw.ndjson --output path/to/new-report.json
```

The output path must not already exist. Raw k6 JSON stays unchanged; incomplete
or dropped delivery still writes a report but exits nonzero.
The per-run manifest requires different raw-output and derived-report references.
If a calculation needs correction, preserve the original report and write a new
versioned path (for example, `analysis-v2.json`); never edit a captured raw file
or replace an earlier report.

The report uses `issued + dropped_iterations` as generator-offered work and
counts only `correct` completions as successful throughput. It retains route
and cohort counts, all-completed and correct-only latency quantiles, timeout,
429 throttle and other failure categories. Missing counter/latency samples,
unexpected route/outcome tags, noninteger counters or clock anomalies invalidate
the accounting check. This parser currently treats HTTP 429 as an explicit
throttle signal; other non-200 responses remain categorized by status class.

The per-run evidence template is
`data/evaluation/workloads/ecs-lambda-run-manifest.template.json`. It separates
the immutable approved schedule from run-specific values and keeps evidence by
run under `docs/evaluation/experiment/<run-id>/`. Validate the untouched template
or a completed record with:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_manifest data/evaluation/workloads/ecs-lambda-run-manifest.template.json
```

The validator enforces the schema and approved workload constants, rejects
unknown fields and common credential/PII patterns, and refuses incomplete
captured records. Its result always says `measurement_authorized: false`; separate
run approval remains required.

## Tool and sources

The official k6 v2.3.0 macOS ARM64 archive/checksum file are pinned in install.py.
Installation is only .tools/k6/v2.3.0/k6; no package manager/global link/PATH edit.
SHA256 is checked against pinned release metadata and checksum content, ARM64
Mach-O minimum OS is inspected before execution (12.0.0; host13.7.8), then version
is verified. Source/cache/installation metadata are retained locally. This installer
does not claim Linux support/packaging. Root Python/model/lock remain unchanged.

- [Official release](https://github.com/grafana/k6/releases/tag/v2.3.0)
- [Arrival-rate executors](https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/constant-arrival-rate/)
- [Built-in metrics/drops](https://grafana.com/docs/k6/latest/using-k6/metrics/reference/)
- [Custom summary completion hook](https://grafana.com/docs/k6/latest/results-output/end-of-test/custom-summary/)

## Source roles and inputs

- core.js validates fixed profiles/public responses, query shapes, fixture oracle
  IDs and generated-contract property parity. It exports pacing definitions shared
  by the real k6 script and Node tests. Fixture expected IDs are technical test
  oracles, never human relevance labels or final dataset judgments.
- load.js issues exactly1uncached collection GET per started in-cohort iteration,
  no redirect/retry/catalogue/image request. It uses only local modules/metrics.
  Native header or explicit fault-fixture header must match selected target kind.
  Public page shape, coordinates, safe summary fields, availability/window/filter
  values, uniqueness and expected controlled IDs must pass; status200alone fails.
- runner.py preflights bounded local profiles/target/binary, creates a fresh ignored
  run directory, freezes profile/source/tool/target/approval-scope manifest, invokes
  real k6 with clean env/no usage reporting/no remote outputs, and retains raw
  metric points, logs, completion marker and aggregate report. Output cannot escape
  .tools via traversal/symlinks. A timeout kills/reaps the owned k6 process.
- fault_probe.py owns ephemeral local HTTP scripts for wrong result (valid-shaped
  empty200),401, request timeout and valid-but-slow generator shortfall. Short2s
  profiles stay within the approved local caps. No real auth/search is claimed.

The pilot profile is2rps,5s warm-up+10s measured, max2active client requests and3s
timeout,30HTTP requests total. Phases do not overlap: each has a bounded drain,
and measured arrivals start after warm-up plus its timeout. k6 may allocate2VUs
per phase, but at most2can issue requests concurrently. A boundary iteration at the
exact scenario end is counted separately without HTTP, enforcing the half-open
rate*duration request cap. Raw built-in dropped iterations are never discarded;
shortfall/drops invalidate even perfectly successful returned requests.

The three nfr-draft profiles record20rps browse/10rps keyword/10rps hybrid and300s
for later discussion. Their warm-up/VUs/timeout/query examples are unapproved
proposals, not a target/run manifest. expected_ids is null. Runner refuses them;
real auth/approved target/final representative corpus/oracles must be added at the
original real checkpoint. Hybrid and indexed Keyword must remain separate series.
Draft manifests under docs/evaluation/nfr/nfr-01 and nfr-02 preserve unknown values
and are explicitly not executable/accepted.

## Measurements and limitations

Each custom issued counter precedes the single HTTP call; one outcome/elapsed
sample follows it. Built-in actual HTTP counts independently verify correspondence.
401/403, incorrect results, unexpected status, transport errors, request timeout
(comparison request/dial timeout codes 1050 and 1211), missing/interrupted completion, negative clock elapsed and generator
drops/shortfall stay visible. Completion marker plus exit0and complete valid
warm/measured cohorts are required for valid_preparation_run. nfr_accepted remains
false in every report. Absence of errors is not an NFR pass.

Latency is Date.now elapsed around the full synchronous HTTP call (including
connection/DNS/TLS where applicable), not http_req_duration alone. Resolution is
milliseconds and wall-clock changes can affect intervals; negative intervals mark
the run invalid. Comparison reports explicitly mark latency timing unverified:
matching counts and a lack of negative intervals cannot prove a monotonic clock.
The approved clock and end-to-end timing method remain an open gate.
Actual raw k6 HTTP phase metrics are retained for diagnosis. R7 interpolation
produces p50/p95/p99 for all completed and successful samples separately; empty is
null, not zero. Successful throughput means cohort completions divided by its
scheduled duration, including bounded drain. NFR01's successful denominator and
NFR02's all-issued eligible denominator remain explicit; failures are not removed.
The local pilot assumes all issued requests are eligible and reports both
`within_1s_fraction_of_correct` (correct responses only) and
`within_1s_fraction_of_issued` (all issued requests). These are arithmetic
previews, not NFR results. Its `valid` flag is stricter than either NFR and
requires every issued response to be correct. A real NFR-02 runner must establish
eligibility independently; dropped or missing work remains visible and invalidates
the run. Timing remains unverified.
Local small-cohort percentiles are not deployed evidence or a generator-capacity
claim at20/10rps. API/helper resource watchdog excludes k6/native PostgreSQL RSS.

## Registered commands

From repository root, using project-local Python/Node:

```sh
.venv/bin/python -m scripts.evaluation.k6.install
PATH="$PWD/.tools/node/bin:$PATH" .tools/node/bin/node --test scripts/evaluation/k6/core.test.mjs
.venv/bin/python -m pytest tests/evaluation -q -W error
.venv/bin/python -m scripts.evaluation.k6.fault_probe
```

The fault probe owns/stops its fixture servers; evidence is in the printed ignored
.tools directory. The actual pilot command requires an explicitly running owned
native preview (existing registered native_preview.py command); it creates no DB:

```sh
.venv/bin/python -m scripts.evaluation.k6.runner --profile data/evaluation/workloads/local-search-pilot-v1.json --port 8000 --output .tools/k6/pilots/UNUSED_RUN_NAME --isolated-local-pilot
```

Output directory must be new; never overwrite prior evidence. Runner exits2for
invalid workload/response/accounting, even when k6 itself returns0. Stop the owned
native preview after the run; it reaps helper/closes DB and retains its evidence.
No token/account/credential values are needed for the explicit local fixture.
The canonical final label file remains absent and cannot be fabricated by tools.

`comparison_cost_preview.py` performs offline per-run cost arithmetic on
operator-supplied values. Its input format and limits are documented in the
[preparation guide](../../../docs/evaluation/comparison-preparation-inputs.md#offline-per-run-cost-arithmetic).
It does not fetch billing or verify allocation or run validity.

`comparison_cost_binding.py` checks cost input run/condition and correct count
against a captured manifest and its hashed derived report. It does not verify
cost allocation, report provenance or run validity. See the preparation guide
for the offline command and limitations.

`comparison_cost_median.py` checks three run inputs and calculates their
per-run cost median offline. The [preparation guide](../../../docs/evaluation/comparison-preparation-inputs.md#three-run-cost-median-preview)
describes the command and outstanding validity checks.

`comparison_offline_prepare.py` combines local preflight checks for a selected
planned run, lists missing or invalid inputs, and always keeps measurement
disabled. See [offline preparation](../../../docs/evaluation/comparison-preparation-inputs.md#offline-preparation-for-one-planned-run).

`comparison_mock_runner.py` tests preflight and fake-session handoff ordering
with fixed in-memory simulation events. It cannot send traffic or authorize a
measurement; the future real runner still requires integration and review.

`comparison_session_handoff.py` prepares a session environment mapping after a
local check. It has no process or network action; the proposed variable and
security-review limits are in the [preparation guide](../../../docs/evaluation/comparison-preparation-inputs.md#session-handoff-preparation).
