# Identity handoff

**Current disposition (2026-11-05):** Aditya directed ID-01 completion. The work-log task row records this status; this page is an evidence index, not new verification.

## Scope and canonical sources

ID-01 delivers Microsoft IISc identity eligibility, temporary email accounts, account recovery, profile/contact management, and regular-versus-temporary authorization. Its numbered requirements are in the [canonical task list](../../tasks/domain-task-list.md#id-01--implement-identity-eligibility-and-temporary-accounts); shared interfaces are in the [Identity contract](../../../contracts/identity.md).

## Read by purpose

| Read | Contents |
| --- | --- |
| [Provider history](provider-history.md) | SES/Resend setup, sender decisions, delivery results and prior provider findings. |
| [Step 12 records](id-01-step-12/) | Migration manifests, shared-role evidence and demo postmortem. |
| [Step 13 evidence](id-01-step-13/README.md) | Runtime/bootstrap, HTTPS, authentication/email, retention and cleanup results. |
| [Step 14 capability matrix](id-01-step-14/README.md) | Regular/temporary authorization expectations and recorded evidence across 47 operations. |
| [Provider setup](../../environment/identity-provider-setup.md) | Current operational setup instructions; refresh live state before acting. |
| [Identity email routing](../../decisions/identity-email-routing.md) | SES/Resend precedence and delivery fallback decision. |
| [Private-data retention](../../decisions/private-data-retention.md) | Retention rules and sensitive-data handling. |
| [Work log](../../status/work-log.md) | Dated decisions, outcomes and task status. |
| [Stub/integration gates](../../architecture/stubs-and-integration-gates.md) | Distinguishes isolated local evidence from real integration. |
| [Secret handling](../../environment/secret-handling.md) and [cloud inventory](../../environment/cloud-inventory.md) | Credential safeguards and recorded cloud state; refresh before any operation. |

## Evidence and maintenance

Step 12–14 files record bounded past work. They are not reusable approvals or current cloud state. Check current source, owner decisions, credentials, account state and budgets before any new operation. Keep credentials, OTPs, session tokens and private recipient values out of committed evidence.

Earlier detailed task narratives were removed from the working tree during documentation cleanup and remain recoverable from Git history at `f36ce3d` and earlier revisions. Do not copy historical pending statements into current status summaries.
