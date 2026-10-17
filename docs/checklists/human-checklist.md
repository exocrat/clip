# Campus Marketplace — Human Verification Checklist

**Canonical path:** `docs/checklists/human-checklist.md`

Use the reusable prompt and current canonical files indexed by `docs/README.md`. The agent finds/reads project information, runs routine commands and prepares evidence. You verify understandable results, answer genuine unresolved questions and approve specific actions. Peer-review roles follow `CONTRIBUTING.md`.

## Start or resume

- [ ] Give the reusable prompt, optionally task/member/scope. For first setup, supply the document bundle and ask for BOOT-00; pre-domain tasks follow its verified documentation/Git bootstrap.
- [ ] Verify the agent's read-only summary of the entire task and its numbered steps in order, plus actual checkpoint, executed versus human-verified state, dependencies, owner/reviewer, boundaries, expected outputs/checks, gates, and proposed first/resumed action.
- [ ] Verify the agent audited the task steps against the task purpose, prerequisites, outputs, acceptance checks, and canonical requirements; review any reported gap before authorizing implementation.
- [ ] Correct misunderstandings; the agent must not write even status/branch changes before this verification. If a result was already executed but not verified, review its existing evidence rather than allowing it to be repeated blindly.
- [ ] Before each numbered step, review the agent's short explanation of its purpose, intended changes/outputs, checks, and gates. Say okay before the agent executes that step; verify the result afterward.
- [ ] Ask the agent to locate recorded project information itself. Supply only genuinely missing decisions/access inputs; never paste secret values/MFA/OTP/passwords in chat.

## After every numbered step

- [ ] Does the report identify the correct step and concrete changed paths/resources?
- [ ] Does it show expected versus observed outcome, exact checks/results, pass/fail/blocked explanation, evidence/revision and remaining questions?
- [ ] Does the status table accurately record each execution checkpoint and human-verification state? The dated history need not contain a separate entry for every step or routine “verified; proceed” message; it should preserve meaningful outcomes, decisions, checks, blockers, consequential human direction, and closeout evidence.
- [ ] Were task boundaries, internal decision gates, privacy and ownership respected? Failed/skipped checks must be explicit.
- [ ] Say verify/continue, correct, or pause. The agent waits after every step; silence gives no permission. It records verification before advancing. If correction method/scope is uncertain it asks first.
- [ ] For frontend changes, verify the contributor followed the approved page/ownership map, used public feature boundaries, coordinated shared-page edits with the current writer, and kept Wanted Request conversations private. Confirm temporary accounts can browse but cannot initiate a response.

You may inspect evidence, but the agent must summarize what makes it acceptable and what you are deciding. You should not need to find files, reconstruct test criteria or perform routine implementation/Git commands.

## Task-wide closeout

- [ ] At task/milestone handoff, check the complete change against the task's acceptance conditions, relevant checklist items, tests/checks, documentation/evidence, privacy/secret handling, and work-log status. The agent should present failures and blockers plainly; you need not reconstruct acceptance from separate files.

## Decisions and separate approvals

- [ ] A question shows the exact uncertainty, affected action, relevant repo facts, useful options/recommendation and smallest decision needed. Durable answers are recorded canonically before consumers depend on them.
- [ ] For hosting/account/permission actions and cloud create/change/delete, deployment, paid provider/load test, external communication or destructive cleanup, review the concrete target/action before approval. Cloud plans include identity/account/region/environment, resource changes/exposure/permissions, cost/headroom/caps/stop limits, rollback and cleanup/retention.
- [ ] Approve that exact plan/version only. Changed plans return for review. General understanding/step verification or a main merge is not separate action authorization.
- [ ] Human-only account/device steps have specific instructions and expected safe results; the agent verifies afterward through the approved access path.

## Peer review and merging

- [ ] Each contributor uses an isolated branch/clone/worktree. After the full PD-00–PD-03 audit confirms all four tasks' outputs and checks with no gaps, integrate that handoff directly into `main` without a PR. BOOT-00's documentation seed keeps its separate direct-to-main rule. Later changes use task/milestone PRs.
- [ ] For pre-domain work, verify the kickoff/stream/integration ownership slot and reserved path scope from the task list. Confirm the PD-00–PD-03 handoff is merged before streams clone, and that each owner removes only their own `.gitkeep` markers; cross-stream changes are coordinated before editing.
- [ ] For PRs, a different designated human peer reviews, with AI assistance if useful; affected owners approve shared surfaces. Author verification does not replace peer approval.
- [ ] Use `docs/prompts/peer-review-prompt.md` as a thorough, scope-adapted review aid. Review findings yourself, verify the latest head/target, required checks and affected-owner approvals, and explicitly authorize the exact PR/revision before merge. AI review is not approval and the prompt grants no merge or deployment authority.
- [ ] Required local/CI checks, dependency milestones and conflict-resolution review pass before authorizing the concrete merge. The author agent cannot approve or autonomously merge its PR.
- [ ] Consumers use the recorded accepted main revision; cloud environment operations remain separately approved and serialized.

## Feature, NFR, and final gates

- [ ] Readiness milestones permit their named consumers but do not claim entire FR/NFR/task completion. A required blocker means incomplete work.
- [ ] Dataset/labels/fixtures/contracts/Black/local setup/CI/work-log/secret-reference/cloud-inventory outputs are evidenced in their assigned task. Final data validation follows domain schemas.
- [ ] Detailed NFR tests happen at their earliest accurate full relevant path, with manifests/tooling/deployment/caps approved beforehand. Later material changes trigger affected revalidation. Offline NFR-04 is valid offline; local smoke checks cannot prove cloud latency/recovery.
- [ ] Document 2 owns the primary ECS/Lambda implementation/comparison; CLOSE-00 owns final whole-project budget reconciliation and report/demo/submission package.
- [ ] Optional work has its own technical prerequisites, your explicit selection and OPTIONAL-OK schedule/cost protection. The recorded planning change explains its earlier scheduling relative to PRD §8; the final buffer remains protected.
- [ ] Task/phase/project closure includes actual checks, human verification, reviewed revisions/evidence, approved cleanup/retention and required delivery state. Do not accept a blocker/deferred required requirement as successful completion.

**Loop:** agent explains the whole task → you verify → before each numbered step, agent explains that step → you say okay → agent executes only that step and reports evidence → you verify → repeat. A new task needs a new understanding verification.

## Environment, startup and stub evidence

- [ ] For a contributor using WSL, the agent reuses the existing setup and works in the verified WSL clone; otherwise it uses that contributor's verified environment. Confirm source staging is distinct from the clone and no redundant setup was done.
- [ ] The agent reports actual workstation/tool/container/credential-route facts and shows that commands use the selected toolchain for that environment, with relevant connectivity evidence.
- [ ] Before isolated work, verify that real PRE-00/DL-00 and frozen contracts exist, or that the exact isolated step is permitted by the stub guide. The agent must identify reviewed stub scenarios and pending real obligations; unknown semantics/security decisions still require a question.
- [ ] Every staged real subcheck retains its original step ID, owner, dependency/revision, resume trigger and acceptance test in the work log. Human verification authorizes only the reported isolated increment; readiness/FR/NFR/full completion remains pending.
- [ ] Review evidence that deployed config rejects test doubles and fake auth, with no public bypass or fallback to fake success. Isolated PRs are labeled and reviewed without claiming readiness.
- [ ] Verify that the earliest pending integration checkpoint resumes when its upstream revision arrives and that original real checks pass before acceptance. Final integration/NFR/experiment/closeout cannot rely on stub-only evidence.
