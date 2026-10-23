# ID-01 Step5 — temporary OTP transaction checkpoint

Recorded2026-10-23 19:39:55 UTC. Aditya(A), task/id-01-identity at7d6be86 plus
uncommitted Step5 changes. Private implementation/checks performed; Aditya verified the private result
on2026-10-23 19:50:57 UTC. The full step/readiness is not complete.

## Audit, scope and dependencies

The reviewed Identity contract at44cd8ff requires initial/reset email challenges,
three approved failed verifications through latest-code expiry, safe provider
failure, single use and account non-renewal. The verified plan clarified task
Steps5/7/11 to include reset challenges/password sign-in/reset UI. Step3's real
schema and Step2's reviewed sandbox SES adapter exist. Isolated Steps1–11 are
permitted by the staging guide; provider/public/UI/current-main acceptance is
still required. No new task-definition gap was silently repaired here.

Aditya approved service-lifetime minimal operation marker retention on
2026-10-23 19:53:44 UTC. Only keyed request digest, key version, challenge ID and
original expiry survive; no target/IP digest, email, code, verifier or ciphertext.
The schema separates markers from OTP/private rate state and implements no
cleanup job. Existing OTP retention is unchanged. Destructive
cleanup remains Step7's separately approved design. Public response timing,
actual runtime secret/DB permissions, provider send and later account/session
integration are pending; private tests cannot accept ID-READY.

## Code/configuration changes and relationship

| Path | Purpose and important behavior |
|---|---|
| apps/api/app/domains/identity/temporary_crypto.py | ASCII trim/lowercase normalization preserves dots/plus aliases. Separate versioned keys protect target/source/request lookups, bind HMAC verifiers and AES-GCM target ciphertext to ID/purpose/target/expiry, and expose only high-entropy key commitments for continuity checking. No persistence or send. |
| apps/api/app/domains/identity/temporary_policy.py | Controlled-time immutable three-failure window; resends preserve failures and extend expiry to newest code; exhausted windows block verification/resend until expiry. Owning database locking supplies atomicity. Constants are ten-minute OTP,60-second cooldown,six target sends/hour and100 trusted source sends/hour. |
| apps/api/app/domains/identity/temporary_delivery.py | Uniform six-digit generation and purpose-specific templates. Persist only protected fields; retain raw code/target only in a private in-memory ticket. One transport attempt even under concurrency/uncertain failure; expired/discarded tickets refuse. No automatic retry, durable raw-code outbox or API route. Python reference release is not memory zeroization. |
| apps/api/app/domains/identity/temporary_challenges.py | PostgreSQL service uses trusted fresh connections/keys/clock/parsed source. Source-then-target locks serialize sends; target-then-user ordering protects verification/eligibility. Commit a generic ID/expiry and private optional send ticket before dispatch. Same-operation retries return original acknowledgement without send, counters or renewed expiry. Wrong-code counters commit; correct verification and trusted callback share one transaction. Unknown/ineligible resets follow the same failure statuses/limits without phantom users. Reject changed keys/unreviewed legacy adoption. No actual activation/password change/session/HTTP binding. |
| database/migrations/20261023192856_identity_otp_transactions.sql | Add nullable protected challenge metadata plus four Identity tables: key commitments, minimal operation acknowledgements, send reservations and shared verification windows.27 domain tables. Legacy data unchanged. Down locks against concurrent writes and refuses occupied security state; empty down removes only its additions. |
| database/tests/identity-otp-smoke.sql | Rollback-only synthetic positive/negative checks for paired protected fields, digest sizes, bounded failures and supersession chronology. No provider/crypto acceptance claim. |
| scripts/check_database.py | Full six-migration/head/four-smoke checks. Pin original Step3 upgrade/down proof to its historical chain, preserving failed-upgrade atomicity. Test empty OTP down/up and unchanged legacy verifier rows. No ambient/retained target. |
| database/tests/native-checks.sh | Source expects six migrations/head20261023192856,27 tables and four smokes. Function/trigger counts remain21/33. Bash syntax passed; no revised macOS execution claimed. |
| apps/api/tests/domains/identity/postgres_fixtures.py, conftest.py, test_microsoft_postgres.py | Move the existing disposable PostgreSQL fixture to an explicitly imported reusable test-only module. Same private SCRAM socket/network-none tmpfs/no-host-port target and owned-container cleanup. Microsoft tests unchanged in behavior and still pass. Verified Linux ARM64 route; macOS/Docker Desktop unverified. |
| apps/api/tests/domains/identity/test_temporary_crypto.py, test_temporary_policy.py, test_temporary_delivery.py |26 synthetic offline cases verify protected fields, normalization, shared failure window and actual SES adapter composition with a recording SDK. No AWS client or live email. |
| apps/api/tests/domains/identity/test_temporary_postgres.py |18 real PostgreSQL cases cover duplicate/new-operation races, concurrent wrong/correct verification, expiry/resend budgets, cooldown/hour boundaries, source/target scope, eligibility/non-enumeration, key continuity, callback/reservation rollback, enrollment after credential cleanup, occupied down refusal and uncertain SES submission without retry. Synthetic callbacks do not implement Step6/7. |

Root/domain/database/schema docs, command registry, temporary-auth decision,
canonical task clarifications and own work-log row record behavior and limits.
[Source SHA-256 manifest](source-hashes.json) pins the implementation/check files.

## Actual checks and corrections

- Initial14 PostgreSQL cases passed. Review found suppressed acknowledgements
  needed the same failed-attempt budget to avoid existence disclosure via422/429;
  corrected lookup/charging and added the explicit status-sequence check.
- Expanded18 real PostgreSQL cases passed. Both Microsoft/OTP DB modules passed
  together before the final three additional OTP cases; final full suite includes
  all of them. Runtime strict mypy passed four new modules. Black passed94 files.
- Full `make check` passed all11 gates:563 Python,63 data and16 web tests;
  CI parity, boundaries, eight current generated artifacts, contract types,
  web lint/types/build,35 wrapper safety cases, actual PostgreSQL18.6/dbmate2.36.0
  migration/upgrade/down checks and Gitleaks8.30.1 source snapshot.
- Bash syntax,213 existing changed-document local file targets and
  `git diff --check` passed. No app.main/public Identity declaration, reviewed
  contract source, dependency manifest/lock, frontend or other private feature
  behavior changed. No shared/retained/cloud database or real send was used.

## Remaining gates and next action

1. Private implementation verification and service-lifetime minimal marker
   retention approval are recorded. Operational-state cleanup details remain
   subject to reviewed Step7 design; no automatic cleanup is enabled.
2. Before public use, bind reviewed request validation/parsed trusted IP, runtime
   key/DB configuration and uniform response/background dispatch. Serialize only
   ID/expiry; never ticket presence/provider status. A crash after commit can lose
   a send; deliberate new-operation resend after cooldown is the recovery path.
3. Step6/7 implement actual atomic activation/password/reset/session behavior
   through the verified consume boundary and preserve target-before-user order.
4. Complete original real OTP/provider/runtime/public/UI checks under separate
   exact cloud/send approval and Step11/12 integration. SES production gate,
   Step4 actual Microsoft/nonce/session and PR10/current-main migration/owner
   integration remain pending. No FR completion or ID-READY acceptance claimed.

Applicable checklist review: owning-domain/parameterized SQL/privacy/timestamps,
synthetic inputs, transaction/race/failure checks and local gates passed for this
increment. Task-wide peer/cloud/browser/integration review is not closed out.
No commit, push, merge, deployment, live email or destructive cleanup performed.
