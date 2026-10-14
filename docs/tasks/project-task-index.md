# Campus Marketplace — Project Task and Milestone Index

**Version:** 3.0 · **Date:** 2026-10-14 · **Canonical path:** `docs/tasks/project-task-index.md`

## Execution source and phase routing

This index supplies the next-work route and readiness definitions. Detailed numbered procedures remain in the linked task lists. Root `CONTRIBUTING.md` is the Git/PR workflow; `docs/prompts/reusable-task-prompt.md` is the mandatory human-verification loop. Status/evidence are actual execution facts, not claims made by this planning document.

| Stage | Task source / route | Gate for advancing |
|---|---|---|
| Initial repository | `docs/tasks/bootstrap-task-list.md`: BOOT-00 | Verified documentation/Git seed, source provenance, actual roster/remote status |
| Foundation | `docs/tasks/pre-domain-task-list.md`: PD-00–PD-19 | PRE-00: every required foundation check passes, human verification, accepted PD-19/main handoff |
| Contracts and domains | `docs/tasks/domain-task-list.md`: DL-00, readiness checkpoints, required domain tasks, INT-01 | Full required FR and NFR-01–07 verification; budget-to-date/reserve; accepted INT-01 revision |
| Primary comparison | `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md`: EXP-01–EXP-08 | Reviewed parity/design/implementation, valid results/analysis and cleanup |
| Final closeout | `docs/tasks/final-closeout-task-list.md`: CLOSE-00 | Current regression/evidence, final NFR-08/cost/resources, report/demo/package and honest submission status |
| Selected optional work | Domain task list OPT-01–03 | Own prerequisites plus OPTIONAL-OK; does not replace required stages |

## Readiness milestone definitions

| Milestone | Creating checkpoint and acceptance |
|---|---|
| PRE-00 | PD-19 plus every required foundation gate; reviewed merged handoff and human acceptance. Defined in pre-domain list. |
| ID-READY | ID-01 step 12 reviewed/merged usable auth/capability/contact interfaces, schema/config/provider safety and local/API/UI checks. Later full consumer matrix is pending. |
| LI-CORE | LI-01 step 11 reviewed/merged listing/owner/read/availability/selection interfaces and local tests. ID-READY is required before real auth/FK/migration integration is accepted; real images/discovery end-to-end completion is pending. |
| SE-CORE | SE-01 step 10 reviewed/merged functional search/browse/filter/sort/pagination, supported listing-data boundary and validated local workload tooling. Final cloud NFR results are pending. |
| DATA-READY | SE-01 steps 2/4/9: final schema/config-aware generated/loaded data, >=5,000 users/>=1,000 listings, constraints/availability/search indexes and repeatable logical fingerprint, 20+ human-reviewed query labels. Image references validated before cloud runs; image-aware labels remain OPT-03's output. |
| CN-CORE | CN-01 step 10 reviewed/merged private-message/E2EE/read-watermark/event interfaces and local/adversarial tests. Final notification write-path integration and cloud NFR-05 remain pending. |
| OPTIONAL-OK | For EACH selected optional task: human selection and approval of its bounded effort/cost/resources/test scope protecting required MVP, NFR checks, primary experiment, budget and final submission buffer. A previous optional selection does not select all options. |

Milestone acceptance requires actual capabilities/checks, step verification, peer review and merged main revision/evidence. Task status stays in progress/blocked until remaining required steps pass. A missing/failed check or a required blocker cannot be counted as accepted readiness/full completion.

## Task starts and dependency-sensitive continuation

After real PRE-00/DL-00, all eight required domains may begin their documented isolated checkpoints using reviewed test doubles under `docs/architecture/stubs-and-integration-gates.md`. Domain-list named milestones remain real integration/acceptance gates. The agent explains the mode, exact checks and pending real obligations before human verification; a stub-only PR is not a readiness milestone. Within-task later checkpoints have additional prerequisites:

- ID-01 step 14 needs implemented consumer paths from LI-01/LI-02, SE-CORE/SE-02 and CN-CORE/CN-02; policy helper tests alone are not the final FR-03 matrix.
- LI-01 step 13 needs LI-02 and SE-CORE for full image-backed publication and unavailable discovery. LI-CORE has separate acceptance before these checks.
- SE-01 cloud-preparation step 12 needs LI-01/LI-02, ID-READY and final validated data. DATA-READY is required for the complete measurement/evaluation evidence.
- CN-01 cloud-preparation step 11 needs CN-03's final producer/notification/read-state path. CN-CORE unblocks CN-02/CN-03 before final NFR-05.
- INT-01 needs all eight required domain tasks fully passing; EXP-01 follows its verified merge. NFR-08 final reconciliation occurs in CLOSE-00 after EXP-08, not before later experiment spend.

Preserve numbered step order except the explicit staged-checkpoint route in the stub guide: human-verified isolated portions may advance while real subchecks remain pending under their original step IDs. As real prerequisites arrive, resume the earliest pending integration checkpoint before new isolated work. If the next checkpoint is non-substitutable, record the blocker and propose another owned unblocked task. The human verifies that new task understanding before switching. Do not restart an executed step or skip its human-verification gate.

## Four-person assignment and peer review

Map A/B/C/D to actual people in the work-log roster during BOOT-00/PD-03. Shared roles use those same four humans; no extra staff are required. Initial allocation balances broad work packages, but actual effort must be inspected and future assignments adjusted through a recorded human decision if needed.

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

## Command and artifact responsibility

| Required output | Creator / readiness |
|---|---|
| Canonical docs/prompt/checklists/status and Git entry points | BOOT-00; PD-01/03 reconcile and extend |
| Pinned Black/install/format/check | PD-02/04, documented actual targets before consumers |
| Safe local setup/start/stop/migrate/seed/test/check | PD-05/07/08/12/13; PRE-00 validation |
| Generator tooling / final schema loaders and labels | PD-09 framework; SE-01/DATA-READY final domain data |
| Core/provider fixtures; schema-specific/domain fixtures | PD-10 core; named domain implementation tasks |
| Contract generator/stale check and actual editable source | PD-11 initial tooling; DL-00/domain tasks public contracts |
| Terraform plan/apply/deploy/verify/rollback/teardown route | PD-15/16 shared, each domain/EXP-03 scoped additions |
| Provider setup and recipient/read-state interfaces | ID-01/CN-01/CN-03, with approved access/secret references |
| NFR workload/manifest/evaluator/recovery/restore tooling | SE-01, CN-01, INT-01 before their accurate runs |
| Lambda packaging/routing/parity/resource plan | EXP-03; approved actual deployment EXP-04 |
| Report/demo/viva/artifact hashes/submission handoff | CLOSE-00 |

PD-03 initializes `docs/environment/commands.md`; creator tasks record actual command spellings, arguments, target/effects/readiness, expected output and safe failure. Missing outputs explicitly assigned to the current step are implemented there; missing prerequisite commands are blocking inputs. Do not invent executed commands or imply an example is configured.

## Completion-dependency registry

The graph is derived from the following acceptance dependencies. For multi-stage tasks, these rows describe FINAL acceptance; their START/checkpoint dependencies are above and in the domain task. Internal numbered step order still applies. Supporting milestones are not additional feature tasks.

| Accepted task/milestone | Prerequisites for that acceptance |
|---|---|
| BOOT-00 | Approved supplied bundle and human-verified bootstrap scope |
| PD-00 | BOOT-00 |
| PD-01 | PD-00 |
| PD-02 | PD-01 |
| PD-03 | PD-02 |
| PD-04 | PD-02 |
| PD-05 | PD-02, PD-04 |
| PD-06 | PD-05 |
| PD-07 | PD-02 |
| PD-08 | PD-02, PD-04, PD-05 |
| PD-09 | PD-06, PD-08 |
| PD-10 | PD-04, PD-05, PD-06 |
| PD-11 | PD-05, PD-06, PD-07 |
| PD-12 | PD-04, PD-05, PD-06, PD-07, PD-08, PD-09, PD-10, PD-11 |
| PD-13 | PD-04, PD-05, PD-06, PD-07, PD-08, PD-09, PD-10, PD-11, PD-12 |
| PD-14 | PD-01, PD-02, PD-03 |
| PD-15 | PD-14 |
| PD-16 | PD-04, PD-05, PD-06, PD-07, PD-08, PD-09, PD-10, PD-11, PD-12, PD-13, PD-14, PD-15 |
| PD-17 | PD-14, PD-15, PD-16 |
| PD-18 | PD-01, PD-02, PD-03, PD-04, PD-05, PD-06, PD-07, PD-08, PD-09, PD-10, PD-11, PD-12, PD-13, PD-14, PD-15, PD-16, PD-17 |
| PD-19 | PD-00, PD-01, PD-02, PD-03, PD-04, PD-05, PD-06, PD-07, PD-08, PD-09, PD-10, PD-11, PD-12, PD-13, PD-14, PD-15, PD-16, PD-17, PD-18 |
| PRE-00 | PD-19 |
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
| CN-02 | CN-CORE, ID-READY, LI-CORE |
| CN-03 | CN-CORE, ID-READY |
| CN-01 | CN-CORE, CN-03 |
| ID-01 | ID-READY, LI-01, LI-02, SE-CORE, SE-02, CN-CORE, CN-02 |
| INT-01 | ID-01, LI-01, LI-02, SE-01, SE-02, CN-01, CN-02, CN-03 |
| OPTIONAL-OK | Explicit per-task human priority/capacity decision |
| OPT-01 | ID-READY, SE-02, CN-03, OPTIONAL-OK |
| OPT-02 | ID-READY, LI-CORE, SE-CORE, SE-02, CN-03, OPTIONAL-OK |
| OPT-03 | LI-02, SE-CORE, DATA-READY, OPTIONAL-OK |
| EXP-01 | INT-01 |
| EXP-02 | EXP-01 |
| EXP-03 | EXP-02 |
| EXP-04 | EXP-03 |
| EXP-05 | EXP-04 |
| EXP-06 | EXP-05 |
| EXP-07 | EXP-06 |
| EXP-08 | EXP-07 |
| CLOSE-00 | INT-01, EXP-08 |

`docs/architecture/task-dependencies.dot` is the derived Graphviz view; update it with this index if dependencies change. Detailed task steps and observed evidence determine actual readiness.

## Startup and parallel-start registry

Existing target: exocrat/clip; existing WSL is reused. BOOT-00 creates the actual clone/docs seed/workstation facts under `docs/environment/wsl-and-first-session.md`; PD-02/13 extend verified tool/startup commands. The prompt explicitly reads both supplied checklists from the first session.

DL-00 plus reviewed contract/test-double readiness enables the isolated parts of ID-01, LI-01, LI-02, SE-01, SE-02, CN-01, CN-02 and CN-03. OPTIONAL-OK also remains necessary for a selected optional isolated start. Dashed graph edges show this early-start allowance; solid edges/registry above are real acceptance dependencies. No task completion row is removed by an isolated start.
