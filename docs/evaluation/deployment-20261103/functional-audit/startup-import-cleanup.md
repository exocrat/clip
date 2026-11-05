# Bounded startup import cleanup — local verification

Suraj requested an easy startup optimization before further cloud measurements.
Application composition previously imported Conversations routes, Wanted/Saved
routes/stores and notification runtime even for the Listing-only Lambda.

`apps/api/app/application.py` now loads those capabilities only when composing
or starting the full application. The notification composition entry point stays
injectable through a small lazy context wrapper. Full ECS routes load before
serving, and notification initialization still completes within lifespan. Lambda
never installs these capabilities; its first search does not inherit their work.
Authentication, role/key audits, model/hash validation, search scoring and model
initialization remain unchanged. No state or cloud configuration is modified.

`apps/api/tests/test_lambda_startup_imports.py` checks in a fresh process that
Listing-only composition excludes the full modules and full startup loads them.
Existing read-only Lambda, real disposable-Postgres Identity/application and
notification lifecycle checks pass:23existing tests plus the new import test.
A first sandboxed attempt had16Docker-permission setup errors; the complete
23-test selection then passed with Docker access. Focused follow-up8passed;
Black and diff whitespace checks pass. No broad new CI run or publication.

Five alternating fresh-process comparisons using the same local interpreter:

| Measurement | Before | After |
|---|---:|---:|
| Median application import | 587.19ms | 505.09ms |
| Median reduction | — | 82.09ms / approximately14% |

All samples are retained in
`/home/suraj/src/.clip-private/pgbouncer-20261104/pilot-preparation/startup-import-optimization.json`.
This measures local application imports only, not AWS cold starts, model/helper
initialization, network or complete request latency. The initial single import
time trace was sensitive to cache/run conditions; the repeated alternating
comparison above is the estimate. No claim that full startup or warm throttling
is solved. The model helper's artifact checks and ONNX initialization need their
own profiling before proposing a larger change; skipping checks or postponing
work into the first search would not establish an optimization.

The change is local and uncommitted. No new image build, deployment, resource
upgrade, pilot/NFR/formal traffic, commit, push or merge occurred. Suraj's hold
after pilots and instruction to defer merging remain active. A deployed startup
benefit requires reviewed image artifacts, exact deployment approval, functional
checks and separately approved affected measurements.

## Additional bytecode optimization and next batch

Suraj authorized quickly/safely checking additional startup work and proceeding
toward deployment plus Lambda-only pilot reruns. Keep ECS pilot results; do not
start NFRs or merge. The current image has zero cached bytecode for105app sources
and2926helper-package Python sources. A local derived image precompiled them
without changing libraries, source or model. In three alternating fresh offline,
read-only, one-core container comparisons, median helper startup was462.34ms
before and273.38ms after (188.96ms reduction). First samples were noisier; all
samples are retained. Exact384-dimensional test-query vectors matched across all
six executions, and the original model/hash/runtime-pin checks ran normally.
This does not measure AWS startup or prove that warm concurrency failures vanish.

`apps/api/Dockerfile` now compiles application source during build with checked-
hash caches. `apps/api/Dockerfile.hybrid` compiles pinned helper libraries and
its three3.13-compatible helper source files with the correct interpreter. Cache
hash validation rejects changed sources; runtime bytecode writes stay disabled.
API dependency bytecode was already compiled by uv; it is not a new change.
The offline local probe used the current exact dependency/model image. No model
preoptimization, validation removal, asynchronous permission bypass or resource
upgrade is included.35focused lifecycle/import/image-builder/evidence checks pass.

The next release must preserve the current live ECS/pool resources, use a new
immutable Lambda image, verify real responses/auth and run only three Lambda
pilot repetitions. Preparing300rather than100generator workers per scenario
(maximum300unchanged) is proposed to avoid allocation delay during temporary
latency spikes; this changes generator settings and needs explicit approval.
Prior ECS baselines remain historical pilot evidence at their recorded source
and generator settings; do not present new B reruns as an unchanged matched A/B
formal comparison. Before formal measurements, freeze the final source/artifacts
and consistent A/Bgenerator settings. Keep startup/warm-up failures and all
invalid earlier runs. Deployment, traffic/cost/window and cleanup/rollback plan
will be presented after immutable images and local checks are ready.

## Deployed rerun checkpoint — 2026-11-04

Frozen source7e88f84and imagef4ab2e were published and deployed under the exact
approved Lambda-only plan. The three replacement pilots all meet their frozen
criteria, but still contain37/65/4HTTP502 matching AWS throttles. The first
standalone request took7585ms; no controlled startup improvement is claimed.
ECS routing is restored and further NFR/formal runs are held. See the
[complete results and exact paths](startup-pilot-results-20261104.md) and
[revised measurement tooling](../../runtime-measurements.md).
