# Campus Marketplace — Pre-Domain Contributor Prompt

**Canonical path:** `docs/prompts/pre-domain-contributor-prompt.md`

Use this prompt with the [reusable task prompt](reusable-task-prompt.md) when working on BOOT-00, PD-00–PD-19, or PRE-00. The reusable prompt governs the human-verification loop; this prompt selects the pre-domain phase and its stream boundaries.

```text
I am working on the Campus Marketplace pre-domain foundation. My verified scope is [kickoff / Stream 1 API and shared core / Stream 2 web / Stream 3 database and data / Stream 4 cloud preparation / integration].

Follow AGENTS.md and docs/prompts/reusable-task-prompt.md, plus the workflow in docs/tasks/pre-domain-task-list.md. Do not infer or assign a person's name from a stream label. Read the task index, current work log, task list, relevant canonical sources, and current branches/PRs.

At the start of each selected task, audit the task's ordered steps against its purpose, prerequisites, expected outputs, acceptance checks, and relevant canonical requirements. Report whether the steps are complete and coherent. If you find a material omission, contradiction, or ordering problem, explain it and wait for a task-definition decision before implementation; do not silently work around it.

The kickoff owner completes PD-00–PD-03 in order, adds the tracked `.gitkeep` files to the exclusive directory roots listed in the task list, and audits all PD-00–PD-03 outputs and checks. Once the full audit finds no gaps, integrate the handoff directly into `main`, without a PR. Stream owners clone or branch from that `main` revision so the directories are present. Before any other task action, each stream owner removes only the `.gitkeep` files in their assigned roots; include those expected deletions in the stream branch/PR. Four stream owners may then proceed in parallel as their task dependencies permit:
- Stream 1: PD-04–PD-06 and PD-10; API and shared core.
- Stream 2: PD-07; web.
- Stream 3: PD-08–PD-09; database and data.
- Stream 4: PD-14–PD-15; cloud preparation.

After PD-04–PD-10 and PD-14–PD-15 have handed off their stream outputs, the integration owner handles PD-11–PD-13 and PD-16–PD-19/PRE-00. Each task still follows its stated prerequisites; in particular, PD-16 waits for PD-04–PD-15. The dependency table and canonical task steps control; this summary does not permit starting a blocked task.

Work only in the directory roots and task-assigned files for the verified scope. The exact `.gitkeep` paths and owners are in docs/tasks/pre-domain-task-list.md. Do not remove another stream's markers or edit another stream's directory. For a required cross-stream integration change, coordinate a bounded change with that stream owner and record the shared-path writer/reviewer before editing.

Follow the required read-only understanding report, human verification, and one-numbered-step-at-a-time execution. Keep the work-log status row current after each step and verification. Add concise dated history entries for meaningful outcomes, decisions, checks, blockers, consequential human direction, and closeout; group related steps where useful and omit routine “verified; proceed” updates. Use exact UTC times for new entries and follow the reusable prompt's rules. Preserve existing changes. Do not start another task while waiting for verification unless the human explicitly selects and verifies that task.
```

Stream labels describe path ownership, not individual identity or a claim that every task can start at once. Check each dependency and active branch before work. The [task list](../tasks/pre-domain-task-list.md) is authoritative for steps and acceptance.
