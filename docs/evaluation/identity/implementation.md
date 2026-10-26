# ID-01 implementation evidence

This is the compact record of local Steps3–11. Aditya verified these increments;
required real runtime/provider/device checks remain in [the handoff](integration.md).
Detailed original per-file reports are recoverable using [the archive map](archive-map.json).
The [contract](../../../contracts/identity.md), decisions and actual source own behavior.
All check results below describe their recorded revisions, not a new rerun.

## Step 3

Identity-only migration `20261023173439` adds profile/contact bounds, consistent
revocation events and immutable provider mapping. Occupied/incompatible changes
fail atomically; rollback removes only its own guards and preserves data. Actual
PostgreSQL18.6 clean/repeat/upgrade/down/reapply passed. Full gate:458Python,
63data,16web. Original shared-main deferral was later resolved locally in Step12.
[Source hashes](id-01-step-3/source-hashes.json).

## Step 4

Real Microsoft RSA/JWKS/discovery validation enforces signature, issuer/tenant
binding, audience, UTC time, nonce and exact signed email domain iisc.ac.in.
No preferred_username/client-domain fallback or IISc tenant allowlist. Atomic
provider/issuer/subject mapping prevents duplicate/orphan/reactivated users;
16concurrent callbacks produced one account/mapping. Metadata fetch is bounded,
fixed-origin TLS and cached; safe401/503, no token logging/persistence.
53token tests and actual SQL checks passed; full gate519Python/63data/16web.
An initial bootstrap-socket fixture error was corrected; no live user sign-in
was proved. [Source hashes](id-01-step-4/source-hashes.json).

## Step 5

Application-owned OTP reservation/consumption is transactional and purpose-bound.
Six digits;10minutes; only newest challenge works; approved resend/rate limits.
Three verification failures share a window through the latest OTP expiry.
Protected verifier/lookup/encrypted target use independent keys; raw codes remain
transient. Idempotent requests cannot resend after challenge cleanup: minimal
keyed acknowledgement markers persist for service lifetime under the reviewed
retention exception. Provider uncertainty does not activate an account.
Full gate563Python/63data/16web. Password minimum later changed to8characters.
[Source hashes](id-01-step-5/source-hashes.json),
[storage decision](../../decisions/temporary-authentication-storage.md).

## Step 6

Only successful initial OTP verification activates a temporary account. Lifetime
is exactly14days from that event; login, resend and reset never renew it. Atomic
activation/consumption and fresh lifecycle checks deny expired/revoked accounts.
Actual SQL and controlled-time/concurrency checks passed; full gate597Python/
63data/16web. [Source hashes](id-01-step-6/source-hashes.json).

## Step 7

Opaque256-bit cookie sessions store only domain-separated digests;7day absolute,
24hour idle and temporary-account expiry caps. Secure host-only HttpOnly Lax
cookies outside explicit loopback development. Exact Origin/non-simple unsafe
header, JSON enforcement and session-bound CSRF protect mutations. Microsoft
attempt cookie/nonce expires after10minutes and is consumed once.

Temporary passwords use reviewed Argon2id; current bounds8–128Unicode code points,
without trimming. Reset consumes OTP, changes hash and revokes all sessions
atomically, issuing no session/lifetime extension. Login/reset races serialize.
Password limits:5target failures/15minutes and100source attempts/15minutes;
unknown/ineligible accounts perform dummy hash work with generic errors.

Cleanup is bounded, dry-run by default, explicit target/apply and approved design:
OTP24hours after terminal state, terminal sessions7days, permanently unusable
password hashes within24hours. Preserve permanent enrollment/request/key guards.
No deployed scheduler enabled. Full gate646Python/63data/16web; real SQL/HTTP/
RSA/Argon2, cleanup and concurrency passed.
[Source hashes](id-01-step-7/source-hashes.json),
[session/cleanup decision](../../decisions/identity-sessions-and-cleanup.md).

## Step 8

Server capability policy denies pending/expired/revoked/stale contexts. Temporary
accounts may browse open Wanted Requests but cannot initiate wanted-response
conversations or manage sale listings; other approved capabilities remain.
Owners still enforce resource ownership/membership/state. Public eligibility is
UUID/optional-class in, eligible boolean out; no user directory/private reason.

Immutable request-scoped technical bindings connect reviewed generated public
functions to real services, reset on exit/failure and isolate concurrent apps.
No unbound/fake fallback. Scoped declaration generation remains source-driven;
workers require their own explicit trusted scope. Full gate709Python/63data/16web.
[Source hashes](id-01-step-8/source-hashes.json),
[binding decision](../../decisions/identity-capabilities-and-runtime-binding.md).

## Step 9

Authorized own display-name/contact read/update/delete APIs validate inputs and
separate mutable sharing fields from immutable login identity. Only selected
own contact fields may be disclosed under trusted participant/confirmation
context; browser-supplied IDs grant no authority. HTTP clears ambient claims.
Contact values never enter general profiles/logs/errors; deletion is immediate.
Profile/contact cleanup is due within30days of permanent expiry/revocation.
Real CN02 consent/participant/encryption integration stays pending with its owner.
Full gate752Python/63data/16web.
[Source hashes](id-01-step-9/source-hashes.json),
[sharing/cleanup decision](../../decisions/identity-contact-sharing-and-cleanup.md).

## Step 10

Deterministic synthetic valid/expired/bad-signature/non-IISc JWTs, OTP/account/
session states and actual SQL integration cover privacy, lifecycle, revocation,
cleanup boundaries, enrollment preservation, duplicate/retry and concurrent reset/
login behavior. Production rejects auth fakes; controlled providers do not prove
live provider behavior or final consumer authorization. Full gate767Python/
63data/16web; focused security coverage passed.
[Source hashes](id-01-step-10/source-hashes.json).

## Step 11

| Verified increment | Behavior and recorded checks | Source snapshot |
| --- | --- | --- |
| Sign-in/registration/OTP | Responsive forms, resend/uncertain outcomes, one-shot writes, session/logout/expiry states. Approved password minimum changed15to8; full771Python/63data/32web. | [Initial](id-01-step-11/source-hashes.json) |
| Forgotten-password/reset | No account enumeration or automatic ambiguous retry; successful reset leads to normal password login. Human-verified. | [Recovery](id-01-step-11/reset-source-hashes.json) |
| Own contacts | Current-user editor with CSRF/refetch, field validation/delete, actor/generation fencing and private-state clearing. Preserve focus and independent drafts. Human-verified. | [Contacts](id-01-step-11/contacts-source-hashes.json) |
| Microsoft button/callback | Lazy pinned MSAL5.26.0, default-disabled flag, exact registered origins and unconditional preview block. Fresh server nonce, SDK PKCE/state, one assertion exchange, safe errors/status recovery. Full771Python/63data/92web. | [Microsoft](id-01-step-11/microsoft-source-hashes.json) |

No silent token acquisition or application bearer cache; SDK sessionStorage
artifacts are cleared on initialized paths and own marker/response URL removed.
Actual consent/cache erasure/PKCE/provider behavior still needs observation.
Callback recovery reports an existing CLIP session rather than fresh IISc proof;
generation fencing prevents stale GETs reviving logout state.

Controlled SDK/DOM tests and local viewport checks do not establish real-phone
keyboard or real provider behavior. The synthetic loopback preview has its own
capped disposable SQL database/mailbox, refuses deployment and contacts neither
SES nor Microsoft. Only approved public feature entry points/shared pages changed.
There is no separately approved profile-edit page; P11 is the contact editor.

## Corrections and limits

Original reports retain corrected SDK type-option/finally handling, fixture
bootstrap/clock/health-route assumptions and ambiguous-request handling. These
were corrected and checked, not skipped. Exact logs, per-file explanations and
historical source revisions remain in Git and the work log. Latest combined
regression and main reconciliation evidence is [separate](integration.md#main-reconciliation).
No native macOS/device, deployed runtime, cleanup schedule, FR03 consumer matrix
or ID-READY acceptance is inferred from these local checks.
