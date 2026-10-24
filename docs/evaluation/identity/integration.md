# ID-01 current integration handoff

Owner Aditya(A); primary independent reviewer Rahul(D), plus affected owners.
Committed base `8616301` includes local main merge `890adb1` and compact docs.
The local API composition increment below is uncommitted; no remote publication
or ID-READY acceptance.

## Main reconciliation

Accepted main/PR10 `defec38f59d4acb683f7b51950860f458aacfdd1` was merged into
checkpoint7a9b4a4, producing890adb1 after human verification/explicit commit
approval2026-10-24 16:41:58 UTC. All13predicted conflicts resolved; all14published
migration files retain their parent bytes. Combined head20261023202807 has33tables,
25functions/37triggers. No shared database was migrated. Private Listings
production code and incoming app.main are unchanged from accepted main; narrow
approved exceptions are a test clock and one corrected documentation link.

| Resolved surface | Important result |
| --- | --- |
| core/config.py | Union of Identity Microsoft/SES safety and Listings DB/S3/isolated-demo guards. |
| pyproject.toml; uv.lock | Added pinned psycopg-pool3.3.3; all existing versions retained, including boto3 1.43.116. |
| web/vite.config.ts | Normal Listings /api proxy preserved; explicit Identity preview keeps only loopback8001 routes and build refusal. |
| check_database.py; native-checks.sh | Combined14migration clean/repeat/upgrades/atomicity/rollback/reapply, five smokes and protected retirement rollback; measured inventory25/37. Native syntax only, no new macOS run. |
| Contract source/generated artifacts | Retained optional pickup/image-selection/retirement changes and Identity nonce/CSRF/contact dispatch. Regenerated all8registered artifacts, never edited generated files by hand. |
| Identity tests | Replaced obsolete health-only/router.path assumptions with real OpenAPI paths and preserved preview exclusion/proxy isolation. |
| Listings test | Human-approved module-scoped clock correction prevents fixed Oct22sessions expiring against calendar time; production expiry comparison untouched. |
| Shared pages/docs | Both domains' public components retained; author histories/statuses preserved; one bad relative link corrected. |

Final `make check` exited0 at2026-10-24 16:39:37 UTC:967Python passed/1DB-only
skip,63data,118web, Black142,0boundary violations,8generated artifacts current,
types/lint/build,35wrapper safety, actual PostgreSQL18.6 combined checks and
Gitleaks8.30.1. The skipped Listings database workflow passed separately using
--listings-store. Focused regression25and contract/config102checks also passed.
Initial13failures (old route assumption/expired test sessions) and later stale
native inventory24/36 assumption were corrected; no checks disabled/migration
rewrites. Final raw log /tmp/clip-id12-merge-verified-check.log, initial failures
/tmp/clip-id12-merge-check.log and /tmp/clip-id12-merge-inventory.log.
[32source/migration hashes](id-01-step-12/merge-source-hashes.json).

## Email routing

Checkpoint7a9b4a4 implements private Resend adapter, fixed CLIP User-Agent, SSM
snapshot loader and primary/alternate router. Defaults remain disabled/unbound.
The selected sender is verify@clip-iisc.site; desired SES IAM source follows it,
but live policy still needs exact plan/apply. Current Resend sender reached Gmail
and IISc locally; this does not establish ECS OTP/API/browser delivery.

A single SecureString contains version1/primary/resend_api_key, read lazily and
cached for14400monotonic seconds per process. First send after expiry refreshes
atomically; failed refresh sends nothing using expired configuration. One send
retains its snapshot. No polling thread or permanent provider promotion. Try
primary once, then alternate once on any exception; same message/OTP, duplicates
possible after uncertainty; no third attempt/fake fallback. Current adapters
retain at most five controlled recipients and SES sandbox/production guards.
SSM path is provisioned for operator access, not verified for ECS task access.
[Snapshot](id-01-step-12/email-routing-source-hashes.json),
[routing decision](../../decisions/identity-email-routing.md),
[current setup](../../environment/identity-provider-setup.md).

## Runtime plan

Next Step12 work must preserve the accepted Listings app/lifespan/routes and add
actual Identity composition. No isolated fixed caller may authorize real sessions.

1. Bind real Identity sessions/middleware/routes/capability/contact services into
   the shared app, retaining Listings pool/storage and request-scoped ownership.
   Safe unconfigured startup; incomplete enabled configuration fails closed.
2. Provide three independent persistent256bit TemporaryKeys with a stable version
   through reviewed SSM references/permissions. Never regenerate on restart: lookup,
   enrollment and idempotency commitments must survive. No secrets in chat/repos.
3. Review a real least-privilege application DB login/grants and TLS. Existing
   CONNECT-only clip_test_probe cannot run auth; do not use the master login.
   Prove grants/refusals on disposable SQL before separately approved shared apply.
4. Review actual trusted proxy/network chain, HTTPS/scheme and source address
   handling. Do not trust arbitrary forwarded headers or rate-limit all users by
   the ALB peer. Test spoofing, allowed hops and fail-closed parsing.
5. Align same-origin API routes/proxy/hosting without swallowing SPA /auth/callback.
   Preserve normal versus synthetic modes and registered callbacks. Keep MSAL
   disabled until actual backend/config/provider gates are approved.
6. Verify actual Microsoft/IISc redirect/PKCE/state/nonce/cookie/session, denial,
   replay, consent and SDK cache cleanup. Mocked SDK ports are not provider proof.
7. Verify actual temporary OTP receipt/redemption/resend/login/reset/logout/contact
   flows via approved active provider and real runtime, with protected code/key
   handling and uniform acknowledgements. Resend can satisfy active-provider setup
   while SES production stays pending; do not bypass its sandbox during fallback.
8. Record integrated desktop/phone/keyboard observations, then rerun affected full
   local/CI checks and prepare the readiness PR. Existing emulation is not a phone
   proof. No new page/profile route is implied.

## Gates and scope

- Human-verification loop remains required for each numbered step/checkpoint.
- Exact cloud/SSM/IAM/DNS/deploy/live-send/cleanup plans retain separate approvals;
  this handoff authorizes none. Preserve Suraj's shared database/workloads.
- Rotate the credential previously supplied in chat through a private approved path.
- Enable general SES only after production access and reviewed configuration;
  apply its verify-sender condition under separate exact approval.
- Readiness requires real interfaces/configuration/provider safety and independent
  Rahul/affected-owner review, current head/base hosted CI and separately approved
  publication/merge. Use the [peer-review prompt](../../prompts/peer-review-prompt.md).
- ID-01 Step13 requires exact account/region/revision/test identity/time/spend/
  rollback/cleanup scope before deployed verification.
- Step14 full consumer authorization/contact matrix waits for real LI01/LI02,
  SECORE/SE02 and CNCORE/CN01/CN02. It is outside current ID-READY scope.
- Step15 retains sanitized evidence/contract/checklist/individual FR closeout.
  ID-READY and ID-01 remain incomplete until their actual required checks pass.

## Local API composition

Aditya authorized this Step12 increment and separately approved the narrow
Listings adapter correction. No new task-definition gap: main/contracts/real
Identity services exist; actual provider/runtime/device gates remain pending.
A is recorded current writer for main.py/application.py, the exact boundary allowlist and shared
docs. Suraj's affected-owner review is still required for the adapter change.

| Changed code | Purpose and important behavior |
| --- | --- |
| apps/api/app/application.py | Side-effect-free create_app retains one Listings/health app and its existing lifespan/pool/routes; accepts explicit Identity bindings only in local/test with DB settings. Rejects production/demo/development-auth composition. Default ASGI app stays unbound, no ambient provider/key discovery. |
| apps/api/app/main.py | Thin default entry retains established settings/app exports, validates settings and configures logging; re-exports the factory without changing ASGI startup. |
| apps/api/app/domains/identity/http.py | Immutable validated IdentityHttpDependencies and one-time install_identity_http reuse actual auth/session/CSRF/contact middleware/routes inside an existing app. Root owns logging/errors/health/lifespan. Standalone create_identity_app retains its signature/behavior. |
| scripts/check_boundaries.py | Exact application.py import exception adds only Identity HTTP module/dependency/installer names; no cross-domain private imports elsewhere. |
| apps/api/app/domains/listings/integrations.py | Approved eligibility call removes blanket regular-class restriction; regular-only seller guards remain in Listings. Fixes real temporary catalogue403. No table reads or authority from browser IDs. |
| apps/api/tests/domains/listings/test_offer_boundary.py | Approved adapter regression covers eligible/ineligible temporary buyers and the existing additional listing-owner eligibility recheck, without fake success for denied accounts. |
| apps/api/tests/domains/identity/test_application_composition.py | Eight real composed-app SQL/cookie cases, controlled signer/mail only: regular catalogue/own reads, contact CSRF, logout, temporary browse versus sale/upload denial, forged-header denial, expiry/revocation, per-app isolation/pool closure and incomplete/production/demo refusal. |

Focused composed tests plus existing unbound adapter case:9passed. Expanded
startup/health/composition/offer selection57passed. Strict mypy for main,
application, Identity HTTP and Listings adapter passed4sources. Final full
aggregate checks are recorded below.
Retained failed runs show new test-fixture corrections (libpq DSN versus required
URI, nonce201status, reserved E164 phone), real temporary catalogue403 and a new
test's incorrect assumption that owner-list reads must be denied. The latter
now asserts empty actor-scoped reads and tests the reviewed sale/upload creation
restrictions directly. No product validation/expiry check was weakened, no
failure relabeled or test disabled. Logs: /tmp/clip-id12-composition-*.log.

This proves local composition with real SQL/session/public eligibility. It does
not turn on Microsoft/Resend, discover SSM secrets, apply IAM/database grants,
change proxy/TLS trust or deploy anything. No actual-phone/provider proof or
complete cross-domain Step14 result. No new schema/generated/public API shape.
The initial full regression also found established main.settings imports and an
old regular-only offer test expectation. Preserved main exports by moving the
reusable factory out of the default-entry module; expanded the approved offer
regression to cover eligible/ineligible temporary buyers and existing seller
eligibility recheck. No auth or seller-eligibility guard removed.
[Seven source hashes](id-01-step-12/composition-source-hashes.json) pin the local
implementation. Final full checks are recorded below; user verification and
explicit commit approval remain pending.

### Final local composition result — 2026-10-24 17:56:54 UTC

Final make check exited0/all11gates:976Python passed/1existing DB-only skip,
63data,118web; Black144files,0boundary violations,8generated artifacts current,
contract types, lint/build,35wrapper safety, actual PostgreSQL18.6 combined
14migration clean/repeat/upgrade/atomicity/rollback/reapply and Gitleaks8.30.1.
Strict mypy passed4runtime files. Focused startup/health/composition/offer suite
57passed, including the positive seller eligibility recheck. Latest source
snapshot contains7code/test files; source/schema/public API/Terraform/frontend
configuration otherwise unchanged. No phone/cloud/provider/SSM/send proof inferred.

Raw final log: /tmp/clip-id12-composition-final-check.log; targeted regression
log: /tmp/clip-id12-composition-regressions-final.log. Initial failed logs remain
in /tmp/clip-id12-composition-*.log (fixture corrections, temporary eligibility
bug, preserved main.settings exports and prior offer expectation). No test disabled.

Aditya verified the implementation plan and explicitly authorized the bounded
Listings adapter correction; this resulting code remains uncommitted and awaits
human verification/explicit commit approval. Suraj/affected-owner peer review and
all actual deployment/runtime/provider/ID-READY gates remain pending.
