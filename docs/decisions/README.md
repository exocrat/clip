# Project decision records

Record a shared, non-secret decision here when other tasks or contributors will rely on it. Create one Markdown record per decision from the template below. Keep detailed requirements in their canonical project documents and link to those documents from the record.

Use descriptive filenames such as `pagination.md`; a task-ID prefix is not required. Record the originating task and step inside the file.

When a decision changes, update the same file and the affected canonical requirements through the normal review/approval workflow. Preserve its origin, record the new revision date, rationale, and approver, and use Git history for earlier versions. A replacement file is not required for a revision of the same decision.

Copy this template for each new decision:

```markdown
# DEC-XX — Short decision title

**Date:** YYYY-MM-DD

**Origin:** Task ID and step where the decision was first taken.

## Question
What needed a decision?

## Options considered
- Option and relevant trade-offs

## Selected choice
What was selected?

## Rationale
Why was this choice selected?

## Implications
What tasks, contributors, systems, or documents are affected?

## Approver
Name the approver when approval was required; otherwise write `Not required`.

## Supersedes
Link the earlier decision this replaces, or write `None`.
```

Update the relevant canonical document when the decision changes its requirements. Link the decision record from that document when useful. Never record secrets or credentials here.
