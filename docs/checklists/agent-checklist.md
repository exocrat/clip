# Campus Marketplace — Agent Execution Checklist

**Canonical path:** `docs/checklists/agent-checklist.md`

**Version:** 1.1 (active-task cleanup)

**Updated:** 2026-10-28 (UTC)

**Sources:** [`AGENTS.md`](../../AGENTS.md), [`README.md`](../../README.md), [`docs/README.md`](../README.md), [source provenance](../source/README.md), the [PRD copy](../source/ICC_Project_PRD_FINAL.pdf), [product reference](../product/product-reference-and-architecture-decisions.md), [Document 2](../evaluation/ecs-only-vs-ecs-lambda-task-list.md), [shared conventions](../conventions/shared-conventions-and-cross-domain-contract-rules.md), [repository structure](../architecture/repository-structure.md), [project task index](../tasks/project-task-index.md), [domain tasks](../tasks/domain-task-list.md), [foundation traceability](../architecture/foundation-traceability.md), [command index](../environment/commands.md), [work log](../status/work-log.md), [`CONTRIBUTING.md`](../../CONTRIBUTING.md), the [reusable prompt](../prompts/reusable-task-prompt.md), the [stub guide](../architecture/stubs-and-integration-gates.md), and the [frontend collaboration map](../architecture/frontend-collaboration.md). Read task-linked decisions, contracts and evidence as applicable.

This checklist is an execution aid; canonical sources retain detailed requirements. Prior-source provenance belongs in `docs/source/README.md`, not recurring runtime questions.

## Before any write

- [ ] Inspect the workspace/bundle or repository read-only; preserve changes and reconcile branch/main/remote active PRs/task checkpoints with real evidence.
- [ ] Read the task index, current remaining-work plan and roster; choose only the requested/assigned task and its next unexecuted checkpoint. BOOT-00/PRE-00 are complete; use the foundation handoff and work log for their accepted status rather than restarting them.
- [ ] Read the current work-log row/history and the task's linked canonical sources before selecting an action; check available branches/PRs and distinguish verified remote state from unavailable evidence.
- [ ] Distinguish expected outputs from missing prerequisites. Search the repo/bundle yourself; ask about every unresolved uncertainty/conflict. No log/branch/file mutation yet.
- [ ] Audit the selected task's ordered steps against its purpose, prerequisites, outputs, acceptance checks, and canonical requirements. Report gaps or confirm none; do not silently work around a material omission or contradiction.
- [ ] Summarize the entire selected task and its numbered steps in order, including the audit result, prerequisites, expected outputs/checks, gates, completed versus pending/verified state, owner/reviewer, and the first step to execute. Wait for human verification.

## Each verified numbered step

- [ ] Before executing each numbered step, explain its purpose, intended changes/outputs, applicable checks, and any internal decision or separate-approval gate. Wait for the human's explicit okay; task-level verification alone does not authorize the next step.
- [ ] Use the isolated task branch/worktree and scoped claim under CONTRIBUTING.md. Resume partial steps without repeating side effects; executed-but-unverified steps wait for verification.
- [ ] Execute that step only; stop at internal decisions/separate action approvals. Do not silently reorder/batch or work elsewhere while waiting without explicit instruction. Only the documented human-verified stub checkpoint route permits staged integration obligations.
- [ ] Use common commands from the [command index](../environment/commands.md) and exact specialized commands from the selected tool/feature guide, `CONTRIBUTING.md`, and task instructions. Confirm actual state and effects; examples are not proof a tool is ready. Document commands explicitly assigned to this step and index shared front-door commands; missing required prerequisites block dependent work.
- [ ] Check each task's concrete data/API behavior against [`shared conventions`](../conventions/shared-conventions-and-cross-domain-contract-rules.md): UUID wire format, UTC-aware instants, integer-paise money, shared error envelope, server-built trusted caller context, bounded/stable pagination, owning-domain authorization/transactions, retry/idempotency behavior, and privacy-safe logs. Record the relevant tests/evidence; preserve public-domain ownership, review shared changes, and regenerate derived files.
- [ ] Run applicable step checks with exact command/results. Use pinned Black for Python and relevant local/CI gates at milestone completion. Preserve failures; report skipped/inconclusive checks honestly.
- [ ] Use synthetic safe fixtures/evaluation data; run the registered `uv run --locked python scripts/check_secrets.py` where applicable and inspect changes/logs/outputs for real data/private conversation content. PD-10 owns shared fixtures under `tests/fixtures/core/`; domain fixtures follow their owners' contracts. PD-09 supplies deterministic schema-independent generation and the label format/review procedure; final schema-aware data and human-reviewed labels at `data/evaluation/query-labels.json` belong to SE-01/DATA-READY, not preview runs. Production rejects unsafe fakes.
- [ ] Keep domain features inside their assigned task and reviewed public contracts. Cloud work must use the approved shared foundation and exact approved plan; inspect/reuse shared resources and do not provision duplicate or domain-specific resources without that domain's reviewed task and separate approval.
- [ ] Update the work-log status row after each step and verification, including current checkpoint (with the immediate next action for active work), execution/verification state, branch/revision/PR, evidence, questions, and blockers. Add dated history only for meaningful outcomes, decisions, checks, blockers, consequential human direction, or closeout; related steps may share an entry, and routine “verified; proceed” updates need no separate entry. Use exact UTC times for new entries and preserve existing timestamp precision. Preserve others' useful history.
- [ ] Report expected versus observed result, changed paths, commands/results, evidence and the precise verification decision. Stop until the human verifies; silence is not approval.

## Task-wide closeout

- [ ] At each named UI checkpoint in the [domain task list](../tasks/domain-task-list.md#human-browser-checks-for-every-frontend-task), follow the [browser procedure](../environment/browser-verification.md): start services, give URL/actions/expected states, and wait for the human's desktop/phone observations and explicit verification. Repeat after meaningful visible increments; record browser/viewport/device, isolated versus real mode, and pending checks. LI-02 Step 12 requires a human check of the deployed website and listing image flow on a supported phone, plus desktop file upload; no separate physical-phone camera/gallery acceptance check is required.

- [ ] At task or milestone handoff, inspect the whole change against its acceptance conditions: changed files, task-specific tests/checks, generated outputs, documentation, evidence, privacy/secret handling, and current work-log status. Resolve or clearly record each failure/blocker.
- [ ] Apply relevant checklist items during execution; perform the consolidated checklist review at task/milestone closeout rather than repeating unrelated items at each step. Keep action-specific safety and approval gates at the point of action.
- [ ] Explain each new function or meaningful code unit in a docstring, comment, or nearby documentation, including purpose and relevant inputs/outputs, side effects, security assumptions, and limits.

## Active task coverage

- [ ] Follow the [remaining-work plan](../tasks/remaining-project-plan.md) for task order and the selected task source for its exact requirements, owners, dependencies and checks.
- [ ] For frontend work, follow the approved page/ownership map and public feature entry points; reserve shared page/composition edits with one named current writer; do not import another feature's private implementation. Keep request-based conversations private and enforce temporary-account response limits through server authorization.

## Cloud, NFR, and optional gates

- [ ] Inspect/reuse shared resources and record evidence before claiming no additional Terraform resources. For a proposed resource, document purpose/owner/state/module/inputs/outputs/permissions/data class/cost cap/test window/evidence/reuse/rollback/cleanup; approve the exact target and plan before a gated operation, renew approval if changed, and verify deployed revision/resources. CI/main merge does not authorize deployment/apply.
- [ ] Create/approve measurement manifests and validate local tools/readiness before accurate NFR runs. Preserve raw/invalid results. Reverify affected evidence after later changes.
- [ ] Before any NFR run, follow the named accurate procedure in the [domain task list](../tasks/domain-task-list.md): SE-01 owns NFR-01/02/04, CN-01 owns NFR-05, and INT-01 owns NFR-03/06/07; declare NFR-08 caps before cloud work, track spend/reserve at INT-01, and complete final NFR-08 reconciliation in the [CLOSE-00 task list](../tasks/final-closeout-task-list.md). The [Document 2 comparison](../evaluation/ecs-only-vs-ecs-lambda-task-list.md) retains only its comparison and the explicitly narrow exception; this checklist is not an NFR procedure.
- [ ] Optional tasks need their feature-specific prerequisites, explicit selection and OPTIONAL-OK. Required work/NFR/experiment/budget/final buffer stays protected; follow the accepted scheduling decision, with no blanket INT-01 or elapsed-buffer prerequisite.

## PR and completion

- [ ] Use an isolated task branch and the normal PR/review process for remaining work. The BOOT-00 documentation seed and PD-00–PD-03 direct-to-main handoffs are complete. Do not approve or merge your own PR autonomously.
- [ ] When preparing a PR, point the human to `docs/prompts/peer-review-prompt.md` and remind them to arrange an independent peer review. Treat AI findings as review assistance only; wait for human peer/affected-owner approval and explicit authorization of the exact PR revision before merge.
- [ ] Record human step verification and accepted milestone/PR/main revision before unblocking consumers. Required blockers remain incomplete.
- [ ] Close only the requested scope; continued work is selected through the task index with a new understanding verification. Do not skip the experiment or final closeout.

## Environment and integration boundaries

- [ ] Verify the contributor's actual environment and repository. Use the WSL guide only when the contributor uses WSL; follow the current tool/setup guide for other environments.
- [ ] Use a test double only when the selected task step permits it and only against a reviewed contract. Record the real dependency, original step ID and check still required; do not count a double as real integration or NFR evidence.
- [ ] When an upstream implementation becomes available, resume its earliest pending integration check. Production configuration must reject test fakes; retain separate approvals for cloud and paid actions.
