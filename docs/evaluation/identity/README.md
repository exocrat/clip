# Identity handoff

ID-01 remains in progress. Current status and open gates are in the [domain task
list](../../tasks/domain-task-list.md#id-01--implement-identity-eligibility-and-temporary-accounts)
and [work log](../../status/work-log.md). Use the [Identity provider setup](../../environment/identity-provider-setup.md)
and [cloud inventory](../../environment/cloud-inventory.md) for operational
instructions and recorded cloud state; refresh state before any cloud action.

Past run receipts, source hashes, proposals and detailed reports were removed from
the working tree. Git history retains them if a specific historical detail is
needed. Do not reuse an old approval or proposed cloud input for a new operation.

The two diagnostic scripts under `id-01-step-2/` remain because Identity's
offline tests import them. Their tests do not call AWS or send email; running a
live command still requires its separately reviewed approval.
