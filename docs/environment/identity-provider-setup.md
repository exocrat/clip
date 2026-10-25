# ID-01 provider setup

Current handoff: [integration](../evaluation/identity/integration.md).
Completed cloud/test chronology: [provider history](../evaluation/identity/provider-history.md).
Canonical choices: [Microsoft/initial SES](../decisions/identity-provider-setup.md)
and [dual-provider email](../decisions/identity-email-routing.md).
This guide contains current setup facts and pending actions, not new approval.

## Current status

| Provider/path | Verified | Still pending |
| --- | --- | --- |
| Microsoft | Registration/callbacks human-confirmed; real validator/SQL and controlled browser tests passed. | Actual IISc sign-in, consent/cache/PKCE and real runtime/browser acceptance. Button remains disabled. |
| Resend | Domain human-reported verified; operator SecureString create/read passed; corrected local adapter reached Gmail and IISc from verify@, human-confirmed. | Normal API/ECS wiring, task-role secret access, real OTP/browser flows, key rotation and general configuration acceptance. |
| SES | Recorded domain/DKIM verification, real sandbox application-role delivery/inbox and owned cleanup passed2026-10-23. | Production access/configuration, current provider-state refresh and exact live verify-sender IAM update. |

No new resource-state inspection was performed for this documentation cleanup.
Provider acceptance/Delivered is not proof of inbox placement. Previous no-reply
messages were missing at IISc; verify messages arrived. Sender/subject changed
together in a comparison, so the precise IISc filtering cause is not established.

## Microsoft registration and policy

- Public client: `ab3a63e3-d4db-4c3c-b4bf-ac5f7573ffbb`.
- Registration tenant: `19d07278-f040-4722-8202-b1174cf3a4d3`; metadata only,
  not an IISc tenant allowlist.
- SPA callbacks: `http://localhost:5173/auth/callback` and
  `https://clip-iisc.site/auth/callback`. The127.0.0.1 origin is not registered.
- Authority/discovery: public-cloud common v2; audience is the client ID.
  Validate signed issuer/tenant/key rather than accepting literal common as issuer.
- Selected flow: SPA code/PKCE, no browser client secret/Graph permission. Real
  server validates signature/audience/time/nonce and usable signed email whose
  parsed lowercased domain is exactly iisc.ac.in. No username/display/client-email
  fallback, extra regular-account OTP or tenant allowlist. Durable identity is
  provider/validated issuer/subject.

MSAL Browser5.26.0 uses explicit runtime flag/exact origins, stays disabled in
synthetic preview and by default, and never silently acquires credentials. SDK
OIDC defaults include offline_access; actual consent/cache cleanup needs real
verification. Public configuration alone grants no backend auth authority.

## Email sender and routing

Use `verify@clip-iisc.site` for verification/password-reset email. Avoid generic
no-reply/marketing-style senders. Keep email transport separate from CLIP-owned
OTP/password/session state. CN03 adoption needs its own owner/public-boundary
review; do not import Identity-private modules into another domain.

`RefreshingEmailSender` reads one versioned SSM snapshot on first send, then the
first send after14400monotonic seconds. Each process retains order/key together;
failed refresh sends nothing from expired settings. No background polling.
Primary initially Resend; later prefer SES through configuration once ready.
One primary attempt, then one alternate on any reported failure; same OTP/body,
no third attempt/fake fallback. Timeout uncertainty can produce two copies.
No bounce/webhook-triggered retry or automatic permanent promotion is included.

[Secret reference](secret-handling.md#id-01-dual-email-configuration):
`/clip/test/identity/email-delivery`, Standard SecureString, alias/aws/ssm,
account335523638354/ap-south-1. Version1 was created/read back by approved operator
adityalaxmi1. Private JSON fields: version(integer1), primary(resend/ses),
resend_api_key. Key/recipients/OTPs must stay out of chat/repo/logs. The key supplied
in chat must be rotated privately. Operator access is not ECS task-role access.

Current adapters accept at most five explicitly controlled recipients. The default
application composition remains Identity-unbound. An explicit
operator-local bootstrap command is prepared in the
[command registry](commands.md#explicit-real-local-identity-bootstrap--id-01-step12-preparation);
it requires separate real-access approval and does not enable deployed startup.
Once both real adapters,
permissions/outbound access and live loader are deployed, changing primary/key
can take effect without rebuilding/restarting; update delay is up to four hours
per active process, or its next send after expiry. General sending is not enabled.

## SES permissions and sandbox transition

Shared application role clip-shared-test-api-task has sender-domain ses:SendEmail
and the controlled recipient identity needed by the observed sandbox denial.
The private ses_sandbox_recipient_identity_arn Terraform input must be preserved
until its deliberate production transition review; do not broaden identity scope.

Desired source in infra/terraform/shared/test/identity-email.tf now uses exact
verify@ FromAddress. Deployed policy still uses historical no-reply until a new
exact reviewed Terraform plan/apply. No local edit changes AWS. SES sandbox
recipients must remain verified; Resend fallback cannot bypass that restriction.
SES uses task-role credentials, not static access keys/SMTP passwords. Local
operators use their own approved non-root profile; review actual identity first.
The local SDK lacked optional AWS-login CRT support in recorded tests, so CLI
exported short-lived credentials were captured only in process memory. Do not
write credential files or treat that workaround as deployed runtime evidence.

General SES use needs production grant and reviewed guard/recipient/IAM transition.
Resend can be the active real provider while SES waits, after its own actual
configuration and safety checks. No provider failure activates an account.

## Real verification and approvals

1. Prepare exact runtime/secret/DB-role/TLS/proxy plan and code, preserving Listings.
2. Review account/region/revision/identity/sender/recipient, caps, deadline and cleanup
   before cloud/deploy/live-send operations. Past proposals are not reusable approval.
3. Verify intended role/configuration; test actual controlled receipt and OTP flow,
   not only SDK acceptance. Keep ambiguous failures/redacted outcomes explicit.
4. Verify owned cleanup; leave other contributors' shared data/workloads untouched.
5. Keep ID-READY incomplete until real provider/runtime/UI checks, independent
   affected-owner review, current CI and authorized milestone merge are complete.

Public DMARC was observed2026-10-24 15:34:02 UTC as v=DMARC1; p=none;. Preserve
DKIM/SPF setup; verify authentication before tightening policy. See the
[development cleanup release gate](../evaluation/identity/provider-history.md#development-cleanup).

Offline checks and effects are registered in
[commands](commands.md#identity-provider-offline-checks--id-01-step-2).
Historical image/task/plan manifests and diagnostic scripts remain under
[retained artifacts](../evaluation/identity/provider-history.md#retained-artifacts).

## API image database trust

The local image correction vendors the official public regional roots and directs
bundled libpq to the installed OS CA file. See the
[trust decision](../decisions/identity-rds-system-trust.md) and
[explicit local checks](commands.md#api-image-rds-root-trust--id-01-step12).
This does not enable authentication or prove AMD64/Hybrid/deployed TLS readiness;
real runtime configuration, permissions and browser/provider acceptance remain pending.
