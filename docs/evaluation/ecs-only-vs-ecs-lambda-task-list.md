# Campus Marketplace — ECS-only vs ECS+Lambda Experiment Task List

**Canonical repository path:** `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md`
**Document 2. Status:** Working task list for the PRD's primary cloud experiment. It does not report experiment results; none have been run while preparing this document.

**Entry:** EXP-01 design may start before INT-01. EXP-06 may run before full INT-01 only after the real selected paths, DATA-READY, EXP-01–05 and the approved read-comparison gate below are verified. Full INT-01/Notifications acceptance remains required for project closeout. Select tasks through `docs/tasks/project-task-index.md`; human verification and action approvals remain separate.

**Purpose:** Determine whether routing selected read-heavy requests from ECS to Lambda improves burst responsiveness or cost efficiency without degrading normal-load performance for this application.

**2026-11-03 user direction:** Revise configuration B to send selected reads to
Lambda first, with excess requests served by ECS when Lambda has no capacity.
The ALB sends all requests to ECS in both configurations. In B, the ECS router
invokes Lambda first for selected Listing GETs and serves the same request on
ECS only after a confirmed Lambda throttle. Other routes stay on ECS. The task
list, design and Terraform draft now reflect that topology; workload/evidence
updates and affected-owner/peer review remain pending. Preserve per-service
attribution and whole-system costs so the mixed result is interpreted correctly.

This is a task list for that comparison. Step-by-step procedures for testing individual NFRs belong in the relevant domain task lists, at the first point when the integrated product makes those tests accurate. If a specific NFR has no earlier accurate test point, include its detailed procedure here as a named integrated verification task, as previously directed. Keep that exception narrow: Document 2 remains focused on the ECS-only versus ECS+Lambda comparison and must not imply that an unrelated NFR was measured by the comparison.

## 1. Experiment boundary

Compare these two configurations:

| Configuration | Request handling |
|---|---|
| **A — ECS-only** | ECS serves all benchmarked read-heavy API requests. |
| **B — ECS+Lambda** | ECS sends selected read-heavy API requests to Lambda first; a confirmed Lambda capacity rejection serves that same request through ECS. Other application routes remain on ECS. |

Both configurations must use PostgreSQL as the authoritative datastore. State-changing requests stay on ECS in both. The selected routes should come from the implemented, integrated product and its generated API contract; the PRD names browsing available listings, retrieving listing details, and searching/filtering listings as candidate read-heavy operations.

The experiment compares the complete user-facing request path under the chosen deployment, including its ingress and routing. For browse, exclude image-body transfer as specified by the PRD. It records latency, offered and successful throughput, failures/timeouts/throttling, runtime behavior, database behavior, and cost. It does not decide that one compute service is universally better.

### Keep out of this task list

- The step-by-step tests for NFR-01 through NFR-07 when the relevant behavior can be tested accurately in a domain task list. Put each there after its feature and required integrations are complete. If a specific NFR has no earlier accurate test point, include its step-by-step process as a clearly identified integrated verification task in this document; do not test partial behavior or present an unrelated NFR as an ECS/Lambda comparison result.
- Project-wide NFR-08 accounting outside this experiment. This task still declares caps and estimates the comparison's cost before running it.
- General agent prompts, session checklists, PR/merge instructions, and reusable human workflow. Those belong in their designated documents.
- Optional wanted-match notifications, weekly digest, and image-aware search. These do not belong in the required comparison.

## 2. Start conditions

Start the measured comparison only when:

- NEXT-03's selected behavior and NEXT-04's relevant integrated app, real sign-in and selected read routes are verified through the normal authorized path.
- ECS-only behavior is healthy. The mixed configuration is implemented and returns equivalent authorized results for the selected routes.
- The selected read-path correctness and relevant checks pass on real integrations; unrelated domain completion stays tracked under its owning task.
- DATA-READY is accepted; final dataset, image references, route behavior, database schema/indexes, model and monitoring are verified for the selected paths.
- EXP-01 is approved; EXP-02's real-target tooling is checked; EXP-03 is reviewed and merged; EXP-04's deployed routing/auth/parity checks and EXP-05's pilot pass. Record exact revisions.
- The current environment and resource inventory identify the actual account, region, resources, owners, and cleanup route.
- Project budget and capacity limits have enough remaining headroom for this experiment and pending required work.
- Exact deployment, run and cleanup plans are separately approved; A/B worker settings match and any absent background delivery is disclosed as a limitation. Later material changes trigger affected paired/NFR rechecks.

If a condition is missing, make it an explicit prerequisite task or ask the human to resolve the blocker. Do not start measured runs against a partly built feature or an unknown environment.

## EXP-01 — Choose and freeze the comparison design

Before changing code or deploying experiment resources:

1. Read the submitted PRD, Document 1, current architecture/environment records, approved decisions, generated API contract, and available feature-task evidence for the candidate routes. Record unfinished work and assumptions.
2. Inspect the current implementation and planned deployed path. List the read routes that can be compared and any route that cannot be safely or fairly offloaded. Confirm the actual integrated and deployed path before measured runs; revise the design with human approval if a material assumption changes.
3. Present the human with feasible choices for:
   - The exact routes to benchmark and the reason each is representative.
   - A normal workload and a burst workload, including route proportions and the point at which the burst begins and ends.
   - Request distribution, payloads, filters, page choices, cache behavior, user mix, and arrival-rate method.
   - Resource settings for ECS, Lambda, PostgreSQL, and ingress, including scaling/concurrency limits.
   - Generator location, warm-up and measurement durations, client timeout, repetitions, run order, cold/warm treatment, metrics, and cost attribution.
   - Time/concurrency/resource caps, stop conditions, estimated cost, and remaining-budget reserve.
4. Include the PRD's required conditions when applicable: synthetic reference data of at least 1,000 listings and 5,000 users; at least five minutes of performance measurement after warm-up; warm and cold behavior reported separately where applicable; each load run's maximum duration and resource/concurrency caps declared before execution.
5. Explain tradeoffs, expected evidence, and any unresolved questions. Recommend one complete plan. Do not silently fill a value that changes workload meaning, comparison fairness, security, cost, or cloud resources.
6. Obtain the human's choices/approval and record the design in the repository manifest. Specify decision rules and proposed values early; identify deployment-dependent assumptions and commands to confirm after integration. Before measured runs, resolve those items and approve the final runnable manifest without changing rules to favor a result.

**Complete when:** The human-approved plan fixes the routes, workload, data, resources, run limits, metric definitions, cost method, run order/repetitions, evidence location, and cleanup action. The design specifies a feasible comparable implementation and run plan within the budget; configuration B is implemented in EXP-03 and deployed/verified in EXP-04 before it is considered runnable.

### NEXT-01 Step 1 — Question and requirement framing

**State:** verified by Suraj on 2026-10-27. Weights and executable settings await
their ordered NEXT-01 steps. Source implementation: main `5e8d264`, confirmed against
GitHub on 2026-10-27. Planning baseline: `c869f33`.

**Question:** For this marketplace's low, normal and burst traffic, does moving
selected authenticated browse/detail/search requests from ECS to Lambda improve
peak responsiveness or whole-system cost efficiency while preserving normal-load
performance, correct behavior and applicable mandatory requirements?

**Decision informed:** choose the final deployed configuration from eligible
tested alternatives using the pre-agreed weighted score and practical tie rule.
The final deployment follows the supported result, including ECS+Lambda if it
wins. A practical tie, inconclusive evidence or neither alternative being eligible
must remain possible outcomes. A result applies to the tested routes/settings.

The [submitted PRD](../source/ICC_Project_PRD_FINAL.pdf), sections 4–7, and
[Document 1](../product/product-reference-and-architecture-decisions.md), sections
3–5, currently specify ECS-only versus selected read offload with writes,
conversations and offers on ECS and PostgreSQL authoritative. NEXT-01 Step 2
confirms that boundary before implementation. The
[experiment guidelines](ecs-lambda-experiment-guidelines.md) require mandatory
eligibility before scoring, equivalent correct work, explicit failure accounting,
repetitions, separate cold/warm observations and full-system cost attribution.

| Required baseline | Implication for design |
|---|---|
| FR-01–03, FR-05–07, FR-14, FR-17 | Preserve identity/eligibility, availability/ownership, pagination, search/filter/order semantics, image references and sensitive-purchase presentation on selected reads. |
| Other required FRs, including FR-13 and FR-16 | Retain full product acceptance, asynchronous notification failure isolation and client-only private-message decryption. Read offloading does not accept unrelated unfinished features. |
| NFR-01 | At 20 browse requests/s, at least 95% of successful requests within 1 s; exclude image bodies and report failures separately. |
| NFR-02 | At 10 indexed search requests/s, at least 95% of issued eligible requests correct within 1 s; owning SE-01 procedure counts failures/timeouts as violations. |
| NFR-03 | At 50 requests/s for five minutes, at least 95% successful, excluding intentionally rate-limited abuse. |
| NFR-04 | Success@5 at least 80% over at least 20 human-reviewed queries. |
| NFR-05 | At least 95% of active-chat messages visible within 5 s under the defined normal workload. |
| NFR-06–07 | From at least two healthy serving instances, restore capacity within 240 s after runtime loss; restore latest managed backup to a usable test DB within 30 minutes. |
| NFR-08 and reference workload | Total project cloud spend below USD 200; caps before each run; at least 5,000 synthetic users/1,000 listings; at least five measured minutes after warm-up; distinguish relevant cold/warm behavior. |

**Current implementation and assumptions to confirm:**

- [Generated API](../../contracts/generated/openapi.json) and current route code
  expose browse/search through `GET /listings` and detail through
  `GET /listings/{listing_id}`. The website-serving app mounts these under `/api`.
  These are candidate operations; exact selection is a later design checkpoint.
- [Application composition](../../apps/api/app/application.py) binds real domain
  providers. Older handoff prose saying Conversations is still declaration-only
  is superseded by this code; full integration acceptance remains pending.
- Product search is intended to use Hybrid only. Merged PR #15 removed the
  website mode control and made Hybrid the default, although current code still
  accepts legacy Keyword URLs and an API mode. The current website defaults to
  newest-first; NEXT-03 Step 3 will make word-first relevance the default for a
  nonblank search using the existing relevance ordering. Hybrid needs its local
  model, read pool and vector pipeline. Compare the same intended Hybrid behavior
  in both architectures and confirm its readiness and limits before running.
- NEXT-03 changes filters/taxonomy and NEXT-04 audits/completes integration.
  Confirm resulting public contracts, authentication, image behavior and runtime
  topology before final freeze. NEXT-06 supplies final data and reviewed labels.
- [Existing k6 tooling](../../scripts/evaluation/k6/README.md) supplies bounded
  local pilots and draft NFR profiles; its current runner refuses full-rate/cloud
  runs. Final workload/tooling preparation stays in EXP-02 rather than being
  inferred from those local results. Mixed-runtime implementation is EXP-03.
- [Cloud inventory](../environment/cloud-inventory.md) records stopped shared
  capacity as of October 26; this review did not query live AWS state or establish
  a running integrated deployment, current prices or remaining budget.
- Current Conversations code records notification intents within the owning
  transactions. Email delivery is not a technical dependency of these selected
  read operations. NEXT-01 Step 8 approved the read-specific measured-run gate;
  full INT-01/FR-13 acceptance remains separate.

### NEXT-01 Step 2 — Deployment alternatives

**State:** verified by Suraj on 2026-10-27. Suraj directed that the
comparison follow the PRD and be rigorous while quick to perform. PRD section 7
specifies the two alternatives below; a broader Lambda-only application is not
part of this comparison.

| | A: ECS-only | B: ECS plus Lambda |
|---|---|---|
| Selected marketplace reads | ECS handles the benchmarked reads. | Lambda handles the selected benchmarked reads. |
| Other app operations | ECS handles the remaining application. | ECS continues to handle the remaining application, including writes, conversations and offers. |
| Data | Uses the authoritative PostgreSQL dataset and relevant indexes. | Uses the same dataset and relevant indexes. |

The PRD's read candidates are available-listing browse, listing detail and
search/filter. On current main, browse and search use `GET /listings` with
different query inputs; detail uses `GET /listings/{listing_id}`. These are
candidates, not a final route selection. Use the same approved Hybrid search
behavior in both alternatives; confirm NEXT-03's final ordering and filters.
Image-body transfer is excluded from the browse latency requirement, although
image references and access behavior must still be correct.

Before any measurements, the Lambda path must preserve the actual caller and
eligibility checks, available/owner-visible listing rules, filters, ordering,
pagination, errors and response fields. It must access the same private data
and current search model and index coverage. A successful HTTP response alone
does not establish equivalence. In particular, a Keyword-only or partial search
substitute would not represent the intended Hybrid product behavior.

The current Search runtime uses a separately managed model helper and database
connections. A Lambda implementation that reproduces this behavior has not yet
been demonstrated; EXP-03 must resolve packaging, startup, authentication, database
connections and resource limits, then test parity. If a route cannot be made
equivalent, do not silently move it or claim a comparison for it; return the
feasibility issue for review. EXP-04 separately deploys and verifies both paths.

Keep the comparison small: reuse existing workload tooling and valid evidence,
use a small justified set of normal and burst conditions, and repeat the
measured pairs. Freeze exact routes, traffic, settings, repetitions, limits and
decision rules in later design steps before final results. Required PRD checks,
correctness and useful failure/cost measurements remain mandatory even when the
comparison is shortened. Final data, live deployment and the approved real-path
measured-run prerequisites remain pending; no experiment has been run.

### NEXT-01 Step 3 — Proposed eligibility and decision rules

**State:** verified by Suraj on 2026-10-28; not yet a runnable protocol.
Freeze these rules before examining final comparative results. Step 4
must specify the workloads and Step 7 must confirm the cost and resource inputs.

#### Eligibility

1. Both paths must serve the same selected reads correctly, including real
   caller eligibility, matching/filtering/order, availability, pagination,
   expected errors and response contents. Their measured workload, dataset,
   indexes, region, client location, timing boundaries and retry rules must
   match. Record unavoidable deployment differences, alternate measurement
   order, and prevent competing work on shared resources. A failed parity or
   invalid measurement is not a pass.
2. Apply the PRD's required FRs and NFR-01–08 listed in Step 1. Reuse valid
   evidence tied to the actual version and configuration; repeat checks affected
   by a change. For final eligibility, unmet mandatory behavior or a failed NFR
   makes an alternative ineligible. Missing evidence means eligibility is unknown,
   not a pass. A read-only comparison may be analyzed for its stated scope if its
   separately reviewed run gate permits it; FR-13, full INT-01 and final product
   eligibility remain pending until their real checks pass.
3. In each scored workload, propose at least 95% of issued logical operations
   complete correctly within the agreed timeout. Count wrong results, failures,
   timeouts and throttles as unsuccessful; separately report retries and dropped
   scheduled arrivals. Generator shortfall or an invalid run cannot establish
   eligibility. This floor limits, but does not eliminate, the risk that fast
   failures make the successful-response times look better.
4. To operationalize the PRD's no-normal-degradation condition, propose that
   for **each selected read class** in the normal workload, B's median successful
   p95 across valid runs may exceed A's by at most the larger of 50 ms or 10% of
   A's median p95. B's normal failure share may exceed A's by at most one
   percentage point for each class. Both must also meet the PRD targets and the
   success floor above. Treat a measured failure of either bound as B failing
   this proposed guard; insufficient observations make the result inconclusive.
   These tolerances express a proposed practical definition, not proof that two
   systems are identical. Step 4 must define class counts and valid repetitions.
5. Project cost must remain below USD 200 overall, with adequate remaining
   budget and approved caps before a run. The final total is checked at CLOSE-00;
   a preliminary comparison cannot assert that final NFR-08 is already passed.

#### Proposed weighted score

Score only alternatives that satisfy the comparison checks above; treat the
result as provisional while any unrelated final-product requirement lacks valid
evidence. If a required score input is unavailable, do not assign it a value.
The weights below express a proposed preference for burst response and cost while
also valuing normal responsiveness and reliability; they are not inferred from
the PRD. Reliability is separately scored because the 95% floor alone permits a
meaningful difference in failures between otherwise qualifying configurations.

| Objective | Weight | Input, lower is better | 100 points at or below | 0 points at or above |
|---|---:|---|---:|---:|
| Burst tail latency | 0.35 | Median per-run p95 of successful operation latency in the burst workload, ms | 500 ms | 3,000 ms |
| Whole-system cost | 0.30 | Pre-credit whole-system cost per 1,000 correctly completed logical operations during the normal workload | Set from the reviewed cost model before final runs | Set from the reviewed cost model before final runs |
| Normal tail latency | 0.20 | Median per-run p95 of successful operation latency in the normal workload, ms | 250 ms | 1,000 ms |
| Reliability | 0.15 | Larger of the median per-run failure percentages in the normal and burst workloads, percentage points | 0% | 5% |

For a metric value `x` between its two anchors `good` and `poor`, compute
`points = 100 * (poor - x) / (poor - good)`; cap at 100 below `good` and 0
above `poor`. Include both endpoints in the cap. Total points are
`0.35 * burst + 0.30 * cost + 0.20 * normal + 0.15 * reliability`, on a 0–100
scale; show unrounded values, each weighted contribution and raw inputs. All
four weights sum to 1. Failure percentage counts incorrect, timed-out, rejected
and otherwise unsuccessful issued logical operations in the defined window;
generator shortfalls invalidate the run rather than improving this score.

The p95 inputs are tail-latency measures: 95% of successful operations finish
within that time and the slowest 5% take longer. Report p50/p95/p99 for every
run and request class; score the overall mixed-workload p95 and retain the
per-class p95 values for interpretation and the normal-load guard. The latency
anchors are proposed fixed scales, with 1,000 ms aligned to the PRD's normal
browse/search limit. Derive the cost anchors from the reviewed normal-load cost
model, actual planned topology and current prices. Use the estimated normal-load
costs for both configurations to set a bounded range that can distinguish them,
with a stated reason for the lower and upper endpoints. Record price sources,
assumptions, formula and endpoints; have the human review and freeze them before
final comparative results are collected. Do not use A/B outcome data to choose
or adjust the range. If a material topology or price change requires new
endpoints, document and review the change before collecting replacement final
results. These scoring bounds are not a spending cap.

For each workload and repetition, compute p95 from the raw successful logical
operations across the fixed request mix; retain route-specific distributions,
failures, offered/achieved rates and sample counts. Use the median of those
per-run p95 values for the score; do not average per-route or per-server p95s.
Include burst transition in the burst window; report cold and warm behavior
separately as required. For cost, calculate pre-credit whole-system cost per
1,000 correctly completed logical operations separately for the low, normal and
burst measured workloads. Allocate each configuration's actual resource cost
over that workload's measured interval and successful operations, including
ECS capacity retained by the Lambda configuration and applicable shared
services. Report each workload's total cost and successful-operation count too.
For each run, divide interval cost by correct completions and multiply by 1,000.
Use the same price basis and allocation method for both versions. The weighted
cost score uses the median of the three per-run normal-workload values; low- and
burst-workload costs remain visible alongside it. Also report total experiment
cost separately. Do not project these measurements into a daily traffic pattern.

For each scored metric, report the three per-run values, their median, and their
minimum-to-maximum range. For each matched A/B round, also show the score
difference. Apply the stated inconclusive rule to those paired differences;
three rounds are a modest repeatability check, not statistical proof.

#### Proposed tie and uncertainty rule

- If only one alternative is finally eligible, it is the eligible choice; if
  neither is eligible, report that outcome. Unknown evidence remains unknown.
- For two eligible alternatives, a score difference of **3 points or less** is
  a practical tie. Present both and let the human choose; do not assume ECS wins.
- For a larger difference, calculate the same scores for each matched repetition
  pair. If paired score differences include both signs or zero, report the result
  as inconclusive rather than claiming a winner; otherwise report the higher
  total as the supported choice for the tested conditions. This simple spread
  check is not a statistical proof. Preserve invalid runs and explain exclusions.
- Recalculate with weights `(burst, cost, normal, reliability)` of
  `(0.30, 0.30, 0.25, 0.15)` and `(0.30, 0.40, 0.15, 0.15)` as sensitivity
  examples. Report if the preferred option
  changes; these checks do not replace the agreed primary weights. Report raw
  results and uncertainty even when the weighted score favors one alternative.

### NEXT-01 Step 4 — Proposed workload and preparation

**State:** verified by Suraj on 2026-10-28, including the revised account plan;
no cloud action or measurement is authorized. Numerical choices here are design
proposals, not PRD traffic claims.
The PRD does not specify a combined normal mix or burst shape. Its separate
NFR-01/02/03 workloads and acceptance checks remain required.

#### Why these load points

These are bounded comparison conditions grounded in the PRD's test targets and
the user's year-start turnover scenario; they are not a forecast of observed
campus traffic. The PRD specifies 10 requests/s for indexed search (NFR-02),
20 requests/s for browse (NFR-01), and 50 requests/s for the integrated peak
check (NFR-03). The comparison's 10 requests/s is a deliberately simple mixed
read workload; with the proposed 50/30/20 mix, it offers 5 browse, 3 Hybrid
search and 2 detail requests per second. It does not replace either separate
browse/search NFR test. The 50 requests/s condition reuses the PRD peak as a
stress point to expose capacity behavior. It is not a claim that the new-year
surge reaches 50 requests/s or lasts five minutes. The turnover scenario
supports testing a short increase over normal traffic, but there is no measured
traffic history here to establish its exact rate, mix or duration. Record that
limitation in the result and check any later available usage evidence before
freezing the final run profile.

#### Comparable work

Use the same HTTPS entry point shape, authenticated user mix, final data and
indexes, search/model version, requested pages, filters, response checks, client
location, timeout and monitoring for both alternatives. Only the documented
deployment/routing and necessary resource settings differ. Record those
differences; choose resource sizing in Step 7. Run one configuration at a time,
with no unrelated traffic against shared dependencies. Preserve the same
background-worker settings for both and record them.

Propose the following fixed request mix for **every** traffic level. Use a
deterministic sequence of ten requests: five browse, three Hybrid searches and
two listing details. Rotate the sequence start between runs using a fixed seed
recorded in the manifest; replay the same cases for the matched A/B pair.

| Class | Share | Request and correctness check |
|---|---:|---|
| Browse | 50% | `GET /listings`: first and later pages, with and without an approved category filter. Check the actual eligible/available IDs, filter, order, page and continuation indicator against the reviewed reference cases. |
| Hybrid search | 30% | Proposed revision pending affected-owner review: `GET /listings` with nonblank `q` and the final approved Hybrid/default relevance behavior. Include direct-word, related-word and meaning-based cases. Before measured runs compare the two paths' valid responses for the same inputs, including IDs, order, pagination and fields; resolve unexplained differences. During runs check successful status, response shape and applicable product requirements. Assess search usefulness separately through NFR-04's reviewed labels. A human-authored exact ordering for these three cases is not required under this proposal. |
| Detail | 20% | `GET /listings/{listing_id}` for available listings. Check the requested ID, current fields and image references. |

Each request is one logical operation and one HTTP attempt; set retries to zero
for measurement. Use a 5-second client timeout and count timeout, transport
error, rejection, unexpected status, malformed output or incorrect content as a
failure. Preflight regular and temporary authorized synthetic users, denial of
expired/unauthorized callers, unavailable detail and invalid filters outside the
timed workload. The dataset step supplies the exact case IDs, query text and valid
filter values. Under the proposed search revision, pre-run A/B evidence records
the comparison outcome; browse and detail retain their reviewed expected outcomes.
Never infer success from HTTP status alone. Keep image-body downloads out of
the browse timing. The existing tool still enforces the prior ordered-reference
rule until its binding and runner dependencies are updated and reviewed; this
proposal does not authorize a run or change NFR-02/04 requirements.

Use the smallest practical number of existing authorized accounts for measured
reads, initially one regular account. Establish and verify sessions outside the
measured windows; neither record credentials nor include sign-in time in read
latency. Confirm whether real session concurrency and rate limits permit the
intended load during EXP-02/04. If they do not, report the actual constraint and
review the smallest practical adjustment. Never disable protections or use the
isolated demo identity. Record the account mix and limits so results are not
presented as proof of behavior across many distinct users. Temporary-account and
denied-caller behavior remains a separately checked functional requirement.

#### Traffic and run order

Use scheduled arrivals independent of response time. Missed scheduled arrivals
or a saturated generator invalidate the affected run; retain its raw output.
Each phase has a 60-second warm-up, 300-second measured window and up to 5 seconds
to drain in-flight operations. The burst phase's warm-up is the normal 10
requests/s mix; at the measured-window boundary increase immediately to 50
requests/s and keep the first transition samples. No measured cohort starts
until the prior phase's drain has completed.

| Condition | Scheduled rate during measurement | Planned operations per run | Purpose |
|---|---:|---:|---|
| Low/intermittent | 0.2 requests/s, one every 5 seconds | 60: 30 browse, 18 search, 12 detail | A low-use comparison point and per-load cost observation. Too few per-class samples for a strong tail claim; not an estimate of typical off-season traffic. |
| Normal | 10 requests/s | 3,000: 1,500 browse, 900 search, 600 detail | A simple mixed-read comparison point, anchored to the PRD's 10 requests/s search test rate. The mix differs from the separately required NFR-02 workload. |
| Burst | 50 requests/s, immediately after normal-rate warm-up | 15,000: 7,500 browse, 4,500 search, 3,000 detail | A PRD NFR-03 peak-rate stress point for response and capacity behavior. It is not an estimate of the year-start surge rate or its duration. |

Run three matched cycles, each containing low, normal and burst for both
configurations. Alternate configuration order: **A then B, B then A, A then B**.
Within each configuration run phases in the table order. A valid phase needs the
planned arrivals, all recorded outcomes, valid response checks and generator
health; classify server-side failures as failures rather than erasing them.
Retain aborted/invalid runs and reasons; rerun both members of an invalid pair
only under the same approved limits, never stop after a favorable result. Three
valid pairs is a modest starting point, not proof that a small difference is
resolved. Apply Step 3's tie and variability rules.

With all phases valid, this schedules 108,360 measured operations across both
configurations, plus 7,272 warm-up operations and separate preflight/cold checks.
The warm-up count is 12 low-rate plus 600 normal-rate plus 600 normal-rate
burst warm-up requests per configuration per round; across three rounds and two
configurations that is 7,272. The burst warm-up runs at 10 requests/s, not the
50 requests/s measured burst rate. Thus the scheduled A/B batch is 115,632
requests before preflight and cold checks; B receives 57,816 before those checks.
The minimum timed windows are 90 minutes measured plus 18 minutes warm-up; allow
up to 90 seconds total for phase drains, plus switching, checks and cleanup.
These are not an approved duration/cost cap. Full required NFR checks, retries of
invalid pairs, deployment and cold verification add time; Step 7 sets the actual
window, maximum spend, resources and stop limits before any run.

Report cost per 1,000 correct operations separately for the low, normal and burst
conditions using the actual cost allocated to each measured interval. Use the
normal condition for the weighted cost score. Do not combine the conditions into
an assumed daily schedule. This read-focused workload does not establish behavior
under concurrent marketplace writes or claim full-application peak acceptance.

#### Timing, cold behavior and evidence

Measure from client request start through the full API response, including network
connection setup where incurred; use a verified monotonic client clock. Record
one outcome and latency per issued operation, plus intended arrivals and missed
work. Report p50/p95/p99 and verified-success throughput, with sample counts and
failures by class and phase; the Step 3 score uses only valid successful p95s
and the separate failure score. Preserve raw observations for recalculation.

Separately collect at least three **confirmed** new-runtime observations per
configuration across the cycles, with the target route and initialization/startup
evidence recorded. For Lambda, identify initialization using its actual runtime
telemetry; a long request or an idle interval alone is not proof of a cold start.
For ECS, record task start, readiness and the first attributable request to that
new serving task. Capture client request latency and startup/readiness time as
different measurements. EXP-03/04 must define and verify a bounded way to obtain
and attribute these samples under a reviewed resource plan. If confirmation is
unavailable, record the missing cold evidence and do not claim it was measured.
Three examples do not support a reliable cold p95/p99. Report warmed responses
and note separately whether database cache and connections were warm.

Retain UTC phase boundaries, routing/version proof, deployed settings, seed and
dataset fingerprint, result and error counts, generator misses, ECS task/host
capacity and scaling, Lambda duration/concurrency/initialization/throttles, DB
connections/query and saturation indicators, and cost inputs. No credentials,
private message content or real personal data belong in the evidence.

#### Expected preparation at measurement time

| Preparation | Assigned work and recheck |
|---|---|
| Product behavior and real deployed app | NEXT-03/04: confirm final Hybrid ranking, filters, auth, route and deployed revision before freezing cases. |
| Final reference dataset and human-reviewed search cases | [NEXT-01 Step 5 recipe](../../data/evaluation/reference-dataset-design.md); NEXT-06 and SE-01 create/validate it and its labels. Recheck counts, indexes, model coverage and fingerprint before each pair. |
| Workload/measurement tool | EXP-02 owns adapting the existing local k6 preparation to real auth, these three request classes, scheduled arrivals, correctness checks, raw outputs and capped runs. The existing runner currently refuses final/cloud profiles; verify the final implemented tool and generator headroom before use. |
| Lambda path and routing | EXP-03 owns packaging, real Hybrid capability and parity; EXP-04 verifies the deployed A/B routes, auth, telemetry and cold-observation method. No Lambda equivalent has yet been proven. |
| Actual resources, cost, operator and cleanup | NEXT-01 Step 7 and EXP-04/08 define/review the exact plan and limits; verify current AWS state and headroom just before use. |
| Run gate and final acceptance | NEXT-01 Step 8's approved real read-specific gate applies; FR-13 and other final requirements retain their real acceptance checks. |

NEXT-03/04 may change query fields or deployment details. Update the fixed cases
before final freeze with documented review; do not revise the decision rules
after seeing results to favor an alternative. No uncovered new task is asserted
until the assigned outputs and their acceptance checks have been reconciled.

### NEXT-01 Step 7 — Proposed costs, limits and evidence

**State:** verified by Suraj on 2026-10-28; not an approved deployment or
executable budget. Suraj considers the planned expense acceptable and wants the
app turned off after experimentation until it is needed for the demo or another
approved check. Current actual project spending still needs confirmation. The project region recorded in the inventory
is `ap-south-1` (Mumbai). A read-only identity check in this session returned
account `484394572488`, not the recorded project account `335523638354`;
no project AWS resources or current billing were inspected. The actual project
operator must confirm the authorized identity, account, live resources, spend
and headroom before any plan or run. Do not use the wrong account.

#### What to record

Keep a versioned run manifest and raw per-operation observations: source/image/
function revisions, deployed route proof, data/model/index fingerprints, request
cases and seeds, actual account/region, UTC phase boundaries, warm/cold evidence,
client start-to-response times, status/content outcomes, generator arrivals and
misses. Record p50/p95/p99, counts and verified-success throughput by route and
phase, with failures/timeouts/throttles separately. Report individual runs and
spread, not averages of percentiles. Record ECS desired/running/healthy tasks and
hosts, Lambda concurrency/duration/errors/initialization, PostgreSQL connections,
query latency and saturation, and any applicable network/ingress signals. Use
aligned UTC windows and retain query names or definitions, not secrets or message
content. Missing telemetry is missing evidence, not zero.

#### Current public prices and example cost

AWS public Mumbai price lists checked on 2026-10-28 show the following on-demand,
pre-credit reference prices. They are not a bill and do not prove the final
architecture or account uses these resources. Rates and service usage must be
rechecked against the actual reviewed plan before use.

| Item | Mumbai reference price | Source |
|---|---:|---|
| Linux `c7i-flex.large` | USD 0.08479 per instance-hour | [AWS EC2 price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/ap-south-1/index.csv), published 2026-10-27 |
| NAT gateway | USD 0.056 per gateway-hour, plus data processing/transfer | Same EC2 price list; [VPC pricing](https://aws.amazon.com/vpc/pricing/) describes partial-hour and data charges |
| PostgreSQL `db.t4g.micro`, single AZ | USD 0.021 per instance-hour | [AWS RDS price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/ap-south-1/index.json), published 2026-10-26 |
| gp3 storage | EC2: USD 0.0912 per GB-month; RDS PostgreSQL single AZ: USD 0.131 per GB-month | AWS EC2 and RDS price lists above |
| Public IPv4 | USD 0.005 per address-hour | [AWS VPC pricing](https://aws.amazon.com/vpc/pricing/) |
| Standard Lambda, x86 | USD 0.0000166667 per GB-second and USD 0.20 per million requests in the first usage tier | [AWS Lambda price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSLambda/current/ap-south-1/index.json), published 2026-10-22; [Lambda pricing](https://aws.amazon.com/lambda/pricing/) |

Illustrative **four-hour whole comparison window**, not a selected deployment:
two continuously running `c7i-flex.large` hosts cost USD 0.67832; one NAT gateway
costs up to USD 0.28 for five billable hours; one running `db.t4g.micro` costs
USD 0.084; 60 GB EC2 gp3 plus 20 GB RDS gp3 cost approximately USD 0.04496
for four hours using a 720-hour month; two public IPv4 addresses cost USD 0.04.
The listed subtotal is about **USD 1.13**. It excludes NAT data processing,
ingress, Lambda, logs, storage requests, image storage, data transfer, billing
minimums beyond the stated assumptions and other retained resources. The final
plan must price every applicable component, including shared baseline costs and
any generator resource, not present this subtotal as the total.

The verified Step 4 schedule sends 57,816 measured/warm-up requests to B before
preflight or cold checks. If all invoke 1 GiB Lambda functions and average
0.3 billed seconds, the reference request-plus-compute estimate is USD 0.30;
at 2 GiB and 1 billed second it is USD 1.94. These are illustrations, not
measured durations or predictions. Initialization, retries, gateway/network,
storage and other whole-system charges can increase the total. Lambda remains
an additional cost unless ECS or other actual paid capacity decreases.

**Scoring-scale review:** the daily-cost score and assumed 24-hour traffic mix
were removed. Step 3 now scores normal-load whole-system cost per 1,000 correct
operations; report the corresponding low- and burst-load costs separately. Set
the numerical cost anchors from the reviewed planned topology and current prices
before final comparative results. This scale is not a spending cap.

#### Proposed limits for the comparative batch

All values below are proposed ceilings for the **comparison only**, including
warm-up, preflight, switching, one invalid-pair rerun and optional cold/reset
checks. They do not cover separately approved NFR-03 writes, recovery/restore,
later deployment or retained costs after the window.

| Limit | Proposal and pre-run check |
|---|---|
| Elapsed window | 4 hours from approved start through stop; 108 minutes is the minimum planned load plus warm-up. Stop new work early enough to finish and check cleanup inside the window. |
| Incremental cost | Maximum USD 20 for attributable whole-system usage in the window, including the share of existing resources. Keep the accepted USD 25 project reserve and USD 50 pause/review point; confirm actual spend, delayed charges and headroom first. |
| Requests | At most 160,000 total across A and B, including warm-up, preflight and cold checks; at most 80,000 Lambda invocations. Step 4 schedules 115,632 read requests total before preflight/cold checks (57,816 routed through B); the remaining allowance is 44,368 total requests and 22,184 Lambda invocations, subject to the separate caps. |
| ECS | At most two `c7i-flex.large`-equivalent hosts and two app tasks; exact CPU/memory, minimum healthy capacity and scale policy are part of the later reviewed plan. Both configurations must retain the required ECS service. |
| Lambda | At most 2 GiB memory, reserved concurrency 20, no provisioned concurrency and function timeout at most 5 seconds. The actual package and safe database usage must fit; otherwise revise before final runs. |
| Client and database | Proposed, non-binding ceiling: at most 300 concurrent client requests and 50 scheduled requests/s. Cap project database connections at 60, reserve separate administrative headroom, and confirm the real database limit and pool sizes before use. Stop if the limit or downstream capacity cannot be established. |

**Human direction (2026-11-01):** The 300 concurrent-client-request figure is
not binding and must not be enforced as a code guard. The actual generator and
client concurrency limits remain open inputs for the reviewed pre-run plan.

As a conservative **illustration**, if all 20 Lambda slots were continuously
billed at 2 GiB for all four hours, compute would be about USD 9.60; 80,000
requests add USD 0.016. This is a deliberately high utilization example, not a
guaranteed billing cap: initialization, extensions, rounding, provider billing
and other services must be checked in the exact plan. Add the whole-system
components and a verified allowance for every omitted cost before deciding that
the USD 20 limit is feasible. Budget alerts can lag and do not enforce the cap.

At 50 requests/s, 20 concurrent Lambda executions cover an average duration of
about 0.4 seconds before the concurrency ceiling itself can constrain throughput.
If a pilot shows this limit, database connections, task capacity or generator
capacity would distort the intended comparison, report it and review revised
limits for both alternatives **before final measurements**, with a new cost plan.
Do not hide throttling or tune only the favored configuration.

#### Operator, stop and cleanup

The project inventory records Aditya as the shared cloud operator; confirm the
actual operator and approved non-root identity for the later window. Before use,
identify current project account/region, version, existing resources and other
contributors' active work. Obtain explicit approval for the exact deploy/routing,
load, optional fault and cleanup plans, including their cost/resource effects.
Stop starting work on a cap breach, unexpected account/target, unsafe exposure,
unexpected data or generator shortfall, uncontrolled saturation, or failure of
required correctness/telemetry checks. Record partial results; never relabel a
failed run as a pass or automatically retry outside remaining approved limits.

After the window, stop the owned generator, restore the approved routing, and
remove only resources created for this experiment using the reviewed cleanup
plan. Shut down the running app/experiment compute after the required work and
keep it off until the demo or another separately approved necessary check; retain
the data, evidence and reproducible start path needed to resume. Recheck ECS tasks/hosts, Lambda versions and concurrency, database/restore
targets, public ingress/IPs, NAT, disks, S3 objects, logs and scheduled workers.
Record retained resources, owner, review date and continuing costs; preserve
shared data, other contributors' resources and experiment evidence. Actual
billing may arrive later: retain estimated unbilled amounts and reconcile the
whole project in CLOSE-00. No budget, deployment or cleanup action is authorized
by this design alone.

### NEXT-01 Step 8 — Proposed changes to measurement gates

**State:** verified by Suraj on 2026-10-28; the approved canonical gate changes
are applied in NEXT-01 Step 9. No measured run, deployment or cloud action is
authorized by this design.

**Evidence before the approved change:** the task index and graph required verified/merged INT-01
before EXP-06; full INT-01 requires all eight domain tasks, including CN-03.
CN-01 Step 11 also required CN-03's final producer/send path before NFR-05.
The current checked-out implementation writes new-conversation notification
intents in the creation transaction and unread-message intents in the message
transaction. That code is evidence of existing behavior, not proof of a deployed
path, complete notification delivery or final CN-03 acceptance. GitHub main was
still `5e8d264` on 2026-10-28; no open PR was returned by the read-only check.

#### Approved independent read-comparison gate

EXP-06 requires all of the following real checks instead of a blanket INT-01
prerequisite. Record the reviewed evidence and exact versions before
running; a test double or a merely planned output is not sufficient:

1. NEXT-03's selected search/filter behavior is agreed, and the actual deployed
   browse, Hybrid search and detail paths use real Identity, authorization,
   data, indexes and model. Verify correct results, denied callers and the
   representative cases in the approved comparison manifest.
2. DATA-READY is accepted for the final corpus, image references, current
   indexes/model coverage and human-reviewed labels; record the fingerprint.
   NEXT-04's relevant integrated app, real sign-in and selected read-path checks
   must be verified. Other unrelated domain completion remains tracked separately.
3. EXP-01's design and decision rules are approved; EXP-02's real-target workload
   and correctness checks pass; EXP-03's mixed implementation is reviewed and
   merged; EXP-04 verifies actual A/B routing, authorization and parity; EXP-05
   pilot and generator/telemetry/resource checks pass. Record exact revisions,
   versions and paired-run limits.
4. Confirm actual project account/region/operator, remaining budget and reserve;
   review and approve the exact deployment, run and cleanup plans. Keep worker
   settings identical across A/B and record them. If Notifications delivery or
   another background path is absent, report that limitation; do not describe
   the run as a fully integrated whole-app workload.

An independent read comparison may then produce **scoped comparison evidence**;
it does not accept FR-13, INT-01, unrelated NFRs or the final project. If later
Notifications integration or another change materially affects the selected
paths, routing, model, data, resources, background load or measurement method,
review the impact and rerun affected paired comparisons and NFR checks. Full
INT-01 and CLOSE-00 retain their existing required domain/Notifications and
whole-project acceptance gates.

#### Approved independent chat measurement

Allow CN-01 Steps 11–12 to measure real active-chat sender-to-display timing
before email delivery is ready **only** when the deployed real auth, participant
keys, encryption, message transaction/notification-intent recording, read state,
polling, two clients, measurement tool and approved workload are verified.
Record the actual producer revision and worker state; no synthetic identity,
fake message provider or missing outcome may be treated as a pass. Such evidence
is scoped to that configuration. CN-01's full acceptance and FR-13 still require
the real CN-03 integration and delivery checks. If the later producer, locks,
read-state, shared database/resource load or runtime changes materially affect
chat timing, repeat the affected NFR-05 measurement on the final configuration.

#### Canonical changes applied after verification

- **Document 2:** replaced its INT-01 prerequisite for EXP-06 and broad requirement
  that all related domain tasks be complete with the four read-specific checks
  above; leave EXP-01–05, real deployment/parity, cost and action gates intact.
- **Project task index:** changed the EXP-06 dependency row and the corresponding
  prose to EXP-05 plus the approved read-specific checks and DATA-READY. Retain
  all existing INT-01 dependencies. Add the narrow CN-01 measurement allowance
  while keeping final CN-01/CN-03 completion dependencies.
- **Dependency graph:** replaced `INT-01 → EXP-06` with `DATA-READY → EXP-06`;
  retain `EXP-05 → EXP-06` and `INT-01 → CLOSE-00`. The real path, parity,
  pilot and approved action prerequisites remain detailed in the index/Document 2.
- **Domain task list:** added the scoped CN-01 Steps 11–12 allowance above without
  claiming CN-01 or CN-03 complete. Preserve full INT-01's existing requirements
  and NFR-03/06/07 procedures. Update its final handoff sentence so it does not
  imply all experiment steps necessarily wait for INT-01.
- **Stub and integration guide:** updated the CN-01 Steps 11–12 row and replaced
  the blanket INT-01 measured-run phrase for EXP with these real-path gates;
  keep its prohibition on mocked identity, data, routing, parity and results.
- **Foundation traceability and NFR measurement design:** clarified that an
  accurately scoped chat measurement may occur early, while the final producer,
  delivery and full-acceptance obligations remain. Retain the original FR/NFR
  ownership and traceability.
- **Reusable task prompt and remaining-work plan:** updated the phase-order and
  current-gate descriptions to reflect an approved independent comparison,
  without changing the full INT-01/CLOSE-00 completion gates.

The graph expresses only acceptance dependencies; the operator must still check
every concrete prerequisite and separate action approval. Full INT-01, FR-13 and
CLOSE-00 acceptance remain required.

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

**Owner:** Rahul (D), reassigned by user direction. **Reviewers:** A as default independent peer; C and B as affected Search/infrastructure owners where required. **Start after:** EXP-02.

1. Inspect the approved EXP-01 manifest, actual integrated read operations, auth context, database access, generated API contract and accepted revision. Identify shared application logic that can be reused without importing another domain's private implementation.
2. Propose the minimal Lambda packaging/adapter, ingress/routing, authorized request-context handling, PostgreSQL connection limits, concurrency/timeouts, logging and failure behavior. Preserve state-changing routes on ECS; present any unresolved compatibility/security/cost decision and wait for approval before dependent implementation. For B, the ALB continues to target ECS; the ECS router invokes Lambda for selected reads and uses ECS on a confirmed Lambda throttle.
3. Implement the Lambda entry/adapter and packaging using the frozen public operations and shared authorized logic. Preserve status/error/response semantics, filters, ordering, pagination, availability and privacy. Add unit/contract/parity tests for success, invalid/auth/forbidden/not-found, database failure and timeouts; no cloud measurement yet.
4. Implement the configuration-A/B selection/routing path and build scripts with explicit targets and reversible configuration. Prove local routing tests keep writes/chat/offers on ECS, select only the approved GET reads for Lambda, and send Lambda capacity rejections to the same ECS read handler.
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
3. Report every measurement specified by the frozen manifest, whether or not it contributes to the score. This includes p50/p95/p99, per-request-class and per-phase results, offered/achieved/successful throughput, failures/timeouts/throttles, dropped arrivals, cold/warm observations, ECS capacity and scaling, Lambda concurrency/duration/initialization, database signals, and cost per 1,000 correct operations at every load. Mark unavailable measurements with the reason; do not omit an inconvenient or unscored result.
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

EXP-01–EXP-08 run in dependency order. Task owners/reviewers are listed in the project task index; every step reports expected and observed results, evidence, and verification state, and updates the work-log status row. Dated history entries capture meaningful outcomes and evidence; related steps may share an entry, and routine proceed acknowledgements do not need separate entries. Shared environment configuration changes/runs are serialized by the named operator; no parallel deployment may contaminate a measured pair. Preserve invalid runs and do not call an incomplete check a pass. Changed configurations require updated approvals and both sides of affected paired measurements rerun.

EXP-08 records experiment cost/cleanup and routes to CLOSE-00 in `docs/tasks/final-closeout-task-list.md`. CLOSE-00 performs full-project cost reconciliation including this experiment and final regression/submission evidence. Optional work follows its separate technical/priority gates, never silently alters a frozen experiment revision.

## Real dependency restriction

Early local domain work may use reviewed test doubles under the canonical stub guide. This comparison still requires actual integrated/authenticated ECS/Lambda paths, real routing/parity/deployed revisions and approved resources/workloads. No stub-only service, dataset preview or simulated timing establishes comparison/NFR evidence. Recheck the pending-integration ledger before run acceptance.
