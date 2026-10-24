# ID-01 Step10 — deterministic fixtures and security integration coverage

Recorded2026-10-24 07:32:48 UTC. Aditya(A), task/id-01-identity at cfb9509 plus uncommitted Step10. The human
verified the Step10 plan before implementation. Aditya verified the local result and authorized its checkpoint commit
on2026-10-24 08:45:31 UTC (recording time).

## Audit, dependencies and execution mode

No material task-definition gap found against canonical Step10, Identity/
combined contracts, trusted-caller/provider-safety/retention/session/sharing
records and the agent/human checklists. Step10 builds on verified local Steps3–9
and accepted PRE-00/DL-00. Existing deterministic OTP/storage/session tests and
PD-10's guarded scripted identity provider are reused, not replaced by duplicate
fixtures. Microsoft tests had wall-clock claims; missing coverage included reset
preserving source contacts, bounded profile cleanup and concurrent denied writes.

Actual disposable PostgreSQL18.6/schema/services/HTTP and actual RSA/date checks
are exercised. Synthetic assertions/mail and controlled sharing preconditions
remain isolated provider/Conversation substitutes allowed for ID-01 Steps1–11.
No live provider call, retained/shared database cleanup or external action occurs.
SES production access is not required for this local step. No actual provider,
Conversations membership, browser or deployed runtime acceptance is inferred.

## Changed code/configuration and behavior

| Path | Purpose and important behavior |
|---|---|
| apps/api/tests/domains/identity/conftest.py | Reuses one ephemeral RSA key per module; each requesting test gets its own fixed UTC JWT clock and signer. Explicit jwt_clock patches only PyJWT's datetime lookup for real date validation and restores it at teardown. Signature/issuer/audience/date checks stay enabled; no system-wide clock patch, autouse authentication or runtime selection. Registers the reusable temporary lifecycle fixture. |
| apps/api/tests/domains/identity/microsoft_fixtures.py | SignedTokens takes an explicit clock and transient key; claims no longer depend on wall time. Expected claims/scenarios are deterministic; fresh random RSA material/signatures are deliberately not a reproducible byte artifact. No private key/assertion file or real provider. |
| apps/api/tests/domains/identity/session_fixtures.py | temporary_state creates active/expired/revoked scenarios through actual activation, controlled expiry and internal revocation, retaining original grants for stale-context checks. No fabricated account SQL or public bypass. |
| apps/api/tests/domains/identity/test_microsoft.py | Uses the explicit fixture clock and adds just-before/exact exp/nbf/iat acceptance boundaries plus fixed-claim reproducibility. Existing valid/wrong-signature/unsigned/non-IISc/provider-negative cases remain intact. |
| apps/api/tests/domains/identity/test_identity_security_integration.py | Adds11 actual local tests: lifecycle authorization, explicitly selected auth fake cannot create a public session, production construction rejection even with unvalidated Settings, reset/retry preserving contacts/name/login/lifetime while revoking sessions and old CSRF, exact unused-OTP and revoked-session retention, bounded cleanup excluding active accounts, concurrent terminal cleanup versus stale source writes. Values remain synthetic/transient; Captures actual non-propagating application records and checks approved metadata-only output without private input. |

Identity domain/API README, command registry, this evidence and the work-log
checkpoint document the result and integration limits. No production/core/public
contract/schema/generated/dependency/frontend code is changed by this step.
[Source hashes](source-hashes.json) pin all5 changed/new Python test/fixture files.

## Step10 requirement-to-evidence map

All paths below are relative to apps/api/tests/domains/identity unless otherwise
stated. These are real local behavior checks, not evidence of a deployed flow.

| Requirement | Existing and added evidence |
|---|---|
| Valid/expired/wrong-signature/non-IISc Microsoft assertions | test_microsoft.py signed RSA negatives, required claims, domain spoofing, provider key/cache failures; new exact exp/nbf/iat boundaries and fixed claims. microsoft_fixtures.py and explicit jwt_clock retain real verification. |
| Temporary lifecycle and stale permission denial | test_temporary_activation_postgres.py exact expiry/non-renewal/guard tests; test_capabilities_postgres.py fresh class/state; new temporary_state and lifecycle integration checks use real activation/revocation. |
| Auth fake rejected in production | Reuse tests/fixtures/core/clip_test_fixtures/providers.py guarded make_test_provider. Existing shared provider tests reject even model_construct bypass; core/test_security_boundaries.py launches actual production startup for every nonempty fake-selector subset and unsafe controls. New domain checks consume the guarded fake explicitly, reject production and prove it cannot authenticate browser headers. |
| OTP expiry, three attempts across latest resend window, replay, retries/uncertain sends | test_temporary_policy.py; test_temporary_postgres.py atomic counters/resend/latest-expiry/replay/duplicate/race tests; test_temporary_delivery.py one-shot/uncertain-failure/no retry; new unused-expired OTP exact24-hour purge and retained request marker. |
| Session/password retention cutoffs and revocation | test_sessions_postgres.py exact idle/absolute/temporary expiry; test_identity_cleanup.py seven-day idle terminal, immediate revoked/expired credential eligibility; new revoked-session exact seven-day boundary. |
| Contact/profile cutoff, immediate deletion and preserved guards | test_contacts.py and test_contacts_http.py own deletion/current reads; test_identity_cleanup.py just-before/exact30-day earliest terminal, regular revocation and lifetime markers; new bounded batches excluding active regular accounts and cleanup race rejecting source restoration. |
| Login/reset concurrency, rollback and idempotency | test_sessions_postgres.py concurrent old-password login/reset, atomic rollback/session revocation and Microsoft attempt race; test_temporary_activation_postgres.py concurrent single enrollment; new HTTP reset request retry and consumed proof replay preserve original account lifetime. |
| Local auth/OTP/session/contact integration and privacy | test_identity_http.py actual registration/login/reset/nonce/CSRF/origin/no-store and provider acknowledgement ordering; test_contacts_http.py own-only CRUD/scope and safe errors; new full register/contact/profile/reset/relogin/delete/revoke journey, old CSRF denial and private-value log assertions. |

## Actual checks

- Controlled-time Microsoft and existing Microsoft SQL/Identity HTTP selection:
88 passed, warnings treated as errors.
- New security integration selection:11 passed, warnings treated as errors.
- Strengthened the new privacy assertion to attach the real non-propagating clip
logger to capture, require actual records/statuses, and validate its formatted
metadata-only output. The revised11-test integration selection passed again.
This final focused run checks the strengthened assertion; the aggregate had
already collected the earlier version. No production behavior changed.
- Full make check passed all11 gates:767 Python,63 data and16 web tests;
Black116files, CI parity, zero boundary violations,8 current generated artifacts,
contract types, web lint/types/build,35 wrapper safety cases, actual PostgreSQL18.6
clean/repeat/five-smoke/upgrade/down/reapply and Gitleaks8.30.1 source snapshot.
All focused runs passed; no failed/skipped check is being accepted as a pass.
- Final source hashes cover5 Python test/fixture files;151 changed/new Markdown
local file targets resolved before final work-log/root README metadata links.
The final privacy-strengthened file is formatted and independently tested.
- Relevant checklist fixture isolation, production fake rejection, actual owned
storage/HTTP, aware time, privacy, authorization, retries/transaction races and
registered checks applied. Task-wide browser/provider/peer/readiness review
remains open. Linux ARM64 local evidence is not new native AMD64/macOS proof.

## Remaining gates / next checkpoint

Step10 local result is human-verified and its checkpoint commit authorized. Preview
only: Step11 responsive Identity UI/controlled-provider UI integration and human
browser checks needs its own understanding/ownership verification. No UI work
has begun. ID-READY still needs actual runtime/key/DB/TLS/proxy/provider/browser
configuration, current-main/PR10 migration reconciliation and independent
reviewed merge. Actual CN-02 sharing membership/confirmation/client encryption
and Step14 final consumer matrix retain their original owners/gates. Cleanup
scheduling/live apply requires separate exact-target approval and observed runs.
No FR/NFR/readiness/full-task completion is claimed. Task-wide closeout is open.
