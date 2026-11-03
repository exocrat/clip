# EXP-02 real-runner preparation design

Status: implementation checkpoint for local review. The shared real-run
coordinator and offline run-plan builder have been added. The local evaluation,
formatting, typing, secret scan, and Terraform mock suites pass. The pinned
monotonic k6 binary has now been built and its timer bridge smoke-checked.
Affected-owner/independent review, normal PR merge, deployment planning and all
live actions remain pending.
Nothing here authorizes a session, cloud action, deployment or experiment.
The approved [comparison protocol](ecs-only-vs-ecs-lambda-task-list.md) and
[preparation guide](comparison-preparation-inputs.md) remain controlling.

## Current implementation checkpoint — 2026-11-03

`scripts/evaluation/k6/prepare_real_run_plan.py` now creates a new offline plan
for comparison or NFR-01/02/03, binding exact target/profile/module/custom-k6
binary hashes and refusing mismatched A/B run IDs. For comparison, the plan
includes the binding, corpus, ordered reference, paired plan, selected parity
evidence and schedule. `scripts/evaluation/k6/real_run_coordinator.py` stages
and validates these inputs before live target or session checks, checks the
separate expiring action approval, verifies the AWS account/caller/ALB route,
ECS/Lambda/database bindings, HTTPS liveness and regular test-user session, then
executes exactly once. Raw output and an immutable receipt remain under a new
run directory; the coordinator does not retry, create AWS resources, or accept
an NFR/comparison result.

NFR-04's retrieval command now binds to the same hashed target plan and performs
the shared live target and session checks before sending reviewed queries.
NFR-05 requires an expiring approval bound to exact manifest bytes and two
distinct regular-user sessions; NFR-06/07 retain their separate exact
stop/restore approvals; NFR-08 is accounting only.

The local evaluation audit passed: 364 tests passed and 5 skipped; Python
compilation, Black across 29 changed Python files, strict Mypy across 22
production files, `git diff --check`, Terraform formatting, 21 Terraform mock
tests, and the pinned Gitleaks scan passed. The Terraform tests exposed and
verified fixes for missing disabled-stickiness duration and an ECS-only plan
that referenced the absent Lambda security group. The custom monotonic k6
binary was built with Go 1.26.10, k6 2.3.0 and xk6 1.4.14. Its SHA-256 is
`58862efeb0ce5f58190f9b267108f4bdf0dd7db63b78f23a957a197b9a24ea44`; a
one-iteration timer bridge smoke passed with zero network traffic. The Go timer
tests also pass in GOPATH mode with a temporary view of cached modules; module
mode fails in this environment even for `go test fmt` with the same testdeps
lookup error. No workload or cloud resource action ran. Read-only project
inspection used `surajs2` in account
`335523638354`. Cost estimate and remaining credit balance, exact deployment
plan/approval, peer/affected-owner review, website DNS handoff, and all live
checks remain outstanding.

## Implemented local tooling

- The offline run-plan builder binds the target, request profile, k6 executable,
  workload modules and reviewed case inputs by exact hashes.
- The shared coordinator stages and checks inputs before checking the live
  target and regular synthetic user's session. It runs exactly once, performs
  no retries or fallback, preserves raw output and writes a separate receipt.
  It supports the main comparison, EXP-05 pilot, and NFR-01/02/03.
- Target preflight checks caller/account, ALB path/method/routing, ECS and
  Lambda resource bindings, private RDS identity, HTTPS origin and session
  identity. A preflight is not proof of data parity or application correctness.
- NFR-01 and NFR-02 use separate request denominators and reports. NFR-03 has
  its own integrated mixed workload, controlled writes, operation IDs, timeout
  reconciliation and cleanup accounting.
- NFR-04 retrieves the reviewed query set and computes Success@5. NFR-05 uses
  two clients to time actual message display and counts failures/undisplayed
  messages without writing message bodies to evidence.
- NFR-06 and NFR-07 bind their separate exact stop/restore approvals and
  observers. NFR-08 has a project spend ledger and does not treat estimates or
  credits as actual cost.
- EXP-05 has the candidate workload and coordinator launch path. EXP-07 checks
  the full paired 18-run matrix, review references, frozen score and sensitivity
  rules without selecting on incomplete/invalid results. EXP-08 checks that
  every planned resource has a recorded disposition and retained costs are
  linked to the ledger.
- `cloudwatch_capture.py` collects one-minute ALB/ECS, Lambda and PostgreSQL
  metrics for a completed run into new immutable files. It binds the exact
  target-plan hash, account, expected caller, run ID and actual time window. It
  is read-only, preserves missing series as `NoData`, and never declares a pass.

## Remaining before a deployment can be approved

1. Complete the consolidated local audit, then commit the reviewed local batch
   as Suraj authorized. Follow the repository PR workflow for publication and
   integration; this does not authorize cloud operations.
2. Use only `surajs2` for this user-directed project inspection; the default
   profile is root in account `484394572488` and is wrong. The infrastructure
   runbook's older `adityalaxmi1` profile instruction was superseded by Suraj's
   direction that `surajs2` has the required project permissions. Refresh
   Terraform state/drift before any plan. Current reads found the API
   service at zero tasks, RDS stopped, host EC2 stopped, no ALB or Lambda,
   and no Route53 zone. The existing issued certificate is not in use.
3. Cost scope is now clarified: Suraj's USD 200 project limit is cumulative
   through experimentation, while the AWS budget object is an unfiltered,
   one-year account monitor. Its USD 26.526 actual excludes credits; Cost
   Explorer shows the same-period gross usage offset by about USD 26.526 in
   credits. Its USD 1,217.222 forecast is an account-level projection, not a
   project estimate. Service totals do not identify the NAT resource; Suraj
   reports an approximate USD 1.56/day NAT charge, which still needs to be
   checked against detailed usage lines for the exact deployment estimate.
   The USD 10 experiment-credit limit remains separate; verify current
   remaining credit headroom and price the exact resource hours before the
   deployment plan.
4. Bind exact reviewed image digests, migration head, final dataset/index/model
   fingerprints, test-account identity, database/runtime settings, external DNS
   and public HTTPS exposure, telemetry/cost limits, rollback, retention and
   cleanup. The existing infrastructure source is opt-in and requires explicit
   phase selection; it must not be applied from guessed or stale values.
5. Present the exact Terraform plan and cost/reserve, including the user's
   separate USD 10 AWS-credit cap and the project's strict under-USD 200 limit.
   Obtain approval for that exact deployment plan before applying it.

## Live checks after deployment

Deploy A and verify the selected requests use ECS. Deploy B and verify the ALB
sends only the approved Listing GET routes to the selected ECS/Lambda weights;
other routes and methods remain on ECS. Confirm authentication, response meaning,
permissions, same authoritative database and per-path telemetry. These smoke
checks are small functional checks, not performance results.

After smoke checks pass, give Suraj access to inspect the actual website and
wait for that inspection before pilot traffic. The pilot then checks the ECS
baseline and Lambda/ECS weights 100/0, 75/25, 50/50 and 25/75 with three
repetitions per weight. Freeze a candidate only against reviewed criteria and
actual database, generator, routing, telemetry and cost headroom. NFR-01/02/03
then each run separately against A and B. NFR-04 scores the same reviewed
queries on each applicable path; NFR-05 measures real message display; NFR-06
and NFR-07 need their own exact action gates; NFR-08 is reconciled across the
whole project.

The CloudWatch collector covers one-minute service metrics and target-group
request counts. It cannot identify an individual request's selected target;
use isolated small smoke requests and the matching aggregate path metrics to
verify routing. The generator's CPU/RSS limits and capacity still need to be
measured and reviewed on the actual host before workload runs. Missing or
incomplete telemetry invalidates the affected run; it is never reported as
zero or as a pass.
