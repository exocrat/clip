# Identity email delivery: Resend and SES with four-hour refresh

**Date:** 2026-10-24
**Origin:** Aditya(A) approved Resend initially, SES later, then specified a
four-hour refresh and one alternate-provider attempt if the first fails.
**Decision recorded:** 2026-10-24 13:57:46 UTC.

## Selected behavior

Retain application-owned OTP/password/session state and the existing private
EmailSender signature. Support real Resend and SES adapters. Configure SES as the
preferred primary and Resend as its alternate through runtime configuration.
One logical OTP ticket may dispatch once to a router. Router attempts primary
once; on any reported exception, including an ambiguous timeout, attempt the
other real provider once using the identical recipient/subject/body/OTP. Stop on
acceptance or after two failures. No third attempt, background retry, permanent
primary promotion, new challenge, fake fallback or extended expiry. A provider
failure never authenticates anyone. Generic public acknowledgement remains the
same for eligible/ineligible targets, send failure and uncertain outcomes.

Aditya's fallback direction replaces the previous no-cross-provider-retry policy.
An uncertain first request can have been accepted: both providers may deliver the
same code. This behavior cannot promise exactly-once delivery across providers.
Provider acceptance is not inbox delivery, and a later bounce is not an immediate
send exception. No webhook-triggered fallback is included. Per-provider internal
retries remain disabled. Existing OTP throttles/resend/attempt/replay limits hold.

## Runtime configuration

Store version, primary provider and Resend API key together in one approved SSM
Standard SecureString using the existing aws/ssm strategy. Read one parameter
version as a complete in-memory snapshot, without raw output or files. Keep
provider credentials/recipients out of repr/logs/evidence. Use task-role AWS
credentials for SSM and SES, a sending-only/domain-restricted Resend key, fixed
TLS endpoints and no redirect/custom endpoint or proxy override.

Refresh lazily at first send, then first send at/after14400monotonic seconds
from the successful load, once per process. No four-hour polling thread is
needed. Concurrent requests share refresh work and each send retains its complete
snapshot through both attempts. A preference/key update can take up to four hours
to reach each running process (or until its next send after that). Existing
in-flight sends can finish on the previous snapshot. A failed or invalid refresh
sends nothing; do not silently keep expired settings. No fake/disabled result is
successful delivery. The cache is process memory, not durable message storage.

Both adapters must be present and approved/configured in the initial deployment.
After that, changing primary/key in SSM needs no rebuild, new task definition or
restart. SSM task-role read permission, runtime source wiring and outbound access
must already exist. Current local components alone do not meet those deployment
prerequisites. Changes to recipient restrictions/provider permissions are separate
reviewed configuration work, not a way to bypass SES sandbox restrictions.

## Current boundaries and acceptance

Suraj's 2026-11-03 [hosted functional repair](hosted-functional-repair.md)
supersedes the recipient restriction below only for the explicit real hosted
runtime. Both adapters use the same hosted recipient policy; local/standalone
probes retain controlled recipients. Provider order, refresh and bounded fallback
remain. The hosted repair and inbox checks were subsequently recorded; ID-01 is marked
complete in the work log. The following historical limits describe the earlier
staged configuration, not current cloud state. Local/standalone probes retain
controlled recipients; the explicit real hosted Identity runtime permits its
account destination. SES production access was later recorded on 2026-10-28. Refresh
current runtime preference, role policy and provider state before a new operation.
Never paste keys or real OTPs in chat. A decision record is not approval for a live
send or cloud policy change.

CN-03 adopted SES-first delivery through its own public transport and owner review;
it must not import Identity-private modules. ID-01 and CN-03 task status is recorded
in the work log; their task completion does not assert current live provider state.

## Approver and superseded scope

Aditya(A), explicit instructions in this session. Supersedes SES-only selection
and no cross-provider retry in the [Identity provider decision](identity-provider-setup.md)
and the broad no-real-fallback phrase in [provider safety](provider-safety.md)
only for this bounded Identity real-email pair. Fake rejection, disabled defaults,
Microsoft policy, OTP storage/limits and action-specific approval gates remain.

## API references checked

- [Resend send-email API](https://resend.com/docs/api-reference/emails/send-email)
- [Resend API keys](https://resend.com/docs/dashboard/api-keys/introduction)
- [Resend verified domains](https://resend.com/docs/dashboard/domains/introduction)
- [ECS startup-only injection versus runtime retrieval](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-ssm-paramstore.html)

## Sender choice — recorded2026-10-24 16:14:25 UTC

Aditya selected `verify@clip-iisc.site` for Identity verification and password-reset
emails across both providers. Avoid generic no-reply/marketing-style senders in
project email; choose future purpose-specific addresses through their owning task.
Human-confirmed Resend delivery to IISc supports this choice but does not prove
which filter rejected older messages. Preserve no-reply historical evidence.
Local adapters/default examples and desired SES FromAddress policy now use verify.
Live SES permission and inbox results were later checked in the task evidence;
current policy is not asserted here. Keep SES sandbox recipient limits and
production guards. Current routing schema remains unchanged: a
primary/key update cannot choose arbitrary sender addresses. No new DNS or mailbox
provisioning is implied by selecting an address on the verified sending domain.
