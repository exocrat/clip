# Local k6 load-runner preparation — SE-01 Step10

## EXP-02 local comparison preparation

For offline ordered-reference binding and telemetry metadata validation, see
[comparison preparation inputs](../../../docs/evaluation/comparison-preparation-inputs.md).
These commands do not send requests or authorize measurements.

## Monotonic timing binary

`comparison_load.js` measures elapsed time with the repository's Go monotonic
timer extension. Install the custom k6 binary with the pinned builder:

```sh
.venv/bin/python -m scripts.evaluation.k6.install_monotonic
```

This records the k6/xk6/Go versions and hashes of the extension and resulting
binary under the ignored `.tools/k6/v2.3.0-monotonic/` directory. It requires a
local Go 1.26-or-later toolchain and builds only for Linux x86-64 or macOS ARM64.
Comparison and NFR load runs must bind their captured manifest to this binary's
hash. The official unextended k6 binary does not provide this timing interface.
The build follows Grafana's [k6 extension quickstart](https://grafana.com/docs/k6/latest/extensions/create/quickstart/)
using the pinned [xk6 v1.4.14 release](https://github.com/grafana/xk6/releases/tag/v1.4.14).

The combined pre-request input check is also offline. It requires complete
binding and paired plans, rebuilds and checks the case corpus from the supplied
ordered reference, then verifies their dataset and corpus fingerprints agree:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_run_preflight \
  path/to/binding-plan.json path/to/complete-case-corpus.json \
  path/to/reviewed-ordered-reference.json path/to/complete-paired-plan.json
```

It prints aggregate status only and always sets `measurement_authorized` to
false. The shared real-run coordinator invokes this preparation before its
live-target and session checks; the standalone command remains preparation
only.

To check one cycle's profile, append `--workload-profile path/to/profile.json
--cycle 1 --expected-profile-sha256 EXPECTED_SHA256` (or cycle 2 or 3). All
three options are required together. The checker compares the file's exact bytes
with the supplied hash, checks its cases and planned starts, and validates the
five-second timeout and worker settings' shape. Without these options both
profile-check flags are false. The hash does not prove review, actual use, or
that the file cannot change later; other run gates still apply.

The legacy NFR draft-shape check remains available with the project's Node 24:

```sh
node scripts/evaluation/k6/nfr_profile_preflight.mjs nfr-01 data/evaluation/workloads/browse-nfr-draft-v1.json
node scripts/evaluation/k6/nfr_profile_preflight.mjs nfr-02 data/evaluation/workloads/hybrid-nfr-draft-v1.json
```

It only checks that old draft format and never runs the workload. For this old
format, browse cases require expected listing IDs, while search cases carry no
expected IDs because NFR-02 measures latency, not ranking. New NFR-01/02
preparation uses a complete profile with full response cases for browse and
representative reviewed Hybrid query texts. The shared `nfr_load.js`
accepts loopback targets only and requires an explicit synthetic cookie. It
schedules the designed 20 or 10 requests/s, 60-second warm-up, 300-second
measurement, five-second drain and timeout, with no retries. Browse responses
are checked against full expected pages; NFR-02 search outcomes use HTTP
completion/status only and do not score relevance. Only aggregate metrics are
emitted. The profile's
`execution_permitted` and `nfr_accepted` fields must both be false.

```sh
CLIP_NFR_LOCAL_LOAD=true CLIP_NFR_LOCAL_TARGET=http://127.0.0.1:8000/api \
  CLIP_NFR_LOCAL_PROFILE=path/to/local-profile.json \
  CLIP_NFR_LOCAL_COOKIE='synthetic-session' \
  .tools/k6/v2.3.0-monotonic/k6 run --out json=path/to/new-raw.ndjson \
  scripts/evaluation/k6/nfr_load.js
.venv/bin/python -m scripts.evaluation.k6.nfr_report path/to/new-raw.ndjson \
  path/to/local-profile.json --output path/to/new-report.json
```

The reporter applies NFR-01's correctly completed browse denominator and
NFR-02's all-issued eligible-search denominator, retains failed and dropped
work, and always marks the result preview-only and timing provenance unverified.
NFR-02 counts successful HTTP responses completed within one second; it does
not judge relevance or ranking. NFR-04 separately scores Success@5 against the
reviewed labels. These reports do not accept drafts or NFRs.

The load modules now have a distinct `approved-runner` target mode. It accepts
only the exact `https://<planned-origin>/api` pair and requires the coordinator
to bind run ID, architecture, condition or profile, and session. NFR-03 also
requires the approved HTTPS origin and CSRF value. This mode is not a standalone
authorization. `prepare_real_run_plan.py` builds an offline hash-bound plan;
`real_run_coordinator.py` then validates it and a separate expiring approval,
stages the exact reviewed workload before live checks, verifies AWS routing and
the regular test-account session, runs once without retries, and preserves raw
output plus an immutable receipt. It cannot create resources or accept results.
The existing direct local mode remains loopback-only.

`real_target_preflight.py` is the shared read-only target check. Its plan
template binds one A or B target to exact AWS resources and the approved
Listing GET route patterns. `--inspect-live` performs read-only STS, ALB, ECS,
Lambda, RDS and encrypted-parameter checks, then checks `/health` over HTTPS
without following redirects or using proxy settings. It verifies the secret
resolves to the named RDS endpoint but never prints the connection string. The
result explicitly leaves DNS-to-ALB binding, source/data attestation, session
identity, workload provenance, evidence capture and measurement authorization
unverified. It can separately verify one supplied session from a named
environment variable after the AWS/HTTPS check. It does not start a workload
and does not replace the later authenticated parity smoke.

### Shared real-run planning and execution

Create one plan for every run and architecture. NFR profiles must already have
been built from the frozen cases. For NFR-01/02/03, supply the reviewed target
plan, profile, custom monotonic k6 binary, output directory and (for NFR-03)
fixture. For the comparison, also supply all paired-plan, corpus, parity and
schedule inputs:

```sh
.venv/bin/python -m scripts.evaluation.k6.prepare_real_run_plan \
  --workload-kind nfr-01 --run-id RUN_ID --configuration A \
  --target-plan .tools/targets/RUN_ID-A.json \
  --profile data/evaluation/workloads/RUN_ID-A-profile.json \
  --k6-binary .tools/k6/v2.3.0-monotonic/k6 \
  --evidence-directory docs/evaluation/nfr/nfr-01/RUN_ID \
  --output .tools/RUN_ID-plan.json
```

The output parent and evidence parent must already exist; the evidence folder
itself must not. The plan builder hashes the target, profile, modules and binary
and rejects mismatched A/B or incomplete inputs. It performs no AWS call and
leaves `execution_permitted` false. Review the exact plan bytes, then record a
separate short-lived approval using
[`real-run-approval.template.json`](../../../docs/evaluation/real-run-approval.template.json).
The coordinator requires that approval, the explicit `--execute` flag, and
`CLIP_REAL_RUN_SESSION_COOKIE` in the environment. NFR-03 additionally obtains
CSRF in memory; neither value is placed in arguments, plans, reports or logs.
The coordinator first stages and validates all local inputs, then inspects the
actual target and session, and only then starts the workload. A nonzero/timeout
run remains failed or incomplete, with raw output retained and no automatic
retry. These scripts are not deployment or run approvals.

After a run, produce the derived report separately and supply the raw file,
staged profile, coordinator receipt and exact run plan. This verifies that the
reported raw bytes match the run record and binds elapsed timing to the hashed
custom binary; incomplete or mismatched evidence is marked invalid. For
example:

```sh
.venv/bin/python -m scripts.evaluation.k6.nfr_report \
  docs/evaluation/nfr/nfr-01/RUN_ID/raw.ndjson \
  docs/evaluation/nfr/nfr-01/RUN_ID/stage/profile.json \
  --execution-receipt docs/evaluation/nfr/nfr-01/RUN_ID/execution-receipt.json \
  --run-plan .tools/real-runs/RUN_ID-plan.json \
  --output docs/evaluation/nfr/nfr-01/RUN_ID/report.json
```

NFR-03 and comparison have corresponding `nfr03_report` and
`comparison_report` commands with the same receipt and plan arguments. Reports
remain pending human measurement-validity review and always set NFR acceptance
to false.

### EXP-05 weighted-candidate pilot

The pilot has its own fixed profile and run mode because each candidate is a
120-second measured burst, followed by the unchanged five-minute comparison
profiles for the final study. Build one profile per candidate run ID/config from
the reviewed comparison profile and frozen dataset fingerprint:

```sh
.venv/bin/python -m scripts.evaluation.k6.exp05_pilot_profile_builder \
  .tools/real-runs/comparison-cases-profile.json RUN_ID A \
  --dataset-fingerprint FROZEN_DATASET_SHA256 \
  --pre-allocated-vus REVIEWED_PREALLOCATED_VUS \
  --max-vus REVIEWED_MAX_VUS \
  --output data/evaluation/workloads/RUN_ID-pilot-profile.json
```

The profile reuses the reviewed 5-browse/3-Hybrid-search/2-detail case mix,
keeps the checked sequence rotation, and fixes 60 seconds at 10 requests/s,
five seconds of drain, then 120 seconds at 50 requests/s. It performs one
checked read per iteration with no retries. `prepare_real_run_plan.py` accepts
`--workload-kind exp05-pilot` and binds the profile to the exact target plan,
which carries that candidate's ALB Lambda/ECS weight. Build all 15 target plans
and profiles before pilot execution; produce a matrix plan with
`exp05_pilot.py plan --target-bindings` mapping every run ID to its target-plan
hash. The normal one-run approval and coordinator then enforce account,
routing, session and raw-capture checks for each candidate.

Each pilot run plan also names and hash-binds the comparison binding, corpus,
ordered reference, paired plan, base comparison profile, parity record and
schedule. Its offline validation confirms the pilot cases and rotation still
match that reviewed source set before any live access. For one run, the plan
command adds those exact source paths:

```sh
.venv/bin/python -m scripts.evaluation.k6.prepare_real_run_plan \
  --workload-kind exp05-pilot --run-id RUN_ID --configuration B \
  --target-plan .tools/targets/RUN_ID.json \
  --profile data/evaluation/workloads/RUN_ID-pilot-profile.json \
  --k6-binary .tools/k6/v2.3.0-monotonic/k6 \
  --evidence-directory docs/evaluation/experiment-runs/RUN_ID \
  --binding-plan PATH_TO_REVIEWED_BINDING \
  --corpus PATH_TO_REVIEWED_CASE_CORPUS \
  --ordered-reference PATH_TO_REVIEWED_ORDERED_REFERENCE \
  --paired-plan PATH_TO_REVIEWED_PAIRED_PLAN --cycle 1 \
  --comparison-profile PATH_TO_REVIEWED_COMPARISON_PROFILE \
  --parity PATH_TO_REVIEWED_PARITY_RECORD \
  --parity-evidence-root PATH_TO_PARITY_EVIDENCE \
  --schedule data/evaluation/workloads/ecs-lambda-comparison-schedule-v1.json \
  --output .tools/RUN_ID-plan.json
```

Report each run with `comparison_report.py --condition burst --profile PROFILE`
and the matching execution receipt/run plan. Supply the 15 receipt-bound
reports and explicit generator, routing, telemetry, database-headroom and cost
checks to `exp05_pilot.py report`. The report may recommend a candidate for
human review; it cannot freeze the B weight or authorize the main experiment.
Review and freeze the numeric resource/headroom and cost criteria before the
pilot. Preserve every failed or incomplete run.

Build a new local preparation profile for one NFR and one configuration (each
configuration gets its own file and run ID). The builder binds all five browse
cases or three reviewed Hybrid queries to the checked-in frozen corpus and
creates files exclusively:

```sh
.venv/bin/python -m scripts.evaluation.k6.nfr_profile_builder nfr-01 A local-nfr01-a \
  --pre-allocated-vus 60 --max-vus 120 --output .tools/nfr01-a-profile.json
```

Capacity is an explicit local draft setting, not a capacity approval. The
Hybrid profile uses three representative query classes from the reviewed label
set, but relevance labels do not affect NFR-02's latency result.

## NFR-03 integrated mixed workload preparation

`nfr03_profile_builder.py` binds the frozen browse/detail cases and three Hybrid
inputs to a fixture file containing an existing wanted-request ID, conversation
ID and five saved-listing IDs. It creates a local-only profile for either A or B;
the IDs are syntax-checked but their live existence and authorization still
belong in the later real-target preflight. `nfr03_load.js` schedules the required
30/25/15/10/10/9/1 route mix at 50 requests/s for 60 seconds of warm-up and 300
seconds measured, sends one controlled wanted-request write per 100 operations,
uses unique operation IDs, performs no retries, and emits no response bodies.
It only accepts loopback targets and explicit synthetic session/CSRF inputs.

`nfr03_report.py` preserves every route outcome, requires exact scheduled counts
for all seven route classes, records drops and invalid timing, and lists each
write operation ID with any returned row ID. Its post-run read of the caller's
`/me/wanted-requests` pages matches the unique synthetic titles to recover row
IDs even when a timed-out create actually committed. This extra reconciliation
read is outside the measured denominator; the report never claims unresolved
writes are safe to repeat or that cleanup occurred. The post-run scan is capped
at ten 100-row pages and stops early when it finds all expected writes; a larger
history with unresolved operations stays incomplete for explicit reconciliation.
Profiles say `execution_permitted: false`; this local preview does not replace
the separately approved A and B real-target workload, resource/cost limits,
write cleanup plan, telemetry or identity/capacity checks.

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
sequence: each invocation requires `CLIP_COMPARISON_LOCAL_CONDITION` set to
`low`, `normal` or `burst`, and schedules only that condition. One request per
iteration follows a 5-browse/3-Hybrid/2-detail cycle;
0.2 requests/s low, 10 requests/s normal and 50 requests/s burst; 60-second
warm-up, 300-second measurement and up to five seconds between cohorts. Burst
warms at 10 requests/s, then starts 50 requests/s immediately. Low uses one
iteration per five-second time unit. Within each run, warm-up and measured windows are sequential; burst
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
the script itself does not open or verify that plan. The staging record identifies
the condition for the selected run; a future real runner must bind that value to
the workload and report and enforce the plan before credentials or requests.

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
corresponding accounting/delivery flag false. Per-condition reports reject
missing route tags on tracked request metrics, compare outcome and latency-label
counts overall and by route, and suppress affected correct-latency summaries when
counts disagree. Dropped arrivals do not require a route tag because no request
was assigned. These aggregate checks do not prove per-request pairing. Its infrastructure section says
`not_collected_local_preparation`; deployed ECS, Lambda and PostgreSQL telemetry
must be attached separately before a real run is assessed.

`cloudwatch_capture.py` collects bounded read-only ECS, ALB, Lambda and RDS
metrics for a completed run. It binds the exact target-plan file hash, run ID,
configured account/caller and actual UTC interval; it refuses an unexpected
AWS caller, a window over six hours or an existing output directory. It queries
one-minute data and writes separate immutable ECS/ALB, Lambda and PostgreSQL
artifacts. Configuration A records Lambda as not applicable. Empty metric
series remain `NoData`; the tool never treats missing observations as zero or
decides whether a run or NFR passed. Generator CPU/RSS and dropped work still
come from the approved local generator evidence and k6 output.

```sh
.venv/bin/python -m scripts.evaluation.k6.cloudwatch_capture \
  docs/evaluation/experiment-runs/RUN/target-plan.json \
  docs/evaluation/experiment-runs/RUN/run-window.json \
  --output-dir docs/evaluation/experiment-runs/RUN/cloudwatch
```

The target plan selects the AWS profile and region. Its expected caller must
match live STS identity. The output directory must be new. The capture uses
CloudWatch `GetMetricData` and STS identity lookup only; it does not inspect
logs, read parameters or change resources. ALB target-group counts help verify
which path received requests, while ECS/Lambda/RDS series show service health
and pressure. Minute-level service metrics do not identify an individual
request.

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_report path/to/raw.ndjson --condition low --output path/to/new-report.json
```

Select the condition recorded for that run (`low`, `normal` or `burst`). The
CLI rejects mixed-condition or missing-phase tracked metrics. The output path
must not already exist. Raw k6 JSON stays unchanged; incomplete
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

### EXP-07 paired analysis

`comparison_analysis.py` reads the three A/B repetitions for low, normal and
burst conditions from immutable derived reports and separate cost records. It
checks every report/cost file hash and receipt-bound execution provenance,
requires a human validity note for all 18 runs, retains invalid/incomplete runs
as exclusions, and calculates the frozen median-based weighted score,
sensitivity examples and paired score differences. It scores only a
configuration whose eligibility review says `eligible`; this is a calculation
tool, not an eligibility decision, NFR acceptance, or product approval.

Start with `data/evaluation/workloads/exp07-analysis-input.template.json` and
`data/evaluation/workloads/exp07-cost-input.template.json`. Fill the score
anchors from the reviewed normal-load cost model and freeze them before
inspecting final comparative results. Preserve report and cost files, record
their SHA-256 values, and include a review reference for each run's validity.
Then write a new analysis file:

```sh
.venv/bin/python -m scripts.evaluation.k6.comparison_analysis \
  path/to/frozen-analysis-input.json --output path/to/analysis-v1.json
```

The report includes per-run medians/ranges, retained exclusions, weighted
contributions, sensitivity scores, matched A/B score differences and an
inconclusive/tie/score status. It never edits raw data and always leaves NFR and
product acceptance false. A human reviewer must verify calculations and the
eligibility/validity decisions against the raw results and telemetry.

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

Latency is measured by a monotonic timer around the full synchronous HTTP call,
including connection setup when incurred; it is not taken from
`http_req_duration` alone. Invalid or missing timer samples remain visible and
make accounting incomplete. Reports still mark timing unverified until the
captured run binds to the custom k6 binary hash and the approved end-to-end
boundary has been checked.
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

`comparison_evidence_capture.py` checks for known sensitive content and prepares
separate, exclusive local raw and report files with read-back hashes. The [preparation guide](../../../docs/evaluation/comparison-preparation-inputs.md#local-evidence-capture-helper)
explains incomplete captures and required privacy review; this is not a runner.

`comparison_declared_parity.py` compares supplied A/B dataset, schema, index,
database and search/model declarations to the bound plan and reference. It can optionally verify local evidence hashes; it does not prove deployment parity. See the [preparation guide](../../../docs/evaluation/comparison-preparation-inputs.md#declared-ab-data-and-search-parity).

`comparison_stage_run.py` checks selected-pair parity declarations and local
evidence hashes, then stages a profile, schedule and fixed set of workload
modules without running them. The [preparation guide](../../../docs/evaluation/comparison-preparation-inputs.md#stage-the-files-for-one-planned-run)
describes the fingerprint inputs and remaining approval and use checks.

The synthetic integration check connects preparation, staging, fake-session,
report and capture helpers without executing a workload; see the [preparation
guide](../../../docs/evaluation/comparison-preparation-inputs.md#synthetic-integration-check).
