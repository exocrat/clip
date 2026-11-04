# Local precommit capacity checkpoint — 2026-11-04

**Decision: capacity gate remains blocked for B at100%selected-read offload.**
No commit, publication, hosted CI, SQL change, resource upgrade or deployment
occurred in this batch. Suraj authorises independent audit/validation while the
capacity decision waits for his return. Do not select a lower weight or add a
proxy/second database automatically.

## Scope and evidence locations

The actual local ECS and Lambda read compositions use the latest invocation
Identity reuse, real session/domain SQL, the accepted1000Listing/5000User archive
and pinned model. Two ECS containers and four serial Lambda containers each have
1CPU/2GiB limits; owned PostgreSQL18.6 has2CPU/1GiB/78connections. Disposable role
caps are Identity20/Marketplace40/Conversations4. These are not live settings.
Transport is loopback HTTP/private Unix sockets with HTTPS scheme adaptation,
not real TLS, ALB, Lambda scaling, Graviton hardware, RDS overhead or CPU credits.
AWS's proposed Lambda concurrency10 is not simulated by four local environments.

Each high-load diagnostic has10seconds warm-up at10rps,5seconds drain,60seconds
at50rps and up to5seconds final drain. Both use the formal burst's same reviewed
5browse/3search/2detail case cycle. Short evidence is not an EXP-05 candidate
selection or formal comparison/NFR pass. Formal timing/repetitions remain intact.

Original outputs: `/tmp/clip-precommit-capacity-09/`.
Persistent private evidence:
`/home/suraj/src/.clip-private/exp261103/precommit-20261104/`.
Within that directory:

- `capacity-09/result.json`: source/module/k6 hashes, configuration, quality and run bindings.
- `capacity-09/lunch-a-exp-05-ae5244.*`: A profile/runtime profile, untouched raw JSONL, report, resources and k6 log.
- `capacity-09/lunch-b-exp-05-582805.*`: corresponding failed B evidence.
- `capacity-derived.json`, `derive-capacity.py`: separate calculations and reproducible derivation.
- `functional-sweep.json`: integrated disposable functional checks.
- `previous-capacity-06`, `previous-capacity-07`, `previous-capacity-08`: retained earlier dedicated-NFR/quality/high-load attempts.
- `sha256-manifest.json`: byte hashes of the preserved evidence; original raw files are not rewritten.
- `tested-source/`:137source/module files verified against the run's exact recorded hashes. Later scorer annotation/explicit-index-type cleanup and harness formatting are not retrospectively presented as the tested source.

## Exact measured results

| Measurement | A: ECS only | B:100%selected reads via local Lambda composition |
|---|---:|---:|
| Scheduled measured requests |3000|3000|
| Issued HTTP requests |3000|2922|
| Correct responses |3000|2510|
| Timeouts |0|412|
| Dropped arrivals |0|78|
| Successful operations per measured second |50|41.8333|
| Overall p95, including failures |65.25ms|5001.04ms|
| p95 among correct responses |65.25ms|3915.34ms|
| PostgreSQL CPU cores used, sampled steady interval |0.4729of2|1.9903of2|
| Percentage of database CPU quota |23.64%|99.51%|
| Pool request/connection errors in sampled counters |0|0|
| Outcome/timing accounting complete |yes|yes|
| Required traffic delivery complete |yes|no|

A p95 by route: browse11.02ms, search71.97ms, detail12.46ms.
B p95 including failures: browse5000.88ms, search5001.20ms, detail5001.11ms.
CPU uses cumulative cgroup deltas between samples20–70seconds after process
launch, within the measured phase; it is not a per-query CPU attribution. Lambda
serial service and queue imbalance also contribute to the observed local limit.
Both warm-ups completed their100requests correctly. B's missed arrivals make
the diagnostic invalid for formal acceptance even though raw accounting is complete.

All22reviewed queries on each path had no retrieval failures, Success@5=1.0,
and complete ordered first pages identical to the independently preserved
original SQL oracle. This is local quality/correctness evidence only.

## Interpretation and stop

Within-invocation Identity reuse does not clear this local high-load gate.
Database CPU is saturated while A has substantial margin. There were no sampled
pool errors; raising role limits alone does not add CPU. The data does not assign
all excess CPU to connection creation or prove a particular proxy/resize will
solve it. Earlier B NFR-03 and50/50comparison results use different workloads,
windows and/or code; do not treat them as a matched before/after improvement.

The runner stopped after the failed main capacity gate. The six planned new
short NFR-01/02/03profiles therefore did not run. Earlier retained dedicated
NFR checks remain historical local evidence and are not substituted for the
latest-source checks. Capacity-dependent release progress waits for Suraj.

Fallbacks to discuss from this evidence: shared backend pooling if connection
creation remains a material cost, targeted remaining SQL work, or an explicitly
costed resource change. A micro-to-small move adds memory, not CPU cores. A read
replica/domain split adds routing/consistency/migration work and is unselected.
Retain strict100%offload as the starting candidate; no favourable weight is chosen
from these diagnostics. No new performance optimisation follows without review.

## Independent functional and audit work

The latest integrated disposable inspection passed26groups, including photo
upload/confirm/byte delivery and batch visibility, caller-only Saved membership,
Wanted/Saved flows, real Hybrid pagination/no-match, owner edits/availability,
conversation/offer flows, temporary-account restrictions and Handle/grouping
behaviour. Provider login/mail are controlled local providers. Real website
rendering, real recipient mail and deployment behaviour remain pending.

The [requirement-to-tooling audit](precommit-audit-20261104.md) records final
local quality checks; their success cannot clear the capacity failure.
