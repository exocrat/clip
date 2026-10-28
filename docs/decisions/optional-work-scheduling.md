# Decision — Optional Work Scheduling

**Status:** Team planning direction accepted in this conversation; record actual task selection/priority approvals at execution.

**Canonical path:** `docs/decisions/optional-work-scheduling.md`

Submitted PRD §8 schedules stretch work after required functionality, evaluation and submission material are complete. The team's later instruction permits optional features to start after their own technical prerequisites, subject to explicit human selection and protection of required work, accurately timed NFR verification, the ECS/Lambda comparison, budget and final submission buffer. Preserve the submitted PRD unchanged and identify this as a planning update in the report if relevant.

OPT-01 prerequisites: ID-READY, SE-02 and CN-03. OPT-02: ID-READY, LI-CORE, SE-CORE, SE-02 and CN-03. OPT-03: LI-02, SE-CORE and DATA-READY; its image-aware label/model plan is created within that optional task. EACH additionally requires OPTIONAL-OK: human approval of its bounded effort/cost/resources/test scope and required-milestone protection. OPT-04 (encrypted chat images) requires CN-CORE, ID-READY and LI-02. OPT-05
(search relevance/inclusion refinement) requires ID-READY, LI-CORE, SE-CORE and
DATA-READY. Both were added as unselected future tasks on 2026-10-28; neither
definition authorizes implementation, resource changes or paid tests. Explicit
selection of one feature never selects the others.

## Approver

User in the planning discussion; personal name not recorded. This accepts the
scheduling rule only; each optional feature still requires its separate
`OPTIONAL-OK` approval before work starts.

Optional changes must not block MVP, weaken security or invalidate a frozen comparison silently. If an optional feature affects measured code/schema/auth/runtime/resources, rerun/review affected evidence and preserve comparable experiment revisions. If required work/budget/buffer becomes threatened, pause/defer optional work through a recorded human decision. Deferral is not optional implementation completion.
