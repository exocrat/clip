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
