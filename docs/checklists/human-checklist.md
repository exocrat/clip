# Campus Marketplace — Human Verification Checklist

**Canonical path:** `docs/checklists/human-checklist.md`

**Version:** 1.0 (first explicitly versioned PD-18 reconciliation)

**Updated:** 2026-10-20 (Asia/Kolkata)

**Sources:** [`AGENTS.md`](../../AGENTS.md), [`README.md`](../../README.md), [`docs/README.md`](../README.md), [source provenance](../source/README.md), the [PRD copy](../source/ICC_Project_PRD_FINAL.pdf), [product reference](../product/product-reference-and-architecture-decisions.md), the [reusable prompt](../prompts/reusable-task-prompt.md), [project task index](../tasks/project-task-index.md), [pre-domain tasks](../tasks/pre-domain-task-list.md), [domain tasks](../tasks/domain-task-list.md), [Document 2](../evaluation/ecs-only-vs-ecs-lambda-task-list.md), [final closeout task list](../tasks/final-closeout-task-list.md), [foundation traceability](../architecture/foundation-traceability.md), [shared conventions](../conventions/shared-conventions-and-cross-domain-contract-rules.md), [command registry](../environment/commands.md), [work log](../status/work-log.md), [`CONTRIBUTING.md`](../../CONTRIBUTING.md), the [peer-review prompt](../prompts/peer-review-prompt.md), [stub guide](../architecture/stubs-and-integration-gates.md), and [frontend collaboration map](../architecture/frontend-collaboration.md). Follow task-linked decisions, contracts and evidence for the selected work.

The agent runs routine commands and prepares evidence; you verify understandable results, answer genuine unresolved questions and approve specific actions. Peer-review roles follow `CONTRIBUTING.md`.

## Start or resume

- [ ] Give the reusable prompt, optionally task/member/scope. For first setup, supply the document bundle and ask for BOOT-00; pre-domain tasks follow its verified documentation/Git bootstrap.
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

## PD-04 Python tooling verification

- [ ] Verify the agent's evidence that `uv sync --locked` installs the pinned tools into an ignored local environment, and that `make format-python` followed by `make check-python-format` works. Check-only must detect formatting drift without rewriting source; plain `make` is check-only.
- [ ] Confirm `uv run --locked black --version` reports 26.10.1 and `uv run --locked pytest --version` reports 9.1.1. The test command is `uv run --locked pytest`; no collected tests (exit 5) does not prove application behavior. Python lint/type tools are deferred.
- [ ] Confirm [CONTRIBUTING](../../CONTRIBUTING.md#local-python-tooling-pd-04) and the [command registry](../environment/commands.md) agree with the Makefile/root configuration. PD-12 owns CI; distinguish the implemented workflow from its current hosted result. Review the agent's summarized evidence; you do not need to run routine commands yourself.

## PD-05 API foundation verification

- [ ] Verify the agent's evidence for the [documented local API command](../../apps/api/README.md), health-only response and clean shutdown without database/cloud credentials. `{"status":"ok"}` is process liveness, not domain or dependency readiness.
- [ ] Review `uv run --locked pytest apps/api/tests -q -W error` results and formatting checks. Confirm tests cover health in test mode and safe configuration failures, use synthetic data, and avoid exposing supplied values. The agent runs routine checks; you verify the summarized evidence.
- [ ] Confirm shared-core/domain placeholders reflect the approved PD-06 conventions. Distinguish local checks from the user-confirmed PD-08 runtime/platform/owner gates and retain the recorded limits on unavailable other-machine artifacts. Setup/start/test instructions must match CONTRIBUTING and the command registry; local checks do not prove hosted acceptance.

## PD-12 CI and merge-gate verification

- [ ] For PR-only CI, verify latest main is incorporated and the successful run covers the recorded head/base. If main advances before merge, update and rerun; superseded/cancelled runs do not pass.
- [ ] Verify pinned Black hook installation/configuration and format/block/review/restage behavior; generated contracts remain excluded and CI formatting is independent. See [hook setup](../../CONTRIBUTING.md#black-pre-commit-hook-pd-12).
- [ ] Review `make check` and current hosted **CI / Foundation quality gates** evidence, including run URL and PR head/base revisions. Missing/skipped/cancelled/failed required checks do not pass.
- [ ] Follow [the approved manual fallback](../../CONTRIBUTING.md#approved-manual-fallback). It preserves PR-only merging, independent human/affected-owner approval and separate exact-revision merge authorization, but cannot technically prevent bypass.
- [ ] Recheck the exact current revision before authorizing merge; require renewed checks/review after relevant changes. Do not treat local checks or AI findings as hosted success or independent human approval.
- [ ] Hosting changes retain separate approval. Checklist coverage does not accept unrun checks; record open checks under their original task/step IDs. The user confirmed the previously pending PD-08/09/12/13/15 gates complete on 2026-10-19. PD-19 and PRE-00 are complete; PRE-00 acceptance and its evidence are recorded in the work log.

## Task-wide closeout

- [ ] At task/milestone handoff, check the complete change against the task's acceptance conditions, relevant checklist items, tests/checks, documentation/evidence, privacy/secret handling, and work-log status. The agent should present failures and blockers plainly; you need not reconstruct acceptance from separate files.

## Pre-domain task evidence

Use the task-specific acceptance checks in `docs/tasks/pre-domain-task-list.md`; this map identifies the evidence to inspect and does not replace those checks.

| Task | Verify the task evidence and boundary |
|---|---|
| BOOT-00 | Approved source bundle/checksum, preserved local Git seed, provenance, roster and actual local/remote state; no implementation task marked complete without evidence. |
| PD-00 | Starting-state inventory matches repository/layout; existing changes are preserved and work-log corrections cite evidence. |
| PD-01 | Canonical source copies and PRD provenance, documentation index, and source-to-task/output/evidence traceability. |
| PD-02 | One selected toolchain/layout and exact manifest/lockfile homes; compatibility claims match recorded machine evidence. |
| PD-03 | README/contributor/agent entry points, roster and reserved paths, command/secret-reference homes, tracked ownership roots, audited kickoff handoff. |
| PD-04 | Locked Python install, pinned Black, format and check-only commands, drift detection, one canonical configuration. |
| PD-05 | Local API health/configuration and tests; no claim of dependency readiness or domain behavior. |
| PD-06 | Canonical shared decisions/helpers and applicable tests for boundary, errors, pagination, trusted context, retries and privacy-safe logs. |
| PD-07 | Human-approved routes/pages, all four feature markers, public component entry points, local install/start/checks, ownership and handoff. |
| PD-08 | Review schema/migrations and retained lifecycle evidence; record the user's confirmation of Linux AMD64/macOS checks on other machines, noting their raw commands/results are unavailable here and not independently reproduced. |
| PD-09 | Deterministic synthetic generator/manifest, safe retention and label-review format; final schema-aware data and reviewed labels remain SE-01/DATA-READY. |
| PD-10 | Reusable synthetic fixtures, explicit test-only fakes, production rejection, failure/retry/auth cases and redacted output. |
| PD-11 | Editable contract source, OpenAPI/type consistency and backend/frontend boundary checks; verify `uv run --locked python scripts/generate_contracts.py generate` and `uv run --locked python scripts/generate_contracts.py check` evidence. |
| PD-12 | PR-only CI result for current head/base, superseded-run cancellation, local/CI Black, independent review and exact-revision merge gates. |
| PD-13 | `make setup`, exact registry-backed start/stop/test/check commands including `make check`, local aggregate parity, safe failures and Terraform portability checks. |
| PD-14 | Account/access, owner, budget, alert and secret-reference evidence; no credentials exposed or cloud change inferred. |
| PD-15 | State ownership/locking/recovery/module boundaries, private artifacts ignored, non-mutating static checks. |
| PD-16 | Exact approved shared-resource inventory, plan/apply/runtime/stop evidence and retained operational gates; no domain-specific duplicate resources or domain/NFR acceptance implied. |
| PD-17 | One authoritative domain task list and its FR/NFR, dependency, owner, evidence, resource and contract consistency checks. |
| PD-18 | Both current checklists map to every task and actionable evidence, with valid links, exact commands, checkpoint rules, and source/version metadata. |
| PD-19 | Full task/check audit, current revision, accurate evidence/blockers and usable foundation handoff; no required unresolved gate counted as passed. |
| PRE-00 | All required checks/reviews, human acceptance, accepted merged revision and handoff before any domain feature work starts. |
| DL-00 | Affected domain owners reviewed the shared contracts; generated declarations match the editable source and contain no behavior; consumer-double type-check and registered checks pass; independent review and exact-revision merge remain separate gates; real integrations and cleanup implementation approval stay pending where recorded. |

## Decisions and separate approvals

- [ ] A question shows the exact uncertainty, affected action, relevant repo facts, useful options/recommendation and smallest decision needed. Durable answers are recorded canonically before consumers depend on them.
- [ ] For hosting/account/permission actions and cloud create/change/delete, deployment, paid provider/load test, external communication or destructive cleanup, review the concrete target/action before approval. A resource proposal records purpose, owner, Terraform state/module, inputs/outputs, permissions, data class, shared-resource reuse, cost/headroom/caps/stop limits, test window, evidence, rollback and cleanup/retention, as well as identity/account/region/environment and exact resource changes/exposure.
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

## Environment, startup and stub evidence

- [ ] For a contributor using WSL, the agent reuses the existing setup and works in the verified WSL clone; otherwise it uses that contributor's verified environment. Confirm source staging is distinct from the clone and no redundant setup was done.
- [ ] The agent reports actual workstation/tool/container/credential-route facts and shows that commands use the selected toolchain for that environment, with relevant connectivity evidence.
- [ ] Before isolated work, verify that real PRE-00/DL-00 and frozen contracts exist, or that the exact isolated step is permitted by the stub guide. The agent must identify reviewed stub scenarios and pending real obligations; unknown semantics/security decisions still require a question.
- [ ] Every staged real subcheck retains its original step ID, owner, dependency/revision, resume trigger and acceptance test in the work log. Human verification authorizes only the reported isolated increment; readiness/FR/NFR/full completion remains pending.
- [ ] Review evidence that deployed config rejects test doubles and fake auth, with no public bypass or fallback to fake success. Isolated PRs are labeled and reviewed without claiming readiness.
- [ ] Verify that the earliest pending integration checkpoint resumes when its upstream revision arrives and that original real checks pass before acceptance. Final integration/NFR/experiment/closeout cannot rely on stub-only evidence.
