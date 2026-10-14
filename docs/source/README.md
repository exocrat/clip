# Source and Revision Record

**Version:** 3.1 · **Date:** 2026-10-14 · **Canonical path:** `docs/source/README.md`

This revision uses the full v2 planning set and the subsequent conversation decisions: existing exocrat/clip repository, existing WSL, agent/repo access and folder/startup instructions, immediate supplied checklists, documented early stub-based implementation with pending real integration obligations. Earlier product/Git/task/NFR/optional-scheduling decisions remain incorporated. The submitted PRD bytes are unchanged. Optional scheduling follows the accepted decision record; no product requirement is silently relaxed by a stub.

BOOT-00 verifies/copies this bundle; PD-01 validates installed provenance. These baseline hashes identify documentation only, not executed setup, code/CI/cloud/NFR results or approvals. Later reviewed edits update provenance/date/revision. Source record and manifest have no recursive self-hash. Current execution facts belong in the work log, actual environment records and task evidence.

## BOOT-00 installation record

On 2026-10-14, the 27 files listed below from the supplied v3.0 bundle were installed at the same canonical paths relative to the repository root. The listed SHA-256 values identify those supplied source files. At installation, the existing repository root `README.md` was merged with the bundle README, retaining the original repository identity and adding navigation/setup content. The README baseline hash below describes the supplied bundle file, not the installed file. The original installed README hash was `f78b6c430df0beb15cab375916a2b9b8883384072cbb47302c1601d5e56d26e7`; a later documentation revision is recorded below. The `bundle-manifest.json` records supplied-source baseline hashes, not later installed-document hashes.

The accepted optional-scheduling planning update remains recorded in `docs/decisions/optional-work-scheduling.md`; the submitted PRD remains unchanged. The supplied source record's pre-installation SHA-256 was `9feb3701cc4333e30959cc6494944309ddf30556e0ea0690c9f8ceb124263b90`. This repository copy adds installation provenance. The supplied manifest retains that baseline; the current source-record checksum is intentionally not self-recorded.

## BOOT-00 step 6.5 — workflow documentation revision

On 2026-10-14, the team-approved documentation revision changed the root README to a public-facing project summary, added contributor-start and peer-review prompts, required a full ordered task summary before work, clarified dependency checks and pending stub integrations, adopted concise work-log entries, added task-wide closeout checks, required explanations for new code, and recorded the one-time direct-to-main seed exception with separate push approval and no separate peer-review requirement for that commit. CN-02 step 8 now says to use the real Identity interface when ID-READY exists and otherwise a reviewed stub, while keeping real integration pending. The submitted PRD remains unchanged. The full step 6.5 audit was performed; it found and corrected a task-start wording mismatch in `CONTRIBUTING.md`. Results are recorded in `docs/status/work-log.md`.

The current public-facing root `README.md` SHA-256 after this revision is `7bc42225b2189bbdc3b46705ec1dc7b9064be0498cc5282439f5981b3c26699e`.

| Canonical file | Source/version | SHA-256 baseline |
|---|---|---|
| `AGENTS.md` | Planning/documentation v3.0, 2026-10-14 | `009d71c774566755a5c6382dacb889f19c6d27a7b95a56fa83e378e48558dfca` |
| `CONTRIBUTING.md` | Planning/documentation v3.0, 2026-10-14 | `673ab0713d7365c04a03e0a385cf891c290c8e0f01d9aed5be32271cdf78cecd` |
| `README.md` | Planning/documentation v3.0, 2026-10-14 | `75e0fee4f91f894601d53d3b0ec44f6670aaac127564ad80c322d221c0b70552` |
| `docs/README.md` | Planning/documentation v3.0, 2026-10-14 | `9d4fc56f4f87b0cd1fdcc475cbaf49e7582a2230580617ff3218d2c506b329a1` |
| `docs/architecture/repository-structure.md` | Planning/documentation v3.0, 2026-10-14 | `709e4819508dddefb42216adfa1feda06645a8b5d25e12259ad14dee217bf701` |
| `docs/architecture/stubs-and-integration-gates.md` | Planning/documentation v3.0, 2026-10-14 | `6e64af6b6ce6cbcb85c18dc6e8d94d7e221ceeb7f706fd900b6cc32419a93927` |
| `docs/architecture/task-dependencies.dot` | Planning/documentation v3.0, 2026-10-14 | `9c756cb66a118b5dea0632e594a0dd0eaefd5f44cc49c69ffb555f06a7be0c8e` |
| `docs/checklists/agent-checklist.md` | Planning/documentation v3.0, 2026-10-14 | `6b1f4bbb00817ceb28fa6f80fcbc16ac43ac96f16513b3bde8c078f7a5cd325b` |
| `docs/checklists/human-checklist.md` | Planning/documentation v3.0, 2026-10-14 | `05aa7d2a2e56b4a917b51dbaea9e69b64c07984a09d7e7caec330b350d201e88` |
| `docs/conventions/shared-conventions-and-cross-domain-contract-rules.md` | Planning/documentation v3.0, 2026-10-14 | `6a7195b0e47eca164da13183747c11d2aae39975a61b8066b8f99a66e9b41ba8` |
| `docs/decisions/optional-work-scheduling.md` | Planning/documentation v3.0, 2026-10-14 | `a6469f79e5824af362dac7c44efa37632a8b4dff2063a31dbed1894d229dd22b` |
| `docs/environment/commands.md` | Planning/documentation v3.0, 2026-10-14 | `f6b387aa4a4a7418b0f642a9ab386bcf622e4096a26f392da9fa37064955c88f` |
| `docs/environment/secret-handling.md` | Planning/documentation v3.0, 2026-10-14 | `1dbf459ba65c4f26b077d6b017bb39a1bb105274a9ec0ba83b408f75a6a0ba9e` |
| `docs/environment/wsl-and-first-session.md` | Planning/documentation v3.0, 2026-10-14 | `5d13681553feaf0e2532e807d1d92cb2f681fa714316c95e01e64afb24b1047c` |
| `docs/evaluation/README.md` | Planning/documentation v3.0, 2026-10-14 | `a1f35471f348dc1db2ccf92fb51de4b0c4b2500cb76cc5454fe03b2bbbb43437` |
| `docs/evaluation/ecs-only-vs-ecs-lambda-task-list.md` | Planning/documentation v3.0, 2026-10-14 | `6968df52aca630fbdbc6d036e21fe598eeefd7df86790b70e85421ba569c56da` |
| `docs/product/product-reference-and-architecture-decisions.md` | Planning/documentation v3.0, 2026-10-14 | `33e6b66834fadcdac615d65067556bdfd042f4287a0295e0244410e09cfdb5f0` |
| `docs/prompts/reusable-task-prompt.md` | Planning/documentation v3.0, 2026-10-14 | `f359592667408325baa59373286fd3b6da275168154371732d1e1c6d103c62c8` |
| `docs/source/ICC_Project_PRD_FINAL.pdf` | Submitted PRD; unchanged | `8ac241d1e72472a5dc77edad18579ec5d2ca3ff2ac8fd454cbc6e9627abf4ad1` |
| `docs/source/revision-check.md` | Planning/documentation v3.0, 2026-10-14 | `2db128e699e5230543bdff47701014b8494f9f29ae74077845673e053b409e34` |
| `docs/status/work-log.md` | Planning/documentation v3.0, 2026-10-14 | `f206044ca9e194a91589b3015f318f9dc97082097e91964ef2ebedebaa0f3a91` |
| `docs/tasks/bootstrap-task-list.md` | Planning/documentation v3.0, 2026-10-14 | `5b790fb8286ad0c8af3b6adf13dac6436d917429887a6e52c3421085422d3573` |
| `docs/tasks/domain-task-list.md` | Planning/documentation v3.0, 2026-10-14 | `44f19ff4a0027c4842cce4088a16fb70f055cf1386e9188f6a6f6c2c6e0afcbc` |
| `docs/tasks/final-closeout-task-list.md` | Planning/documentation v3.0, 2026-10-14 | `2d043fbbcc8424e7675f48d682b2431d454ea3556beab042dfddb1f3cc80aba5` |
| `docs/tasks/pre-domain-task-list.md` | Planning/documentation v3.0, 2026-10-14 | `08ca80c8fe63c0b40025efcfc97fca9d2fea94c8ce2b78ff322d81e586eddc54` |
| `docs/tasks/project-task-index.md` | Planning/documentation v3.0, 2026-10-14 | `7f139abd270a595d4832b8268556fb161b34be7854ef4781e9244dc2d72bc324` |
