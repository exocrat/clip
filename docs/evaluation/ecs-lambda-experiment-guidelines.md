# Guidelines for Defining the ECS-only vs ECS+Lambda Experiment

**Purpose:** mandatory design guidance for NEXT-01 and the later EXP-01 task.
This file defines how to prepare a defensible experiment; it does not select the
winner or claim that the experiment has been designed or run.

## Priority labels

- **Essential:** needed for a defensible comparison. Simplify the experiment's scope before dropping these.
- **Conditional:** include when the stated condition applies.
- **Extra — time-consuming:** useful for stronger evidence; omit unless it could change the decision or resolve an important uncertainty.

## 1. Requirements and decision rules — Essential

First identify the non-negotiable FRs and NFRs from the approved project requirements. An architecture failing any applicable mandatory requirement is ineligible, regardless of advantages elsewhere. Missing or inconclusive evidence is not a pass. Reuse valid existing evidence; recheck behavior affected by the alternative architecture. Do not repeat unrelated domain testing.

Compare eligible alternatives using the user's weighted score method:

1. Identify and rank the objectives that are desirable beyond minimum compliance.
2. Agree on numerical importance weights; ranking alone does not specify their relative magnitude. Normalize weights to sum to 1.
3. Map each metric to a common bounded points scale. Specify units, whether higher/lower is better, numerical score ranges, boundary handling, and caps. Qualitative objectives need observable criteria.
4. Calculate total = sum(weight × metric points).
5. Show raw measurements and individual contributions alongside totals. Avoid double counting closely related objectives.

Agree on requirements, weights, score ranges, workload aggregation, and a practical tie rule **before inspecting final comparative results**. Do not adjust them to favor an outcome. Missing measurements cannot silently receive invented scores.

Weights express agreed preferences; the calculation makes their application consistent and transparent, rather than making those preferences objectively true. Check briefly whether plausible weight changes or measurement noise near a score boundary change the winner. If so, report that sensitivity.

## 2. Comparable work and fair controls — Essential

Define exactly what changes between alternatives and what constitutes correct completion. Both must implement equivalent business behavior, authorization, validation, data access, query semantics, and outputs. HTTP 200 alone does not establish correctness.

Keep relevant conditions equal where possible: application logic, dataset and indexes, request/query mix, payload size, region, client location, dependencies, timeout/retry policy, cache/connection state, and instrumentation. Record unavoidable differences and their implications.

ECS and Lambda resource settings are not automatically equivalent. Choose and justify the comparison basis. A complete-architecture comparison may include necessary differences in ingress, allocation, and scaling; its conclusions concern those configurations. To isolate a particular cause, change one factor at a time in a separate controlled comparison.

Avoid unrelated deployments, teammate load, or competing runs against shared dependencies during measurements. Apply consistent reset/warm-up policies and alternate or randomize run order where practical to reduce time-order bias.

## 3. Workload and timing — Essential

Use a small justified set of representative conditions. Steady traffic, intermittent traffic, and bursts can favor different architectures; include those relevant to the intended use rather than an exhaustive test matrix. Preserve relevant route/query classes and read/write interference when that affects the decision.

Specify offered load, request mix/data, phase duration, warm-up, repetitions, and timeouts. Record actual achieved load as well as intended load.

**Load terminology:** threads, requests/s, in-flight concurrency, server attempts, and successful completions/s are different quantities. A closed-loop client waits for responses, so it sends fewer requests when the service slows. This can hide overload and tail latency (**coordinated omission**). Choose a generator model matching the intended arrival pattern; record missed scheduled arrivals and generator saturation.

Warm-up → measured load phases → cool-down is a useful structure. Compare stable intervals for steady-state claims, but retain transient intervals when measuring burst response or scaling. Phases must be long enough for relevant initialization, scaling, and telemetry windows to be visible.

Use equivalent timing endpoints. Request acceptance, API response, and verified completed work are distinct. For asynchronous work, acceptance latency cannot be compared directly with another design's completed-work latency.

## 4. Outcomes and failure accounting — Essential

Measure these together for each relevant condition:

- Client-observed latency distribution, including median and an adequately sampled tail percentile.
- Offered and achieved load, verified successful throughput, and sample counts.
- Success share, errors, timeouts, throttles/rejections, and retry counts.
- Cost using the same workload, period, and successful-completion definition.

Define success at the logical-operation level and distinguish operations from retry attempts. Fast rejection can improve an overall latency percentile while useful performance worsens. Report successful-request latency alongside failures; do not silently exclude failures or classify timeouts as ordinary successful observations. A timed-out server operation may still finish and consume resources.

Mean latency can hide slow tails. A measured maximum is only the largest observation. Small samples provide unstable p95/p99 estimates; do not make strong tail claims from a handful of requests.

## 5. Cold starts, resources, and scaling — Essential where they affect the comparison

Separate first-call/cold behavior from warmed steady state. State how cold samples are obtained and verified; a slow first request or assumed idle timeout alone does not prove initialization. Lambda initialization telemetry supports a cold-start classification, but does not identify which initialization stage dominated.

A recently invoked function may still create additional cold environments under a burst. Warm function state, warm database caches, and reused connections are separate effects. Warm local state is an optimization, not durable authoritative storage.

Record allocations and limits rather than assuming resources are unlimited. Lambda memory allocation can affect CPU/time/cost; the smallest memory allocation need not be cheapest. Under stable conditions, concurrency is approximately arrival rate × average duration; downstream waits increase occupancy.

Reserved concurrency caps/allocates concurrency; provisioned concurrency prepares initialized capacity and has a cost. Neither expands database capacity. Record downstream connection limits and other binding quotas. Excess synchronous requests may be rejected; buffering/retries depend on invocation type and source.

For ECS, distinguish desired, running, healthy, and actually serving task capacity. For EC2-backed ECS, service task scaling and host-capacity scaling are separate. Startup, image pulls, readiness checks, load-balancer registration, routing, and scale-in delays matter. More replicas only help if they address the bottleneck; they can increase database contention instead.

**Conditional:** inspect burst-credit state if burstable compute/database resources could distort short versus sustained results. Inspect connection reuse or routing skew if additional replicas receive uneven traffic.

## 6. Measurement validity and diagnosis — Essential

Client timing and handler timing cover different boundaries. High latency with low CPU may indicate database/I/O/pool/queue waits. Correlation is not a root-cause proof; use the smallest additional signal that distinguishes plausible explanations.

Use existing telemetry where sufficient. Ensure it actually records known test traffic, uses aligned time windows, and is retained with raw client results. Missing telemetry is not zero. Record UTC phase boundaries; export, batching, scrape, query-window, and dashboard delays can smooth or shift apparent events.

Percentiles cannot be averaged across replicas/routes to obtain a combined percentile. Combine raw observations or compatible histogram buckets, then calculate it. Likewise, client p95 minus server p95 is not the p95 of network overhead. Keep histogram units/boundaries consistent and sufficiently fine near decision thresholds.

**Conditional — when using Prometheus:** apply reset-aware rate() before aggregation; retain le when aggregating histogram buckets. Rate windows need multiple scrapes. Distinguish errors/s from errors/requests. Record exact queries and windows.

**Conditional:** correlate slow/failed requests across layers using existing request IDs, logs, or traces when component attribution matters. Avoid high-cardinality metric labels such as request IDs, user IDs, or raw search queries; exclude secrets and private data.

**Extra — time-consuming:** introduce distributed tracing or a new monitoring stack only if existing evidence cannot answer a decision-critical question. A large observability deployment is not a prerequisite for a small rigorous comparison.

## 7. Repetition and interpretation — Essential

Repeat measurements and report central values plus spread across runs, not just many requests from one run. The notes suggest 3–5 measured runs as a classroom starting pattern; sufficiency depends on noise and the size of the difference. Thousands of correlated requests are not independent infrastructure repetitions.

Define durations/sample targets, exclusions, and stopping rules in advance. Preserve failed/aborted runs and reasons. Do not stop when a favorable result first appears. Keep exploratory tuning separate from final evidence and allow both architectures a comparable tuning opportunity.

Distinguish a measurable difference from a practically worthwhile difference. If observed differences are small relative to variability, report insufficient resolution. Overlapping ranges do not prove equality; normalization does not repair unfair controls. Retain absolute values, units, and formulas even when presenting ratios or scores.

**Extra — time-consuming:** formal power analysis, advanced uncertainty modeling, or sequential testing when the decision hinges on a small difference. Prefer a fixed, modest protocol and an honest inconclusive result over unsupported precision.

**Conditional — live A/B traffic only:** define randomization unit, allocation, carryover/interference, important segments, and guardrails. Canary safety evidence is not automatically causal comparative evidence. Live A/B testing is not required merely to compare controlled synthetic workloads.

## 8. Whole-system cost and bounded execution — Essential

Compare the full ECS-only system with the full ECS+Lambda system. ECS remains in the hybrid design: read offloading saves money only if paid capacity or another actual cost decreases. Show incremental cost separately if useful.

Include applicable compute/idle capacity, Lambda billable allocation-duration and invocations, prepared concurrency, ingress/API services, database, networking, storage, logs/metrics, retries, and retained resources. Allocate shared costs consistently without double counting.

Report total cost and cost per verified successful operation. Distinguish measured billing, usage-based estimates, and longer-period projections. Record region, pricing date, period, units, and assumptions; verify current prices/limits during design. Show comparable pre-credit cost separately from credit consumption where credits obscure the comparison. Operational effort is a separate criterion from provider charges.

Keep approved duration/load/concurrency/resource caps and cleanup ownership explicit. Budgets/alerts can lag and are not hard spend limits. Preserve evidence, remove only experiment-owned resources, and verify residual billable resources/controllers. Zero tasks does not imply zero cost; retained disks, load balancers, addresses, logs, object versions, and registry artifacts may remain.

## 9. Minimum reproducibility and reporting — Essential

Record enough to reconstruct each run: commit, image digest/function version, configuration/resource limits and scaling settings, runtime/tool versions, region/topology, dataset fingerprint, workload/seed, commands, UTC intervals, actual load, raw results, calculation method, deviations, and cost basis.

Verify the intended deployed versions/routes and correct outputs before interpreting timing. Deployment success, a running process, or a successful invocation does not establish end-to-end correctness. Keep applicable security/permission requirements intact.

The report needs eligibility evidence, configuration differences, workload/run conditions, raw comparative metrics with variability, cost assumptions, weighted score contributions/sensitivity, and limitations. State whether a conclusion is supported under the tested conditions; allow neither-eligible, practical-tie, and inconclusive outcomes.

## 10. Where to save time

- Keep the scenario matrix and tuning search small and justified.
- Reuse current fixtures, scripts, infrastructure, monitoring, and valid requirement evidence.
- Measure user-visible outcomes first; add detailed diagnostics only for important unexplained results.
- **Extra — time-consuming:** broad memory/CPU sweeps, exhaustive stress limits, multi-region tests, new fault-injection campaigns, elaborate dashboards, live traffic experiments, and extensive causal microbenchmarks. Include only when required or likely to change the decision.
- Required FR/NFR evidence remains mandatory. If time cannot support a required claim, narrow the conclusion or report the evidence gap rather than treating the check as optional.
