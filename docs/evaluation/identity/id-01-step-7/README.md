# ID-01 Step7 — sessions, password reset, HTTP security and bounded cleanup

Recorded2026-10-23 20:57:44 UTC. Aditya(A), task/id-01-identity at90121c9 plus
uncommitted Step7 changes. Full Step7 design/settings/contract additions and
bounded cleanup implementation were human-verified before coding. Local
implementation performed/checked; Aditya verified the result and authorized
a local checkpoint commit on2026-10-24 05:47:19 UTC. ID-READY and
real runtime/browser/provider/consumer integration remain incomplete.

## Audit and dependencies

Read canonical ID-01 Steps4–12, reviewed Identity/combined/types contracts,
provider/session/retention decisions, actual Step3/5/6 code/schema/evidence,
contribution/staging/checklist and environment records. Real OTP/activation/
Microsoft crypto and SQL implementations exist, so no account/database fake is
used. Found the explicit session-policy gate and missing server attempt/CSRF
operations; Aditya verified the new canonical endpoints before implementation.
No domain ownership, Microsoft exact-domain/tenant policy or readiness gate was
changed. PRE-00/DL-00 remain accepted; PR10/current-main reconciliation remains
deliberately deferred before shared application/ID-READY.

Policy: seven-day absolute/24-hour idle sessions capped by temporary expiry;
256-bit opaque cookie, only its digest persisted. HTTPS Secure/HttpOnly/host-only
Lax cookies; explicit loopback-only development mode. Exact Origin, non-simple
unsafe header and session CSRF; no bearer JSON/local storage. Five password
failures/target/15minutes and100 source attempts/15minutes, including unknown
accounts; OTP remains three. The [canonical decision](../../../decisions/identity-sessions-and-cleanup.md)
records defaults, lock ordering and cleanup approval. No scheduler is enabled.

## Changed code/configuration files and behavior

| Path | Purpose and relation |
|---|---|
| apps/api/app/domains/identity/sessions.py | IdentitySessions owns opaque secret/digest/HMAC domains, dummy Argon2 checks, durable source/target failure limits, fresh current user/session checks, idle/absolute/account caps and trusted CallerContext. Activation/user/credential/guard/session is one transaction. Reset/consume/hash/all-session revocation is one transaction serialized with login; no reset login or renewal. Internal account revocation and current-session idempotent logout. Microsoft attempt is browser-bound,10-minute, one-use; validate signature outside final DB transaction, then atomically consume/map/create session. Secrets stay in transport-only hidden objects, never persistence/JSON/logs. |
| apps/api/app/domains/identity/http.py | Explicit real app factory, actual approved auth/GET /me/CSRF endpoints, canonical operation IDs and public models. Middleware rejects invalid origin/TLS/development peer before session lookup/idle renewal, establishes only trusted caller scope, ignores submitted identity/forwarded headers and enforces CSRF on protected mutations. Exact CORS and no-store, secure host-only cookies; development requires loopback origin, URL and transport peer. Committed OTP acknowledgement body emits before one-shot threadpool background dispatch. Default app.main is unchanged; runtime wiring/real browser checks remain gates. |
| apps/api/app/domains/identity/cleanup.py | Dry-run-by-default Identity-only retention service; batch100/max1000 per table, fresh bounded per-candidate transactions and cutoff rechecks under compatible target/user locks. OTP first unusable includes supersession; sessions include idle terminal; terminal hashes immediately eligible. Rate/attempt records survive24hours beyond their protection window. Never deletes users, contacts, lifetime operation/enrollment markers or key commitments. Apply can partially commit before failure; retry safely rechecks. No scheduler/deadline claim until approved runtime job verified. |
| scripts/identity_cleanup.py | Explicit expected database must match real connected name; refuses administrative template DBs. Reads DSN only from environment, emits counts/generic error, dry-run default and explicit --apply. No argv credential, dotenv fallback, schedule or automatic cleanup. CLI dry-run/wrong-target/apply checked only on the owned disposable DB. |
| apps/api/app/domains/identity/microsoft_accounts.py | Extract same-connection get_or_create_in; original private wrapper behavior preserved. Provider/account lock and mapping now compose atomically with nonce consumption/session insertion. Failure cannot leave orphan mappings/users. |
| apps/api/app/domains/identity/temporary_accounts.py | Add trusted activate_with callback while preserving existing activate result. Session callback shares OTP/account/credential/enrollment transaction; caller owns commit and cannot pass a browser callback. |
| apps/api/app/domains/identity/temporary_passwords.py | Real bounded-cost verification of approved stored Argon2 parameters, safe mismatches/errors, no automatic rehash. Existing validation/hash behavior retained; dummy hash is real work for unknown/ineligible login. |
| apps/api/app/domains/identity/temporary_challenges.py | Key adoption also refuses existing unbound new auth state. Reset eligibility race returns reviewed409 only after matching proof; invalid/unknown proof retains422/429 and failures commit. OTP three-attempt/resend semantics unchanged. |
| database/migrations/20261023202807_identity_sessions_and_login.sql | Nullable legacy-safe session last_seen_at plus bounds for new bound digests/lifetime. Add protected password_login_windows, auth_source_events and microsoft_login_attempts.30 domain tables/seven versions. Old rows are not backfilled or rewritten; occupied down locks and refuses security-state deletion. |
| database/tests/identity-session-smoke.sql | Rollback-only actual SQL checks for session activity/digest/lifetime bounds and attempt timing; synthetic data only. |
| scripts/check_database.py | Head20261023202807,30 tables/five SQL smokes; retain historical Step3 and OTP round trips at their own heads. Actual up/down/reapply preserves legacy OTP and session bytes and never invents last-seen activity; incompatible Step3 upgrade remains atomic. Only its fresh tmpfs/no-host-port target. |
| database/tests/native-checks.sh | Updated source expects seven migrations/30 tables/five smokes with21 functions/33 triggers. Bash syntax passed; no revised macOS execution claimed. |
| contracts/source/identity.py and contracts/source/types.py | Approved POST /auth/microsoft/login-attempts and GET /auth/csrf, public nonce/expiry and CSRF shapes; cookie bearer remains outside JSON. Other operation signatures unchanged. |
| apps/api/app/contracts/domain_types.py; apps/api/app/domains/identity/public.py; contracts/generated/openapi.json; contracts/generated/types.gen.ts | Regenerated from canonical sources, never hand-edited.53 operations across46 paths; all eight registered outputs current, unchanged other outputs not rewritten. Generated declarations are not live service implementations. |
| apps/api/tests/domains/identity/conftest.py and session_fixtures.py | Explicit synthetic fixture composes real session/HTTP/cleanup/Argon2/RSA/SQL with controlled time and transient mail capture, no autouse authentication injection. Reuses private SCRAM/socket/tmpfs database fixture; no external target/host port. |
| apps/api/tests/domains/identity/test_sessions_postgres.py |16 real cases: activation/session atomicity, token privacy, idle/absolute/account deadlines, password/source limits, logout/revocation, reset/login race and rollback, Microsoft nonce replay/race/rollback and legacy-session refusal. |
| apps/api/tests/domains/identity/test_identity_http.py |23 real HTTP/SQL cases: cookie/JSON separation, current trusted scope/forged-header denial, CSRF/CORS/origin/TLS/loopback guards, idle recovery/reset/logout, nonce cookie/redemption, uncertain one-shot delivery, response-before-send, proof-gated409 and canonical operation IDs. Rejected origins cannot renew idle activity. |
| apps/api/tests/domains/identity/test_identity_cleanup.py |10 actual retention/CLI cases: dry-run/exact cutoffs/supersession/idle/hash removal, batch/idempotency, cleanup/login race, guard/contacts preservation, post-cleanup dedup and explicit real target checks. All deletions are owned disposable synthetic data. |
| apps/api/tests/domains/identity/test_temporary_postgres.py | Update correct-proof revoked-reset expectation to409; wrong-purpose remains422. Extend its explicit disposable truncate for new FK, preserving legacy adoption safety case. |
| tests/contracts/test_generation.py | Update approved operation/path counts and assert the two specific new endpoints. Unconfigured app remains health-only; offline generation still cannot import/use real application dependencies. |

Root/API/domain/database/schema/provider/command docs and canonical session/
retention decisions record behavior and limitations. [Source SHA-256 manifest](source-hashes.json)
pins code, SQL, contracts and generated artifacts. Manifest uses separate path/
digest fields rather than credential-like key/value labels.

## Checks, corrections and evidence limits

- Early strict typing caught missing tuple/HTTP helper/closure annotations;
  corrected, final strict mypy passed eight changed runtime/CLI files.
- Initial service suite had four test-assumption failures: exactly
 24hours between touches correctly expires idle sessions; immediate reset after
 registration correctly hits existing cross-purpose OTP cooldown. Corrected
 controlled time and session-vs-account expiry expectations without relaxing
 limits. Initial service suite then passed; expanded regression modules passed64
 actual DB cases together before final full run.
- New FK required an old disposable fixture truncate to name the new table;
  corrected. Reset contract alignment found correct-proof state race409, while
  incorrect/unknown codes remain indistinguishable. Added regression coverage.
- Initial full run failed two old51-operation/44-path assertions after approved
 endpoints; updated to53/46 and asserted new IDs. Final HTTP operation IDs also
 match the canonical registry. A guarded text-edit assertion caught formatting
 mismatch during iteration; partial local edits were inspected before proceeding.
- Final full make check passed all11 gates:646 Python,63 data and16 web tests,
 Black106 files, CI parity, boundaries, eight current generated artifacts,
 contract Mypy, web lint/types/build,35 wrapper safety cases, actual PostgreSQL18.6/
 dbmate2.36.0 clean/repeat/five-smoke/legacy-up/down checks and Gitleaks8.30.1
 source snapshot. No skipped/failed required final local gate.
- Runtime Mypy eight files, Bash syntax,223 changed/new Markdown local targets
 and whitespace checks passed before final evidence/status additions. No new
 runtime dependency, core auth change, default main enablement, private feature
 edit, frontend behavior, live email or retained/shared/cloud DB was used.
 Verified local storage route is Linux ARM64, not new native macOS/AMD64 proof.

Final evidence-inclusive Gitleaks scan passed; all25 source hashes matched and
226 changed/new local Markdown file targets resolved.

## Remaining real gates and next checkpoint

Human result verification and local checkpoint commit authorization are recorded.
Step8 still requires its plan verification. No push/merge occurred; peer/shared
contract/schema review remains before ID-READY PR.

The local HTTP factory now verifies nonce/session/context/activation/reset paths;
these are no longer missing local implementations. Actual runtime connection/key
SSM references and permissions, real application DB grants, merged current-main
migrations, trusted TLS/ALB proxy/source configuration, real Microsoft browser
PKCE/state/inbox/provider behavior and general SES production access remain
original integration gates. Default app.main remains health-only until reviewed
runtime binding is supplied. No deployment or new public website sign-in is
claimed. SES production access does not block an independently approved sandbox
OTP send to the existing verified recipient; no send was performed here.

Cleanup design and bounded implementation are approved/checked, but no schedule
is enabled and no real retention deadline is accepted. Exact target/dry-run/
operator/cloud approval and observed runtime runs are still required. Step8/9/11/
12 must finish capability/contact/frontend/integration; Step14's real consumer
matrix remains outside ID-READY scope. No FR/NFR/readiness closeout claimed.
Relevant checklist privacy/ownership/UTC/real crypto/storage/concurrency/error/
local checks applied; task-wide browser/provider/peer/review gates remain open.
