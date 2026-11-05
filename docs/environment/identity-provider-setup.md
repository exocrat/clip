# ID-01 provider setup

**Task status:** ID-01 is marked complete in the [work log](../status/work-log.md)
by Aditya's 2026-11-05 direction. This operational guide does not establish
current cloud, DNS, provider-preference, or secret-parameter state. The recorded
Step13 hosted checks and Step14 authorization matrix are indexed in the
[Identity handoff](../evaluation/identity/README.md). Refresh live state and get
a new exact approval before any provider, permission, or hosting action.

## Recorded provider outcomes

| Path | Previously verified | Limit of this record |
|---|---|---|
| Microsoft | Real IISc sign-in and non-IISc denial were verified locally; Chrome and Firefox sign-in were later reported working. Step13 also recorded successful hosted sign-in and a phone-browser check. | Historical user-reported results; no current origin, application registration, cache or runtime state is asserted. |
| Resend | Domain verification was user-reported; `verify@clip-iisc.site` delivery and temporary registration/reset flow were reported successful. | Current key/parameter version, runtime preference and inbox placement are not rechecked here. |
| SES | Production access and a standalone delivery were recorded; Step13 hosted reset flow also completed per user report. | Current task-role policy, SSM preference and deployed image are not rechecked here. |

Provider acceptance is not proof of inbox placement. Earlier no-reply messages
were missing at IISc; later tests used `verify@`. The sender/subject comparison
did not isolate the precise IISc filtering cause.

## Microsoft registration and policy

- Public client: `ab3a63e3-d4db-4c3c-b4bf-ac5f7573ffbb`.
- Registration tenant: `19d07278-f040-4722-8202-b1174cf3a4d3`; metadata only,
  not an IISc tenant allowlist.
- Intended SPA callbacks: `http://localhost:5173/auth/callback` and
  `https://clip-iisc.site/auth/callback`. The127.0.0.1 origin is not registered.
  Earlier portal setup was human-reported, not independently inspected. Real
  local callback on2026-10-26 returned `AADSTS9002326`, showing the URI used for
  browser redemption is not marked SPA. In Entra App registrations, select client
  `ab3a63e3-d4db-4c3c-b4bf-ac5f7573ffbb`, Authentication, and move these exact
  CLIP callbacks to Single-page application (not Web). Preserve unrelated URIs;
  no client secret/implicit-flow toggle is needed. Following this guidance,
  Aditya verified real IISc sign-in and non-IISc denial at2026-10-26 04:48:20UTC;
  portal contents were not independently inspected. See [Microsoft SPA configuration](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow#redirect-uris-for-single-page-apps-spas).
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
OTP/password/session state. CN-03 uses its own public notification transport,
SES-first routing and `updates@clip-iisc.site`; do not import Identity-private
modules into that domain.

`RefreshingEmailSender` reads one versioned SSM snapshot on first send, then the
first send after14400monotonic seconds. Each process retains order/key together;
failed refresh sends nothing from expired settings. No background polling.
SES is the preferred primary; Resend is the configured alternate. One primary
attempt, then one alternate on any reported failure; same OTP/body, no third
attempt/fake fallback. The route is read from the versioned configuration below.
Timeout uncertainty can produce two copies.
No bounce/webhook-triggered retry or automatic permanent promotion is included.

[Secret reference](secret-handling.md#id-01-dual-email-configuration):
`/clip/test/identity/email-delivery`, Standard SecureString, alias/aws/ssm,
account335523638354/ap-south-1. Version1 was created/read back by approved operator
adityalaxmi1. Private JSON fields: version(integer1), primary(resend/ses),
resend_api_key. Key/recipients/OTPs must stay out of chat/repo/logs. On
2026-10-27 18:25:58UTC Aditya confirmed the chat-exposed key was revoked and its
replacement stored in SSM. This is human-reported; no value/version was retrieved
and no post-rotation delivery tested in this checkpoint. Operator access is not
ECS task-role access.

Standalone/local test configuration retains its controlled-recipient restriction;
the explicit hosted Identity runtime permits its authenticated account destination.
The default synthetic application composition remains Identity-unbound. The
operator-local bootstrap command is documented in the
[command registry](commands.md#explicit-real-local-identity-bootstrap--id-01-step12-preparation);
it requires its own current access approval and does not enable deployed startup.
A provider/key update takes effect on the first send after the four-hour per-process
cache expiry, without an image rebuild. This guide records prior setup; it does not
assert that current runtime configuration was read or tested.

## SES permissions and sandbox transition

Shared application role clip-shared-test-api-task has sender-domain ses:SendEmail
and the controlled recipient identity needed by the observed sandbox denial.
The private ses_sandbox_recipient_identity_arn Terraform input must be preserved
until its deliberate production transition review; do not broaden identity scope.

Source in infra/terraform/shared/test/identity-email.tf uses exact verify@
FromAddress. The approved2026-10-26 07:04:31UTC apply recorded that sender-condition
update; it is not still an unperformed change. The recorded apply and delivery
checks are historical; current effective permissions and runtime delivery state
are not asserted here. SES sandbox recipients must remain verified; Resend fallback
cannot bypass that restriction.
SES uses task-role credentials, not static access keys/SMTP passwords. Local
operators use their own approved non-root profile; review actual identity first.
The local SDK lacked optional AWS-login CRT support in recorded tests, so CLI
exported short-lived credentials were captured only in process memory. Do not
write credential files or treat that workaround as deployed runtime evidence.

SES production access and a standalone send were subsequently recorded on
2026-10-28, superseding the earlier pending-access statement above. That account
status alone does not enable general application delivery: the route is selected
through a private versioned parameter, the current provider preference has not
been read by this agent, the source adapter is test-profile and controlled-
recipient only, and the deployed role/recipient policy must be refreshed. Any
production source/configuration change, permission change or live send requires
its own review and approval. No provider failure activates an account.

## Real verification and approvals

1. Prepare exact runtime/secret/DB-role/TLS/proxy plan and code, preserving Listings.
2. Review account/region/revision/identity/sender/recipient, caps, deadline and cleanup
   before cloud/deploy/live-send operations. Past proposals are not reusable approval.
3. Verify intended role/configuration; test actual controlled receipt and OTP flow,
   not only SDK acceptance. Keep ambiguous failures/redacted outcomes explicit.
4. Verify owned cleanup; leave other contributors' shared data/workloads untouched.
5. ID-READY is marked complete in the work log. Future provider/runtime changes
   still need current source review, applicable checks and their separate action
   approvals; they do not reuse this task's historical approval or cloud window.

Public DMARC was observed2026-10-24 15:34:02 UTC as v=DMARC1; p=none;. Preserve
DKIM/SPF setup; verify authentication before tightening policy. Check current
DNS/provider state before any live change; historical checks are not authorization.

Offline checks and effects are registered in
[commands](commands.md#identity-provider-offline-checks--id-01-step-2).
Most old run manifests and receipts were pruned; the two diagnostic helpers still
used by offline tests remain in `docs/evaluation/identity/id-01-step-2/`. See the
[Identity handoff index](../evaluation/identity/README.md).

## API image database trust

The local image correction vendors the official public regional roots and directs
bundled libpq to the installed OS CA file. See the
[trust decision](../decisions/identity-rds-system-trust.md) and
[explicit local checks](commands.md#api-image-rds-root-trust--id-01-step12).
This does not enable authentication or prove current AMD64/Hybrid/deployed TLS
state. The recorded ID-01 acceptance is not a fresh runtime or provider check.

## Browser transport integration

Shared cookie/CSRF transport now connects Identity and marketplace wrappers locally;
normal Identity uses /api, with unprefixed routing only in its explicit preview.
Protected writes fail before dispatch when fresh preflight fails; no client demo
bypass or automatic transport replay. See the
[decision](../decisions/browser-session-transport.md) and the
[current ID-01 status](../status/work-log.md).
This local transport change does not establish present provider/browser/proxy or
image state; consult the current deployment plan before any release action.

## NFR-07 restore hostname preparation

The isolated restore app has code support for the exact test origin
`https://restore.clip-iisc.site`. Before enabling that deployment, its reviewed
plan must arrange DNS/certificate and register the Microsoft SPA redirect
`https://restore.clip-iisc.site/auth/callback` with the existing test application.
This is a pending operator configuration action, not a record of registration.
See the [NFR-07 provisioning procedure](../evaluation/predeployment-gap-tools.md).
