# Identity sessions, password sign-in and bounded cleanup

**Date:** 2026-10-23
**Origin:** ID-01 Step7 verified plan, recorded2026-10-23 20:28:07 UTC.

## Question
How are browser sessions, password/login reset races and private-state cleanup enforced?

## Selected choice
Aditya verified the following implementation plan. Sessions use256-bit random
opaque cookie secrets and store only domain-separated SHA-256 digests. Seven-day
absolute and24-hour inactivity limits are server-enforced; temporary account
expiry caps both. Rotate on authentication; never return the session secret in
JSON or local storage. Secure host-only HttpOnly SameSite=Lax cookies in HTTPS;
explicit loopback-only development cookie configuration. No wildcard CORS or
browser-forwarded identity/source header is trusted.

Unsafe requests require an exact allowed Origin, JSON where a body is expected
and a non-simple request header. Authenticated mutations additionally require a
session-bound CSRF token from GET /auth/csrf, returned with no-store. Derive it
with HMAC from the high-entropy session secret; it is not a session credential.
POST /auth/microsoft/login-attempts creates a ten-minute server-bound opaque
attempt cookie/digest; derive the public nonce from that secret. Signed assertion
exchange consumes the attempt once in the account/session transaction. Browser
PKCE/state remain the approved Microsoft SPA flow; no new tenant/mailbox policy.

Password failures share a fixed15-minute target window, at most five; success
does not erase failures before expiry. Source limit100 attempts/15minutes,
including unknown accounts. Unknown/ineligible targets perform equivalent dummy
Argon2id work and expose generic401/429. Persist no raw email/IP/password.
OTP limits remain as previously approved. Serialize source then target then
account then session; reset and login cannot leave a pre-reset password session
usable. Reset atomically consumes OTP, updates hash and revokes all sessions;
it issues no new session or extended account lifetime. Account revocation stays
an internal trusted operation. Activation and Microsoft mapping/session creation
are atomic; no automatic retry of ambiguous credential exchanges.

## Cleanup design approved for implementation
Bound each table batch to100 by default (maximum1000), use trusted UTC and
recheck eligibility under compatible target/user/row locks. Dry-run is default;
apply is explicit and target-checked. No scheduler/deployed job is enabled.
Delete OTPs24hours after first unusable event (consumed/superseded/expiry),
terminal sessions after seven days (including idle expiry), and permanently
expired/revoked temporary credentials as soon as eligible so a later approved
hourly run can meet the within24-hour requirement. Remove obsolete operational
attempt/rate windows/events24hours after they cease being needed. Never delete
users, contacts, lifetime enrollment/request markers or key commitments here.
Step9 owns contact/profile cleanup. Fail closed on races/SQL errors and emit
only per-table counts. Separate exact cloud/target approval precedes any real
cleanup execution or enabling its schedule; fixture deletion is disposable only.

## Implications
Add nullable last-seen time for legacy sessions (legacy sessions cannot silently
become authenticated), bounded password/source windows and Microsoft attempts.
Preserve prior data with forward-only migrations; occupied rollback fails closed.
Implement actual HTTP handlers/security with explicit trusted dependencies;
normal unconfigured startup remains health-only. Runtime secrets/DB roles and
provider/browser/current-main/peer acceptance remain real integration gates.

## Approver
Aditya(A), explicit verification of Step7 settings/contracts/cleanup plan.

## Supersedes
Resolves session/login/cleanup implementation choices left open in
[temporary authentication](temporary-authentication-storage.md), preserving
[private-data retention](private-data-retention.md) and Microsoft/OTP decisions.
