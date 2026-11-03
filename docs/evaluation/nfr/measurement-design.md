# Proposed implementation design for NFR-01–08

**State:** NEXT-01 Step 6 verified by Suraj on 2026-10-28. The frozen final
dataset exists and DATA-READY is accepted in the work log; its recorded logical
fingerprint is
`7efd142e11c3e8555e1aa08603cbf8dff07de5d74412ccde3c39869b9334ab98`. These
are implementation instructions and proposed run settings, not live results or
cloud authorization. The [domain task list](../../tasks/domain-task-list.md)
owns each check and [CLOSE-00](../../tasks/final-closeout-task-list.md) owns
final budget reconciliation. The pre-deployment tooling batch has passed its
local evaluation-suite, compile, formatting, whitespace and focused type checks.
Affected-owner/independent review and normal PR merge remain before deployment.
Recheck the
frozen fingerprint, schema, indexes, model, reviewed labels and application
revisions against each target before running. Do not call local evidence a cloud
result.

## Common preparation and evidence

1. Use the accepted final dataset release and its recorded fingerprint; do not
   regenerate it for the experiment. Before a run, verify that the deployed
   database, image references, indexes, model and reviewed labels match the
   frozen release, and that the accepted measurement window covers the run.
   NFR-06/07 use their own approved fixtures/targets.
2. For each deployed measurement record the actual account/region/environment,
   authenticated operator, app/image and schema revisions, configuration,
   routing, synthetic data/label fingerprints, real authorized test sessions,
   resource settings, generator version/location and UTC start/end. Use one
   existing regular synthetic Microsoft test account from the approved Entra
   test tenant; sign in outside measured traffic and use the reviewed secure
   session handoff. NFR-05 needs two authorized participants. Never store tokens,
   private contact data, keys or message bodies in evidence.
3. The owning task writes a manifest before each run under the existing
   `docs/evaluation/nfr/` convention. Include exact target and version, input
   profiles/fixtures, valid/invalid criteria, timing/timeout, workload,
   measurements, duration/resource/concurrency/spend caps, stop conditions,
   cleanup/retention and owner. Review the concrete cloud action separately;
   nothing in this design approves a deployment, load test, forced loss or restore.
   Step 7 supplies cost and cap proposals; a blank cap blocks the run.
4. For API load, extend the existing SE-01/EXP-02 k6 preparation in its owning
   task to run against the approved real target with the actual contract, session
   and checked synthetic cases. Use scheduled arrivals, a monotonic client clock,
   a 5-second request timeout and no retries for measured requests. Record each
   planned arrival, issued request, status, correctness, latency and timeout;
   record missing arrivals and generator saturation. Use a 60-second warm-up,
   300-second measured window and up to 5 seconds' drain per phase. Confirm
   the actual tool and rate-limit behavior in a bounded pilot. Do not bypass
   protections; use existing authorized accounts and report the account mix.
5. A run with missed arrivals, invalid timing, unverified target/version or
   missing required evidence is invalid, not a pass. Unexpected status, wrong
   response, timeout and throttle are failures. Record failures separately from
   latency among successes. Preserve raw/invalid results and calculate from raw
   observations; never average percentiles across routes or servers. Record p50,
   p95, p99 and counts when sample size allows, plus offered/achieved/successful
   rates and runtime/database signals. Use the same correctness and timing rules
   in comparable runs. Stop on an approved cap or unsafe/uncontrolled behavior;
   do not repeat an invalid run without remaining approved headroom.
6. Retain a sanitized manifest, raw observations, aggregate calculations,
   telemetry queries/windows and outcome under the owning NFR's evidence home.
   Record completed and failed checks honestly. Use existing valid evidence when
   its source revision, data, configuration and measured behavior still apply;
   recheck any part affected by later changes. A human reviews labels, results and
   applicable action gates; scripts do not supply human approval.

The 60-second warm-up, timeout and one measured repetition per applicable
architecture below are proposals, not PRD defaults. Each performance window is
at least five minutes after warm-up. Record warm and cold evidence separately
where relevant; the [architecture comparison](../ecs-only-vs-ecs-lambda-task-list.md)
has its own three paired repetitions and cold-observation procedure.

### Which architecture needs each check

Apply this matrix when both actual configurations are known. Record the version,
route, resources and evidence behind every reuse decision; an unchanged result
must not be assumed merely because the source code is shared.

| NFR | Required coverage and permitted reuse |
|---|---|
| 01 — Browse | Run the 20 requests/s check separately against A and B. Preserve the successful-request denominator and report each configuration's results. |
| 02 — Search | Run the 10 requests/s check separately against A and B. Preserve the all-eligible-issued-request denominator and report each configuration's results. |
| 03 — Peak API | Run the integrated mixed workload separately against A and B at 50 requests/s. Preserve the NFR-03 success rules; the comparison's read-only burst is not this check. |
| 04 — Search usefulness | Use the same reviewed labels. Retrieve and compare the first five results for every included query on both paths if search routing changes. A previously calculated score may be reused only after identical ordered results, data, model, configuration and applicable behavior are verified; otherwise calculate and report each result separately. |
| 05 — Chat latency | Measure on both if chat routing, shared capacity, background activity, polling or dependencies differ in a way that could affect sender-to-display time. Reuse only with evidence that the actual chat path and relevant normal workload/resources are unchanged. |
| 06 — Runtime recovery | Check both if serving paths, orchestration or relevant capacity differ. Reuse only when the tested recovery path and configuration are unchanged. Both proposed architectures retain ECS: stop one approved ECS task, measure restoration of configured ECS serving capacity and record request outcomes for the applicable routes, including Lambda-routed reads in the mixed configuration. |
| 07 — Database restore | One valid restore can cover both if they use the same unchanged database, backup policy and restore procedure. Repeat when those change or prior evidence is invalid. |
| 08 — Budget | Account for both configurations' incurred costs and all other project spending in one final project total. Do not count shared costs twice or assume the comparison's estimate is final billing. |

### Tool work assigned to existing tasks

These are implementation contracts. The status notes below identify current
local tooling and its remaining integration limits; a command is not a live-run
approval or acceptance result.

| Owner and planned home | Required inputs, outputs and verification |
|---|---|
| SE-01/EXP-02: `scripts/evaluation/k6/` | Offline profiles, monotonic timing, A/B real-run coordinator, receipt-bound reports and separate NFR-01/02 and EXP-05 workloads are implemented. Consolidated local audit, reviewed inputs and later deployed target/session checks remain. NFR-01 and NFR-02 keep their distinct denominators. |
| INT-01: peak profile/runner under `scripts/evaluation/` and `data/evaluation/workloads/` | The separate NFR-03 mixed workload, controlled writes, unique operation IDs, timeout reconciliation and A/B reports are implemented. Consolidated local audit, final route/case bindings and live integration remain. |
| SE-01: `scripts/evaluation/nfr04_retrieval.py` | The approved-manifest retrieval runner uses reviewed labels, binds target/session and produces Success@5 evidence. Consolidated local audit, current label/retrieval contract review and live A/B results remain. |
| CN-01: `scripts/evaluation/nfr05_browser.mjs` and `scripts/evaluation/nfr05_report.py` | The two-client harness measures actual message submission to display, supports bounded background load, counts undisplayed messages and avoids message-content logging. Consolidated local audit, two securely supplied sessions and the live participant run remain. |
| INT-01: `scripts/evaluation/nfr06_recovery.py` | The recovery observer is implemented with a separately gated exact task-stop action. Live stop action requires its own approval. |
| INT-01: `scripts/evaluation/nfr07_restore_observer.py` | Restore observation and integrity checks are implemented with a separately bound isolated target. A live restore needs its own approved target and cleanup plan. |
| INT-01/CLOSE-00: `scripts/evaluation/nfr_cost_ledger.py` | The project ledger records actuals, estimates, delayed charges, retained resources and credits. Current price/billing evidence, the $10 AWS-credit cap, remaining project budget and final reconciliation need live review. |

## NFR-01 — Browse latency (SE-01)

**Scheduled preparation:** NEXT-03/04 finish the real browse path and deployment;
NEXT-06/SE-01 supply the frozen corpus and reviewed browse cases; SE-01 Step 10
supplies the real-target runner. Existing `nfr-01/manifest.template.json` and
`data/evaluation/workloads/browse-nfr-draft-v1.json` are drafts, not runnable proof.

1. Preflight actual regular-user access, current pages/filters/order and reference
   IDs through `GET /listings`; ensure image bodies are not downloaded. Cycle a
   fixed set of approved first-page, later-page and category-filter cases from
   the final dataset. Each started iteration sends one HTTP request.
2. Run one approved phase on A and one on B at 20 requests/s: 1,200 warm-up and
   6,000 measured scheduled requests per configuration. Check
   each status, listing availability, filter, page, IDs/order and response shape
   against the reviewed cases. Use the common timeout, drain and evidence rules.
3. Let `S` be correctly completed browse requests and `F` be those in `S`
   completed within 1,000 ms, including the boundary. Pass only if `S > 0` and
   `F / S >= 0.95`; separately report all failures/timeouts and actual load.
   This is the PRD's successful-request denominator; do not silently substitute
   the search or peak denominator. Apply the comparison's separate success floor
   when using this evidence for the architecture decision.

## NFR-02 — Indexed search latency (SE-01)

**Scheduled preparation:** same real deployment/data/runner as NFR-01, with
reviewed search queries, actual indexed search, final Hybrid model and coverage.
`nfr-02/manifest.template.json` and the existing Hybrid profile are drafts.

1. Preflight the real public search route with frozen representative direct-word,
   related-word and meaning-based cases; check final NEXT-03 filters and ordering.
   Use the intended Hybrid product behavior, not an invented keyword-only path.
2. Run one approved phase on A and one on B at 10 requests/s: 600 warm-up and
   3,000 measured scheduled requests per configuration. Record successful HTTP
   response completion and latency, plus query/database timing and
   connection/saturation signals. Do not score relevance in this latency NFR;
   NFR-04 is the separate Success@5 evaluation. Image bodies are outside the
   API-response timing.
3. Let `E` be all issued, eligible indexed-search requests and `F` those that
   completed successfully within 1,000 ms. Pass only if `E > 0` and
   `F / E >= 0.95`. Unsuccessful HTTP responses and timeouts count in `E` as
   violations. Separately record dropped arrivals, which invalidate the run.
   Use SE-01's explicit denominator and preserve raw samples. Relevance and
   ranking quality are evaluated separately under NFR-04.

## NFR-03 — Integrated peak API behavior (INT-01)

**Scheduled preparation:** NEXT-04 and the applicable INT-01 gate supply real
integrated routes and approved deployment; INT-01 Step 6 owns the workload and
runner. SE-01/EXP-02's read runner is a reusable starting point, not proof that
it supports integrated writes. Prepare one controlled account with at least one
actual conversation and five saved listings; use the finalized category code.
The exact target and creation/retention of synthetic wanted requests require an
approved run plan. Run this test outside frozen A/B comparison windows.

1. Implement a deterministic cycle of 100 operations: 30 browse, 25 Hybrid
   search, 15 listing detail, 10 public wanted-request reads, 10 own conversation
   list reads, 9 saved-list reads and 1 wanted-request creation. Resolve route,
   body, response and CSRF behavior from the current generated contract. For each
   write use a unique deterministic operation ID and synthetic title/description;
   verify the created ID and returned fields. A request that times out may still
   have created a row; track its operation ID for reconciliation, not blind retry.
2. Run one phase on A and one on B at 50 requests/s: 3,000 warm-up and 15,000
   measured scheduled operations per configuration, including 30 and 150
   wanted-request create attempts respectively. All ordinary expected 429s are
   failures; exclude only a separately identified intentionally abusive request,
   of which this workload schedules none. Record per-route results and generator
   misses. Validate correct response content, not status alone.
3. Pass only if at least 95% of all 15,000 issued eligible measured operations
   return the expected result within the timeout. Count errors, rejected requests,
   timeouts and wrong results as failures; a missed arrival invalidates the run.
   The architecture comparison's 50 requests/s is read-focused and does not by
   itself satisfy this integrated mix. Reconcile all created rows, retain their
   synthetic IDs/operation IDs and follow the separately approved cleanup or
   retention plan; do not reset a shared database.

## NFR-04 — Search usefulness (SE-01)

**Scheduled preparation:** NEXT-06/SE-01 Step 9 supplies the fixed corpus and
at least 20 human-reviewed query judgments in `data/evaluation/query-labels.json`.
The existing evaluator validates templates and synthetic arithmetic; SE-01 must
complete real dataset binding and retrieval. Human review is independent of the
measured search results, with reviewer, time, inclusion rules and fingerprints.

1. Validate the reviewed labels, inclusion policy, listing IDs, eligible contexts,
   dataset/model/contract revisions and real search provider. Use the same labels
   for both architectures. For each included query obtain the first five real
   results through the relevant integrated search path with final Hybrid ordering.
2. A query succeeds when at least one human-labeled relevant ID is among those
   five. Let `Q` be all included reviewed queries, including empty relevant sets;
   let `H` be hits. Pass only if `Q >= 20` and `H / Q >= 0.80`. A failed or timed
   out retrieval is reported and does not disappear from the denominator. Do not
   change labels or exclude failed cases to force a pass.
3. Save query IDs, result IDs, hit/failure status, label/code/data/model hashes
   and aggregate calculation without private search content. Run once per path
   needing independent evidence; reuse valid equivalent-result evidence only when
   its exact deployed configuration is covered.

## NFR-05 — Active-chat latency (CN-01)

**Scheduled preparation:** CN-01 supplies a two-client harness and workload;
NEXT-04 supplies real auth, browser/API, participant keys, encrypted messaging
and polling. Two existing authorized participants use controlled synthetic test
content and one actual conversation. The approved NEXT-01 Step 8 gate permits
scoped measurement before CN-03 email delivery only after the real message/intent
transaction and all other named deployed-path checks pass. Final CN-01/FR-13
acceptance and affected timing rechecks still require real CN-03 integration.

1. Implement the harness using two separate browser sessions on the same test
   machine and one host monotonic clock. It starts timing at the sender's actual
   UI submission, and records the recipient's actual message display after real
   encryption, API transport, polling and decryption. Correlate using controlled
   non-secret identifiers and actual UI/client events; do not log message bodies,
   keys or ciphertext. Validate locally that undisplayed/failed messages remain
   in the denominator, and that a server response alone never counts as display.
2. Warm the integrated path for 60 seconds with both conversation views open.
   During the 300-second measured window submit exactly 60 test messages, one
   every 5 seconds, while the approved 10-read-requests/s normal background
   workload is running. Set each message's visibility deadline to five seconds;
   record its eventual outcome even if not displayed. Verify real rate limits,
   sessions and safe notification handling before the run; do not send bulk email.
3. Let `M = 60` expected submissions and `V` those visible to the recipient at
   or before five seconds. Pass only if all 60 outcomes are accounted for and
   `V / M >= 0.95` (at least 57); failures and undisplayed messages count against
   the target. Record actual polling interval, timestamps, account classes,
   sample counts and background-load success. Missing observations invalidate
   the run; do not calculate p95 only from displayed messages and claim a pass.

**Tooling checkpoint:** `scripts/evaluation/nfr05_browser.mjs` observes the
sender form-submit event and recipient rendered-message event through two local
browser debugging sessions, hashes synthetic message text only in memory, and
records sanitized host-monotonic event times. It requires a separate expiring
approval bound to the exact manifest; the manifest binds a hashed A/B target
plan, two distinct reviewed user IDs, revisions, caps and cleanup. Before any
browser message or background request, it calls the shared read-only AWS/HTTPS
preflight and verifies both regular test-account sessions against those IDs.
It starts the hash-bound comparison profile as a concurrent 10-read/s
browse/search/detail mix for the 300-second message window, retains its raw k6
stream separately, and marks the background load valid only when 3,000 requests
are issued and correctly accounted with no drops or failed responses.
`scripts/evaluation/nfr05_report.py` checks this receipt and keeps the full
60-message denominator. The browser tool creates no AWS resources, stops no
tasks and does not accept the NFR result.

## NFR-06 — Runtime recovery (INT-01)

**Tooling checkpoint:** `scripts/evaluation/nfr06_recovery.py` binds a hashed
shared A/B target plan to the exact account/service/task/target group, performs
the shared AWS/HTTPS routing preflight, and verifies the regular test-user
session before any baseline traffic. It then performs the bounded 1-read/s
baseline and recovery stream and requires an unexpired `ecs.stop_task` approval
bound to the exact plan bytes and named task. It never creates resources. It
records request failures and drops separately from the 240-second capacity
result; no automatic fallback is assumed.

**Scheduled preparation:** INT-01 Step 7 owns an observer and an exact reviewed
failure/recovery plan. At least two ECS tasks must be healthy, registered and
serving the deployed path before starting. The shared Terraform root now has
explicit `api_service_desired_count=2` and `ecs_host_max_size=2` inputs for this
separately approved plan; normal defaults remain one task/one host maximum. A
two-task request with a one-host maximum is rejected. Prepare an approved way to
identify one specific task and invoke ECS task stop; verify which paths each
task serves.

1. Run a 1-request/s controlled read stream for 60 seconds to establish normal
   service. Alternate an approved listing-read case with an authenticated
   ECS-served read such as `GET /me`; in the mixed configuration verify the
   listing case is routed through Lambda. Start a monotonic timer immediately before the approved stop
   request for the named task. Continue the stream for a 300-second measured
   window while observing ECS events, running/healthy task counts and actual route
   health. Record the capacity-restoration deadline at 240 seconds.
2. Stop the timer when configured serving capacity is restored and each required
   task is healthy/registered and serving. Pass only if that interval is at most
   240 seconds. Retain all request outcomes, start/stop events and observations;
   if capacity is not restored by the deadline, record failure and stop the load.
   Do not stop additional tasks or repair infrastructure without the relevant plan.
3. Repeat for each deployment configuration where prior evidence cannot be reused.
   In the mixed configuration, include requests to the selected Lambda-routed
   reads as well as an ECS-served route while the ECS task recovers. Report the
   actual ECS recovery and observed request outcomes. The PRD and INT-01 specify
   this serving-instance recovery check; they do not require a separate forced
   Lambda-environment loss. Lambda cold starts, failures and scaling are observed
   during the comparison under its own approved method.

### Optional short Lambda reset observation

Suraj requested this additional check if it can be done without substantial
extra effort. During EXP-03/04, first check whether the actual Lambda packaging,
test infrastructure and telemetry make a bounded runtime-crash or timeout probe
straightforward. AWS states that an invocation crash or timeout resets the
execution environment; if that environment is reused, the runtime initializes
again on the next invocation. See [Lambda lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html).

If feasible, prepare a separately reviewed test-only function version or isolated
harness using the same relevant read code and dependencies. Restrict the induced
failure to the test invocation: do not add a publicly accessible crash switch
or change the production route. Under an exact approved plan, establish a working
baseline, trigger one controlled runtime crash or timeout, then send a normal
authorized read and record outcomes, timestamps, function version and Lambda
initialization/reset evidence. Use logs/telemetry to establish what occurred;
do not assume the follow-up request reached the same environment. A successful
request routed to a different environment demonstrates service continuity, not
that the failed environment itself recovered. If reset or attribution is not
observed, report the result as inconclusive.

Aim to keep the actual probe to a few minutes; assess preparation, resource and
cost overhead once the Lambda implementation exists. If it needs significant
new infrastructure or instrumentation, report that and omit it unless separately
selected. AWS Fault Injection Service's Lambda invocation-error action requires
an extension and S3 configuration and marks an invocation failed; it does not by
itself prove the runtime was terminated. See [AWS FIS Lambda actions](https://docs.aws.amazon.com/fis/latest/userguide/use-lambda-actions.html)
and [action definitions](https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html).
This optional observation is separate from the required NFR-06 ECS task-loss test,
does not establish a 240-second Lambda recovery claim, and must not interfere with
final comparison runs or their fixed scoring.

## NFR-07 — Managed database restore (INT-01)

**Tooling checkpoint:** `scripts/evaluation/nfr07_restore_observer.py` verifies
the named latest available automated snapshot, refuses an existing target,
requires a separate approval bound to the exact restore-plan hash, checks the
approved regular test-user session before requesting the restore, restores
privately, verifies the migration head/FKs/representative relationships, and records the monotonic
restore timeline. It also verifies a named ECS smoke service's image digest and
`CLIP_DATABASE_URL` SSM parameter binding, confirms the parameter resolves to
the restored instance, checks healthy service targets, then makes an
authenticated `/api/me` read and a wanted-request detail read through HTTPS.
The smoke service and its database parameter must already exist under a
separately reviewed plan; this observer creates neither. Cleanup remains a
separate approved action, and NFR-07 acceptance still requires human review.

**Scheduled preparation:** INT-01 Step 8 owns the restore/observer and exact
plan. Identify the latest available managed backup, its timestamp and synthetic
data scope, source revision/schema, isolated target name/network/permissions,
expected cost and retention. The source database must remain unchanged. Ensure
the approved snapshot contains representative synthetic rows needed for checks.

1. Immediately before the approved restore request, start a monotonic timer. Restore
   that backup to the approved isolated test database, wait for it to accept
   authorized connections, then run read-only checks: connection/`SELECT 1`,
   expected migration head, key foreign-key/integrity checks and representative
   synthetic user, listing, wanted, conversation and offer relationships plus
   an approved application smoke read. Do not print credentials or private data.
2. Stop the timer only when all checks succeed. Pass only if the full interval is
   at most 30 minutes and every check passes. Preserve restore/status events and
   check results; a running database alone is not a pass. If the deadline or a
   check fails, record failure and follow the reviewed recovery/cleanup plan.
3. Delete or retain only the isolated target as specifically approved; verify
   residual billable storage/backups. Reuse this evidence for both configurations
   only if they use the same unchanged database and backup/restore procedure.

## NFR-08 — Project budget (INT-01 and CLOSE-00)

**Tooling checkpoint:** `scripts/evaluation/nfr_cost_ledger.py` validates the
append-only project ledger, reconciles billing against outstanding estimates,
reports gross costs and credits separately, and shows the USD 200 project
headroom plus the user's USD 10 AWS-credit stop condition. It cannot claim final
acceptance without complete project scope and human closeout review.

1. Before each cloud action, the owner records spend to date, delayed-billing
   estimate, current unit prices, expected and worst allowed resources/duration,
   reserve for remaining required work and a maximum incremental spend. Include
   idle compute, ECS/Lambda, ingress, database/restore storage, networking,
   images, logs and retained resources as applicable. Stop if cost or headroom
   is unknown or an approved cap is reached. Provider alerts are not hard limits.
2. After each run, record actual available billing/usage evidence and the
   estimated unbilled amount, with pricing date and assumptions. Keep comparable
   pre-credit cost separate from credits. Avoid double-counting shared resources.
3. CLOSE-00 sums all project implementation/evaluation costs across the recorded
   scope, including later experiments, cleanup and remaining liabilities. The PRD
   requires **strictly less than USD 200**; exactly USD 200 or missing evidence
   does not pass. Record the source periods and treatment of credits, refunds and
   delayed charges; obtain current bill evidence at closeout.
