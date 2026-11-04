# EXP-05 cloud pilot — exact batch awaiting approval

Account335523638354, Mumbai, profile/operator surajs2. Prepared2026-11-04
17:11UTC. This is a pilot plan; no pilot or formal measurements have started.

Use the current two API tasks, existing-host PgBouncer, existing RDS, reviewed
images and 2048-MiB/five-second Lambda with ten unreserved slots. Keep imports
and model startup optimization open for later profiling; no tuning during runs.

## Six sequential runs

Three ECS-only baselines, then three100%Lambda selected-read repetitions. Each
uses60seconds at10requests/s, five-second drain,120seconds at50requests/s and
up tofive seconds final drain. Mix50%browse/30%Hybrid/20%detail, same cases and
rotation for every pilot, no retries, five-second client timeout. This schedules
39,600 workload requests:36,000 measured and3,600warm-up, plus at most100normal
preflight/session requests. Per scenario100preallocated/max300VUs; the separate
coordinator watchdog is400seconds per run. Request scheduling remains190seconds
at most; the larger watchdog is an administrative failure bound.

Before A, delete only the captured selected-GET ALB rule so selected reads use
the existing ECS default. After three passing A pilots, recreate the exact same
selected GET conditions/actions at priority10 for B. Preserve the initial B
plans; bind new B copies only to the returned rule ARN and dependent hashes,
with normal source/target preflight checks. At completion or stop, delete only
the pilot selected rule, leaving website traffic on ECS. Record the deliberate
Terraform rule-state drift; reconcile before another apply. Never replay an old
saved plan. No service restart, image, resize, permission or SQL change.

## Limits and decisions before results

Maximum60minutes after approval, incremental gross cost capUSD2 within project
USD200. ExpectedUSD0.50–1.50including existing resources during the window,
bounded Lambda execution, monitoring/transfer and contingency; this is an
estimate before credits and tax reconciliation. Gross account billing for
October1–November4currentlyUSD31.5397798548; retainUSD5delayed-billing allowance.
Billing is delayed, so bound spending operationally through time/traffic/size.

Stop for60or more database client connections; database CPU90%or more across
two latest one-minute averages; DB freeable memory below64MiB; lock wait over
three seconds; generator available memory below512MiB; service-count/concurrency
drift; lost monitoring; raw output over90MB/run; or time limit. Monitor DB every
five seconds and AWS health/metrics every15seconds. CloudWatch delivery is delayed
and can miss short spikes; raw client outcomes and pool counters remain evidence.

After each run require all6,000measured arrivals issued, zero generator drops,
complete accounting, at least95%correct responses, zero incorrect-content outcomes,
verified timing provenance and ECS/database/Lambda/pool telemetry where applicable.
Preserve errors/timeouts/throttles and report all latency distributions. A failed
criterion stops the next run. No automatic rerun or alternate weight. Three
passing B repetitions support reviewing100%for selection; they do not accept an
NFR or authorize the formal comparison. Separate NFR01/02/03profiles remain needed.

## Inputs and evidence

All six run plans passed offline source/case/parity/binary validation. The exact
monotonic k6 build and current extension match; the bridge check passed. Current
read-only database check:7client connections, max78/reserved3, all1003embeddings
ready,900available listings and index fingerprint matching the frozen plan.
Pilot-gate fixtures accepted valid input and rejected wrong content, success
below95%, dropped work and absent database telemetry. Wrapper scripts compile.

Private exact approval package:
`/home/suraj/src/.clip-private/pgbouncer-20261104/pilot-preparation/batch-plan-v2.json`
SHA256`71fc6a997985425887655fd658abb17391979948502dd1124dc4b7489851e703`.
It binds the run index, six plans/targets/profiles and these temporary execution
helpers: `/tmp/clip-run-cloud-pilot-batch.py` serializes approved routing/runs and
restores ECS; `/tmp/clip-pilot-monitor.py` records numeric headroom and requests
stops; `/tmp/clip-pilot-review-gates.py` evaluates fixed post-run criteria.

Raw results/receipts/reports go into
`/home/suraj/src/clip-planning-main/.tools/pool-pilot/runs/RUN_ID/`.
Monitoring, routing receipts and batch summary go under the private preparation
directory, one subdirectory per run. Raw output becomes read-only; reports are
separate. No session value is stored in result files or command arguments.
Approval extends only this pilot's runtime window; existing pool24-hour/USD2
approval remains separate. This plan requires the separate live-load/routing
approval mandated by CONTRIBUTING.md. The previous50-request smoke approval
cannot cover39,600pilot requests or extend its17:23UTCdeadline.

## First launch outcome and local repair — 17:19 UTC

The first coordinator execution exited with k6status107after0.20seconds,
zero raw samples and zero workload requests. Retained base-r1 raw/receipt/report
show the failure; it is not a capacity result. The batch stopped and left ECS.
Offline inspection with the real binary and explicit environment isolated a
missing browser URL global in approvedApiTarget. The pilot environment also
omitted CLIP_REAL_RUN_SESSION_COOKIE, which would have blocked the next startup
check. Earlier inspect without --include-system-env-vars failed the runner-mode
check; that diagnostic is distinct from the actual run's recorded exit.

Local repair: comparison_cases.js validates a strict literal HTTPS DNS origin
and matching /api mount without browser globals; comparison_cases.test.mjs
covers absent URL, wrong origins, credentials, paths and unsafe spellings.
real_run_coordinator.py now passes the pilot session through the private child
environment; test_pilot_session_environment.py verifies that handoff and keeps
local mode disabled. No session appears in logs/arguments. The repaired actual
k6 script passes initialization-only inspection with a synthetic cookie, sending
no requests. Four focused Node test files and three Python checks pass; Black
and whitespace checks pass. Original failed evidence and approval expiry remain.
No cloud rerun has started; fixed source, new immutable plan hashes and review
are required before a replacement run. No application image deployment needed.
