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
Listings adapter correction; Aditya subsequently verified this result and authorized its commit;
composition is committed at `fad1e2f`. Suraj/affected-owner peer review and
all actual deployment/runtime/provider/ID-READY gates remain pending.


## Secure runtime preparation

Step12 local implementation; subsequently human-verified with explicit commit authorization. `prepare_local_identity`
returns real dependencies for the explicit shared API factory. It does not enable
`app.main:app`, provision secrets, change grants, send mail or discover Microsoft
metadata. Tests use an offline SSM port and owned disposable PostgreSQL, not the
shared RDS instance. Production and demo/bypass combinations remain rejected.

| Path | Purpose |
|---|---|
| `apps/api/app/domains/identity/runtime_configuration.py` | Read bounded versioned SecureStrings; parse persistent independent keys; validate DB and warm the email snapshot before returning dependencies. |
| `apps/api/app/domains/identity/runtime_database.py` | Validate an explicit private URI, open bounded connections and audit effective role/table/logging/migration/key-binding state read-only. |
| `database/roles/identity-runtime.sql.proposed` | Reviewable minimum grants for a separate Identity login; not a migration or live apply script. |
| `apps/api/app/core/config.py`, `email.py` | Accept the dual-provider selector while retaining controlled-recipient and production guards. |
| `apps/api/app/domains/identity/email_routing.py` | Warm the four-hour routing cache without sending or exposing its configuration. |
| `apps/api/tests/domains/identity/test_runtime_configuration.py` | Exercise real restricted-role OTP/session/contact operations, denied privileges, restart/key mismatch and malformed configuration. |

The proposed login is `clip_test_identity_app`, separate from Listings. Only
SELECT/INSERT are granted on permanent enrollment/external-identity/key/operation
records; users additionally permit UPDATE, and other named Identity tables permit
CRUD. No DDL, TRUNCATE, ownership, memberships or cross-domain data grants. Database
CONNECT/PUBLIC TEMP and schema baseline changes need their own approved plan.
Remote connections require `clip_test`, explicit credentials and verify-full TLS
with system roots. Only the owned test-mode Unix socket may disable TLS.

The authentication key parameter is loaded once per bootstrap; never regenerate it
on restart or refresh it with the email preference. Existing database commitments
must match. An empty database adopts keys through the established service transaction,
not startup writes. The current default API remains unbound.

Remaining live work: review/provision key and separate database-URL references;
approve role/PUBLIC baseline and logging changes; scope runtime IAM; validate
actual certificate chain, proxy/cookies/browser and provider delivery; finish device,
independent/affected-owner review and hosted CI. No such action is authorized by
this local result. ID-READY and Step12 remain incomplete; Step14 stays outside scope.

[Runtime source snapshot](id-01-step-12/runtime-source-hashes.json). Focused suite:
32 passed; raw log `/tmp/clip-id12-runtime-focused-2.log`. Strict mypy passed both
new modules (`/tmp/clip-id12-runtime-types-final.log`). Full local gate result is
recorded below after completion.

Final local runtime checks — 2026-10-24 18:32:01 UTC: `make check` exited0; all11gates
passed,1008Python/1existing DB-only skip,63data/118web, Black147files, zero boundary
violations, current contracts, web build,35wrapper safety cases, actual
PostgreSQL18.6 lifecycle and Gitleaks8.30.1 source scan. Source hashes, relative
file links and `git diff --check` pass. Raw full log:
`/tmp/clip-id12-runtime-check.log`. Aditya verified this local result and authorized its commit/continuation.
No live checks or ID-READY acceptance inferred.


### Next live gate: create persistent keys only

Read-only preflight on 2026-10-24 18:37:02 UTC confirmed account335523638354,
operator `arn:aws:iam::335523638354:user/adityalaxmi1`, region ap-south-1.
DescribeParameters returned only `/clip/test/identity/email-delivery`, Standard
SecureString version1. No parameter values were requested. The shared API task
role has one inline SES policy and no attached policies; its live From condition
still names no-reply, and it has no SSM read statement. These are future IAM
changes, not part of the following request. No RDS/shared DB operation occurred.

Proposed bounded action, awaiting separate approval:

- Target only `/clip/test/identity/authentication-keys` in that account/region,
  using profile adityalaxmi1. Create one Standard SecureString with aws/ssm;
  `Overwrite=false`. No overwrite, advanced tier, IAM, database, compute or send.
- Generate three independent32-byte keys with the OS cryptographic random source
  in process memory, encode canonical base64 and use schema_version1 and a stable
  UTC-derived key_version. Parse through the reviewed runtime validator before
  submission. Never print values or pass them in shell arguments/files/logs.
- Use one bounded SDK submission with automatic mutation retries disabled. Stop
  if target/account differs, name exists, paid tier is needed or any AWS error
  occurs. If the response is ambiguous, inspect metadata rather than overwrite
  or retry creation. Confirm only Type/Tier/Version metadata; no decrypted read.
- No compute duration/concurrency or paid provider activity. One Standard
  parameter plus bounded control-plane requests; no new paid infrastructure or
  advanced-tier enrollment. Stop for an unexpected cost/configuration requirement.
- Retain the persistent secret across restarts. No automatic deletion/rotation;
  deleting a key after data adoption can make retained data unusable. If unused
  creation must be undone, deletion requires its own explicit approval.

After this gate: separately plan the database login/URL and shared PUBLIC-grant
baseline with the current DB operator; then scoped runtime IAM and sender update;
then proxy/TLS/deployment and real browser/provider checks. The existing email
secret is retained. This request does not start or alter Suraj's environment.

Creation result — 2026-10-24 18:47:02 UTC: Aditya explicitly approved the exact cloud
mutation after automatic review requested clearer action approval. The initial
SDK attempt stopped before generation/write because the optional login credential
dependency was missing; STS CLI metadata confirmed the correct account/operator.
Used CLI session credentials captured only in memory for the SDK; no dependency,
profile or application configuration change. One create-only PutParameter
succeeded, validated key schema before submission and confirmed only metadata:
`/clip/test/identity/authentication-keys`, SecureString, Standard, version1,
aws/ssm. No decrypted read, overwrite, file containing keys, database/IAM/compute
change or send. Retain keys; runtime access/adoption and DB URL remain pending.
Aditya verified the provisioning result; execution record changes are uncommitted.


## Database login and URL setup plan

Step12 planning checkpoint — 2026-10-24 19:39:13 UTC; Aditya(A). Read-only RDS
metadata confirms `clip-shared-test-postgres`, resource ID
`db-PYRRZJPVKPGHIXDAHUWATXGH7A`, stopped, PostgreSQL18.6, database `clip_test`,
private endpoint `clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com:5432`,
security group `sg-02f98707f8e43d2ea`, account335523638354/ap-south-1. No SQL,
secret-value retrieval, start/stop, task launch or mutation performed.

Audit: the local role proposal and restricted-role integration checks exist.
PD-16 recorded PUBLIC CONNECT/TEMP and public-schema CREATE revocation, so do
not repeat revocations by default. Actual current ACLs, Identity migration presence,
RDS ability to set proposed role logging defaults, and private execution availability
remain unverified. A superuser disposable test does not prove RDS-admin permissions.
The historical setup task creates only the probe login; it cannot be rerun as an
Identity setup procedure. These are explicit preflight gates, not assumed success.

Ordered execution plan (each live gate requires its own exact approved action):

1. Prepare an Identity-owned bounded setup/preflight procedure locally. Keep the
   existing probe task/script unchanged. Test on disposable PostgreSQL: absent
   schema/unsafe logging/PUBLIC grants reject without changing shared defaults;
   create only the new role and named grants; existing-role collision rejects;
   verify restricted operations and denied DDL/cross-domain access. Register the
   local command and preserve redacted output. This is the next implementation
   increment after human plan verification, not a cloud operation.
2. Review a fresh private execution route using an immutable image and separate
   setup permissions; neither the app nor its runtime role receives the master
   secret. Existing shared roles/tasks are not repurposed silently. Before any
   launch/start, record exact task/image/roles, active operator/window, costs,
   concurrency and cleanup caps. No public ingress or direct laptop connection.
3. Separately approve a bounded start of this exact stopped RDS and necessary
   private execution capacity. Inspect current SQL metadata only: database and
   migration versions, ownership, table/sequence/default ACLs, PUBLIC/schema
   privileges, role-name collisions and effective logging. Never retrieve business
   rows or key/credential values as evidence. If migrations are absent, stop for
   a separate migration plan; if PUBLIC grants differ, stop for affected-owner
   review. Do not revoke another contributor's privileges automatically.
4. After reviewing actual preflight findings and exact SQL, separately approve
   role/password/grant creation. Create `clip_test_identity_app` with the flags
   and named grants in the role proposal, explicit CONNECT, no memberships and
   connection limit10. Apply credential-safe logging guards before password work;
   fail closed if RDS lacks necessary privileges. No global logging weakening,
   owner changes, schema migration or application-data mutation. Generate the
   password privately; never place plaintext or verifier in task overrides/logs.
5. Separately approve create-only Standard SecureString
   `/clip/test/identity/database-url` with aws/ssm, using the restricted login and
   exact private endpoint/database plus verify-full/system-root TLS. No overwrite.
   Preserve the credential privately between approved setup/publication phases;
   if either phase fails, keep the unused role disabled or roll back its creation
   where possible, and inspect outcome before retries. Do not lose an enabled
   unrecorded credential or automatically drop/rotate an existing role.
6. Approve a controlled runtime read/validation against actual RDS using the new
   login, persistent keys and required schema. Verify TLS chain/hostname, logging,
   exact allowed/denied privileges and key commitments with the read-only startup
   audit. No OTP/account/key adoption writes or mail in this check. Schema source
   and runtime revision must match the reviewed source hashes.
7. Record sanitized metadata/results, retain the persistent key/URL references,
   and clean up only owned temporary execution resources under the approved
   cleanup plan. Stop shared RDS/capacity only when the named operator confirms
   the coordinated window has ended and authorizes the exact stop. Subsequent
   runtime IAM, SES sender, proxy/TLS/deployment/provider/browser checks remain
   separate; this checkpoint does not complete ID-READY.

No cloud spend is authorized by this plan. The start/launch request must supply a
fresh budget/headroom check, exact duration/concurrency/cost ceiling and rollback;
these cannot be inferred from old run approvals. Preserve Suraj's resources and
workloads throughout. No new RDS instance or alternate shared database is proposed.


### Local database setup procedure

The database plan was human-verified. `database_setup.py` now implements explicit
read-only catalog preflight and create-only role/password/grant setup. It has no
AWS code, live CLI, secret storage or default-app import. Callers supply trusted
connections plus expected database and administrator; future execution must also
verify endpoint/TLS/account and bound connection/process time.

Preflight checks effective logging before any verifier submission; exact
current/session user and database; absent target role; PUBLIC database/schema/
table/default-table-or-sequence grants; required migration versions and exact
Identity table inventory. No automatic baseline repair or migration. Role creation
holds a transaction advisory lock, computes SCRAM client-side, creates only the
named restricted role, sets its logging defaults and applies named grants/CONNECT
atomically. Plaintext does not enter SQL; no password/verifier/error SQL is output.
Existing roles are rejected rather than modified. If commit acknowledgement is
ambiguous, inspect metadata before retries; retaining/publishing credentials and
handling an unused live role remain the operator's separately approved duties.

`test_database_setup.py` uses actual disposable PostgreSQL with synthetic private
credentials.14focused tests pass, including working SCRAM login checked by the
existing runtime validator, unsafe PUBLIC/default grants, missing schema/version,
logging, wrong-target, collision and post-create rollback. Strict mypy passes the
new implementation. Focused log `/tmp/clip-id12-database-setup-focused.log`;
full gates passed in `/tmp/clip-id12-database-setup-check.log`. No RDS/cloud/secret
read or mutation occurred during this implementation. Aditya verified the local result and authorized commit/continuation; this does not prove RDS-admin permissions or TLS.

[Setup source snapshot](id-01-step-12/database-setup-source-hashes.json) pins the
implementation, tests and reviewed SQL proposal.

Final setup checks — 2026-10-24 21:24:08 UTC: `make check` exited0/all11gates;
1022Python passed/1existing DB-only skip,63data/118web, Black149files, zero boundary
violations, current generated contracts, type/lint/build,35wrapper safety cases,
actual PostgreSQL18.6 clean/repeat/upgrade/atomicity/rollback/reapply and
Gitleaks8.30.1 source scan. Strict setup mypy, source hashes, relative file links
and `git diff --check` pass. Local result and prior provisioning records remain
Aditya verified the local result and explicitly authorized commit/continuation.
