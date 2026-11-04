# Local capacity batch and deployment handoff — active

Suraj explicitly began the lunch batch. Local implementation and required-rate
capacity testing are authorised. The commit, publication, CI, deployment, live SQL
and more expensive resource holds remain active. Existing repairs are preserved.

## Current authorised order — 2026-11-04

Suraj authorises an autonomous local batch ending immediately before commit:
functional rechecks, short capacity measurements, analysis, then the relevant
audit/experiment alignment and final local checks if results are satisfactory.
The theoretical capacity discussion now follows the measurements, only when a
problem remains. Persistent database CPU saturation or another material decision
blocks capacity-dependent progress; independent audit/documentation may continue.
Do not add shared pooling, a second database or a resource upgrade automatically.
No commit, push, hosted CI, merge, live SQL, deployment or cloud change is allowed
in this batch. This explicit grouped authorisation supersedes routine per-step
verification for this bounded batch only.

The main capacity gate uses the formal comparison's burst mix:50Listing reads/s,
25browse/15search/10detail, reviewed cases and matching planned runtime settings.
Test A and B with100%of selected reads on the actual local Lambda composition.
The integrated NFR-03 mix remains a separate check because it adds other reads
and writes. Short NFR-01/02/03 checks cover both configurations. A comfortable
read-burst result is useful evidence for lighter read profiles, not proof of
write contention, recovery, restore, real chat display or cost acceptance.

`capacity_local.py --synthetic-local --profile-set short-release` uses10seconds
warm-up/60seconds measured per profile at unchanged required rates. Strict source
profiles remain unchanged; a local-only flag overrides runtime timing and is
rejected by the affected deployed runners. Separate runtime profiles and reports identify
short evidence explicitly; default NFR reports reject shortened inputs. Formal
AWS pilot/formal/NFR durations and repetitions are unchanged. The local transport,
four serial Lambda environments, real model/data and resource limits remain
diagnostic approximations, never AWS measurements.

## Settled scope

- Leave password hashing/login/signup/reset optimisation out. Measured workloads
  use established sessions; normal session authentication remains in scope.
- Prioritise first-time query performance. Implement common ECS/Lambda numerical
  scoring and a bounded vector cache, with fresh database eligibility/readiness.
- Treat ready vectors as immutable within their pipeline/generation. Normal
  writes already follow that rule; Suraj rules out privileged in-place changes.
- Include the approved1vCPU per ECS task in planning, retaining two tasks/two
  existing hosts. AWS still has512CPU units/task; no allocation change was applied.
- Recommend other resource changes only if measurements warrant them. Do not
  automatically deploy higher-cost resources or change live SQL role grants.

## NFR-03 schedule choice

The PRD requires50requests/s for five minutes and at least95%success, excluding
intentionally rate-limited abusive requests. It does not prescribe a100-operation
cycle, operation proportions or consecutive blocks of searches. The current
integrated cycle/mix comes from the project's measurement design; grouped
execution comes from the workload implementation.

Implement a deterministic, well-spread ordering of the same30browse/25search/
15detail/10wanted-read/10conversation-list/9saved-list/1wanted-create cycle.
Freeze the exact schedule before formal measurement and use it for both A/B.
Update the design, builder/runner, schedule tests and bindings together. Preserve
rate, measured duration, relevant cases, controlled writes, unique operation IDs,
timeout reconciliation, denominators and complete outcomes. Suraj explicitly
declined the optional grouped stress diagnostic; do not retain it as planned work.
Do not select schedules after formal results or suppress failures. The main
architecture comparison retains its own separately reviewed traffic sequence.

Time priority: run required PRD/experiment procedures and checks needed to verify
the changed implementation. Do not add grouped/over-rate stress campaigns or the
optional Lambda-reset experiment. Assess headroom from required-load measurements,
connection/CPU budgets and the selected resource limits.

## Ordered work after explicit start

1. Trace each measured request and background path, including session writes,
   locks, pools, model work, data transfer and per-route scheduling bursts.
2. Implement common application-side scoring, cache/change checks, precomputed
   stored norms and connection return before CPU work. Retain all prior repairs.
3. **Update application/experiment tooling together now:** align NFR-03 ordering;
   route/response checks, A/B expectations, manifests and profile generators;
   dataset/revision bindings; cold/warm cache observations; and credential/session
   handoff. Wire CLI-login SDK compatibility into the runners that need it.
4. Verify actual implementation against original SQL, including ranking, filters,
   pages, visibility, unavailable embeddings, source edits, cache misses and races.
5. Exercise full real local HTTP/DB/model paths under explicit application/DB
   limits. Include the actual workload sequences, new queries, cold loading,
   sustained required rates. Assess margin from those measurements; no additional
   above-required-rate stress campaign is selected.
6. Report measured CPU, memory, connection holding/queue time, latency, correctness
   and generator capacity by request class and architecture. Explain the limiting
   component. Compare minimal costed resource options if required-load margin is
   insufficient. No local result proves deployed NFR acceptance.
7. **Repeat application/experiment alignment immediately before deployment:**
   inspect the final diff against PRD/experiment requirements; verify every
   changed path is measured correctly; regenerate/rebind final cases, profiles,
   source/model/schema/contract hashes and revised pool/resource settings; run
   affected final checks and ensure images contain the verified final revision.
   Do this again if any subsequent code or resource setting changes.
8. Prepare the concrete review/commit/CI/image and deployment package. Wait at
   the existing exact commit/merge/cloud/SQL gates. Renew the cloud execution
   window and cost cap before live changes or workload traffic.
9. Deploy reviewed final images/settings; verify routing, sessions, both response
   paths and all repaired website flows. Reproduce image/Saved failures on repeated
   rendered pages, and retain actual network/body results. Suraj inspects the site
   before pilot traffic.
10. Run the reviewed EXP-05 candidates, freeze B's selected weight, then execute
    the paired comparison and applicable NFR01–08 procedures. Preserve invalid/
    failed/cold runs. Task loss and isolated restore retain separate exact gates.
11. Review reports and raw accounting, reconcile spending, perform approved cleanup
    and complete closeout.

## Read-only access findings

AWS CLI login for `surajs2` currently works and STS confirms account335523638354,
user`surajs2`, Mumbai. Actual ECS/RDS/ECR/ALB/Lambda/SSM/EC2 read calls passed;
two existing c7i-flex.large hosts are running, both SSM agents online, and the
service has two running/no pending tasks at revision13,512CPU/2048MiB per task.
RDS remains available on db.t4g.micro. IAM simulation allowed all20checked actions
covering the main deployment, telemetry, task-loss and restore operations, with
no missing simulation context. This is permission evidence, not an executed apply
or approval for those actions. GitHub authentication/repository access works.

Plain root-venv `boto3.Session(profile_name='surajs2')` fails locally because its
login provider expects the optional CRT dependency. The repo already supplies a
credential-private refreshable bridge in`data/generators/reference_login.py`.
Its actual STS call succeeded under this login during the access check.
The lunch batch wires the existing bridge into real-target preflight, CloudWatch
capture, Lambda initialization, recovery and restore; do not misreport this local
SDK integration issue as missing IAM permission or an application-server failure.

## Image and Saved release state

The repair source3691a50 passed CI and web504/3skipped plus prior integrated
local checks. It includes bounded Identity pooling, batched image/Saved checks
and API-clock-based signed-link expiry handling. The repaired API/Lambda images
were built and smoke-checked locally, but not published/deployed.

Read-only AWS inspection confirms task revision13 still uses the old API image
digest860c8c15fe29b2592976ca5b8dafdb5738d791de012ccbc4f57b9bc076ae674b.
Therefore neither intermittent image errors nor Saved warnings can be declared
fixed on the live website yet. The earlier narrow Search grant correction was
applied, but the later connection/batching repair remains local. Final new search
changes also require final source-bound builds and deployed functional checks.


## Local capacity observations and simulation scope

The corrected A NFR-03 run in`/tmp/clip-lunch-capacity-04` completes exact accounting.
The initial B diagnostic intentionally routed all selected reads into only two
serial local environments. It queued/timed out; its partial raw output is retained
and cannot count as a pass. The monitoring client also shared that overloaded
HTTP pool, so a monitoring PoolTimeout ended the attempt. Monitoring now uses a
separate client, with resource samples preserved even on interruption.

A low-rate actual-path trace in`/tmp/clip-lunch-capacity-trace-01` measures Lambda
browse/detail about34ms and search about104ms including initial cache loads,
versus ECS about10/7/68ms. The observed selected mix needs roughly two continuously
busy serial environments at35selected reads/s; two has no headroom. The planned
AWS reserved concurrency is already10. Remaining local diagnostics therefore use
four serial environments, each1CPU/2GiB, and disposable-only Identity20/Marketplace40
role limits matching the proposed full pilot budget. This is no live role grant,
AWS capacity change or permission to apply one. The validated A run is retained;
`--profile-set nfr-remaining` now runs A/B01/02without repeating the validated A/B03runs.

The local database quota is not an emulator for RDS's managed-service overhead,
Graviton processor, network/storage or CPU credits. A separate read-only RDS
sample at08:05UTC finds73.28CPU credits, eight connections and about134MiB latest
freeable memory. This is idle old-deployment evidence, not required-load capacity.
Actual database memory/CPU/credit headroom must be checked during the bounded
smoke and pilot before accepting any frozen configuration.


The four-environment100%Lambda B NFR-03 check completes all15000measured
operations correctly within5seconds, with no drops, but local database use is
about1.80of2CPU cores. That passes the local latency criterion with limited CPU
margin. The follow-up therefore also exercises the already-planned50/50candidate
under the main pilot mix and mixed NFR-03 profile. It does not freeze B's weight;
all AWS candidate runs and the original selection criteria remain required.
The first A01attempt in`-05`issued zero HTTP requests because the added arrival
guard referenced k6's exported options rather than an internal scenario constant;
its report rejected delivery. That reference is corrected and script exceptions
now stop diagnostics early. `-06`contains the four remaining dedicated profiles.
Every failed attempt remains retained, including the zero-request one.
