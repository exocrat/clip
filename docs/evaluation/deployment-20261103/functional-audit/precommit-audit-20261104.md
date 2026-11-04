# Precommit requirement and release audit — 2026-11-04

This is a source/tooling audit and local validation checkpoint, not deployed
acceptance. Suraj authorises work up to immediately before commit, with capacity
decisions held if the local database saturates. The
[capacity gate is blocked](precommit-capacity-20261104.md); independent checks
continue. No automatic pooling/replica/resize, merge or deployment is authorised.

## Measurement trace

| Requirement | Workload/observer | Evidence/report and interpretation |
|---|---|---|
| Main ECS/Lambda comparison | `k6/comparison_load.js`, reviewed comparison cases/profile, paired plan, real-run coordinator | Monotonic end-to-end samples; strict expected responses; offered/issued/correct throughput, errors, timeouts, drops, route quantiles; comparison report/telemetry/cost and paired analysis. Freeze100%or explicitly reviewed B definition before formal runs. |
| Candidate weight pilot | `k6/exp05_pilot_load.js`, pilot builder and coordinator | Same reviewed5browse/3search/2detail burst mix at50rps;60second10rps warm-up and120second measured windows; ECS baseline plus four weights/three repetitions each. Candidates do not accept NFRs. |
| NFR-01, A and B | `k6/nfr_load.js`, `nfr_workload.js`, browse cases |20browse/s;95%of correctly completed browse requests within1000ms; image-body downloads excluded. Failures and missed arrivals separately visible. |
| NFR-02, A and B | Same entry point with separate Hybrid search cases/profile |10search/s;95%of all eligible issued requests successfully complete within1000ms; failures/timeouts stay in denominator. Ranking quality is not added to this latency criterion. |
| NFR-03, A and B | `k6/nfr03_load.js`, fixed balanced schedule/case rotation, own profile |50mixed/s for300measured seconds;correct outcomes within client deadline;95%success; seven operation classes, unique write IDs, separate preflight, timeout reconciliation and cleanup ledger. Different from the read-only main burst. |
| NFR-04 | `nfr04_retrieval.py`, verified frozen labels/data consumer |22reviewed included queries;Success@5 first five results;failures remain misses. Both paths checked when search routing differs. Local22/22and original-SQL equivalence do not replace the selected live retrieval evidence. |
| NFR-05 | `nfr05_browser.mjs`, `nfr05_background.js`, `nfr05_report.py` |60messages;actual submission-to-recipient-display observed with one Node monotonic clock; failed/undisplayed messages retained;normal10read/s background workload;no message-content evidence. Two real regular accounts/CDP sessions needed later. |
| NFR-06, A and B | `nfr06_recovery.py` |Two healthy ECS runtimes;exact separately approved task stop;restore configured serving capacity within240seconds with request outcomes. B retains Lambda-read evidence and no assumed fallback. |
| NFR-07 | `nfr07_restore_observer.py` |Latest available automated source snapshot;exact separately approved isolated restore;30minute deadline, migration/FK/representative relationship checks and restored-application smoke. One result may cover unchanged shared DB/procedure. |
| NFR-08 | `nfr_cost_ledger.py`, shared project ledger/cost helpers |Strict gross project spending under200USD through evaluation/cleanup;credits separately, unbilled and retained estimates, actual reconciliation. Historical10USDcap is superseded, not reintroduced. |

Paths in the table are relative to`scripts/evaluation/`. Formal NFR-01/02/03
windows remain60seconds warm-up/300seconds measurement. Explicit short local
mode never changes those canonical profiles or authorises deployed execution.

## Application and input review

- Session/account authorization remains fresh. ECS pools are bounded. Lambda
  reuses only the physical Identity connection within an invocation, closes it
  before terminal response delivery and keeps restricted roles separate.
- Search receives current eligibility, readiness, metadata and missing vectors
  in SQL, releases its Hybrid lease, then performs bounded application scoring.
  Cached immutable generations do not cache visibility or result pages. Exact
  arithmetic, all sorts/pages and source changes have native differential tests.
- Browser batching reduces per-card Identity/API work. Image bodies remain S3
  downloads and require real rendered-page verification after deployment.
- The final dataset is present and unchanged. The frozen consumer checks the
  accepted archive, member/fingerprint/label hashes and repeated dataset equality
  without regenerating old data against newer additive contracts.
- Staged real-run bundles include transitive imports. Real target/approval/input
  validation precedes session handling and measured traffic. The CLI-login bridge
  consistently selects the named reviewed AWS profile without copying secrets.
- Raw k6 output remains untouched. Separate runtime timing profiles, reports,
  source hashes and the custom monotonic binary receipt identify local evidence.
- Normal public response contracts, rank/filter/page rules, money/UUID/timestamp
  types and authorization are preserved; no new contract generation is needed
  for these numerical/connection changes.

## Before commit and deployment

Final local checks completed:

- Python:2429passed/180skipped;data331passed;web504passed/3skipped, lint/types/build passed.
- Native Listings/Hybrid PostgreSQL:27passed/3skipped;integrated functional inspection26groups passed.
- CI parity, boundaries, contract freshness/types,35database-wrapper safety cases,
  clean/repeated migrations and Conversations retirement checks passed.
- Backend-free Terraform formatting/validation passed;23mock tests passed.
- Strict typing for the new scorer and final481-file Black check passed.
- The aggregate's final secret-scan step initially flagged descriptive cache
  documentation as a generic API key. The phrase was rewritten without changing
  scanner rules/exceptions;the focused final Gitleaks8.30.1scan passed. The
  original nonzero aggregate result is retained, not relabelled as a clean run.

The skipped optional/native suites are reported as skipped, not assumed passes.
These quality results do not clear the blocked capacity gate or live acceptance.

Capacity is unresolved; do not call this release ready. Finish final local
aggregate/native/Terraform checks and inspect changed source, docs and secret-scan
results. Keep the branch uncommitted for Suraj's decision. Prepare the final PR
description only after the actual selected capacity implementation is known.
Final local result paths/check status are in the work-log checkpoint and
`/tmp/clip-precommit-final-validation/state.json`; copy completed logs privately.

Before cloud actions, refresh real identity/account/resources/drift/spending,
renew the bounded execution window/cap and bind final revisions/image digests.
Existing image-only approval does not authorise1vCPUallocation, full Lambda
creation/concurrency or SQL changes. Proposed worker grants and pilot role limits
Identity20/Marketplace40remain separately gated, not missing app implementations.
Keep the same authoritative data/settings for A and B; record actual additional
controlled fixtures without deleting user content. Build both final images from
the accepted revision and inspect the exact saved Terraform plan/rollback.

Before formal results, freeze run order/repetitions, candidate-selection rules,
numerical cost-score endpoints/allocation/prices, telemetry windows and generator
headroom evidence. Existing comparison telemetry validates supplied CPU/RSS/VU
and drop observations; actual generator-host observations must be collected and
bound at run time rather than inferred from local service metrics. CloudWatch
collection is read-only and preserves missing series; it cannot identify a
single request's target or invent PostgreSQL lock-wait evidence. Collect those
through the reviewed routing/DB observations in the live plan.

Deploy functional smoke checks first, including repeated photos/Saved/search,
real mail, worker publication and both routing paths. Suraj inspects the website
before pilot traffic. Pilot then applicable NFRs then formal comparison, with
NFR-08accounting throughout and exact task-loss/restore gates at their actions.
