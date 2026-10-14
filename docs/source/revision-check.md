# Revised Document Set — Consistency Check

**Version:** 3.1 · **Date:** 2026-10-14

This report covers document logic and the supplied bundle. It is not proof of application correctness, real CI execution, cloud setup, actual human PR approval or measured NFR compliance. Those are future verified task outputs.

| Audit issue | Resolution in the revised set |
|---|---|
| Undefined PRE-00 | Named foundation milestone in pre-domain list and task index, tied to successful PD-19/required checks and reviewed human-accepted handoff |
| Existing-repository bootstrap and missing source/output confusion | BOOT-00 and the public root README; expected task outputs are distinguished from missing source/prerequisite inputs; prompt/checklists installed before normal PD execution |
| Dataset-before-schema cycle | PD-09 prepares tooling; SE-01/DATA-READY performs final schema-aware generation/load/integrity/index/label validation |
| Identity and listing verification depends on successors | ID-READY/LI-CORE readiness PRs, later full direct API matrix and image/discovery checks; no entire task marked done prematurely |
| Contradictory listing-image parallel claim | LI-02 follows LI-CORE/ID-READY; starts versus final acceptance explicitly distinguished |
| Cloud approval after measurement | SE-01 cloud preparation before NFR-01/02; CN-01 cloud preparation before NFR-05; applicable local checks/manifests and deployed revision verified first |
| Missing mixed implementation | EXP-03 explicitly assigns Lambda adapter/package/routing/parity/Terraform/scripts, before EXP-04 deployment |
| Prompt cannot reach experiment/final closeout | Phase index routes BOOT → PD/PRE → DL/domains/INT → EXP → CLOSE with scoped step resumption |
| Premature final budget claim | Budget-to-date/reserve in INT; complete NFR-08 after experiment costs/cleanup in CLOSE |
| Optional graph/doc/PRD mismatch | All runtime docs use feature-specific prerequisites + OPTIONAL-OK; planning change relative to submitted PRD §8 recorded while PDF remains unchanged |
| Log mutation before understanding verification | Initial inspection read-only; claims/log/branch writes only after human-verifies scope |
| Contradictory waiting rules and resume state | One waiting rule; recorded task/step/sub-checkpoint, execution versus verification state, side effects, next action and actual revision |
| Human must reconstruct acceptance | Reports require expected/observed result, exact checks/evidence, pass/fail/blocked explanation and precise human decision |
| Missing UI/provider/read-state/secret procedures | Named Identity/wanted/saved UI and provider setup; read-watermark/acknowledgement interfaces and notifications integration; secret-reference/access template/tasks |
| Search/private-table boundary ambiguity | DL-00 chooses supported public query or approved projection, with explicit SE-01 projection/index/sync tasks if selected |
| Ownership and simultaneous Git workflow | CONTRIBUTING and roster: separate clones/worktrees, task/milestone branches/PRs, human peer/affected review, merge gates, owned task selection, shared writer/status/environment coordination |
| Missing NFR tooling/evidence invalidation | Explicit manifests/tool creators, outcome denominators, accurate-path gates and rerun/equivalence requirements after changes |
| Required blocker counted as completion | Task/milestone/phase acceptance requires actual passing required checks; readiness unblocks named consumers only |
| Missing final delivery tasks | CLOSE-00 assigns regression/revalidation, cost/resources, report/demo/viva/artifact package and precise submission state |

Checks performed: dependency acceptance graph is acyclic; every prerequisite node is defined; all 17 FR and 8 NFR IDs remain in product/domain traceability; revised task step numbering is contiguous; internal Markdown links resolve; current source/PRD checksums are recorded; archive paths match canonical destinations. The Graphviz file is supplied as source; no rendered diagram is claimed.

Remaining execution-time decisions are intentional: actual humans/remote accounts and permissions; pinned runtime/package choices; exact implemented command flags; approved provider/secret access; unresolved product/security behavior; real cloud targets/resource/cost settings; workload/timing details and authoritative course submission instructions. Each has a named task/decision/checkpoint and must be read from the repo when recorded or asked before dependent action. No uncertain execution fact is fabricated in this planning package.

## v3 follow-up: parallel starts and existing-machine bootstrap

- Existing WSL is reused. One-time human agent-access actions are separated from agent-operated clone/install work; Linux CLI/root/tool/PATH, authentication and optional WSL editor verification are explicit.
- Existing exocrat/clip is the fixed target. Staging versus working clone, conflict inspection, no nested archive folder, the one-time direct-to-main documentation seed without separate peer-review requirement, separate push approval, and subsequent PD-00 sessions are explicit.
- Both checklists are supplied and read by exact canonical path in the prompt/AGENTS/start guide before initial writes. PD-18/INT-01 are maintenance checkpoints.
- Every required domain and selected optional task has explicit allowed isolated checkpoints versus real integration/acceptance gates. Unknown interfaces/security/approvals and actual NFR/experiment/restore/cost/submission evidence cannot be faked.
- The staged-step exception preserves original IDs, human verification and pending real subchecks; ledger/resume triggers prevent fake-only task/milestone completion. Real prerequisites remain in solid graph edges; dashed edges explain early starts.
- README/index/conventions/repo structure/task headers/steps/prompt/checklists/work log/CONTRIBUTING/evaluation/final-closeout references agree on mode and acceptance.

Verification for this revision checks internal links, continuous task step numbering, FR/NFR coverage, graph definitions/edge agreement/acyclicity, acceptance gates and PRD/hash/ZIP integrity. No commands were run on the user's WSL or GitHub repo; no application/cloud/NFR result is claimed. Official CLI/filesystem setup sources were fetched for these instructions. Graphviz rendering was not available; DOT source and acyclic edge checks are supplied.

## BOOT-00 step 6.5 follow-up — audit performed

The step 6.5 workflow edits are recorded in `docs/source/README.md` and `docs/status/work-log.md`. The read-only audit checked cross-document task-start rules, dependencies/stubs (including CN-02 step 8), concise logs, task-wide closeout, code explanations, peer review, direct-to-main/push gates, task checks/acceptance, links/anchors and PRD provenance. It found one task-start wording mismatch in `CONTRIBUTING.md`; that wording was corrected to require the full ordered task sequence. Post-correction checks found 0 broken relative Markdown links or anchors across 28 Markdown files; the PRD checksum still matches the supplied manifest. No application tests or commit/push were performed. Human verification of the correction remains pending.

## BOOT-00 completion and publication separation — 2026-10-14

The documentation workflow now treats the audited local seed commit as BOOT-00 completion after human verification. Publishing that revision remains separately approved and does not block PD-00 in the clone where the seed is present. Remote/local status must be recorded, and other clones must obtain the canonical documentation revision before using it. The unchanged PRD and source manifest baselines remain intact.
