# Shared-pool local validation — 2026-11-04

This validates local source and deployment preparation. It is not managed-proxy,
website, cloud capacity or formal NFR acceptance. No AWS mutation occurred.
The [shared-pool plan](shared-pool-plan.md) records the exact pending action.

## Release checks

Evidence directory: `/home/suraj/src/.clip-private/proxy-20261104/validation/`.
`sha256.json` fingerprints retained logs; original failures are preserved.

| Check | Actual result | Evidence file |
|---|---|---|
| Shared CI mapping | Passed | `aggregate.log` |
| Full Python suite, first attempt | 2457 passed, 14 failed, 180 skipped | `aggregate.log` |
| Final affected suites and proxy/pilot checks | 77 passed, including every failed test and two added historical/current pilot-scoring tests | `corrections.log` |
| Final Python format | 486 files unchanged; passed | `final-python-format.log` |
| Data tools | 331 passed | `final-data-tests.log` |
| Architecture boundaries, generated contracts, contract typing | Passed | `final-boundaries.log`, `final-contracts.log`, `final-contract-types.log` |
| Web lint/types/tests/build | 504 passed, 3 skipped; build passed | `final-web.log` |
| Database wrapper safety and migrations | Passed | `final-database-safety.log`, `final-database.log` |
| Native Listings/Hybrid SQL | 27 passed, 3 skipped; clean/repeat/upgrade/rollback checks passed | `native-listings.log` |
| Native Conversations retirement | 184 passed | `final-conversations-retirement.log` |
| Source secret scan | Gitleaks 8.30.1 passed | `final-secrets.log` |
| Backend-free Terraform validation | Passed | `terraform-validate.log` |
| Terraform mocks | 27 passed, 0 failed | `terraform-mocks.log` |

The first Python failure was not discarded: eleven lifecycle assertions expected
constructor arguments before the new callbacks, and three embedding fixtures used
`synthetic-unused` instead of a valid unused DSN. Fixtures now assert the explicit
callbacks and all original pool bounds, or use a valid `.invalid` DSN. They still
exercise startup failure, cancellation and cleanup without external connections.
All failed suites passed in the 77-test correction run. One formatting failure
following that fixture edit was corrected; both the original and final logs remain.
The full aggregate was not rerun from the beginning after these fixture-only
changes. Its remaining required checks were run individually and all passed.
Skipped suites remain skipped; CI has not run for this uncommitted revision.

The current pilot scoring also refuses a baseline claiming more correct requests
than issued. Focused tests prove complete current/historical matrices, rejection
of missing repetitions and no invented winner after a failed 100% candidate.

The web build retains its existing chunk-size advisory. Local Lambda packaging
reports default-FROM-argument warnings, but exact supplied cached image inputs
build successfully. Neither warning is a claim of a runtime failure or cloud pass.

## Capacity and real integration

All four short direct ECS diagnostics completed with two 1-vCPU/2-GiB apps,
local PostgreSQL capped at 2 CPUs/1 GiB and the accepted synthetic dataset.
Each measured window is **60 seconds**, after **10 seconds** of warm-up.
These are shorter than the formal pilot/NFR procedures and omit AWS networking,
real RDS/EC2 hardware and credits, managed proxy behavior and Lambda scaling.

| Local A profile | Issued / successful | Drops / failures | p95 | Mean DB CPU quota used |
|---|---:|---:|---:|---:|
| exp-05 at 50rps | 3000 / 3000 | 0 / 0 | 130.08ms | 48.54% |
| nfr-03 at 50rps | 3000 / 3000 | 0 / 0 | 124.49ms | 39.43% |
| nfr-01 at 20rps | 1200 / 1200 | 0 / 0 | 20.51ms | 4.22% |
| nfr-02 at 10rps | 600 / 600 | 0 / 0 | 131.70ms | 23.58% |

Browse and search each had 100% of their applicable denominator succeed
within 1,000ms. NFR-02 records successful search completion, not relevance; its
`completed` outcome is counted separately from the other profiles' `correct`
outcome. NFR-04 remains the separate ranking-quality measure. The mixed profile had 3,000/3,000 correct outcomes within 5,000ms,
with complete write reconciliation. All four runs had complete accounting and
delivery, no timeouts, and unchanged raw-file hashes. Quality retrieval returned
22/22 Success@5 hits with zero retrieval failures. Owned temporary containers and
database resources were removed after completion.

The CPU column uses cgroup CPU-time deltas between observations within seconds
20–70 of each run, divided by elapsed time and the two-CPU quota. It is an average,
not a peak. Mixed-profile p95 is separately calculated from all 3,000 measured
`clip_nfr03_elapsed_ms` raw points using the same interpolated quantile helper;
other p95 values come from the corresponding report's measured phase.

Exact raw files, per-run reports, telemetry and source/binary hashes are under
`/home/suraj/src/.clip-private/proxy-20261104/ecs-fallback-check/`.
`result.json` is the runner checkpoint; `summary.json` lists every exact path,
raw hash, sampling interval and result. The generation script is retained there.
Individual preview reports deliberately retain `nfr_accepted=false` and
`latency_timing_verified=false`: they are not full execution-receipt-bound cloud
reports. The local runner separately checks and records the custom monotonic
binary/extension hashes; do not upgrade these diagnostics into formal evidence.

The earlier A read-burst diagnostic had p95 65.25ms and mean DB quota23.64%; this
run had130.08ms and48.54%. Both delivered all scheduled work, but these separate
local runs do not establish identical performance or identify the reason for the
variation. Do not promise that AWS will match either measurement. The current
short diagnostics retain margin to their thresholds; managed-proxy capacity
still requires approved real measurement.

No B run was repeated against direct local PostgreSQL: that would not test the
chosen managed-proxy repair. Actual proxy authentication, TLS/default deadlines,
backend reuse/pinning, AWS capacity and repaired website behavior remain pending
approved provisioning and release.

## Review scope and gates

Application review covers unchanged role isolation, current session state,
transaction ownership, bounded waits, deadline checks, no automatic direct
fallback and direct rollback. Restore composition refuses source-proxy reuse.
Tooling review covers explicit target-version bindings, immutable raw output,
proxy telemetry and the authorized six-run pilot. Public response contracts,
search ranking and NFR denominators/rates are unchanged in this follow-up.
The [file guide](repair-files.md#shared-proxy-follow-up-after-fallback-commit-6193ca7)
explains every changed implementation/configuration file.

No local check failure remains unresolved. This is not an exhaustive
proof against undiscovered defects. Actual cloud behavior is a required next gate.
Suraj remains the designated human reviewer; use the
[peer-review prompt](../../../prompts/peer-review-prompt.md) for the exact PR revision
before authorizing its merge. Read-only GitHub inspection found PR32 still a draft
at `3691a5019efdfbb6fc9ed8c70fb9f9746500c6e4`, with that older revision's CI green;
that CI does not validate the fallback commit or this new uncommitted code. The optimized fallback
is committed; Suraj has now authorized its commit, push and CI. The proxy follow-up remains
undeployed; exact PR-head merge approval is still required.
