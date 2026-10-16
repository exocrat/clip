# Campus Marketplace — Minimal Repository Structure

**Version:** 3.1
**Date:** 2026-10-14  
**Canonical repository path:** `docs/architecture/repository-structure.md`
**Document 4. Status:** Proposed repository layout and file responsibilities. Use it with the product reference, shared conventions, submitted PRD, and the pre-domain task list. This document defines where project information and code live; it does not make unresolved implementation or infrastructure choices on the team's behalf.

## 1. Purpose and boundary

Create the smallest repository that lets a new contributor or AI agent understand project status, run the foundation locally, validate changes, and proceed through the pre-domain tasks without relying on chat history or a human to locate missing instructions.

This layout covers the pre-domain foundation and leaves domain feature implementation to the later single domain task list. The pre-domain task list records stream path ownership and the exact directory roots. PD-03 places a tracked `.gitkeep` file in each exclusive root so the directories are present in stream owners' clones. After the PD-00–PD-03 handoff is merged, each owner removes only their own marker files as the first action in their worktree, then populates those paths. Markers do not authorize edits outside the owner's assigned roots or task files. Domain directories may be created as empty ownership placeholders, but must not contain speculative feature code or invented APIs. Optional/stretch features remain out of the foundation.

The repository is the execution source of truth. Keep the submitted PRD as the source of requirement intent. Store the current product/architecture reference, shared conventions, task lists, checklists, task prompt, work log, decisions, and actual environment records in the repository so an agent can read them from the supplied reusable prompt.

## 2. Proposed top-level layout

```text
campus-marketplace/
├── README.md
├── AGENTS.md
├── CONTRIBUTING.md
├── .gitignore
├── .editorconfig
├── .env.example
├── pyproject.toml
├── package.json
├── package-lock.json                 # or the one chosen Node lockfile; never multiple
├── docker-compose.yml
├── Makefile                          # one discoverable front door for common commands
├── .github/
│   └── workflows/
│       └── ci.yml
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   └── domains/
│   │   │       ├── identity/
│   │   │       ├── listings/
│   │   │       ├── search/
│   │   │       └── conversations/
│   │   └── tests/
│   └── web/
│       ├── src/
│       └── tests/
├── contracts/
│   ├── README.md
│   └── generated/                    # generated outputs only; source is defined by contract task
├── database/
│   ├── migrations/
│   └── seed/
├── infra/
│   └── terraform/
├── scripts/
│   ├── setup.*
│   ├── start.*
│   ├── stop.*
│   ├── migrate.*
│   ├── seed.*
│   ├── test.*
│   ├── check.*
│   ├── deploy.*
│   ├── verify.*
│   └── teardown.*
├── tests/
│   ├── integration/
│   └── fixtures/
├── data/
│   ├── generators/
│   ├── evaluation/
│   └── README.md
├── docs/
│   ├── README.md
│   ├── product/
│   ├── architecture/
│   ├── conventions/
│   ├── tasks/
│   ├── checklists/
│   ├── prompts/
│   ├── status/
│   ├── decisions/
│   ├── environment/
│   └── evaluation/
```

The tree is a target, not a request to create empty files for every possible future feature. During implementation, keep only paths with a named owner and task. The canonical `.github/` directory is the one shown above.

### Layout adjustment before implementation

The root `pyproject.toml` is the canonical Python tool configuration, including Black. The exact Python dependency/package manager and Node package manager are not yet locked here. The pre-domain task must inspect the chosen build/deployment approach, choose one clear dependency/package boundary and one Node lockfile, document the choices in `docs/decisions/`, and keep the tree consistent. Do not create duplicate tool configurations or lockfiles.

## 3. Canonical files and what they must contain

| Path | Responsibility |
|---|---|
| `README.md` | Public-facing project overview: purpose, current implementation status, scope, and links to contributor/setup guidance and canonical project documentation. Keep detailed agent procedures out of it. |
| `AGENTS.md` | Repo-wide agent operating rules and required reading order. It points to the current reusable prompt, task index, checklists, work log, and uncertainty rule. It is not a substitute for those documents. |
| `CONTRIBUTING.md` | Branch/PR and review expectations, code ownership, local validation before review, and how shared contracts or conventions change. |
| `.env.example` | Non-secret variable names and safe dummy values only. Never place real credentials or secret values in the repo. |
| `pyproject.toml` | Canonical Python tool configuration, including Black line length/target and the selected pinned Black dev dependency in the appropriate dependency manifest. Avoid a second conflicting Black configuration. |
| `package.json` plus one lockfile | Web scripts and exact Node dependency resolution. Select npm or another package manager once; commit only its matching lockfile. |
| `docker-compose.yml` | Minimal local dependencies needed for foundation work, such as PostgreSQL. It must not silently provision cloud resources. |
| `Makefile` | Short, stable front door for documented setup, start/stop, migrations, synthetic seed, tests, formatting, and checks. Each target calls a maintained script or package command rather than duplicating logic. |
| `.github/workflows/ci.yml` | Reproducible local-equivalent CI gates: Python formatting check, Python tests, web lint/type/test/build checks, contract generation consistency where configured, and relevant integration checks. CI must not apply Terraform or create billable cloud infrastructure. |
| `contracts/README.md` | Identifies the authoritative editable contract source, generator, generated destinations, and exact regeneration/check commands once selected by the contract task. Generated outputs are not edited by hand. |
| `database/migrations/` | Versioned schema changes and documented migration command. Do not maintain a second unversioned schema definition as a competing source of truth. |
| `database/seed/` | Deterministic local seed entry point for small development data. Evaluation-scale synthetic data belongs in `data/generators/`. |
| `infra/terraform/` | Terraform source and non-secret examples for the shared environment and later domain-owned resources. State access/locking, resource ownership, plan/apply gates, outputs, and teardown must be documented before cloud use. |
| `scripts/` | Portable, discoverable wrappers for setup, local lifecycle, migration, seed, test/check, and cloud deploy/verify/teardown. Scripts must validate required inputs and never guess an AWS account, profile, region, or target. |
| `data/generators/` | Named, deterministic synthetic-data generation source, with seed/count options and a dataset fingerprint. Never store real user or contact data. |
| `data/evaluation/` | Fixed labeled search-query/listing data and workload definitions needed by NFR and ECS comparison tasks. Store generator/source data and safe metadata; avoid committing large generated datasets unless the task establishes that as necessary. |
| `tests/fixtures/` | Reusable, clearly synthetic fixtures, including controlled identity-provider fakes for local/test mode. Production configuration must reject unsafe fake providers. |
| `docs/status/work-log.md` | Shared project work log and current status, described in Section 5. |
| `docs/decisions/` | Durable record of approved shared implementation decisions, with date, scope, rationale, affected paths, and superseded decisions. Do not use it for secrets or transient chat. |
| `docs/environment/` | Current non-secret account/access, budget-alert, environment/resource inventory, and operation records based on verified facts and actual cloud outputs. Secret values stay in the approved secret manager. |

## 4. Project documentation copied into the repository

Place the reviewed source documents in these canonical locations and link to them from `docs/README.md`:

| Repository path | Document |
|---|---|
| `docs/product/product-reference-and-architecture-decisions.md` | Document 1: required MVP, optional/stretch scope, functional/NFR references, architecture baseline, and information classification. |
| `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | Document 2: only the ECS-only versus ECS+Lambda comparison, including its experiment-specific tasks. |
| `docs/conventions/shared-conventions-and-cross-domain-contract-rules.md` | Shared conventions, contracts, cross-domain boundaries, and privacy/logging rules. |
| `docs/architecture/repository-structure.md` | This repository-structure document. |
| `docs/tasks/pre-domain-task-list.md` | Ordered foundation tasks, including every implicit artifact/setup step required before domain work. |
| `docs/tasks/domain-task-list.md` | One authoritative task list for Identity, Listings, Search/Wanted/Saved, Conversations, and cross-domain integration. Include NFR procedures at the first point the complete relevant behavior can be tested accurately. Do not create separate domain task-list files or a duplicate combined copy. |
| `docs/checklists/agent-checklist.md` | Regenerated agent checklist for execution, review, and evidence. |
| `docs/checklists/human-checklist.md` | Regenerated human review/approval checklist. |
| `docs/prompts/reusable-task-prompt.md` | Reusable prompt that tells the agent to inspect current repo status and canonical docs, report its understanding and wait for human verification, execute one task-list step at a time, report evidence and wait for verification after each step, update the work log, and stop to ask about uncertainties or approval gates. |

The repository copies are the execution-time references. Use the reviewed repository copies and `docs/source/README.md` as the runtime provenance record. Changes follow the documented review workflow, including the one-time BOOT-00 direct-to-main documentation-seed exception, which does not require separate peer review; runtime execution never requires an external copy. When a shared rule is required during execution, the relevant checklist must state the check and point to the canonical repo file; do not make an agent search a conversation or infer a missing requirement.

## 5. Shared work log and status

Create `docs/status/work-log.md` during the pre-domain foundation. This is a required, shared repository artifact, not an optional suggestion.

Keep the log concise enough to scan and resume work. It must contain:

1. A compact current-status table with task ID/name, status (`not started`, `in progress`, `blocked`, `done`), owner, branch/PR or commit reference when available, last update in UTC, and next action/blocker.
2. An append-only dated work-entry section. Each short entry records task/step, contributor, execution and human-verification state, changed files, exact checks and results, revision/evidence when available, blocker/decision and next action. Do not repeat background or paste long command output; link existing evidence where useful.
3. A link to the decision record, environment inventory, task list, and evidence directory where applicable.
4. Clear instructions to read the status table before starting and update it after meaningful progress, before stopping, and after a task is completed or blocked. A task/milestone closeout checks the full acceptance set and relevant checklist items.

For parallel work, each agent updates only its assigned task row and adds a distinct timestamped entry. Rebase/merge and resolve log conflicts without deleting another task's entry. A status claim must match the repository and CI evidence. Do not mark a task done merely because code was written.

## 6. Python Black and shared quality gates

Black setup is part of the foundation and must be completed before domain implementation:

1. Configure Black once in the canonical `pyproject.toml`, including the agreed line length, Python target version, and include/exclude paths.
2. Pin Black in the development dependency set and commit the applicable lockfile. Do not rely on an unpinned globally installed formatter.
3. Provide one discoverable format command and one non-mutating check command through the documented project entry point, for example `make format-python` and `make check-python-format`.
4. Run the same check in CI and fail the build when tracked Python files are not Black-formatted.
5. Document the exact commands in `CONTRIBUTING.md` and the agent checklist. Regenerate the checklists when these commands or gates change.

The exact Black version, line length, target Python version, and package manager should be resolved by inspecting the actual repo/toolchain during the foundation task. Record the selected values once; do not invent conflicting copies in another config file.

## 7. Foundation runnable surface

Before domain tasks begin, the repo must provide one documented path to:

- install pinned Python and web dependencies;
- start and stop local services;
- run database migrations and deterministic small local seed data;
- prepare deterministic generator tooling; after domain schemas/configuration exist, generate/load the required reference dataset (at least 1,000 listings and 5,000 users) and record its seed/counts/fingerprint;
- run unit, integration, and contract checks that exist at that stage;
- format/check Python with Black and run the other selected language quality checks;
- run the complete local CI-equivalent check;
- generate/check public API artifacts from their authoritative source;
- inspect Terraform plan, deploy and verify only through explicit, documented, human-reviewed steps, and tear down resources safely.

Every required script, dataset, fixture, generated artifact, checklist, and evidence location is a named task with an owner, prerequisites, commands, and a verifiable completion condition in the pre-domain checklist. “The setup implies it” is not an acceptable completion criterion.

## 8. Minimal contents before domain work

The pre-domain milestone creates only what later domain work needs to operate consistently:

- repository and agent entry-point docs;
- current product, architecture, and shared convention docs;
- task index, pre-domain checklist, regenerated agent/human checklists, and reusable prompt when authored;
- the shared work log, decision log, and non-secret environment/resource inventory;
- a runnable frontend/API skeleton and shared core boundaries;
- selected public contract source, generator, and generated output path;
- foundation migrations, local compose setup, schema-independent generator tooling, and core/test-provider fixtures; domain data loading/validation follows the approved domain schemas;
- pinned dependencies, Python Black config and checks, other selected tool checks, and CI;
- AWS account/access readiness, budget alerts, Terraform state/ownership, and safe operation/cleanup documentation;
- one human-approved shared cloud test foundation for domain integration testing, provisioned through Terraform after its exact plan, cost, security, and cleanup/retention are reviewed;
- explicit handoff rules requiring the single domain task list to identify any additional domain-owned resources, reuse the shared environment, and include approval, verification, cost, and cleanup steps for each feature.

Domain directories and domain-specific infrastructure modules remain ownership placeholders until the appropriate task list begins. Do not create unapproved feature behavior, optional features, duplicate docs, or unused infrastructure modules just to fill the tree. Account access and cloud provisioning are pre-domain tasks, but every apply still requires human approval of the exact target and plan.

## 9. Checklist regeneration and drift control

When this structure is accepted and the pre-domain list is prepared:

- Regenerate both `agent-checklist.md` and `human-checklist.md` from the full current requirements, not from an earlier checklist alone.
- Put the shared-work-log read/update steps, Black local/CI checks, repository-doc synchronization, and explicit synthetic-data/fixture/generator tasks in the relevant checklist items.
- Include checklist tasks in the pre-domain task list itself, with dependencies and completion criteria.
- Add a final traceability pass from every user requirement and PRD foundation item to a repository path and a named task/check.
- If a required reference, command, decision, secret-access instruction, or target is missing or ambiguous at execution time, stop and ask the user before taking the dependent action. Do not silently guess or require a human to cross-reference chat.

## 10. Open decisions this document deliberately leaves to tasks

The relevant foundation task must inspect the repository and resolve each item before dependent work begins:

- Python dependency/package manager and where runtime dependencies are declared; the root `pyproject.toml` remains the single Black/tool configuration;
- Node package manager and its single lockfile;
- exact Python and Node versions and pinned tool/dependency set;
- public contract source format and generation commands;
- exact local service, migration, seed, and test commands;
- Terraform module/resource ownership, state, review/apply gates, and environment naming;
- status/evidence retention and any repository size limits for generated datasets.

For choices that change security, privacy, data, public contracts, cost, or cloud resources, the task must present feasible options and tradeoffs and get the required human decision before implementation. Routine reversible details within the approved boundary may be selected by the agent and recorded. Never store secrets in repository docs, source, fixtures, logs, or generated data.

## 11. Bootstrap and runtime document homes

The first request may supply this structure and the complete document bundle and ask the agent to make the repository. Execute BOOT-00 from `docs/tasks/bootstrap-task-list.md` with the same understanding and step-verification loop. Bootstrap installs approved documentation and minimal entry points, initializes/preserves Git, records source provenance, and connects an explicitly selected remote. Pre-domain tasks then extend the repository; do not treat bootstrap as completion of those tasks.

Additional required document homes:

| Path | Responsibility / creating task |
|---|---|
| `docs/tasks/bootstrap-task-list.md` | BOOT-00 initial documentation/Git bootstrap. Supplied in the document bundle. |
| `docs/tasks/project-task-index.md` | Phase selection, all task IDs, readiness milestones, owner/reviewer assignment, expected artifact and command creation responsibilities. Installed in BOOT-00, maintained by each relevant task. |
| `docs/tasks/final-closeout-task-list.md` | CLOSE-00 regression, complete-project cost/resource review, report/demo/viva/submission package. Installed in BOOT-00. |
| `docs/status/work-log.md` | Task state plus current step, within-step checkpoint, pending human verification/decision, actual branch/revision/evidence, next action; initialized from the supplied template in BOOT-00 and extended in PD-03. |
| `docs/environment/commands.md` | Actual command spellings/arguments, creator task, effects, target, success/failure behavior, and prerequisite milestone. Initialized in PD-03; populated by command-creating tasks. |
| `docs/environment/secret-handling.md` | Non-secret reference/access/owner/rotation instructions; PD-03 template, PD-14 shared access, domain provider updates. |
| `docs/evaluation/README.md` | Evidence locations and manifest requirements; supplied documentation, populated with real artifacts by each evaluation task. |
| `docs/decisions/optional-work-scheduling.md` | Accepted team scheduling change relative to submitted PRD §8; installed in BOOT-00. |
| `docs/architecture/task-dependencies.dot` | Graphviz task/milestone dependencies maintained with the task index. |
| `CONTRIBUTING.md` | Canonical branch, PR, peer review, merge, integration, and shared-file coordination workflow; supplied initially and configured in PD-03/PD-12. |

PRE-00 is the named milestone for the foundation completion gate in the pre-domain list and the verified PD-19 handoff; it is not an extra implementation task.

After bootstrap, each contributor uses a separate clone or worktree and task branch. Exact paths and tools that depend on runtime choices are frozen by their named foundation task and recorded in the command/ownership registry before consumers run them. Expected uncreated outputs are not missing-input errors. All linked source documents are already installed by BOOT-00; routine execution must not ask a human to find documents.

## v3 setup and stub execution homes

- `docs/environment/wsl-and-first-session.md`: existing WSL/agent access, source staging versus working clone, exact exocrat/clip clone/folder/startup flow; supplied at bootstrap.
- `docs/environment/development-workstation.md`: actual non-secret machine/agent/tool/container/root evidence created by BOOT-00 and extended PD-02/13.
- `docs/architecture/stubs-and-integration-gates.md`: canonical task/checkpoint allowance table, safe test-double rules, real gates and handoff procedure; supplied at bootstrap and reconciled DL-00/PD-17.
- Domain test adapters/scenarios use the existing owned test/fixture locations; no second production implementation or duplicated domain task list.

The existing remote is exocrat/clip. Clone/preserve it and install bundle contents at its root. The repository prompt/checklists are already supplied. README points to first-session setup; later application commands are implemented by their named PD tasks.
