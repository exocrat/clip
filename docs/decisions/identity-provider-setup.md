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

Aditya specified the exact `@iisc.ac.in` email-domain rule for regular accounts.
This rule is recorded direction, not proof of current institutional mailbox
control: Microsoft email/username claims can be mutable or absent. Required-claim
selection and the security reconciliation with the reviewed Identity eligibility
contract remain a Step 4 decision gate; do not silently authorize from an
unvalidated string or invent a mailbox-control guarantee.

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
Connect/read timeouts are 3/5 seconds per socket operation, not an absolute
end-to-end deadline. Step 5 owns OTP templates, throttling and challenge state;
no generic mail endpoint is introduced. General production delivery requires a
reviewed configuration change after provider access and delivery checks.
Cloud permission changes and each live test need their separate exact approval.
See [setup and pending checks](../environment/identity-provider-setup.md).

## Approver
Aditya (A): recorded Microsoft audience/domain/callback direction on 2026-10-22;
authorized completion of the Step 2 setup increment on 2026-10-23. Cloud changes,
live sends, and affected-owner review remain separate gates.

## Supersedes
None. Preserves [application-owned temporary authentication](temporary-authentication-storage.md)
and [provider safety](provider-safety.md).

## Provider references
- [Microsoft ID-token claims and authorization limits](https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference)
- [SES v2 SendEmail request/acceptance semantics](https://docs.aws.amazon.com/boto3/latest/reference/services/sesv2/client/send_email.html)
- [SDK total-attempt configuration](https://docs.aws.amazon.com/boto3/latest/guide/retries.html)
