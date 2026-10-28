# Campus Marketplace — Human Verification Checklist

**Canonical path:** `docs/checklists/human-checklist.md`

**Version:** 1.1 (active-task cleanup)

**Updated:** 2026-10-28 (UTC)

**Sources:** [`AGENTS.md`](../../AGENTS.md), [`README.md`](../../README.md), [`docs/README.md`](../README.md), [source provenance](../source/README.md), the [PRD copy](../source/ICC_Project_PRD_FINAL.pdf), [product reference](../product/product-reference-and-architecture-decisions.md), the [reusable prompt](../prompts/reusable-task-prompt.md), [project task index](../tasks/project-task-index.md), [domain tasks](../tasks/domain-task-list.md), [Document 2](../evaluation/ecs-only-vs-ecs-lambda-task-list.md), [final closeout task list](../tasks/final-closeout-task-list.md), [foundation traceability](../architecture/foundation-traceability.md), [shared conventions](../conventions/shared-conventions-and-cross-domain-contract-rules.md), [command index](../environment/commands.md), [work log](../status/work-log.md), [`CONTRIBUTING.md`](../../CONTRIBUTING.md), the [peer-review prompt](../prompts/peer-review-prompt.md), [stub guide](../architecture/stubs-and-integration-gates.md), and [frontend collaboration map](../architecture/frontend-collaboration.md). Follow task-linked decisions, contracts and evidence for the selected work.

The agent runs routine commands and prepares evidence; you verify understandable results, answer genuine unresolved questions and approve specific actions. Peer-review roles follow `CONTRIBUTING.md`.

## Start or resume

- [ ] Give the reusable prompt and identify the task/member/scope. The foundation seed and PRE-00 are complete; use the current task index and remaining-work plan for active work.
- [ ] Verify the agent's read-only summary of the entire task and its numbered steps in order, plus actual checkpoint, executed versus human-verified state, dependencies, owner/reviewer, boundaries, expected outputs/checks, gates, and proposed first/resumed action.
- [ ] Verify the agent audited the task steps against the task purpose, prerequisites, outputs, acceptance checks, and canonical requirements; review any reported gap before authorizing implementation.
- [ ] Confirm current work-log state and available branch/PR evidence were checked; unavailable remote evidence is reported as unknown, not assumed.
- [ ] Correct misunderstandings; the agent must not write even status/branch changes before this verification. If a result was already executed but not verified, review its existing evidence rather than allowing it to be repeated blindly.
- [ ] Before each numbered step, review the agent's short explanation of its purpose, intended changes/outputs, checks, and gates. Say okay before the agent executes that step; verify the result afterward.
- [ ] Ask the agent to locate recorded project information itself. Supply only genuinely missing decisions/access inputs; never paste secret values/MFA/OTP/passwords in chat.

## After every numbered step

- [ ] For a visible UI increment, open the exact result supplied by the agent and try the prepared actions/states on desktop and phone layouts under the [browser procedure](../environment/browser-verification.md). Verify or request correction before advancing the named checkpoint. Check actual-phone camera/gallery and on-screen keyboard behavior where required; browser emulation and automated passes do not establish those device checks. Missing observations remain pending.

- [ ] Does the report identify the correct step and concrete changed paths/resources?
- [ ] Does it show expected versus observed outcome, exact checks/results, pass/fail/blocked explanation, evidence/revision and remaining questions?
- [ ] Does the status table accurately record each execution checkpoint and human-verification state? The dated history need not contain a separate entry for every step or routine “verified; proceed” message; it should preserve meaningful outcomes, decisions, checks, blockers, consequential human direction, and closeout evidence.
- [ ] Were task boundaries, internal decision gates, privacy and ownership respected? Failed/skipped checks must be explicit.
- [ ] Say verify/continue, correct, or pause. The agent waits after every step; silence gives no permission. It records verification before advancing. If correction method/scope is uncertain it asks first.
- [ ] For frontend changes, verify the contributor followed the approved page/ownership map, used public feature boundaries, coordinated shared-page edits with the current writer, and kept Wanted Request conversations private. Confirm temporary accounts can browse but cannot initiate a response.

You may inspect evidence, but the agent must summarize what makes it acceptable and what you are deciding. You should not need to find files, reconstruct test criteria or perform routine implementation/Git commands.

## Task-wide closeout

- [ ] At task/milestone handoff, check the complete change against the task's acceptance conditions, relevant checklist items, tests/checks, documentation/evidence, privacy/secret handling, and work-log status. The agent should present failures and blockers plainly; you need not reconstruct acceptance from separate files.

## Completed foundation

BOOT-00 and PD-00–PD-19/PRE-00 are complete. Review the accepted result and evidence limits in the [foundation handoff](../status/foundation-handoff.md) and current task-by-task [work log](../status/work-log.md); use the active task sources for remaining work.

## Decisions and separate approvals

- [ ] A question shows the exact uncertainty, affected action, relevant repo facts, useful options/recommendation and smallest decision needed. Durable answers are recorded canonically before consumers depend on them.
- [ ] For hosting/account/permission actions and cloud create/change/delete, deployment, paid provider/load test, external communication or destructive cleanup, review the concrete target/action before approval. A resource proposal records purpose, owner, Terraform state/module, inputs/outputs, permissions, data class, shared-resource reuse, cost/headroom/caps/stop limits, test window, evidence, rollback and cleanup/retention, as well as identity/account/region/environment and exact resource changes/exposure.
- [ ] Approve that exact plan/version only. Changed plans return for review. General understanding/step verification or a main merge is not separate action authorization.
- [ ] Human-only account/device steps have specific instructions and expected safe results; the agent verifies afterward through the approved access path.

## Peer review and merging

- [ ] Each contributor uses an isolated branch/clone/worktree. The BOOT-00 documentation seed and PD-00–PD-03 direct-to-main handoffs are complete; later changes use task/milestone PRs and the normal review gates.
- [ ] For PRs, a different designated human peer reviews, with AI assistance if useful; affected owners approve shared surfaces. Author verification does not replace peer approval.
- [ ] Use `docs/prompts/peer-review-prompt.md` as a thorough, scope-adapted review aid. Review findings yourself, verify the latest head/target, required checks and affected-owner approvals, and explicitly authorize the exact PR/revision before merge. AI review is not approval and the prompt grants no merge or deployment authority.
- [ ] Required local/CI checks, dependency milestones and conflict-resolution review pass before authorizing the concrete merge. The author agent cannot approve or autonomously merge its PR.
- [ ] Consumers use the recorded accepted main revision; cloud environment operations remain separately approved and serialized.

## Feature, NFR, and final gates

- [ ] Readiness milestones permit their named consumers but do not claim entire FR/NFR/task completion. A required blocker means incomplete work.
- [ ] For each domain task, confirm the agent checked changed contracts/code/tests against [`shared conventions`](../conventions/shared-conventions-and-cross-domain-contract-rules.md): UUID wire form, UTC-aware timestamps, integer-paise money, standard error envelope, trusted server caller context, stable bounded pagination, domain-owned authorization/transactions, retries/idempotency, and privacy-safe logging. The report should identify the concrete checks/evidence, not just say “conventions followed.”
- [ ] Confirm PD-09 evidence is deterministic synthetic generator/manifest tooling plus a labeled-query format/review procedure. Final schema-aware dataset, validation and human-reviewed labels at `data/evaluation/query-labels.json` belong to SE-01/DATA-READY; preview data is not final evidence. Confirm PD-10 shared fixtures are synthetic and minimal, with domain fixtures owned by their domain tasks.
- [ ] For applicable changes, verify the registered `uv run --locked python scripts/check_secrets.py` result and review the diff/logs for real personal data, secrets or private message content. Failed or skipped scans remain open checks.
- [ ] Confirm domain behavior stays within its assigned task/public contract. Cloud changes use the approved shared foundation and exact reviewed plan; shared resources are reused, and domain-specific duplicate resources require their own reviewed task and separate approval.
- [ ] At INT-01, verify cross-domain calls use reviewed public contracts and test authorized/denied callers, retry/duplicate/concurrency and partial-failure behavior, transaction/side-effect ownership, and privacy/logging along the named user journeys.
- [ ] Dataset/labels/fixtures/contracts/Black/local setup/CI/work-log/secret-reference/cloud-inventory outputs are evidenced in their assigned task. Final data validation follows domain schemas.
- [ ] Follow the named accurate procedure in the [domain task list](../tasks/domain-task-list.md): SE-01 owns NFR-01/02/04, CN-01 owns NFR-05, and INT-01 owns NFR-03/06/07; declare NFR-08 caps before cloud work, track spend/reserve at INT-01, and complete final NFR-08 reconciliation in the [CLOSE-00 task list](../tasks/final-closeout-task-list.md). The [Document 2 comparison](../evaluation/ecs-only-vs-ecs-lambda-task-list.md) retains only its comparison and the explicitly narrow exception; this checklist is not an NFR procedure. Review manifests, tooling, deployment and caps before any run. Later material changes trigger affected revalidation. Offline NFR-04 is valid offline; local smoke checks cannot prove cloud latency/recovery.
- [ ] Document 2 owns the primary ECS/Lambda implementation/comparison; CLOSE-00 owns final whole-project budget reconciliation and report/demo/submission package.
- [ ] OPT-01 requires ID-READY/SE-02/CN-03; OPT-02 requires ID-READY/LI-CORE/SE-CORE/SE-02/CN-03; OPT-03 requires LI-02/SE-CORE/DATA-READY. Each also needs your explicit selection and OPTIONAL-OK schedule/cost protection. The recorded planning change explains its earlier scheduling relative to PRD §8; the final buffer remains protected.
- [ ] Task/phase/project closure includes actual checks, human verification, reviewed revisions/evidence, approved cleanup/retention and required delivery state. Do not accept a blocker/deferred required requirement as successful completion.

**Loop:** agent explains the whole task → you verify → before each numbered step, agent explains that step → you say okay → agent executes only that step and reports evidence → you verify → repeat. A new task needs a new understanding verification.

## Environment and integration boundaries

- [ ] Confirm the agent checked the actual repository and contributor environment. The WSL guide applies only when the contributor uses WSL.
- [ ] Before accepting isolated evidence, verify that the selected task step permits the stub and that its contract is reviewed. Keep the corresponding real integration and acceptance checks open until they pass.
- [ ] Confirm test doubles are rejected in production and do not create fake success. Cloud, hosting and paid actions still need their separate exact-scope approvals.
