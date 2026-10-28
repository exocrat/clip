# Campus Marketplace — Project Task and Milestone Index

**Canonical path:** `docs/tasks/project-task-index.md`

**Current remaining-work plan:** [Ordered task groups NEXT-00–10](remaining-project-plan.md)
records Suraj's 2026-10-27 direction. The order is: define the ECS/Lambda
experiment early; reduce repository clutter; complete the NEXT-03 marketplace
changes; then NEXT-04 audits readiness and verifies the integrated app on HTTPS,
so the cloud walkthrough does not need to be repeated after those changes. Notifications
joins when ready, followed by final synthetic data, required NFR/experiment runs,
deployment of the measured eligible architecture, final usability/security work,
optional work if time remains, and CLOSE-00. Suraj verified NEXT-00 and the
NEXT-01 experiment design. Use the original task sources for detailed
implementation and acceptance. The experiment method is in the separate
[ECS/Lambda experiment guidelines](../evaluation/ecs-lambda-experiment-guidelines.md).
[Dataset recipe](../../data/evaluation/reference-dataset-design.md),
[NFR measurement design](../evaluation/nfr/measurement-design.md) and
[comparison design and gates](../evaluation/ecs-only-vs-ecs-lambda-task-list.md#next-01-step-1--question-and-requirement-framing)
provide the reviewed early-design handoff; actual run readiness and peer-reviewed
merge remain pending.
Native-mobile feasibility is deferred research only; no native build is selected.

## Execution source and phase routing

This index supplies the current work route and readiness definitions. The
remaining-work plan sets the order; active task sources hold detailed steps.
Root `CONTRIBUTING.md` is the Git/PR workflow and
`docs/prompts/reusable-task-prompt.md` is the human-verification loop. Status
and evidence come from the work log and current repository checks.

| Stage | Task source / route | Gate for advancing |
|---|---|---|
| Initial repository | BOOT-00 seed and provenance in the [work log](../status/work-log.md) | Complete; use the existing clone and current work plan |
| Foundation | [Accepted PD-19/PRE-00 handoff](../status/foundation-handoff.md) | Complete; use current environment/database/cloud guides for operations |
| Contracts and domains | `docs/tasks/domain-task-list.md`: DL-00, readiness checkpoints, required domain tasks, INT-01 | Full required FR and NFR-01–07 verification; budget-to-date/reserve; accepted INT-01 revision |
| Primary comparison | `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md`: EXP-01–EXP-08 | Reviewed parity/design/implementation, valid results/analysis and cleanup |
| Final closeout | `docs/tasks/final-closeout-task-list.md`: CLOSE-00 | Current regression/evidence, final NFR-08/cost/resources, report/demo/package and honest submission status |
| Selected optional work | Domain task list OPT-01–03 | Own prerequisites plus OPTIONAL-OK; does not replace required stages |

PD-19/PRE-00 were accepted. The [foundation handoff](../status/foundation-handoff.md)
and [work log](../status/work-log.md) retain the accepted result and limits;
the original detailed PD procedures remain in Git history. The
[database integration handoff](../decisions/database-integration-handoff.md)
records how carried PD-08 checks were completed. Refresh the
[cloud inventory](../environment/cloud-inventory.md) and follow current
Terraform runbooks before any cloud action. Frontend work follows the
human-verified ownership and public-entry map in
`docs/architecture/frontend-collaboration.md`.

## Readiness milestone definitions

| Milestone | Creating checkpoint and acceptance |
|---|---|
| PRE-00 | PD-19 plus every required foundation gate; accepted per the [foundation handoff](../status/foundation-handoff.md). |
| ID-READY | ID-01 step 12 reviewed/merged usable auth/capability/contact interfaces, schema/config/provider safety and local/API/UI checks. Later full consumer matrix is pending. |
| LI-CORE | LI-01 step 11 reviewed/merged listing/owner/read/availability/selection and listing-offer-command interfaces with local tests against a reviewed Conversations double. ID-READY is required before real auth/FK/migration integration is accepted; real Conversations offer writes, images and discovery end-to-end completion remain pending their owning tasks. |
| SE-CORE | SE-01 step 10 reviewed/merged functional search/browse/filter/sort/pagination, supported listing-data boundary and validated local workload tooling. Final cloud NFR results are pending. |
| DATA-READY | SE-01 steps 2/4/9: final schema/config-aware generated/loaded data, >=5,000 users/>=1,000 listings, constraints/availability/search indexes and repeatable logical fingerprint, 20+ human-reviewed query labels. Image references validated before cloud runs; image-aware labels remain OPT-03's output. |
| CN-CORE | CN-01 step 10 reviewed/merged private-message/E2EE/read-watermark/event interfaces and local/adversarial tests. Final Conversations-owned notification producer integration and cloud NFR-05 remain pending. |
| OPTIONAL-OK | For EACH selected optional task: human selection and approval of its bounded effort/cost/resources/test scope protecting required MVP, NFR checks, primary experiment, budget and final submission buffer. A previous optional selection does not select all options. |

Milestone acceptance requires actual capabilities/checks, step verification, peer review and merged main revision/evidence. Task status stays in progress/blocked until remaining required steps pass. A missing/failed check or a required blocker cannot be counted as accepted readiness/full completion.

## Selecting and resuming current work

Follow the [remaining-work plan](remaining-project-plan.md) for NEXT-00–10,
Notifications timing and CLOSE-00. Use the domain task list and experiment
design for detailed dependencies, and reconcile each dependency with the
current work log and repository state. Do not restart a completed foundation
task or treat a planned output as already verified.

## Four-person assignment and peer review

Roles A/B/C/D map to the people in the [work-log roster](../status/work-log.md). Shared roles use those same four humans; no extra staff are required. Adjust future assignments through a recorded human decision when actual effort calls for it.

| Contributor | Implementation ownership | Primary peer | Shared review/support |
|---|---|---|---|
| A | ID-01; CN-03; optional OPT-01 if selected | D | Identity/contact/recipient interfaces; default DL-00/INT-01/CLOSE-00 coordination |
| B | LI-01; LI-02 | C | Authoritative buyer-selection/availability interfaces; cloud configuration/recovery slice |
| C | SE-01; SE-02; optional OPT-02/03 if selected | B | Dataset/labels, NFR-01/02/04, workloads and peak API evaluation |
| D | CN-01; CN-02 | A | E2EE/private messaging, NFR-05, notification producer integration; B also reviews listing selection |

DL-00: each owner drafts/reviews its domain contract; A coordinates combined artifacts and D is the primary independent peer. INT-01: A coordinates; A verifies identity/notifications, B images/listings and isolated DB-restore preparation/evidence, C search/peak-load tooling/evidence, D conversations and runtime-loss preparation/evidence. The named cloud operator serializes actual recovery/load/deployment runs. All owners review the integrated journey and fix only their owned implementation through PRs.

Experiment allocation: EXP-01/02 C; EXP-03/04 B; EXP-05/06 C with B infrastructure support; EXP-07 A with C/D raw-data/calculation review; EXP-08 B with A cost review. CLOSE-00 A coordinates, each owner runs/fixes its domain slice, C checks results/report, B resources/cost evidence, D encryption/demo evidence. Peer human approvals remain independent of authors.

## Selecting work without human cross-reference

Read roster and actual main plus active assigned branch/PR checkpoints. Respect an explicitly requested task/member. If no task is specified, use the phase route and select the first unexecuted unblocked step of required work OWNED by this contributor; resume pending verification/partial checkpoint first. A task owner is unique. Ask if ownership/order is genuinely ambiguous. Optional work needs explicit selection and OPTIONAL-OK.

The claim and shared-path coordination workflow is in CONTRIBUTING.md; the branch work log carries live checkpoints and the coordinator serializes shared main-status updates. Refresh relevant remote branches/PRs so old main status is not treated as proof of availability. Update the repository registry for ownership changes before dependent work. Reports always show expected versus observed evidence; humans verify and decide, agents investigate and execute.

## Commands

Use the [common command index](../environment/commands.md) for shared entry points and each owning guide for exact inputs, targets, expected output, and safe failure behavior. An output assigned to the active step is work; a missing prerequisite is a blocker.

## Completion-dependency registry

The graph is derived from the following acceptance dependencies. For multi-stage tasks, these rows describe FINAL acceptance; their START/checkpoint dependencies are above and in the domain task. Internal numbered step order still applies. Supporting milestones are not additional feature tasks.

| Accepted task/milestone | Prerequisites for that acceptance |
|---|---|
| PRE-00 | Foundation handoff accepted; see work log and handoff summary |
| DL-00 | PRE-00 |
| ID-READY | DL-00 |
| LI-CORE | DL-00, ID-READY |
| SE-CORE | ID-READY, LI-CORE |
| DATA-READY | ID-READY, LI-CORE |
| LI-02 | LI-CORE, ID-READY |
| LI-01 | LI-CORE, LI-02, SE-CORE |
| SE-01 | SE-CORE, LI-01, LI-02, DATA-READY |
| SE-02 | SE-CORE, ID-READY, LI-CORE |
| CN-CORE | ID-READY, LI-CORE |
| CN-02 | CN-CORE, ID-READY, LI-CORE, SE-02, CN-01 |
| CN-03 | CN-CORE, ID-READY |
| CN-01 | CN-CORE, CN-03, SE-02 |
| ID-01 | ID-READY, LI-01, LI-02, SE-CORE, SE-02, CN-CORE, CN-02 |
| INT-01 | ID-01, LI-01, LI-02, SE-01, SE-02, CN-01, CN-02, CN-03 |
| OPTIONAL-OK | Explicit per-task human priority/capacity decision |
| OPT-01 | ID-READY, SE-02, CN-03, OPTIONAL-OK |
| OPT-02 | ID-READY, LI-CORE, SE-CORE, SE-02, CN-03, OPTIONAL-OK |
| OPT-03 | LI-02, SE-CORE, DATA-READY, OPTIONAL-OK |
| EXP-01 | Early design may start before INT-01 |
| EXP-02 | EXP-01 |
| EXP-03 | EXP-02 |
| EXP-04 | EXP-03 |
| EXP-05 | EXP-04 |
| EXP-06 | EXP-05, DATA-READY and the approved real read-path/action gates in Document 2 Step 8 |
| EXP-07 | EXP-06 |
| EXP-08 | EXP-07 |
| CLOSE-00 | INT-01, EXP-08 |

`docs/architecture/task-dependencies.dot` is the derived Graphviz view; update it with this index if dependencies change. Detailed task steps and observed evidence determine actual readiness.

## Startup and parallel work

Follow the active task's current dependency and ownership instructions. WSL is
optional; use its setup guide only when the contributor is working in WSL.
Notifications may proceed independently when its owner is ready, as described
in the remaining-work plan.
