# Normal API Hybrid read lifecycle

Current optimisation checkpoint: the
[2026-11-04 measurements](../evaluation/deployment-20261103/functional-audit/search-optimisation/README.md)
record first-use SQL improvements, inference before the read-pool lease and a
bounded immutable query-vector cache. Session checks and live result snapshots
are still required. Historical pool numbers below are superseded by the
[functional repair connection budget](../evaluation/deployment-20261103/functional-audit/connection-budget.md).
The lunch batch implements common ECS/Lambda application-side numerical scoring
in `hybrid_snapshot.py`: fresh SQL eligibility/readiness and metadata on every
request, missing-generation binary vector transfer, a bounded immutable-vector
cache and precomputed norms, then ordered-double NumPy scoring after returning
the DB lease. Numerical workers are limited to two per process, with32pending
requests and an overall20second deadline. Cancellation retains its numerical slot
until the underlying CPU work finishes. There is no cached authorization/page or
automatic Keyword fallback. This paragraph describes the 2026-11-04 local checkpoint; it is not a current
release or deployment assertion. SE-01 completion is tracked in the work log, while
formal experiment/NFR and deployment evidence remains in the linked evaluation
records.

Merge follow-up: [the combined deployment handoff](listings-search-deployment.md)
now provides and locally verifies an optional Linux AMD64 Hybrid image and normal
website-serving configuration. The original checkpoint evidence below remains
historical; integrated cloud workload/resource acceptance is still separate.

**Origin:** SE-01 hybrid amendment checkpoint5, Mohit-verified implementation plan.
**Task status:** SE-01 is complete in the work log. The implementation and local
checks described here are historical evidence. EXP deployment, NFR, final corpus,
and live upstream evidence remain separately tracked. A subsequent separately enabled
[dispatcher](semantic-embedding-dispatcher.md) now processes existing jobs only;
pipeline activation/backfill remain separate.

## Configuration and defaults

The API reads process environment only. `.env.example` is documentation.

| Setting | Default / rule |
|---|---|
| CLIP_HYBRID_SEARCH_ENABLED | false; true explicitly opts into helper/read-pool startup |
| CLIP_HYBRID_SEARCH_INTERPRETER | unset; enabled mode requires an absolute existing interpreter path; preserve venv symlink invocation |
| CLIP_HYBRID_SEARCH_MODEL_DIR | unset; enabled mode requires an absolute local artifact directory |
| CLIP_DATABASE_URL | existing secret setting; required with enabled Hybrid; never logged |

Paths with disabled mode, partial enabled settings, relative/NUL paths and missing
DB configuration are rejected before resource creation. Settings repr excludes
interpreter/model paths; invalid configuration names fields without values.
Settings validation does not read/download artifacts. The actual helper checks
pinned model/tokenizer/runtime versions, CPU/offline protocol and supported space.
The code accepts explicit production settings but that is not deployment/platform
approval; deployment remains gated on its own compatibility/resources/upstream plan.

## Ownership and request behavior

`app.main.lifespan` opens the existing transactional Listings pool, then enters
Listings-owned `search_runtime`. Disabled mode creates no helper or extra pool.
Enabled mode creates one real helper per API process and a separate bounded
read pool (min1/max2, timeout5s, autocommit, statement5s/lock1s/idle-transaction5s).
The existing command pool stays min1/max10/timeout5s with its original transaction
configuration. Thus enabled mode adds at most2connections per API process; no
existing command or Keyword connection is changed to autocommit. Deployment-wide
worker/process counts and DB capacity still need their real resource review.

The composition root injects helper/pool into the existing PostgresListingsStore.
Only nonblank Hybrid borrows that read pool. Keyword and blank browse in either
mode retain the command pool and no semantic dependency. No test identity, fake
model, schema access, response field or generated/public signature is introduced.
The exact boundary allowlist admits only this lifecycle factory/cleanup import.

Invalid settings fail configuration. Expected helper/read-pool startup failure
closes partial resources, logs a fixed message and yields unavailable; the API
can still serve Keyword. Nonblank Hybrid is503 with no fallback. Startup failure
requires a configuration repair/restart to enable capability. After successful
startup, existing client request/queue/deadline/restart semantics remain; runtime
ready means startup succeeded, not perpetual readiness or complete source coverage.
A serving pipeline and complete eligible vectors remain mandatory per request.

## Cleanup and scope boundaries

The context owns helper and read pool; the composition root owns the command
pool. Shutdown rejects/reaps owned inference then closes pools, attempting pool
close even when helper close fails. Shielded cleanup completes through late
cancellation/SIGINT; cleanup errors propagate instead of being counted as success.
Startup cancellation cleans partial resources and propagates. A later adapter
construction/body error also unwinds both contexts. No coroutine here registers a pipeline, backfills or flips serving state.
A separately enabled owned dispatcher now processes existing jobs only.

The opt-in normal_runtime_probe uses only a freshly created native private
Unix-socket database and controlled sources. A separately explicit test bootstrap
publishes real vectors before the normal app starts. The actual app lifespan then
runs disabled/ready/unavailable cases, real HTTP queries and normal cleanup.
Only caller/eligibility are test doubles; helper instrumentation observes actual
inference and does not replace it. The probe runs at most6min/40windows with
one simultaneous child and a sampled512MiB API/helper ceiling; native PostgreSQL
RSS is separate. No live listener or existing/shared target is accepted.

The historical receipt records source hashes, actual run/cleanup/resource
observations and focused checks; see the
[evaluation retrieval guidance](../evaluation/README.md).
The subsequent dispatcher and bootstrap checkpoints are documented separately.
This runtime guide does not claim that experiment deployment, controlled corpus,
relevance or NFR gates have passed; those remain in the evaluation plan. SE-01's
peer, merge, and task acceptance status is recorded in the work log.


Worker-enabled cleanup now first cancels/awaits/closes the dedicated dispatcher,
then closes the helper/read pool. Worker pool adds at most1connection per API
process (max13combined). It shares the existing helper and is disabled by default;
startup failure/cancellation and cleanup ordering have their own checks/evidence.


The subsequent [explicit bootstrap operations](semantic-pipeline-bootstrap.md)
are now implemented/checked outside startup: status/prepare/bounded queue/activate.
They require separate operator target/action approval; no shared activation is
performed by this implementation or by enabling read/worker capability flags.
