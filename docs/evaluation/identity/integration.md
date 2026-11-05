# ID-01 integration handoff

**Current disposition (2026-11-05):** Aditya directed ID-01 completion. The task ledger records it complete; this page is a navigation summary, not new verification evidence.

## Current handoff

ID-01 delivers Microsoft IISc identity eligibility, temporary email accounts, account recovery, profile/contact management, and regular-versus-temporary authorization. Its implementation and numbered acceptance criteria remain in the [canonical task list](../../tasks/domain-task-list.md#id-01--implement-identity-eligibility-and-temporary-accounts). The [Identity contract](../../../contracts/identity.md), [provider routing decision](../../decisions/identity-email-routing.md), [provider setup](../../environment/identity-provider-setup.md), and [private-data retention decision](../../decisions/private-data-retention.md) define the interfaces and operational rules.

Use the dedicated records for implementation and runtime evidence:

| Record | Contents |
| --- | --- |
| [Identity overview](README.md) | Current ownership, decisions, setup links and evidence index. |
| [Provider history](provider-history.md) | SES/Resend selection, sender setup, delivery results and prior development findings. |
| [Step 12 migration and integration records](id-01-step-12/) | Reviewed migration inputs, applied manifest and role-grant evidence; demo postmortem and retained runtime evidence. |
| [Step 13 runtime evidence](id-01-step-13/README.md) | Reviewed bootstrap, deployed image/runtime, HTTPS, authentication/email/browser checks, retention run and cleanup. |
| [Step 14 capability matrix](id-01-step-14/README.md) | Regular/temporary authorization outcomes across consumer APIs and their evidence. |
| [Work log](../../status/work-log.md) | Dated task decisions, status changes and verification reports. |

## Maintenance rules

- Treat the task ledger and work-log status table as the current status sources. Older checkpoint statements in historical evidence describe the state at their recorded time.
- Evidence files are records of bounded past operations, not reusable approval or executable instructions. Re-review plans, account state, credentials and budgets before any new cloud or provider action.
- Keep secrets, OTPs, session tokens and private recipient values out of committed evidence.
- Full chronological task narratives removed during documentation cleanup remain recoverable from Git history at `f36ce3d` and earlier revisions. Use Git history when investigating an old checkpoint; do not restore superseded narratives to this handoff.

## Related decisions and safeguards

The [stub and integration gates](../../architecture/stubs-and-integration-gates.md) distinguish isolated local evidence from real integration. The [secret-handling guide](../../environment/secret-handling.md) governs credential access. Current cloud state belongs in the [cloud inventory](../../environment/cloud-inventory.md); refresh it before acting.
