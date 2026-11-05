# Remaining project work

**Current status (2026-11-05):** Aditya directed completion of every non-EXP task
listed in the [pending task register](../status/pending_tasks.md). EXP-02–08 remain open. The current task rows and
verification limits are in the [work log](../status/work-log.md); the remaining
EXP rows are in [pending task register](../status/pending_tasks.md).

This page is a short navigation map, not a second task procedure. Follow the
[canonical experiment task list](../evaluation/ecs-only-vs-ecs-lambda-task-list.md)
for the exact order, owners, prerequisites, steps, acceptance checks and action
gates. Follow its linked manifests, measurement procedures and current evidence.
Do not use historical plans or receipts as current approval or cloud state.

## Open required sequence

| Task | Current obligation | Dependency / next gate |
|---|---|---|
| EXP-02 | Review the valid pilot and final inputs; freeze the comparison inputs; complete approved formal comparison and NFR runs. | Use the accepted EXP-01 design, DATA-READY release and exact approved run plan. Preserve failed/invalid results. |
| EXP-03 | Publish the prepared runtime and reusable tooling through the required PR, CI and approved merge. | Independent review, affected-owner review, passing checks and explicit merge authorization. |
| EXP-04 | Run deployed parity checks after EXP-03. | Accepted deployed revision and separately approved target/window. |
| EXP-05 | Review capacity results and align selected Lambda memory with Terraform and frozen inputs. | Human capacity decision; no unreviewed resource/configuration change. |
| EXP-06 | Run the approved Lambda initialization measurement. | EXP-05 decision, DATA-READY and exact run approval. |
| EXP-07 | Analyze valid results after EXP-06. | Freeze source/input bindings; retain uncertainty and invalid evidence. |
| EXP-08 | Reconcile cost/resources and publish the comparison report. | EXP-07 analysis; account for retained costs and cleanup before project closeout. |

This table summarizes the remaining-work inventory; it does not replace the
canonical tasks or imply that any measurement, deployment, merge or cleanup is
authorized. Cloud/hosting actions require their separate exact approval.

## Deferred work and closeout

Optional tasks remain unselected, including OPT-02. The notification centre is
foregone. Consider OPT-01 only if time permits and its prerequisites, approval,
budget and final buffer allow it. After EXP-02–08, follow the canonical
[CLOSE-00 checklist](final-closeout-task-list.md) for final regression, evidence,
cost/resource reconciliation and delivery status.

## Project sources

- [Project task index](project-task-index.md) — ownership and readiness.
- [Domain task list](domain-task-list.md) — accepted feature requirements and
  owner boundaries.
- [Experiment design and EXP-01–08 steps](../evaluation/ecs-only-vs-ecs-lambda-task-list.md).
- [Current checkpoints](../status/work-log.md) and [pending inventory](../status/pending_tasks.md).
