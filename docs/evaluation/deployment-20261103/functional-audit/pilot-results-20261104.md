# Cloud pilot results — 2026-11-04

All six pilot runs are complete. Current public routing is ECS default only;
two API tasks and the separate pool are healthy. No NFR or formal comparison
was started. Suraj explicitly holds further traffic and defers merging until
the experiment/optimization review. PR35 remains unmerged; application images,
resource sizes, role limits, Lambda memory and SQL are unchanged.

## Exact results

Latency columns below cover **correct responses**, using the bound monotonic
client timer. Failed HTTP responses, client timeouts and generator drops remain
in separate counters and immutable raw output. These are two-minute50rps
mixed-read pilots after60seconds10rpswarm-up; no NFR acceptance is claimed.

| Configuration / repetition | Correct / issued measured | HTTP errors | Client timeouts | Generator drops | p50 ms | p95 ms | p99 ms | Pilot state |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A / 1 | 6000 / 6000 | 0 | 0 | 0 | 176.58 | 355.38 | 564.16 | passed pilot gates |
| A / 2 | 6000 / 6000 | 0 | 0 | 0 | 174.64 | 326.38 | 413.01 | passed pilot gates |
| A / 3 | 6000 / 6000 | 0 | 0 | 0 | 141.09 | 234.26 | 313.41 | passed pilot gates |
| B / 1 | 5996 / 6000 | 4 | 0 | 0 | 154.50 | 268.50 | 361.17 | passed pilot gates |
| B / 2 | 5992 / 6000 | 8 | 0 | 0 | 133.42 | 235.75 | 366.97 | passed pilot gates |
| B / 3 | 5793 / 5994 | 201 | 0 | 7 | 167.82 | 509.07 | 1553.18 | invalid delivery |

A warm-ups each completed600/600correct. B1warm-up:560correct,35HTTP502,
five client timeouts out of600issued. B2/B3warm-ups each600/600correct. All six
raw hashes match execution receipts. A1reporting initially rejected its existing
evidence directory; the corrected separate report verifies provenance without
changing or repeating raw data. Launch-time zero-request failures are retained.

## What the failures establish

B1fresh metrics show39Lambda throttles matching39client502s:35warm-up/four
measured. Ten environment startup observations took3842.74–5170.17ms. Five client
timeouts occurred during initial startup. No request-ID correlation was retained,
so matching counts/time windows are aggregate attribution rather than a proven
one-to-one mapping. B2has eight client502s/eight AWS throttles, zero invocation
errors and zero initialization reports. B3has201client502s/201AWS throttles,
zero invocation errors and zero initialization reports. Peak concurrency reached
the account limit10. B2/B3reused all ten observed log streams from B1.

Therefore startup contributed to the initial cold pressure, but initial startup
does not explain the warmed B2/B3rejections. Those show concurrency-related
throttling under this ten-slot account limit. Standard metrics do not directly
measure Lambda CPU utilization/cgroup throttling; no direct CPU-throttle claim
is made. B2platform duration p95was113.87ms/max334.48ms; B3maximum317.69ms.
Peak Lambda memory in B1/B2was511/514MB out of2048MB, with no invocation errors.
Database CPU reached46.24%in B1and45.53%in B2one-minute samples; pool CPU peak
was6.29%in B1. RDS CPU credits remained above124with zero surplus balance/charges
in delivered samples. Database connections stayed at most20in B2/B3observations,
and no long lock waits or service-loss safety stop occurred. Delayed minute
samples do not exclude brief spikes or establish unseen Lambda CPU behavior.

B3client all-outcome request timing p99wasabout1.615seconds/max3.373seconds,
despite maximum recorded function execution318ms. Much of the increase was
outside the recorded invocation. Generator drops all occurred at18:11:24UTC
(23:41:24IST), while its initial100worker allocation expanded to104. This supports
a generator-capacity response to increased in-flight work; it does not prove
the source of the network/ALB delay. The phone may have left range after that
interval; Suraj is unsure. A hotspot-disconnection cause remains unconfirmed.
No long issue gap was observed (largest measured issue gap about61ms), and the
recorded request failures were502rather than transport-timeout errors in B3.

## Current validity and recommended review

Three A pilots and two B pilots pass the frozen gates. B3has5994issued plus
seven dropped arrivals, with incomplete delivery/accounting against6000planned.
The preserved report exposes the boundary mismatch; it cannot be relabelled a
valid pilot merely because its successful share exceeds95%. All-three B
criterion is unmet, so100%Lambda is not frozen and no winner is selected.

Warm-up is preparation, not three independent cold-start samples. Label B1cold
and B2/B3warm reuse; keep cold evidence separate and count any measured-window
cold events. No function reset is needed merely to make every warm-up cold.

Next actions require review/approval: keep the generator network stable; inspect
or preallocate enough workers for transient in-flight demand; any capacity-profile
change must be recorded consistently for both architectures. Then rerun the
invalid matched pair under an approved amendment, or restart the pilot matrix if
material settings change. Preserve this entire batch. Consider a lower paired
comparison burst as the already documented fallback, identically for A/B, if
the10-slot account limit remains; NFR03stillrequires50rps. Do not increase memory,
change resources, rerun traffic or start NFRs automatically. Profile startup
imports/model initialization only under an approved next batch; faster startup
will not automatically solve warmed concurrency spikes.

## Exact evidence locations

Private summary:
`/home/suraj/src/.clip-private/pgbouncer-20261104/pilot-preparation/pilot-results-summary.json`.

Per-run raw/receipt/report files:
`/home/suraj/src/clip-planning-main/.tools/pool-pilot-repair/runs/RUN_ID/`
with run IDs`pilot-261104r-base-r1/r2/r3`and`pilot-261104r-l100-r1/r2/r3`.
A1uses`report-verified.json`; its original`report.json`remains unchanged.

Under the private preparation directory: per-run`RUN_ID-monitor-v4/`contains
numeric monitoring, CloudWatch/pool captures and Lambda REPORT evidence. See
`lambda-first-run-failure-investigation.json`, `warm-lambda-error-analysis.json`,
`pilot-network-analysis.json`, `cpu-memory-credit-diagnostics.json`, and
`batch-execution-lambda-final.json`for the final stop/ECS rollback. Raw records
are read-only. No credentials, message bodies or mailbox addresses enter reports.

Reporting repair remains local on task/pilot-launch-repair: validate_run_plan
can explicitly validate an existing completed run; its default still rejects
overwriting evidence. real_run_evidence.py uses that reporting mode. The new
completed-evidence regression checks valid provenance, overwrite rejection and
raw tamper rejection. Two focused Python tests and Black pass after correction.
No additional commit/push/merge or cloud change was performed for that repair.
