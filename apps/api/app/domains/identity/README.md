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
a session-creation endpoint. Browser PKCE/state, login-attempt creation and
single-use redemption, cookie/CSRF/lifetime/session wiring need their explicit
design/real checks before exposing the existing public contract route.
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
