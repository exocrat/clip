# Higher-memory Lambda diagnostic — 2026-11-04

Suraj authorized trying the highest permitted Lambda memory through 4096 MiB
immediately. AWS rejected 4096 with a ValidationException reporting a 3008-MiB
ceiling. The exact fallback to 3008 succeeded. Same frozen image/source7e88f84,
five-second timeout, ten unreserved concurrency slots, existing API14/pool3/RDS,
permissions and environment. Only function memory changed; the identical selected
Listing GET rule was temporarily activated and removed after the diagnostic.
No preliminary Lambda smoke requests were issued by this batch. Ten new log
streams, zero reused from the previous 2048-MiB batch, and ten explicit init
reports confirm the new runtime cohort. All initializations occurred in warm-up.
The first warm-up request completed correctly in4211.37ms.

## Results

Run `pilot-261104m-l100-r1`:60 seconds at10rps, then120seconds at50rps,
five-second client deadline, zero retries,300preallocated/maximum generator
workers per scenario. This is one diagnostic, not three independent memory
comparison repetitions or an NFR result.

| Phase | Correct/issued | HTTP502 | Client timeouts | Generator drops | Correct p95 | Correct p99 |
|---|---:|---:|---:|---:|---:|---:|
| Warm-up | 572/600 | 28 | 0 | 0 | 520.66ms | 4251.17ms |
| Measured | 5946/6000 | 53 | 1 | 0 | 496.18ms | 1497.17ms |

No incorrect-data outcomes occurred. Measured correct share99.1% meets the
existing >=95% pilot criterion, and all frozen delivery/timing/telemetry gates
pass. However, the intended improvement of eliminating failures was **not**
achieved. Retain all warm-up failures, measured502s and the timeout.

AWS recorded81throttles, matching28+53HTTP502, peak concurrency10and zero
Lambda execution errors. Initialization durations3248.79–4289.96ms are separate
from sustained execution. Platform invocation duration mean47.94ms,p95110.99ms,
p99144.22ms,max539.35ms. The previous 2048-MiB runs had platform p95about
113–114ms. These observations do not demonstrate a material execution-time gain
or establish a controlled before/after causal estimate.

Across5946matched measured responses, p95of client elapsed minus application
elapsed is439.74ms and p99is1439.96ms. This difference includes network,
connection/TLS setup, ALB/invocation overhead and other work outside application
request processing; it does not prove the hotspot caused throttling. CPU alone
cannot be assumed to remove that time. The cause of the individual client
timeout is not established by these aggregate metrics.

## Current state and next decision

ECS-only routing restored; two API tasks and one pool healthy, task definitions
unchanged. Lambda remains idle at3008MiB for result review. Its image, revision
and memory were checked before and after the run. The monitoring tunnel conflict
was resolved by stopping verified owned orphan processes and using local15435;
read-only SQL was verified before workload. The trial's remote SSM session and
local plugin were both closed at the end. Raw hashes and frozen tooling hashes
match. No source-code change, new image, resource creation/resize outside Lambda
memory, SQL, permission change, commit, push, CI or merge in this increment.

The trial records the temporary SDK-applied memory setting explicitly. If3008
is retained, the canonical Terraform memory validation (currently capped2048)
and selected tfvars must be aligned before another Terraform apply/formal freeze.
This is documented trial drift, not authorization to replay an old saved plan.
The approved USD1allowance is a cap, not a final billing figure.

Do not infer a required NFR failure or pass from this read-only50rps diagnostic.
NFR03has a prescribed integrated50rps workload; its mix routes35selected
Listing reads per second to Lambda, with the other15operations on ECS. It needs
its own full-duration evidence, as do NFR01/02and the remaining NFRs. Formal
comparison high-load choices must be declared for both architectures before
formal results, not changed silently after unfavorable observations. A separate
AWS load generator could reduce external client-network variability, but its
benefit against throttling is unproven and provisioning needs its own approval.

## Exact evidence

- Final structured results: `/home/suraj/src/.clip-private/pgbouncer-20261104/memory-trial-20261104/final-summary.json`.
- Plan, memory-quota rejection, activation and rollback receipts: `/home/suraj/src/.clip-private/pgbouncer-20261104/memory-trial-20261104/`.
- Raw samples, execution receipt, profile-bound report: `/home/suraj/src/clip-planning-main/.tools/pool-pilot-memory/runs/pilot-261104m-l100-r1/`.
- Monitor, runtime correlation, initial/delayed telemetry: `/home/suraj/src/.clip-private/pgbouncer-20261104/memory-trial-20261104/pilot-261104m-l100-r1-monitor/`.
- [Previous 2048-MiB reruns](startup-pilot-results-20261104.md).

All evidence remains separate from the previous batch. No NFR/formal traffic
started; hold for human review remains.

## Read-only arrival/concurrency reconstruction

Using retained request hashes and same-stream platform START/REPORT boundaries,
5882of5946successful measured responses could be bound unambiguously to an
invocation;64ambiguous matches were excluded. Phase selection uses request IDs,
not an assumed client/AWS wall-clock alignment. No new load or deployment.

| Sliding window | Maximum client-issued requests | Maximum matched Lambda starts |
|---|---:|---:|
| 100ms | 6 | 20 |
| 200ms | 11 | 24 |
| 500ms | 26 | 51 |
| 1second | 51 | 85 |

Matched STARTplus platform-duration intervals reach10overlapping invocations.
Their total duration divided by120seconds is approximately2.36occupied slots
(an estimate excluding unbound calls), so the average hides short peaks.
33of53measured502responses reached the client within one one-second window.
These are maxima at different times, not identical cross-clock windows.

Accepted invocation starts are materially more clustered than client issuance.
That supports transient bursts as a cause worth targeting before speculative
application changes. It does not locate burst formation in the generator,
network or AWS/ALB dispatch, nor observe the exact arrival of rejected requests.
Current logs do not break execution into connection acquisition, SQL and
short-lock waits. Those would need additional bounded instrumentation if further
application profiling is selected. No conclusion that the hotspot is proven.

Derived evidence: `/home/suraj/src/.clip-private/pgbouncer-20261104/memory-trial-20261104/concurrency-observation-bound.json`.
The earlier clock-window approximation is retained separately and is superseded
for phase membership by the ID-bound reconstruction. Raw output stays unchanged.
