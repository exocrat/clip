# Campus Marketplace — Agent Entry Point

Start with the public project overview in `README.md`, then follow `docs/prompts/reusable-task-prompt.md`. A ready-to-copy task starter is in `docs/prompts/contributor-start-prompt.md`.

At startup, verify the existing exocrat/clip clone and identify the current contributor's environment from repository records and available read-only evidence. Read `docs/environment/wsl-and-first-session.md` when the contributor uses WSL; do not assume WSL is installed or required for other contributors. Both checklists apply from BOOT-00. Before environment-dependent actions, inspect the actual repository and `docs/status/work-log.md`; read `docs/README.md`, `docs/tasks/project-task-index.md`, the selected task, `CONTRIBUTING.md`, and relevant canonical sources. Ask targeted questions for human-only setup details that materially affect the task and remain unknown after inspection; do not ask the human to repeat facts that can be discovered or are already recorded. Summarize the selected task's full ordered steps, dependencies, outputs, and gates before asking the human to verify the plan. Execute one numbered step at a time and wait for verification after each report.

Check each dependency against current evidence. When an upstream implementation is missing, use a test double only for the steps permitted by `docs/architecture/stubs-and-integration-gates.md` and only against a reviewed contract. Record real integration work as pending; the task remains incomplete until its required real checks pass. If a contract is missing or unclear, stop and ask.

Use the relevant checklist items while working and complete the task-wide review before declaring a task or milestone done. Keep the work log concise. Explain the purpose and important behavior of new functions and other meaningful code in the code or its documentation.

Follow `CONTRIBUTING.md` for code ownership, peer review, and Git. BOOT-00 has one documented, team-approved direct-to-main exception for the initial documentation seed. Remote pushes, merges, hosting changes, and cloud actions retain their separate approvals.
