# Bounded embedding job dispatcher

**Origin:** SE-01 hybrid integration checkpoint5; Mohit verified the worker plan.
**State:** Implemented/locally checked; result awaits human verification. No shared
activation, controlled bootstrap, Linux acceptance or deployment is implied.

## Enablement and ownership

CLIP_HYBRID_WORKER_ENABLED defaults false and requires
CLIP_HYBRID_SEARCH_ENABLED=true with its existing explicit DB/interpreter/model
settings. It is a real capability setting, not test authentication. Disabled mode
creates no task/worker connection. A failed helper startup starts no dispatcher.
The normal lifecycle owns one dispatcher per API process and borrows that
process's existing helper. No second model process or service is introduced.

The dispatcher owns a min1/max1 autocommit pool (wait5s, statement5s/lock1s/idle
transaction5s). Command pool max10 and Hybrid read pool max2 remain separate;
worker-enabled maximum is13connections per API process. Deployment process count,
DB capacity, CPU/memory and Linux packaging remain separately reviewed gates.

## Scheduling and existing guarantees

One background task processes existing durable jobs serially through the real
EmbeddingStore/EmbeddingWorker and the helper's exact supported pipeline spec.
Each successful/stale outcome yields the event loop. At most10jobs form a burst,
then pause1s. No due job pauses2s. Capacity deferral, recorded failure or known
DB/helper/persistence error ends the burst and pauses5s. Pauses occur after the
borrowed connection is returned. This is bounded work per turn, not a claim that
a continuously enabled service has a finite lifetime/total job count.

The worker still enforces20s work,30s leases, <=5s helper reap and <=3s failure
recording. Existing source/generation/token/lease/retirement fences, full-chunk
validation, attempt limits and durable backoff remain unchanged. Model execution
holds an idle dedicated connection, never an open database transaction/row lock.
Uncertain writes are not immediately replayed; later claims obey due/lease rules.
Failed jobs are not reset by the dispatcher; explicit retry remains separate.

No registration, queue_missing reconciliation, historical backfill, new pipeline,
serving transition or retirement policy is invoked. Existing invalidation triggers
queue source edits for active pipelines; an empty registry stays empty and idle.
Controlled initialization/activation remains the following checkpoint.

## Failure and shutdown

Worker-pool startup failure closes partial resources and leaves the helper/read
capability available. Operational failure pauses with safe fixed logs and no
source/driver exception text. Internal status contains only fixed states/outcome
and aggregate counters, never listing/query IDs, text or vectors. Unexpected task
failure is marked failed/logged safely and propagates during close; it is not
reported as a healthy running worker.

Shutdown cancels/awaits the task, returns its connection and closes its pool before
the owning context closes the shared helper/read pool and then command pool.
Shutdown does not invent failure/deferral writes: a committed lease remains
recoverable after expiry. Context-wide shielding completes cleanup through late
cancellation; cleanup errors propagate and all remaining resources are attempted.
Worker failure does not change Keyword availability or permit partial Hybrid
results. Complete current vectors remain mandatory for Hybrid on every request.

## Verification and remaining gates

Unit tests use explicit job receipts, not fake relevance/model implementations:
serial10job pacing, idle/deferral/failure pauses, dependency redaction, duplicate
start, cancelled active job, task failure, worker-first shutdown and startup
cancellation/partial cleanup. The guarded worker_dispatch_probe runs actual
app.main, SQL/helper and a new private native DB. It proves empty-registry idle,
source invalidation and old/current chunk state, pending Hybrid503/Keyword200,
automatic due-job publication/current-fingerprint recovery and worker-pool failure
independence. A controlled future retry_after gates publication for deterministic
HTTP coverage checks; it is test setup, not changed production retry policy.

The probe uses <=6min/40windows,1simultaneous helper and sampled512MiB API/helper
RSS, excluding native DB; it stops/reaps all owned resources and retains logs.
Only identity is a test override; bootstrap is explicit fixture setup outside
app startup. The historical receipt records source hashes, failed-probe
correction, real results and remaining gates; see the
[evaluation retrieval guidance](../evaluation/README.md).
Actual upstream/auth/images, controlled bootstrap, Linux/resources/final corpus,
20+human labels/NFR/full CI/secret scan/independent review remain pending.


The subsequent [bootstrap checkpoint](semantic-pipeline-bootstrap.md) now supplies
explicit initial preparation/queue/activation tooling. The dispatcher still never
calls it; empty registries remain idle and current failed jobs are not reset.
