# ID-01 provider history

Historical evidence, consolidated from the44report archive at `890adb1`.
Current operational instructions are in [provider setup](../../environment/identity-provider-setup.md).
Exact old requests/results are recoverable using [archive-map.json](archive-map.json);
none of their approvals authorizes a new action. No private inbox/key/OTP values.

## Setup and permissions

Microsoft SPA registration metadata/callbacks were human-confirmed; real signed
IISc sign-in remains pending. Application-owned OTP/password state was chosen
instead of provider-managed auth. Initial email transport was SES in account
335523638354/ap-south-1 with verified clip-iisc.site domain/DKIM.

| UTC checkpoint | Outcome |
| --- | --- |
| 2026-10-23 04:48:31 | SES sender domain/DKIM observed verified; sandbox remained active. This is historical, not a fresh quota/account check. |
| 2026-10-23 06:01:08 | First Terraform plan stopped: unexpected shared ECS AMI and RDS scope. Plan99dbcff…180db was not applied; no refresh/target bypass. |
| 2026-10-23 06:17:00 | Approved sender-scoped ses:SendEmail policy applied/verified. Exact planbaa80880…5e9a; no static SES/SMTP credential. |
| 2026-10-23 06:30:46 | Controlled recipient verification SUCCESS observed before dispatch preparation. |

The shared role is clip-shared-test-api-task. Original exact From condition was
no-reply@clip-iisc.site; desired source now uses verify@, but the live permission
change still requires its own reviewed plan/apply. Retain the private optional
ses_sandbox_recipient_identity_arn input in sandbox plans; do not broaden to
identity/*. Initial policy proposal/hashes remain in the artifact directory.

## Builder and image

Aditya approved a small AMD64 temporary builder in Mumbai with exact cost/time/
cleanup boundaries. Cloud-init/source/secret handling, non-root image, denied
smoke invocation and isolated health were checked. Original builder/apply plans,
prices and caps are historical; do not reuse them as authorization.

| UTC checkpoint | Outcome |
| --- | --- |
| 2026-10-23 07:21:38.860970 | One native AMD64 image published to the existing ECR repository from source52186a0. |
| 2026-10-23 07:22:28.116194 | Owned builder/root disk termination verified before the approved expiry; other resources left intact. |
| 2026-10-23 09:12:58 | Registration preflight stopped for concurrent RDS activity; no database action. Revised scope explicitly excluded RDS. |
| 2026-10-23 09:27:10 | Exact smoke task revision1 registered; unused temporary builder IAM/profile/group resources removed. No send yet. |

[Published image](id-01-step-2/published-image.json) retains full source/image/
config/manifest digests. Registry digest3ef8b13d…eddd1d identifies the historical
smoke image, not current authentication deployment. Task family:
clip-test-identity-email-ap-south-1-id01:1 (256CPU units/512MiB), disabled defaults.
Original template/proposal files and source hashes stay unchanged for audit.

## Delivery diagnostics

| UTC checkpoint | Result, distinction and correction |
| --- | --- |
| 2026-10-23 09:49:29 | First RunTask CLI input failed; no task/host/submission observed. Anonymous-memory-file transport was offline-verified before separately approved retry. |
| 2026-10-23 10:14:29 | Corrected task ran under the actual application role but returned failed_or_uncertain/exit1; human received no mail. Owned task/host/root cleanup passed, RDS untouched. |
| 2026-10-23 10:26:07 | Human confirmed one local CLI SES mail. This proved operator delivery, not ECS task-role permission. Local SDK lacked optional AWS-login CRT support; no dependency bypass. |
| 2026-10-23 16:57:21 | Approved diagnostic isolated AccessDeniedException at SES submission; signed task-role identity and client construction passed. Sender-only simulation had not proved actual authorization. |
| 2026-10-23 17:13:37 | Enhanced diagnosis identified the controlled recipient identity as the denied resource; exact approved plan36e9738a…3d47 added only that private ARN alongside sender domain, preserving action/From condition. State serial10/policy/lock verified. |
| 2026-10-23 17:17:30 | Corrected role-based task accepted/exit0 and human inbox receipt confirmed. Owned host/root removed, ECS/ASG zero verified17:17:09.706322; RDS unchanged. Full458Python/63data/16web/all11gates and three Terraform roots passed. |
| 2026-10-23 17:23:48 | Aditya verified the SES fix/delivery/cleanup and approved staged progression while production-access/configuration remained pending. |

Raw provider text, addresses, bodies and credentials were omitted. Exact applied
recipient correction is in [the saved review](id-01-step-2/sandbox-recipient-fix-review.json).
Two retained diagnostic wrappers are loaded by offline tests: runtime_diagnostic.py
and runtime_authorization_diagnostic.py. Do not delete/move them as prose cleanup.
No historical snapshot establishes current resource state or safe rerun authority.

## Resend and sender outcome

Aditya selected Resend initially and SES later, with a four-hour routing/key cache
and one alternate real-provider attempt after failure, including uncertainty.
Same OTP/message is reused; two delivered copies are possible. Both failures
stop dispatch and never authenticate a user. [Canonical routing decision](../../decisions/identity-email-routing.md).

| UTC checkpoint | Outcome |
| --- | --- |
| 2026-10-24 14:15:45 | Operator identity checked; Standard SecureString /clip/test/identity/email-delivery version1 created under aws/ssm and privately read back. CLI-exported temporary credentials stayed in memory because direct SDK login support was missing. A submitted chat key requires rotation. |
| 2026-10-24 14:19:07 | Authorized Resend retry failed HTTP403/1010 before normal API handling. Added explicit CLIP User-Agent;44offline tests passed. |
| 2026-10-24 14:22:05 | One corrected submission accepted after reviewing official Resend guidance. Acceptance alone was not inbox receipt. |
| 2026-10-24 14:23:58 | Gmail test accepted; Aditya subsequently confirmed receipt. |
| 2026-10-24 15:34:02 | Public DMARC TXT verified v=DMARC1; p=none; one IISc retest accepted. Aditya reported dashboard Delivered but no inbox receipt. |
| 2026-10-24 16:08:47 | Paired comparison: verify variant arrived at IISc, no-reply variant did not; both arrived at Gmail. From and subject changed together, so root cause was not isolated. |
| 2026-10-24 16:10:19 | Single-recipient verify sender test accepted; receipt confirmed by Aditya at16:11:27. |
| 2026-10-24 16:14:25 | Aditya chose verify@clip-iisc.site for verification/reset and avoided generic no-reply/marketing-style senders. Local adapters/settings/desired IAM source aligned;82focused checks passed. |

Resend Delivered means recipient-server250OK acceptance, not mailbox placement.
DMARC alone did not prove the cause. No IISc filter rule is claimed; real runtime/
SES verify-sender permission and production readiness remain separate checks.

## Development cleanup

Recorded2026-10-23 10:20:49: Aditya requested avoiding the15minute ECS managed
scale-in wait during development. The AWS-managed delay was not disabled;
managed termination protection was already off. The approved alternative was a
prompt guarded desired-zero action only after owned task STOPPED, empty shared
work/desired services, sole owned host and ASG min0/max1, serialized shared window.
Recheck before mutation; stop on concurrent work/unclear ownership; keep managed
draining and leave RDS untouched. Verify task/host/root cleanup, retain normal
managed scaling if prompt cleanup is unsafe. Every new run needs exact approval.

**Before development ends/production:** remove the development early-scale-to-zero
override, rely on normal ECS managed scale-in, and verify cleanup. Aditya owns
this release gate. The underlying15minute managed behavior remains enabled.

## Retained artifacts

Original Step2 directory holds published-image.json, sandbox-recipient-fix-review.json,
source/build/plan manifests, proposed task/run/policy JSON, builder-proposal inputs,
policy patch and the two test-used diagnostic scripts. Later step folders retain
source-hashes.json snapshots; Step11 retains its four snapshot sets, Step12 its
email-routing and merge snapshots. Their original paths/bytes are retained.
Full exact historical plan SHA256s/commands/IDs remain in those artifacts or the
archived Markdown blobs, rather than being duplicated in a new live runbook.
