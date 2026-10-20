# Campus Marketplace — Agent Execution Checklist

**Canonical path:** `docs/checklists/agent-checklist.md`

**Version:** 1.0 (first explicitly versioned PD-18 reconciliation)

**Updated:** 2026-10-20 (Asia/Kolkata)

**Sources:** [`AGENTS.md`](../../AGENTS.md), [`README.md`](../../README.md), [`docs/README.md`](../README.md), [source provenance](../source/README.md), the [PRD copy](../source/ICC_Project_PRD_FINAL.pdf), [product reference](../product/product-reference-and-architecture-decisions.md), [Document 2](../evaluation/ecs-only-vs-ecs-lambda-task-list.md), [shared conventions](../conventions/shared-conventions-and-cross-domain-contract-rules.md), [repository structure](../architecture/repository-structure.md), [project task index](../tasks/project-task-index.md), [pre-domain tasks](../tasks/pre-domain-task-list.md), [domain tasks](../tasks/domain-task-list.md), [foundation traceability](../architecture/foundation-traceability.md), [command registry](../environment/commands.md), [work log](../status/work-log.md), [`CONTRIBUTING.md`](../../CONTRIBUTING.md), the [reusable prompt](../prompts/reusable-task-prompt.md), the [stub guide](../architecture/stubs-and-integration-gates.md), and the [frontend collaboration map](../architecture/frontend-collaboration.md). Read task-linked decisions, contracts and evidence as applicable.

This checklist is an execution aid; canonical sources retain detailed requirements. Prior-source provenance belongs in `docs/source/README.md`, not recurring runtime questions.

## Before any write

- [ ] Inspect the workspace/bundle or repository read-only; preserve changes and reconcile branch/main/remote active PRs/task checkpoints with real evidence.
- [ ] Read task index and roster; choose only the requested/assigned task and its next unexecuted checkpoint. If the existing exocrat/clip clone/document seed is incomplete select BOOT-00; route through PRE-00, domain milestones, experiment and CLOSE-00 afterward.
- [ ] Read the current work-log row/history and the task's linked canonical sources before selecting an action; check available branches/PRs and distinguish verified remote state from unavailable evidence.
- [ ] Distinguish expected outputs from missing prerequisites. Search the repo/bundle yourself; ask about every unresolved uncertainty/conflict. No log/branch/file mutation yet.
- [ ] Audit the selected task's ordered steps against its purpose, prerequisites, outputs, acceptance checks, and canonical requirements. Report gaps or confirm none; do not silently work around a material omission or contradiction.
- [ ] Summarize the entire selected task and its numbered steps in order, including the audit result, prerequisites, expected outputs/checks, gates, completed versus pending/verified state, owner/reviewer, and the first step to execute. Wait for human verification.

## Each verified numbered step

- [ ] Before executing each numbered step, explain its purpose, intended changes/outputs, applicable checks, and any internal decision or separate-approval gate. Wait for the human's explicit okay; task-level verification alone does not authorize the next step.
- [ ] Use the isolated task branch/worktree and scoped claim under CONTRIBUTING.md. Resume partial steps without repeating side effects; executed-but-unverified steps wait for verification.
- [ ] Execute that step only; stop at internal decisions/separate action approvals. Do not silently reorder/batch or work elsewhere while waiting without explicit instruction. Only the documented human-verified stub checkpoint route permits staged integration obligations.
- [ ] Use exact commands from the [command registry](../environment/commands.md), `CONTRIBUTING.md`, and task-owned instructions. Confirm their actual state and effects; planned entries are not implemented commands. Create/register commands explicitly assigned to this step; missing required prerequisite commands block dependent work.
- [ ] Check each task's concrete data/API behavior against [`shared conventions`](../conventions/shared-conventions-and-cross-domain-contract-rules.md): UUID wire format, UTC-aware instants, integer-paise money, shared error envelope, server-built trusted caller context, bounded/stable pagination, owning-domain authorization/transactions, retry/idempotency behavior, and privacy-safe logs. Record the relevant tests/evidence; preserve public-domain ownership, review shared changes, and regenerate derived files.
- [ ] Run applicable step checks with exact command/results. Use pinned Black for Python and relevant local/CI gates at milestone completion. Preserve failures; report skipped/inconclusive checks honestly.
- [ ] Use synthetic safe fixtures/evaluation data; run the registered `uv run --locked python scripts/check_secrets.py` where applicable and inspect changes/logs/outputs for real data/private conversation content. PD-10 owns shared fixtures under `tests/fixtures/core/`; domain fixtures follow their owners' contracts. PD-09 supplies deterministic schema-independent generation and the label format/review procedure; final schema-aware data and human-reviewed labels at `data/evaluation/query-labels.json` belong to SE-01/DATA-READY, not preview runs. Production rejects unsafe fakes.
- [ ] Keep domain features inside their assigned task and reviewed public contracts. Cloud work must use the approved shared foundation and exact approved plan; inspect/reuse shared resources and do not provision duplicate or domain-specific resources without that domain's reviewed task and separate approval.
- [ ] Update the work-log status row after each step and verification, including current checkpoint (with the immediate next action for active work), execution/verification state, branch/revision/PR, evidence, questions, and blockers. Add dated history only for meaningful outcomes, decisions, checks, blockers, consequential human direction, or closeout; related steps may share an entry, and routine “verified; proceed” updates need no separate entry. Use exact UTC times for new entries and preserve existing timestamp precision. Preserve others' useful history.
- [ ] Report expected versus observed result, changed paths, commands/results, evidence and the precise verification decision. Stop until the human verifies; silence is not approval.

## Task-wide closeout

- [ ] At task or milestone handoff, inspect the whole change against its acceptance conditions: changed files, task-specific tests/checks, generated outputs, documentation, evidence, privacy/secret handling, and current work-log status. Resolve or clearly record each failure/blocker.
- [ ] Apply relevant checklist items during execution; perform the consolidated checklist review at task/milestone closeout rather than repeating unrelated items at each step. Keep action-specific safety and approval gates at the point of action.
- [ ] Explain each new function or meaningful code unit in a docstring, comment, or nearby documentation, including purpose and relevant inputs/outputs, side effects, security assumptions, and limits.

## Phase/task coverage

- [ ] For frontend work, follow the approved page/ownership map and public feature entry points; reserve shared page/composition edits with one named current writer; do not import another feature's private implementation. Keep request-based conversations private and enforce temporary-account response limits through server authorization.

| Phase/tasks | Required checklist evidence |
|---|---|
| BOOT-00 | Verify the approved source bundle/checksum, preserved Git seed on local `main`, provenance, roster, and actual local/remote status; no implementation task is falsely complete. Pending publication does not block PD-00 in this clone. |
| PD-00 | Verify the starting-state inventory against tracked files and repository layout; preserve existing changes and correct stale work-log claims with evidence. |
| PD-01 | Verify required canonical sources/PRD provenance, docs index, and requirement-to-task/output/evidence map; planned paths are identified as planned. |
| PD-02 | Verify one selected toolchain/layout and exact manifest/lockfile homes; compatibility claims match recorded environments and evidence. |
| PD-03 | Verify README/contributor/agent entry points, roster/task-path ownership, command/secret references, `.gitkeep` roots, and the audited kickoff handoff. |
| PD-04 | Verify locked Python setup, pinned Black, rewriting/check-only commands, check-only failure probe, and one canonical config. |
| PD-05 | Verify local API health/configuration and tests without claiming dependency readiness or domain behavior. |
| PD-06 | Verify approved shared conventions, decision records, core helpers, and applicable boundary/error/pagination/auth-context/logging tests. |
| PD-07 | Verify only approved routes/pages, all four feature markers, public component entry points, local install/start/checks, ownership, and downstream handoff. |
| PD-08 | Verify reviewed schema/migrations and retained local lifecycle evidence; record the user's confirmation of other-machine Linux AMD64/macOS checks and state that raw commands/results are unavailable here, not independently reproduced. |
| PD-09 | Verify deterministic synthetic generator/manifest, safe retention and label-review format; final schema-aware data and reviewed labels remain SE-01/DATA-READY. |
| PD-10 | Verify reusable minimal synthetic fixtures, explicit test-only fakes and production rejection, retries/failures/auth cases, and redacted output. |
| PD-11 | Verify editable contract source, OpenAPI/type consistency, and backend/frontend domain-boundary checks; use `uv run --locked python scripts/generate_contracts.py generate` and `uv run --locked python scripts/generate_contracts.py check` for regeneration/freshness. |
| PD-12 | Verify PR-only workflow/current head-base success, cancellation behavior, local/CI Black gates, required checks, and separate independent-review/merge gates. |
| PD-13 | Verify `make setup`, registry-backed start/stop/test/check commands including `make check`, local aggregate parity, safe failures, and portable Terraform static checks. |
| PD-14 | Verify account/access, owner, budget, alert, and secret-reference records without exposing credentials or implying cloud changes. |
| PD-15 | Verify state ownership/locking/recovery/module boundaries, ignored private artifacts, and non-mutating static checks. |
| PD-16 | Verify the exact approved shared-resource inventory, plan/apply/runtime/stop evidence and retained operational gates; no domain-specific duplicate resources or domain/NFR acceptance implied. |
| PD-17 | Verify the single domain task list, FR/NFR/task/evidence coverage, dependency/owner gates, resource procedures and consistency with canonical contracts/decisions. |
| PD-18 | Verify both checklists against every PD task, current command/task/checkpoint rules, exact paths, source/version metadata, and actionable evidence. |
| PD-19 | Verify the full foundation audit and handoff against every required task/check, current revision, evidence, blocker and next action; do not pass required unresolved gates. |
| PRE-00 | Verify every required foundation gate, human/affected-owner review, accepted merged revision and handoff before domain feature work starts. |
| DL-00 | Four reviewed contracts and combined source agree; call graph is acyclic; all generated declarations are behavior-free/current; a consumer-owned Listings double type-checks; FR/NFR traceability and pending real integrations are explicit. |
| ID-01/LI-01/SE-01/CN-01 | Explicit readiness PR/milestone distinct from full FR/NFR completion; assigned UI/core/fixtures and final dependent validations. |
| LI-02/SE-02/CN-02/CN-03 | Full feature UI/API/failure/privacy checks; explicit provider/read-state/image/selection boundaries and actual live deployment when required. |
| DATA-READY | Final schema/config-aware loader, >=5,000 users/>=1,000 listings, logical fingerprint/integrity and 20+ human-reviewed labeled queries. |
| INT-01 | All required FR/NFR-01–07 evidence; public-contract use, auth/denial, retry/concurrency/failure, transaction ownership and privacy checks across journeys; accurate integrated/recovery tooling/manifests; budget-to-date/reserve; no required blocker counted as pass. |
| OPT-01/02/03 | Only explicitly selected work proceeds, after that task's named technical prerequisites and OPTIONAL-OK; required MVP/NFR/experiment/budget/final buffer remains protected. |
| EXP-01–08 | Approved comparison design/tooling, explicit mixed implementation/packaging/routing/Terraform, parity/deploy/pilot/run/analyze/cleanup evidence. |
| CLOSE-00 | Affected regression/revalidation, full-project cost/NFR-08, exact residual resources, final report/demo/viva/delivery and honest submission status. |

## Cloud, NFR, and optional gates

- [ ] Inspect/reuse shared resources and record evidence before claiming no additional Terraform resources. For a proposed resource, document purpose/owner/state/module/inputs/outputs/permissions/data class/cost cap/test window/evidence/reuse/rollback/cleanup; approve the exact target and plan before a gated operation, renew approval if changed, and verify deployed revision/resources. CI/main merge does not authorize deployment/apply.
- [ ] Create/approve measurement manifests and validate local tools/readiness before accurate NFR runs. Preserve raw/invalid results. Reverify affected evidence after later changes.
- [ ] Before any NFR run, follow the named accurate procedure in the [domain task list](../tasks/domain-task-list.md): SE-01 owns NFR-01/02/04, CN-01 owns NFR-05, and INT-01 owns NFR-03/06/07; declare NFR-08 caps before cloud work, track spend/reserve at INT-01, and complete final NFR-08 reconciliation in the [CLOSE-00 task list](../tasks/final-closeout-task-list.md). The [Document 2 comparison](../evaluation/ecs-only-vs-ecs-lambda-task-list.md) retains only its comparison and the explicitly narrow exception; this checklist is not an NFR procedure.
- [ ] Optional tasks need their feature-specific prerequisites, explicit selection and OPTIONAL-OK. Required work/NFR/experiment/budget/final buffer stays protected; follow the accepted scheduling decision, with no blanket INT-01 or elapsed-buffer prerequisite.

## PD-04 Python tool checks

- [ ] From the repository root, run `uv sync --locked`; confirm root `pyproject.toml`/`uv.lock` supply Python 3.14 and the pinned development tools, with local `.venv` ignored.
- [ ] Run `make format-python`, inspect the source diff, then run `make check-python-format`. The check must fail on deliberate temporary formatting drift without changing source; remove temporary probes afterward. Plain `make` must select check-only. Record an empty-source result as such.
- [ ] Confirm versions with `uv run --locked black --version` (26.10.1) and `uv run --locked pytest --version` (9.1.1). Use `uv run --locked pytest` for implemented tests; exit 5 is no collection, not a passing suite. Keep Black/pytest configuration solely in root `pyproject.toml`.
- [ ] Follow the [contributor commands](../../CONTRIBUTING.md#local-python-tooling-pd-04) and [command registry](../environment/commands.md). Reuse recorded clean-install/negative-test evidence where unchanged. CI remains PD-12 and aggregate lifecycle commands remain PD-13; deferred Python lint/type tools are documented in the [tooling decision](../decisions/python-test-tooling.md).

## PD-05 API foundation checks

- [ ] Follow the [API instructions](../../apps/api/README.md): `uv sync --locked`, then `uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000`; verify `curl --fail http://127.0.0.1:8000/health` returns only `{"status":"ok"}` and stop the owned process with Ctrl+C. Do not interfere with another running developer process or claim dependency readiness from liveness.
- [ ] Run `uv run --locked pytest apps/api/tests -q -W error` and `make check-python-format`. Check health in explicit test mode, safe local defaults, rejected configuration, no input-value leaks and ignored dotenv/example files. Reuse the recorded fresh locked environment evidence if dependencies/configuration are unchanged.
- [ ] Review README-only domain placeholders and shared-core boundaries: reflect the approved PD-06 conventions, and do not represent unresolved PD-08 runtime/platform/owner/hosted acceptance as complete. Keep configuration examples non-secret and distinguish local evidence from hosted/cloud acceptance.

## PD-12 CI and merge-gate checks

- [ ] For PR-only CI, verify latest main is incorporated and the successful run covers the recorded head/base. If main advances before merge, update and rerun; superseded/cancelled runs do not pass.
- [ ] Verify pinned Black hook installation/configuration and format/block/review/restage behavior; generated contracts remain excluded and CI formatting is independent. See [hook setup](../../CONTRIBUTING.md#black-pre-commit-hook-pd-12).
- [ ] Run `make check` with locked setup/local Docker; verify CI still calls the shared registry and retain applicable failure-control evidence.
- [ ] Verify hosted **CI / Foundation quality gates** success for the current PR revision, with run URL/head/base evidence; local-only evidence is insufficient. Confirm the exact status context/source on the first hosted run.
- [ ] Follow [the merge gates](../../CONTRIBUTING.md#ci-and-required-merge-checks-pd-12): independently approved peer/affected-owner review, resolved findings and separate exact-revision merge authorization. The manual fallback is approved; do not claim technical host enforcement from inaccessible settings.
- [ ] Obtain separate approval before hosting changes; retain unresolved dependency/platform gates under their original task/step IDs. Checklist coverage does not accept unrun hosted checks.

## PR and completion

- [ ] Integrate the combined PD-00–PD-03 handoff directly into `main` after a full audit confirms all four tasks' outputs and checks with no gaps. Use a coherent task/milestone PR for later changes; follow BOOT-00's separate documentation-seed rule. Do not approve or merge your own PR autonomously.
- [ ] When preparing a PR, point the human to `docs/prompts/peer-review-prompt.md` and remind them to arrange an independent peer review. Treat AI findings as review assistance only; wait for human peer/affected-owner approval and explicit authorization of the exact PR revision before merge.
- [ ] Record human step verification and accepted milestone/PR/main revision before unblocking consumers. Required blockers remain incomplete.
- [ ] Close only the requested scope; continued work is selected through the task index with a new understanding verification. Do not skip the experiment or final closeout.

## Existing WSL, startup and stub checks

- [ ] Both supplied checklists are read before BOOT-00/PD-00 writes; PD-18/INT-01 maintain them rather than defer their initial availability.
- [ ] For pre-domain streams, start from the merged PD-00–PD-03 handoff, remove only the `.gitkeep` markers in the assigned roots as the first action, preserve other streams' markers/paths, and coordinate a bounded cross-stream change before editing another owner's root.
- [ ] When the contributor uses WSL, reuse the existing WSL setup and run commands in that verified context and real exocrat/clip clone; otherwise use the contributor's verified environment. Keep source staging distinct from the clone; do not create nested bundle folders, repeat git init, add a second remote, or reinstall WSL unnecessarily.
- [ ] Inspect and record actual workstation/tool/container/credential-route facts. Run project install/start/check commands with the selected toolchain for that contributor's environment, and verify LF/executable permissions and connectivity where applicable.
- [ ] Before isolated work, real PRE-00/DL-00 and frozen contracts exist; the understanding report identifies allowed task/checkpoint, mode, reviewed stub scenarios and pending real obligations under the stub guide. Unknown semantics/security decisions still require a question.
- [ ] Every staged real subcheck retains its original step ID, owner, dependency/revision, resume trigger and acceptance test in the work log. Human verification authorizes only the reported isolated increment; readiness/FR/NFR/full completion remains pending.
- [ ] Deployed config rejects test doubles and fake auth; no public bypass or fallback to fake success. Isolated PRs are labeled and independently reviewed without claiming readiness.
- [ ] When the actual upstream revision arrives, the earliest pending integration checkpoint is resumed, migrations/data/adapters reconcile and the original real checks rerun before acceptance. Final integration/NFR/experiment/closeout never uses stub-only evidence.
