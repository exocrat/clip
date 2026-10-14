# Campus Marketplace — Peer Review Prompt

Use this prompt from the repository root when reviewing a task or milestone change. The designated human reviewer remains responsible for approval.

```text
Review the proposed [TASK-ID or milestone] change in this repository. Follow
AGENTS.md and the review rules in CONTRIBUTING.md. Read the task's canonical
steps and acceptance criteria, relevant contracts/conventions, work-log entry,
and applicable agent checklist items. Inspect the complete diff and the exact
revision being reviewed.

Check correctness against the task and requirements; ownership and public
contracts; security, privacy, and failure paths; migrations and generated
files; tests and their results; documentation and code explanations; evidence
and work-log accuracy; unintended changes; and any pending stub integration.
Run only safe, relevant checks available for this review. Do not alter files.

Report findings first, each with severity, file/path, and a concrete reason.
Then list checks run and their results, unverified claims or gaps, and whether
the reviewed scope appears to satisfy its stated acceptance criteria. If there
are no findings, say so and give the limits of the review. Do not approve or
merge the change; the designated human reviewer makes that decision.
```

This prompt supports independent review; it does not replace human approval or the applicable task/merge gates.
