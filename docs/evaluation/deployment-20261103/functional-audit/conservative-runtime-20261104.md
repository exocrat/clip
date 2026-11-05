# Conservative runtime optimization and three-check batch — 2026-11-04

Suraj approved proceeding through implementation, checks, matched deployment,
one short comparison-load check on A and B, and one full Lambda NFR03check,
then stopping for results review. Product retries are deferred. No overnight
campaign, task-loss NFR06fault or NFR07restore is included in this batch.

## Application changes

| File | Purpose and important behavior |
|---|---|
| `apps/api/app/core/sql_bounds.py` | Sets the same transaction-local deadlines in one exchange. Setup remains a separate statement before protected queries so their timeout applies before query planning/locks. Commit/rollback restores original defaults. |
| `apps/api/app/domains/identity/sessions.py` | Combines token/session lookup and account-locking lookup. Locks only the account first, then the session as before. Keeps every account/session lifecycle check and the exact last-seen update. Pure account validation is shared with existing login/logout paths. Adds safe setup/account/session/touch timings. |
| `apps/api/app/domains/identity/temporary_challenges.py` | Uses combined timeout setup; key commitments, OTP behavior and transaction boundaries remain checked as before. |
| `apps/api/app/domains/identity/capabilities.py` | Uses combined timeout setup and times the existing fresh eligibility lookup. No authorization caching or policy changes. |
| `apps/api/app/domains/identity/runtime_database.py` | Retains shared-pool clients for240seconds rather than60, below the pooler's300second idle expiry. Direct clients retain60seconds. Hard bounds, TLS, health checks and transaction cleanup remain. Times actual connection acquisition. |
| `apps/api/app/core/logging.py` | Adds a strict code-owned stage allowlist and monotonic stage timing, using existing server request correlation. No SQL, credentials, account IDs, query text, results or exception messages enter these events. Nested spans overlap and must not be summed. |
| `apps/api/app/domains/identity/http.py` | Times authentication including thread scheduling and SQL; authorization behavior remains unchanged. |
| `apps/api/app/domains/listings/browse_routes.py`, `routes.py` | Time browse/search/detail operations without logging request arguments or changing their contracts. |
| `apps/api/app/domains/listings/hybrid_read.py`, `hybrid_snapshot.py` | Combine the same SQL deadline setup; candidate selection, ranking, model checks, pagination and snapshot consistency are unchanged. |
| `apps/api/app/domains/listings/postgres_store.py` | Separately times pool acquisition and Hybrid snapshot work. Database lease still ends before NumPy scoring. |

This batch intentionally preserves the existing account/session locks and
per-request last-seen update. Relaxing those semantics is not a conservative
shortcut. These changes reduce exchanges and improve visibility; zero throttling
under the ten-slot limit is not guaranteed.

## Measurement and configuration changes

`runtime_observations.py` sanitizes stage events and groups repeated stage events
per request/phase. Unknown-client events remain unattributed; nested spans are
not added together. Its event cap and `lambda_initialization.py`'s cap are raised
to400,000to accommodate the extra bounded diagnostic events in full50rpsruns.
The ECS and Lambda images must contain the same application source and logging.

The Terraform Lambda-memory validation now permits the user-approved ceiling of
4096MiB; actual AWS quota3008MiB still applies. The selected deployment input
will bind3008, matching the latest trial. No host, database, pool, permission or
concurrency increase is included. Mock tests cover3008and rejection above4096.

New/updated tests cover safe stage data and exceptions, transaction-local deadline
reset on commit/rollback, shared-pool idle policy/stale sockets, existing exact
session expiry/reset/revocation races, query results and stage aggregation. Existing
privacy checks still inspect every record; their allowed metadata includes only
the new controlled stage field. The result-query test expects one combined setup
exchange rather than two separate SETs, still one result/coverage statement.

## Execution contract

1. Finish relevant local checks, audit source and obtain required commit approval.
   Merge remains deferred. Build two matched images with immutable source labels.
2. Prepare exact deployment plans and bounded action package: account335523638354,
   Mumbai, existing two API tasks at1CPU/2GiB each, existing pool/RDS and Lambda
   at3008MiB/5seconds/ten unreserved slots. Only image/task-definition updates,
   selected-read routing transitions and explicit fresh-runtime resets.
3. Verify real health and read/auth parity, then start fresh application runtimes
   before each recorded check. Keep host/database/pool/data caches unchanged.
4. Run one A and one B EXP05-style diagnostic:60swarmup10rps,120smeasured50rps,
   five-second deadline, zero retries,300preallocated/maximum workers per scenario.
5. Run one B NFR03:60swarmup50rps,300smeasured50rps, same five-second deadline,
   zero retries and fixed integrated schedule. Preserve3,000warmup/15,000measured
   operations and180wanted-create attempts with unique IDs. Reconcile all writes.
6. Restore ECS routing, close only run-owned Wanted rows and remove only five
   new Saved prerequisites. Preserve all raw/results, reconcile telemetry and
   stop for human review. No further tests begin automatically.

The approved prerequisite inventory found three existing conversations but zero
Saved/Open Wanted rows. A private intent/receipt records five newly saved existing
listings and one controlled Wanted fixture, with cleanup required. Source dataset,
Listings availability and credentials were not regenerated. Their identifiers
and all later generated operation IDs remain in private evidence only.

NFR03requires >=95% successful eligible requests at50rpsfor five minutes; it
is not a zero-error requirement. The script/report already use that rule. The
separate first coverage check does not supply all later A/B repetitions.

Private batch home:
`/home/suraj/src/.clip-private/pgbouncer-20261104/conservative-20261104/`.

## Completed source audit and local checks

Final Python regression with `CLIP_NATIVE_PGBOUNCER_TESTS=1`:2530passed,
180skipped, with warnings treated as errors.34Terraform mock checks pass;
eight generated contract artifacts current; zero Python boundary violations;
strict Mypy passes all18changed production files with explicit package bases.
Type-only accumulator annotations were completed after the full run;16focused
runtime/provenance tests then passed. Changed Python formatting and whitespace
checks pass; Gitleaks source snapshot scan passes. No model/dependency/browser
changes. Earlier logging-test monkeypatch, missing tool PATH and old setup-call
assertion failures are retained and corrected, not product failures or hidden
measurement runs. Exact private receipts accompany this source snapshot.

Commit approval is required before the existing build helper can produce
commit-labelled matched images. This is source preservation only; publication,
CI and merging remain held. The later exact cloud/run package will retain the
user's stop at step6and the separate recovery/restore gates.
