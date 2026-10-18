# Campus Marketplace — Agent Execution Checklist

**Canonical path:** `docs/checklists/agent-checklist.md`

**Sources:** `docs/README.md`, product reference/unchanged PRD, shared conventions, repository structure, bootstrap/pre-domain/domain/experiment/final task lists, project task index, root `CONTRIBUTING.md`, reusable prompt, current status/decisions/contracts/environment/evidence. This is an execution check; canonical sources retain detailed rules. Prior-source provenance belongs in `docs/source/README.md`, not recurring runtime questions.

## Before any write

- [ ] Inspect the workspace/bundle or repository read-only; preserve changes and reconcile branch/main/remote active PRs/task checkpoints with real evidence.
- [ ] Read task index and roster; choose only the requested/assigned task and its next unexecuted checkpoint. If the existing exocrat/clip clone/document seed is incomplete select BOOT-00; route through PRE-00, domain milestones, experiment and CLOSE-00 afterward.
- [ ] Distinguish expected outputs from missing prerequisites. Search the repo/bundle yourself; ask about every unresolved uncertainty/conflict. No log/branch/file mutation yet.
- [ ] Audit the selected task's ordered steps against its purpose, prerequisites, outputs, acceptance checks, and canonical requirements. Report gaps or confirm none; do not silently work around a material omission or contradiction.
- [ ] Summarize the entire selected task and its numbered steps in order, including the audit result, prerequisites, expected outputs/checks, gates, completed versus pending/verified state, owner/reviewer, and the first step to execute. Wait for human verification.

## Each verified numbered step

- [ ] Before executing each numbered step, explain its purpose, intended changes/outputs, applicable checks, and any internal decision or separate-approval gate. Wait for the human's explicit okay; task-level verification alone does not authorize the next step.
- [ ] Use the isolated task branch/worktree and scoped claim under CONTRIBUTING.md. Resume partial steps without repeating side effects; executed-but-unverified steps wait for verification.
- [ ] Execute that step only; stop at internal decisions/separate action approvals. Do not silently reorder/batch or work elsewhere while waiting without explicit instruction. Only the documented human-verified stub checkpoint route permits staged integration obligations.
- [ ] Use actual registered commands. Create/register commands explicitly assigned to this step; missing required prerequisite commands block dependent work.
- [ ] Follow shared conventions and public-domain ownership; reserve/review shared file/migration/contract changes and regenerate derived files.
- [ ] Run applicable step checks with exact command/results. Use pinned Black for Python and relevant local/CI gates at milestone completion. Preserve failures; report skipped/inconclusive checks honestly.
- [ ] Use synthetic safe fixtures/evaluation data; inspect changes/logs/outputs for secrets/real data/private conversation content. Production rejects unsafe fakes.
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
| BOOT-00 | Approved bundle/PRD checksum, audited documentation/Git seed committed on local `main`, source provenance and roster, actual local/remote status recorded, no falsely completed implementation tasks. Pending publication does not block PD-00 in this clone. |
| PD-00–03 | Starting-state audit/preservation, canonical sources/provenance, minimal toolchain/layout, Git/PR reviewer setup, shared status/command/secret-reference homes, and the tracked path-ownership map for four streams. |
| PD-04–10 | API/core, web, database/data, and cloud-preparation streams stay within their reserved roots; their task dependencies still control start order. |
| PD-11–19 / PRE-00 | Integration owner reconciles contracts, CI, commands, shared cloud, task/checklist docs, and the full foundation audit/handoff. |
| DL-00 | Four contracts/combined source agree; supported Search listing-data boundary, auth/contacts, read-watermarks/notification interfaces, private-data classifications and no call cycles. |
| ID-01/LI-01/SE-01/CN-01 | Explicit readiness PR/milestone distinct from full FR/NFR completion; assigned UI/core/fixtures and final dependent validations. |
| LI-02/SE-02/CN-02/CN-03 | Full feature UI/API/failure/privacy checks; explicit provider/read-state/image/selection boundaries and actual live deployment when required. |
| DATA-READY | Final schema/config-aware loader, >=5,000 users/>=1,000 listings, logical fingerprint/integrity and 20+ human-reviewed labeled queries. |
| INT-01 | All required FR/NFR-01–07 evidence, accurate integrated/recovery tooling/manifests, budget-to-date/reserve, no required blocker counted as pass. |
| EXP-01–08 | Approved comparison design/tooling, explicit mixed implementation/packaging/routing/Terraform, parity/deploy/pilot/run/analyze/cleanup evidence. |
| CLOSE-00 | Affected regression/revalidation, full-project cost/NFR-08, exact residual resources, final report/demo/viva/delivery and honest submission status. |

## Cloud, NFR, and optional gates

- [ ] Inspect/reuse shared resources; approve the exact target/plan/cost/caps/rollback/cleanup before any gated operation, renew approval when changed, and verify actual deployed revision/resources. CI/main merge does not authorize deployment/apply.
- [ ] Create/approve measurement manifests and validate local tools/readiness before accurate NFR runs. Preserve raw/invalid results. Reverify affected evidence after later changes.
- [ ] Optional tasks need their feature-specific prerequisites, explicit selection and OPTIONAL-OK. Required work/NFR/experiment/budget/final buffer stays protected; follow the accepted scheduling decision, with no blanket INT-01 or elapsed-buffer prerequisite.

## PD-04 Python tool checks

- [ ] From the repository root, run `uv sync --locked`; confirm root `pyproject.toml`/`uv.lock` supply Python 3.14 and the pinned development tools, with local `.venv` ignored.
- [ ] Run `make format-python`, inspect the source diff, then run `make check-python-format`. The check must fail on deliberate temporary formatting drift without changing source; remove temporary probes afterward. Plain `make` must select check-only. Record an empty-source result as such.
- [ ] Confirm versions with `uv run --locked black --version` (26.10.1) and `uv run --locked pytest --version` (9.1.1). Use `uv run --locked pytest` for implemented tests; exit 5 is no collection, not a passing suite. Keep Black/pytest configuration solely in root `pyproject.toml`.
- [ ] Follow the [contributor commands](../../CONTRIBUTING.md#local-python-tooling-pd-04) and [command registry](../environment/commands.md). Reuse recorded clean-install/negative-test evidence where unchanged. CI remains PD-12 and aggregate lifecycle commands remain PD-13; deferred Python lint/type tools are documented in the [tooling decision](../decisions/python-test-tooling.md).

## PD-05 API foundation checks

- [ ] Follow the [API instructions](../../apps/api/README.md): `uv sync --locked`, then `uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000`; verify `curl --fail http://127.0.0.1:8000/health` returns only `{"status":"ok"}` and stop the owned process with Ctrl+C. Do not interfere with another running developer process or claim dependency readiness from liveness.
- [ ] Run `uv run --locked pytest apps/api/tests -q` and `make check-python-format`. Check health in explicit test mode, safe local defaults, rejected configuration, no input-value leaks and ignored dotenv/example files. Reuse the recorded fresh locked environment evidence if dependencies/configuration are unchanged.
- [ ] Review README-only domain placeholders and shared-core boundaries: pending PD-06 conventions and PD-08 database lifecycle must not be represented as working services. Keep configuration examples non-secret and preserve the distinction between local checks and future CI/cloud evidence.

## PD-12 CI and merge-gate checks

- [ ] Run `make check` with locked setup/local Docker; verify CI still calls the shared registry and retain applicable failure-control evidence.
- [ ] Verify hosted **CI / Foundation quality gates** success for the current PR revision, with run URL/head/base evidence; local-only evidence is insufficient. Confirm the exact status context/source on the first hosted run.
- [ ] Follow [the merge gates](../../CONTRIBUTING.md#ci-and-required-merge-checks-pd-12): independently approved peer/affected-owner review, resolved findings and separate exact-revision merge authorization. The manual fallback is approved; do not claim technical host enforcement from inaccessible settings.
- [ ] Obtain separate approval before hosting changes; retain unresolved dependency/platform gates. PD-18 consolidates these checks without accepting unrun hosted checks.

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
