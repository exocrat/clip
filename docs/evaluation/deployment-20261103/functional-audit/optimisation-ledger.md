# Functional repair and optimisation ledger

Current discussion checkpoint: 2026-11-04. This records the whole optimisation
set, not just search arithmetic. Nothing below is a deployed capacity guarantee.
The latest repair images have not been deployed; current search changes are
uncommitted. Suraj has held commits/publication/CI while the authorised local lunch batch proceeds.

| Change | Purpose and current state |
|---|---|
| Bounded Identity connection pool | Reuse at most4connections/ECS task instead of opening fresh connections for every request. Finite queue/wait; expiry/logout/revocation SQL retained. Implemented in repair3691a50, CI passed, not deployed. |
| Whole-app connection budget | Bound Listings, Hybrid, workers and Conversations across both tasks. Maximum30app connections for A;36for B smoke concurrency2. Full Lambda concurrency10 needs reviewed role limits/headroom. Implemented configuration; actual capacity unmeasured. |
| Lambda null pools | Close unused connections so frozen environments cannot accumulate idle leases. Implemented in repair3691a50; B is not deployed. |
| Lambda within-request Identity reuse | Uncommitted: session and eligibility transactions share one exclusive connection, closed before the response completes. Preserves roles/current-state checks;109focused tests passed before this short capacity batch. Does not pool across invocations. |
| Batched saved membership | Combine per-card Saved checks into a bounded request for the rendered page. Implemented and locally checked; not deployed. |
| Batched image-link delivery | Combine per-card authenticated link requests, reducing session checks and DB work. S3 bodies remain separate downloads. Existing visibility and temporary-link rules remain. Implemented and locally checked; not deployed. |
| Photo expiry and bounded refresh | Use the API Date header so incorrect device clocks do not immediately reject links; refresh remains bounded. Implemented/local web checks passed; not deployed. |
| Inline exact cosine and one query norm | Remove repeated vector validation/query-norm SQL from the inner comparison while retaining write constraints, exact stored norms and ordered double accumulation. Uncommitted; focused/native exact comparisons passed. |
| Page-aware lexical-tier skipping | Avoid scoring tiers that cannot affect this requested page plus lookahead; non-relevance sorts skip unnecessary lexical-match scoring. Coverage still checks all eligible sources. Uncommitted; original-equivalence tests through page5/all sorts passed. |
| Encode before borrowing Hybrid DB lease | Inference and helper queueing no longer occupy a search connection. Overall timeout and idle/autocommit checks remain. Uncommitted; lease/failure tests passed. |
| Bounded query-vector cache | Reuse immutable model output for exact query text and model identity. At most 128 entries expire after 300 monotonic seconds; lifecycle guards remain. Does not cache scores/results/auth. Uncommitted; helper tests passed. |
| Fast application-side scoring | Local NumPy prototype scored2000vectors in median8.73CPU ms, excluding retrieval/decoding/filtering/sorting/auth/HTTP. Subsequent real-PG differential check passed2568part scores with zero numerical/threshold differences,72ordered sets and360page windows. Common product snapshot/cache/binary-transport/scoring integration is now implemented locally; full-path required-rate diagnostics are in progress. |
| Precomputed stored-vector norms | Implemented: validate/decode immutable generation vectors once per cache load and compute ordered-double norms; reuse across different queries. Query norm remains per query. Cold/warm and original-SQL native checks pass. |
| Chunk aggregation and score blending | Implemented in the application scorer: maximum description cosine and35/65blend use the same arrays. Original-SQL native differential fixtures preserve weighting, order and pages. |
| Cached listing vectors plus per-search change check | Implemented: each process caches at most4096parts/2048generations with270–300second spread expiry. Fresh SQL checks pipeline, generation identity, visibility and readiness; only missing vectors transfer. Native cold/warm, changed-price/visibility/source-generation checks pass; required-rate HTTP profiling continues. |
| Consolidating repeated eligibility reads | Considered, not implemented. Current pooled session+eligibility SQL measured1.12DB-CPU ms/phase locally. Preserve fresh account-state checks; avoid changing auth semantics for a small unproven gain. |
| Query/background inference scheduling | Still under review. Worker and query share one helper; long indexing work can delay a query. No priority, extra helper or worker-disabling change made. Keep worker publication reliable. |
| ECS task CPU allocation | Existing tasks are0.5CPU each, two total, on two2CPU hosts. Increasing task quota may use existing spare host capacity, Suraj approves planning1vCPU per task on the same hosts. Overlay updated; nothing applied. Complete-path local diagnostics use1CPU/task. |
| RDS memory/CPU sizing | Discussed only. No resize. More memory can help memory pressure; it does not remove inefficient scoring or automatically increase cores. Actual deployment, cost and headroom need exact review. |
| External shared connection pool | RDS Proxy/PgBouncer discussed as fallbacks only. May reduce backend creation overhead; requires compatibility, permissions/TLS, budget and deployment review. Not implemented or approved for deployment. |
| Second RDS instance | Read replica or domain split discussed as later fallbacks. Replication lag, write/session routing and cross-schema dependencies require design work. No second instance is selected or authorised. |
| Numerical-score cache | Rejected and removed: helped repeated queries but added first-use overhead. User prioritises new-query latency. Raw evidence retained. |
| Global score-cache join/grouped comparison batches/JIT toggle | Local alternatives measured; no product adoption. Keep unfavourable results as well as improvements. |

## Generation IDs and vector changes

The normal application publishes vectors by INSERT in
`apps/api/app/domains/listings/embedding_store.py::complete`, then marks that
generation ready in the same transaction. Its lease/state guard prevents a ready
generation from being published again through this method. Listing text changes
invalidate old generations and create fresh IDs; explicit failed-job retry also
creates a fresh generation ID. This supports a generation-based cache design.

No normal application path updating published vector values in place was found.
The reference-role probe performs an ordinal no-op; mutation tests deliberately
try direct vector changes. The current schema checks validity/completeness, but
does not make ready vector values immutable against an appropriately privileged
direct UPDATE. That is a schema capability, not evidence that production does it.

Suraj explicitly confirmed that privileged out-of-band vector replacements under
an existing generation will not occur. Adopt that operational invariant together
with the existing application publication rules: a ready generation's vectors
are immutable; replacements require a new generation. The proposed cache may use
pipeline/generation/part identity without per-request vector hashing or a new
revision mechanism solely to defend against such manual changes. Cache only
complete ready generations and still check fresh eligibility/readiness in the
database snapshot. A per-request timestamp heuristic alone is insufficient.
No migration/grant change is made here. Revisit the invariant if a future supported
write/rebuild path needs to replace ready vectors in place.

## Evidence and remaining checks

The [search checkpoint](search-optimisation/README.md) contains exact timings,
raw reports, test counts and conditional capacity math. The
[repair file guide](repair-files.md), [connection budget](connection-budget.md)
and [coverage ledger](coverage.md) retain earlier implementation/functional scope.
All final revisions and connection/runtime settings must be recorded before
paired experiments. Public Listing responses, search order/filters/pagination,
NFR denominator rules and image-body exclusions must survive any scoring move.
No experiment or NFR result has been claimed by these local diagnostics.

Suraj's time constraint excludes optional grouped/above-rate stress campaigns.
Keep required experiment/NFR runs and implementation correctness checks; calculate
headroom using the required-load observations and resource/connection budget.
