# Campus Marketplace — Pull Request Review Prompt

Use this prompt from the repository root for a pull request of any kind. Supply
the PR URL/number or the source branch and target branch. Add a task or
milestone ID when known. The reviewer identifies the applicable project scope
from the PR description, changed files, task records, and repository state; the
prompt does not assume the PR is a stream or domain task. A designated human
reviewer remains responsible for approval.

```text
Review pull request [URL/number, or source branch → target branch] in this
repository. Its task/milestone is [ID if known]. Follow AGENTS.md and
CONTRIBUTING.md. Be an independent, read-only reviewer: do not edit files,
approve the PR, merge it, deploy it, or perform cloud/paid/destructive actions.

Establish the exact target/base and source/head revisions being reviewed. Read
the PR description, changed-file list, full diff, and relevant surrounding code
or documentation. Check the current work log and active task/ownership records.
Identify the applicable task acceptance criteria, prerequisites, decisions,
contracts, conventions, checklists, and generated-file rules. Infer the change
type from repository evidence when its task ID is missing; state any acceptance
criteria that cannot be established. Do not assume chat is the source of truth.

Review every changed area against the criteria that apply to it. Consider:
- correct behavior, scope, requirements, edge cases, error handling, retries,
  concurrency, and failure recovery;
- ownership boundaries, public interfaces, cross-domain dependencies, shared
  file coordination, and downstream compatibility;
- authorization, privacy, secrets, sensitive data in logs/evidence, and safe
  local/production configuration;
- schema and migration integrity, generated outputs, reproducibility, and
  forbidden direct access to another domain's private data;
- test relevance and failure-path coverage, whether the reported commands ran
  on this revision, and any gaps between test coverage and the PR's claims;
- documentation, commands, links, meaningful code explanations, work-log
  accuracy, and whether task status matches the evidence;
- allowed test doubles, exact reviewed contract/version, fake-provider safety,
  and pending real integration entries, when stubs are involved;
- unintended changes, unrelated files, and merge conflicts or integration
  effects visible against the target branch.

Apply only relevant checks; do not require unrelated checks just because they
appear in this list. Run safe, documented, local checks when useful. Do not
access production data or credentials, send messages, change external state,
or treat a missing tool/environment as a passing check. Do not modify the PR.

Present the result as a clear report for the PR author and designated human.
Start with **Findings**; do not lead with a generic review recap. Order findings
by severity (blocking, major, minor, then observation), and give each distinct
issue its own short, plain-language heading. For every finding, explain:
- **Severity** and the exact file and line;
- **What is wrong**, with the relevant evidence;
- **Why it matters**, including the user, security, compatibility, or merge
  consequence;
- **Suggested resolution**, stating the concrete change or investigation the
  PR author should make. The reviewer reports this action but does not make the
  change.

Keep separate issues separate, and avoid reporting non-actionable style
preferences as defects. If evidence is incomplete, phrase the finding as a
question or unverified concern rather than a confirmed defect. If there are no
findings, say **No actionable findings** and state the review limits.

After Findings, report **Review details**:
1. the exact base/head revisions, scope, and acceptance criteria reviewed;
2. checks run, with exact commands and passed/failed results;
3. relevant checks or claims not verified, and why;
4. pending dependencies, stub integration obligations, owner approvals, or
   other merge gates;
5. a recommendation: changes required, unable to assess, or ready for the
   designated human's merge decision.

Do not grant peer approval or merge readiness on behalf of the human. The
designated human reviewer must independently decide approval. Before merge,
the human must also verify the latest reviewed head, target branch, required
checks and affected-owner approvals, unresolved comments, and authorize the
specific PR/revision. This review prompt never authorizes a merge, deployment,
or cloud action.
```

The prompt structures a review; it does not replace task-specific checks,
affected-owner review, required CI, human approval, or the separate merge gate
in `CONTRIBUTING.md`.
