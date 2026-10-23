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
