# Campus Marketplace — Document Index

Start with the [project overview](../README.md), then follow [AGENTS.md](../AGENTS.md)
and the [reusable task prompt](prompts/reusable-task-prompt.md). The
[task index](tasks/project-task-index.md) selects the work; the selected task
links to the detailed requirements and evidence it needs. Do not read every
document here for every task.

## Work order and current status

- [Project task index](tasks/project-task-index.md) — phases, ownership,
  dependencies and readiness gates.
- [Remaining-work plan](tasks/remaining-project-plan.md) — ordered NEXT-00–10
  work.
- Active task procedures: [domain](tasks/domain-task-list.md) and
  [final closeout](tasks/final-closeout-task-list.md). BOOT-00 and PRE-00 are
  complete; see the task index and work log for their accepted status.
- [NEXT-06 pre-cloud review package](evaluation/domain/next-06/pre-cloud-review.md) —
  local adapter implementation, PR description, peer-review focus and check status.
- [NEXT-06 dataset cloud handoff](evaluation/domain/next-06/cloud-handoff.md) —
  verified local inputs, external photo transfer, cloud adapter/integration gates
  and account335523638354-only restriction.
- [Work log](status/work-log.md) — current status rows, pending real-integration
  checks and concise project history. Older detailed entries remain in Git.
- [PD-19 foundation handoff](status/foundation-handoff.md) — short historical
  acceptance summary; active work is in the task plan and work log.

## Product, requirements and shared rules

- [Product reference and architecture decisions](product/product-reference-and-architecture-decisions.md)
- [Submitted PRD](source/ICC_Project_PRD_FINAL.pdf) and
  [submitted PRD provenance](source/README.md)
- [Shared conventions and cross-domain contracts](conventions/shared-conventions-and-cross-domain-contract-rules.md)
- [Decision-record process](decisions/README.md); task lists link the decisions
  that apply to their work.
- [FR/NFR ownership and evidence](architecture/foundation-traceability.md)
- [Repository structure](architecture/repository-structure.md),
  [frontend ownership and composition](architecture/frontend-collaboration.md),
  and [test-double/integration gates](architecture/stubs-and-integration-gates.md)
- [Terraform ownership](architecture/terraform-ownership.md) and the
  [Terraform workflow](../infra/terraform/README.md)
- [Database and migration record](../database/README.md),
  [backup/restore handoff](../database/backup-and-restore.md), and
  [synthetic-data tooling](../data/README.md)

## Evaluation and task handoffs

- [Evaluation evidence index](evaluation/README.md) — evidence homes and
  retention rules.
- [ECS-only versus ECS+Lambda experiment tasks](evaluation/ecs-only-vs-ecs-lambda-task-list.md)
  and [experiment-definition guidelines](evaluation/ecs-lambda-experiment-guidelines.md)
- [NFR measurement design](evaluation/nfr/measurement-design.md) and the
  [reference dataset recipe](../data/evaluation/reference-dataset-design.md)
- Active handoffs used by later integration work:
  [Identity](evaluation/identity/README.md),
  [CN-01 Conversations integration](evaluation/domain/conversations-integration.md),
  [CN-02 offers and contact sharing](evaluation/domain/conversations-offers.md),
  and the [Identity demo postmortem](evaluation/identity/id-01-step-12/demo-postmortem-20261026.md).
- NEXT-03 handoff artifacts: [change summary](tasks/next-03-change-summary.md),
  [implementation and verification report](tasks/next-03-visual-feedback-implementation-report.md),
  and the [next-agent PR/cloud-readiness prompt](prompts/next-03-pr-and-cloud-readiness-handoff.md).

## Setup and contributor process

- [Environment index](environment/README.md),
  [command registry](environment/commands.md),
  [secret-handling rules](environment/secret-handling.md), and
  [cloud inventory](environment/cloud-inventory.md). Refresh live cloud state
  before any cloud action.
- [WSL first-session guide](environment/wsl-and-first-session.md) applies only
  to contributors who use WSL.
- [Contribution and Git workflow](../CONTRIBUTING.md),
  [contributor start prompt](prompts/contributor-start-prompt.md),
  and [peer-review prompt](prompts/peer-review-prompt.md).
- [Agent checklist](checklists/agent-checklist.md) and
  [human checklist](checklists/human-checklist.md) — use the items relevant to
  the selected task and complete the task-wide review at closeout.
