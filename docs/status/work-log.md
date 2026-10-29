# Campus Marketplace — Shared Work Log and Checkpoints

**Canonical path:** `docs/status/work-log.md`

Read this status before work and reconcile it with the repository and active branch evidence. Keep each task's status row current after every step and human verification so the current checkpoint and execution/verification state are unambiguous. Use dated history entries for meaningful outcomes, decisions, check results, blockers, consequential human direction, and task/merge closeout. Related steps may share an entry when their outcomes belong together; routine “verified; proceed” acknowledgements and repeated navigation updates do not need separate entries. Do not add history entries solely to record a commit, push, or the act of updating this work log; Git history is the evidence for publication. Record the substantive task outcome and its checks once, and record merge or acceptance only when it changes task status. Record enough to resume and verify the work without repeating background or copying long command output. Keep check results and decisions concise, and link existing evidence where useful. New entries use exact UTC date and time; preserve the precision of historical timestamps and never infer missing times. Do not create a separate report just to duplicate the work log. Preserve useful prior facts and other contributors' entries. No implementation, cloud provisioning, PR approval, or test pass is complete until actual evidence supports it.

## Human/role roster

| Role | Actual human | Assigned work / peer |
|---|---|---|
| Initial bootstrap/foundation contributor | Suraj (B) | BOOT-00; no separate peer review for the one-time direct-to-main commit |
| A | Aditya | Identity/notifications; primary peer Rahul (D) |
| B | Suraj | Listings/images; primary peer Mohit (C) |
| C | Mohit | Search/wanted/saved; primary peer Suraj (B) |
| D | Rahul | Conversations/offers; primary peer Aditya (A) |
| Shared release/status coordinator | Aditya (A) | Current default under `CONTRIBUTING.md`; update when the role changes |
| Shared cloud operator | Aditya — current operator, explicitly named by the user (2026-10-19 UTC); existing team-roster/contact references apply | PD-16 test environment; exact action/window approvals remain required; update this assignment when responsibility changes |

## Current task state

Task status: not started / in progress / blocked / done; optional may be unselected/deferred. Step execution: not started / partial / performed / blocked. Human verification: pending / verified / correction requested. Readiness/full acceptance also requires the named reviewed main merge/checks. Record actual UTC update times and decision/approval evidence; no invented approval.

Navigation: [project docs](../README.md), [project task index](../tasks/project-task-index.md), [decisions](../decisions/README.md), [environment inventory](../environment/README.md), [evaluation evidence](../evaluation/README.md).

| Task ID | Owner role | Task status | Current checkpoint / immediate next action | Execution state | Human verification | Branch/revision/evidence | Blockers | Last UTC update |
|---|---|---|---|---|---|---|---|---|
| NEXT-00 | Suraj — requested planning coordinator | done | Planning output verified; NEXT-01 Step 1 authorized. | performed; planning only | verified by Suraj | `task/integrated-marketplace-rollout`, based on main `5e8d264`; [remaining-work plan](../tasks/remaining-project-plan.md), linked from project task index | No blocker for the accepted planning output; implementation and measured-run gates remain separate. | 2026-10-27 18:42:09 UTC |
| NEXT-01 | Suraj — requested planning coordinator; C retains EXP-01 ownership | done | Design and task-wide review verified; NEXT-02 is next. | Steps 1–9 performed | Steps 1–9 verified | Planning baseline `c869f33`; [design and approved gates](../evaluation/ecs-only-vs-ecs-lambda-task-list.md#next-01-step-8--proposed-changes-to-measurement-gates); [NEXT-07 references](../tasks/remaining-project-plan.md#experiment-protocol-reference) | No blocker for the design handoff. Real implementations, data, tools, cost anchors, project AWS identity/spend and run approvals remain NEXT-07 prerequisites. | 2026-10-28 06:24:24 UTC |
| NEXT-02 | Suraj — planning coordinator | done | Evaluation and documentation cleanup completed; test/fixture and app/infrastructure audits found no safe deletions. | Cleanup review and checks complete; its changes are included in the current commit. NEXT-02 itself changed no executable test or application code. | User accepted the cleanup and directed committing the combined changes on 2026-10-28. | `task/integrated-marketplace-rollout`; [NEXT-02 cleanup criteria](../tasks/remaining-project-plan.md); [command index](../environment/commands.md) | No cleanup blocker; documentation references and `git diff --check` passed. No tests/app checks, AWS actions, or paid runs for NEXT-02. | 2026-10-28 09:26:47 UTC |
| NEXT-03 | Suraj — planning coordinator | in progress | Step 0.5 layout fixes are implemented and locally checked; next reconcile this branch with current `origin/main`, run post-integration gates, perform the requested read-only NEXT-04 audit, then prepare the PR package. | Prior full local aggregate, supplemental migration/privacy checks, 24-group real-app sweep, responsive Chromium review and clean reseed remain recorded; Step 0.5 targeted tests: 12 passed; full frontend check: 496 passed/3 skipped, 2 files skipped; lint, both TypeScript projects and production build passed. | Initial visual inspection performed; Step 0.5 fixes await renewed desktop/phone visual review. | `task/integrated-marketplace-rollout` at `1fdca96` plus working changes; [walkthrough](../tasks/next-03-step-10-visual-checklist.md), [implementation/check report](../tasks/next-03-visual-feedback-implementation-report.md) | Current `origin/main` not yet fetched; Identity 17-migration live package still needs separate owner review; no cloud apply/deploy or hosted acceptance. | 2026-10-29 10:56:18 UTC |
| BOOT-00 | B / Suraj (initial contributor) | done | Local documentation seed verified; publication pushed and verified | performed | verified | Current `origin/main` verified at `cfbf9352c03302990e6ffda09521f0a5450572d7`; includes seed `7fb9bfed79b45614a17de1bf2f9c50dbb3981b3f` and publication record | None | 2026-10-15 07:18 UTC |
| PD-00 | Kickoff owner — Suraj (B) | done | Steps 1–6 complete; task-wide closeout reviewed | performed | verified | `task/pre-domain-foundation` at base `cfbf9352c03302990e6ffda09521f0a5450572d7`; work-log task table, initial inventory, Document 4 comparison, and `git diff --check` | None | 2026-10-16 07:02 UTC |
| PD-01 | Kickoff owner — Suraj (B) | done | Steps 1–8 and task-wide acceptance review complete; published handoff confirmed | performed | verified | `docs/architecture/foundation-traceability.md`; handoff `d29c02b` is in remote `main` at `4754e97fdaf4284e84062a926eb1864fab745036`, confirmed by `git ls-remote` | None | 2026-10-17 06:26:36 UTC |
| PD-02 | Kickoff owner — Suraj (B) | done | Steps 1–7 and task-wide acceptance review complete; published handoff confirmed | performed | verified | Repository-structure §§2–3/10; `git diff --check`; handoff `d29c02b` is in remote `main` at `4754e97fdaf4284e84062a926eb1864fab745036` | None | 2026-10-17 06:26:36 UTC |
| PD-03 | Kickoff owner — Suraj (B) | done | Steps and task-wide review complete; published handoff confirmed | performed | verified | Combined audit and handoff `d29c02b` are in remote `main` at `4754e97fdaf4284e84062a926eb1864fab745036` | None | 2026-10-17 06:26:36 UTC |
| PD-04 | Stream 1 — Aditya (A) | done | Stream handoff merged and accepted; integration consumes recorded outputs | performed | Local verification recorded; contributor confirms merged closeout | PR #2, main commit `dbafeee`; included in `e4d7551`; prior check evidence below | None for stream handoff; later integration/domain checks remain with their owning tasks. | 2026-10-18 15:54:16 UTC |
| PD-05 | Stream 1 — Aditya (A) | done | Stream handoff merged and accepted; integration consumes recorded outputs | performed | Local verification recorded; contributor confirms merged closeout | PR #2, main commit `dbafeee`; included in `e4d7551`; prior check evidence below | None for stream handoff; later integration/domain checks remain with their owning tasks. | 2026-10-18 15:54:16 UTC |
| PD-06 | Stream 1 — Aditya (A) | done | Stream handoff merged and accepted; integration consumes recorded outputs | performed (steps 1–6/local audit) | Local verification recorded; contributor confirms merged closeout | PR #2, main commit `dbafeee`; included in `e4d7551`; prior check evidence below | None for stream handoff; later integration/domain checks remain with their owning tasks. | 2026-10-18 15:54:16 UTC |
| PD-07 | Stream 2 — Suraj (B) | done | Stream handoff merged and accepted; integration consumes recorded outputs | performed | Local verification recorded; contributor confirms merged closeout | PR #3, main commit `fabe40c`; included in `e4d7551`; prior check evidence below | None for stream handoff; later integration/domain checks remain with their owning tasks. | 2026-10-18 15:54:16 UTC |
| PD-08 | Pre-domain integration owner (continuation); Mohit (Stream 3 handoff) | done | Required platform, schema, runtime and affected-owner checks verified; domain workload scope remains with domain tasks | Required checks passed; Linux ARM64 lifecycle/reset, concurrency and index evidence retained | User confirmed outstanding PD-08 gates on 2026-10-19 and specifically confirmed deferred Linux AMD64/macOS checks passed on other machine(s) on 2026-10-20 IST | `598c915`; `/tmp/clip-pd08-races-j6takuzv`; other-machine commands/raw outputs unavailable in this checkout | No PD-08 blocker by user confirmation. Service races/workload performance remain DL-00/domain work under approved scope clarification. | 2026-10-19 20:49:45 UTC |
| PD-09 | Stream 3 — Mohit (C) | done | Six local steps and final upstream/review/hosted acceptance verified; DATA-READY remains with SE-01 | Performed; merged handoff and final acceptance | User confirmed all previously pending PD-09 gates verified on 2026-10-19 | PR #5 merged at `e4d7551`, source `5046b43`; 63 data/361 combined Python tests and Black 42-file evidence recorded below | None for PD-09. Domain adapters/population/labels remain SE-01/DATA-READY. | 2026-10-19 19:58:52 UTC |
| PD-10 | Stream 1 — Aditya (A) | done | Stream handoff merged and accepted; integration consumes recorded outputs | performed (steps 1–5/local audit) | Local verification recorded; contributor confirms merged closeout | PR #2, main commit `dbafeee`; included in `e4d7551`; prior check evidence below | None for stream handoff; later integration/domain checks remain with their owning tasks. | 2026-10-18 15:54:16 UTC |
| PD-11 | Integration contributor (current session) | done | Complete per contributor confirmation; shared integration proceeds through PD-12/13 | performed (steps 1–9/local review) | Steps 1–9 locally verified; user confirms task complete | PR #6 source merged on main at `1171b4a`; user confirmation recorded 2026-10-18 | No PD-11 blocker; remaining common CI/command publication is tracked under PD-12/13 | 2026-10-18 21:50:52 UTC |
| PD-12 | Integration contributor (current session) | done | Steps 1–8 and CI policy acceptance complete | Steps 1–8/local review verified; CI policy revision implemented | User confirmed previously pending independent/upstream acceptance on 2026-10-19 | PR #7 merged at `68d9da9`; final head `61dd7674` passed hosted CI run `39280676449`; previous local evidence retained | None for PD-12 | 2026-10-19 19:58:52 UTC |
| PD-13 | Integration contributor | done | Local platform and setup handoff complete; final domain data loading remains with DATA-READY. | Steps 1–6 performed | User confirmed outstanding platform/owner checks on 2026-10-19 and reported Linux AMD64/macOS checks passed elsewhere on 2026-10-20 IST. | task/pre-domain-integration-continued at 27e983c; PR #7 merged at 68d9da9; [foundation traceability](../architecture/foundation-traceability.md) | No PD-13 blocker. Final dataset loading remains with SE-01/DATA-READY. | 2026-10-19 20:49:45 UTC |
| PD-14 | Stream 4 — Rahul (D) | done | Stream handoff merged and accepted; integration consumes recorded outputs | performed | Local verification recorded; contributor confirms merged closeout | PR #4, main commit `aa671b5`; included in `e4d7551`; prior check evidence below | No stream handoff blocker. Carry recorded credit/quota/budget/secret/recovery decisions into PD-16 plan approval; no cloud provisioning implied. | 2026-10-18 15:54:16 UTC |
| PD-15 | Stream 4 — Rahul | done | Backend/migration and independent acceptance complete | Steps 1–8 and bootstrap state migration verified | User confirmed previously pending independent acceptance on 2026-10-19 | Branch `task/pd-15-backend-handoff`; [migration result and recovery record](../../infra/terraform/bootstrap/state-migration-plan.md); state and backups remain Git-ignored and mode 0600; source merged via PR #7 at `68d9da9` | None for PD-15 | 2026-10-19 19:58:52 UTC |
| PD-16 | Integration owner | done | Operational closeout and carried foundation gates verified; last recorded compute state was off. | Operational scope performed and verified | User confirmed carried PD-08/09/12/13/15 gates on 2026-10-19. | task/pd16-image-publication at dfb61ec; [cloud inventory](../environment/cloud-inventory.md); [accepted cost treatment](../decisions/foundation-cost-review-precision.md) | No PD-16 blocker. Refresh live cloud state before any later action. | 2026-10-19 19:58:52 UTC |
| PD-17 | Integration owner (task assigned in this session) | done | Steps 1–16 and combined handoff complete | Performed; final local documentation audit passed | User confirms all work before PRE-00 is complete | PR #8 merged at `2cd83e7`; source `18c966e`; local checks and outputs recorded below; [DEC-07](../decisions/shared-foundation-dependency-staging.md) | No open PD-17 work per user confirmation. PR #8 has no submitted GitHub review; independent-review completion is user-confirmed, with no separate review artifact linked. | 2026-10-19 21:09:05 UTC |
| PD-18 | Integration owner (current branch) | done | Steps 1–7 and combined handoff complete | Performed | User confirms all work before PRE-00 is complete | PR #8 merged at `2cd83e7`; source `18c966e`; checklists, API instructions and CONTRIBUTING; prior links/fragments, metadata, PD-task coverage, registered commands and `git diff --check` passed | No open PD-18 work per user confirmation. PR #8 has no submitted GitHub review; independent-review completion is user-confirmed, with no separate review artifact linked. No tests were needed for the documentation-only steps. | 2026-10-19 21:09:05 UTC |
| PD-19 | Integration owner (current branch) | done | Steps 1–9 and combined foundation handoff complete | Steps 1–9 performed | User confirms all work before PRE-00 is complete | PR #8 merged at `2cd83e7` from head `18c966e` against base `68d9da9`; [Foundation quality gates passed](https://github.com/exocrat/clip/actions/runs/39323851584) for that exact head/base; `make test` (395 Python, 63 data, 16 web), Black, contract freshness and 10 `make check` gates passed; [handoff](foundation-handoff.md) | No open PD-19 work per user confirmation. Linux AMD64/macOS results remain user-confirmed without raw outputs. PR #8 has no submitted GitHub review; independent-review completion is user-confirmed, with no separate review artifact linked. Refresh cloud snapshot before any operation. | 2026-10-19 21:09:05 UTC |
| PRE-00 | Integration owner | done | Foundation gate audit accepted; DL-00 is unblocked | performed | verified/accepted by user | Reviewed handoff PR #8 merged to `main` at `2cd83e7`; hosted Foundation quality gates passed for head `18c966e` against base `68d9da9` (run `39323851584`); clean-checkout evidence at `0747be6`; see [PD-19 handoff](foundation-handoff.md) | None. PR #8 has no GitHub review event; independent-review completion remains user-reported without a separate artifact. | 2026-10-19 21:20:55 UTC |
| DL-00 | Shared-core/contract coordinator; all domains review | done | Steps 1–13 and task-wide audit complete; accepted and merged | Steps 1–13 performed; accepted by user | User confirmed full acceptance and merge on 2026-10-22 05:30:49 UTC | PR #9 merged to `main` at `f5576ef`; current `main` is `44cd8ff`; Step 13 check evidence is recorded below and was not rerun for this update | None for DL-00; cleanup implementation remains separately gated; real providers/integrations and crypto/worker implementation remain downstream | 2026-10-22 05:30:49 UTC |
| ID-01 | A | in progress | Step12 runtime-preparation review handoff; main PR15 integrated; Firefox fix locally human-verified | All11 local gates pass: Python1841/24skip, data94, web295/3skip, Black262, boundaries/contracts/types/build, wrapper35, PostgreSQL18.6 lifecycle and Gitleaks; Terraform4roots pass | Aditya verified Firefox sign-in and requested branch rename, main integration and PR creation; peer/affected-owner approval pending | `task/id-01-runtime-preparation`; accepted base `d7afc8b`; runtime and Firefox evidence/history below | Current hosted CI, independent/affected-owner review and exact merge approval; durable HTTPS/runtime/provider/image/Search acceptance; ID-READY incomplete | 2026-10-26 19:43:43 UTC |
| LI-01 | B | in progress | Finish the remaining Step 7 browser states and current-head Step 11 checks/reviews; prepare a progress PR without claiming LI-CORE. Steps 12–13 remain integration-gated. | Steps 1–6 and 8–10 implemented and locally checked; Step 7 partial (create/detail/edit/My Listings/gallery). | Suraj verified the multi-image edit/gallery checkpoint, seller-only selected-buyer visibility, and Step 10. No LI-01 phone-device result is claimed. | domain/listings at 6ffbe0b; focused Listings suite: 61 passed, one database-only test skipped outside the wrapper; disposable PostgreSQL workflow passed; current worktree `make check` passed 2026-10-23 (573 Python, 63 data, 42 web tests; remaining contract, type, boundary, database, safety, formatting, lint, and build checks passed). | LI-CORE not accepted. Remaining Step 7 states; Step 11 query-plan, current aggregate, and affected-owner review; native schema check; five pre-existing backend boundary findings; real Identity, Conversations, storage, and Search integration; Steps 12–13. | 2026-10-23 10:38:31 UTC |
| LI-02 | B | in progress | Step 12 demo is tested and stopped; record final evidence, then begin intake of the Search owner's PR under the review workflow. | Steps 1–11 and 1.5 verified; Step 12 ran on ECS and was tested on desktop/mobile. Read-only app checks found the synthetic listing and its S3 image; teardown is complete. | User approved and applied teardown plan `3703bb7b23405a5a23a1ac6c39fa8870e682dddf3a1a8272183f4642f8f0db81` (0 add, 1 change to LI-02 bucket CORS, 20 LI-02 deletes). Post-stop inventory confirms disposable RDS/ALB/service/host/root volume/run S3 objects/URL parameter/log streams absent; shared RDS is stopped, shared ECS cluster remains, LI-02 ASG desired 0/no instances. Two run ECR images are retained (105,624,604 bytes total) per user direction. | `task/li-02-isolated-runtime` at `f0bf6c6`; earlier 11 focused tests, Black, Python compilation, Terraform fmt/validate, CLI help and diff checks. Start plans: infrastructure `a2b8cbeaa6cc4fc2d13ff8c8696cfa133d8134280de89f719e0d6f2b91668f55`; app start `b6a3fbd4812c965a5830780f337997d13b4b362c7eb1a73f2b3e70f5946b5bd4`. Stop-path corrections are currently uncommitted in `scripts/li02-demo`, `infra/terraform/domains/listings/test/database_tasks.tf`, both LI-02 operator guides, and this work log. `git diff --check` passed; no tests rerun. Existing untracked `data/runs/` and `database/migrations.zip` remain untouched. | Compute/ingress/disposable-database charges from the demo have ended. Retained run images add about 101 MiB of ECR storage; Step 4 bucket/IAM/log group and shared VPC/NAT/ECS/RDS remain. No manual RDS snapshot remains. | 2026-10-25 09:29:55 UTC |
| SE-01 | Mohit (C); peer Suraj (B), Identity review | in progress | Formal SE-CORE/DATA-READY and final NFR acceptance remain pending. Last recorded PR15 functional/database CI passed; evidence-format rerun was pending. | Local Search work and PR15 correction recorded; no final dataset/NFR result | Mohit verified the Hybrid-default UI and requested branch publication on 2026-10-26. | Last recorded Search worktree: task/search-evidence-reduction at 864e53b; PR #11 later merged as e315c9d; [SE-01 task](../tasks/domain-task-list.md). Refresh current branch/PR/CI before relying on this snapshot. | Final SE-CORE/DATA-READY, current hosted checks, and NFR evidence remain open. | 2026-10-26 19:06:47 UTC |
| SE-02 | Mohit (C); peer Suraj (B), Identity/Conversations review | in progress | Step 8 real integration is gated; isolated Steps 1–7 were verified. | Local handoff performed; Step 8 audit recorded | Mohit verified the isolated UI and local handoff on 2026-10-25. | [SE-02 task and real gates](../tasks/domain-task-list.md); prior detailed result is recoverable from Git at f36ce3d. | Real ID-READY/LI-CORE/SE-CORE provider paths, Step 9 acceptance, current CI and independent review remain pending. | 2026-10-25 08:50:43 UTC |
| MERGE-LI-SE | Suraj (integration); Listings/Search affected owners | done | PR #11 is squash-merged; Search–Listings local merge task is complete | Steps 1–9 performed; approved PR head `2a43066` merged to `main` as `e315c9d`; final hosted CI run `40204621122` passed | Steps 3–8 verified by Suraj; user authorized squash merge of the exact PR revision on 2026-10-25 | PR #11 `https://github.com/exocrat/clip/pull/11`; source head `2a430660d25e7c14cf33d84bd78172db4ec063c7`; squash merge `e315c9df3e0e11d6e9c8d7d244d676204d3af7e8`; hosted CI `40204621122`; local merge commit `29eb6fb`; fallback branch `safety/search-pr11-pre-main-reconciliation-20261025`; stash `af9d7f5`; local checks recorded below | No blocker for the Search–Listings merge. Final dataset, formal NFR/cloud checks, and real Identity/Conversations remain later work. | 2026-10-25 15:17:46 UTC |
| CN-01 | Rahul (D) | in progress | PR17 integration merged; final CN-01/readiness/NFR obligations remain | Accepted main b09978e contains reviewed head3773931; hosted run40402518748 passed; prior local aggregate1930Python/403web and Conversations114 | Rahul verified local correction and confirmed PR merged; no additional milestone acceptance inferred | [PR17](https://github.com/exocrat/clip/pull/17), merge `b09978e91620ae3877a77c5bea8a4f12df7a8907`; [integration checkpoint](../evaluation/domain/conversations-integration.md) | Formal readiness/remaining device and security checks; CN-03 producer path and final NFR-05; full task acceptance pending | 2026-10-27 06:16:43 UTC |
| CN-02 | Rahul (D); Aditya/Suraj review | in progress | Step11 local aggregate checks passed; obtain human verification, then complete real dependency/owner review gates | 1930 Python passed/153 skipped; 94 data; 433 web/3 skipped; build/types/lint, Black 296 files, mypy, contract generation (8 artifacts), boundaries, DB lifecycle PostgreSQL18.6, Conversations harness167, DB safety35, Gitleaks8.30.1 passed | Step10 verified; Step11 local result pending Rahul verification | `task/cn-02-offers-contact-sharing`; [checkpoint](../evaluation/domain/conversations-offers.md); [browser walkthrough](../environment/conversation-browser-test.md) | Formal CN-CORE/ID-READY/LI-CORE acceptance, affected-owner review and hosted CI remain required for full CN-02 acceptance; later real-session/deployment gates remain | 2026-10-27 15:15:10 UTC |
| CN-03 | A; D producer review | not started | — | not started | pending | No domain implementation outputs in initial inventory; task definition in `docs/tasks/domain-task-list.md` | CN-CORE, ID-READY | — |
| INT-01 | A coordinator; all domain slices | not started | — | not started | pending | No integration completion evidence; task definition in `docs/tasks/domain-task-list.md` | ID-01, LI-01, LI-02, SE-01, SE-02, CN-01, CN-02, CN-03 | — |
| EXP-01 | C; Suraj coordinates NEXT-01 design | done | NEXT-01 design and gates are approved; actual topology pricing and numeric cost endpoints are NEXT-07 pre-result gates. | Design Steps 1–9 performed; no experiment run | Suraj verified NEXT-01 Steps 1–9 on 2026-10-28. | [Approved design and gates](../evaluation/ecs-only-vs-ecs-lambda-task-list.md); [NEXT-07 execution plan](../tasks/remaining-project-plan.md#experiment-protocol-reference) | Implementation, final data/tools, actual account/spend, numeric cost endpoints, and separate run approvals remain before measurement. | 2026-10-28 06:24:24 UTC |
| EXP-02 | C | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-01 | — |
| EXP-03 | B | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-02 | — |
| EXP-04 | B | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-03 | — |
| EXP-05 | C | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-04 | — |
| EXP-06 | C operator; B infra support | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-05 | — |
| EXP-07 | A; C/D calculation review | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-06 | — |
| EXP-08 | B; A cost review | not started | — | not started | pending | No experiment outputs in initial inventory; task definition in `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | EXP-07 | — |
| CLOSE-00 | A coordinator; all domain slices | not started | — | not started | pending | No final closeout outputs in initial inventory; task definition in `docs/tasks/final-closeout-task-list.md` | INT-01, EXP-08 | — |
| OPT-01 | A | unselected | — | not started | pending | No optional work selected; task definition in `docs/tasks/domain-task-list.md` | ID-READY, SE-02, CN-03, OPTIONAL-OK | — |
| OPT-02 | C | unselected | — | not started | pending | No optional work selected; task definition in `docs/tasks/domain-task-list.md` | ID-READY, LI-CORE, SE-CORE, SE-02, CN-03, OPTIONAL-OK | — |
| OPT-03 | C | unselected | — | not started | pending | No optional work selected; task definition in `docs/tasks/domain-task-list.md` | LI-02, SE-CORE, DATA-READY, OPTIONAL-OK | — |
| OPT-04 | D | unselected | Encrypted chat images defined; no implementation selected. | not started | selection pending | [optional task](../tasks/domain-task-list.md#opt-04--optional-end-to-end-encrypted-images-in-private-conversations) | CN-CORE, ID-READY, LI-02, OPTIONAL-OK | 2026-10-28 17:45:09 UTC |
| OPT-05 | C | unselected/deferred | Search relevance/inclusion improvements recorded for later; correctness bugs remain required. | not started | selection pending | [optional task](../tasks/domain-task-list.md#opt-05--optional-search-relevance-and-result-inclusion-refinement) | ID-READY, LI-CORE, SE-CORE, DATA-READY, OPTIONAL-OK | 2026-10-28 17:45:09 UTC |
| ORIGIN-RETIREMENT-BOUNDARY | Shared A/B/C/D; B/D may author | in progress | Published main retirement schema retained; Conversations uses its canonical marker/ledger, with new local guard hardening | Disposable migration lifecycle and 73 Conversations checks passed | Earlier isolated checks verified; current integration awaits verification | `task/cn-01-conversations`; main `3d6c270`; forward `20261026090000`; original branch-only SQL archived unchanged | Affected-owner review and final owner cleanup/races remain; inspect/reconcile exact persistent target before any separately approved apply. No push/shared apply/destructive cleanup authorized. | 2026-10-26 07:10:21 UTC |

## Milestones

| Milestone | State | Creating task/checkpoint | Accepted revision/PR/checks | Human verification |
|---|---|---|---|---|
| PRE-00 | accepted | PD-19 foundation gate | `main` at `2cd83e7`; PR #8 exact-head hosted CI run `39323851584`; user accepted audit 2026-10-19 21:20:55 UTC | verified/accepted by user |
| ID-READY | not accepted | ID-01 step 12 | — | pending |
| LI-CORE | not accepted | LI-01 step 11 | — | pending |
| SE-CORE | not accepted | SE-01 step 10 | — | pending |
| DATA-READY | not accepted | SE-01 steps 2/4/9 | — | pending |
| CN-CORE | not accepted | CN-01 step 10 | — | pending |
| OPTIONAL-OK | not approved | Each optional task's selection/priority plan | — | pending |

## Task summaries

The detailed chronological log remains recoverable with `git show
f36ce3d:docs/status/work-log.md`. These summaries explain meaningful outcomes;
the task table above records each current checkpoint. Older check output does
not establish current integration or NFR acceptance.

The foundation work (BOOT-00, PD-00–PD-19, PRE-00 and DL-00) is recorded
complete. See the [PD-19 handoff](foundation-handoff.md); Linux AMD64/macOS
checks were reported from other machines without raw outputs in this checkout.

### ID-01 — Identity, eligibility and runtime preparation

Local implementation and review covered account/session behavior, eligibility,
provider wiring and runtime preparation; the current row records 11 local gates
and the human-verified Firefox origin correction. The hosted demo did not pass a
full sign-in/listing/search journey or real image upload. Its temporary
zero-photo workaround was removed and the normal one-to-eight image rule
restored. ID-READY remains open pending current hosted checks, affected-owner
review, durable runtime/provider configuration and real integration. The dated
[demo postmortem](../evaluation/identity/id-01-step-12/demo-postmortem-20261026.md)
records the deployment and cleanup facts; refresh live state before future cloud
actions.

### LI-01 — Listing lifecycle and seller controls

Implemented and locally checked listing create/read/edit, availability,
seller-only buyer selection, offer-command and retirement behavior. The
multi-image edit/gallery and selected-buyer visibility were human checked; the
focused suite passed 61 tests and the disposable database workflow passed.
Step 7 remains partial, LI-CORE is not accepted, and the phone check, current
Step 11 review/schema/query checks, and real Identity, Conversations, storage
and Search integration remain open. See the
[domain task list](../tasks/domain-task-list.md).

### LI-02 — Listing image storage and upload lifecycle

The isolated image path implements private storage, bounded owner-authorized
upload/delivery, byte/type/size checks, listing confirmation and retry-safe
cleanup. Its ECS demo returned a synthetic listing with its S3 image and was
checked on desktop/mobile, then stopped with the reviewed teardown; two run
images were retained by user direction. This isolated synthetic run does not
prove signed-in integrated publication or real-user upload. See the
[domain task list](../tasks/domain-task-list.md), current LI-02 row for retained
resources, and the [demo postmortem](../evaluation/identity/id-01-step-12/demo-postmortem-20261026.md).

### MERGE-LI-SE — Search/Listings integration

PR #11 merged to main as `e315c9d`; its final hosted CI run passed. That closes
the named merge task only. It does not accept LI-CORE, SE-CORE, final data or
NFRs; see the [task row](#current-task-state).

### SE-01 — Browse and Hybrid search

PR #15 removed the website's Keyword/Hybrid selector; the product uses Hybrid,
while legacy API/URL mode handling remains. Current website search still starts
with newest-first ordering; NEXT-03 must make direct word matches rank ahead of
expanded/typo and meaning-based matches using the existing score within each
group. SE-CORE, DATA-READY and final search NFR evidence remain open.
See the [domain task list](../tasks/domain-task-list.md) and
[NEXT-03](../tasks/remaining-project-plan.md#next-03--marketplace-behavior-and-everyday-controls).

### SE-02 — Wanted Requests and saved listings

Steps 1–7 have isolated implementation and verification, including typed route
checks. Step 8 real provider integration and Step 9 acceptance remain gated on
ID-READY, LI-CORE and SE-CORE, with current checks and affected-owner review
still required. See the [domain task list](../tasks/domain-task-list.md).

### CN-01 — Private conversations and encrypted messages

PR #17 merged with hosted checks passing. The retained
[integration handoff](../evaluation/domain/conversations-integration.md)
records the local key-readiness, browser/session and recovery work and names the
remaining real-browser, owner, readiness, CN-03 and NFR-05 checks. The merge is
not full CN-01 acceptance.

### CN-02 — Offers, seller selection and contact sharing

Offer writes/reads use the Listings command boundary and Conversations provider;
the inbox groups conversations by origin, seller selection follows current
Listings state, the approved done-deal action preserves selection, and contact
sharing requires deliberate selection and confirmation. Local cross-domain
checks passed. At the last recorded update, Step 11's aggregate result awaited
Rahul's verification; real provider/owner review and hosted checks still gate
acceptance. The [CN-02 handoff](../evaluation/domain/conversations-offers.md)
has the detailed step history; key outcomes by checkpoint are below.

- **Steps 1–2:** Contract and existing storage verified; no shared database
  migration was applied.
- **Step 3:** Offer create/revise/withdraw and member-only reads use the real
  Listings and Conversations boundaries, with exact retry behavior and focused
  PostgreSQL checks.
- **Steps 4–6:** The inbox groups and filters by origin; seller selection uses
  current Listings state; the approved done-deal action preserves selection.
- **Steps 7–8:** Contact selection is deliberate and shared values are
  encrypted; cleanup and privacy checks passed locally.
- **Steps 9–10:** Combined offer/contact paths and cross-domain failure/retry
  behavior passed local checks.
- **Step 11:** The aggregate passed locally; Rahul verification, real owner and
  readiness gates, and hosted CI remained pending at the last recorded update.

### EXP-01 — ECS-only versus ECS+Lambda design (NEXT-01)

Suraj verified the nine-step design. It compares the same eligible read paths
with fair workloads. Reports include p50/p95/p99, per-request-class and per-load
results, cold/warm observations, throughput, failures, runtime/database signals,
cost and variation, including measurements that do not affect the score. No
experiment or final NFR run has occurred. NEXT-07 must freeze numeric cost-score
endpoints from the actual reviewed topology before results; the eligible result
will guide the final architecture. See the [experiment tasks](../evaluation/ecs-only-vs-ecs-lambda-task-list.md),
[guidelines](../evaluation/ecs-lambda-experiment-guidelines.md) and
[remaining-work plan](../tasks/remaining-project-plan.md).

### NEXT-00 — Remaining-work plan

The user accepted the ordered NEXT-00–10 plan and its cleanup priorities; the
[plan](../tasks/remaining-project-plan.md) is the source for sequence and gates.

### NEXT-02 — Repository cleanup

Evaluation cleanup restored the CN-01, CN-02 and Identity-demo handoffs used by
later tasks. Work-log history is summarized by task; startup instructions use
conditional WSL/test-double guidance. The command index fell from 1,946 to 247
lines. The live FR/NFR ownership map remains, while its completed foundation
inventories were removed (159 to 49 lines); the dependency graph now covers
PRE-00 onward (249 to 134 lines). The task index fell from 182 to 140 lines.

Completed BOOT/PD procedures, the one-time source-bundle manifest and consistency
report were removed from the checkout after checking NEXT-03–CLOSE-00 references;
the PRD, accepted foundation handoff, task summaries, current runbooks and active
decisions remain. The source record now keeps the PRD checksum and current source
hierarchy (67 to 14 lines). Removing the bundle also retired its exact Gitleaks
hash exception; other allowlists remain. The retained FR/NFR map, current
runbooks, experiment guides, active handoffs and decision records serve upcoming
work. A check found no Markdown links to missing local targets across 871 links,
verified the changed anchor, confirmed the PRD SHA-256 and passed
`git diff --check`. No tests, app changes, AWS actions or paid runs were done.
The test/fixture category has 221 tracked paths, 1,882,802 bytes and 46,228
text lines. Its 66-byte decrease comes from the Search test README edit; no
executable test or fixture code changed. The shared fixture package and opt-in
database, browser and local-image checks protect distinct future gates, so no
safe test deletion was evident.
The app/infrastructure inventory covered 100 API files, 79 web files, 28
Terraform code files and 23 database migrations. It found no TODO/FIXME markers
or empty implementation modules; declaration-only public interfaces and
fail-closed error handling serve current boundaries. No application or
infrastructure source reduction was clearly safe, so those files remain intact.
See the [NEXT-02 plan](../tasks/remaining-project-plan.md).

### NEXT-03 — Category catalogue and dataset alignment

Suraj verified nine categories, their retained/new stable codes, the balanced
1,000-listing distribution (112 mobile-phone listings; 111 in each other
category), and five proposed controlled item/synonym examples per category. A
forward migration updates the Electronics and Home appliances labels and adds
Sports & fitness without reclassifying existing listings or wanted requests.
The listing contract, database schema reference, category decision,
reference-dataset recipe and search preview fixtures now agree. Generated API
schemas need no change because category codes remain strings. `git diff --check`
passed. A dbmate marker issue found on the first isolated run was fixed; the
disposable PostgreSQL migration/rollback/reapply check then passed on PostgreSQL
18.6. Python syntax checks passed for eight changed files. At Suraj's direction,
the full Python test suite is deferred until the end of NEXT-03; install the
documented pinned tools then if they are still unavailable. No shared/cloud
database apply occurred. Identity's reviewed 17-migration package remains frozen
and needs a separate owner review before its live migration gate. NEXT-02 cleanup
is accepted and closed; NEXT-03 Step 2 is next.

On 2026-10-28, Suraj verified Step 2's multi-select behavior: category and
condition values are independent choices, with OR within each filter and no
condition hierarchy. The plan now includes multi-select origin and partner
filters in the Conversations inbox while retaining single-choice controls where
the existing “all” choice covers the union or a record stores one value. Suraj
also added public Wanted Request search/discovery and a Step 9 human visual
checklist with synthetic sample data as a fallback. The detailed outputs and
acceptance conditions are in the [NEXT-03 plan](../tasks/remaining-project-plan.md#next-03--marketplace-behavior-and-everyday-controls).
Step 2 implementation uses repeated query parameters for sale category and
condition, and for conversation origin and partner IDs. UI filters apply as one
draft in the inbox; Sale Discovery keeps applied filters in browser history and
resets pagination when filter changes are submitted. SQL uses independent
`ANY` predicates, and the HTTP test preview handles repeated query values. The
single-choice catalogue assignments, conversation view/type/status/sort,
negotiability, and page size remain as specified in the plan. Relevant tests
were updated but not run. Source contracts are updated; generated contracts and
the final verification remain pending until pinned tools are installed at the
end of NEXT-03. No shared/cloud database apply occurred.

Suraj verified the Step 2 implementation on 2026-10-28 and clarified the
negotiability requirement: remove it from the search filter in Step 3 while
keeping the state visible on discovery cards and detail pages. The current card
shows the state inline beside condition; the approved task text does not yet
specify a dedicated badge style. Step 2's generated contract files and tests
remain deferred to NEXT-03 final verification. Step 3 is the next review gate;
no Step 3 changes have started.

Suraj clarified that the website must not let users filter listings by
negotiability, while the API field may remain for compatibility/future use.
They asked whether a short card marker would improve visibility. Step 3's plan
now records retaining the API field and considering a visible badge; I
recommended the full word “Negotiable” rather than an unexplained “N”. The
specific card treatment and complete Step 3 scope await Suraj's verification.

Suraj verified Step 3 on 2026-10-28, keeping the negotiability filter out of
the website while retaining the API field, and chose readable status badges.
The Search UI now defaults text searches to the existing Hybrid relevance
ordering, hides relevance as a selectable sort, preserves explicit newest/price
choices, and defaults empty browsing to newest-first. Listing cards display a
full-word “Negotiable” or “Fixed price” badge; the detail page retains its
existing status. Legacy website negotiability query values are ignored and
omitted from API calls. An explicit sort remains while filters refine the same
search; editing its query text resets to automatic match ordering. Relevant
tests were updated but not run; `git diff --check` passed. Generated Step 2
contracts and final verification remain pending. No database migration was
applied.

Suraj then verified that **Best Match** should remain a selectable sort, not
only the automatic state, so users can restore it after choosing Newest or a
price order. The sort control now uses that title-cased label for the existing
`relevance` API sort; text searches default to it, and empty browsing stays
newest-first. The exact label and behavior are recorded in the task plan and
Search contract.

Suraj verified the Step 3 implementation on 2026-10-28, including the selectable
**Best Match** sort. Step 4 is next. Its existing photo picker keeps preview
object URLs private to Listings, and Search's sale card is not a public Search
entry point; the Step 4 plan must settle a public preview composition/data
boundary before implementation.

For Step 4, Suraj requires the browse card and draft preview to share one
Search-owned renderer so later browse-card presentation changes automatically
appear in the preview. The plan now specifies that shared renderer and a public
feature entry point with draft/photo data passed through route composition,
without duplicate card markup/styles or a direct private Listings-to-Search
dependency. Suraj verified Step 4 on 2026-10-28. The create form now exposes a
non-publishing draft preview through the route's public Search entry point;
browse and preview share the same sale-card renderer, and the first local photo
preview follows the selected image order. Photo counts and upload/failure
statuses use plain wording in create/edit flows. The relevant preview test was
updated but not run under NEXT-03's deferred-test rule; `git diff --check`
passed. Step 5 is next: review the existing Wanted Request title-only matching
flow and its failure/submission behavior; the reviewed panel is already
implemented and currently reachable under My Listings → Wanted Requests →
Create wanted request. Suraj verified the review and asked that Step 9 provide
local synthetic data or exact instructions that produce known positive sale
listing matches as well as no-match/failure checks. The plan now requires this
data and setup guidance. Step 6 is next. Generated Step 2 contracts and final
verification remain pending. No shared/cloud database apply occurred.

On 2026-10-28, Suraj verified the Step 6 Wanted Request discovery implementation
and asked for programmatic evidence before proceeding. The environment has no
pinned Node/npm or uv/pytest executables, Python's pytest module is absent, and
the Docker daemon socket denies access, so the focused web/API/PostgreSQL tests
could not run here. `python3 -m py_compile` passed for the changed Wanted API,
contract and database-test modules; `git diff --check` passed. Behavioral test
results and generated contracts remain pending for NEXT-03's pinned-tool final
verification. Suraj also directed that an optional cost/original-price field be
added before the previous Step 9 walkthrough. The plan now inserts this as Step
9 and moves the comprehensive local checklist to Step 10. Existing Listings
currently require an asking price and define no separate reference/purchase
price field in the UI/schema; the new step first resolves whether the optional
field means public original retail/reference price or seller purchase cost, and
where the approved value appears. No field implementation or database change
has started.

After Suraj authorized installation, the existing pinned Node 24.22.0/npm
11.19.1 and uv 0.10.7 toolchain was found outside PATH and used; `npm ci` and
`uv sync --locked` installed project dependencies locally. The focused web
Wanted discovery query/API tests passed (55 tests). The first disposable
PostgreSQL run found five related Search failures because the generated runtime
ListingQuery still represented category/condition as nullable scalars; the
validator received `None` where the new multi-select contract expects lists.
Regenerating the eight registered outputs from canonical contract sources
resolved those failures. The rerun of
`uv run --locked python scripts/check_database.py --listings-store` passed its
full disposable migration/reapply and Listings/Search adapter workflow: 22
passed, 3 skipped, including `test_wanted_discovery_postgres.py`. Contract
freshness passed for all eight outputs, and pinned Black reported all ten
relevant Python files unchanged after formatting. The database runner now
includes the new Wanted discovery SQL test. Suraj clarified the added price
field: seller-entered, buyer-visible, not necessarily MRP; the plan names it
**Original price**, treats it as seller-provided, and leaves exact display
locations to Step 9. No listing field or migration had been implemented at that planning point.

On 2026-10-28, Suraj verified the Steps 7–9 scopes together. Step 7 now shows Unicode-aware title/description/pickup-area counters and consistent input validation, and sets an inclusive ₹1,00,00,000 cap for listing prices, Original price, Wanted budgets, and their filters. Step 8 adds a top-level **New Wanted Request** link in discovery and the header that opens the existing form directly; the Conversations inbox still groups by origin, and its seller-only Mark as done deal action follows the approved availability command. Step 9 adds optional, positive, seller-provided Original price across create/edit, API/contracts/storage, public cards, detail, My Listings, and the shared preview. Blank stays absent; no discount is inferred. Forward migration `20261028120000_sale_original_price_and_marketplace_amount_cap.sql` is authored but has not been applied to any shared/cloud database. Focused web checks passed (186 tests across 16 files), TypeScript checks passed, all eight generated contract artifacts are current, and the disposable PostgreSQL Listings/Search workflow passed (22 passed, 3 skipped) with migration clean/head/repeat, seven SQL smokes, rollback, and reapply checks. Targeted Conversations inbox/done-deal checks also passed (25 tests across four files). Step 10's three-part order was directed by Suraj on 2026-10-28: Part 1 commits this work, runs the full local quality/test aggregate, fixes failures, and reports the Part 2 action inventory; Part 2 performs the isolated programmatic action sweep and prepares the visual checklist; Part 3 creates the final data for the user's visual inspection. Notifications are excluded. No Part 2 actions or Part 3 data are to be run during Part 1. The pinned 17-migration Identity review package remains unchanged.

On 2026-10-28, Step 10 Part 1 completed on `task/integrated-marketplace-rollout` at `d3ccfff`. The first aggregate runs surfaced stale amount/filter assertions, two pruned Identity review inputs still required by the runner/readiness tests, an outdated local-search response-shape check for `original_price_paise`, and web lint findings; the test fixtures, load-response validator, and frontend lint issues were corrected. The 17 migration files still match the manifest hashes; the restored review-candidate record states `review_candidate_not_executable` and does not grant live approval. Final `make check` passed: Black 297 files unchanged; Python 1932 passed/154 skipped; data 94 passed; boundaries 0 violations; eight generated contract artifacts current; mypy passed; web lint passed, 464 passed/3 skipped across 37 files (2 skipped), TypeScript passed, production build passed; database safety 35 cases passed; disposable PostgreSQL 18.6 migration/store checks passed (combined clean/head/repeat, seven SQL smokes, Identity upgrade/atomicity/rollback, protected retirement rollback, full clean reapply); Conversations fresh-PostgreSQL suite 167 passed; Gitleaks 8.30.1 passed. Vite emitted its existing informational bundle-size warning. No Part 2 actions or Part 3 data were run; notifications remain excluded.

On 2026-10-28, Step 10 Part 2 exercised the real local Hybrid API with a synthetic bicycle listing: exact-title search and the meaning-related `wheeled vehicle` query both returned it; sale and Wanted no-match queries returned empty success pages, and an unsupported mode failed safely. Direct HTTP checks also covered sale multi-category/multi-condition OR filters, price sorting, detail/edit and Original price, availability hide/reopen, Wanted create/search/category+budget filters/edit/close/reopen/draft match, saved-list create/read/remove/retry, and numbered pagination. Part 1's passing suites additionally cover image progress and retry states, seller buyer-selection UI behavior, and inbox multi-select controls; the disposable Listings PostgreSQL workflow covers SQL-level buyer selection and image replacement/removal. The disposable Conversations runner passed 167 tests; the signed Identity/Listing/Conversation integration file passed 8 tests, exercising real local session/CSRF and domain SQL with explicit synthetic provider ports. No live Microsoft, email, or S3 provider, notifications, physical-phone URL, cloud change or paid action is claimed. The browser test database was removed after the sweep. The [visual checklist](../tasks/next-03-step-10-visual-checklist.md) records that the conversation presentation demo omits origin/partner multi-select controls and the local preview does not connect seller selection/Mark as done deal. Those visible paths remain open for Part 3 design and the user's inspection; Part 3 data has not been generated.


### NEXT-03 Step 10 — complete programmatic sweep and inspection handoff

**2026-10-28 16:19:31 UTC — Suraj’s authorized combined execution; visual verification pending.**
The user directed one uninterrupted execution through a running inspection
environment, synthetic data and instructions. The target remains an essentially
complete app at `https://clip-iisc.site` after NEXT-04 deployment/configuration,
excluding Notifications for this increment. Inspection found that the normal
conversation routes already connect inbox filters, seller selection and done-deal
actions; the old separate presentation demo had omitted them. A missing connected
amount-only offer form was completed in `pages/ConversationOffers.tsx`, mounted
from `ScaffoldPages.tsx` through public Listings submit/withdraw exports. Buyers
can submit/revise/withdraw/resubmit with revision checks and identical-operation
retry after uncertain outcomes; sellers have read access; Wanted has no offers.
Obsolete conversation placeholders were removed. Four new offer tests passed.
The frontend collaboration map records the completed Suraj composition edit and
required later owner/independent review.

`scripts/marketplace_inspection.py` now uses the normal application factory,
real local cookie/CSRF Identity and all domain stores, pinned real Hybrid
helper/dispatcher/model and actual photo bytes. Only external signing/mail/storage
ports are synthetic. Its test-only loopback account switch and file downloads
are absent from deployed startup. It seeds five accounts, 28 photo-backed sales
(27 available), 26 Wanted Requests and 54 conversations. Twenty-one action groups
passed, including exact/semantic bicycle search, all 28 real vector generations
current, filters/sorts/pagination, photo upload/confirm/cancel/retry/delivery/edit/
removal, Original price, Wanted lifecycle/draft matches, saves, actual cross-domain
buyer selection, offers and temporary-account capability denials. Signed
message/read/contact flows and the real SDK are covered by the aggregate
integration/crypto suites; no fake message keys were seeded into inspection data.
The live HTTP smoke also passed real actor cookies, paginated inbox, normal
conversation/contact SPA routes, compiled seller/offer controls and bounded
sample downloads. Test sessions used during earlier sweeps were cleaned up.

`make check` passed: Python 1932 passed/154 skipped; data 94 passed; web
468 passed/3 skipped across 38 passed/two skipped files; eight contract artifacts
current; boundary/mypy/lint/type/build gates passed; database safety 35 passed;
disposable PostgreSQL18.6 clean/head/repeat/seven SQL smokes, Identity
upgrade/atomicity/rollback, protected retirement rollback and clean reapply passed;
Conversations 167 passed; Gitleaks8.30.1 passed. The new launcher tests were added
after aggregate collection and run separately: two passed. Final Black checked
299 unchanged files. The extra `scripts/check_database.py --listings-store`
workflow passed 22 tests/three explicitly gated native/model/calibration probes
skipped and repeated its full migration/rollback/reapply checks. Ordinary web
aggregate skips its opt-in HTTP fixtures; their separate integration and the
actual inspection sweep are recorded without relabelling skips. A sandbox-only
formatter/process and Docker scan permission failure was rerun successfully with
local process/Docker access. Final secret scan and `git diff --check` passed.
Vite’s existing bundle-size notice remains informational.

The [walkthrough](../tasks/next-03-step-10-visual-checklist.md) gives exact actor,
record, sample-download, desktop/responsive, two-profile encrypted-chat, failure/
retry and cleanup instructions. The prepared session is running at
`http://127.0.0.1:5174/__inspection`, PID2245336; `kill -INT 2245336` cleans up
only that launcher’s disposable DB and temporary files. Suraj’s human inspection
is the next action; NEXT-03 remains open. No cloud/shared DB apply, live provider
call, paid action or Notifications work occurred. Identity’s pinned17-migration
review package remains unchanged and its live review gate stays separate.


**2026-10-28 17:45:09 UTC — NEXT-03 visual feedback planning.** Suraj reported
shared multi-select/card/form/header issues, missing detail Original price, Wanted
match placement, browse/owner shortcuts, conversation naming/grouping/navigation,
blocked seller encryption/contacts/offers and suspected stale selection after
reopening (selection was initially accessible). All feedback and proposed product
decisions are preserved in the linked grouped correction plan. No application
corrections or unattended execution started. Actual PostgreSQL verification reran
`python scripts/check_database.py --listings-store`: 22 passed/three gated skips
and full migration/rollback/reapply passed. Hybrid has an original/expanded OR
semantic>=0.35 exclusion predicate shared by alternate sorts; the native SQL
fixture excludes a nonlexical0.315 result while sorting the same eligible set.
Exact causes of each broad preview result were not measured; do not attribute
them solely to Inspection or claim exact-word absence guarantees exclusion.
Display name exists, username does not; public participant identity remains a
pending design decision. OPT-04 encrypted chat images and OPT-05 relevance tuning
were added with owners, prerequisites, contracts/security/cost/verification and
acceptance steps, and index/scheduling links; both remain unselected. No cloud,
paid action, live provider change or implementation occurred in this increment.


**2026-10-28 17:58:38 UTC — NEXT-03 decision clarification.** Suraj clarified
that there is no Remove listing feature: retain unavailable/reopen only, without
delete/archive. Encryption onboarding belongs at first sign-in, not every login;
explicit missing-device-key recovery is still necessary. Other recommendations
were accepted. Inspection confirms display_name is stored/read and shown when
present, with an existing server profile-update operation but no frontend
collector/editor or username. First-setup name entry and later profile/contact
editing are included. Duplicate-name handling remains the one identity choice
(display names alone versus a new unique public handle); tentative discussion of
public email is not authorization to disclose private addresses. Application
corrections await that decision.


**2026-10-28 18:05:05 UTC — NEXT-03 handle decision and complete feedback audit.**
Suraj chose Handle only, reusing `display_name`: required first-setup collection,
later editing, trimmed3–30 ASCII letters/digits/underscores, case-insensitive
database-enforced uniqueness with safe legacy-account transition and preserved
IDs/references. No second display-name/username field or public-email disclosure
is selected. All D1–D7 decisions are settled. A documentation-only audit mapped
every original feedback item, the My Listings addition and subsequent decisions
to the grouped plan; stale pending removal/display-name/Saved/selection text was
corrected. Offline-peer messaging and group-level selected-buyer/offer tracking
were made explicit. AGENTS.md and the task plan now require reopening the feedback
plan before every implementation step, context recovery and completion report.
No new product decision was found necessary by this coverage audit; unforeseen
implementation/security issues remain subject to the recorded safe handling rule.
`git diff --check` passed; no tests needed for these documentation changes.
Application changes have not started: Suraj explicitly requested waiting.


### NEXT-03 — Conversations-first functional repair and human demo

**2026-10-28 18:41:09 UTC — execution performed, human verification pending.** Suraj
authorized Conversations functional repair first, a demo while he remains
available, then commit after verification; handle/schema work and the broader
visual/grouped-inbox batch remain afterward. The feedback plan and AGENTS.md
record this priority and the mandatory per-step consultation rule. No current
public handle values, uniqueness schema or real email verification code changed.

Clean separate Chromium profiles could initialize the original thread, but the
SDK’s default single IndexedDB identity plus the account-owner check could reject
switching demo accounts or regenerated IDs. `accountStore.ts`/`relay.ts` now open
account-specific stores and preserve matching legacy keys/history; an explicitly
guarded SDK13.0.0 adapter sets database/lock identity before initialization,
without changing global IndexedDB or silently replacing keys. Repeat the actual
browser checks on SDK upgrades; this compatibility adapter needs peer review.
`ConversationKeySetup.tsx`, its public export and `AppShell.tsx` provide first-
device consent/publication before normal marketplace use, quiet returning resume
and explicit missing-key/error states. The later handle-onboarding batch must
finish the full profile flow and refine access to browsing while setup is pending.

Actual-browser testing exposed a separate reload defect: received text bypassed
verified local history and attempted SDK replay decryption. `ConversationPages.tsx`
now restores locally authenticated text/contact history only with matching entry
ID/sequence/author/timestamp/key versions, and honours retention tombstones first.
It also shows seller selected-offer context and thread origin links.
`ConversationThread.tsx` explains offline-peer readiness;
`ConversationContactPreparation.tsx` adds missing-contact setup navigation;
`ScaffoldPages.tsx` validates the conversation return target;
`ConversationInbox.tsx` adds group origin links.

`ConversationListingSelection.tsx` supports private set/change/clear, including
unavailable non-retired origins. `ConversationListingDoneDeal.tsx` and selection
refresh visible/focused state without discarding uncertain-write intents, so an
externally reopened listing is reflected without remounting. The seller group
shows selected tracking/current offer and a thread shortcut. Listings
`service.py`/`postgres_store.py` preserve availability on selection and retain
owner/participant/revision/idempotency checks. Forward migration
`20261028181500_private_buyer_selection.sql` relaxes only the existing selection
trigger’s availability prerequisite; the canonical offer decision documents
Suraj’s superseding semantics. Database/native/Conversations check runners and
database README now expect this new head; the frozen Identity17 package is intact.

Tests added/updated: `conversation-key-setup.test.tsx` (first consent/quiet resume/
retry), `conversations-cached-display.test.ts` (reload binding/tombstones),
`conversations-done-deal.test.tsx` (reopen on focus),
`conversations-selection.test.tsx` and `conversation-composition.test.tsx`
(private tracking), `conversations-ui.test.ts` (readiness copy), Listings
`test_postgres_store.py` and `test_conversation_contact_share_cleanup.py`
(actual independent selection/availability with offers and encrypted shares).
`marketplace_inspection.py` adds an isolated5175 debug port, forces both app pools
to its own DB and disables external storage; its actual API sweep also selects/
clears while unavailable and leaves fresh human accounts without fake message keys.

Real-browser regression used Playwright1.58.0’s cached driver with
Chromium153.0.8010.12 and actual SDK13.0.0/IndexedDB, real SQL/cookie/CSRF APIs,
and explicit synthetic external providers. It passed first-device publication,
both-way messages (including recipient outside the thread), selected-field
encrypted contact delivery, offer revision/read/withdrawal, selection preserving
availability, seller selected-offer context, done-deal plus live reopen, account
switch isolation, quiet return and message history after reload. Disposable test
fixtures were removed; fresh human demo is running on5174, PID2346525.
Browser evidence: `/tmp/clip-conversation-functional.log`. No human click result
is claimed; remaining naming/grouping/visual work is not marked complete.

Final `make check` exited0: Black299 unchanged; Python1934 passed/154 skipped;
data94 passed; web475 passed/3 skipped across40 passed/two skipped files; eight
contracts current; boundaries/mypy/lint/type/build passed; DB safety35 passed;
PostgreSQL18.6 migration clean/head/repeat/seven smokes, Identity upgrade/atomicity/
rollback, protected retirement rollback/full clean reapply passed; Conversations
167 passed; Gitleaks8.30.1 passed. The separate store workflow passed22/three gated
skips plus its full migration workflow. Initial aggregate failures were stale
runner-head and old selection-closes-listing assertions; these were corrected,
affected checks rerun, then the entire aggregate rerun successfully. The existing
Vite bundle-size notice remains informational. Final formatting/secret/diff checks
passed. No cloud/provider/paid operation or commit occurred. Next: Suraj tests the
focused checklist, verifies/corrects, then the authorized commit checkpoint.


**2026-10-28 19:11:58 UTC — NEXT-03 follow-up plan update; documentation only.**
Suraj requested recording the new chat screenshots, keyboard/unread behaviour,
simplified modes/controls and deployment discussion, while explicitly deferring
cloud work. The feedback plan now includes bounded onboarding/chat form margins,
offer-action gaps and contact checkbox rows; Enter send/Shift+Enter newline with
IME safeguards; a navigation unread-message count, stable first-unread divider/
opening window and display-based acknowledgements. Buying/Selling mode buttons
replace primary origin/participation selectors, with correct sale/Wanted intent
mapping, compact Item/Person grouping, visible origin/partner multi-selects removed
and only useful controls behind collapsed Sort & Filter. Recent activity is the
existing default; title/handle search and an Unread filter are explicitly absent
and unselected, correcting the earlier assistant description. Group, within-group
and message-history pagination are distinguished. These revisions supersede the
earlier Sale/Wanted primary-tab proposal without dropping recognizable origin
context or selected-buyer tracking. A follow-up coverage table preserves each item.

Deferred sectionG records the read-only deployment audit: normal app composition,
hosted real test-Identity path, application production/recipient restrictions,
frontend Microsoft build flag, existing Hybrid image/pipeline, HTTPS/proxy trust,
DB migration/grants and origin-scoped browser-key requirements. Suraj reports SES
production access granted today; live AWS state was not verified and no policy
was changed. NEXT-04 retains cloud/configuration/promotion verification and exact
action gates. No application, infrastructure or provider files changed; no tests
needed for this documentation update. `git diff --check` passed.

**2026-10-28 19:24:42 UTC — NEXT-03 feedback batch released.** Suraj confirms the
committed Conversations functional demo was visually completed and authorizes the
remaining in-scope correction plan as one uninterrupted batch. Exclusions are
Buying/Selling conversation modes, unread counts and first-unread positioning,
unique Handle collection/uniqueness/database migration, cloud work, and unselected
optional OPT-04/OPT-05. The visual feedback plan now has a per-task status ledger;
each task must be checked against it and its status updated before proceeding.
This confirmation supersedes the older “demo verification pending” checkpoint.

**2026-10-28 19:28:33 UTC — A2 shared sale-card consistency.** My Listings now
uses the Search public `SaleListingCard` through the ScaffoldPages composition
callback, retaining owner Edit and availability actions. Wanted draft matches now
render the same shared card as Discover, Saved and the listing preview. Web
typecheck passed; targeted tests passed (14 across `identity-marketplace-state`
and `discovery-controls`). Full-card navigation is tracked separately in A4.

**2026-10-28 19:29:42 UTC — A3 Wanted card hierarchy.** Wanted cards now place
their budget (including “Budget not stated”) after the title, use the neutral
surface/category treatment, and clamp long descriptions on browse/owner cards.
Wanted detail keeps its full description. `git diff --check` passed; compiled
browser presentation and viewport review remain part of batch closeout.

**2026-10-28 19:31:22 UTC — A4 card and group navigation.** Sale and Wanted
title links now provide a full-card pointer target via an overlay while their
separate action regions remain interactive. Conversation origin groups similarly
target origin details; conversation row buttons still open individual threads.
Added a regression check for group-detail versus thread navigation. Focused tests
passed (12 across Conversations inbox, sale-card and Wanted controls);
`git diff --check` passed. Actual pointer/keyboard behavior remains in final
browser review.

**2026-10-28 19:33:26 UTC — A5 bounded forms and action spacing.** Wanted
creation now sits in a bounded card, first-device key setup has centered margins
and a clear consent/action row, the Offer panel has a sized amount field and
spaced/wrapping controls, and contact choices/actions now have readable rows and
gaps. TypeScript checks passed; targeted KeySetup/Offer/Contact UI tests passed
(12 across three files). `git diff --check` passed; mobile/desktop viewport review
remains for batch closeout.

**2026-10-28 19:26:33 UTC — A1 multi-select layout.** The nested label rules in
sale and Wanted discovery were overriding the shared checkbox-row flex layout.
The feature selectors now exclude dropdown option labels, preserve a horizontal
checkbox/text row, use a 44px minimum target, and constrain the options panel to
the viewport height/width. `git diff --check` passed; final browser viewport
inspection is included in batch closeout.

**2026-10-28 19:35:36 UTC — A6 shell navigation.** The shell now shows only
product navigation, with Sign in visible for anonymous users and sale creation
restricted to eligible regular accounts. Account/sign-out controls sit in the
top-right header row. Regression tests cover anonymous, regular and temporary
sessions (3 passed); both application and test TypeScript checks passed.
`git diff --check` passed; responsive browser review remains at batch closeout.

**2026-10-28 19:37:00 UTC — A7 sale discovery creation action.** The shared
route composition now supplies a New Listing action to sale discovery only for
an eligible regular account; the public Search component renders it above the
filters, parallel to New Wanted Request. Search-controls regression tests passed
(5), and application/test typecheck passed. An initial direct Biome invocation
from the repository root hit the repo's nested-config guard; use the repository
lint script (which runs in `apps/web`) for final lint verification. Browser
visibility and responsive review remain for batch closeout.

**2026-10-28 19:37:41 UTC — A9 modest Conversations presentation.** The thread is
now centered within a readable width, messages sit in a distinct scroll panel,
message bubbles and timestamps have clearer separation, and the composer is a
separate responsive panel. Key setup, contact and offer layout were already
corrected under A5. TypeScript checks passed; 12 existing KeySetup/Offer/Contact
tests passed. This repository has no focused ConversationThread test file;
mobile/desktop browser review remains for batch closeout.

**2026-10-28 19:38:26 UTC — A10 system dark appearance.** Added a compact
`prefers-color-scheme: dark` token override in `tokens.css` for text, surfaces,
borders, primary/focus and disabled controls, including native form-control
color-scheme. TypeScript checks and `git diff --check` passed. Actual page contrast
and visual behavior remain in the final browser review.

**2026-10-28 19:41:22 UTC — B2 browse actions.** Sale discovery now composes
compact Save/Unsave and Message seller controls inside each shared sale card;
anonymous visitors get sign-in links and temporary accounts cannot start seller
conversations. Wanted cards now offer Contact requester using the Search public
action and one page-scoped session read; the server remains authoritative and no
author identity/contact value is exposed. Focused Search/Wanted tests passed
(48), TypeScript checks passed, and `git diff --check` passed. Browser action and
phone review remain at batch closeout.

**2026-10-28 19:43:00 UTC — B3 sale detail owner controls.** Added an owner-only
detail action component that checks the current eligible session against the
private Listings management endpoint before showing Edit or Mark unavailable/
Mark available. Availability changes use the current revision and a stable
operation ID; successful changes refresh the public detail and owner projection,
while conflicts require reloading current state. TypeScript checks passed and
the listing-conversation composition tests passed (4); `git diff --check` passed.
Browser owner/non-owner review remains for batch closeout.

**2026-10-28 19:44:07 UTC — B4 Wanted detail owner controls.** Wanted detail
now checks its request ID against the signed-in caller's private Wanted pages
before exposing inline Edit and Mark unavailable/Reopen controls. The existing
revision-guarded editor and availability operation are reused; successful writes
refresh both public detail and private owner state. Anonymous/non-owner details
show no owner controls. TypeScript checks passed; 53 focused Wanted and Identity
tests passed; `git diff --check` passed. Browser ownership review remains pending.

**2026-10-28 19:45:40 UTC — B5 Wanted draft matches before publish.** The
Possible sale matches panel now sits inside the Wanted editor form before its
Publish/Save action, so draft matches are visible before submission. It still
uses the shared Search-owned sale card, stays attached to the unsaved title, and
retains the existing non-blocking failure/retry behavior. Added a rendering-order
regression test. TypeScript checks passed; 44 focused Wanted tests passed;
`git diff --check` passed. Browser layout/error-state review remains pending.

**2026-10-28 19:48:42 UTC — D3 simplify inbox controls.** Removed the visible
participation/type selectors, origin/partner multi-selects and global offer
status/range/sort controls. Recent activity remains the default; API and URL
query compatibility remains, with a collapsed Sort & Filter disclosure that
can clear legacy saved filters. Updated inbox rendering tests: 41 Conversations
tests passed, TypeScript checks passed, and `git diff --check` passed. Browser
phone/desktop inspection remains for batch closeout.

**2026-10-28 19:51:04 UTC — D5 Enter-to-send.** An unmodified Enter now sends
through the same pending/encrypted callback as the visible Send button; Shift+
Enter keeps a newline. IME composition, repeated key events, unready encryption,
blank drafts and concurrent sends are ignored. The lock prevents rapid duplicate
submits, and a failed send retries with its original operation ID. Added seven
interaction tests for these safeguards and stable retry. TypeScript checks and
`git diff --check` passed. Phone keyboard/browser inspection remains pending.

**2026-10-28 19:54:28 UTC — C4 peer account-class contract audit.** The reviewed
`ConversationSummary` and its HTTP response contain the counterparty UUID only;
Identity currently exposes no reviewed participant-profile/account-class
projection. A browser-side guess or direct query against Identity-owned tables
would cross the recorded domain boundary, so the temporary-account marker stays
pending until that public projection is reviewed. No email or raw ID is used as
a substitute.

**2026-10-28 19:54:28 UTC — D1 recognizable conversation origins.** Conversation
groups now resolve public listing/Wanted titles and prices, show a sale thumbnail
when present, and keep origin-detail navigation while removing displayed listing,
request, conversation and participant UUIDs. Sale detail no longer prints its
listing UUID. The display is wired only through public Listings/Search exports at
the ScaffoldPages composition boundary. TypeScript passed; 51 focused
Conversations, Listings and Wanted tests passed; `git diff --check` passed.
Participant Handle is excluded and the Temporary badge remains pending under C4.
Browser context/card review remains for batch closeout.

**2026-10-28 20:11:16 UTC — NEXT-03 full local verification.** Installed pinned
uv 0.10.7 and the locked Python test environment under `/tmp`, leaving the clone's
`.venv` untouched. `make check` passed: Python 1,934 passed/154 skipped; data 94
passed; web 488 passed/3 skipped across 42 passing and two skipped files; 137
files linted; application/test TypeScript and production build passed; boundary,
8 generated-contract, and 2 contract-type checks passed; 35 database wrapper
safety cases passed; PostgreSQL 18.6 clean/head/repeat, seven smokes, Identity
upgrade/atomicity/rollback, protected-retirement rollback and full reapply passed;
Conversations PostgreSQL 167 passed; Gitleaks 8.30.1 source snapshot passed.
The first aggregate attempt had one 5-second Microsoft callback UI timeout; that
test passed alone, and the full aggregate passed on a clean rerun. The build
reports its existing large-chunk advisory. A fresh 21-action synthetic inspection
run passed against real local SQL and Hybrid inference on 5175; the final seeded
server remains live as the handoff. Human visual review remains pending.

DEC-12's approximate PD-16 run cost is not an invoice or final NFR-08 result;
CLOSE-00 still reconciles total project spend against the strict USD 200 limit.

## Pending integration ledger

| Task/step | Mode, source/version, double and scenarios | Required real dependency | Owner roles | Trigger | Real checks and expected result | Current evidence/state |
|---|---|---|---|---|---|---|
| CN-01 Step 8 local history | Actual SDK memory CAS adapter and real crypto with reviewed HTTP double; `conversations-history.test.ts` and `conversations-relay.test.ts` | Browser IndexedDB, ID-READY transport and actual API/PostgreSQL path | Conversations D; Identity A | Real auth and service transport are available | Verify browser restart and two profiles, retained sender/recipient history, prepared retries after unknown outcomes, account/key-loss isolation, storage failure, concurrent tabs and display-only acknowledgements | Isolated result human-verified; route composition now exists, but real browser durability and service integration remain pending; no CN-CORE/FR/NFR acceptance |
| CN-01 Step 8 SDK relay | Real OpenE2EE 13.0.0 crypto/local-memory adapters; generator format 2 HTTP double in `apps/web/tests/conversations-relay.test.ts`; API/provider recovery exercised on disposable PostgreSQL; SDK content recovery is explicitly off; IndexedDB factory implemented but not browser-tested | ID-READY authenticated HTTP transport, real API/PostgreSQL binding, browser IndexedDB and page/history integration | Conversations D; Identity A; affected origin owners B/C | Real Identity transport and service are available | Run two actual browser profiles against real services: registration and offline peer bundles, encrypted send/decrypt, prepared retries, display-only reads, changed/lost keys, browser restart/account isolation, safe null response when recovery is disabled, useful sender decryption-failure status, and no sensitive observability | SDK controls and page handling/status are locally implemented and tested through the same page helper with real SDK sessions; UI suite/full web check passes (86 tests). Real multi-browser/IndexedDB/HTTP integration and browser interaction review remain pending; no CN-CORE or latency acceptance |
| CN-01 Steps 4–8 route integration | Reviewed generated contract format 2; actual PostgreSQL providers and HTTP handlers, synthetic typed public-key bytes and test-only trusted Identity contexts in `test_conversation_directory.py` | ID-READY authentication/session transport and origin-owner composition; live `ConversationPageRuntimeProvider` mounting | Identity A; Conversations D; Listings B/Search C | Identity implementation and transport become available; route/session composition is implemented | Wire trusted sessions, then run actual two-browser key registration/participant binding/encrypted send/retry/history/read acknowledgement and nonmember/expired-session denial through the real application | Backend prerequisites pass 48 disposable PostgreSQL tests; page controllers are implemented but Identity/runtime mounting and real owner integration remain pending; no CN-CORE or FR/NFR acceptance |
| DL-00 Step 11; Search → Listings | Isolated; HTTP 0.1.0 / generator format 2; `apps/api/tests/domains/search/doubles/listings.py`; success/repeat, denied 403, expired caller 401, missing ID 404, timeout/unavailable 503 | Accepted LI-CORE implementation and the consuming SE-01 integration checkpoint | Listings B; Search C | LI-CORE is accepted and SE-01 reaches its real Listings integration checks | Run SE-01 Steps 3–8 against real Listings: verify availability/filter/order/page ties, category labels, saved/current summaries and retired-content privacy; denied/expired/missing/failure outcomes preserve safe errors; confirm Search uses only the public interface. | Isolated tests pass in the 55-test contract/double run; real provider checks remain pending. |
| LI-01 Step 5 / Step 11 — migration and database smoke | Isolated PostgreSQL 18.6/dbmate 2.36.0; never the shared Compose database | Current expected head 20261022062357, 26 domain tables across 11 migrations; retirement rollback guard at 20261020142319 | Listings B; database/migration maintainer if needed | Before LI-CORE/Step 11 database acceptance | Clean/repeat apply, SQL smokes, retirement rollback refusal, empty rollback/reapply; native inventory of 26 tables, 23 functions, 35 triggers | Historical disposable check passed at 20261020142319. Step 11 aggregate passed at current head; native schema-inventory run and affected-owner review remain pending. |
| LI-01 Steps 9–10 — isolated owner-command and lifecycle behavior | Local Listings service/store, disposable PostgreSQL, reviewed Conversations test double, synthetic Identity context | Real Identity and Conversations interfaces/providers | LI-CORE Step 11 and real consumer integration | Verify owner/auth denial, idempotent create/command replay and conflict, competing edits, availability/selection/offer gates, 180/90-day retirement, content/receipt cleanup, and 500,000-paise/category/proof boundaries | Focused suite: 61 passed, one direct DB-only skip outside wrapper; PostgreSQL workflow passed. Real Conversations offer writes and thread-start rejection, Identity, images, and Search remain pending. |
| LI-01 Step 5 — retirement integration and cleanup decision | Listings-owned pending operation ID/cutoff; public Conversations activity/marker interface only | Real Conversations provider and LI-02 storage/worker | Before real retirement acceptance at INT-01 | Verify 180-day eligibility plus 90 quiet days, all-or-none marker, stable retry identity, blocking while pending, receipt/detail scrub, and retry-safe object deletion | Listings coordinator, cleanup and focused tests are implemented; real Conversations/storage worker wiring and retired My Listings behavior remain pending. |
| LI-01 Steps 11–13 — real integrations and human browser verification | Real auth, ordered migrations, APIs/UI, image and Search dependencies | ID-READY, LI-CORE, CN-02, LI-02, SE-CORE; affected owners | Step 11 review; Step 13 after LI-02 and SE-CORE | Current full checks/query plans and public-boundary review; then real owner-auth create/edit/availability, image-backed discovery exclusion, desktop and phone journey | Not accepted. Real Identity, Conversations, storage, and Search integration plus desktop/phone Step 13 checks remain pending. |

| LI-01 Step 7 — isolated browser create/detail/My Listings/edit | Local HTTP browser demo with synthetic caller and image metadata; real Listings API/PostgreSQL | ID-READY and public A/C/D connections; LI-02/SE-CORE for real media/discovery | Resume remaining Step 7 states before LI-CORE | Complete validation/loading/unavailable/error cases and record browser observations | Multi-image edit/gallery verified. Step 7 remains partial; no real sign-in or photo upload is claimed. Phone website check remains LI-02 Step 12. |

| LI-01 Step 7 pickup-area correction | Nullable pickup contract/model and disposable/browser PostgreSQL | Affected consumers/schema owners and native/shared migration check | Before shared integration of migration 20261021105546 | Verify omitted/null create, explicit-null replacement, nullable reads, preserved existing values, and safe rollback without inventing data | Local SQL/API/UI checks passed and Suraj verified the browser behavior; consumer review and native/shared migration checks remain pending. |

| ID-01 Step 2 production delivery/configuration | Reviewed contract at44cd8ff; actual SES adapter/task-role sandbox delivery and inbox/cleanup verified; isolated Steps3–11 permitted | Reviewed active Resend runtime/provider configuration; SES production access before general SES use | Aditya; shared owner reviews policy | Approved Resend setup/runtime path, or SES production grant; resume original Step2 real configuration checks before readiness | Refresh provider status, review sandbox-guard/recipient-scope transition, verify required real production-configuration checks under separate cloud/send approval | SES sandbox evidence passed; Resend local verify sender delivered to Gmail/IISc and human-confirmed; actual normal runtime/permissions/general config pending; SES production remains pending |
| ID-01 Step3 combined migration-chain integration | Real disposable PostgreSQL18.6/dbmate2.36.0; five-migration isolated branch at80abc52 plus new Identity forward guard; no schema double | Accepted current-main migrations (known PR10 head20261022062357), reconciled shared checker/docs and owning-domain changes | Aditya; affected schema/domain owners; Rahul(D) reviews | After isolated Identity implementation, before ID-READY review/merge | Integrate current main; verify full ordered clean/upgrade/down/reapply chain and affected-domain checks; never claim missing earlier migrations applied from higher version alone | Exact accepted main defec38f integrated locally without commit;14migration bytes preserved; actual combined chain/Identity upgrade/retirement rollback/Listings workflow and full gate passed; human merged-result/peer/CI acceptance pending; no shared DB apply |
| ID-01 Step4 actual sign-in/session integration | Real RSA/SQL mapping plus Step7 server nonce/session/HTTP integration using synthetic assertions; original contract44cd8ff with Aditya-verified Step7 extension | Real Microsoft/IISc browser PKCE/state and runtime key/DB/TLS configuration | Aditya; shared/frontend/security reviewers and Rahul(D) | Before live credential exchange/ID-READY; local Step7 result verification then Step11/12 runtime | Verify real signed claims/domain and browser single-use attempt/session flow, safe failures/privacy and deployed permissions | Local nonce/session/context/mapping now implemented and checked; real user/provider/browser/runtime checks remain pending |
| ID-01 Step5 real OTP/public/runtime integration | Real private PostgreSQL plus Step7 actual HTTP ack/dispatch/reset/session composition with synthetic mail/SDK; no schema fake | Real controlled active-provider (Resend or SES) OTP/inbox and reviewed runtime key/DB/TLS/proxy/source/provider configuration | Aditya; shared/frontend/security reviewers and Rahul(D) | Separate exact send/cloud approval and owning Step11/12 runtime ready; sandbox can proceed without production access | Verify real delivery/code redemption, uniform browser acknowledgement/timing, trusted peer handling and actual runtime replay/rate/privacy behavior | Local HTTP/DB activation/reset/limits/one-shot timing and cleanup checked; no real OTP send or configured public website; original provider/runtime checks pending |
| ID-01 Step6 public activation/current authorization integration | Real Argon2id/SQL plus Step7 actual HTTP activation SessionView, atomic session and trusted protected-request context | Reviewed runtime/browser deployment and actual marketplace capability/contact consumers | Aditya; shared/frontend/security owners and Rahul(D) | Local Step7 result verified; owning Steps8/9/11/12 runtime ready | Verify actual configured activation/login/session/lifetime/no-renewal and expired/revoked marketplace denial with real consumer paths | Local actual activation/session/current-context/rollback/race checks pass; runtime/browser/consumer integration pending; not full FR-03/ID-READY acceptance |
| ID-01 Step7 actual runtime retention/session acceptance | Actual SQL/Argon2/RSA/HTTP and bounded cleanup CLI checked only with disposable data; design approved, no deployed schedule | Merged migration/runtime secret/DB role/proxy/TLS configuration, enabled approved cleanup operation/schedule and real provider/browser flows | Aditya/operator; shared/security owners and Rahul(D) | Human verifies local result; exact deployment/cleanup/cloud/send plan approved before execution | Verify real cookie/CSRF/replay/session/privacy behavior, source/proxy trust, reset/login revocation races and observed cleanup deadlines while permanent markers survive | Local implementation/checks performed; no enabled cleanup schedule, real runtime/provider/browser or shared deployment acceptance |
| ID-01 Step8 real consumer/runtime capability acceptance | Explicit scoped generated eligibility with real PostgreSQL/session/RSA and fixture HTTP probes; verified canonical signatures and policy | Configured runtime/worker composition and actual owning-domain marketplace endpoints after accepted dependencies | Aditya; consuming owners and Rahul(D) | Local Step8 result verified; owning consumer integration checkpoints/current-main runtime ready, final matrix atStep14 | Verify authoritative target binding, fresh class/lifecycle checks and per-resource ownership/membership/state, no private data/cross-domain imports, actual regular/temporary/expired/revoked API matrix | Local provider/matrix/scoped dispatcher/HTTP probes passed; no fabricated consumer endpoint or FR-03 acceptance; real consumers remain pending |


### SE-02 pending integration checkpoints

| Task/step | Mode, source/version, double and scenarios | Required real dependency | Owner roles | Trigger | Real checks and expected result | Current evidence/state |
|---|---|---|---|---|---|---|
| SE-02 Step3 wanted API/retries | Isolated HTTP/contract format2; real PostgreSQL14migrations; `test_wanted_postgres.py:Dependencies` supplies only eligible IDs and active/historical catalogue codes | Actual ID-READY/LI-CORE/SE-CORE providers and reviewed Conversations operations | Search C; Identity A; Listings B; Conversations D | Accepted providers and SE-02 Step8 | Real auth/revocation/temp permissions, category assignment/display, close/first-response serialization and retirement activity races; preserve owner/privacy/retry behavior | Local API/native checks pass; real integration pending; normal declaration-only defaults fail503 |
| SE-02 Step3 retirement remainder | Existing pending fields and defensive receipt guards; concrete cleanup proposal only, no scrubber/scheduler | Mohit approval of exact local method/order; reviewed actual Conversations before real acceptance | Search C; Conversations D | Cleanup approval, then isolated implementation; final integration at Step8/INT-01 |180/90day boundaries/reset, unknown/blocked marker results, transaction rollback, receipt/origin scrub and content-free late-key/no-reopen checks | Pending proposal approval; author API checkpoint does not complete Step3 |

### SE-02 approved retirement checkpoint: updated real gate

| Task/step | Mode, source/version, double and scenarios | Required real dependency | Owner roles | Trigger | Real checks and expected result | Current evidence/state |
|---|---|---|---|---|---|---|
| SE-02 Step3 retirement (updates earlier proposal-pending checkpoint) | Concrete local order approved; internal coordinator/atomic SQL implemented; explicit typed Conversations double, real native transaction/failure/race checks | Accepted actual Conversations activity/marker and Search request-response integration; Identity/Listings readiness | Search C; Conversations D; affected owners | Actual providers available and Step8/INT-01 | Validate real pending/close/response serialization, all-thread activity/no-write marker races and atomic local scrub; preserve unknown result identity | Local isolated checks pass; prior local approval/implementation gate satisfied, real integration remains pending |

### SE-02 draft-matching pending real integration

| Task/step | Mode, source/version, double and scenarios | Required real dependency | Owner roles | Trigger | Real checks and expected result | Current evidence/state |
|---|---|---|---|---|---|---|
| SE-02 Step4 draft matches | Reviewed public query format2; actual Listings native SQL via test composition, synthetic Identity; no fake ranking; independent wanted submit probe has explicit catalogue fixture | Accepted actual ID-READY/LI-CORE/SE-CORE provider composition and Step8 | Search C; Listings B; Identity A | Real providers available/Step8 | Real session/revocation/temp capabilities, available-only title/description match ordering/bounds, no draft persistence and nonblocking UI/submit behavior | Isolated native/HTTP checks pass; normal declaration-only defaults fail503; real integration pending |

### SE-02 saved-listing pending real integration

| Task/step | Mode, source/version, double and scenarios | Required real dependency | Owner roles | Trigger | Real checks and expected result | Current evidence/state |
|---|---|---|---|---|---|---|
| SE-02 Step5 saved behavior | Reviewed format2 target/current-summary contracts; SavedListingsDouble scripts; actual Search SQL/HTTP/concurrency/FKs with controlled upstream fixtures | Accepted actual Identity and Listings read_save_target/read_saved_listing_summaries providers, LI-CORE/SE-CORE | Search C; Listings B; Identity A | Actual providers available/Step8 | Real auth/revocation/temp scope, current target checks, unavailable/window transitions, retired content-free pages, own-page-only lookup, cross-user privacy and provider outage behavior | Isolated checks pass; no upstream provider implementation inferred, normal required declarations fail503; real integration pending |

### SE-02 Step6 local response gap and real coverage gates

| Task/step | Mode, source/version, double and scenarios | Required dependency/correction | Owner roles | Trigger | Checks and expected result | Current evidence/state |
|---|---|---|---|---|---|---|
| SE-02 Step6 response capability/races | Inventory of actual routers vs reviewed declarations; no synthetic pass for absent handler | Human-verified local response/200schema correction, then actual C provider | Search C; Conversations D; Identity A | Approve proposed corrective checkpoint; real provider integration later | Regular-only initiation, no self/hidden/retired create, closed exact-pair retry, ambiguous result recovery, Search row-lock serialization; real C uniqueness/membership separately | Local API absent; generated200body missing vs docs; Step6 partial and proposed correction not yet implemented |

### SE-02 response correction: local gap resolved, real integration pending

| Task/step | Mode, source/version, double and scenarios | Required real dependency | Owner roles | Trigger | Checks and expected result | Current evidence/state |
|---|---|---|---|---|---|---|
| SE-02 Step6 response (updates missing-handler/200body checkpoint) | Approved correction implemented; current contract0.1.0/format2; all11Search routes mounted,201/200typed; actual Search SQL/row locks and schema FK probe, explicit C pair-result script | Actual Identity/C create/existing lookup providers with independent capability/membership/unique thread and close/retirement enforcement | Search C; Conversations D; Identity A | Actual providers ready/Step8/INT-01 | Repeat positive/denied/closed/retired and ambiguous retry/race cases with real C transactions, member/privacy assertions and current auth | Local gap resolved; native/consumer tests pass, real provider acceptance still pending |

## Resolved integration evidence

The user confirmed on 2026-10-19 that the carried PD-08/09/12/13/15 platform,
owner and hosted-check gates were complete; the PRE-00 foundation gate was
accepted. This confirms those foundation obligations only. It does not accept
current domain integration, DATA-READY, any NFR, or the ECS/Lambda experiment.
Exact old check records remain in Git history; see the current task rows and
[foundation traceability](../architecture/foundation-traceability.md) for the
remaining obligations.

**2026-10-29 04:25:25 UTC — NEXT-03 full visual-feedback batch resumed.** Suraj authorized all remaining feedback work in one run, explicitly including the previously queued higher-reasoning tasks. Added outside-click/Escape dropdown dismissal, compact shared sale-card geometry, bounded shell content, collapsible mobile navigation and discovery forms, Wanted matches above Description, Seller Provided labels, distinct inbox surfaces and thread spacing. Updated obsolete UI assertions. `npm run check` passed: lint, 488 tests passed/3 skipped, typecheck, production build (existing bundle-size advisory). No cloud actions. Full batch remains in progress; do not treat the old inspection URL/checklist as the final handoff for these changes.

Intermediate verification: added `multi-choice-dismissal.test.tsx` covering outside dismissal, Escape/focus return and retained selection. `npm run check` passed with 489 tests passed and 3 skipped. Full `make check` is running with output at `/tmp/clip-full-visual-check.log`; no full result is claimed. The first attempt stopped at sandbox socket permission, then was rerun with local process/socket access. The batch and final visual handoff are incomplete.

**2026-10-29 05:05:29 UTC — NEXT-03 full visual-feedback implementation.** C3/C4, D2/D4 and D6 now implemented with the new forward Handle migration, Identity public participant view, canonical/generated contract updates, onboarding and profile editor, safe Handle/Temporary participant labels, marketplace-intent modes, item/person group paging, global unread aggregate and bounded first-unread/history presentation. Identity17 review manifest is unchanged. Real PostgreSQL Conversations checks passed (168 tests); combined clean/head/repeat, seven smokes, Identity upgrade/rollback and full clean reapply passed. Frontend lint/tests/typecheck/build passed with 493 tests and 3 skipped. Corrected obsolete fixture/profile/schema assertions; a final full check is underway. Expanded seeded action sweep and final inspection handoff remain pending.

**2026-10-29 05:35:44 UTC — NEXT-03 complete local feedback handoff, human inspection pending.** All feedback groups now include the formerly queued Handle/participant, marketplace modes/group pagination and unread tasks. Full `make check` passed: Python 1,936 passed/155 skipped, data 94 passed, frontend 493 passed/3 skipped plus lint/typecheck/build, contracts/boundaries/types, 35 wrapper-safety cases, complete disposable migration checks, 168 PostgreSQL Conversations tests and Gitleaks. Added final unread account-isolation test and reran frontend: 494 passed/3 skipped. Added a multi-page unread/read-watermark scenario and reran real PostgreSQL Conversations: 169 passed. Supplemental Handle migration checks preserve valid/invalid/missing/colliding names and IDs through down/reapply, enforce uniqueness and prove public-view access while denying private users/contacts. Restricted frontend workers to four after two existing tests timed out under unrestricted parallel load; assertions and timeouts are unchanged. Chromium passed phone/desktop/ultrawide layout, actual group continuation and Handle setup, real encrypted keyboard messaging, unread/divider and selective encrypted contacts. Clean replacement inspection app (PID 2833284) runs at `127.0.0.1:5176`; all 23 seeded action groups passed with 28 sale fixtures, 26 requests, 77 conversations, new-member onboarding and pagination peers. Browser-test keys/database were discarded. Updated plan, walkthrough, architecture/contracts and file-by-file report. Task-wide local review complete; human visual acceptance, independent review/merge and cloud release remain separate. No cloud or paid experiments occurred.

**2026-10-29 07:00:44 UTC — NEXT-03 reopened after mobile/desktop visual inspection.** Suraj reported that shared browse cards remain too tall with stretched badges and misplaced actions; listing detail facts do not read as the requested table; conversation mode axes are visually ambiguous, group row density/separation is insufficient, and phone pagination stacks vertically. He also refined unread behavior (open with preceding message, clear marker after sending, date separators, compact per-message time, count contact-sharing entries), requested a mandatory missing-key-first Account flow, and asked that `inspection_buyer` own sample listing and Wanted records. Added A18/A19, C6, D9–D11 and S1 to the decision plan; the previous clean inspection handoff is no longer final. Current implementation owner is the integrator for this single shared batch, coordinating only through the recorded public feature boundaries; no cloud work. Update the plan and this checkpoint after each correction group, then rebuild/seed a fresh local inspection environment for Suraj.

**2026-10-29 10:56:18 UTC — NEXT-03 Step 0.5 visual correction.** After reviewing the local inspection screenshots, Suraj asked for balanced desktop navigation, a reserved sale-card Original price row when the value is absent, and a single left-aligned conversation/thread/offer layout with spacing after Open listing. Updated AppShell navigation, shared sale-card markup/styles, and conversation page composition/styles; added regression checks. The targeted frontend suite passed 12 tests; the full frontend check passed lint, both TypeScript projects, production build and 496 tests (3 skipped across 2 files); `git diff --check` passed. The build retains the existing large-chunk advisory. Human review of these corrections remains pending. Suraj reordered the handoff so the NEXT-04 read-only deployment audit follows integration checks and precedes PR preparation; no cloud mutation is authorized.

**2026-10-29 09:08:58 UTC — Additional visual corrections recorded.** Suraj requested four more adjustments after reviewing the refreshed sale card and inbox: center Save/Message/View in one row below the card content; collapse each Item/Person conversation group by default; show its total unread count while collapsed; and scroll the conversation to the bottom after a successful send. The group unread total must include every authorized conversation in that group, including continuation pages, rather than summing only the first 20 loaded rows. Added A20 and D12–D14 to the feedback plan. Existing tests and action sweep apply to the preceding UI only; implement and verify these additions before the final human inspection handoff.

**2026-10-29 09:23:22 UTC — NEXT-03 inbox/card correction implementation.** D12 now collapses item/person groups by default while retaining their context/action headers. D13 exposes an authorized group-wide unread aggregate in the conversation summary; the query computes it before the 20-row cap, and the inbox displays it beside the group title even when collapsed. Its fresh PostgreSQL regression places 21 unread messages across the group and verifies the displayed 20 rows each carry the full count. D14 now scrolls to the transcript bottom after both a successful send and retry; the focused UI regression verifies a new entry reaches the bottom. `vitest` on the inbox and thread-interaction files passed (12 tests); the disposable PostgreSQL Conversations suite passed (169 tests). A20’s actions have been moved to a centered full-width row below card content with tighter phone controls; browser geometry verification and full aggregate remain next. Contract source and generated artifacts include the group aggregate; no cloud action occurred.

**2026-10-29 09:54:02 UTC — NEXT-03 full local verification and visual handoff refreshed.** The full `make check` passed (Python 1,936 passed/155 skipped; data 94 passed; frontend 493 passed/3 skipped; all contracts, boundaries, types, lint/build, database safety, disposable migration checks, Conversations PostgreSQL 168 passed, and Gitleaks). After the final compact browse-card label, `npm run check` passed with 495 tests and three opt-in HTTP skips; the expanded Conversations PostgreSQL suite passed 169 tests. Supplemental Handle migration/rollback/reapply and public-view privilege checks passed. All 24 seeded local action groups passed against real sessions, PostgreSQL stores and Hybrid inference; final records include 29 photo-backed sale listings, 27 Wanted Requests and 77 conversations. Chromium measured Save/Message/View together in one centered row at 360px, 390px and 1440px; all tested pages had no horizontal overflow or console errors, inbox groups started collapsed with their headers visible, and phone pagination remained horizontal. The clean inspection environment is running at `http://127.0.0.1:5176/__inspection` (launcher PID `3122258`; synthetic photos under `/tmp/clip-marketplace-inspection-nocf1mhm/`). The plan, walkthrough and file-by-file report are updated. Human visual acceptance remains pending. No cloud action, paid run, or external provider call occurred.
