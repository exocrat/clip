# Campus Marketplace — Document Index


The root [README](../README.md) describes the project. Agents start from [AGENTS.md](../AGENTS.md) and follow the canonical task and review instructions below. Use the project task index to select/resume work; this index locates canonical sources. Detailed Git/review workflow is [CONTRIBUTING.md](../CONTRIBUTING.md).

- [Document 1 — Product/reference and decisions](product/product-reference-and-architecture-decisions.md)
- [Document 2 — Primary experiment task list](evaluation/ecs-only-vs-ecs-lambda-task-list.md)
- [Document 3 — Shared conventions](conventions/shared-conventions-and-cross-domain-contract-rules.md)
- [Document 4 — Repository structure](architecture/repository-structure.md)
- [Terraform ownership and state boundaries](architecture/terraform-ownership.md)
- [Terraform change workflow](../infra/terraform/README.md)
- [Foundation requirement traceability](architecture/foundation-traceability.md)
- [MVP database schema proposal and review gates](architecture/mvp-database-schema.md)
- [Database migration files, ownership and verification state](../database/README.md)
- [Future database backup/restore handoff and approval gates](../database/backup-and-restore.md)
- [PD-08 unfinished-work transfer to pre-domain integration](decisions/database-integration-handoff.md)
- [Synthetic-data preview tooling and final dataset prerequisites](../data/README.md)
- [Document 5 — Pre-domain task list](tasks/pre-domain-task-list.md)
- [Single domain task list](tasks/domain-task-list.md)
- [Frontend page inventory and collaboration map](architecture/frontend-collaboration.md)
- [Human browser, mobile layout and camera verification](environment/browser-verification.md)
- [Responsive UI and camera verification decision](decisions/responsive-ui-and-camera-verification.md)
- [Initial repository bootstrap](tasks/bootstrap-task-list.md)
- [Project phase/milestone/owner index](tasks/project-task-index.md)
- [Final regression/cost/delivery tasks](tasks/final-closeout-task-list.md)
- [Reusable execution prompt](prompts/reusable-task-prompt.md)
- [Pre-domain contributor prompt and stream workflow](prompts/pre-domain-contributor-prompt.md)
- [Contributor start prompt](prompts/contributor-start-prompt.md)
- [Peer review prompt](prompts/peer-review-prompt.md)
- [Agent execution checklist](checklists/agent-checklist.md)
- [Human verification checklist](checklists/human-checklist.md)
- [Status/checkpoint template](status/work-log.md)
- [Pre-domain foundation handoff (PD-19)](status/foundation-handoff.md)
- [Command registry](environment/commands.md)
- [Secret-reference/access template](environment/secret-handling.md)
- [PD-16 shared test foundation proposal](environment/shared-test-foundation-proposal.md)
- [PD-16 evidence and native AMD64 handoff](evaluation/foundation/pd-16/README.md)
- [PD-16 operational closeout and carried integration gates](evaluation/foundation/pd-16/closeout-review.md)
- [PD-16 approximate recent-run cost acceptance](decisions/foundation-cost-review-precision.md)
- [PD-16 RDS stop/resume operation plan](environment/shared-test-rds-operations.md)
- [PD-16 image handoff/publication preparation](environment/pd16-image-publication.md)
- [PD-16 service-plan preparation](environment/pd16-service-plan-preparation.md)
- [PD-16 broad human-operator exception](decisions/broad-human-operator-access.md)
- [PD-16 private PostgreSQL probe-login decision](decisions/private-postgresql-probe-login.md)
- [Database-task deadlines and manual image cleanup](decisions/database-task-deadlines-and-manual-image-cleanup.md)
- [Development workstation record](environment/development-workstation.md)
- [Evidence/measurement manifest index](evaluation/README.md)
- [Accepted optional-scheduling change](decisions/optional-work-scheduling.md)
- [Wanted-request discovery and response decision](decisions/wanted-request-discovery-and-response.md)
- [Frontend ownership and page-composition decision](decisions/frontend-ownership-and-composition.md)
- [Web route scaffold decision](decisions/web-routing.md)
- [Derived Graphviz dependencies](architecture/task-dependencies.dot)
- [Unchanged submitted PRD](source/ICC_Project_PRD_FINAL.pdf)
- [Source/version/checksum record](source/README.md)
- [Revision consistency check](source/revision-check.md)

Code, scripts, manifests, generated contracts, migrations, actual provider/environment configuration and run evidence not present yet are outputs of the named tasks. Expected uncreated outputs are not missing source inputs.

## Development setup and early parallel work

- [Existing WSL, Codex, cloning, folders and first session](environment/wsl-and-first-session.md)
- [Stub-enabled checkpoints and non-substitutable integration gates](architecture/stubs-and-integration-gates.md)

Both checklists are present in this bundle and apply from BOOT-00. Workstation facts are produced at `docs/environment/development-workstation.md` during BOOT-00/PD-02; do not fabricate them in planning.

- [Identity provider setup and pending real checks](environment/identity-provider-setup.md)
- [Identity provider setup decision](decisions/identity-provider-setup.md)

- [Shared test ECS image pin](decisions/shared-test-ecs-image-pin.md)
