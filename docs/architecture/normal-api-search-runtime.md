# Normal API Hybrid read lifecycle

**Origin:** SE-01 hybrid amendment checkpoint5, Mohit-verified implementation plan.
**State:** Implemented and locally checked; result awaits human verification.
Linux/deployment/resource acceptance and actual upstream identity/images remain
pending. This checkpoint supplied read capability. A subsequent separately enabled
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

[Evidence](../evaluation/domain/se-01/normal-api-lifecycle/result.json) records
source hashes, actual run/cleanup/resource observations and focused checks.
Worker scheduling is now implemented in its subsequent checkpoint, awaiting
result verification. Controlled bootstrap/backfill/activation, real upstream and
Linux/deployment checks remain subsequent verified checkpoints. Final counts,
20+human labels, relevance/load/NFR and CI/peer/merge gates remain incomplete.


Worker-enabled cleanup now first cancels/awaits/closes the dedicated dispatcher,
then closes the helper/read pool. Worker pool adds at most1connection per API
process (max13combined). It shares the existing helper and is disabled by default;
startup failure/cancellation and cleanup ordering have their own checks/evidence.


The subsequent [explicit bootstrap operations](semantic-pipeline-bootstrap.md)
are now implemented/checked outside startup: status/prepare/bounded queue/activate.
They require separate operator target/action approval; no shared activation is
performed by this implementation or by enabling read/worker capability flags.
