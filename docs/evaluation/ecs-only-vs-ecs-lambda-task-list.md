# Campus Marketplace — ECS-only vs ECS+Lambda Experiment Task List

**Version:** 3.0  
**Date:** 2026-10-14  
**Canonical repository path:** `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md`
**Document 2. Status:** Working task list for the PRD's primary cloud experiment. It does not report experiment results; none have been run while preparing this document.

**Entry:** INT-01 verified/merged; select tasks through `docs/tasks/project-task-index.md`. Use the mandatory one-step human-verification loop and `CONTRIBUTING.md` branch/PR/reviewer workflow. Readiness/cloud action approvals remain separate.

**Purpose:** Determine whether routing selected read-heavy requests from ECS to Lambda improves burst responsiveness or cost efficiency without degrading normal-load performance for this application.

This is a task list for that comparison. Step-by-step procedures for testing individual NFRs belong in the relevant domain task lists, at the first point when the integrated product makes those tests accurate. If a specific NFR has no earlier accurate test point, include its detailed procedure here as a named integrated verification task, as previously directed. Keep that exception narrow: Document 2 remains focused on the ECS-only versus ECS+Lambda comparison and must not imply that an unrelated NFR was measured by the comparison.

## 1. Experiment boundary

Compare these two configurations:

| Configuration | Request handling |
|---|---|
| **A — ECS-only** | ECS serves all benchmarked read-heavy API requests. |
| **B — ECS+Lambda** | Selected read-heavy API requests are served through Lambda; the rest of the application remains on ECS. |

Both configurations must use PostgreSQL as the authoritative datastore. State-changing requests stay on ECS in both. The selected routes should come from the implemented, integrated product and its generated API contract; the PRD names browsing available listings, retrieving listing details, and searching/filtering listings as candidate read-heavy operations.

The experiment compares the complete user-facing request path under the chosen deployment, including its ingress and routing. For browse, exclude image-body transfer as specified by the PRD. It records latency, offered and successful throughput, failures/timeouts/throttling, runtime behavior, database behavior, and cost. It does not decide that one compute service is universally better.

### Keep out of this task list

- The step-by-step tests for NFR-01 through NFR-07 when the relevant behavior can be tested accurately in a domain task list. Put each there after its feature and required integrations are complete. If a specific NFR has no earlier accurate test point, include its step-by-step process as a clearly identified integrated verification task in this document; do not test partial behavior or present an unrelated NFR as an ECS/Lambda comparison result.
- Project-wide NFR-08 accounting outside this experiment. This task still declares caps and estimates the comparison's cost before running it.
- General agent prompts, session checklists, PR/merge instructions, and reusable human workflow. Those belong in their designated documents.
- Optional wanted-match notifications, weekly digest, and image-aware search. These do not belong in the required comparison.

## 2. Start conditions

Start the measured comparison only when:

- The required application is integrated and deployed, and the selected read routes work through the normal authorized user path.
- ECS-only behavior is healthy. The mixed configuration is implemented and returns equivalent authorized results for the selected routes.
- Related domain tasks have completed their tests and recorded their required NFR work at the correct integration point.
- The evaluation dataset, route behavior, database schema/indexes, and monitoring needed for this experiment are available.
- The current environment and resource inventory identify the actual account, region, resources, owners, and cleanup route.
- Project budget and capacity limits have enough remaining headroom for this experiment and pending required work.

If a condition is missing, make it an explicit prerequisite task or ask the human to resolve the blocker. Do not start measured runs against a partly built feature or an unknown environment.

## EXP-01 — Choose and freeze the comparison design

Before changing code or deploying experiment resources:

1. Read the submitted PRD, Document 1, current architecture/environment records, approved decisions, generated API contract, and the completed feature tasks for the candidate routes.
2. Inspect the actual deployed path and current implementation. List the read routes that can be compared and any route that cannot be safely or fairly offloaded.
3. Present the human with feasible choices for:
   - The exact routes to benchmark and the reason each is representative.
   - A normal workload and a burst workload, including route proportions and the point at which the burst begins and ends.
   - Request distribution, payloads, filters, page choices, cache behavior, user mix, and arrival-rate method.
   - Resource settings for ECS, Lambda, PostgreSQL, and ingress, including scaling/concurrency limits.
   - Generator location, warm-up and measurement durations, client timeout, repetitions, run order, cold/warm treatment, metrics, and cost attribution.
   - Time/concurrency/resource caps, stop conditions, estimated cost, and remaining-budget reserve.
4. Include the PRD's required conditions when applicable: synthetic reference data of at least 1,000 listings and 5,000 users; at least five minutes of performance measurement after warm-up; warm and cold behavior reported separately where applicable; each load run's maximum duration and resource/concurrency caps declared before execution.
5. Explain tradeoffs, expected evidence, and any unresolved questions. Recommend one complete plan. Do not silently fill a value that changes workload meaning, comparison fairness, security, cost, or cloud resources.
6. Stop and ask for the human's choices/approval. Record the approved design in the repository manifest before proceeding. The manifest must contain actual values and commands, not unresolved placeholders.

**Complete when:** The human-approved plan fixes the routes, workload, data, resources, run limits, metric definitions, cost method, run order/repetitions, evidence location, and cleanup action. The design specifies a feasible comparable implementation and run plan within the budget; configuration B is implemented in EXP-03 and deployed/verified in EXP-04 before it is considered runnable.

## EXP-02 — Prepare dataset, workload, and evidence capture

1. Reuse the project's approved deterministic synthetic-data generator. Confirm the seed and record the actual user/listing counts and a dataset fingerprint. Do not use real users, contacts, conversations, or credentials.
2. Confirm the same logical dataset, indexes, and relevant database settings will serve A and B. Freeze dataset changes for the comparison. If equivalent restored datasets must be used, document how equivalence is checked.
3. Implement or update the load scenario using the real generated API contract and authorized synthetic accounts. Do not invent endpoint names or response fields; discover them from the current contract and code.
4. Make each scenario check the expected status **and** response meaning, such as availability, filter correctness, pagination, and detail identity. A successful HTTP status with incorrect data is not a successful request.
5. Configure the selected workload to issue the approved request mix at the approved arrival rate. Distinguish a scheduled iteration from an HTTP request; if an iteration sends multiple requests, count each request correctly. Measure and report generator-side dropped work and resource saturation.
6. Record route-tagged request outcomes, durations, timeout/throttle/failure counts, offered throughput, successful throughput, and relevant resource/DB metrics. Keep authentication setup outside measured request traffic unless it is explicitly part of the approved workload.
7. Capture application/image/frontend revisions, migration head, dataset fingerprint, configuration, run times, resource telemetry, and cost inputs with each run. Exclude credentials, tokens, private keys, contacts, and message plaintext from logs and evidence.
8. Keep raw run output unchanged after capture. Store analysis and corrected calculations as separate files or versions.

### Local checks before cloud use

- Seed a fresh local test database and verify deterministic data and counts.
- Run a small workload against the local integrated app. Verify request meaning, route labels, arrival calculations, timing boundaries, timeout handling, and output artifacts.
- Exercise wrong responses, delayed responses, timeouts, authorization failures, and generator scheduling shortfalls. Confirm each is reported accurately and never counted as a success.
- Run the repository's relevant tests, lint/format, type/build, and generated-contract checks. Use Black for Python workload tooling.
- Review evidence for secrets or real personal data before storing it.

If scripts, metrics, or fixtures required by the approved plan do not exist, add and verify that tooling as an explicit prerequisite task. Do not replace it with undocumented manual measurements.

**Complete when:** Local workload checks pass, the workload produces all approved metrics, and the exact cloud commands can be resolved from repository scripts/documentation.

## EXP-03 — Implement and locally verify the mixed configuration

**Owner:** B. **Reviewers:** C and D; affected contract owners where required. **Start after:** EXP-02.

1. Inspect the approved EXP-01 manifest, actual integrated read operations, auth context, database access, generated API contract and accepted revision. Identify shared application logic that can be reused without importing another domain's private implementation.
2. Propose the minimal Lambda packaging/adapter, ingress/routing, authorized request-context handling, PostgreSQL connection limits, concurrency/timeouts, logging and failure behavior. Preserve state-changing routes on ECS; present any unresolved compatibility/security/cost decision and wait for approval before dependent implementation.
3. Implement the Lambda entry/adapter and packaging using the frozen public operations and shared authorized logic. Preserve status/error/response semantics, filters, ordering, pagination, availability and privacy. Add unit/contract/parity tests for success, invalid/auth/forbidden/not-found, database failure and timeouts; no cloud measurement yet.
4. Implement the configuration-A/B selection/routing path and build scripts with explicit targets and reversible configuration. Prove local routing tests keep writes/chat/offers on ECS and select only the approved reads for Lambda.
5. Prepare scoped Terraform/runtime configuration for the Lambda, ingress/routing, roles/network/database access, resource/concurrency caps, telemetry and retention. Reuse shared datastore/resources. Register exact plan/build/deploy/verify/rollback/cleanup commands in canonical records; run static checks and inspect the plan without applying it.
6. Run pinned Black and applicable tests/type/build/contract/CI gates; review packaged artifacts and privacy-safe diagnostics. Record configuration fingerprints and parity results; obtain peer PR review and merge the accepted implementation. Keep exact human-reviewed plan/apply/deployment gates for EXP-04.

**Complete when:** Mixed-path implementation, packaging/routing, parity tests and scoped infrastructure plan/scripts are reviewed and merged; neither deployment nor measured improvement is claimed complete.

## EXP-04 — Integrate and smoke-test both configurations

1. Follow the project's task, review, CI, merge, and deployment gates. This experiment task does not authorize an agent to approve or merge its own code.
2. Inspect/approve the exact resource and deployment plans for A/B (account/role/region, add/change/delete, exposure, cost/reserve, duration/caps, rollback, cleanup/retention). Wait for explicit human approval and apply only that plan. Then deploy configuration A using the documented infrastructure workflow. Record actual account/profile, region, environment, application revision/image digest, frontend revision if applicable, migration head, and resource settings.
3. Verify A is healthy and the benchmarked read routes really execute in ECS.
4. Deploy or select configuration B using the documented workflow. Record the exact Lambda/ECS routing and settings. Verify the selected routes really execute through Lambda and remaining/state-changing routes remain on ECS.
5. For each selected route, compare representative response content and authorization behavior between A and B. Confirm both read the same authoritative data and preserve filtering, sorting, pagination, not-found behavior, and access restrictions.
6. Confirm logging and metrics can distinguish ECS and Lambda paths without logging sensitive data. Confirm PostgreSQL remains private and is the same authoritative datastore for both configurations.
7. Run small, bounded cloud smoke tests. Do not call them measured results.
8. If either configuration fails smoke tests or differs functionally, stop measurement. Fix the issue through its own task/review/deployment path, then repeat the smoke checks.

**Complete when:** Both deployed configurations are healthy, functionally equivalent for the frozen routes, correctly instrumented, and identifiable by immutable revision/configuration.

## EXP-05 — Pilot and confirm safe limits

1. Re-read the approved manifest, exact environment/resource targets, remaining project budget, and cleanup commands.
2. Verify the load generator has enough capacity for the requested workload and will not exceed its approved virtual-user/concurrency cap.
3. Run a short pilot on A, then B, using identical data and workload settings. A pilot is not an NFR run and must not be reported as one.
4. Check that scheduled request rates are actually achieved, requests are not dropped by the generator, telemetry aligns to the run, expected response checks work, and the DB or runtime is not affected by unrelated traffic.
5. Estimate the full planned batch from pilot duration/resource usage and current provider prices. Include warm-up, run time, idle/transition time, both configurations, database, ingress, logs/monitoring, and any temporary resources. Record assumptions and billing-data delay.
6. Verify the estimate plus the approved reserve fits the project's remaining USD 200 budget. Confirm each run has a declared maximum duration and resource/concurrency caps.
7. If the pilot reveals an unsafe cap, generator limit, unexpected scaling/cost, unavailable metric, or unclear result, stop. Present options and a revised plan for human approval; do not tune quietly.

**Complete when:** The pilot validates the measurement setup and the approved batch remains within the budget and resource limits.

## EXP-06 — Run the measured comparison

For every approved run:

1. Assign a unique run ID and record configuration A or B, workload, repetition, manifest version, and planned UTC start time.
2. Reconfirm the deployed revision, resource settings, route placement, data fingerprint, healthy state, approved budget headroom, and absence of concurrent deployments/data changes.
3. Start workload and resource/DB telemetry using the exact manifest commands. Record the actual start time.
4. Apply the approved warm-up. Keep warm-up samples separate from the measured interval.
5. Execute the complete approved measured duration. Do not shorten a five-minute PRD performance window. Do not alter routes, workload, thresholds, scaling settings, or data during a pair.
6. Stop starting new requests at the scheduled end and follow the frozen drain/timeout policy for requests already started. Record actual end and drain times.
7. Export raw latency/outcome data, generator health/dropped work, ECS/Lambda metrics, database metrics, configuration snapshots, and cost inputs.
8. Verify the run reached the offered rate, all required metrics exist, the correct runtime served each route, and no uncontrolled change invalidated the pair.
9. Mark each run **valid**, **invalid**, or **incomplete**, with the reason. Preserve failed and invalid runs; never delete an unfavorable result or relabel application failure as a tooling failure.
10. Perform the approved between-run transition and verify the next configuration is stable before starting its warm-up.

Run paired configurations close enough in time to reduce time-of-day/environment drift. Follow the approved order and repetition count; do not choose order after seeing results. If any code, resource, dataset, route, or workload setting changes, create a new manifest version and rerun both sides of the affected comparison.

**Stop and ask** if the account, target, permission, cap, metric, expected result, failure cause, or safe next action is uncertain. If a valid run shows poor performance, preserve it as a result and create/fix the responsible task before any new comparison.

**Complete when:** All approved run pairs are captured, validity is justified, and no incomplete run is presented as a pass.

## EXP-07 — Analyze and report

1. Group runs by manifest version, workload, configuration, and repetition. List invalid, interrupted, and failed runs with their exclusion reason before summarizing.
2. For every configuration/workload, report p50, p95, and p99 end-to-end latency; offered and successful throughput; failure, timeout, and throttling rates; dropped generator work; and request counts.
3. Report ECS healthy/running task counts and scaling timeline; Lambda concurrency, errors, throttles, duration and cold-start behavior; PostgreSQL latency/connections/saturation indicators; and measured or estimated costs.
4. Use the same metric and cost calculation method for A and B. Report per-run results and variation across repetitions. Do not call the average of per-run p95 values a pooled p95.
5. Compare normal-load performance, burst behavior, cold and warm observations where applicable, database bottlenecks, and cost together. Show cost per a fixed quantity of successful requests, such as cost per 1,000, and label estimates and billing lag.
6. Explain differences in configuration and measurement limits. State conclusions only for the tested routes, dataset, workload, region, and resource settings.
7. Map each claim to its run IDs and exact deployed revision/image/configuration. Link the result to task/NFR evidence without claiming that this document completed domain-specific NFR steps.
8. Have a reviewer check selected calculations from raw data, validity exclusions, fairness, cost method, evidence privacy, and cleanup status.

**Complete when:** Another teammate can reconstruct the comparison from its manifest, synthetic data/workload versions, raw results, calculations, and actual deployed configuration.

## EXP-08 — Clean up and close the experiment

1. Stop generators, scheduled runs, and any controller that could recreate experiment resources.
2. Identify exact temporary targets from the approved manifest and resource inventory. Do not guess from console names.
3. Review the repository-managed cleanup plan, dependencies, cost, and retained resources. Obtain any required human authorization for the exact cleanup target.
4. Tear down temporary resources through the documented Terraform/lifecycle route. Preserve the shared development baseline and retained backups.
5. Run the documented verification after teardown. Check that no unplanned ECS tasks, Lambda capacity, database copies, load balancers, storage, logs, schedules, or other billable resources remain.
6. Record what was removed and what remains, with owner, cost, expiry, and next cleanup action. Update the environment/inventory records if deployed state changed.
7. Keep sanitized raw results and analysis in their agreed repository location. Do not retain tokens, private keys, live identity data, or decrypted message content.
8. Record task status, files/tools changed, local/cloud checks actually run, exact revisions, run IDs, result, costs/estimates, cleanup, unresolved issues, and next action.

**Complete when:** The reviewed comparison report is reproducible, the result is tied to exact deployed revisions, and temporary resources are verified removed or explicitly retained with an owner and expiry.

## 10. Measures required by the PRD's comparison

The experiment report must include:

- p50, p95, and p99 end-to-end request latency.
- Offered throughput (requests the load generator attempts to start) and successful throughput (requests completed before client timeout with the expected status and response checks).
- Request failures, timeouts, and throttling.
- ECS task health/count/scaling; Lambda concurrency, cold-start behavior, errors and throttling; PostgreSQL latency, connections, and saturation indicators.
- Measured or estimated experiment compute cost and cost per fixed successful work, such as per 1,000 successful requests.

Define the exact latency boundary, quantile method, success response checks, timeout treatment, billing allocation, workload, and run repetition before measured runs. k6 arrival-rate executors schedule iterations, so convert iterations to actual HTTP request rate explicitly. Keep generator-dropped work visible; it cannot count as load delivered to the application. k6's built-in `http_req_duration` does not include initial DNS/connection times, so use the approved end-to-end client timing boundary and retain phase metrics for diagnosis.

The PRD asks whether the mixed configuration improves peak responsiveness or cost efficiency without degrading normal-load performance. Compare both dimensions; do not force equal cost or latency. A shared PostgreSQL bottleneck must be reported because it can limit either configuration.

## 11. Source references

- Submitted source: `docs/source/ICC_Project_PRD_FINAL.pdf`, Sections 5–7; implementation baseline and information ownership: Document 1, `product-reference-and-architecture-decisions.md`.
- [k6 constant arrival-rate executor](https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/constant-arrival-rate/), [dropped iterations](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/dropped-iterations/), and [built-in metrics](https://grafana.com/docs/k6/latest/using-k6/metrics/reference/).
- [AWS Lambda execution environment lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html) for initialization/reuse and cold-start observations.
- [AWS Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html) for cost-data refresh limits; reconcile estimates with later billing data.

## Execution and closeout routing

EXP-01–EXP-08 run in dependency order. Task owners/reviewers are listed in the project task index; every step reports expected and observed results, evidence, work-log checkpoint and verification state. Shared environment configuration changes/runs are serialized by the named operator; no parallel deployment may contaminate a measured pair. Preserve invalid runs and do not call an incomplete check a pass. Changed configurations require updated approvals and both sides of affected paired measurements rerun.

EXP-08 records experiment cost/cleanup and routes to CLOSE-00 in `docs/tasks/final-closeout-task-list.md`. CLOSE-00 performs full-project cost reconciliation including this experiment and final regression/submission evidence. Optional work follows its separate technical/priority gates, never silently alters a frozen experiment revision.

## Real dependency restriction

Early local domain work may use reviewed test doubles under the canonical stub guide. This comparison still requires actual integrated/authenticated ECS/Lambda paths, real routing/parity/deployed revisions and approved resources/workloads. No stub-only service, dataset preview or simulated timing establishes comparison/NFR evidence. Recheck the pending-integration ledger before run acceptance.
