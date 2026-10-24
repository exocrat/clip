# Identity provider setup

**Date:** 2026-10-23
**Origin:** ID-01 Steps 1–2; Aditya's verified setup direction.

## Question
Which providers and setup boundaries support ID-READY?

## Options considered
- Firebase-managed temporary authentication, requiring a reviewed storage/flow redesign.
- Resend or SES email transport with application-owned authentication state.

## Selected choice
Use Microsoft SPA authorization code with PKCE, without a browser client secret
or Graph permissions. Registration accepts organizational and personal Microsoft
accounts. The registered client ID and callbacks are recorded in
[secret handling](../environment/secret-handling.md#id-01-microsoft-app-registration--user-reported-2026-10-22-140207-utc).
Use Microsoft public-cloud v2 discovery at
`https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration`.
Step 4 must validate signatures, issuer against the signed tenant/discovery rules,
client-ID audience, expiry and required claims; `common` is not an accepted literal
issuer. Do not impose an IISc tenant-ID allowlist.

Aditya reaffirmed the exact `@iisc.ac.in` email-domain rule on
2026-10-23 18:02:37 UTC after discussing mutable Microsoft claims and current
unverified-domain filtering. No bypass of this application's actual configuration
was demonstrated; this decision does not claim impossibility of bypass or prove
current mailbox control. Retain Microsoft SSO plus backend domain validation;
no additional regular-account mailbox OTP or IISc tenant allowlist is selected.

The backend must first validate the signed Microsoft v2 token, then require a
usable signed `email` claim whose parsed domain, case-normalized, is exactly
`iisc.ac.in`. Reject missing/malformed email and every other domain, including
subdomains/lookalikes; do not fall back to `preferred_username`, display name,
client-provided email or an unsigned decoded token. The durable account key stays
provider/validated issuer/subject, not email. The eligibility-policy choice is
resolved; implementation must still verify issuer/key/tenant binding, audience,
time claims and the reviewed login-attempt/replay design. Real configuration and
provider behavior remain integration checks; no extra flow is implied by them.

Current email routing is [Resend initially with SES fallback, four-hour runtime
refresh and bounded two-provider attempts](identity-email-routing.md), approved
by Aditya on2026-10-24. The following records the initial SES setup and its
remaining sandbox/production gates.

Use Amazon SES v2 in `ap-south-1` for Identity email delivery, proposed sender
`no-reply@clip-iisc.site`, retaining CLIP-owned OTP/password/session state.
CN-03 may reuse the provider/domain after its own owner review, without importing
Identity-private transport code or claiming its worker is implemented.
The reviewed shared task-role permission is applied. A verified sandbox delivery
check required adding the one controlled recipient identity alongside the sender
domain; the exact FromAddress condition remains. Preserve that private Terraform
input during sandbox work and review its removal after production access.

## Rationale
Matches the existing application-owned temporary authentication decision and
uses the existing AWS environment. Microsoft registration details and SES domain
verification are recorded; real task-role delivery is now human-confirmed.
Production-access/configuration review remains pending.

## Implications
The initial adapter is sandbox-only, explicitly selected, with at most five
controlled allowlisted destinations; production configuration refuses it.
No automatic SDK retry: a timed-out submission may already have been accepted.
The later approved email-routing decision allows one alternate real-provider
attempt with the same message despite that ambiguity; duplicates are possible.
Connect/read timeouts are 3/5 seconds per socket operation, not an absolute
end-to-end deadline. Step 5 owns OTP templates, throttling and challenge state;
no generic mail endpoint is introduced. General production delivery requires a
reviewed configuration change after provider access and delivery checks.
Cloud permission changes and each live test need their separate exact approval.
See [setup and pending checks](../environment/identity-provider-setup.md).

## Approver
Aditya (A): recorded Microsoft audience/domain/callback direction on 2026-10-22;
authorized completion of the Step 2 setup increment on 2026-10-23; reaffirmed
Microsoft SSO plus exact backend email-domain eligibility at18:02:37 UTC. Cloud changes,
live sends, and affected-owner review remain separate gates.

## Supersedes
None. Preserves [application-owned temporary authentication](temporary-authentication-storage.md)
and [provider safety](provider-safety.md).

## Provider references
- [Microsoft ID-token claims and authorization limits](https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference)
- [SES v2 SendEmail request/acceptance semantics](https://docs.aws.amazon.com/boto3/latest/reference/services/sesv2/client/send_email.html)
- [SDK total-attempt configuration](https://docs.aws.amazon.com/boto3/latest/guide/retries.html)

## Step11 browser implementation — 2026-10-24

Under Aditya's verified Step11 plan, pin MSAL Browser5.26.0 for the existing
Microsoft SPA code/PKCE flow. Fixed public client/common authority and exact
registered callback origins; no new tenant allowlist or Graph data permission.
The SDK supplies its standard OIDC defaults including offline_access in addition
to the requested openid/profile/email. Actual consent, redirect and cleanup must
be reviewed and observed before live enablement; no provider request occurred.

Default public build flag VITE_MICROSOFT_SIGN_IN_ENABLED is false. The synthetic
preview always disables Microsoft. Enabling a button does not wire or authorize
a server/provider: reviewed real API/key/DB/TLS/proxy/provider gates still apply.
The actual server alone validates claims/domain/nonce/cookie and creates a session.

A fresh server attempt gives public nonce/expiry plus HttpOnly cookie. Browser
stores only its random state/public nonce/expiry in CLIP's scoped session marker;
MSAL owns its sessionStorage redirect artifacts. No CLIP cookie bearer or raw
assertion is stored by application code or logged/server-persisted. Clear SDK
cache before new starts and on completed/failed callback, and consume CLIP's
marker before awaiting the response. Do not reuse SDK account/token cache or
silently acquire/refresh credentials. Cleanup cannot promise crash/backups/browser
storage erasure; actual SDK/browser artifact checks remain a live gate.

Matching state/nonce and fresh expiry precede one assertion exchange; backend
full verification is authoritative. Coalesce only in-flight callback work for
React StrictMode, never replay a settled sign-in result after logout. Safe GET
session recovery uses the existing generation fence. Callback strips response
query/fragment and the app uses no-referrer. Provider diagnostics stay out of UI/
logs. No global Microsoft logout, live call or deployment is approved here.
