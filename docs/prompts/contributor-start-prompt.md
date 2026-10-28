# Campus Marketplace — Contributor Start Prompt

Use this short prompt from the repository root. Fill in the contributor and task before sending it to your coding agent. BOOT-00/PRE-00 are complete; use the current task index and remaining-work plan for active work.

```text
I am [name] ([A/B/C/D or role]). Work on [TASK-ID] in this repository.

Follow AGENTS.md and the complete protocol in
docs/prompts/reusable-task-prompt.md. Read the task index, the selected task's
canonical list, its relevant status rows and related work-log history,
CONTRIBUTING.md, applicable checklist items, and relevant
source/decision/contract/environment/evidence files. Do not read the full
chronological work log unless the task needs it.

First inspect the repository and current task state read-only. Audit the task's
ordered steps against its purpose, prerequisites, outputs, acceptance checks,
and canonical requirements; report any material gaps or confirm none. Then
explain the whole selected task in order: its numbered steps, dependencies,
outputs, checks, and decision gates. Check whether each dependency is done. If an
implementation is missing, use a stub only for steps allowed by
docs/architecture/stubs-and-integration-gates.md and only against a reviewed
contract. Keep the task incomplete until its required real integration checks
pass. Wait for my verification before changing anything.

After I verify the plan, do one numbered step at a time. Report the result,
changed paths, checks and evidence, update the work-log status row for each
step and verification, and wait for my verification before continuing. Add a
dated history entry for meaningful outcomes; related steps may share one entry.
Do not add separate entries for routine “verified; proceed” updates. Use exact
UTC times for new entries and follow the reusable prompt's entry rules. Apply
the relevant checklist items as you work and do the task-wide review before
declaring the task complete. Keep cloud, hosting, push, and merge actions
behind their separate approvals.
```

The reusable prompt is authoritative if this starter is shorter or a detail changes. Never paste credentials or secret values into the conversation.
