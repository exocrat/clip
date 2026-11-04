# Startup-optimized Lambda pilot reruns — 2026-11-04

All three Lambda-only reruns meet the frozen pilot checks, including at least
95% correct measured requests, complete scheduled delivery, zero incorrect data,
verified monotonic timing and required telemetry. They are not NFR passes.
The operator restored ECS-only routing and stopped before NFR/formal traffic.
No commit, push or merge was performed in this increment.

## Measured results

Each run uses 60 seconds at10requests/s, then120seconds at50requests/s,
five-second client deadline and zero retries. Generator workers are preallocated
300per scenario, maximum300per scenario; AWS concurrency remains10. The table
reports latency of correct responses. Failure counts are retained separately;
all-outcome distributions and route-level results remain in each report.

| Run | Correct/issued | Correct share | HTTP502 | Timeouts | Drops | Correct p50 | Correct p95 | Correct p99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B1 | 5963/6000 | 99.383% | 37 | 0 | 0 | 169.92ms | 280.09ms | 387.68ms |
| B2 | 5935/6000 | 98.917% | 65 | 0 | 0 | 157.16ms | 261.17ms | 504.99ms |
| B3 | 5996/6000 | 99.933% | 4 | 0 | 0 | 140.57ms | 231.45ms | 289.45ms |

Measured totals:17,894correct/18,000issued;106HTTP502; zero timeouts,
incorrect-data outcomes, uncompleted requests or generator drops. All three
warm-ups completed600/600correct. Do not average the table percentiles and call
that a pooled percentile. These retain all failures, not just successful runs.

## Why failures remain

AWS recorded37,65and4throttles, exactly matching the corresponding HTTP502
counts, with zero function execution errors and peak concurrency10in every run.
This strongly supports the account concurrency cap as the source. The rejected
requests have no application request UUID, so individual rejected requests cannot
be joined to Lambda execution logs. They remain unattributed in client/server
correlation, not invented successful or cold requests.

Run1has nine explicit initialization reports: six uniquely linked to warm-up
client requests and three to measured requests. Runs2/3have zero new initialization
reports and reuse all ten log streams observed in run1. Therefore cold starts
are not the whole explanation for later throttling. Missing Init Duration by
itself never proves a warm invocation; observed stream reuse is separate evidence.
The first standalone post-rollout browser diagnostic took7585.27ms and returned
200using an explicitly labelled15-second diagnostic timeout. It exceeded the
five-second experiment deadline and is preserved. No claim that this image
solved startup or that these are three independent cold-start repetitions.

The frozen image removes unnecessary full-app imports from Lambda and compiles
bytecode at build time. Local improvements were checked, but these cloud samples
do not establish a controlled before/after startup improvement. No model/hash
checks or authentication rules were removed.

## Capacity observations

Late CloudWatch captures are retained beside initial captures because early
delivery omitted some final-minute database CPU points. CPU below refers to the
largest one-minute average over the expanded actual run window, including
warm-up and partial boundary minutes. This is not instantaneous CPU.

| Run | RDS CPU | Max observed DB client connections | Pool CPU | Lambda maximum memory | Lambda duration p95 |
|---|---:|---:|---:|---:|---:|
| B1 | 45.17% | 18 | 6.07% | 531/2048MiB | 112.64ms |
| B2 | 47.21% | 20 | 6.06% | 531/2048MiB | 114.37ms |
| B3 | 45.77% | 20 | 6.30% | 531/2048MiB | 114.14ms |

No database lock-wait or safety stop fired. Memory and connection stop limits
held. These results do not show the previous local database CPU saturation.
They also do not prove every NFR passes: NFR03has its own integrated writes,
error rules and five-minute windows. NFR01/02have their own rates/denominators;
quality, real chat display, recovery and isolated restore require their own checks.
There is no direct Lambda CPU-throttling measurement in the current telemetry;
low memory and zero execution errors do not supply such a measurement.

## Source, functional checks and current state

Lambda source7e88f84be0db6e780f407138018847ee01308f24; immutable image digest
f4ab2eaabed6f8a0dbb15a86921caecfd79c0ccbfa36e1365d40f56f37f4cf41.
Exact previously approved Terraform plan6b88d6... changed only that image and
the selected Listing GET rule. Existing API task14and pool task3were unchanged.
Normal HTTPS smoke: ten reviewed responses equal retained ECS responses,
anonymous401and hidden-listing404. No resource resize, SQL or permission change.

Earlier ECS pilots remain historical: their application revision and generator
preallocation differ. These reruns are not the final matched A/B comparison.
Before formal comparison, freeze consistent final source and generator settings
on both paths and use the approved fresh-runtime procedure.

The first monitoring launch stopped before workload, restored ECS and retained
its failure receipt. A fresh SSM tunnel was independently checked with read-only
SQL. Local smoke/plan harness mistakes were corrected without changing the app,
overwriting raw output, extending the original expiry or increasing the traffic
cap. New run IDs distinguish the actual three-run batch. The owned monitoring
SSM session was closed afterward.

Current state: selected Lambda rule absent, two API tasks and one pool task
healthy; optimized Lambda remains deployed but idle. Account concurrency still10.
NFRs/formal runs and merging remain on hold for human review. The immediate
recommendation is to review/freeze100%as the candidate, align final A/Bsource and
run the first NFR coverage round. Give NFR03early attention because the remaining
ten-slot throttling is a capacity risk; these pilot criteria do not guarantee its
stricter integrated behavior. No further optimization/resource change is automatic.

## Exact evidence locations

Public summary: this file. Runtime tooling and changed-file explanations:
[runtime amendment](../../runtime-measurements.md).

Private machine-readable final summary (no credentials):
`/home/suraj/src/.clip-private/pgbouncer-20261104/startup-rerun/attempt2/final-reconciled-summary.json`.

For each run ID `pilot-261104t-l100-r1`, `r2`, `r3`:
- Raw samples, execution receipt, report: `/home/suraj/src/clip-planning-main/.tools/pool-pilot-startup-retry1/runs/RUN_ID/`.
- Runtime report/events, monitor observations, initial telemetry and delayed `telemetry-final/`: `/home/suraj/src/.clip-private/pgbouncer-20261104/startup-rerun/attempt2/RUN_ID-monitor/`.
- Exact batch, approval, finish-routing receipt and final service check: `/home/suraj/src/.clip-private/pgbouncer-20261104/startup-rerun/attempt2/`.
- Rollout receipt, functional smoke and first diagnostic: `/home/suraj/src/.clip-private/pgbouncer-20261104/startup-rerun/`.

Raw files and receipts are owner-read-only; all three hashes were verified.
Frozen tooling hashes stayed unchanged during measurements. Final regression:
450evaluation tests passed/11skipped; all18Node test files passed; formatting
and whitespace checks passed. No new CI/merge claim.
