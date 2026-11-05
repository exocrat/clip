# Identity handoff

**Current disposition (2026-11-05):** Aditya directed ID-01 completion. The work-log task row records this status; this overview does not add verification evidence.

## Read by purpose

| Read | Contents |
| --- | --- |
| [Canonical task and acceptance criteria](../../tasks/domain-task-list.md#id-01--implement-identity-eligibility-and-temporary-accounts) | Numbered Identity scope and acceptance requirements. |
| [Identity contract](../../../contracts/identity.md) | Shared Identity interfaces and authorization behavior. |
| [Provider history](provider-history.md) | SES/Resend setup, sender decisions, delivery results and prior provider findings. |
| [Integration handoff](integration.md) | Concise status/navigation page for ID-01 and its evidence. |
| [Step 12 records](id-01-step-12/) | Migration manifests, shared-role evidence and demo postmortem. |
| [Step 13 evidence](id-01-step-13/README.md) | Runtime/bootstrap, HTTPS, authentication/email, retention and cleanup results. |
| [Step 14 capability matrix](id-01-step-14/README.md) | Consumer authorization matrix and recorded evidence. |
| [Provider setup](../../environment/identity-provider-setup.md) | Current operational setup instructions; refresh live state before acting. |
| [Identity email routing](../../decisions/identity-email-routing.md) | SES/Resend precedence and delivery fallback decision. |
| [Private-data retention](../../decisions/private-data-retention.md) | Retention rules and sensitive-data handling. |
| [Work log](../../status/work-log.md) | Dated decisions, outcomes and task status. |

## Evidence and maintenance

The Step 12–14 files are records of past work, not reusable approvals or current cloud state. Check current source, owner decisions, credentials, account state and budgets before any new operation. Keep credentials, OTPs, session tokens and private recipient values out of committed evidence.

Earlier detailed task narratives were removed from the working tree during documentation cleanup and remain recoverable from Git history at `f36ce3d` and earlier revisions. Do not copy historical pending statements into current status summaries.

For new integration work, follow the [stub and integration gates](../../architecture/stubs-and-integration-gates.md), [secret-handling guide](../../environment/secret-handling.md), and [cloud inventory](../../environment/cloud-inventory.md).
