# Campus Marketplace — Git, PR, and Execution Workflow

**Canonical path:** `CONTRIBUTING.md`

## Human and agent responsibilities

Each contributor has an execution agent. Before work, the agent explains the entire selected task and its ordered steps, dependencies, outputs/checks and decision gates, then waits for that contributor's understanding verification. It implements one numbered step at a time and waits for verification of each report. The agent runs routine Git/build/test commands, prepares PRs and resolves review comments. A human supplies missing decisions/access that cannot be obtained from the repository and verifies each increment. Do not ask the human to run routine commands, locate files or reconstruct acceptance criteria.

The designated peer reviewer may use their own AI review session to inspect the diff, run checks and produce findings. Final peer approval belongs to the designated human. An author/author-agent cannot approve its own PR. Human step verification does not replace peer review, and peer approval does not authorize cloud changes.

## Main, task branches, and isolated workspaces

`main` contains work with its real versus isolated acceptance status recorded. During BOOT-00, the team-approved initial documentation seed and step 6.5 documentation revisions may be committed directly to the existing `main`, even though it already contains the original README commit. This is a one-time, docs-only exception; a separate peer review is not required for this commit. The author must still inspect the exact staged diff after the documentation audit. The exception does not authorize a remote push; publishing the local BOOT-00 seed remains separately gated by human approval of the exact target and revision. That publication gate does not block PD-00 in the clone where BOOT-00 is locally complete; other clones must first obtain the canonical documentation revision. Do not change host protections to make a direct main update possible. If the host rejects it, stop and report the blocker.

After a full audit confirms that PD-00, PD-01, PD-02, and PD-03 outputs and checks are correct with no unresolved gaps, integrate the combined handoff directly into the existing `main`, without a PR. That full audit is the gate for this handoff. Once it is on `main`, all later changes use task or milestone PRs and the normal peer-review rules. After PRE-00, `main` must remain locally runnable with required checks passing. The document bundle alone is not a claim that the app runs or any implementation task is complete.

Each person uses a separate clone on separate computers, or a separate Git worktree and task branch on a shared computer. Never run multiple coding agents in one working directory or switch a worktree out from under an active agent. The roster is fixed in the project task index before parallel work; select only assigned tasks unless the human explicitly reassigns ownership and the registry is updated.

Branch naming: `task/<task-id-lowercase>-<short-purpose>`, e.g. `task/id-01-identity`. A task with a merged readiness PR can continue on a subsequent branch, e.g. `task/id-01-final-verification`. Name the exact milestone and originating task in that PR. Do not create a PR for every numbered step; commits are useful checkpoints, not a requirement for every read-only action. Before a task or milestone handoff, inspect the complete diff, staged files, task acceptance checks, tests, generated files, documentation, and secret/data scan results. Commit only reviewed in-scope files. Preserve user changes and never commit sensitive state/plan artifacts.

Obtain explicit human approval before every commit. Approval to execute a task step, including a step that mentions committing, is not commit approval. Prepare and verify the changes, then leave them uncommitted until approval is given.

## CI and required merge checks (PD-12)

Run `uv sync --locked`, root `npm ci`, then `make check` before review. The
[command registry](docs/environment/commands.md#shared-aggregate--pd-12-step-6)
describes prerequisites and effects. Workflow **CI**, job **Foundation quality
gates**, runs the same ordered checks on PRs and pushes to `main`: parity,
Black, Python/data tests, domain boundaries, contract freshness, web
lint/tests/types/build, database-wrapper safety, clean PostgreSQL migrations/schema
and secret scanning. This job is the intended required GitHub Actions check;
confirm its exact displayed context/source on the first hosted PR run.

**Current status:** local aggregate passed; workflow publication, hosted success
and hosted intentional-failure/recovery evidence remain pending. Local results
alone do not satisfy the hosted gate. CI never merges, deploys or applies.

### Approved manual fallback

Read-only inspection on 2026-10-18 found a private repository and no admin access
for the current account. Rulesets returned HTTP 403 with an upgrade requirement;
branch-protection inspection returned HTTP 404, which does not prove protections
are absent. GitHub documents [private-repository protection plan requirements](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
No host setting, plan or visibility was changed.

Approved by the current integration contributor on 2026-10-19; use this
human-enforced gate while hosting cannot enforce it. See the
[decision record](docs/decisions/manual-main-merge-gate.md).

1. Use a PR into `main`; no direct main push, force push or deletion.
2. Refresh main into the branch as required by the existing merge workflow;
   rerun affected checks. Record the exact current PR head and base SHAs.
3. Require a successful **Foundation quality gates** run for the current PR
   revision and local `make check` evidence. Missing, skipped, cancelled or failed
   required checks do not pass. Record the hosted run URL and tested revision.
4. Require one independent designated human peer approval, all affected-owner
   approvals and resolved findings for that revision. New reviewable changes
   require renewed review. Use [the peer-review prompt](docs/prompts/peer-review-prompt.md).
5. The human checks that the revision/evidence is still current and separately
   authorizes the exact PR/head/target merge. Record approvals, run evidence and
   accepted main SHA in the work log. CI never performs the merge.

This fallback cannot technically stop someone bypassing the policy. Approval
accepts the manual process; it does not authorize any particular merge. If supported hosting
becomes available, prepare a separately approved main-protection change requiring
PR review, the confirmed Actions check, up-to-date branches and resolved
conversations, with force pushes/deletions disabled. Reverify after configuration.
PD-18 consolidates these checklist requirements; pending foundation dependencies
and PD-19/PRE-00 gates remain unchanged.

## Starting and claiming work

1. Inspect the current workspace read-only; fetch the approved remote main/task branches and inspect relevant draft PRs when access is available. Read the main roster and current task/step evidence. The main work log contains merged status; reconcile active work against the assigned remote task branch's checkpoint log and draft PR before treating an item as available.
2. Explain the entire selected task/milestone and its ordered steps, verified prerequisites, permitted paths, expected outputs/checks, decision gates, first action and uncertainties. Wait for human verification before branch/status/file mutations.
3. Check whether the assigned task already has an active branch/PR/session. Resume that work after human verification or ask about conflicting claims; do not open a second implementation stream for the same task. Only the named contributor can claim its task. Unknown ownership is a question, not a race to claim the first available task.
4. Create/reuse the isolated branch/worktree and record the claim/checkpoint. Publish an early draft PR once an in-scope verified checkpoint is ready, except for the BOOT-00 seed and combined PD-00–PD-03 handoff, which follow their direct-to-main paths above. Use the approved repository host/target. The agent handles the Git operations; any missing authentication uses the approved secure path.
5. Update only your assigned task row/entries on your branch. The release coordinator serializes shared main-log/registry updates through reviewed status PRs as needed. Other agents fetch active task branches when reconciling live progress; a stale main row alone is not proof a task is unclaimed. Preserve append-only history during merge conflicts.

## Task and milestone PR lifecycle

1. Implement verified steps on the branch; stop at internal uncertainty/approval gates. Keep the work-log status table current for each step and verification; add concise dated history only for meaningful outcomes, decisions, checks, blockers, consequential human direction, and task/merge closeout. Related steps may share an entry; routine “verified; proceed” updates do not need separate entries. Check dependencies at task start; use a stub only for a task step explicitly allowed by the stub guide, and keep real integration pending until its checks pass.
2. At an isolated implementation handoff, task or named readiness milestone, inspect diff/staged files and run applicable exact local formatting/type/build/migration/contract/tests plus the aggregate CI-equivalent check. Show failed/skipped checks honestly. A required failure blocks merge/milestone acceptance unless the existing bootstrap stage explicitly has no corresponding implementation check yet.
3. Open/update the PR with task/milestone ID, problem/resulting behavior, scope, prerequisite revisions, expected/observed checks, evidence, work-log state, decisions, reviewer requests and remaining steps. Readiness PRs state which capabilities are ready and which FR/NFR checks remain pending.
4. Request the designated peer reviewer and affected owners. Use the task-agnostic checklist in [`docs/prompts/peer-review-prompt.md`](docs/prompts/peer-review-prompt.md) against the exact PR base/head; the reviewer adapts its checks to the actual changed scope. The reviewer checks correctness, ownership/contract compatibility, privacy/security, data/migrations, generated artifacts, test coverage/failure paths and evidence. Shared core/contracts/conventions require affected-domain approval; reviewers are among the four people, with roles mapped in the roster. An AI-assisted review supplies findings, not human approval.
5. Resolve comments within the assigned scope. Bring updated main into the branch using the recorded merge strategy (default: merge main into the task branch). Inspect conflict resolutions, rerun affected checks and the required merge gates, and obtain renewed review where the reviewed diff changed materially. Do not force-push/rewrite shared history without explicit authorization.
6. Before merge, verify peer human approval, affected-owner approval, CI results, prerequisite milestone acceptance appropriate to the declared isolated or integrated scope, correct branch/target, and no unresolved review. The designated human confirms the latest reviewed head and explicitly authorizes that concrete PR/revision for merge. The agent may perform the merge only after that authorization; it must not approve or merge its own PR autonomously.
7. After merge, record the actual accepted main revision/PR/checks and readiness/task status. Refresh dependent workspaces. If a post-merge check fails, stop propagation, report it and coordinate a reviewed fix/revert; do not mark consumers unblocked from a failed revision.

## Review allocation

| Author/area | Primary peer | Additional reviewer when relevant |
|---|---|---|
| A — Identity and notifications | D | Consumers of changed auth/contact/recipient contracts |
| B — Listings and images | C | D for buyer-selection behavior; A for auth interfaces |
| C — Search, wanted and saved | B | A for authorization; D for conversation-facing contracts |
| D — Conversations and offers | A | B for selection/availability; A reviews notification-producer integration |
| Shared contracts/core or integrated release | Named coordinator with a different primary human reviewer | All affected domain owners |

Map A/B/C/D to actual people during BOOT-00/PD-03. Security, platform, frontend and contract roles are hats worn by these people. A coordinates DL-00/INT-01/CLOSE-00 by default subject to the human-confirmed roster; each domain executes its own test/fix/evidence slice. Inspect actual workload and rebalance future work through an explicit roster update if necessary; task counts are not an effort estimate.

## Shared files, migrations and generated outputs

Identify one current writer before changing combined contracts, core types, common web utilities, shared page compositions, migration integration, generated outputs, shared CI, Terraform or the task registry. For web work, consult `docs/architecture/frontend-collaboration.md` for the human-verified page composition, and after Step 3 for its maintainer, feature entry points and import boundaries. Other owners submit bounded changes/review rather than concurrent uncoordinated edits. Generated artifacts are regenerated from their editable source through the frozen command; never hand-edit them. Allocate non-colliding migration identifiers/heads using the selected migration tool; resolve multiple heads under the named migration integrator and test a clean database. A shared-file reservation is recorded with owner/branch/scope in the repository checkpoint; inspect current remote work before taking it.

Dependencies use merged readiness milestones from main. Do not silently base production work on another person's unreviewed branch. Any exceptional stacked/dependent PR arrangement needs an explicit recorded plan and cannot bypass review or final main-based checks.

## Hosting protections and cloud boundaries

BOOT-00 verifies the supplied exocrat/clip remote/account/branch policy and records actual access; it does not create another host/repository. Later task and milestone PRs require independent human peer review, required checks, and explicit human authorization before integration. BOOT-00's documentation seed follows its separate direct-to-main rule. The combined PD-00–PD-03 handoff goes directly to `main` after the full audit described above. All subsequent changes use PRs. PD-12 may configure supported PR/check protections, but they do not replace the manual requirements for later PRs.

CI runs local/disposable tests and build/format/contract/secret gates. A merge does not automatically deploy, send messages, invoke paid providers, create billable infrastructure, or apply Terraform. Those operations retain exact target/plan/cost/caps/rollback/cleanup approval in their assigned task. One named operator serializes changes to the shared cloud test environment and records its deployed revision; state locking alone does not make simultaneous deployments or load tests safe.

The command registry is `docs/environment/commands.md`; actual commands are populated by their named creator tasks. Missing commands that are outputs of the selected step are implemented and registered there. Missing prerequisites or uncertainty block dependent work and require a question.

## Local Python tooling (PD-04)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and GNU Make for your development environment, then run these commands from the repository root:

```bash
uv sync --locked
make format-python
make check-python-format
```

`uv sync --locked` creates or updates the ignored local `.venv` from `uv.lock`, including development tools; uv can obtain Python 3.14 when needed. Run it after cloning or receiving dependency changes. Each developer uses their own environment; do not share `.venv` or install project tools globally. `uv run` selects the project environment without shell activation. `--locked` refuses manifest/lockfile drift instead of silently rewriting the lock.

`make format-python` runs pinned Black 26.10.1 and rewrites Python source to the root `pyproject.toml` rules. Review its diff, then run `make check-python-format`; check-only reports formatting drift and returns nonzero without rewriting source. Plain `make` runs check-only too. Both targets may synchronize the local environment/cache. No cloud credentials or services are needed. Run the check before requesting review; PD-12 will wire automated CI, and PD-13 will extend the shared command front door.

The equivalent direct commands are `uv run --locked black .` and `uv run --locked black --check --diff .`. To inspect installed versions, run `uv run --locked black --version` and `uv run --locked pytest --version`.

The pinned test runner is pytest 9.1.1; run `uv run --locked pytest` to execute all configured tests, or `uv run --locked pytest apps/api/tests -q` for the API/configuration suite supplied by PD-05. Root `pyproject.toml` is its sole configuration. Root pytest includes PD-11 generation/TypeScript consumer tests and requires `npm ci` with the pinned Node toolchain; the API-only suite needs no Node. Exit 5 means no tests collected and must not be reported as a passing suite. Additional shared-core/fixture tests remain PD-06/10 outputs. Python lint/static type tools are deferred; see the [tooling decision](docs/decisions/python-test-tooling.md). Full command effects, prerequisites, failure recovery and current readiness are in the [command registry](docs/environment/commands.md).

## Local API foundation (PD-05)

After `uv sync --locked`, start the API from the repository root:

```bash
uv run --locked uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

In another terminal, `curl --fail http://127.0.0.1:8000/health` should return `{"status":"ok"}`; stop your foreground server with Ctrl+C. This is loopback-only process liveness, requiring no database/provider/cloud access. Environment settings come from the process, not `.env.example`. The [API setup/settings/test instructions](apps/api/README.md) document defaults, safe startup failures and occupied-port recovery. Run `uv run --locked pytest apps/api/tests -q` for persistent health/configuration checks and `make check-python-format` before handing off changes. `make check` supplies the shared quality aggregate; full lifecycle targets remain PD-13, and hosted CI verification remains PD-12.

## Assigned implementation paths

PD-02 freezes these roots against the actual repository layout before consumers edit them; valid existing equivalents may be retained through a recorded layout decision. Domain task outputs create the corresponding files only when needed.

| Contributor | Owned implementation roots |
|---|---|
| A | `apps/api/app/domains/identity/`, matching tests and `apps/web/src/features/identity/`; `apps/api/app/domains/conversations/notifications/` for CN-03 with D reviewing public producer/read-state integration |
| B | `apps/api/app/domains/listings/`, matching tests and `apps/web/src/features/listings/` |
| C | `apps/api/app/domains/search/`, matching tests, `apps/web/src/features/search/` and assigned generator/evaluation tooling |
| D | `apps/api/app/domains/conversations/` core/public APIs excluding A's notification module, matching tests and `apps/web/src/features/conversations/` |

Root/core/client utilities, contract sources/generated outputs, migrations, CI, shared docs and Terraform are coordinated paths. A task can propose a necessary change there, but must reserve the bounded writer scope and obtain affected-owner review. Domain ownership is not permission to edit unrelated private implementations. Record actual file paths and writer/reviewer in the task understanding before editing.

## WSL clone and isolated development

Use the existing exocrat/clip remote and Linux working clone under `docs/environment/wsl-and-first-session.md`; bootstrap verifies actual remote/emptiness before using its one-time initial-main seed exception. Each human/agent has a separate clone or worktree. A staging bundle is not a live task branch.

Follow `docs/architecture/stubs-and-integration-gates.md`. An isolated implementation PR must label stub-covered paths, contract version and pending real checks. It may merge only after peer review, local/CI checks and proof that deployed configuration cannot enable the fake or incomplete route unsafely. It creates no accepted readiness milestone. When the real upstream revision arrives, bring current accepted main into the branch, bind the real adapter, reconcile migrations/fixtures, rerun named checks and submit the integration/readiness PR. Shared environment deployment remains separately approved.
