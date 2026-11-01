# Experiment log

This log tracks detailed progress and decisions for the ECS-only versus ECS+Lambda
comparison and related NFR measurements. The [project work log](../status/work-log.md)
remains the task-status and verification record. Approved manifests, raw results,
and analysis belong in the [evaluation evidence homes](README.md), linked from
this log. Record UTC times; never include credentials or private data.

For each meaningful checkpoint, record its task and step, purpose, environment,
revisions, inputs and target, changes and decisions, exact checks and outcomes,
evidence links, verification state, limitations, and next action. For measured
runs also record the run ID, configuration, manifest, workload and intervals,
validity, results, costs and cleanup; link raw evidence instead of copying it.
Record skipped, failed and inconclusive checks as such and retain prior entries.

## Current checkpoint

- **EXP-01:** Design verified; see the [comparison protocol](ecs-only-vs-ecs-lambda-task-list.md).
- **EXP-02:** Steps 1 and 2 reviewed from retained dataset evidence. Step 2's
  actual ECS/Lambda database and configuration equivalence remains pending.
- **EXP-02 Steps 3–5:** Local path, response and scheduled-workload preparation
  exists on `task/exp-02-workload`. A ten-case dataset-bound draft now has five
  browse and two detail expected responses plus three reviewed Hybrid query
  references. An offline adapter now accepts ordered results when supplied; the
  real ordered results and independent review remain pending. Corrected the
  burst arrival transition to eliminate an unintended five-second gap. DATA-READY
  acceptance, capacity/session/run gates and deployed-path checks remain pending.
- **EXP-02 Step 6:** Client accounting/reporting is implemented and locally
  checked with synthetic metrics. Offline metadata checks expose declared timing,
  generator limits, VU headroom and drops. A verified monotonic k6 timing method,
  real resource telemetry and a real k6 run remain pending. Reports explicitly
  mark latency timing unverified even when counts match.
- **EXP-02 Step 7:** A per-run capture template and validator are ready. No
  measured run exists, so run-specific values remain blank. An offline telemetry
  metadata validator now checks run binding, artifact references and windows; it
  does not open or attest actual artifacts.
- **EXP-02 Step 8:** The existing report tool reads raw k6 output and opens
  derived reports as new files. Added a manifest guard against using the same
  reference for raw and derived evidence; local regression checks confirm raw
  hashes stay stable and existing reports cannot be replaced. User verified
  this checkpoint; no run output has been captured.
- **Measurements:** No ECS/Lambda comparison or final NFR run is recorded here.

## History

### 2026-11-01 18:48:42 UTC — EXP-02 local safety and reporting audit

**Direction:** The user verified the preceding grouped result and approved a
local timing, runner-safety and report audit. The checkout was clean at the
start, at `422a45a`; no live requests or workload runs were authorized.

**Timing:** The approved boundary includes connection setup and requires a
verified monotonic clock. The installed Linux k6 v2.3.0 previously lacked
`performance.now` in an inspect-only probe. `Date.now` can change with wall time,
and built-in `http_req_duration` omits connection setup, so neither resolves the
approved boundary. No supported replacement has been verified. The report now
states `latency_timing_verified: false` and explains that matched accounting and
no detected backward jumps do not establish valid timing. Latency figures remain
preview values; a clock solution and verification remain open.

**Runner and evidence:** The existing bounded local smoke runner permits only
documented loopback ports and validates the entire supplied case batch through
`k6 inspect` with a placeholder before synthetic login. It is not a real-target
runner; real-target credential and request gates remain to be implemented. The
report opens raw data read-only and creates a separate report exclusively; tests
cover unchanged raw hashes and refusal to overwrite existing analysis. It
reports counts, throughput, errors, timeouts, throttles and drops, and explicitly
marks infrastructure telemetry uncollected. Artifact contents, real metrics,
and provider claims are not verified by these local tools.

**Checks:** 35 focused Python tests and three Node test files passed. The system
Python lacked pytest and Black; the repository virtual environment supplied them.
Black's multi-file invocation failed because its worker socket was denied by the
sandbox; both individual file checks and `git diff --check` passed. No k6 run, experiment,
cloud, database or external-service call occurred. This result awaits user
verification.

### 2026-11-01 18:23:04 UTC — EXP-02 ordered references, timing and telemetry preparation

**Direction and scope:** The user verified a grouped Steps 4, 6 and 7 local
preparation checkpoint and requested detailed experiment logs. For preparation
only, treat DATA-READY and ordered Hybrid results as assumed available; neither
is recorded as actually accepted. No workload, API, cloud or provider call was
authorized or performed. Existing modifications and untracked work were retained.

**Step 4:** Added `comparison_ordered_results.py` and an incomplete ordered
reference template. The adapter checks frozen archive/data/schema/model/search
contract bindings, the three exact query IDs/texts, supplied order, eligibility,
duplicates and page shape, then reconstructs expected public listing fields from
the synthetic archive. It records a canonical reference hash and a review-record
pointer, without claiming the referenced review occurred. Output is created only
at a new path and remains non-authorizing. The actual ordered results were not
present in the repository and were not invented; tests use explicitly synthetic
orderings. The initial corpus remains a draft until actual references are supplied.

**Step 6 timing correction:** Inspection found that `comparison_schedule.js`
placed a five-second gap between the burst warm-up and measured arrivals, despite
the approved immediate 10-to-50 requests/s transition. The previous Step 5 log's
claim of an immediate transition was therefore incorrect; no workload was run
under that schedule. Corrected the boundary and its test. Warm-up requests may
finish draining during the first five seconds of measured arrivals and retain
their warm-up scenario tags. k6's VU cap is per scenario, so the two burst
cohorts can jointly use up to twice the supplied cap during that overlap; a
future plan must budget and verify the combined generator limit.

**Steps 6–7 telemetry:** Added `comparison_telemetry.py` and an incomplete local
metadata template. Given a captured manifest, the validator checks the run ID,
clock declaration, operator-supplied generator CPU/RSS/VU limits and drops, and
ECS/Lambda/PostgreSQL/generator artifact references, hashes and UTC coverage.
It reports supplied-limit/headroom flags without reading artifact contents,
attesting hash values or limits, proving monotonic timing, or authorizing a run.
The corresponding preparation guide and command index describe input formats,
limitations and no-request commands.

**Checks:** 33 focused Python tests passed with warnings as errors, covering the
new binders and prior corpus/manifest/report checks; three additional mocked
runner tests passed. Four Node test files passed, including the mocked k6 adapter.
Black formatted each changed Python file individually; template JSON parsing and
`git diff --check` passed. `k6 inspect` accepted a test-only synthetic corpus and
showed burst warm-up at 12m20s and 50/s measured arrivals at 13m20s. A separate
inspect probe found `performance.now` unavailable in installed Linux k6 v2.3.0;
the existing `Date.now` code is not a verified monotonic method. Inspect sent no
requests. No experiment, real telemetry, measured result or NFR pass is claimed.

**Follow-up checks at 2026-11-01 18:27:13 UTC:** Strict Mypy initially found a
duplicate module path, then identified missing typing in the telemetry/manifest
boundary. Added type annotations and explicit validated-object narrowing without
changing manifest validation behavior. Mypy with `--explicit-package-bases` now
passes for the manifest, ordered-reference and telemetry scripts; the 16 affected
manifest/telemetry tests pass with warnings as errors. Contract freshness check
could not complete: the available Node is 26.8.2 and project-local Node 24 is
absent. The generator requires Node 24 and reported its standard toolchain error.
No dependencies were installed or downloaded. Full aggregate/contract checks
remain pending on the pinned toolchain.

**Next gates:** Obtain and bind actual reviewed search references; verify a
supported monotonic end-to-end clock and combined generator caps; validate real
telemetry artifacts/approval against actual run inputs; finish real-target/auth
tooling and the separate deployment, data, review and action gates. This grouped
local result awaits user verification.

### 2026-11-01 17:51:15 UTC — EXP-02 dataset-bound case corpus draft

**Purpose and evidence:** Continued the verified Step 3–4 corpus preparation
using the retained NEXT-06 archive, frozen-dataset manifest and reviewed
`query-labels.json`. The archive SHA-256 and logical fingerprint match the
frozen manifest; its A/B listing and image-plan records match. The final dataset
is still marked `data_ready: false` and its retained native-rebuild receipt says
SQL is not loaded.

**Result:** Added `prepare_comparison_corpus.py` and the generated
`ecs-lambda-case-corpus-v1.json`. The draft contains the approved 5/3/2 mix:
five browse cases (first/later pages, with/without category filters), three
explicit Hybrid cases using reviewed direct-word, related-word and meaning-based
queries, and two available-listing details. Browse/detail expectations are
derived from frozen rows and the public response contract. The three search cases
retain Mohit's reviewed relevant-ID sets but have null ordered responses. The
NEXT-06 Step 4 result contains six different diagnostic query phrases; its
ranking samples are not reviewed case references and cannot supply order for
these approved query texts. Canonical reference-data guidance prohibits
manufacturing rankings from relevance labels or measured top results.

**Checks:** The generator verifies the archive hash, frozen fingerprint/schema/
seed, A/B listing/image-plan equality and available-listing count. One focused
Python test passed. Black checks passed for each changed Python file. A
regenerated draft compared byte-for-byte with the retained output. k6 schedule
validation accepted the ten-case mix, and the existing response checker accepted
all seven dataset-derived expected responses. `k6 inspect` refused the full draft
with `invalid_expected_case` because Hybrid order is unset; it sent no requests.
`git diff --check` passed. No API, cloud, deployed path, performance workload or
measurement was run.

**Remaining:** The case file is deliberately not executable. Ordered Hybrid
responses need final DATA-READY search results for these exact queries and
independent Search-owner review. Browse/detail expectations also await the same
case review. Availability is frozen only through 2026-12-01; run timing must
remain within that window or the dataset/cases must be revalidated. See the
[case draft](../../data/evaluation/workloads/ecs-lambda-case-corpus-v1.json)
and [generator](../../scripts/evaluation/k6/prepare_comparison_corpus.py).

### 2026-11-01 16:11:38 UTC — EXP-02 Step 8 immutable raw and versioned analysis

**Direction:** User verified the Step 8 understanding. Reopened the EXP-02 task
and evidence rules. Existing `comparison_report.py` already reads the raw k6
file without writes and uses exclusive creation for its separate report path.

**Implementation:** `comparison_manifest.py` now rejects a captured record when
its raw-output and derived-report references are identical. The k6 guide says to
preserve earlier reports and write corrected calculations to a new versioned
path. `test_comparison_manifest.py` covers a reference collision;
`test_comparison_report.py` exercises the CLI, verifies the raw file's SHA-256
is unchanged, and confirms a repeated report command refuses to replace the
existing report. The report generator itself needed no behavior change.

**Checks:** Nine focused Python tests passed. Black check-only passed for each
changed Python file; the run-manifest template validator returned `valid: true`,
`state: template`, `measurement_authorized: false`; `git diff --check` passed.
An initial multi-file Black invocation failed to start worker processes in the
sandbox, and a second multi-file invocation stalled; formatting and check-only
were then run per file and passed. No k6 workload, cloud call, or measurement ran.

**Remaining:** Step 8 is verified. The tool proves local no-write and
no-overwrite behavior, but there are no actual captured run files or hashes yet.
All deployment/parity, case-review, capacity, run-approval, telemetry, cost,
and cleanup gates remain open.

### 2026-11-01 16:06:30 UTC — EXP-02 Step 7 evidence manifest preparation

**Direction:** User verified the Step 7 understanding. Reopened the experiment
and evidence-home instructions: every run needs identifiable revisions, target,
data/workload, timing, telemetry, cost, raw/derived outputs and cleanup evidence;
the record excludes secrets and personal/private content.

**Implementation:** Added
`ecs-lambda-run-manifest.template.json` with placeholders for configuration A/B,
condition/repetition, owner role, planned/actual UTC times, target account/role/
region/resource IDs, app/image/frontend/migration/API revisions, dataset seed/
counts/fingerprints, workload/case/script hashes and command reference, per-system
telemetry artifact paths and hashes, cost source/interval/amount/billing delay,
raw/derived evidence hashes, and approval/cleanup references. The approved mix,
timing and retry policy are repeated as immutable constants. `comparison_manifest.py`
validates exact fields and those constants, checks captured records are complete,
checks count/fingerprint/UTC fields, screens common credential/PII/signed-URL
patterns, and always reports that validation grants no measurement authorization.
`test_comparison_manifest.py` covers untouched templates, missing/extra data,
unsafe values, schedule drift, complete capture records and undersized datasets.
The workloads README, k6 guide, evaluation index and environment command registry
document where per-run copies belong and how to validate them.

**Checks:** Four focused Python tests passed; the template parsed and the validator
returned `valid: true`, `state: template`, `measurement_authorized: false`. Black
reported both changed Python files unchanged; JSON parsing and `git diff --check`
passed. No run values were filled and no cloud/load action occurred.

**Remaining:** The exact run command, target/resource identifiers, deployed
revisions and migration head, accepted dataset and paired-case fingerprints,
telemetry/cost records, approval reference and cleanup evidence are not available
until the real deployment and run gates. Copy and populate a manifest only for an
actual authorized run; do not treat this template or validation as authorization.

### 2026-11-01 15:56:58 UTC — EXP-02 Step 6 request accounting

**Direction:** User verified the Step 6 scope. The plan requires request outcomes,
latencies, timeout/throttle/failure counts, offered and successful throughput,
and relevant runtime/database metrics, with authentication outside measured
traffic.

**Implementation:** `comparison_load.js` now keeps the full cohort tag, marks
HTTP 429 as throttling, and records wall-clock anomalies instead of silently
clamping them away. `comparison_report.py` reads immutable k6 JSON points and
produces separate per-cohort and per-route accounting, R7 p50/p95/p99 latency,
scheduled/issued/HTTP/dropped/completed/failed counts, offered and correct
throughput, and accounting/delivery validity flags. Dropped iterations count as
offered but never delivered. The derived report explicitly marks AWS/PostgreSQL
telemetry as not collected. `test_comparison_report.py` covers complete output,
throttle/timeout classification, dropped delivery, missing outcomes/latencies,
clock anomalies and malformed counter values. The k6 README documents how to
create a new report without changing raw results.

**Checks:** Four focused Python tests passed; three focused Node test files passed;
k6 v2.3.0 `inspect` parsed the six-cohort script; `git diff --check` passed.
Black initially reported the test file needed formatting; it was formatted, and
per-file Black checks then passed for both changed Python files. The combined
Black process had hung during shutdown. Initial unit-test failures exposed an
incomplete phase tag and mismatched synthetic case expectations; both were
corrected before the passing run. No HTTP workload or infrastructure metrics
were collected.

**Remaining:** Validate the report against actual k6 JSON from a bounded local
request run, exercise local timeout/throttle/dropped-work faults through k6,
and attach real ECS/Lambda/PostgreSQL telemetry only when deployed-path gates
and separate run approvals permit. The final cases, seed, capacity/session caps,
cloud run manifest and cleanup remain open. Step 6 is partial; no NFR or A/B
claim is made.

### 2026-11-01 14:22:56 UTC — EXP-02 Step 5 scheduled workload configuration

**Direction:** User verified the Step 5 understanding. Reopened the approved
comparison plan. Its mixed request schedule is 50% browse, 30% Hybrid search,
20% detail; the low/normal/burst rates are 0.2/10/50 requests per second; each
cohort has 60 seconds warm-up and 300 seconds measured, with up to five seconds
for drain. Burst warms at 10 requests/s then transitions to 50.

**Implementation:** `comparison_schedule.js` builds six sequential k6
constant-arrival-rate cohorts, including low-rate `1 per 5s`, and validates a
ten-case 5/3/2 mix with a paired-run rotation input. `comparison_load.js` uses
one checked HTTP read per iteration, the supplied synthetic cookie, no retries
or redirects, exact response checks and loopback-only target validation.
`comparison_schedule.test.mjs` checks cohort rates/order/drains, capacity input,
mix and stable rotation. `ecs-lambda-comparison-schedule-v1.json` records the
approved values and names remaining run inputs. The k6 README describes how
these pieces relate to the existing bounded local runner.

**Checks:** Three focused Node test files passed (3 test files); k6 v2.3.0
`inspect` parsed the prepared schedule and displayed all six executor cohorts.
JSON parsing and `git diff --check` passed. No load scenario was run. The first
test command used a missing repository-local Node path; rerunning with available
system Node 26.8.2 passed. k6 inspect used a synthetic input profile under
`/tmp`; it contains no credentials or repository dataset values.

**Open inputs and limits:** No independently reviewed final ten-case dataset
corpus or seed/rotation manifest exists yet. EXP-01 Step 7 capacity limits,
actual session concurrency/rate limits, real ECS/Lambda parity, final target,
telemetry, run/spend caps, cleanup and run authorization remain pending. The
schedule is not an executable or approved deployed run manifest and provides no
performance/NFR evidence. Step 6 outcome/latency/drop accounting remains ahead.

### 2026-11-01 14:18:17 UTC — EXP-02 Step 4 local response checks

**Direction:** User verified the Step 4 understanding. Reviewed cases contain
separate `request` and complete `expected` objects; expected values must be
prepared independently, not copied from the measured response. Final corpus
reference cases and their review remain pending.

**Implementation:** `comparison_checks.js` validates page/detail shapes,
listing fields, available-time window, categories/conditions/price filters,
pagination, uniqueness and exact ordered response equality. `comparison_smoke.js`
requires a valid expected object, checks HTTP 200 plus response content in memory,
and emits `correct`, `incorrect` or `transport_error` by case index without
retaining response content. `comparison_runner.py` pairs exactly one request and
outcome per case index, rejects missing/duplicate outcomes and returns exit 1 for
incorrect content, 2 for invalid preparation. The case input format changed;
the k6 README and command index describe it. This remains loopback-only and is
not an NFR or performance measurement.

**Checks:** Three checker tests exercise correct results, changed IDs/fields,
unavailable or wrongly filtered rows, pagination, duplicates, malformed content,
non-200, detail identity and reversed result order. Three focused JS test files
passed on Node 26.8.2; three Python runner tests passed with warnings as errors;
Black formatted both changed Python files. Real k6 against a temporary synthetic
loopback server returned `correct`/exit 0 for the expected body and `incorrect`/
exit 1 when the server returned a wrong title with HTTP 200. Server and temporary
metrics were removed. `git diff --check` passed. No real dataset oracle, real
provider, deployed A/B or cloud measurement was used; Node 24 remains pending.

**Remaining:** Independently prepare/review actual dataset-bound expected cases,
test the checks against those and both real deployed paths, and preserve final
Step 2/3 integration obligations. Step 4 local checkpoint awaits verification.

### 2026-11-01 14:14:45 UTC — EXP-02 Step 3 revised runner integrated smoke

**Direction:** User requested continuation after confirming that product search
uses Hybrid and the frontend sends a single listing-search call.

**Check:** Restarted the documented disposable synthetic inspection app on
127.0.0.1:5175; its startup action sweep passed. Invoked the registered Python
runner with browse and explicitly Hybrid search cases. Its actual k6 preflight,
synthetic buyer login and k6 run completed; it reported one HTTP 200 for each
case, with correctness unchecked and measurement false. The app was stopped
and exited 0. No response oracle, cloud, real provider, or performance run.
`git diff --check` passed. Node 24 and final k6 provenance remain pending.

**Next:** User verification of the revised runner; real deployment/session and
Step 2 A/B parity remain pending. Step 4 is the separately verified correctness
work; Step 5 sets the scheduled load profile.

### 2026-11-01 14:09:02 UTC — EXP-02 Step 3 Hybrid mode and preflight

**Finding and correction:** The generated API contract and Listings store use
Keyword when `search_mode` is omitted. Earlier local helper tests permitted a
search case without a mode, which could have exercised the wrong behavior. The
case builder now requires `search_mode: "hybrid"` explicitly and refuses absent
or Keyword modes. Prior integrated smoke cases explicitly selected Hybrid; they
remain valid for their recorded route/status scope.

**Runner behavior:** Before requesting the synthetic inspection login, the Python
runner invokes `k6 inspect` with a non-secret placeholder session. k6 initializes
and validates the entire case list without sending requests. Invalid cases are
refused before session creation. The real cookie is obtained only after preflight
and kept in the child environment for the local run.

**Checks:** Three Python tests passed (`pytest tests/evaluation/test_comparison_runner.py
-q -W error`), including refusal before login. Eleven focused JS tests passed with
approved loopback socket access. Actual k6 inspect accepted an explicit-Hybrid
case and rejected a missing-mode case; the runner returned exit 2 for the latter
while no inspection app was running. Black formatted the two changed Python files;
`git diff --check` passed. Node was 26.8.2; pinned Node 24 remains pending. No
cloud, live app, performance run or new integrated-session claim occurred.

**Next:** Recheck the modified runner with the integrated synthetic app; response
content, final workload and real deployed/session paths remain pending. User
verification of this checkpoint is pending.

### 2026-11-01 14:04:51 UTC — EXP-02 Step 3 Python local runner

**Direction and change:** User verified the previous checkpoint. Added
`scripts/evaluation/k6/comparison_runner.py`, a bounded Python orchestrator for
the existing k6 scenario. It accepts case JSON on stdin, permits only the three
documented loopback inspection ports, obtains a synthetic buyer session from the
inspection app in memory, runs the explicit k6 binary in a minimal environment,
and prints only route kinds and statuses marked `correctness: unchecked` and
`measurement: false`. It caps input, subprocess duration and temporary metrics;
it neither accepts real credentials nor runs cloud traffic. Updated the k6 guide
and command index with the local invocation.

**Checks:** `tests/evaluation/test_comparison_runner.py` passed 2 tests covering
session non-disclosure and refusal before login for invalid targets/counts/tools.
Black passed both Python files after sandbox multiprocessing stalled and an
approved escalated rerun. Against the disposable inspection app, the actual
Python runner invoked installed k6 for browse and Hybrid search: two HTTP 200
statuses, explicitly unchecked. The app was stopped, temporary metrics removed,
and no cookie or raw output retained. No cloud or performance run occurred.

**Remaining:** Detail has previously passed in the same k6 scenario; this new
runner still needs the full real-session and deployment path. Step 4 owns
response correctness and Step 5 scheduled arrivals. Node 24, final k6 provenance,
real A/B parity and approved measurement gates remain pending. Checkpoint awaits
user verification.

### 2026-11-01 14:02:36 UTC — EXP-02 Step 3 k6 local multi-case scenario

**Change:** `comparison_smoke.js` accepts one to ten cases via
`CLIP_COMPARISON_LOCAL_CASES`, validates all paths before sending, and executes
one sequential k6 iteration per case. The target remains loopback-only; the
session is supplied in memory, response bodies are discarded, and results are
not classified as correct. `comparison_smoke.test.mjs` covers three-case order,
invalid later cases and the case-count limit. This replaces the earlier singular
`CLIP_COMPARISON_LOCAL_CASE` input for this smoke scenario.

**Checks:** Four adapter tests passed with Node 26.8.2. With the disposable
synthetic inspection app and an ephemeral synthetic buyer session, a single
actual k6 invocation sent browse, Hybrid search and listing detail in that order;
all three returned HTTP 200. A browse preflight selected a valid synthetic listing
ID. Temporary k6 metrics were removed and the app stopped with exit 0.
`git diff --check` passed. No real provider, cloud or performance run occurred.

**Remaining:** This bounded scenario does not implement response correctness,
scheduled arrival profiles, dropped-work handling, real target/session handling,
or final evidence collection. Step 2 deployed parity and Node 24/toolchain
provenance remain pending. The checkpoint awaits human verification.

### 2026-11-01 14:00:23 UTC — EXP-02 Step 3 three-route local smoke

**Direction and target:** User verified the previous checkpoint. Restarted the
documented synthetic inspection app on 127.0.0.1:5175 with a disposable local
database, synthetic provider signing and the real local Hybrid model. This is
not the frozen reference corpus or a real-provider deployment.

**Method and result:** Obtained an ephemeral synthetic buyer session through the
local inspection login; one authenticated browse preflight supplied a valid
synthetic listing ID. Ran `/usr/bin/k6 run --quiet --out json=<temporary-file>
scripts/evaluation/k6/comparison_smoke.js` separately for browse, Hybrid search
and listing detail. Each k6 process exited 0 and recorded exactly one HTTP 200.
The cookie remained in process memory; temporary metric files were removed and
the app was stopped cleanly. No code changes or cloud calls occurred.

**Limits and next step:** The smoke verifies routing and status for three local
cases, not response meaning, scheduled mix, real provider identity or performance.
User verification is pending. The reviewed reference cases and their correctness
checks remain EXP-02 Step 4; rates and dropped-work handling remain Step 5. Step 2
real A/B dataset parity and Step 3 real-deployment session checks remain pending.

### 2026-11-01 13:58:35 UTC — EXP-02 Step 3 integrated local smoke

**Setup:** User verified the previous checkpoint. Installed verified uv 0.10.7
in temporary local storage and CPython 3.13.12 in `.tools/semantic/python`, then
synced the 24 hash-pinned Linux helper packages into `.tools/semantic/venv`.
Downloaded only the pinned ONNX model and tokenizer into `.tools/semantic/model`;
both matched the checked-in size and SHA-256 manifest. Initial sandbox DNS
failures were followed by approved network escalation. No global tools changed.

**Inference:** A first helper startup failed because the test resolved the venv
Python symlink to its base interpreter, bypassing venv packages. Retrying with
the actual venv path passed and returned a 384-dimensional synthetic query vector.

**Integrated smoke:** Started the documented synthetic inspection app on local
port 5175 using its disposable Docker/PostgreSQL database, actual app routes,
local Hybrid helper and synthetic signing/mail/images. Its startup action sweep
completed, including Hybrid queries. A Python harness obtained a buyer session
through the local synthetic-signing login and passed the cookie in memory to
`/usr/bin/k6 run --quiet --out json=<temporary-file> scripts/evaluation/k6/comparison_smoke.js`.
k6 exited 0; its temporary metrics recorded exactly one Hybrid search request and
HTTP 200. Metrics temporary directory was removed and the app stopped via Ctrl+C;
the launcher exited 0. No cookie was retained in the log.

**Limits:** Synthetic Identity/provider and disposable data are not deployed
real-provider evidence. The smoke checks route/session/status only: response
correctness, real accounts, final A/B workload and measurements remain pending.
No cloud action or NFR/architecture run occurred. `git diff --check` passed.
Node 24 and final k6 provenance remain pending.

### 2026-11-01 13:49:47 UTC — EXP-02 Step 3 integrated route preparation

**Finding:** The integrated app mounts its public API under `/api`, while the
generated OpenAPI contract describes `/listings` paths without that prefix.
The earlier local helper accepted only the contract-root form and would miss
the website-served integrated route.

**Change:** `comparison_cases.js` now validates only two explicit loopback
target shapes: a bare origin or its `/api` mount. Both `comparison_local.js`
and `comparison_smoke.js` use this shared guard. Their tests exercise `/api`
alongside remote/invalid-target refusal; no arbitrary URL path is accepted.

**Checks:** The three comparison test files passed 10 tests under Node 26.8.2
with approved loopback socket access. `git diff --check` passed. Docker engine
29.8.1 responds outside the sandbox after the sandbox denied its socket. The
integrated inspection launcher requires `.tools/semantic/venv/bin/python` and
`.tools/semantic/model`, neither of which is present on this machine. Therefore
no integrated-app/session smoke was started or claimed; the Node 24 and real
k6 integrated-path checks remain pending. No cloud or measurement run occurred.

**Next:** Prepare the project's supported pinned local Hybrid interpreter/model
and associated prerequisites, then run the bounded synthetic inspection and k6
smoke under the documented local procedure. Preserve real-provider/deployment
and dataset acceptance as separate gates.

### 2026-11-01 13:46:42 UTC — EXP-02 Step 3 installed k6 smoke

**User direction and environment:** User reports compiling and installing k6.
`/usr/bin/k6 version` reports `k6 v2.3.0 (commit/devel, go1.27.1-X:nodwarf5,
linux/amd64)`; binary SHA-256 is
`603b32fb28e5802a4a64bd053c0f2ec0d27146dfef8d803bd429abea37236960`.
This identifies the installed binary; it does not establish official release
provenance or approve the final measurement toolchain.

**Actual k6 check:** A short Python harness started a temporary loopback HTTP
server and invoked `/usr/bin/k6 run --quiet scripts/evaluation/k6/comparison_smoke.js`
with an in-memory synthetic cookie and a Hybrid search case. k6 exited 0; the
server observed exactly one expected `/listings?q=desk&search_mode=hybrid` GET
and the synthetic cookie. The server stopped after the check. The first sandbox
socket probe failed `EPERM`; the actual local test passed with approved escalation.
No real app, authorized real account, response correctness, cloud, timing claim,
or NFR/architecture measurement was involved. `git diff --check` passed.

**Remaining:** Check/record final toolchain provenance, Node 24 and a real
integrated-app session; complete the multi-case workload, correctness, arrival
profiles, telemetry and run manifests in their assigned steps. Step 3 remains
partial and requires verification.

### 2026-11-01 13:29:30 UTC — EXP-02 Step 3 k6 adapter preparation

**Direction:** User requested continuation and the existing k6/JavaScript plus
Python orchestration split. Base `f816f66`; `task/exp-02-workload`.

**Change:** `comparison_smoke.js` is a single-iteration k6 scenario using the
contract path builder, a loopback-only target and an out-of-band in-memory
session cookie. It does not follow redirects or declare HTTP status to be correct.
It records only a preparation response classification; it is not the measured
workload. `comparison_smoke.test.mjs` substitutes k6 APIs to check single request,
session forwarding and refusal of non-loopback targets and unsafe inputs.

**Checks:** `node --test scripts/evaluation/k6/comparison_cases.test.mjs
scripts/evaluation/k6/comparison_smoke.test.mjs` passed both files with Node
26.8.2; `git diff --check` passed. The adapter tests use mocked k6 APIs; no actual
k6 process, HTTP, real session, cloud call or measurement ran. No k6 binary is
on PATH; the existing pinned installer supports macOS ARM64, not this Linux
x86_64 environment. Node 24 and actual k6 runtime verification remain pending.

**Remaining:** Register and validate a supported local k6 toolchain and safe
session/run entry point; exercise the real app and complete response correctness,
scheduled load, telemetry and final cloud gates in their assigned steps.
EXP-02 Step 3 remains partial, pending user verification.

### 2026-11-01 13:27:01 UTC — EXP-02 Step 3 bounded local batch

**Direction:** The user verified the preceding partial checkpoint and directed
continuation. Base revision `f816f66`; branch `task/exp-02-workload`.

**Change:** `comparison_local.js` now provides `runLocalPreparation`, which
validates a whole batch before sending, permits one to ten sequential loopback
requests, stops on a transport error and records only route kind, HTTP status and
`correctness: unchecked`. Its result explicitly marks `measurement: false`.
Sessions and response bodies are not returned in the result. The existing
single-request helper carries the in-memory cookie and rejects remote targets.

**Test:** `node --test scripts/evaluation/k6/comparison_cases.test.mjs
scripts/evaluation/k6/comparison_local.test.mjs` passed six tests under Node
26.8.2. A synthetic loopback HTTP server verified browse/search paths, session
forwarding, a 401 outcome and server shutdown. Invalid later cases and batches
over ten were refused before requests. The first sandboxed attempt failed with
`listen EPERM` on 127.0.0.1; the same test passed with approved escalation.
`git diff --check` passed. No real app session, cloud call or performance run.

**Remaining:** This is a bounded preparation batch, not the scheduled k6
workload or a correctness oracle. Actual integrated app/session execution,
response checks, project-pinned Node 24, real deployment, and A/B checks remain
pending. Step 3 awaits verification before continuing.

### 2026-11-01 13:25:12 UTC — EXP-02 Step 3 local transport preparation

**Purpose and scope:** Prepare a single local read using a supplied session,
without enabling remote or cloud execution. This is partial EXP-02 Step 3.

**Changes:** `scripts/evaluation/k6/comparison_local.js` combines a reviewed
case path with an in-memory session cookie and an injected transport. It accepts
only `http://127.0.0.1:<port>`, rejects line breaks in the session, refuses
redirects and returns the transport response without marking it successful.
`comparison_local.test.mjs` exercises one search request and checks that unsafe
targets and headers fail before the transport runs. The existing case builder is
in `comparison_cases.js`; no session value is stored by this adapter.

**Checks and environment:**
`node --test scripts/evaluation/k6/comparison_cases.test.mjs scripts/evaluation/k6/comparison_local.test.mjs`
passed both test files using Node 26.8.2 on Linux x86_64. `git diff --check`
passed. The transport was simulated: no HTTP request, real session, k6 run or
cloud call was made. Project-pinned Node 24 verification remains pending.

**Checkpoint:** Partial result reported to the user; Step 3 remains open. The
complete k6 scenario, authorized real session, response correctness checks and
deployed/cloud integration are pending. Next, verify this partial result and
finish the actual local workload in the current step.

### 2026-11-01 13:14:04 UTC — EXP-02 preparation

**Direction:** The user directed Rahul to proceed, relayed Mohit's confirmation
that the dataset exists, and accepted the explanation of the two deployment
configurations. A is ECS-only; B routes selected reads through Lambda.

**Dataset evidence:** The frozen manifest and retained cloud-load receipt agree on
seed 42, 5,000 users, 1,000 listings, and logical fingerprint
`sha256:7efd142e11c3e8555e1aa08603cbf8dff07de5d74412ccde3c39869b9334ab98`.
The frozen manifest's SHA-256 was
`fcb86edb0412f39cda77cf65be87a2e963783f95842f5080ec0456c0b64f21b4`,
matching the recorded release hash. The receipt reports 1,000 images and 800
available listings. See [frozen release](domain/next-06/frozen-dataset.json),
[cloud load](domain/next-06/transfer/cloud-load-20261031/result.json), and
[cloud/native snapshot](domain/next-06/transfer/dataset-snapshot-20261031/result.json).
This was a local evidence check, not a fresh cloud inspection or DATA-READY
acceptance. The deployed A/B database, indexes, settings and model still require
verification once both paths exist.

**Implementation and checks:** Added `scripts/evaluation/k6/comparison_cases.js`
to build contract-shaped browse, Hybrid search and listing-detail paths, and
`comparison_cases.test.mjs` to check the generated API operation names and
rejection cases. `node --test scripts/evaluation/k6/comparison_cases.test.mjs`
passed with Node 26.8.2; rerun using project-pinned Node 24. The code does not
send requests or handle sessions. No cloud action or performance measurement ran.
See the [EXP-02 work-log entry](../status/work-log.md) for the checkpoint and
pending integration.
