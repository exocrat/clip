# Search optimisation checkpoint — 2026-11-04

Local implementation and diagnostics only. No new image is deployed, and these
results are not NFR passes. Suraj has explicitly held commits, publication and CI
while discussing the remaining optimisation choices. First-time search takes
priority over repeated-query performance.

**Latest result:** the
[precommit capacity checkpoint](../precommit-capacity-20261104.md) supersedes
older in-progress descriptions below. A short50read/s ECS burst completed all
3000requests correctly;100%Lambda-selected reads saturated the local database
and had412timeouts/78drops. Invocation Identity reuse is implemented, but the
capacity gate remains blocked. Independent local audit/checks continue; no
further optimisation, commit or deployment is automatically authorised.

## Lunch batch implementation (supersedes the SQL-only checkpoint below)

The common API now uses `hybrid_snapshot.py` for application-side numerical
scoring on both ECS and Lambda. Each search still obtains current authorization,
filter/visibility/source/pipeline/readiness and summary metadata from SQL. Only
missing generation vectors transfer, as PostgreSQL binary float32 arrays. A
process cache retains at most4096parts/2048generations, with270–300second spread
expiry and immutable arrays. It stores no sessions, user decisions or result pages.
Precomputed stored norms, ordered float64 cumulative sums, maximum description
cosine and the original35/65blend preserve the original arithmetic. No candidate
cap or approximate index is introduced.

The store releases its SQL connection before running the numerical/sort step in
one of two bounded CPU workers. At most32search requests may wait, and the whole
sequence retains its20second deadline. A cancelled request cannot free its CPU
slot until its underlying thread finishes. Exact cold/warm cache, metadata edit,
visibility/source-generation and unavailable-coverage native checks pass against
the original SQL. Root API dependencies now pin NumPy2.5.4; the existing pinned
model helper remains a separate interpreter/runtime.

The full-path local harness is `scripts/evaluation/capacity_local.py`, with a
UDS-only worker in `capacity_local_worker.py`. It uses the exact accepted archive,
real pinned model and actual session/domain SQL in owned disposable containers:
two1CPU/2GiB ECS apps, four serial1CPU/2GiB read-only Lambda-code environments and
a2CPU/1GiB/78connection PostgreSQL18.6 database. This is not an emulator for AWS
hardware, ALB/TLS, Lambda initialization/concurrency scaling, RDS storage or managed
service memory overhead. Both ECS workers remain enabled; no applicable queued
embedding or notification work is silently disabled.

`/tmp/clip-lunch-capacity-01` and `-02` preserve preparation failures caused by
attempting to regenerate frozen inputs against newer contract hashes. `-03`
preserves the first full mixed diagnostic:18001correct responses/zero HTTP errors,
but invalid exact delivery because k6 issued one extra boundary iteration.
The reports refused success. All four load scripts now cap HTTP work at their
planned arrival budget and record surplus scheduler executions separately;
missing/dropped work still fails. `/tmp/clip-lunch-capacity-04` contains a valid
A NFR-03 and aborted B diagnostic, not a completed six-profile campaign. Later
`-05`completed B NFR-03;`-06`completed the four dedicated NFR-01/02checks. The
latest source has a separate failed high-load gate in the linked checkpoint;
do not substitute these older results for its unrun NFR profiles. Raw results
remain unchanged. The earlier attempt's
executed harness copy and timing/workload receipts are retained alongside output;
later follow-up harness changes do not retrospectively alter that source.

Final aggregate checks, derived resource/connection analysis and the separate
comparison-mix/22-query quality follow-up are recorded in the lunch capacity
report when complete. No repaired image has been deployed and no local threshold
is a formal NFR acceptance.

## Earlier SQL-only implementation

`apps/api/app/domains/listings/hybrid_read.py` computes the query-vector norm
once and inlines the original ordered double-precision cosine calculation.
Stored vectors still have their existing mandatory write-time validity checks;
the query vector is validated before SQL. Near-unit vectors retain their real
norms. Model/configuration/source readiness is checked over the entire eligible
set before pruning any scoring work.

For relevance, lower lexical tiers need no scoring only when higher tiers fill
the requested offset, page size and one-row lookahead. Every later page derives
its own required window. Price/recency sorts skip similarity for lexical matches
whose membership does not depend on similarity. No candidate cap, approximation,
ranking-policy change or keyword fallback is introduced.

`apps/api/app/domains/listings/postgres_store.py` finishes model inference before
borrowing the Hybrid database connection, with the existing overall deadline and
idle/autocommit guard. `embedding_client.py` reuses at most128 checked query
vectors for300monotonic seconds, keyed by exact text/model hashes; stopped,
broken, closed or fork-inherited helpers cannot satisfy hits. This caches neither
sessions nor result pages. Both deployment paths use the same implementation.

The expensive numerical-score cache prototype was removed: it accelerated
repeated broad searches but made first-time scoring slower. Alternative global
cache joins and disabling PostgreSQL JIT were also measured without introducing
those changes into the product. Their raw results remain in the private evidence
directory listed in [the manifest](evidence-manifest.json), alongside earlier
unfavourable grouped-batching measurements. Raw files were copied unchanged.

## SQL measurements

The [final raw profile](clip-search-first-use-final-profile.json) uses an owned,
network-isolated PostgreSQL18.6 container limited to2CPU/2GiB,1000synthetic
listings and2000dense vector parts. It compares every ordered public response
with the frozen original SQL. Three alternating attempts per case are retained.
The original and optimised query receive identical data, filters and vectors.
This is a first-use scoring implementation with no numerical-score cache; usual
database buffer/plan warming is not a cloud cold-start experiment.

| Case | Original median SQL ms | Optimised median SQL ms |
|---|---:|---:|
| Broad semantic | 896.60 | 213.87 |
| Filtered semantic | 105.41 | 33.25 |
| Selective lexical page1 | 935.95 | 35.32 |
| Selective lexical page3 | 853.62 | 193.19 |
| Lexical recency | 865.83 | 41.03 |
| Lexical price | 844.55 | 183.03 |

Four reused SQL connections then issued40queries per diagnostic group, all
correct. Closed-loop results include queueing/contention in this local fixture.

| SQL-only case | Correct queries/s | DB CPU ms/query | Observed p95 ms |
|---|---:|---:|---:|
| Broad semantic | 4.35 | 460.89 | 1190.38 |
| Selective lexical | 34.36 | 60.48 | 177.67 |
| Artificial three-case mix | 11.87 | 171.07 | 1006.91 |

The artificial mix is broad, selective and filtered search; it is **not** the
formal workload or final dataset. Earlier same-implementation local broad probes
reached5.94SQL/s, illustrating host/diagnostic variability. Do not select only the
best result. No test here emulates Graviton hardware, RDS storage or CPU credits.

Unchanged pooled session-plus-eligibility SQL passed200/200 attempts using four
connections/eight callers:237.50phases/s and1.12database-CPU ms/phase. This measures
controlled session SQL, not Microsoft login or deployed authentication acceptance.

The [real local model diagnostic](clip-query-model-cpu-probe.json) measured thirty
distinct query inputs: median5.19ms elapsed,4.67ms helper CPU and1.04ms parent CPU
per uncached query. Cache hits took median0.013ms. Startup was1175.86ms. These are
unconstrained local-process measurements, not the ECS0.5CPU quota or Lambda cold
start. They indicate that SQL scoring is the larger local bottleneck.

## Moving numerical scoring to the application — feasibility only

Suraj proposed moving expensive similarity calculations to ECS. The
[local numerical prototype](clip-vector-compute-candidate.json) processed2000
stored float32 vectors of384dimensions with ordered float64 accumulation in
median8.73CPU ms. It recomputed both norms and dot products, using the already
installed isolated NumPy2.5.4 environment. No product dependency was added.

This establishes a promising arithmetic implementation, **not** a finished
replacement. The prototype excludes database retrieval/parsing, metadata,
snapshot/readiness checks, filtering, sorting, helper IPC, authentication, network,
resource quotas and independent numerical equivalence against PostgreSQL.
The raw vector payload alone is3,072,000bytes per complete corpus transfer.
API implementation would need a bounded common ECS/Lambda path, safe treatment
of changed source/generation/vector data, all pagination tests and new profiling.
It must preserve the same public response and ranking requirements. Application
scoring was a design proposal at this earlier checkpoint; the lunch implementation
above supersedes it.

### Differential equivalence follow-up

The [real PostgreSQL/NumPy comparison](clip-numpy-sql-equivalence.json) subsequently
passed2568part-score comparisons over428vector parts/six queries, with zero
numerical differences and zero threshold mismatches. All72ordered result sets
and360page windows matched across relevance, recency, price ascending/descending,
availability/category/price/negotiability fixture filters. Fixtures include dense
vectors, near-unit norms, both sides of the threshold, ties and96description
chunks with a late maximum. Weighted title/maximum-description scores matched too.

The SQL oracle is the actual original `listings.embedding_cosine` function in
the freshly migrated PostgreSQL18.6 fixture. NumPy2.5.4 rounds inputs to stored
float32 precision and uses ordered float64 accumulation. This does not license
substituting an arbitrary matrix multiplication or a differently ordered sum.
No new dependency was installed; the owned database was removed on completion.

Fixture ranking uses supplied lexical tiers and metadata in both implementations;
it does not test a production cache, actual-model relevance, full-text compilation,
concurrent edits/readiness or the complete HTTP retrieval path. Those integration
checks remain before adopting application scoring. Probe source/raw output are
retained under the private paths and hashes in the evidence manifest.

## Capacity interpretation

Last verified deployment: two c7i-flex.large hosts, one task per host, two tasks
total; each host has2vCPU/4GiB, each task has0.5vCPU/2GiB. Host CPU total is4,
but combined task quota is1CPU. RDS is db.t4g.micro with2vCPU/1GiB. This checkpoint
does not refresh AWS inventory or change any resource. A memory-only RDS upgrade
does not add CPU cores. Task quota changes would need a reviewed deployment plan.

CPU demand is rate multiplied by measured CPU time. For example,12.5broad searches
per second at460.89ms each would require5.76database CPU-seconds every second,
before other requests. With selective searches at60.48ms, the same rate needs
0.76CPU-seconds instead. The current NFR-03 mix at50requests/s includes12.5searches/s;
NFR-02 schedules10searches/s. Their actual reviewed queries/data must be measured.
The all-broad diagnostic is insufficient evidence of either requirement passing.

The theoretical SQL CPU ceiling is2000 divided by CPU-ms/query on two cores.
Operating at65% CPU for headroom would give roughly2.8broad or21.5selective
searches/s before other database work. These conditional estimates cannot be
presented as full API capacities; task CPU, connection holding time, Lambda
concurrency, network, storage, background work and queueing can impose lower limits.
Adding a fixed network allowance to unloaded latency cannot predict a loaded p95.

## Verification and files

- Focused Hybrid/helper suite:73passed, `/tmp/clip-search-first-use-focused.log`.
- Real PostgreSQL adapter suite:26passed/3skipped; migration/head/rollback,
  seven smokes and retirement lifecycle passed, `/tmp/clip-search-first-use-native.log`.
- Native comparisons cover near-unit and threshold-adjacent vectors, all four
  sorts, lexical/expanded/semantic boundaries through page5 and missing lower-tier
  embeddings returning503. The frozen oracle is
  `apps/api/tests/domains/listings/hybrid_reference.py`; it is never imported by
  production code. `test_hybrid_read_postgres.py` owns those comparisons.
- `test_hybrid_read.py` checks inference-before-lease and failure behavior;
  `test_embedding_client.py` checks cache bounds, expiry and helper lifecycle.
- `scripts/evaluation/search_local_profile.py` owns the explicit synthetic-local
  profiler. `apps/api/tests/domains/identity/postgres_fixtures.py` adds an optional
  profiling quota/owned CPU-counter identifier; ordinary fixture behavior remains.

The full aggregate, hosted CI, fresh image builds and deployed checks remain
pending. Authentication semantics, worker scheduling, resource allocation and
public API shapes were not changed by this search checkpoint. Existing image
rollout approval does not cover new database grants or larger resources; the
previous cloud execution window has expired. No cloud operations occurred here.
