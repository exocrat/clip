# Campus Marketplace — Shared Work Log and Checkpoints

**Template version:** 3.1 · **Created:** 2026-10-14 · **Canonical path:** `docs/status/work-log.md`

Read this status before work and reconcile it with the repository and active branch evidence. Keep the status table current and add a short dated entry for meaningful progress, a completed step, a block, human verification, or merge. Record enough to resume and verify the work; do not repeat background or copy long command output. Keep test commands/results and decisions concise, and link evidence only when a relevant artifact already exists. Do not create a separate report just to duplicate the work log. Preserve prior facts and other contributors' entries. No implementation, cloud provisioning, PR approval, or test pass is complete until actual evidence supports it.

## Human/role roster (populate during BOOT-00/PD-03)

| Role | Actual human | Assigned work / peer |
|---|---|---|
| Initial bootstrap/foundation contributor | Suraj (B) | BOOT-00; no separate peer review for the one-time direct-to-main commit |
| A | Aditya | Identity/notifications; primary peer Rahul (D) |
| B | Suraj | Listings/images; primary peer Mohit (C) |
| C | Mohit | Search/wanted/saved; primary peer Suraj (B) |
| D | Rahul | Conversations/offers; primary peer Aditya (A) |
| Shared release/status coordinator | Aditya (A) | Documented default under `CONTRIBUTING.md`; confirm changes in PD-03 |
| Shared cloud operator | Not selected | One operator per recorded environment/window; separately approved actions |

## Current task state

Task status: not started / in progress / blocked / done; optional may be unselected/deferred. Step execution: not started / partial / performed / blocked. Human verification: pending / verified / correction requested. Readiness/full acceptance also requires the named reviewed main merge/checks. Record actual UTC update times and decision/approval evidence; no invented approval.

| Task | Owner role | Task status | Current step / sub-checkpoint | Execution state | Human verification | Branch/revision/evidence | Blockers | Last UTC update | Next action/question |
|---|---|---|---|---|---|---|---|---|---|
| BOOT-00 | B / Suraj (initial contributor) | done | Local documentation seed verified; publication pushed and verified | performed | verified | Current `origin/main` verified at `cfbf9352c03302990e6ffda09521f0a5450572d7`; includes seed `7fb9bfed79b45614a17de1bf2f9c50dbb3981b3f` and publication record | None | 2026-10-15 07:18 UTC | PD-00 in progress |
| PD-00 | Kickoff owner — Suraj (B) | done | Steps 1–6 complete; task-wide closeout reviewed | performed | verified | `task/pre-domain-foundation` at base `cfbf9352c03302990e6ffda09521f0a5450572d7`; work-log task table, initial inventory, Document 4 comparison, and `git diff --check` | None | 2026-10-16 07:02 UTC | PD-01 understanding report and human verification before any write |
| PD-01 | Kickoff owner — Suraj (B) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-00 | — | Start after PD-00 is complete |
| PD-02 | Kickoff owner — Suraj (B) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-01 | — | Start after PD-01 |
| PD-03 | Kickoff owner — Suraj (B) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-02 | — | Start after PD-02 |
| PD-04 | Stream 1 owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-02 | — | Start when dependency is met and owner assigned |
| PD-05 | Stream 1 owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-02, PD-04 | — | Start when dependencies are met and owner assigned |
| PD-06 | Stream 1 owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-05 | — | Start when dependency is met and owner assigned |
| PD-07 | Stream 2 owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-02 | — | Start when dependency is met and owner assigned |
| PD-08 | Stream 3 owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-02, PD-04, PD-05, PD-06 | — | Start when dependencies are met and owner assigned |
| PD-09 | Stream 3 owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-06, PD-08 | — | Start when dependencies are met and owner assigned |
| PD-10 | Stream 1 owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-04, PD-05, PD-06 | — | Start when dependencies are met and owner assigned |
| PD-11 | Integration owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-05, PD-06, PD-07 | — | Start when dependencies are met and owner assigned |
| PD-12 | Integration owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-04–PD-11 | — | Start when dependencies are met and owner assigned |
| PD-13 | Integration owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-04–PD-12 | — | Start when dependencies are met and owner assigned |
| PD-14 | Stream 4 owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-01–PD-03 | — | Start when dependencies are met and owner assigned |
| PD-15 | Stream 4 owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-14 | — | Start when dependency is met and owner assigned |
| PD-16 | Integration owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-04–PD-15 | — | Start when dependencies are met and owner assigned; cloud action gates still apply |
| PD-17 | Integration owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-14–PD-16 | — | Start when dependencies are met and owner assigned |
| PD-18 | Integration owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-01–PD-17 | — | Start when dependencies are met and owner assigned |
| PD-19 | Integration owner (unassigned) | not started | — | not started | pending | No implementation outputs in initial inventory (PD-00 Steps 2–3); task definition in `docs/tasks/pre-domain-task-list.md` | PD-00–PD-18 | — | Start when dependencies are met and owner assigned |
| PRE-00 | Integration owner (unassigned) | not started | — | not started | pending | Foundation gate has no acceptance evidence; see milestone row below | PD-07, PD-08, PD-11, PD-19 | — | Start only after its listed dependencies pass |
| DL-00 | A coordinator; all domains review | not started | — | not started | pending | No domain implementation outputs in initial inventory; task definition in `docs/tasks/domain-task-list.md` | PRE-00 | — | Start after PRE-00 |
| ID-01 | A | not started | — | not started | pending | No domain implementation outputs in initial inventory; task definition in `docs/tasks/domain-task-list.md` | ID-READY, LI-01, LI-02, SE-CORE, SE-02, CN-CORE, CN-02 | — | Start when dependencies are met |
| LI-01 | B | not started | — | not started | pending | No domain implementation outputs in initial inventory; task definition in `docs/tasks/domain-task-list.md` | LI-CORE, LI-02, SE-CORE | — | Start when dependencies are met |
| LI-02 | B | not started | — | not started | pending | No domain implementation outputs in initial inventory; task definition in `docs/tasks/domain-task-list.md` | LI-CORE, ID-READY | — | Start when dependencies are met |
| SE-01 | C | not started | — | not started | pending | No domain implementation outputs in initial inventory; task definition in `docs/tasks/domain-task-list.md` | SE-CORE, LI-01, LI-02, DATA-READY | — | Start when dependencies are met |
| SE-02 | C | not started | — | not started | pending | No domain implementation outputs in initial inventory; task definition in `docs/tasks/domain-task-list.md` | SE-CORE, ID-READY, LI-CORE | — | Start when dependencies are met |
| CN-01 | D | not started | — | not started | pending | No domain implementation outputs in initial inventory; task definition in `docs/tasks/domain-task-list.md` | CN-CORE, CN-03 | — | Start when dependencies are met |
| CN-02 | D; A/B interface review | not started | — | not started | pending | No domain implementation outputs in initial inventory; task definition in `docs/tasks/domain-task-list.md` | CN-CORE, ID-READY, LI-CORE | — | Start when dependencies are met |
| CN-03 | A; D producer review | not started | — | not started | pending | No domain implementation outputs in initial inventory; task definition in `docs/tasks/domain-task-list.md` | CN-CORE, ID-READY | — | Start when dependencies are met |
| INT-01 | A coordinator; all domain slices | not started | — | not started | pending | No integration completion evidence; task definition in `docs/tasks/domain-task-list.md` | ID-01, LI-01, LI-02, SE-01, SE-02, CN-01, CN-02, CN-03 | — | Start when dependencies are met |
| EXP-01 | C | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | INT-01 | — | Start when dependency is met |
| EXP-02 | C | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-01 | — | Start when dependency is met |
| EXP-03 | B | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-02 | — | Start when dependency is met |
| EXP-04 | B | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-03 | — | Start when dependency is met |
| EXP-05 | C | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-04 | — | Start when dependency is met |
| EXP-06 | C operator; B infra support | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-05 | — | Start when dependency is met; cloud action gates apply |
| EXP-07 | A; C/D calculation review | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-06 | — | Start when dependency is met |
| EXP-08 | B; A cost review | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-07 | — | Start when dependency is met |
| CLOSE-00 | A coordinator; all domain slices | not started | — | not started | pending | No final closeout outputs in initial inventory; task definition in `docs/tasks/final-closeout-task-list.md` | INT-01, EXP-08 | — | Start when dependencies are met |
| OPT-01 | A | unselected | — | not started | pending | No optional work selected; task definition in `docs/tasks/domain-task-list.md` | ID-READY, SE-02, CN-03, OPTIONAL-OK | — | Remains unselected unless human selects it |
| OPT-02 | C | unselected | — | not started | pending | No optional work selected; task definition in `docs/tasks/domain-task-list.md` | ID-READY, LI-CORE, SE-CORE, SE-02, CN-03, OPTIONAL-OK | — | Remains unselected unless human selects it |
| OPT-03 | C | unselected | — | not started | pending | No optional work selected; task definition in `docs/tasks/domain-task-list.md` | LI-02, SE-CORE, DATA-READY, OPTIONAL-OK | — | Remains unselected unless human selects it |

## Milestones

| Milestone | State | Creating task/checkpoint | Accepted revision/PR/checks | Human verification |
|---|---|---|---|---|
| PRE-00 | not accepted | PD-19 foundation gate | — | pending |
| ID-READY | not accepted | ID-01 step 12 | — | pending |
| LI-CORE | not accepted | LI-01 step 11 | — | pending |
| SE-CORE | not accepted | SE-01 step 10 | — | pending |
| DATA-READY | not accepted | SE-01 steps 2/4/9 | — | pending |
| CN-CORE | not accepted | CN-01 step 10 | — | pending |
| OPTIONAL-OK | not approved | Each optional task's selection/priority plan | — | pending |

## Concise checkpoint entries

Each entry should usually fit in a few lines and include:

- UTC date/time, contributor, task/step/checkpoint, and execution plus human-verification state.
- Expected and observed outcome, changed paths, and exact checks with results.
- Branch/revision and relevant evidence or decision reference, if applicable.
- Blocker or decision owner and the next safe action.

Record human verification when received. A performed step awaiting verification is not repeated or advanced. Keep task scope explicit; coordinate shared rows and merges; never remove another contributor's history. Links: `docs/tasks/project-task-index.md`, `docs/decisions/`, `docs/environment/`, `docs/evaluation/README.md`.

### BOOT-00 step 3 — clone and install seed — 2026-10-14
Suraj (B); performed and verified. Cloned existing exocrat/clip at /home/suraj/src/clip, preserved .git and LICENSE, created task/boot-00-doc-seed from origin/main 3e81554ce3d713478d8f0979d76480e286096455, and installed 28 bundle files at the clone root. All paths were present; no nested bundle folder. PRD source and clone SHA-256 matched: 8ac241d1e72472a5dc77edad18579ec5d2ca3ff2ac8fd454cbc6e9627abf4ad1. No commit or push.

### BOOT-00 step 4 — provenance and navigation — 2026-10-14
Suraj (B); performed and verified. Updated README.md, docs/source/README.md, docs/source/bundle-manifest.json, and this log. Existing optional-scheduling decision was retained. Link checks passed (17 README links; 10 required direct links); manifest checksum matched. The installed README at that checkpoint had SHA-256 f78b6c430df0beb15cab375916a2b9b8883384072cbb47302c1601d5e56d26e7. No commit or push.

### BOOT-00 step 5 — workstation and roster — 2026-10-14
Suraj (B); performed and verified. Added docs/environment/development-workstation.md; recorded observed WSL/tool/container facts and the A/B/C/D roster in the work log. Aditya (A) is the default release/status coordinator; shared cloud operator remains unselected. No secrets or cloud account facts were added. No application tests, commit, or push.

### BOOT-00 step 6 — documentation validation — 2026-10-14
Suraj (B); performed and verified. All 27 supplied baseline hashes and installed paths passed; PRD SHA-256 remains 8ac241d1e72472a5dc77edad18579ec5d2ca3ff2ac8fd454cbc6e9627abf4ad1. Checked 41 Markdown links/anchors; required task and milestone definitions, 45 step sequences, and the 61-node/175-edge dependency graph resolved without gaps, orphans, or cycles. Credential-signature scan found no secrets; no application data files were found. gitleaks, trufflehog, Graphviz dot, and full PDF text extraction were unavailable; local scans and graph parsing were used. PDF text/OCR was incomplete; the unchanged PRD was scanned in raw and Flate-decoded streams for credential signatures. The user accepted this limitation. No application tests, commit, or push.

### BOOT-00 step 6.5 — documentation workflow revisions — 2026-10-14 16:46 UTC
Suraj (B); performed; human verification pending. Updated README, AGENTS, CONTRIBUTING, task/startup/structure/stub guidance, checklists, prompts, provenance, and this log; added contributor-start and peer-review prompts. Clarified full-task planning, dependency checks, concise logs, task-wide closeout, code explanations, the one-time direct-to-main seed without separate peer review and with separate push approval, and CN-02 step 8 real-interface-or-reviewed-stub behavior.

Audit: corrected CONTRIBUTING.md to require the full ordered task plan. Checked task acceptance/tests and closeout, dependency/stub rules, review/main/push gates, and documentation links/provenance. All 28 Markdown files had 0 broken relative links/anchors; simple credential-signature search had no matches; PRD SHA-256 matched the manifest (`8ac241d1e72472a5dc77edad18579ec5d2ca3ff2ac8fd454cbc6e9627abf4ad1`). README SHA-256: `7bc42225b2189bbdc3b46705ec1dc7b9064be0498cc5282439f5981b3c26699e`. No application tests, commit, or push.

Follow-up decision: Suraj confirmed that the BOOT-00 step 7 direct-to-main commit does not require separate peer review. Updated the BOOT-00 instructions and direct-to-main references accordingly; normal peer review remains in effect for later PRs.

### BOOT-00 step 6.5 verification — 2026-10-14 16:57 UTC
Suraj (B) verified the workflow revision, audit, and no-separate-peer-review exception for the BOOT-00 direct commit. Step 7 is not started; its understanding and exact staged diff await verification. No commit or push.

### BOOT-00 step 7 — documentation seed commit — 2026-10-14
Suraj (B); performed, human verification pending. Committed the audited 31-file documentation seed on `main` as `7fb9bfed79b45614a17de1bf2f9c50dbb3981b3f` (`docs: seed Campus Marketplace workflow`). Staged scope contained only README/agent/contribution/docs/source files; PRD SHA-256 matched the manifest. `git diff --cached --check` reported Markdown trailing spaces used for intentional hard line breaks; preserved them. No application tests or push. Step 8 remains separately gated.

### BOOT-00 step 6.5 and step 7 verification — 2026-10-14
Suraj (B) verified both documentation workflow revisions and the step 7 local commit. The BOOT-00 follow-up changes separate local completion from remote publication: the seed is committed on local `main`, and `origin/main` remains at `3e81554ce3d713478d8f0979d76480e286096455`. Publication is pending separate exact-target/revision approval; it does not block PD-00 in this clone. BOOT-00 is complete locally; another clone must obtain the canonical documentation revision before using it.

### BOOT-00 separate publication — 2026-10-14
Suraj (B); approved target/revision push completed and verified. Pushed `main` to `https://github.com/exocrat/clip`; `git ls-remote origin refs/heads/main` returned `aa961ca0c3a67003d15162669c3a1a8cfb5355c0`, matching local `main`. The remote now has the canonical docs seed and BOOT-00 completion/publishing rules. No further push was made.

### PD-00 step 1 — starting repository state — 2026-10-15 07:08 UTC
Suraj (B); performed and human-verified. Created shared branch `task/pre-domain-foundation` at base `cfbf9352c03302990e6ffda09521f0a5450572d7`; repository root is `/home/suraj/src/clip`. The pre-existing unstaged change to `docs/tasks/pre-domain-task-list.md` (40 insertions, 30 deletions) remains intact; no other changed or untracked paths were present. `origin/main` was observed at the same base revision. `git diff --check` passed. No commit or push.

### PD-00 step 2 — tracked-file comparison — 2026-10-15 07:13 UTC
Suraj (B); performed and human-verified. `git ls-files` listed 32 tracked paths. Entry-point/project source docs and supplied task/checklist/prompt files are present; app/tooling/contracts/migrations/data/infra outputs and the environment README/inventory are not yet present and are assigned to later pre-domain tasks. Document 4 classifies its layout as a target and says to create only task-owned paths. Read-only comparison; no tests or resource operations.

### PD-00 step 3 — setup and tooling inventory — 2026-10-15 07:14 UTC
Suraj (B); performed and human-verified. Read-only file searches found no package/dependency manifests, CI workflow, application tests, generated outputs, migrations, data/generator files, Terraform, or project scripts. `docs/environment/commands.md` marks setup/lifecycle/check/generator/contract/Terraform commands not implemented and assigns their creators. `git status` shows only the preserved task-list edit and work-log updates; `git diff --check` passed. No tests or cloud operations.

### PD-00 step 4 — work-log status reconciliation — 2026-10-15 07:18 UTC
Suraj (B); performed and human-verified. Reconciled the BOOT-00 current revision row to `origin/main` at `cfbf9352c03302990e6ffda09521f0a5450572d7`; remote, tracking ref and branch base match. Preserved the historical publication entry at `aa961ca0c3a67003d15162669c3a1a8cfb5355c0`. Remaining task rows are not started/unaccepted, consistent with the documentation-only tracked inventory; PD-00 is in progress. Suraj confirmed the current pre-domain task-list edits are approved; the diff remains preserved and uncommitted. `git diff --check` passed.

### User-requested pre-domain workflow revision — 2026-10-16
Updated the pre-domain stream/path ownership plan, PD-03 directory-creation instruction, PD-08 dependency registry/graph, reusable and pre-domain contributor prompts, task-step audit guidance, and checklists. Removed the code-explanation section from `CONTRIBUTING.md`; the reusable task prompt retains that guidance. `git diff --check` passed. No application tests were run. No directories or marker files were created as part of this documentation edit; PD-03 now specifies the directory setup. Suraj confirmed these changes are intended.

### Follow-up clarification: tracked stream directories — 2026-10-16
Updated PD-03 to add a tracked `.gitkeep` file in each exclusive stream/integration directory root. The kickoff handoff must be merged before stream owners clone/branch; each owner removes only their assigned markers as their first action, with those deletions expected in their PR. Updated the pre-domain contributor prompt, repository-structure guidance, and checklists. No marker files were created now; they are future PD-03 outputs. `git diff --check` passed. Suraj confirmed these changes are intended.

### PD-00 step 5 — task-by-task starting-state table — 2026-10-16 06:11 UTC
Suraj (B), kickoff owner; performed and human-verified at 2026-10-16 06:25 UTC. Updated the existing Current task state table rather than adding a duplicate: recorded task status, current evidence, and unmet prerequisites; added PRE-00 as a task row; recorded the stream/integration ownership slots as unassigned; and set PD-00 to Step 5 with Step 4 verified. Suraj confirmed the current task-list and workflow revisions are intended. The initial repository inventory remains documentation-only, with implementation outputs absent as described in PD-00 Steps 2–3. `git diff --check` passed; no application tests, commits, or pushes.

### PD-00 step 6 — actual layout comparison — 2026-10-16 06:58 UTC
Suraj (B), kickoff owner; performed and human-verified at 2026-10-16 07:02 UTC. `git ls-files` returned 32 tracked paths; `rg --files --hidden -g '!.git'` also showed the untracked pre-domain contributor prompt. The current tree contains the root/project documentation and environment records, with no `apps/`, `contracts/`, `database/`, `data/`, `infra/`, `.github/`, `scripts/`, or `tests/` implementation paths or PD-03 `.gitkeep` markers. Compared with Document 4 and the pre-domain task ownership map, these are planned outputs assigned to PD-03 and later named tasks; no unexplained layout discrepancy was found, so no decision item was needed. No files outside this work log were changed by Step 6. No application tests, commits, or pushes.

### PD-00 task-wide closeout — 2026-10-16 07:02 UTC
Suraj (B), kickoff owner; complete and human-verified. Reviewed PD-00's six steps and completion condition against the Agent and Human checklist closeout items. Repository root/branch/base, current tracked and untracked paths, preserved intended documentation changes, missing task-assigned implementation outputs, task states/evidence/blockers, and the no-discrepancy result are recorded above. `git diff --check` passed. No application tests were required for this read-only inventory; no secrets, cloud resources, commits, or pushes were handled. PD-01 is the next task and requires its own full understanding report and human verification before mutation.

## Pending real integration ledger (initially empty)

An isolated implementation checkpoint may be human-verified while real subchecks remain pending under the stub guide. Task/step state stays partial/in progress; no readiness/FR/NFR completion is implied. Resume these original checkpoint IDs when the real prerequisite arrives, before further new isolated increments. Preserve resolved entries with their final evidence instead of deleting history.

| Task/step/subcheck | Execution mode | Stub paths/scenarios and contract version | Required real dependency/revision | Owner | Resume trigger | Exact real checks/expected result | Evidence/verification/state |
|---|---|---|---|---|---|---|---|
| No obligations recorded yet | Not executed | — | — | — | — | — | Planning template; no test pass |

Task reports include mode, both isolated verification and unresolved real checks. BOOT-00/PD-02 also record the actual WSL root/agent/tool facts in `docs/environment/development-workstation.md`; that file is an expected execution output, not an absent source document.
