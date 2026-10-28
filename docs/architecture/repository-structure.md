# Current Repository Map

The shared foundation reached PRE-00 acceptance. The
[foundation handoff](../status/foundation-handoff.md) records that result; the
[work log](../status/work-log.md) has task summaries. Original BOOT/PD procedures
are retained in Git history. Use the current task sources and subsystem guides
for remaining work.

## Main homes

| Path | What belongs here | Current source of detail |
|---|---|---|
| Root `README.md`, `AGENTS.md`, `CONTRIBUTING.md` | Project overview, agent entry, Git/review workflow | Start with README and AGENTS; follow the selected task |
| `docs/tasks/` | Active task order, requirements, dependencies and closeout | [Task index](../tasks/project-task-index.md) and [remaining-work plan](../tasks/remaining-project-plan.md) |
| `docs/product/`, `docs/source/` | Product decisions and submitted source documents | [Product reference](../product/product-reference-and-architecture-decisions.md); source provenance |
| `docs/architecture/`, `docs/decisions/`, `docs/conventions/` | Current code boundaries, design choices and shared rules | Read only the sources linked by the selected task |
| `docs/environment/` | Local setup, commands, secrets and last-known cloud state | [Environment index](../environment/README.md); refresh cloud state before action |
| `docs/evaluation/`, `data/evaluation/`, `scripts/evaluation/` | Experiment/NFR design, workload inputs, labels and tools | [Evaluation index](../evaluation/README.md); keep measured results in their assigned run folders |
| `docs/status/` | Current task checkpoints and accepted handoffs | [Work log](../status/work-log.md) |
| `apps/api/` | FastAPI application, domain implementations and API tests | API/domain READMEs and the domain task list |
| `apps/web/` | React/TypeScript application and browser tests | [Frontend ownership map](frontend-collaboration.md) and web README |
| `contracts/` | Editable public declarations and generated API/types | [Contract guide](../../contracts/README.md) |
| `database/` | PostgreSQL migrations, seed tools and isolated SQL checks | [Database guide](../../database/README.md) |
| `data/` | Synthetic-data generators, formats and validation | [Data guide](../../data/README.md) |
| `infra/terraform/` | Terraform state, shared test resources and reviewed domain resources | [Terraform ownership](terraform-ownership.md) and the relevant root README |
| `tests/`, `.github/workflows/` | Shared fixtures, evaluation tests and CI | Relevant test guide; root `make check` for the common local suite |
| `Makefile`, `scripts/` | Common local commands and project tools | [Command index](../environment/commands.md) and each tool's README |

Generated files belong to their documented generator; edit the source and
regenerate them. Keep test-only providers and fixtures inside their assigned
test boundaries. Do not add a second web lockfile or create a cloud resource
because a directory or example exists.

## Choosing what to read

Use the remaining-work plan for task order, the selected task source for exact
steps, the work log for current status, and current code/runbooks for observed
behavior. The task index records ownership and milestones. Frontend changes
follow the human-verified page map; cloud changes follow Terraform ownership
and their separate review gates. WSL setup applies only to contributors using
WSL.
