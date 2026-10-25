# Local k6 load-runner preparation — SE-01 Step10

This tool runs bounded loopback pilots only. It cannot execute the full-rate NFR
profiles or accept SE-CORE/DATA-READY/NFRs. The final target/auth/data/image/index/
telemetry/resource/cost/repetition plan remains a separately approved real gate.

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
(k6 code1050), missing/interrupted completion, negative clock elapsed and generator
drops/shortfall stay visible. Completion marker plus exit0and complete valid
warm/measured cohorts are required for valid_preparation_run. nfr_accepted remains
false in every report. Absence of errors is not an NFR pass.

Latency is Date.now elapsed around the full synchronous HTTP call (including
connection/DNS/TLS where applicable), not http_req_duration alone. Resolution is
milliseconds and wall-clock changes can affect intervals; negative intervals mark
the run invalid. Final clock/timing method still needs the real run manifest.
Actual raw k6 HTTP phase metrics are retained for diagnosis. R7 interpolation
produces p50/p95/p99 for all completed and successful samples separately; empty is
null, not zero. Successful throughput means cohort completions divided by its
scheduled duration, including bounded drain. NFR01's successful denominator and
NFR02's all-issued eligible denominator remain explicit; failures are not removed.
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
