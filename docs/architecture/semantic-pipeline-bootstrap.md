# Explicit embedding pipeline bootstrap and activation

**Origin:** SE-01 hybrid integration checkpoint5, Mohit-verified bootstrap plan.
**State:** Implemented/checked; result awaits human verification. This is initial
pinned-space tooling, not automatic startup, target approval or deployment.

## Operations and coverage

Listings-owned EmbeddingBootstrap accepts an injected idle autocommit connection
and only the current checked pipeline manifest. No model process is started.

| Operation | Behavior |
|---|---|
| status | Read-only transaction and one aggregate SQL snapshot. Absent registry remains absent. |
| prepare | Register absent space as planned, then building. Planned resumes to building; building/serving remain unchanged. Retired/mismatched space is refused. |
| queue(limit) | One1..1000batch of existing reconciliation. Requires building/serving. Current pending/leased/failed/ready jobs are preserved; no automatic failed retry. |
| activate | Separate building->serving transition, or checked idempotent serving result. Refuses absent/planned/retired/mismatch, conflicting serving space or incomplete coverage. No replacement/retirement/demotion/reset. |

Coverage follows the registry schema's entire live scope: non-retired listings
not pending retirement, including unavailable/future/ended listings. Aggregate
counts cover missing/current/stale/pending/leased/failed and invalid ready parts;
state and freshness counts may overlap. Ready requires current source fingerprint,
exact title/description counts and complete contiguous ordinals. Existing vector
and deferred completeness constraints remain authoritative; no fake vector or
candidate cap is introduced. Reports contain no listing IDs/source text/vectors.

Statements are bounded5s/lock1s. Mutations use registry advisory lock21 and reuse
existing transaction/store guards. prepare and repeated queueing never reset
current generations/attempts. Zero queued does not prove completeness: locked
rows may be skipped; use status and retain refusal until all coverage checks pass.
No operation loops through a whole corpus or invokes inference. Worker processing
is separately enabled and may leave bounded retries/failed jobs requiring explicit
recovery through their existing reviewed operation.

Activation rechecks full coverage before/after the state transition, and SQL guards
check it too. A concurrent writer can commit after the observed complete snapshot:
activation is not future readiness/linearizability. Existing invalidation and
request-time snapshot guards are mandatory; Hybrid returns503 until all eligible
current vectors are ready. Keyword remains independent. This race is explicitly
proved by the native probe rather than hidden by locking away concurrent writes.

## Operator CLI and target gate

`scripts/search_pipeline.py` accepts status/prepare/queue/activate, pinned pipeline
ID and exact expected host/port/database/login. CLIP_DATABASE_URL is read only as
an approved process secret, never an argument/dotenv. Explicit URL host/port/db/
user must match before connect, and actual server database/current+session role/
connection host+port are checked before the operation. Ambient PG/service/options
indirection and multi-target input are refused. SSL parameters remain supplied
through the approved secret path; normal deployment/security policy still applies.

Each mutation requires --execute; queue also requires --batch-size. This flag is
an execution guard, never human approval. Obtain approval for the concrete target,
pipeline/action and bounds before any shared/cloud mutation. Status is read-only
but still requires correct binding. Operation deadline10s (connect<=5s); output is
aggregate JSON or fixed refusal code, never raw driver/source/credential text.
No public HTTP/admin route, test caller, model download or startup activation.

These commands are initial pinned-space operations. They do not upgrade/switch
another serving pipeline, resurrect retired spaces or remove state. Such work
requires its own reviewed operation/target plan. Disabling read/worker flags and
owned shutdown remain available without deleting retained data. No shared target
is selected or approved in this checkpoint.

## Real verification

The guarded bootstrap_probe creates one new private native PostgreSQL cluster;
operator subprocesses use only that generated Unix-socket target. Three controlled
sources include one unavailable listing. It checks absent/read-only status,
conflicting serving refusal (empty alternative metadata only, no fake vectors),
prepare/resume,1/2/0batch progress, generation preservation and missing/failed/
leased refusal. Existing explicit retry/defer are fixture recovery, not new policy.
Actual app.main worker/model publishes all3sources. Building space remains Hybrid
503; an activation while an edit is uncommitted observes old complete state, then
the writer's commit makes status incomplete/Hybrid503. Keyword stays200, activation
recheck refuses the gap, and due-job publication permits idempotent activation/
Hybrid recovery. All tasks/helpers/pools/cluster stop with retained evidence.

Probe bounds:10min/40windows,1simultaneous helper, sampled512MiB API/helper; native
DB and short operator CLI processes are outside that RSS measurement. Only trusted
caller/eligibility are test overrides. [Evidence](../evaluation/domain/se-01/bootstrap/result.json)
records real CLI/SQL/model results, resources, unit checks and remaining gates.
Actual upstream/identity/images, Linux/deployment/capacity, final corpus20+human
labels/NFR/full CI/secret scanning/independent review remain incomplete.
