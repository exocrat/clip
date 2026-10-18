# Secret scanning

**Date:** 2026-10-19

**Origin:** PD-12 Step 3.

## Question
Which reproducible repository secret gate should CI run without cloud credentials?

## Options considered
- A project-specific regex scan: small but limited provider coverage.
- Pinned Gitleaks in an isolated local container with upstream rules.

## Selected choice
Use Gitleaks 8.30.1 through `scripts/check_secrets.py` and explicit
`.gitleaks.toml`. Scan a snapshot of tracked/nonignored current source, including
new files, without Git history or ignored developer files. Report only finding
path, line and rule; never matched values. Inline allow comments and ignore files
do not bypass the scan. Scanner execution has no network and a read-only mount.

## Rationale
Upstream rules cover common credential formats without a paid action or token.
The existing bundle manifest triggers a generic-key false positive for the
historical SHA-256 of `secret-handling.md`. The only project exception requires
both that exact checksum and its exact manifest path; no file or rule is disabled.

## Implications
CI/local commands use the same pinned scanner. Findings/tool errors fail.
Ignored files, removed historic credentials and every possible secret format are
outside this snapshot gate's coverage; normal secret-handling rules still apply.
Changes to rules/exceptions require review. Default Gitleaks rule behavior follows
[its official configuration guide](https://github.com/gitleaks/gitleaks#configuration).

## Approver
Not required for tool selection within approved PD-12 Step 3; human verification
of the implementation and normal peer review remain required.

## Supersedes
None.
