# Identity domain

Owner: A — Aditya. Required feature implementation belongs to ID-01 in the [domain task list](../../../../../docs/tasks/domain-task-list.md), after the required foundation and contract gates. Step 2 now supplies an isolated sandbox SES transport in `email.py`; Step4 now supplies private Microsoft token validation and transactional account mapping; public authentication/session, capability and contact integration remain pending.

Identity owns its authentication/capability/contact behavior. Shared technical primitives belong in `app.core`. Other domains must use reviewed public interfaces rather than importing private implementation or reading private tables. `public.py` contains the generated reviewed DL-00 declarations. The sandbox transport is private to Identity and introduces no routes, schemas or authorization shortcuts. See the [provider setup](../../../../../docs/environment/identity-provider-setup.md) for configuration and pending real checks.

`email_smoke.py` is a separately gated one-shot ECS command that exercises
`email.py` using the real application task role. It is not wired to an HTTP route
or normal API startup. It sends at most one fixed synthetic message, only in
explicit approved test mode, and emits no recipient/content/credential data.

## Private Microsoft validation/account mapping — Step4

`microsoft.py` owns fixed-origin TLS discovery/JWKS with a five-minute bounded
cache and30-second refresh throttle, signature/issuer/key/tenant/audience/time
validation and required trusted nonce. Only signed email whose parsed domain is
exactly iisc.ac.in grants eligibility; malformed/absent claims fail closed.
This implements Aditya's reviewed SSO/domain policy without claiming current
mailbox control. `MicrosoftIdentity` hides private claims in repr and is not a
credential/CallerContext. Real factory selection is local/test-only.

`microsoft_accounts.py` takes a trusted fresh PostgreSQL connection factory. It
serializes the provider/issuer/subject key with a transaction advisory lock and
uses the existing unique mapping plus one atomic user/mapping write. Conflicting
callbacks do not create orphan users. Existing ineligible accounts stay denied.
Provider errors are safe503; invalid tokens/accounts safe401; token/email/nonce
are not persisted or logged. No sessions or caller contexts are created.

The private `authenticate` method requires a trusted expected nonce and is NOT
a session-creation endpoint. Step7 now supplies server attempt redemption and explicit cookie/CSRF/session
HTTP composition. Browser PKCE/state and real provider/runtime wiring still
need their original checks before live enablement.
Synthetic keys/documents are injected only by tests; production never selects
a fake key source via configuration. Real Microsoft claims/callback and runtime
DB-role checks remain pending.

## Private temporary-authentication primitives — Step 5 (partial)

`temporary_crypto.py` normalizes protected login identifiers and binds keyed OTP
verifiers and AES-GCM target ciphertext to one challenge/purpose/expiry.
`temporary_policy.py` models three failed verifications shared across resends
until the latest OTP expires. Its pure values require transactional persistence
and locking before they can enforce abuse limits.

`temporary_delivery.py` prepares a uniform six-digit code with an in-memory,
one-shot delivery ticket using the existing `email.py` transport. Persist only
the explicit protected fields, never the whole preparation object or ticket.
After a newly eligible reservation commits, dispatch once outside the async
event loop; discard duplicate/ineligible tickets. Expired, discarded or already
attempted tickets cannot submit. An uncertain provider outcome is not retried.
Discarding releases Python references; it does not promise memory zeroization.

`temporary_challenges.py` now supplies private PostgreSQL enforcement for
idempotency, eligibility, send limits, atomic verification/consumption and
key-version continuity. These modules
are not wired to startup or public routes and grant no account/session authority.
Minimal request markers have approved service-lifetime retention. Actual
provider/public integration and the separate private-state cleanup design
remain pending. Public acceptance must not reveal eligibility or dispatch
outcome; response timing/background execution still need integration checks.

`PostgresTemporaryChallenges.start` commits a generic acknowledgement and optional
private one-shot send ticket. The HTTP adapter must serialize only ID/expiry and
finish a uniform response before dispatch outside the event loop; ticket presence
and provider status must never reach the client. Committed-but-unsent requests
remain unsent on retries; deliberate resend needs a new operation ID and ordinary
cooldown/limits. No durable raw-code outbox or automatic retry is introduced.

`consume` invokes a trusted callback on the same connection/transaction as code
consumption. It commits wrong-code counters before returning safe422; exhausted
windows return429. Superseded/expired/consumed/wrong-purpose challenges fail.
Suppressed reset acknowledgements follow the same failed-attempt statuses as
eligible requests. Callback failure rolls back consumption and its own SQL.
The callback must not send, commit, open another connection or invert target/user
lock order. Step6/7 must still implement real activation/password/session effects.

First key adoption rejects existing temporary credentials/enrollments/challenges;
current deployments require reviewed migration rather than guessed keys. Existing
commitments reject key/version replacement. Runtime secret references and DB role
permissions remain deployment review gates; tests inject synthetic keys only.
No public route or production factory is added, and real provider/public timing
checks are pending. Retention cleanup remains separately gated.

## Private temporary activation and current-state check — Step6

`temporary_passwords.py` uses pinned argon2-cffi25.1.0 (bindings26.1.0 in the
root lock) with explicit Argon2id19MiB/t2/p1,16-byte random salt and32-byte hash.
Password inputs must be SecretStr,15–128 Unicode characters including spaces;
no trimming/normalization/truncation. Reject malformed UTF-8 text safely. This
module hashes only; routine password authentication/reset remain Step7.

`temporary_accounts.py` composes with Step5's actual consume transaction.
`TemporaryActivation.activate` accepts challenge ID, code and secret password,
recovering the login solely from protected OTP state. After initial proof, hash
inside the target-locked transaction; insert active temporary user, protected
credential and service-lifetime enrollment guard, then bind the consumed OTP to
that user. Every write and consumption roll back on hashing/SQL failure.
Concurrent/replayed verification creates at most one account and never renews
its original336-hour activation/expiry. No email/password hash is returned.

`PostgresTemporaryAccounts.require_current` is a private fresh-state gate for a
caller already authenticated by later session wiring. It checks caller expiry,
actual temporary class/active status/intact profile and account lifetime on each
call, with bounded SQL waits. Cached valid_until cannot extend account expiry or
hide revocation. It does not authenticate a caller, install request scope or
supply marketplace capabilities. Step7/8 must wire it into actual authorization;
Step11/12 must verify public routes/browser/provider behavior. Activation returns
private account facts only; the reviewed public session response remains pending.
No migration, session/CallerContext issuance, cleanup job or route is added.

## Sessions, actual HTTP composition and bounded cleanup — Step7

`IdentitySessions` uses opaque256-bit secrets and domain-separated SHA-256
session/attempt digests. Seven-day absolute and24-hour idle expiry are checked
server-side, capped by temporary lifetime. Fresh authentication locks user then
session and establishes CallerContext; raw cookie/nonce/assertion never persists.
A real dummy Argon2 hash makes unknown/ineligible password checks equivalent.
Five failures per target/15minutes survive successful logins; source budget100
requests/15minutes is shared across credential/attempt requests. No password
state is exposed. Reset hashes/consumes/revokes all sessions under the same target/
user lock as login. Account revocation is internal; no new public admin route.

`microsoft_accounts.py.get_or_create_in` and
`temporary_accounts.py.activate_with` compose account and session writes in the
same transaction. `temporary_passwords.py.verify` bounds trusted stored hash
parameters before real verification. Reset state races return409 only after
correct OTP proof; wrong/unknown codes retain422/429 behavior.

`http.py.create_identity_app` supplies actual reviewed auth/GET /me routes with
explicit trusted services, real validator and sender. It does not discover keys,
DB URLs, cloud roles or fake providers; unconfigured app.main stays health-only.
Middleware refuses invalid TLS/origin/development peer before reading sessions,
sets only trusted request scope, requires non-simple unsafe headers and
session-bound CSRF, and emits no-store. Secure HttpOnly host-only Lax cookies
carry bearers; JSON contains only SessionView/nonce/CSRF/acknowledgements. Explicit
insecure development mode requires both loopback origins and transport. CORS has
exact origins/headers. Transport peer IP is used; deployment proxy/TLS/source
adaptation requires review before public enablement. Never trust arbitrary XFF.

Microsoft login-attempt cookie/digest expires after ten minutes; public nonce is
HMAC-derived from that private secret, consumed once with mapping/session commit.
Browser MSAL PKCE/state still needs actual Step11 integration. No tenant/domain
policy changed. OTP handlers commit generic acknowledgements before background
one-shot dispatch outside the event loop; ambiguous sends never auto-retry.
This is local HTTP integration evidence, not an actual provider/inbox/browser run.

`cleanup.py.IdentityCleanup.run` is count-only by default, bounded per table and
rechecks cutoffs under target/user locks. Apply commits per candidate and may be
partial on failure; rerun safely rechecks eligibility. Never delete users,
lifetime markers or key bindings. Step9 extends this mechanism to remove
source contacts and clear display names after thirty days of terminal state. `scripts/identity_cleanup.py` reads
only the explicit DSN environment input and requires matching expected database;
--apply is an explicit write, not approval to run against retained/cloud data.
No scheduler is enabled. Exact deployment/operator approval and observed runs
are still required before claiming production retention deadlines are met.

## Current capabilities and public eligibility — Step8

`capabilities.py` supplies an explicit allowlist for each active class. Both may
browse/search/save, manage own wanted/profile/contacts, start listing-origin
conversations, use existing authorized conversations, submit offers and share
selected own contacts. Only regular accounts may manage sale listings or start
wanted-response conversations. New/unmapped enum categories default to denial.
Resource ownership, membership, consent and availability remain with owners.

`PostgresCapabilities.require_capability` accepts only an already-authenticated
CallerContext and code-owned Capability. It rechecks account status/class/expiry/
profile and caller deadline, rejecting stale or mismatched facts. It does not
authenticate a constructed caller. Existing GET /me now uses the fresh own-profile
gate; HTTP middleware still establishes actual session context first.

The real async `check_account_eligibility` reads only lifecycle fields outside
the event loop. Returns exactly AccountEligibility{eligible:bool}; missing/
ineligible=false, unavailable=503, optional required class is an exact match.
An offline account may be eligible; this operation is not authentication. IDs
must originate from trusted context/authoritative relationships. No profile,
contact, denial reason or new HTTP user-directory endpoint is exposed.

Canonical RUNTIME_BINDINGS and the generator produce a thin public wrapper for
only this function, using `core.runtime_bindings` scoped dispatch. `sessions.py`
constructs the real provider without I/O, and `http.py` binds it per request;
parallel runtimes cannot overwrite each other. Explicit worker scopes are also
required. No mutable global provider or fake fallback; missing/wrong results
fail503. Other public contact/provider declarations remain unimplemented until
their owning increments. Full consumer API matrix remains Step14, and default
app.main/runtime/provider/browser/cloud readiness gates remain unchanged.

## Own profile/contacts and deliberate sharing — Step9

`contacts.py.PostgresContacts` locks the current user before own source fields,
rechecks lifecycle/caller/capability and uses field-only upserts/deletes. Display
name omission preserves, null clears and valid text trims. Syntax-only email,
E.164 phone and UPI validation never verifies ownership/payment or changes login.
The HTTP factory exposes the reviewed own-profile PATCH and own-contact GET/PUT/
DELETE routes with its existing session/origin/CSRF/no-store protections.
`sessions.py` constructs the provider with explicit connection/clock dependencies.
HTTP imports generated runtime models to share nominal types with its services.

Generated public contact dispatch requires the server-only ContactSharingContext
installed in a technical runtime-claims scope after Conversations verifies actual
membership and UI confirmation. Options expose flags only; selection reveals
only requested/confirmed/current own values; removed fields fail422. Missing
claims fail403 and no binding fails503. Identity reads no Conversation tables.
The HTTP boundary clears ambient claims; trusted composition may set an inner
scope. The notification recipient operation remains unimplemented. See the
[reviewed mechanism](../../../../../docs/decisions/identity-contact-sharing-and-cleanup.md).

Cleanup clears display names/marks profiles and deletes source contacts at the
thirty-day terminal cutoff under the same user lock. Users, enrollment/request
markers and key commitments survive. No job or live cleanup is enabled. Actual
CN participation/consent/client encryption, runtime/provider/browser/current-main
reconciliation and ID-READY acceptance remain pending.

## Deterministic security fixtures and integration coverage — Step10

Owned tests now explicitly control PyJWT time as well as the existing session/
OTP/retention clock, retaining real RSA and claim checks. Temporary lifecycle
fixtures use actual activation/expiry/revocation. The existing guarded scripted
auth provider is test-only and cannot install a browser session or run in
production. Additional real local HTTP/SQL checks connect contact/profile edits
to reset, relogin, deletion, revocation and bounded cleanup/concurrent denied
writes. See [Step10 coverage/evidence](../../../../../docs/evaluation/identity/id-01-step-10/README.md).
These are synthetic controlled provider tests; actual deployed/browser/CN and
ID-READY gates remain open. No production implementation changed in Step10.
