# Campus Marketplace — Contributor Start Prompt

Use this short prompt from the repository root. Fill in the contributor and task before sending it to your coding agent.

```text
I am [name] ([A/B/C/D or role]). Work on [TASK-ID] in this repository.

Follow AGENTS.md and the complete protocol in
docs/prompts/reusable-task-prompt.md. Read the task index, current work log,
the selected task's canonical list, CONTRIBUTING.md, applicable checklists,
and relevant source/decision/contract/environment/evidence files.

First inspect the repository and current task state read-only. Then explain the
whole selected task in order: its numbered steps, dependencies, outputs,
checks, and decision gates. Check whether each dependency is done. If an
implementation is missing, use a stub only for steps allowed by
docs/architecture/stubs-and-integration-gates.md and only against a reviewed
contract. Keep the task incomplete until its required real integration checks
pass. Wait for my verification before changing anything.

After I verify the plan, do one numbered step at a time. Report the result,
changed paths, checks and evidence, update the concise work log, and wait for
my verification before continuing. Apply the relevant checklist items as you
work and do the task-wide review before declaring the task complete. Keep
cloud, hosting, push, and merge actions behind their separate approvals.
```

The reusable prompt is authoritative if this starter is shorter or a detail changes. Never paste credentials or secret values into the conversation.
