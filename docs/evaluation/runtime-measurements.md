# Runtime measurement amendment — 2026-11-04

Suraj approved finishing the experiment tooling before publishing the optimized
Lambda image, then three Lambda-only pilot reruns and a hold for results review.
The approved image/source is frozen at `7e88f84`; these tooling changes run on the
generator and do not need to be embedded in the application image. The existing
safe application logs and `X-Request-Id` response header provide correlation.
No NFR, formal comparison, runtime reset, fault or restore is authorized by this
amendment alone. No commit, push or merge is included in this checkpoint.

## Changed code and how it connects

| File | Purpose and behavior |
|---|---|
| `scripts/evaluation/k6/request_correlation.js` | Reads only the server request UUID header and hashes it; missing/rejected responses stay unattributed. Never copies cookies, URLs or other headers. |
| `comparison_load.js`, `exp05_pilot_load.js`, `nfr_load.js`, `nfr03_load.js` in that directory | Add a scenario-local sample index and hashed response correlation after stopping the monotonic timer. Offered rate, timeout, retries and correctness rules remain unchanged. |
| `scripts/evaluation/k6/comparison_stage_run.py` | Includes the new dependency in immutable comparison workload bundles. |
| `scripts/evaluation/k6/real_run_coordinator.py` | Includes it in every other bundle. New formal/NFR01–03 execution also requires a recent exact-target fresh-runtime receipt and checks actual ECS task IDs/Lambda revision; pilot runs retain observed reuse. Execution receipts bind preparation evidence. Historical completed runs remain reportable. |
| `scripts/evaluation/runtime_observations.py` | Reads bounded CloudWatch pages, keeps only safe IDs/status/timing, and joins real client/server IDs. Reports warm-up and measured distributions separately, including unattributed failures. Cold client samples need one completion between matching platform START/REPORT boundaries with explicit Init Duration. Ambiguous boundaries or missing initialization remain unknown. |
| `scripts/evaluation/fresh_runtime.py` | Separately approved reset observer: replaces only the two API tasks and, for B, updates an inert Lambda marker. Waits for new tasks and their exact healthy target IPs; preserves partial observations on failure. Does not restart hosts/pool, change images/sizes/SQL or send load. Readiness does not itself prove cold observations. |
| `scripts/evaluation/performance_campaign.py` | Freezes coverage-first NFR order, three NFR01/02/03/05 repetitions per applicable configuration, then three matched main cycles in A/B, B/A, A/B order. Formal measured windows remain 300 seconds; hosts/database/pool caches remain unchanged. Rejects stale, incomplete or wrong-run reset receipts. |
| `request_correlation.test.mjs`, `comparison_load.test.mjs`, `nfr_load.test.mjs` in the k6 directory | Exercise privacy and missing headers, and wire the real new helper into existing fake-transport/timer checks. |
| `tests/evaluation/test_runtime_measurements.py` | Tests privacy, exact correlation and ambiguity, separate phases, immutable raw bytes, complete campaign ordering, invalid reset receipts/approvals and A/B reset orchestration using local AWS doubles. |

The canonical NFR design and NFR01/02/03/05 manifest templates now record the
approved repetition/start-state policy. The actual future run plans must still
bind concrete targets, caps, credentials, action approvals and result paths.

## Checks and limits

The evaluation suite passed 448 tests with 11 skipped. Two subsequent reset
orchestration cases passed; the final affected selection passed 30 tests. All 18
Node test files pass through the evaluation checks. Formatting and whitespace
checks pass. Actual pinned-k6 `inspect --include-system-env-vars` loads the new
three-run pilot profile with the expected two scenarios and sends zero requests.
Initial sandbox socket restrictions, a missing Node PATH, fake-port wiring and
inspection environment flags were corrected; they are tooling setup failures,
not application capacity measurements.

This does not prove the cloud NFRs pass. The current target group's 300-second
ECS draining can extend reset transitions; preparation allows 900 seconds. A
change to draining needs its own cloud approval. Deployment draining and manual
NFR06 task-loss recovery must be investigated separately rather than assumed
to have the same timing.

## Future approved-run interface

Prepare and hash a reset plan using `fresh_runtime.build_plan(target_path,
target_sha256)`. Only a separate exact expiring reset approval enables:

```bash
.venv/bin/python -m scripts.evaluation.fresh_runtime RESET_PLAN \
  --approval RESET_APPROVAL --output NEW_RECEIPT --execute
.venv/bin/python -m scripts.evaluation.k6.real_run_coordinator \
  --plan RUN_PLAN --approval LOAD_APPROVAL \
  --fresh-runtime-receipt NEW_RECEIPT --execute
```

Use `performance_campaign.build_campaign(prefix)` offline to produce the frozen
order, then bind each entry to canonical per-run plans and the applicable
observers. It is an order/preparation helper, not an unattended cloud campaign
executor. Later overnight execution still needs its bounded action package and
robust resumption/stop handling; do not treat this helper as that approval.

## Integration of reusable measurement tools

The runtime integration includes the reusable evaluation tools and their tests.
`campaign_runner.py` journals each run and serializes execution; measured failures
remain results and unsafe conditions stop the queue. `keep_awake.py` owns a
temporary sleep-prevention request without editing the machine's power plan.
`observer_journal.py` preserves incremental recovery/restore observations, and
`lambda_billing.py` captures numeric billed usage with hashed invocation IDs.
These tools neither approve a cloud action nor establish an NFR outcome.

Fresh-runtime preparation matches healthy ALB instance/host-port targets to the
new API tasks. Preflight can wait for bounded transient DNS/provider errors or a
scheduled database backup, while requiring the same strict target checks before
traffic. Measured HTTP requests have no retries. The concurrency guard records
provider failures separately from actual concurrency-setting drift.

NFR-03 optionally adds version-2 sale-listing creation to the existing smooth
operation schedule. Fixture inputs bind six confirmed photo uploads and future
availability: one warm-up and five measured creations replace browse operations
without changing the total rate of 50 requests per second. Unique operation IDs support timeout
reconciliation. This scheduled-listing subcase does not establish immediate
publication under concurrent writes; photos are prepared outside timed traffic.
Legacy version-1 profiles remain supported.

The chat observer validates its target/session receipt, holds the selected active
browser mode throughout capture and passes an explicit background run ID. The
background entry point enforces its scheduled request boundary. Recovery counts
only healthy replacement tasks actually registered at the API target group, and
uses an absolute deadline beginning before the task-stop API call. Restore
validation rejects unsafe paths, handles the SDK's actual missing-instance error,
preserves a pre-action journal and records only sanitized error codes.

Terraform exposes the reviewed 30/300-second drain settings and permits retaining
idle Lambda resources while selected-read routing is disabled. Isolated restore
smoke removes the source pool endpoint and replaces all database connections.
The evaluation reset marker is excluded from unrelated Terraform updates; all
functional environment settings remain managed.

Formal comparison and NFR execution records are being retained separately until
the evaluation is complete. This integration includes the application, build
changes, optimization/pilot history and reusable tooling, without publishing
those unfinished execution reports. No deployment or load starts on merge.

Local integration validation: Python 2,576 passed/180 skipped (owned native pool
tests enabled), data 331 passed, web 504 passed/3 skipped, Conversations 184 passed,
36 Terraform mocks, 16 strictly typed tooling modules, contracts/boundaries, 35 local
database safety cases, clean/repeated migrations and Gitleaks passed. The final Node entry suite passed all 63 tests after a test was made
independent of private campaign fixtures. An ambient native-test flag was removed before continuing the data
checks; no runtime safeguard was weakened. Hosted CI awaits PR creation.
