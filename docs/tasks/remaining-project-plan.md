# Remaining project work: ordered task groups

**Planning branch:** task/integrated-marketplace-rollout based on remote `main` at `5e8d264018c85475fbe13809316616b63a40886e`
(PR #18), 2026-10-27. **Coordinator:** Suraj for this planning request; domain
ownership and independent review remain as recorded in the project index.
**State:** NEXT-00 planning and NEXT-01 experiment design verified by Suraj. NEXT-01 is early experiment design. All implementation,
deployment, dataset generation, research, measurements, and cleanup below are
future work. This document records the user's requested sequence and decisions;
it does not claim those tasks or existing readiness milestones are complete.

**Agent reading:** read the order table and the selected task group. Read the
detailed experiment instructions only when defining/reviewing that experiment;
follow linked canonical sources as needed for the selected task. Loading every
task and historical evidence file is not the default starting procedure.

Use this sequence to select remaining work, then execute the original owning
task's applicable steps and checks. Existing FR/NFR IDs, acceptance obligations,
and approved source PRD remain intact. Reconcile proposed scheduling/behavior
changes at the named design checkpoint before depending on them. Do not restart
completed work just because an old status row says it is missing.

## Order and dependencies

| Order | Task group | Output / gate |
|---|---|---|
| 0 | NEXT-00 — Load main and organize remaining work | This plan, preserved user directions, task-index entry and work-log checkpoint; human verifies this planning output. |
| 1 | NEXT-01 — Define and approve the experiment early | Agree the question, alternatives, requirements, score rules, controls, workloads, measures and caps; confirm later assumptions and freeze the rules before final results. |
| 2 | NEXT-02 — Reduce repository clutter and agent reading burden | First implementation group: measured cleanup with working commands, links and necessary evidence preserved. |
| 3 | NEXT-03 — Improve marketplace behavior and controls | Categories/multiple filters, previews/limits, simpler controls and essential navigation fixes; finish before cloud verification. |
| 4 | NEXT-04 — Audit completion and make the integrated app work at https://clip-iisc.site | Audit actual requirements and blockers, get approval for any new task-list items, then verify the final NEXT-03 product state in the integrated cloud app. |
| 5 / parallel | NEXT-05 — Integrate Notifications when its owner is ready | Its development runs in parallel; integrate at a suitable checkpoint and do not block independent NEXT-06/07 work. Final FR-13 acceptance remains required. |
| 6 | NEXT-06 — Generate and validate the final synthetic dataset | PRD-sized data, valid media/vector workflow, reproducible fingerprint and human-reviewed query labels; before dataset-dependent runs. |
| 7 | NEXT-07 — Run the required NFR tests and the already-designed experiment | NFR evidence and comparative runs under NEXT-01's approved method; no late redesign to favor results. |
| 8 | NEXT-08 — Select and deploy the measured architecture | Use the better eligible tested configuration; ECS is not the predetermined final choice. |
| 9 | NEXT-09 — Final usability, visual polish and red-team preparation | Last product-change group; human usability check, buying/selling clarity, visual consistency and adversarial review; revalidate affected evidence. |
| 10 | NEXT-10 — Consider optional work if time remains | Review OPT-01–03 after NEXT-09 and before CLOSE-00; select only bounded work that fits remaining time/budget and triggers required rechecks. |
| Closeout | Existing CLOSE-00 | Final regression, Notifications acceptance, cost/resource reconciliation, report/demo/submission and cleanup or explicit retention. |
| Deferred | MOBILE-REVIEW — Brief native-mobile feasibility assessment | Low priority, research only if time remains; no native app implementation selected. |

NEXT-03 product/schema changes happen before NEXT-04 cloud verification. The
planned human walkthrough therefore validates the intended product state and does
not need to be repeated because NEXT-03 lands afterward. NEXT-04 begins with a
completion/dependency audit. If it finds a real gap, draft the task-list addition
with owner, dependency and acceptance check, show it to the user, and add it only
after verification. NEXT-09 still needs a focused usability walkthrough and
regression of paths it changes; it does not automatically repeat the full cloud
deployment acceptance. Notifications development stays with its current owner.
Do not delay the first useful hosted app for optional polish or native research.

## NEXT-00 — Planning only

1. Load current remote main in a clean working checkout; preserve existing dirty
   branches and local demos. Inspect entry documents and current planning sources.
2. Put every request from this conversation into the groups below, including
   dataset generation, notifications timing, experiment rigor and final deployment
   of the chosen architecture. Identify actual dependencies instead of treating
   broad project-completion gates as technical requirements.
3. Link this plan from the project index and work log. Record source revision,
   pending verification and the first future group. Check links and coverage.

**Done for this increment:** task definitions only. No application work, cloud
operation, repository cleanup, final completion audit, experiment design or
dataset generation is authorized by this planning increment.

## NEXT-01 — Define and approve the experiment early

**Timing:** immediately after NEXT-00 verification, before repository cleanup or
implementation. **Scope:** design/documentation only; no code, cloud deployment
or measured run. Follow the separate
[experiment-definition guidelines](../evaluation/ecs-lambda-experiment-guidelines.md).
Document 2 permits EXP-01 design and the scoped read comparison before full
INT-01 under the approved real-path gates. Check assumptions affected by later
work and freeze the final approved rules before comparative results. Full
INT-01/Notifications acceptance remains required for project closeout.

1. Read the submitted PRD, Document 1, current experiment task, product decisions,
   actual main architecture and NFR requirements. State the exact question and
   the final application decision the comparison will inform.
2. Confirm alternatives before implementation. Current Document 2 proposes
   ECS-only versus ECS plus Lambda for selected read-heavy routes, leaving writes,
   chat and offers on ECS. The user expects the final app to use the better
   eligible measured architecture, not a predetermined ECS choice. Resolve
   whether the alternative is this hybrid or a broader Lambda option; do not
   silently redefine the experiment or move untested paths.
3. Identify mandatory FRs/NFRs and eligibility. Rank objectives beyond compliance;
   agree numerical weights summing to one, bounded point scales, units, direction,
   ranges, boundaries/caps, aggregation and a practical tie rule before final
   comparative measurements.
4. Define equivalent correct work, candidate routes, authorization/response
   checks, data/index requirements, representative workloads, arrival model,
   timing endpoints, cold/warm treatment, retries/failures, repetitions and
   stopping rules. Specify the complete implementation and preparation needed
   for both alternatives: exact routing and real search/model dependencies,
   deployed revision and identity, parity checks, generator and outcome checks,
   configuration and resource settings, measurement/evidence tooling, paired run
   order, telemetry, cost inputs and cleanup. Check current evidence and the
   tasks scheduled before each run; identify what those tasks are expected to
   deliver and any remaining uncovered work, with owner and acceptance checks.
   Mark assumptions the
   NEXT-03 product changes and NEXT-04 completion audit must confirm before final freeze;
   do not postpone decision rules until NEXT-07.
5. Design the [final synthetic dataset](../../data/evaluation/reference-dataset-design.md) in implementation-ready detail: exact
   proposed counts and distributions, deterministic seed, user/account classes,
   listing fields/states/images, search cases, relationships, data safety,
   reviewed relevance labels, generation/load/index/vector steps, validation and
   fingerprinting. Inspect existing tools and current schema first; preserve the
   PRD minimums and mark fields affected by NEXT-03 for later reconfirmation.
   Define the recipe now; NEXT-06 generates and verifies the actual data.
6. Specify implementation-ready procedures for NFR-01–08 in their existing
   owning task or linked canonical evidence homes. For each, map prerequisites,
   exact inputs/target and version checks, application/runtime setup, controlled
   identities and client setup, data, indexes/model, workload or fault action,
   measurement tools and telemetry, timing and success denominators, calculations,
   repetitions, outputs, failure/stop rules, resource/cost caps, cleanup, owner
   and approval gates. For every prerequisite, check current evidence and the
   outputs of the existing tasks scheduled before its measurement; identify
   what is already available, what an assigned task is expected to supply, and
   only work still uncovered by that schedule. Specify the responsible task,
   expected behavior, inputs/outputs, acceptance check and point of recheck.
   Give executable commands only where they
   exist, otherwise define the command/tool work required. A contributor should
   be able to implement and verify the procedure from these instructions without
   inventing missing technical decisions. Keep NFR-04 human labels and NFR-06/07
   cloud fault/restore approvals explicit. Separate these NFR tests from the
   architecture comparison and preserve their existing owners.
7. Define raw outputs, latency/throughput/failure metrics, telemetry, whole-system
   cost method, region/pricing date, duration/spend/resource/concurrency caps,
   stop conditions, operator and cleanup.
8. Inspect current task gates. Selected browse/search comparisons do not
   technically need email delivery; chat send-to-visible timing does not wait
   for email. Current message/thread code already writes notification intents in
   the owning transaction. Propose the precise update to the broad INT-01/EXP
   entry gate so an agreed independent comparison can run without falsely
   accepting FR-13 or full INT-01. Preserve final integration/Notifications
   acceptance. Obtain human verification of canonical gate changes first.
9. Record the reviewed design in Document 2 or its experiment manifest; update
   task-index/dependency links. Update NEXT-07 to directly reference the final
   dataset recipe, each NFR procedure and the comparison protocol so an executing
   agent can find all of them. Freeze decision rules before results. Reopen only
   for documented material requirement, implementation or validity changes,
   never to favor a result.

### Required preparation coverage for Steps 4–7

This is a design checklist, not a claim that the tools or environment are ready.
Inspect actual implementations before writing each detailed procedure.

| Check | Preparation the design must cover |
|---|---|
| NFR-01/02 | Real authorized browse/search paths and response checks; reference data, applicable indexes/model; load generator, workload, clock, failure accounting, telemetry and deployed versions. Browse excludes image bodies; the search denominator follows SE-01. |
| NFR-03 | Integrated API routes, controlled users and realistic route mix; 50 requests/s for the required measurement period; a generator that reports missed arrivals, correct outcomes and resource/DB signals. |
| NFR-04 | Fixed representative queries and listing data; human-reviewed relevance labels; evaluator, calculation, query-level results and dataset/model fingerprints. |
| NFR-05 | Two authorized clients with working encrypted messaging and polling; a clock and observer that measure sender submission through recipient display, including undisplayed or failed messages; defined normal load and sample policy. |
| NFR-06 | At least two healthy serving runtimes, verified health/routing; a controlled request stream and recovery observer; the exact separately approved runtime-loss action, time boundaries, restoration checks and cleanup. |
| NFR-07 | A known latest managed backup, approved isolated restore target, restoration observer, representative integrity/smoke checks, timing boundaries, cost limit and approved deletion or retention. |
| NFR-08 | Project-wide cost scope, spend-to-date and delayed billing, current prices/estimates, run and resource limits, reserve, stop rules and final CLOSE-00 reconciliation below USD 200. |
| ECS/Lambda comparison | Two correctly deployed and routed implementations with equivalent real authentication/search/data and verified results; fixed normal/burst workloads and generator; warm/cold and scaling observations; paired repetitions, raw results, telemetry, whole-system cost and scoring; exact operator, approvals and cleanup. |

For each row, distinguish (1) verified available outputs, (2) outputs assigned to
an existing task that should be ready by the measurement checkpoint, and
(3) genuine gaps not covered by that schedule. Link the owning task and its
acceptance check and identify when each expected output will be rechecked. Do
not create duplicate work for a scheduled output; do not treat a planned output
as already verified. For uncovered tooling, specify concrete file homes,
inputs/outputs and safe failure behavior; confirm exact run commands once the
owning task has implemented them. Preserve all required checks even when the
same preparation can be shared between a test and the comparison.

**Complete when:** The question/alternatives and measurable rules are approved;
an implementable dataset recipe, NFR procedures and complete comparison
preparation are defined in their owning homes; cost/resource limits and cleanup
are defined; source-task/gate updates are reviewed; and NEXT-07 can execute this
design once its implementation and operational prerequisites are met. This does not mean data,
alternatives or measurements are ready.

## NEXT-02 — Repository cleanup first

**Owner:** planning coordinator, with affected domain owners reviewing removals.
Keep the current checkout focused on what contributors and their agents
realistically need to work, verify results and deliver the project; archive
other material when it must remain available.

1. Measure tracked/untracked size, file/line counts and the default agent reading
   path. Distinguish application code, executable tests, fixtures/models, generated
   artifacts, raw machine output, repeated documents and historical evidence.
   Inspect actual contents before choosing removals; line count alone is not a
   reason to remove code or tests.
2. Reduce material in this order: **evaluation documentation and machine output**;
   **other documentation, including the work log**; **tests**; then **app code**.
   Focus on documentation. Tests and app code should normally remain untouched;
   consider them only for an explicitly identified, obvious and safe reduction
   with a concrete benefit and preserved behavior and coverage. Never remove a
   test merely because it is long or replace an executable test with prose.
3. Condense repetitive material into a useful current summary. Consider
   condensing or archiving older work-log entries while keeping current task
   states, decisions, blockers and links sufficient for contributors to resume
   work. Retain the original evidence wherever a summary alone would not support
   an existing claim or required review.
4. Move material outside the repository when it is not realistically needed in
   the working checkout but must be retained. Choose a durable, accessible
   archive, record its owner and retrieval path, and verify retrieval before
   removing the repository copy. Keep necessary contributor/agent instructions,
   current sources of truth, required submission artifacts, reproducibility data
   and evidence available. Respect privacy and access restrictions.
5. Distinguish agent reading burden, current checkout size and Git history size.
   Moving a file within Git does not reduce its bytes; removing a tracked file
   from the current tree does not remove it from existing Git history. Measure
   the relevant before/after sizes and do not rewrite Git history in this task.
6. Repair indexes, commands and references after moves. Make README/agent entry
   points direct agents to the current task and its necessary sources rather
   than requiring the whole archive. Report before/after sizes and reading path;
   run the relevant link/document and affected implementation checks.

**Complete when:** the repository and agent entry path are measurably more
manageable, required sources/checks still work, and removals have been reviewed.
This group handles cleanup; subsequent groups should avoid creating duplicate
reports or another competing status system.

## NEXT-03 — Marketplace behavior and everyday controls

**Owners:** Listings/Search/Conversations owners with the page maintainer.
Reserve shared composition files through the frontend collaboration procedure.
Implement related increments with automated checks before each human walkthrough.

1. Review user-facing categories against understandable marketplace categories
   such as Amazon/OLX; resolve confusing boundaries such as appliances versus
   electronics. Present the proposed taxonomy and map existing codes/data first.
   Assess actual schema/contract/filter/migration impact rather than assuming a
   label-only change. Preserve existing sale/wanted/saved data and URLs; update
   generated contracts and affected fixtures deliberately. After the final
   taxonomy is agreed, review and update the dataset recipe's category counts,
   item mappings and search cases before NEXT-06 generates or labels data.
2. Define and implement multi-selection where requested: multiple categories
   (e.g. appliances or bicycles) and conditions (e.g. Like New or better).
   Specify OR within one filter and combination across different filters,
   empty/all behavior, URL/API encoding, pagination and condition ordering.
   Do not invent a condition order without confirming its meaning. Normalize
   visible labels to proper title case, including **Like New**.
3. Remove the negotiability search filter; continue showing negotiability on
   discovery cards before the user opens full detail and on the detail page.
   Remove the visible **Sort by Relevance** control while retaining the correct
   default ranking; review any remaining sort choices rather than silently
   deleting unrelated sorting capabilities. Use Hybrid for the product search.
   For a nonblank search, make the default ordering put direct word matches
   first, expanded/typo matches next, and other meaning-based matches after
   them, ordered by the existing score within each group. The reader already
   supports this relevance ordering, but the website currently defaults to
   newest first. Preserve normal browsing and deliberate price/recency choices;
   assess existing links and API compatibility before changing legacy mode
   handling. Verify ordering with representative results across pages.
4. Replace technical image wording such as **1 out of 8 confirmed** with plain
   photo-count/status text that still explains failures or in-progress uploads.
   Add a pre-publication sale-listing preview using the normal discovery-card
   presentation and current draft/photos, without publishing it.
5. Verify/complete Wanted Request draft matching: show existing sale listings
   matching the request while it is composed, without saving the draft merely
   to search. Reuse the real search path and existing implementation. Confirm
   the intended interaction before implementation because the user's original
   sentence about the preview was unfinished. Search failure must not erase
   the draft or unnecessarily prevent a valid request from being submitted.
6. Check title/description and other length/field limits for both sale listings
   and wanted requests against the PRD, approved contracts and server rules.
   Align UI validation, counters and server errors; test boundary, empty,
   whitespace and relevant Unicode cases. Do not invent new numerical limits.
7. Fix essential buying/selling navigation: make creating a Wanted Request
   reachable from the relevant buying/discovery context, rather than only My
   Listings. Check meaningful header/tab/link names and destinations. Verify
   Conversations grouping and Close deal against approved CN rules; NEXT-04
   audits the resulting integration and cloud behavior. Implement any known
   gaps through the owning feature. Leave the broader aesthetic refresh to
   NEXT-09.
8. Verify changes locally. Finish schema/ranking/filter changes before freezing
   data and measurement settings; a later behavior change triggers an evidence-
   impact review. Cloud verification belongs to NEXT-04 after these changes.

## NEXT-04 — Completion audit and integrated HTTPS cloud app

**Sources:** [domain tasks](domain-task-list.md), [work log](../status/work-log.md),
[product reference](../product/product-reference-and-architecture-decisions.md),
[submitted PRD](../source/ICC_Project_PRD_FINAL.pdf), current merged code/tests,
pending integration ledger and actual current contributor branches/PRs.

1. Audit each required domain task and FR against current main and evidence.
   Distinguish implemented, connected, locally checked, human checked, deployed
   and measured. Reconcile stale rows without blindly treating merged code as
   full acceptance. Inspect workers, retirement/retention cleanup, real capability
   matrices, migrations and supported-device checks as well as visible features.
2. Produce a compact gap list with owner, original checkpoint, blocking
   dependency and acceptance check. Validate the user's expectation that most
   remaining work is deployment, Notifications and evaluation; explicitly list
   any additional implementation or acceptance gaps found.
3. For any uncovered requirement or dependency found in this audit, draft a precise task-list addition with owner, acceptance check and dependency. Show it to the user and add it only after the user verifies it; do not silently expand scope.
4. Verify already-requested Search behavior: Hybrid is the default and no
   Keyword/Hybrid selector appears in the product UI; inspect actual candidate
   retrieval/combination so eligible keyword and semantic candidates are combined
   and deduplicated. Do not require a particular sequential implementation merely
   because the user described it as two steps. Distinguish union/coverage from
   ranking quality and preserve the approved error/availability behavior.
5. Verify Conversations integration, inbox grouping by sale listing/wanted
   request, seller selection and the requested Close deal action against CN-01/
   CN-02 rules. Define exactly which approved state change Close deal invokes;
   do not add payment verification or silently change availability rules.
6. Verify the temporary zero-photo Identity-demo workaround and its flags,
   routes, triggers and tests are absent; current main's consolidated
   [postmortem](../evaluation/identity/id-01-step-12/demo-postmortem-20261026.md)
   already reports its removal. Clean only proven leftovers. Normal publication
   still requires one to eight images.
7. Record final synthetic data and labeling as explicitly unfinished work under
   NEXT-06. Existing generators, unit fixtures, preview labels and tiny demo
   databases do not establish DATA-READY.
8. Map each NFR/experiment route to its actual dependencies. Resolve scheduling
   amendments described under NEXT-05/NEXT-07 with the human and update affected
   canonical task instructions before executing against a revised gate.
### Integrated cloud deployment

**Reuse:** [ID-01 postmortem](../evaluation/identity/id-01-step-12/demo-postmortem-20261026.md),
[cloud inventory](../environment/cloud-inventory.md),
[Listings/Search deployment notes](../architecture/listings-search-deployment.md),
[isolated LI-02 lifecycle](../../infra/terraform/domains/listings/test/README.md)
and its existing scripts. Reuse demonstrated mechanisms without deploying the
isolated synthetic-identity profile as the real integrated application.

1. Verify the full non-notification composition locally through real public
   domain interfaces: Identity, images, sale listings, search/browse, saved
   listings, wanted requests, private conversations, offers/selection/contact
   sharing. Fix concrete missing connections or required behavior. Use real
   implementations for implemented domains; identify any truly unavailable path.
2. Inspect current AWS state and Terraform state/source together. Recheck the
   service revision mismatch from the postmortem before any apply. Preserve DB
   data; reconcile drift through a reviewed plan. Confirm account/region,
   operator, remaining budget, runtime/model/image revisions and capacity limits.
3. Resolve supported HTTPS ingress for `clip-iisc.site`, account load-balancer
   restrictions, certificate/DNS correctness and trusted forwarded headers.
   Recheck public and IISc DNS rather than assuming the old cache/IP is current;
   arrange removal/correction of any released-IP DNS record. Do not reintroduce
   the temporary proxy-trust bypass or assume a rejected NLB now works.
4. Prepare the exact reviewed deployment/start/stop/cleanup plan. Include real
   auth, cookies/CSRF, appropriate IAM, private image storage/CORS, approved
   migrations and DB trust, Hybrid helper/model/worker and pipeline preparation/
   activation. Ensure new listing creation and edits automatically update
   vectors through the normal application workflow. Never copy vectors to fake
   integration. Set duration/resource/cost caps and retained-resource ownership.
5. Deploy only after the action's approval. Exercise real sign-in, image upload/
   confirm/display, create/edit/unavailable transitions, search, wanted/saved,
   conversations, offers/selection/close-deal and consented contact sharing using
   controlled accounts. Check permissions and failures as well as success.
6. The agent runs command-based checks first, including a newly created listing,
   automatic vectors and its appearance through Hybrid search. Then provide the
   URL, desktop/phone actions and expected outcomes for the human walkthrough.
   Fix failures and repeat affected checks before calling the hosted app usable.
7. Record exact versions and a reproducible start/stop route, including a
   post-stop inventory of residual NAT, storage, addresses, images and schedules.
   A usable app without Notifications is an intermediate delivery, not full
   FR/NFR/project acceptance. Initial ECS use is a baseline for later comparison.


**Output:** current facts and a prioritized gap list, not another blanket claim
that everything beyond cloud is done; plus a human-verified integrated cloud
walkthrough. Route missing required behavior into its owning group. Any newly
discovered task-list addition requires human verification before it is added.

## NEXT-05 — Notifications integration when its owner is ready

**Owner:** existing CN-03 owner; consuming domains support integration. Inspect
their actual branch/checkpoint before claiming work or duplicating implementation.

1. Integrate the finished delivery implementation into the working cloud app at
   the earliest suitable time. Verify current atomic notification recording,
   background dispatch, recipient resolution, preferences/eligibility,
   deduplication/retries, unread suppression and terminal retention through real
   provider/runtime checks and controlled recipients. Provider failure must not
   undo the successful primary conversation/message operation.
2. Distinguish recording notification work from delivering email. Current main
   already records new-conversation notification work in
   `apps/api/app/domains/conversations/thread_creation.py` and updates unread
   reminder work during message persistence in
   `apps/api/app/domains/conversations/messages.py`. The main-line chat test can
   include that database work without waiting for email delivery to exist.
3. Browse/search/detail comparison and active-chat sender-to-display timing do
   not inherently require email delivery. Allow preparation and accurate checks
   of implemented paths before the delivery worker is ready. Record which worker
   is disabled/enabled, and use equivalent settings in both experiment variants.
   Do not claim Notifications passed while it is absent.
4. At integration, inspect whether producer/read-state transactions, locks,
   schema, app resources or shared DB load changed. Recheck affected chat/API
   latency or comparative results when material; unchanged paths do not need a
   blanket repeat of every test. If a workload is intended to represent the
   complete running app, include its representative background work or state
   the limitation and defer that full-system claim.
5. NEXT-01 Steps 8–9 reviewed and applied the scheduling correction: permit
   independent real-path measurements and a scoped comparison under their
   specific gates, while preserving final FR-13/INT-01 acceptance. Recheck the
   actual paths and approved run procedure before relying on these gates.

## NEXT-06 — Generate the missing final synthetic data

**Owner:** Search/data owner under SE-01 steps 2/4/9 and DATA-READY; domain owners
review their records. Read the submitted PRD and current approved data rules.

1. Inspect the existing deterministic generator, schema-aware loaders, fixtures,
   seed/label tooling and any retained valid dataset. Identify what is genuinely
   reusable and what is still missing. Do not equate generator implementation
   with having generated, loaded and verified the required final data.
2. Generate at least **5,000 synthetic users and 1,000 synthetic listings**, as
   required by the PRD. Use the final taxonomy, schema and relevant runtime
   settings; include representative text/categories/conditions/prices,
   availability and meaningful queries, not only kettles. Add controlled
   wanted/conversation/offer/notification data where required by the workload.
   No real personal data, accidental emails or provider sends from bulk seeds.
3. Load through an explicitly reviewed reproducible schema-aware path. Verify
   relationships, eligible user classes, constraints, counts, availability,
   ownership and indexes. Validate media references for cloud paths. Bulk
   generation need not manually click every UI, but new-listing/vector behavior
   must also be checked through the normal app workflow.
4. Prepare/queue/process/activate the pinned embedding pipeline through existing
   supported tooling, verify complete current vector coverage and failures, and
   check representative keyword/semantic results. Do not copy unrelated vectors
   or treat generated vectors alone as proof of good search quality.
5. Create at least **20 human-reviewed representative search queries** with
   relevant listing IDs, reviewer/date and inclusion rules. Reuse the approved
   label format; machine proposals are not human review. Preserve labels rather
   than changing them to force Success@5 to pass.
6. Record seed, generator/config/version, actual counts, image/model/index state
   and repeatable logical fingerprint. Validate reset/reload on an isolated
   target and freeze the dataset for final runs. DATA-READY needs actual checks;
   a small hosted demo can precede it, final dataset-dependent evidence cannot.

## NEXT-07 — Required NFR evidence and rigorous architecture experiment

**Owners:** existing SE-01/CN-01/INT-01 and EXP-01–08 owners. Use the
[canonical experiment tasks](../evaluation/ecs-only-vs-ecs-lambda-task-list.md)
as the execution home; this group preserves new planning requirements.

1. Reconfirm the approved NEXT-01 question, alternatives, applicable PRD
   requirements and eligibility rules against the implementation that will be
   measured. Do not silently broaden the experiment or predetermine a winner.
2. Create the missing NFR tools/manifests and run each accurate test at its
   earliest real verification point. Reuse valid evidence; route gaps into the
   owning original task. Keep required NFR evidence distinct from comparative
   performance results. Review Notifications dependencies as NEXT-05 specifies.
3. Before final comparative results are collected, price the exact reviewed A/B
   topology and normal workload, calculate and document the numeric good/poor
   cost-score endpoints, per-run allocation formula, price sources and
   assumptions, and obtain human verification of those frozen endpoints. Do not
   choose endpoints from final A/B outcomes. If topology or prices materially
   change, review and verify revised endpoints before replacement final results.
   Then execute the already designed NEXT-01 experiment under the separate
   [experiment-definition guidelines](../evaluation/ecs-lambda-experiment-guidelines.md).
   Do not change scoring or workload after seeing comparative final results; a
   material validity change needs documented human approval.
4. Follow EXP-02–08: prepare data/tools, implement and test the alternative,
   review plans, deploy/smoke both, pilot separately, run approved repetitions,
   analyze with uncertainty and costs, preserve evidence, and verify cleanup.
   NEXT-01 defines the method early; NEXT-07 runs it only after the data and
   measured paths are ready.
   After the approved runs and cleanup, turn off app/experiment compute until
   the demo or another separately approved necessary check; retain required data,
   evidence and a reviewed restart path, and account for any remaining costs.
5. Report the eligible winner, practical tie, inconclusive result or neither
   eligible. State what the data supports. Carry the selected architecture and
   any required follow-up into NEXT-08; do not merely write a report and leave
   an unchosen default in the final deployment.

The PRD targets to operationalize and verify are:

| Requirement | Required target / execution home |
|---|---|
| NFR-01 | Browse at 20 requests/s: at least 95% of successful requests within 1 second, excluding image bodies; SE-01. |
| NFR-02 | Indexed search at 10 requests/s: at least 95% within 1 second with the canonical eligible-request denominator; SE-01. |
| NFR-03 | 50 requests/s for five minutes, at least 95% successful, excluding intentionally rate-limited abuse; INT-01. |
| NFR-04 | Success@5 at least 80% over 20+ human-reviewed queries on fixed data; offline SE-01 evaluation. |
| NFR-05 | Both users viewing chat: at least 95% of messages visible within 5 seconds of send under defined normal workload; CN-01. |
| NFR-06 | From at least two healthy serving instances, restore configured healthy capacity within 240 seconds after approved forced runtime loss; record request failures; INT-01. |
| NFR-07 | Latest managed backup restored to a usable isolated test DB within 30 minutes, verified by integrity/smoke checks; INT-01. |
| NFR-08 | Total implementation/evaluation cloud spend strictly below USD 200; caps before every run, ongoing accounting, final reconciliation in CLOSE-00. |

Reference data is at least 5,000 users/1,000 listings; performance measurements
last at least five minutes after warm-up and distinguish relevant cold/warm
behavior. Read the original PRD before freezing operational definitions. A
different final architecture must still meet applicable mandatory requirements;
check recovery and affected user paths on the actual selected configuration.

### Experiment protocol reference

NEXT-07 executes the reviewed NEXT-01 design using the
[reference dataset recipe](../../data/evaluation/reference-dataset-design.md),
[NFR-01–08 measurement procedures](../evaluation/nfr/measurement-design.md),
[comparison question and alternatives](../evaluation/ecs-only-vs-ecs-lambda-task-list.md#next-01-step-1--question-and-requirement-framing),
[decision rules](../evaluation/ecs-only-vs-ecs-lambda-task-list.md#next-01-step-3--proposed-eligibility-and-decision-rules),
[workload](../evaluation/ecs-only-vs-ecs-lambda-task-list.md#next-01-step-4--proposed-workload-and-preparation),
[costs and limits](../evaluation/ecs-only-vs-ecs-lambda-task-list.md#next-01-step-7--proposed-costs-limits-and-evidence),
[measurement gates](../evaluation/ecs-only-vs-ecs-lambda-task-list.md#next-01-step-8--proposed-changes-to-measurement-gates),
and [experiment-definition guidelines](../evaluation/ecs-lambda-experiment-guidelines.md).
It covers required NFR measurements at accurate integration points and the
predefined comparison. It does not wait until this stage to invent weights,
score ranges or a decision rule. If a material code/requirement change invalidates
the protocol, document it and obtain approval for a revised design before
inspecting affected final results.

## NEXT-08 — Deploy the chosen architecture

1. Apply the agreed eligibility/scoring/tie rules to valid results. Present the
   supported choice and obtain the human's decision; if inconclusive, gather only
   decision-critical additional evidence or use the previously agreed tie rule.
   Never assume ECS must remain the winner or that Lambda must win.
2. Turn the selected tested configuration into the final reproducible runtime
   and infrastructure path, including `https://clip-iisc.site`, auth/images,
   Hybrid workers and Notifications when ready. If the winner is ECS+Lambda,
   preserve the tested division of routes; a winner for read offload alone does
   not justify moving untested writes/chat to Lambda.
3. Review the exact deployment/retirement plan before changing cloud resources.
   Update documentation/configuration defaults to the accepted choice, remove
   obsolete competing runtime resources through approved cleanup, preserve
   experiment evidence and verify residual costs. Verify the final deployed
   journeys and affected NFRs against its actual versions/settings.

## NEXT-09 — Final usability, visual refresh and adversarial review

This is the final planned usability and security group. Optional features may
follow in NEXT-10 if selected, with affected checks repeated. Establish basic
security before first cloud exposure in NEXT-04; the deeper final review is not
permission to leave a known security defect deployed until the end.

1. Walk through the app as a new buyer and seller. Evaluate whether people can
   understand page names, headers/tabs/links, sale versus wanted requests,
   publication actions, saved items, conversation groups, offers, selection and
   Close deal without developer explanation. Observe real human desktop/phone
   use and fix concrete confusion. Ensure buying/selling entry points and Wanted
   Request creation are obvious; build on NEXT-03's functional navigation fixes.
2. Refresh visual consistency and presentation: cards/images, buttons versus
   links, typography/spacing, forms, responsive layouts and clear empty/loading/
   error/success states. Reuse feature components; keep technical storage/vector/
   pipeline details out of the ordinary user flow. Confirm behavior with the human.
3. Review the repo/app assuming peers can read source and use their own agents
   to attack it. Define an authorized bounded test scope, controlled identities,
   safe data and fixes. Cover unauthorized/cross-user access, regular/temporary/
   expired permissions, sessions/CSRF/proxy trust, injections/XSS, upload/signed
   URLs, contact consent/encryption/key boundaries, retries/replays/concurrency,
   offers/selection, rate/resource exhaustion, dependencies/secrets, workers/
   retention and IAM. Fix actual weaknesses and add meaningful regression checks;
   protect real accounts, retained data and shared resources during tests.
4. Review all late changes against measured paths. Rerun affected functional,
   security and NFR checks; if comparative conditions changed, revalidate both
   alternatives rather than keeping a stale winning score. Record remaining
   limits honestly, then hand the final tested revision to CLOSE-00.

## NEXT-10 — Consider optional work if time remains

After NEXT-09 and before CLOSE-00, review existing OPT-01 weekly wanted-request
digest, OPT-02 wanted-match alerts and OPT-03 image-aware search. Check remaining
time, budget, team capacity and deadline. Select none, one or more only through
the existing per-task OPTIONAL-OK decision and protected required-work/budget
buffer. If selected, complete its real prerequisites and checks, rerun affected
NFR/experiment evidence and update final cost accounting. Considering options is
not selection or approval to start them.

## MOBILE-REVIEW — Deferred native-mobile feasibility only

If time remains after required work is protected, briefly assess responsive web/
PWA, a native wrapper and a separate native client: reuse, auth redirects,
uploads/camera, encrypted-chat/device-key storage, notifications and distribution.
Give effort/risk estimates and a recommendation. Native mobile is explicitly
outside the submitted MVP scope; no mobile implementation is selected by this
plan and this research must not delay the working web app or required evidence.

## Execution handoff

After human verification of NEXT-00, start NEXT-01 under the repository's
normal step-verification protocol. It is an early experiment-design task, not an
experiment run. Then follow the numbered order table; NEXT-05 can proceed in
parallel when Notifications is ready. Keep detailed execution/results in the original task homes and
work log, and update this sequence only for actual
scope/dependency decisions. Preserve independent review and explicit approval
for concrete merges, cloud mutations, paid runs and destructive cleanup.
