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
Listings adapter correction. The local API composition exists, but the offline
audit found that the current hosted task still lacks its runtime settings, DB URL,
SSM permission and HTTPS ingress/proxy route. This increment supplies a guarded
test-only startup path; it does not configure the hosted task. A is recorded current
writer for main.py/application.py, the exact boundary allowlist and shared docs.
Suraj's affected-owner review is still required for the adapter change.

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

Step12 local implementation; `prepare_local_identity` returns real dependencies
for the explicit operator-local API factory. A separate hosted test-mode opt-in
now binds these dependencies from `app.main:app` only when the full validated
configuration is enabled. Both paths read fixed secret references, validate the
restricted DB role, and warm the email snapshot without sending. They do not
provision secrets, change grants, migrate the shared DB, or discover Microsoft
metadata. Tests use offline SSM ports and owned disposable PostgreSQL, not shared
RDS. Production and demo/bypass combinations remain rejected.

| Path | Purpose |
|---|---|
| `apps/api/app/main.py` | Keep default startup unbound; only the explicit hosted test flag prepares and installs real Identity dependencies. |
| `apps/api/app/application.py` | Allow the validated test-only composition and choose `/api` Identity paths when the bundled UI is served. |
| `apps/api/app/domains/identity/http.py` | Install the existing Identity endpoints under the same `/api` prefix used by the bundled UI while preserving public-auth CSRF boundaries. |
| `docs/decisions/identity-test-runtime-activation.md` | Record the default-off, test-only startup behavior and separate cloud/ingress gates. |
| `apps/api/app/domains/identity/runtime_configuration.py` | Read bounded versioned SecureStrings; parse persistent independent keys; validate DB and warm the email snapshot before returning dependencies. |
| `apps/api/app/domains/identity/runtime_database.py` | Validate an explicit private URI, open bounded connections and audit effective role/table/logging/migration/key-binding state read-only. |
| `database/roles/identity-runtime.sql.proposed` | Reviewable minimum grants for a separate Identity login; not a migration or live apply script. |
| `apps/api/app/core/config.py`, `email.py` | Validate the explicit test-only startup flag, exact HTTPS origin, separate Listings URL, dual-provider selector and recipient/production guards. |
| `apps/api/app/domains/identity/email_routing.py` | Warm the four-hour routing cache without sending or exposing its configuration. |
| `apps/api/tests/domains/identity/test_runtime_configuration.py`, `test_main_runtime.py`, `apps/api/tests/core/test_provider_settings.py` | Exercise real restricted-role OTP/session/contact startup, default-unbound versus opted-in composition, environment parsing and unsafe-config refusals. |

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
not startup writes. The default API remains unbound; the new explicit hosted
test-mode path is described below and is not configured in ECS yet.

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


## Private database preflight window — approval request

Prepared 2026-10-24 21:29:32 UTC; Aditya(A), profile adityalaxmi1,
account335523638354, ap-south-1. Local procedure committed at13db098. Read-only
AWS checks show original RDS stopped, shared cluster ACTIVE with0registered hosts/
running/pending tasks, ASG `clip-shared-test-ecs-host` min0/max1/desired0. Existing
launch template lt-0327bb81cb3269f0b/version1 uses private c7i-flex.large,
AMI ami-0c10ee7b040aa465e and host SG sg-0a3c8d683731470b4. RDS SG
sg-02f98707f8e43d2ea already allows5432 from that host SG. No ingress change.

### Exact bounded actions, none executed

1. Recheck operator/account, exact RDS resource ID, empty tasks/services/ASG and
   current owner window. Start only `clip-shared-test-postgres`, resource
   db-PYRRZJPVKPGHIXDAHUWATXGH7A; wait at most20minutes for availability.
   Do not recreate, change class/storage/parameters/network or stop another run.
2. Launch at most one standalone task in `clip-shared-test` using capacity
   provider `clip-shared-test-capacity` (weight1/base0), count1, no service:
   `clip-test-identity-email-ap-south-1-id01:1`. Its existing digest is
   sha256:3ef8b13d3b102dc97e67d79d91e43eb8d4b2cc02fbabb45cf6001c8a93eddd1d.
   Use exactly [these overrides](id-01-step-12/database-preflight-task-overrides.json):
   `python -c 'import time; time.sleep(1800)'`. The overridden command never imports
   the email sender/API, and the definition has no injected secrets or ports.
   Existing task/execution roles stay unchanged. No task registration, image build,
   push, API deployment, mail, DB write or IAM change. Capacity provider may start
   only the existing ASG's one permitted host; do not manually scale out.
3. Discover the sole task's actual container-instance/EC2 ID, check expected VPC/
   SG/AMI ownership, SSM Online and agent>=3.1.1374.0 (plus current security
   support). Installed local plugin is1.2.896.0. Use
   `AWS-StartPortForwardingSessionToRemoteHost` only to the exact recorded RDS
   endpoint on5432, local loopback15432 if free; no broad shell/RunCommand or
   inbound rule. Stop if agent/private route is unsupported; no automatic upgrade.
4. Authorize one private decrypted retrieval of
   `/clip/test/database-master-password` for the operator's read-only SQL metadata
   preflight, captured in memory only; no master credential in task overrides,
   image, command arguments, environment dump or output. Use username
   `clip_test_admin`, database clip_test, host equal to the original RDS hostname
   for TLS verification, hostaddr127.0.0.1 through the tunnel and port15432. Require
   verify-full and an approved AWS RDS trust bundle/system trust; reject bad TLS,
   never disable verification. Bound connection3s, SQL5s, locks3s, tunnel/inspection
   to10minutes. Inspect catalogs/migration metadata only: report safe presence/
   match/count/privilege/logging flags, never business rows, role password hashes,
   key commitments or credentials. No authentication-key/email-secret read.
5. Stop on wrong target/collision/missing migrations/unsafe grants or logging,
   unavailable permission, concurrent work or unexpected spend/configuration.
   No self-repair, migration, setup-function call, role/password/grant/URL creation
   or retry of an uncertain mutation. Capture sanitized findings for the next
   exact SQL/setup approval. The current preflight validator may reject RDS
   logging defaults; this is a finding, not permission to change them.
6. Close only the owned tunnel/session and stop only the owned task. Under the
   explicitly approved development cleanup guard, recheck empty tasks and desired
   services, sole owned host and ASG min0/max1; then restore desired0 rather than
   waiting15minutes. If concurrent work appears, preserve it and ask the operator;
   otherwise use normal managed draining/scale-in when prompt cleanup is unsafe.
   Stop the same RDS only after verifying the serialized window is still ours.
   Verify original stopped/zero baseline and host/root deletion. No deletion of
   persistent data/secrets, snapshots, state, IAM or task definition. Retain normal
   managed scale-in behavior; development override ends before production.

### Duration, cost, permissions and retention

One operator, one task, at most one existing host and original RDS. One-hour
operator cutoff from first start submission, including startup/checks/cleanup;
record actual UTC start/deadline before mutation. Stop early on failure. Task has
its own30minute sleep bound; the whole window and AWS spending are not automatic
hard caps. Escalate cleanup failure and report remaining billable resources.

AWS Pricing GetProducts current Mumbai On-Demand results: c7i-flex.large Linux
Shared0.08479USD/hour; PostgreSQL db.t4g.micro Single-AZ0.021USD/hour. Combined
one-hour compute0.10579USD; allow an operating ceiling1USD for this short run,
including small root-volume/control-plane/NAT/log traffic, not an AWS-enforced
cap. Existing NAT/storage/backups/state retention continue independently; no new
paid subscription or long-lived infrastructure. [Session Manager on EC2 has no
additional charge](https://aws.amazon.com/systems-manager/pricing/).

Current Budgets metadata: project actual8.233USD, forecast382.855USD against
200USD limit; second account budget actual8.244USD/forecast16.25USD against5USD.
Forecast horizons differ; neither is a hard spending cap or current credit proof.
Human must explicitly accept the bounded window despite this forecast mismatch;
no assumption that earlier budget deferral authorizes it. The prior25USD reserve
and remaining credits are not freshly verified. No budget/alert changes proposed.

[Official remote-host forwarding prerequisites](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html)
require appropriate SSM agent/plugin and network connectivity. Local source runs
from13db098; the old container is only a bounded host keeper, not a deployed
Identity revision or provider acceptance. If this window is approved, it authorizes
only the stated starts/task/tunnel/master-secret read/metadata SQL and guarded
cleanup. All database writes and runtime provisioning remain separately gated.


### Private preflight execution — failed metadata check, cleanup complete

Aditya explicitly approved the bounded window. Anchor2026-10-24 21:40:05 UTC,
deadline22:40:05 UTC. Original RDS reached available; one secret-free sleep task
ran on the expected sole private host. SSM agent3.3.5390.0, exact VPC/SG/AMI and
host ownership checked. Approved tunnel and hostname-verified TLS with the public
AWS RDS regional CA bundle succeeded. Requested one master-secret retrieval kept
in memory; no authentication-key/email-secret retrieval or DB writes.

Metadata collection failed with UndefinedTable before publishing its snapshot.
The likely missing relation is public.schema_migrations at the migration check;
the failing relation was not separately confirmed. No complete versions/grants/
logging snapshot or canonical startup acceptance is available. Do not infer
Identity migrations applied or that a new role can be created. No automatic
migration or repeat secret read was attempted. A focused, separately approved
metadata follow-up must establish actual schema state before any write plan.

Task/tunnel stopped; host terminated, root deletion confirmed, ASG0/no instances.
Initial desired-zero cleanup was rejected with ScalingActivityInProgress; waited,
rechecked idle guards and successfully submitted it with honor-cooldown. RDS stop
accepted; original RDS confirmed stopped by 2026-10-24 21:59:41 UTC. Final
cluster hosts/running/pending0, shared API desired/running/pending0 and no active
SSM sessions. Owned host/root deletion and ASG0 confirmed; cleanup complete
within the one-hour window. [Sanitized execution record](id-01-step-12/database-preflight-result.json).
No email, deployment, IAM/network or secret provisioning action occurred. Retain
existing NAT, data, credentials/state and task definition; task-wide acceptance pending.

Aditya verified the execution failure/cleanup and authorized commit/continuation.
Next: prepare a focused metadata collector that checks relation existence before
querying it and retains safe partial diagnostics, then obtain a new bounded
window/secret-read approval if live follow-up is needed. No migrations or role
setup can proceed on this incomplete schema evidence.


### Safe metadata collector follow-up

Previous failed preflight/cleanup verified by Aditya and committed4628904. Local
`database_metadata.py` replaces the ad-hoc all-or-nothing diagnostic pattern for
future inspections; it does not change the strict setup/runtime validators.
It checks the migration relation's existence, kind and version column before any
known-version query. A missing tracker/unsupported relation/schema is a finding;
remaining catalog checks continue. Uses one bounded repeatable-read/read-only
transaction, stops on wrong target, exposes only fixed safe fields and code-owned
failure phases, and retains completed findings if a later query/connection fails.
`complete=true` only describes collection, never setup acceptance. No key binding,
credential hash, contact/business data, raw exceptions or arbitrary row dumps.

`test_database_metadata.py`:9actual disposable PostgreSQL cases pass; normal
catalog findings, missing tracker/column/Identity schema, wrong database/admin,
actual read-only snapshot, late partial-result preservation and private connection
error suppression. Strict mypy passes the new module. No new CLI, AWS call,
secret read or live window. Commands registered in the existing registry.
Focused log `/tmp/clip-id12-database-metadata-focused.log`; full gates passed in
`/tmp/clip-id12-database-metadata-check.log`. Aditya verified and approved the local result.
A new exact window and master-secret-read approval is required before live use;
previous window is closed and RDS/host remain at verified stopped/zero baseline.

[Collector source snapshot](id-01-step-12/database-metadata-source-hashes.json).

Final collector checks — 2026-10-24 22:06:46 UTC: `make check` exited0/all11gates;
1031Python passed/1existing DB-only skip,63data/118web, Black151files, zero boundary
violations, current contracts, types/lint/build,35wrapper safety cases, actual
PostgreSQL18.6 lifecycle and Gitleaks8.30.1 source scan.9focused cases, strict mypy,
source hashes, relative file links and diff whitespace pass. Aditya verified and approved the local result; no new live checks or readiness claim.


### Renewed metadata window — approval request

Prepared2026-10-24 22:08:21 UTC after Aditya verified/approved the local collector,
committed9bfb607. This is a new run, not an extension of the closed21:40:05 window.
Use the exact targets, private network, task:1/digest/sleep-only overrides,
SSM prerequisites, rate references, one-hour total/1USD operating ceiling and
owned guarded cleanup in the earlier private-window plan. Account335523638354,
region ap-south-1, profile adityalaxmi1; original RDS
clip-shared-test-postgres/db-PYRRZJPVKPGHIXDAHUWATXGH7A; clusterclip-shared-test,
capacity providerclip-shared-test-capacity and ASGclip-shared-test-ecs-host.
Fresh account/idle-resource/session checks and an exact UTC deadline are required
before any start. No resource names, configuration or privilege expansion.

Only changed inspection behavior: run the source-pinned `collect_database_metadata`
from9bfb607 after verify-full TLS to the original RDS hostname. Authorize one new
private in-memory master-secret read from `/clip/test/database-master-password`;
no other decrypted parameters. Safe results now include tracker existence/type/
column and required-version flags, Identity inventory, role collision, logging/
parameter permissions and PUBLIC ACL counts. Preserve partial findings with a
fixed phase when incomplete; a missing tracker is reported rather than queried.
No business/key-binding rows, credential hashes or raw diagnostics. A complete
metadata report does not authorize setup or establish runtime readiness.

No DB writes/migrations/roles/grants/URL provisioning, emails, deployment, IAM,
network changes or NAT cost work. Stop after findings and restore the approved
stopped/zero baseline; no automatic repair. Existing forecast mismatch and
unverified credits/reserve remain disclosed; renewed approval must cover the
bounded cloud starts, one sleep task/tunnel, one master-secret read, read-only SQL
and guarded cleanup. Previous window's approval is spent; no new mutation yet.


### Renewed live findings — 2026-10-24 22:21:47 UTC

Approved renewed window uses collector9bfb607. Exact private host/task/network
and SSM agent3.3.5390.0 verified; private tunnel and verify-full TLS succeeded.
One private master-secret read requested in memory; no key/email-secret access.
Safe metadata collection completed, target matched, no failed phase:

- public.schema_migrations does not exist; no migration versions can be verified.
- All14expected Identity tables are absent and clip_test_identity_app is absent.
- PUBLIC database/schema-create/relation/default-relation grant counts are all0;
  do not repeat shared PUBLIC revocations.
- Five of six effective logging checks match; log_min_error_statement does not.
  Catalog SET permission flags are false for all six parameters; this is not an
  attempted SET/ALTER test or proof of all RDS special-administrator behavior.
  Audit/auto-explain checks match the disabled requirement.

[Sanitized report](id-01-step-12/database-preflight-followup-result.json) preserves
these completed observations. No setup readiness: first prepare an exact,
affected-owner-reviewed migration plan for the already tested combined chain and
review safe logging/permission handling before login/URL provisioning. Tracker
absence is confirmed; do not infer other domains' entire schema state from the
Identity-only inventory. No automatic schema/role/grant/default/logging repair.
Final cleanup verified 2026-10-24 22:27:20 UTC: original RDS stopped, owned task/tunnel
closed, ASG0/empty, cluster hosts/running/pending0, API desired/running/pending0,
no active sessions, owned host terminated and root volume deleted. Guarded scale-in
accepted with cooldown honored; all work finished before23:13:36 UTC deadline.
No IAM/network/NAT/provider changes; persistent data/secrets/state retained.

Gitleaks8.30.1 source snapshot, sanitized JSON, relative file links and diff
whitespace pass. Prior1031Python/63data/118web/full11gate collector checks remain
source-identical; not rerun for this evidence-only increment. Aditya verified the execution findings and cleanup; evidence/documentation
uncommitted. ID-READY remains incomplete.


## Migration and safe-logging plan

Planning checkpoint2026-10-24 22:44:26 UTC, Aditya(A). Last live result is verified:
original RDS stopped, shared host/task/session capacity0; public tracker and all
Identity tables absent. No AWS account queries or mutations in this planning
increment. Existing local combined migration checks passed at9bfb607; this is
not permission to apply to shared RDS.

Audit of execution order found two material gaps in an Identity-only apply:
its3forward migrations depend on the earlier shared baseline, and the old API
image includes neither dbmate nor migration files. Public tracker absence alone
also does not prove every other domain namespace is absent. The plan therefore
uses the existing14file combined chain, preserves every SQL file unchanged, and
requires metadata checks for all4namespaces before any live migration. The
existing local wrapper targets clip_local; the Listings lifecycle script targets
its isolated rehearsal. Neither may be reused against shared RDS by overriding
its target checks. No canonical task-step waiver, new migration or fake schema.

### Ordered checkpoints and gates

| Order | Work and output | Dependency/check/gate |
|---|---|---|
| 1 | Implement an Identity-owned fixed-target migration runner and rollback-only logging probe locally; register commands. | Human verifies this plan first. Local disposable PostgreSQL/TLS only; no cloud. Keep app startup, existing wrappers, migrations and Suraj's code unchanged. |
| 2 | Test real14file dbmate clean/repeat plus TLS hostname rejection, input/hash/target/collision refusals and safe logging rollback; preserve sanitized evidence. | Actual local PostgreSQL/dbmate, not a schema double; strict types/format/full applicable checks and result verification. |
| 3 | Review exact manifest/image and affected-owner scope; refresh accepted upstream before a live request. | Shared-schema/migration integrator and affected B/C/D owners review the14file scope; do not infer peer approval from local tests or this plan. [Manifest](id-01-step-12/shared-migration-manifest.json) pins current source; digest/remote-currentness remain gates. |
| 4 | Prepare fresh bounded private execution window using the established sleep task/tunnel; inspect all4namespace names, tables/tracker, owner and migration state. | Separate exact cloud/secret-read/cleanup approval. Stop on any existing project namespace/manual/partial state or active writer. No unreviewed adoption, reset, down or drop. |
| 5 | Run the separately approved rollback-only logging permission probe, reconnect and verify no role/default persisted. | No password/application-data operation; static probe SQL only. Stop on any failure; catalog SET flags are not substituted for an actual RDS permission test. |
| 6 | Apply the pinned14file chain using dbmate migrate --strict; inspect exact versions/head and structural invariants read-only. | Separate explicit shared-schema DDL approval for exact source/head/manifest and baseline. No create/drop database command or synthetic users; only the existing catalogue migration's approved categories/conditions. |
| 7 | Record prefix/head, results and recovery state; restore owned stopped/zero baseline. | No automatic retry, down or namespace deletion on failure. Human verifies result; role/password/URL provisioning remains a later exact action. |

### Local runner transport and credential design

Proposed runner targets only the original RDS endpoint/clip_test/clip_test_admin
and the approved loopback tunnel; local tests have a separate explicit disposable
route. Use dbmate2.36.0 with reviewed image digest (tag alone is not the live pin),
read-only migration/CA mounts, --env-file /dev/null, --no-dump-schema,
--migrations-dir /db/migrations, migrate --strict. No implicit .env, glob-selected
extra migrations, bootstrap SQL splitting, custom replacement migration engine,
or rewriting published SQL. Inspect file count/version/SHA before and after.

On this verified Linux host, use a local Docker container with host networking
and container-only `--add-host original-rds-hostname:127.0.0.1`, connecting to15432
with sslmode=verify-full and the public regional CA bundle. This preserves the
original hostname for certificate verification without global /etc/hosts changes
or disabling TLS. Other platforms are unsupported until separately verified.
Mount source/public CA read-only, drop capabilities, no-new-privileges, read-only
root, bounded tmpfs if required, unique owned container/name and --log-driver=none.
No shared host mount or private Docker socket inside it.

Keep DATABASE_URL non-secret, with explicit host/user/database/TLS and bounded
connection/SQL settings. Pass the privately retrieved credential over stdin to a
fixed shell that reads it, exports PGPASSWORD only inside the running process and
execs dbmate. Never pass PGPASSWORD as a Docker --env/config value, embed it in
URL/argv, write a passfile or expose raw client output. Reject newline/NUL or
unsupported credential encoding before submission. No shell interpolation of
secrets. Capture/suppress raw output in operator process memory; emit only fixed
phases/results and independently collected safe metadata. Docker process memory
is private to this approved operator route; remove the owned container on exit.
Local tests must prove credential absence from Docker inspect configuration and
sanitized output. No AWS permission or secret-manager access inside the container.

One named operator serializes the entire CLI run. Existing migrations retain
transaction advisory key(1129072976,8)/10s lock wait; dbmate2.36 has no global
--migration-lock flag. Bound connection3s, statements30s, process5minutes and
finite lock waits; treat tool/network/commit uncertainty as a stop, not a replay.
Each migration commits separately: a failure can leave an applied prefix and an
empty/partial tracker. Preserve it, record versions without private rows, inspect
before a forward-recovery plan; never claim the whole batch rolls back atomically.
Do not restore an entire shared instance or drop other domains as a convenience.

### Safe logging probe design

Prior PD-16 recorded successful transaction-local logging guards on this same
RDS; the new collector's false has_parameter_privilege flags are not a definitive
runtime denial. PostgreSQL/RDS settings and ALTER ROLE restrictions still require
actual checks. Proposed probe: bounded transaction; verify target/idle baseline
and absent fixed `clip_test_identity_logging_probe`; attempt the exact approved
session-local logging settings; create only that NOLOGIN, non-elevated probe role,
apply the six proposed per-role logging defaults, inspect their names/values and
always ROLLBACK. No password, SCRAM verifier, membership or data grants. Verify
absence of the role and unchanged session/default baseline after rollback through
a fresh connection. Role-name collision or insufficient privileges stops the
probe; no overwrite, grants to rds_superuser, global parameter change or fallback.
The live probe is catalog-writing SQL inside a rolled-back transaction and needs
explicit approval; planning/local tests authorize no such live SQL.

If the probe fails, review its fixed phase and RDS-supported alternatives before
migration/app login setup. No blanket logging weakening or parameter-group apply.
Sources: [RDS parameters](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.Parameters.html),
[PostgreSQL18 ALTER ROLE](https://www.postgresql.org/docs/18/sql-alterrole.html),
[pinned dbmate dependency source](https://github.com/amacneil/dbmate/blob/v2.36.0/go.mod),
[driver hostname verification](https://github.com/lib/pq/blob/v1.12.3/ssl.go).

### Scope and immediate next action

No live run is approved by this document. Next is only checkpoint1/2 local
implementation and tests after human plan verification. Reserve A-owned Identity
runner/tests/command/evidence paths; no migration edits or shared Terraform/file
writes. Any unexpected baseline, unclear recovery, owner objection, unsupported
TLS/tool behavior or changed scope stops for a targeted decision. Public/cost/NAT
redesign remains deferred. Login/password/grant/URL provisioning, runtime IAM,
proxy/TLS deployment and real provider/browser acceptance remain later gates.


### Local migration runner and rollback logging probe

Aditya verified the migration/logging plan. Implemented `migration_runner.py`
(operator-only; no AWS retrieval, live CLI or API startup import). Fixed live target
or explicit disposable target,14file manifest/SHA checks and immutable image/tool
version gate precede credential submission. The current manifest still rejects
live use pending image review. A session advisory lock serializes this wrapper;
existing per-file locks remain unchanged. Fresh run requires all4project namespaces
absent; repeat requires exact14versions and33tables/25functions/37triggers. Partial,
manual, unknown or inconsistent state refuses without automatic adoption/replay.

Local dbmate transport uses verify-full TLS, read-only public CA/migration mounts,
container-only hostname mapping and Linux host networking. Credential enters stdin
and is exported only inside the running shell process, absent from URL/args/Docker
Config.Env. The container runs as the operator UID/GID with read-only root, dropped
capabilities, no-new-privileges and logging disabled. Connection/process/SQL/lock
bounds apply; raw subprocess errors/output stay suppressed. Zero client exit is
insufficient without the full postcondition. Failures preserve committed prefixes;
no down/reset. Named cleanup covers both version and migration containers, including
a timed-out CLI; cleanup uncertainty emits a fixed failure instead of claiming done.

Logging probe applies only transaction-local settings and6defaults to the fixed
passwordless NOLOGIN role, always rolls back and verifies role absence/unchanged
baseline through a fresh connection. Existing-role collisions refuse; a late SQL
failure rolls back. No global defaults, memberships, real passwords or data grants.
Local success is not proof of RDS administrator permissions.

`migration_fixtures.py` supplies owned loopback TLS PostgreSQL with ephemeral
synthetic CA/server material; no real/private environment input. `test_migration_runner.py`
exercises actual dbmate/TLS/SQL plus controlled failures and actual Docker config
inspection. Focused final cases/types and full gates recorded below after completion.
Local tested image: dbmate@sha256:520c740c6e0ad73fde2cd1ea7e2b779aaf789d22aca8858f87a478e7094535fb,
Linux ARM64; live image review remains pending. No migration SQL, deployed image,
AWS/IAM/network/provider or shared-database change. No native macOS/AMD64 claim.

[Runner/probe source snapshot](id-01-step-12/migration-runner-source-hashes.json).

Final local runner/probe result — 2026-10-24 23:07:15 UTC:17focused tests pass
(`/tmp/clip-id12-migration-runner-focused-complete.log`), strict mypy passes the
implementation (`/tmp/clip-id12-migration-runner-types-final.log`). Final
`make check` exited0/all11gates:1048Python passed/1existing DB-only skip,
63data/118web, Black154files, zero boundary violations, current contracts,
types/lint/build,35wrapper safety cases, actual PostgreSQL18.6 lifecycle and
Gitleaks8.30.1. Final log `/tmp/clip-id12-migration-runner-final-check.log`;
earlier gate log retained but superseded after the timeout-cleanup correction.
Source/migration hashes, JSON, relative file links and diff whitespace pass.
No runner-owned containers remain. No AWS/shared writes, provider calls or secret
retrieval in this increment. Aditya verified the implementation and authorized commit/continuation; real RDS
probe/migrations and affected-owner/image review remain separately gated.


## Source review and live logging-probe gate

Prepared 2026-10-25 01:44:19 UTC. Aditya verified the local runner/probe and authorized
commit/continuation; implementation/evidence committed
ca935b950a173a33f34641ea3cf80012f7f93f03. Fresh `git fetch origin main` confirms
upstreamdefec38f59d4acb683f7b51950860f458aacfdd1 unchanged. Its11migration files
are byte-unchanged; this branch adds only the3Identity forwards, producing the
manifest's14file chain/head20261023202807. No new source edit or AWS call here.

Bounded independent review package: branch task/id-01-identity, headca935b9,
baseorigin/main@defec38f, [manifest](id-01-step-12/shared-migration-manifest.json),
[runner source hashes](id-01-step-12/migration-runner-source-hashes.json),
[17case/full-gate result](#local-migration-runner-and-rollback-logging-probe).
Rahul(D) is Aditya's primary human peer; affected B/C/D schema owners review their
shared surfaces using the [peer review prompt](../../prompts/peer-review-prompt.md).
Review source/current tests, unchanged11baseline files plus3new forwards, TLS and
stdin credential boundary, no-op/prefix/timeout guards, logging rollback and
shared target/recovery assumptions. No independent approval is recorded or
inferred. This is a local review package, not a published PR/push or merge request.
Image digest review and shared DDL approval remain pending; current manifest
still refuses live migration execution.

### Proposed next window: logging probe only

This can resolve RDS permission uncertainty without applying the shared migration
chain. Exact proposed scope, awaiting explicit fresh approval:

- Account335523638354/ap-south-1, profileadityalaxmi1; original RDS
  clip-shared-test-postgres/resource db-PYRRZJPVKPGHIXDAHUWATXGH7A. Recheck account,
  exact stopped target, idle API/services/tasks/ASG/sessions and serialized operator
  window before mutation; record a new UTC anchor/deadline.
- Same bounded infrastructure as the completed preflights: start only that RDS;
  one existing task clip-test-identity-email-ap-south-1-id01:1, exact unchanged
  [sleep1800 overrides](id-01-step-12/database-preflight-task-overrides.json),
  digest3ef8b13d3b102dc97e67d79d91e43eb8d4b2cc02fbabb45cf6001c8a93eddd1d,
  capacity providerclip-shared-test-capacity and ASGclip-shared-test-ecs-host min0/
  max1. Verify sole actual private host/VPC/SG/SSM before the same ten-minute
  endpoint-only tunnel. No API service enablement/new task registration/build/push.
- Authorize one private in-memory decrypted read of
  /clip/test/database-master-password. Verify original endpoint hostname through
  CA-backed verify-full TLS and loopback15432; connect timeout3s, SQL5s, locks3s,
  total probe process120s. No auth-key/email-secret/DB-URL parameter reads.
- Invoke only committed `probe_logging`, expected databaseclip_test and admin
  clip_test_admin. It checks absent clip_test_identity_logging_probe, sets only
  this transaction's6logging settings, creates only that fixed NOLOGIN restricted
  role, tries its6logging defaults, verifies them and always ROLLBACKs. No password,
  membership, grants or application-data SQL. A fresh connection verifies role
  absence and unchanged effective baseline. This is explicitly SQL-writing inside
  a rolled-back transaction, not a read-only operation. No global parameter group
  or persistent role/default change is approved by the request.
- Emit only the code-owned completed/rollback_verified/failed_phase fields and
  sanitized execution metadata. Stop if collision/permission/default verification
  fails; no automatic repair, new grant, schema apply or replay. A complete probe
  requires both completed=true and rollback_verified=true; cleanup is independent.
- Close owned session, stop owned task, and guarded desired0 only after STOPPED,
  empty tasks/services/sessions and sole-owned-host/min0/max1 checks. Honor cooldown;
  preserve normal draining/managed scale-in on concurrent work or unsafe cleanup.
  Stop original RDS only while still the serialized operator; verify stopped,
  cluster/ASG0, no sessions and owned host/root deletion. Retain all persistent
  secrets/data/state/IAM/task definitions/NAT. No unrelated cleanup or topology change.
- One-hour total window including startup/cleanup, one host/task maximum,1USD
  operating ceiling, not an AWS-enforced cap. Use previously quoted compute rates
  (0.08479USD/hour host+0.021RDS) as estimates, plus root/NAT/control-plane/log
  traffic; existing retained costs continue separately. Prior disclosed project
  forecast382.855USD versus200USD budget and unverified credits/reserve remain
  unresolved; no new budget query or change here. Human acceptance covers only
  this bounded window, not general future spend. Stop for unexpected targets,
  additional cost/permission/infrastructure needs or concurrent users.

Successful probe does not authorize migrations, permanent login/password/grants,
URL provisioning, deployment, provider sends or merge. After human verifies the
probe/cleanup result, return to the earliest actual schema gate with affected-owner
review and a separate exact manifest/image/DDL approval. No new live action yet.

Logging-only gate status — 2026-10-25 04:02:48 UTC: Aditya approved the exact scope;
AWS login expired before final metadata guards could authenticate. No mutation or
secret read, and no one-hour clock started. Await human sign-in, then recheck all
target/idle guards under the existing approval; do not infer fresh resource state.

Logging-only attempt — 2026-10-25 04:06:31 UTC: authentication recovered, all exact
account/idle guards passed. Recorded anchor04:05:35/deadline05:05:35 UTC, then one
RDS start request was rejected with InsufficientDBInstanceCapacity (db.t4g.micro,
ap-south-1a). Original RDS confirmed still stopped. No task/tunnel/secret read,
probe SQL or resource creation; no cleanup required. No automatic retry or class/
AZ change. [Sanitized result](id-01-step-12/logging-probe-start-result.json).
Probe remains unexecuted; current source is unchanged and readiness incomplete.

Logging-only retry state — 2026-10-25 04:37:19 UTC: Aditya explicitly requested retry.
Fresh idle guards passed; original start accepted, recovery event04:16:15.760UTC.
Readiness did not arrive within20minutes. Probe remains unexecuted, no host/task/
tunnel/secret read. Asked whether to extend readiness wait to35minutes inside the
same overall05:05:35UTC/1USD limits; unanswered, no consent inferred. Approved
cleanup stop attempted after fresh idle checks, rejected InvalidDBInstanceState
because RDS is still starting. Monitoring only for stoppable state; no class/AZ
or alternative infrastructure change. [Sanitized retry record](id-01-step-12/logging-probe-retry-result.json).
Cleanup is not complete; subsequent status must supersede this snapshot explicitly.

Recovery failure confirmed — 2026-10-25 04:42:09 UTC: original instance now stopping.
AWS event04:37:55.153UTC explicitly reports insufficient db.t4g.micro capacity in
ap-south-1a and putting the database into stopping. This explains the transition;
our earlier StopDBInstance was rejected, not accepted. No probe/secret read/host
launch. Wait-extension question is moot and no consent inferred. Await stopped
confirmation before claiming cleanup complete.

Logging-only retry closeout — 2026-10-25 04:53:05 UTC: original RDS stopped;
cluster hosts/running/pending0, API desired/running/pending0, ASG0/empty and active
sessions0 verified. No task/host/tunnel or credential read was started, no SQL
probe/migration/permanent role change. Cleanup completed inside the original
05:05:35UTC deadline. AWS capacity recovery failed; actual logging permissions
remain untested. Wait-extension question is moot, not an approval or pending
requirement. Source unchanged; Gitleaks8.30.1 snapshot, JSON/links/whitespace pass.
[Final retry evidence](id-01-step-12/logging-probe-retry-result.json). Human result
verification pending; docs uncommitted; ID-READY remains incomplete.


### Live logging probe passed — 2026-10-25 05:33:26 UTC

Aditya explicitly requested another same-scope retry after the prior stopped
closeout. New window05:22:29→06:22:29UTC/1USD; fresh account/idle checks passed,
original class/AZ/private endpoint matched. RDS reached available; one exact
sleep-only task/host and private SSM tunnel established. Committed ca935b9 source
hashes verified before import, one private in-memory master-secret read, actual
verify-full TLS to original hostname/public regional CA.

`probe_logging` returned completed=true, rollback_verified=true, failed_phase=null.
All6transaction-local settings and the passwordless NOLOGIN probe-role defaults
were accepted. Role absence and unchanged original settings were verified through
a fresh connection. This resolves the earlier RDS-specific setting/default
permission uncertainty despite false catalog SET flags. No global parameter change,
permanent role/password/grant, data/migration/provider operation, or key/email-secret
read. [Sanitized result](id-01-step-12/logging-probe-20261025T052229Z.json).

Owned tunnel/task stopped, host terminated/ASG0 and root deletion confirmed;
original RDS stop accepted and confirmed stopped by 2026-10-25 05:41:05 UTC. Final
cluster hosts/running/pending0, API desired/running/pending0, ASG0/empty and active
sessions0; owned host/root removed, cooldown honored. Cleanup complete inside the
06:22:29UTC deadline. Gitleaks8.30.1 source snapshot, JSON/source hashes/links/diff
checks pass. Source unchanged; no full-suite rerun for evidence-only changes.
Aditya verified the live result/cleanup and authorized commit/continuation.
Migration
chain/affected-owner/image review and exact shared DDL approval remain separate.


## Shared migration apply review package

Prepared 2026-10-25 05:56:34 UTC; live probe/cleanup human-verified, evidence committed8df97eb.
Fresh origin/main remainsdefec38f. GitHub CLI found no PR for task/id-01-identity
(all states), so no PR review can be cited; offline reviews remain unknown.
[Machine-readable review candidate](id-01-step-12/shared-migration-apply-review.json)
pins head8df97eb, source manifest SHA
c5259bd6b4b2427505ffffd52903931ac626d5d6c8f065a9756c3a0126f028a3,
14files/head20261023202807 and tested dbmate digest. This is not executable
approval: manifest image-review flag stays pending; no SQL/manifest bytes changed.

Review scope, without reopening accepted unchanged baseline SQL:

| Scope | Concrete behavior and check |
|---|---|
| 11upstream migrations, unchanged | Shared namespaces/FKs/triggers and catalogue plus accepted Listings forwards; byte equality against fetched base. First apply affects all4namespaces, so serialize shared owner/operator window. |
| Identity20261023173439 | Profile/contact bounds, paired chronological revocation and immutable external-account binding; validates rather than scrubs existing records. |
| Identity20261023192856 | Protected OTP fields plus4key/idempotency/send/verification tables, constraints/indexes; no key adoption or credential generation. |
| Identity20261023202807 | Session last-seen/bounds plus3password/source/Microsoft-attempt tables; no sessions/accounts created. |
| Runner/image | Version2.36.0, reviewed immutable digest, exact file hashes, TLS/credential handling, prefix/postcondition/cleanup behavior;17local focused tests/full11gates and real rollback logging proof already recorded. |

Rahul(D) is the primary independent human peer. Affected owners confirm the
shared first-apply scope and consuming constraints; original11accepted files do
not require editing/reapproval as new code. Use the
[peer review prompt](../../prompts/peer-review-prompt.md) with base/head and this
bounded scope. Author/agent review does not substitute for human approvals.
No review request/comment/message was sent, no PR/push created, and no approval
inferred from task-step verification. No matching PR is not proof that offline
review did not happen; ask Aditya for any such recorded approvals.

Proposed execution, after review gates and a separate exact live DDL approval:

1. Record reviewer/image decisions; update manifest image fields only from actual
   reviewed evidence, regenerate its SHA and the final exact request. Do not
   manufacture a reviewed flag merely to make the runner execute.
2. Fresh one-hour/1USD original-RDS/one-sleep-task/private-tunnel window,20minute
   startup bound, no automatic start retries. Same known class/AZ/resources and
   cleanup as passed probe; public rates are earlier quotes, not a current bill.
   Disclose capacity risk and fresh operator/budget constraints before the run.
3. Verify exact current target/engine, exclusivity and actual all4namespace/tracker
   state, owner/permissions and source hashes. Last inspection proved only absent
   Identity/tracker; do not assume Listings/Search/Conversations namespaces absent.
   Abort before DDL on partial/manual schemas, unexpected tracker or concurrent
   application use. Preserve Suraj/other owners' databases and work.
4. One approved private master-secret read for trusted connection and dbmate's
   stdin runtime credential. Original host verified over TLS; fixed runner uses
   the exact reviewed image/manifest, not the API image or local/LI-02 wrappers.
5. Execute migrate --strict only. Existing per-file advisory locks retained;
   wrapper lock/serialized operator covers this invocation. Each file commits
   separately; no batch-atomic claim. Expected14versions/head,33tables/25functions/
   37triggers. Only existing approved catalogue seed; no users/fixtures or live
   mutation smoke scripts. Read-only catalog postchecks, never business row dumps.
6. On failure, preserve applied prefix and actual safe metadata; no down/drop,
   reset, global permission/logging repair, restore or replay. On success, record
   sanitized versions/inventory. Close owned session/task, honor cooldown and
   guarded host/root cleanup; stop original RDS only while the window is still
   exclusive. Verify stopped/zero and disclose any cleanup uncertainty.

Permanent Identity login/password/grants, DB-URL publication, runtime IAM,
proxy/TLS deployment, providers/browser/device/peer/CI acceptance remain later
gates. Current review candidate is complete as a review artifact, not as an apply
artifact. No AWS call/change or new SQL execution in this preparation increment.

Owner-facing change/reason/check handoff: [cross-owner review](cross-owner-review.md),
covering the full Identity branch plus direct Listings/shared impacts.


## Pre-merge migration and configuration audit — 2026-10-25 09:32:32 UTC

Aditya(A) authorized local review/preparation while Suraj integrates Mohit's PR.
Scope remains ID-READY/Step12; no live inspection, SQL, provider send, Terraform
plan/apply, main integration or publication occurred. Source remains `8df97eb`,
recorded local upstream `defec38f`; that local ref is not a fresh remote observation.
Aditya reports Suraj/Rahul have found no conflicts so far. Final exact-revision
technical/peer approval remains pending after main integration.

### Audit result and dependencies

No new task-definition gap was found against ID-01 Steps2–12 and the stub guide.
The existing execution order is sound: reconcile upstream, validate source and
schema, review exact plan, approve live window, preflight, migrate, provision the
runtime separately, then verify real providers/UI. The following material
operational gates must stay explicit:

| Area | Local finding | Required resolution/evidence |
|---|---|---|
| Migration bytes | All14manifest paths/hashes match; all11SQL files from pinned main are byte-identical. Candidate manifest SHA matches. | Refresh against the actually merged main, not the old remote-tracking ref. Preserve published SQL. |
| Runner compatibility | `migration_runner.validate_manifest` fixes14files/head20261023202807; `_baseline` fixes33tables/25functions/37triggers. | If upstream adds migrations/objects, update the owned runner, fixtures, inventory expectations, manifest and candidate together; repeat real disposable lifecycle/failure checks. Do not weaken guards or merely edit JSON to pass them. |
| Live schema baseline | Last live metadata was not a complete four-domain inspection. Successful logging probe is rollback-only. | Fresh all-four-namespace/tracker/owner preflight in an approved exclusive window; stop on partial/manual/unknown state. No automatic adoption/reset/replay. |
| DB privileges | Proposed SQL and `database_setup.create_identity_role` agree:14Identity tables, four append-only guards, users without DELETE, remaining nine with CRUD; tracker SELECT and schema USAGE only. Setup additionally grants explicit DB CONNECT. | Fresh inherited/PUBLIC/default grants, ownership and logging checks before separate role creation; verify actual app-role denials. Never change Listings credentials or silently revoke PUBLIC. |
| TLS/runtime | Migration probe used an explicit regional CA; app remote URI requires verify-full with system roots. | Prove RDS certificate trust and hostname verification in the final app image. Probe success does not establish app-image trust. |
| Cloud source | AMI pin preserves existing image; desired SES FromAddress is verify@; last inspected sender permission was still no-reply. | After main integration, review a fresh full shared-root plan with existing approved inputs preserved. No unrelated launch-template/ASG/RDS/network changes; review unexpected drift rather than apply it. |
| Secret/runtime wiring | Keys/email references exist historically; Identity DB login/URL, task scoped reads and final deployment are pending. | Separate private role/URL/IAM/build/deploy plan. Keep admin credentials out of app runtime. Rotate the previously exposed Resend key privately. |
| Consumer/browser readiness | Default API remains Identity-unbound; Listings web protected writes still need the shared Origin/marker/CSRF integration described in the owner handoff. | Coordinate affected-owner changes, then verify actual browser writes. Synthetic HTTP tests do not establish that the unchanged browser helper sends required headers. |

These are readiness conditions, not evidence of a decision conflict. No production
code/configuration was changed during this audit. Current image-review and live
approval flags remain closed.

### Prepared execution sequence and decision gates

1. **After Suraj's merge:** fetch accepted main, identify exact base/head and inspect
   migrations, contracts, shared API/frontend composition and Terraform deltas.
   Integrate into this branch through the normal verified checkpoint. Resolve
   conflicts within owned/reviewed paths. Reconcile fixed runner assumptions as
   needed, run the full local CI-equivalent gate and refresh source evidence.
2. **Finalize shared migration review:** record independent/affected-owner and
   immutable image review against the integrated revision. Regenerate manifest
   hashes/count/head/inventory and candidate SHA from actual source. Current
   fourteen-file figures are a pre-merge snapshot, not future deployment constants.
3. **Request exact migration window approval:** use the candidate's fixed target,
   account335523638354/ap-south-1, original RDS, one task/host, one hour/$1 ceiling,
   startup20minutes, no automatic starts/retries, secret-read scope and cleanup.
   Assign one operator; confirm other owners idle. Dates and approval must be new;
   past logging-probe authorization is not reusable.
4. **Approved live preflight/apply:** verify target and current four-schema state,
   image/source/TLS and logging; run only the reviewed strict migration route.
   Record versions/head/structural invariants, not business rows. Failure preserves
   committed prefix for reviewed forward recovery; no down/drop/reset or retry.
   Close owned tunnel/task and verify guarded cleanup without interrupting others.
5. **Separate runtime setup:** review/approve Identity role/password/DB-URL and
   scoped SSM/IAM changes, sender policy if needed, trusted proxy/TLS configuration,
   immutable image composition and deployment. Verify denied cross-domain/DDL
   privileges and effective safe logging. Do not enable production/fake bypasses.
6. **Real acceptance:** under separately approved identities/recipients/send caps,
   run the matrix below and retain sanitized source-bound results. Any required
   cloud verification follows Step13's exact approval requirements; Step14's full
   consumer matrix remains outside ID-READY scope.
7. **Milestone handoff:** refresh full local/hosted CI for the PR revision, obtain
   independent and affected-owner approval using the peer-review prompt, human
   verification and separate exact merge approval. ID-READY is not complete now.

### Real runtime acceptance checklist prepared for execution

| Path | Required observed result |
|---|---|
| Microsoft/IISc | Actual PKCE/state/nonce callback and valid signed claims create/reuse the stable account; wrong domain, replay, expiry and invalid assertions deny safely; consent/cache behavior reviewed. |
| Temporary activation | Controlled verify@ receipt and code redemption activate once; resend/expiry/replay behavior and three verification attempts through latest OTP expiry hold; no token/code/contact output. |
| Password/reset | Minimum8characters enforced; real sign-in/reset succeeds, reset revokes old sessions and preserves the original14day lifetime. Uniform acknowledgement and provider-failure behavior verified. |
| Protected HTTP/UI | Real cookies, HTTPS/proxy source handling, Origin/CSRF, logout/stale/expired/revoked denial; Listings buyer/seller smoke via reviewed integration, desktop and supported phone UI. No full Step14 claim. |
| Contacts | Own edits/deletion and selected-field disclosure use trusted scope; unrelated user/unauthorized conversation denies; contacts never appear in general profile/error/log output. Actual CN-02 journey remains with its real dependencies. |
| Delivery routing | Resend is usable before SES production access, with controlled recipients. Verify actual loader/task permissions and bounded primary/alternate behavior. SES sandbox remains restricted; switching primary must respect the four-hour lazy refresh. |
| Retention/operations | Approve and verify cleanup operation/schedule, deadlines and permanent guards, with no cross-domain deletion. Remove development scale-to-zero override before production; retain safe shared cleanup. |

Local checks performed for this audit: manifest/file SHA equality, upstream SQL byte
equality, candidate manifest SHA and closed-live-gate assertions passed. No code
changed, so prior test results are referenced rather than presented as fresh runs.
Full post-merge validation and every live acceptance item above remain pending.

### Offline review checker — 2026-10-25 11:38:34 UTC

Aditya authorized autonomous local checkpoints/commits in a separate worktree,
with decisions resolved locally where possible; cloud/sends/other-owner changes
and publication remain separately gated. Worktree `/tmp/clip-id-ready-local-hardening`,
branch `task/id-ready-local-hardening`, starts from85c4606. Main worktree is untouched.

Added `scripts/identity_readiness.py` to turn the migration review's local checks
into a repeatable offline command, registered in the command guide. It checks full
immutable/integrated upstream SHA, candidate/manifest base and SHA, the actual
runner's file/count/head rules, recorded local image, all upstream SQL bytes and
reviewed migration/setup source. Local uncommitted edits invalidate source review;
external Git diff/text conversion drivers cannot execute. It neither fetches nor
loads settings/credentials, connects to SQL, starts Docker, sends mail or grants
approval. Output always states `ready_for_live:false`, even when consistent.

Twelve offline tests passed: genuine disposable Git history with changed/extra/
missing/symlink SQL, unreviewed runner edits, advanced/unintegrated main, corrupt
manifest hash, wrong image, invalid input and external diff driver refusal.
Strict mypy and boundary check passed. The current actual package passes all nine
local checks againstdefec38f. New upstream still requires main integration and
refreshed lifecycle/full CI checks; no live-readiness acceptance is implied.

### Explicit local runtime preparation and image trust finding — 2026-10-25 11:46:06 UTC

Added `scripts/identity_runtime.py` and its owned tests. The command wraps existing
`prepare_local_identity` and shared `create_app` without changing default startup,
Settings, domain services, contracts, web pages, Dockerfile or Terraform. It refuses
missing Listings configuration/debug before secret bootstrap, requires an explicit
mode plus acknowledgement, and uses only the registered localhost5173 loopback
browser policy. Check-only validates real Identity bootstrap without a listener or
Listings pool; serve binds127.0.0.1:8000, one worker, no reload/forwarded-header trust,
with existing safe JSON logs. Exceptions print fixed text, not private SDK/DSN data.
Either real invocation still requires separate approval; no invocation was made.

Fourteen tests passed, including offline mode/opt-in/failure/listener controls and
an actual owned PostgreSQL/HTTP test: activation/session cookie/profile and allowed
owner-list read, temporary seller-write denial and hostile Origin refusal. The new
test initially used the wrong profile URL and an incomplete image-upload body;
corrected the test to the canonical /me route and full reviewed request schema.
No implementation behavior was changed to satisfy it. Strict mypy passed.

**Concrete remaining image trust gap:** cached `python:3.14.8-slim-trixie` image ID
`sha256:cbe8543d6805b7a78660e2ea2f17dc9313c6dfe38090b4958cc1fba9fea9ac10`
is AMD64. Its extracted system CA bundle has150roots and contains none of the3
roots in the public ap-south-1 RDS bundle used by the successful probe (bundle SHA
`ca4a9dc14e06c3f84274eff3ffed0e5d4d3463141593e1159eb4a0904df6cd74`).
Current Dockerfile does not add them; app DB URI requires sslrootcert=system.
This confirms missing regional trust material, not a fresh live RDS chain check.

The first network-disabled image process attempt failed with exec-format error on
this ARM64 host. Rechecked by creating an owned stopped container and copying its
public system CA file; no image process/network or cloud operation was used.
Compared DER certificate bytes using host SSL contexts; removed the owned container.
No image rebuild, root-store modification, DB connection or secret read occurred.

Recommended fix for review: pin/provenance-check the public regional bundle, split
its three roots into one public .crt per certificate under the Identity source,
and add a narrowly scoped COPY/update-ca-certificates step before USER in the shared
Dockerfile. Preserve verify-full/system roots and hostname verification; no insecure
fallback. Check expiry, intended platform and installed root membership, then
repeat real TLS success/hostname-failure checks in the final approved image.
Shared Dockerfile work needs coordinated writer reservation/affected-owner review
under CONTRIBUTING.md; it is deliberately left unchanged while Suraj integrates
upstream. Live runtime prerequisites and final image/deployment approval remain
pending. This is the next approval/coordination boundary, not local readiness.

Local checkpoint review — 2026-10-25 11:48:05 UTC: full make check passed all11
ordered gates (1074Python/1existing DB-only skip,63data,118web; Black158files),
including actual PostgreSQL18.6 combined clean/repeat/upgrade/atomicity/rollback/
reapply,35wrapper safety cases, contracts/types/boundaries/build and Gitleaks.
Log `/tmp/clip-id-ready-autonomous-check.log`; both new scripts pass strict mypy,
current offline package check and changed-document links/whitespace checks pass.
No owned DB fixture/image-inspection container is intentionally retained.

Applicable checklist review: isolated branch/source preserved; local-only tests
and real/synthetic evidence distinguished; commands/function behavior documented;
no secret values exposed or default production bypass introduced. Original
worktree remains clean at85c4606. Task-wide ID-READY closeout remains incomplete:
accepted-main integration/current hosted CI, independent/affected-owner approval,
image trust fix, real schema/login/IAM/proxy/provider/browser/device/retention
acceptance and exact authorized merge are still required. Stop at the shared-image
coordination/live approval boundary; no background/cloud work is scheduled.


## Accepted main integration — 2026-10-25 17:07:10 UTC

Aditya authorized merging accepted main after Suraj's PR integration. Target branch
is `task/id-ready-local-hardening` in `/tmp/clip-id-ready-local-hardening`, retaining
the two autonomous local commits. Accepted base is
`6c860603bdd81a98485e721d789b557c5d433948` (PR11Search and PR12Listings). Original
worktree remains on task/id-01-identity at85c4606; no push/cloud/deploy/send action.

Resolved14conflicts preserving both domains' settings, narrow scanner exceptions,
documentation and evidence. Regenerated-contract check confirms all8artifacts are
current. All14accepted upstream migration files and raw evidence logs remain
byte-identical. Exact-UTC histories were interleaved without deleting entry bodies;
untimed entries retain their relative barriers and no time was invented.

Changed integration code:

- `apps/api/app/application.py` now composes accepted Search/Wanted/Saved stores,
  routes, public Listings resolver and optional Hybrid lifecycle alongside the
  existing explicit Identity bindings. Shared application_lifespan retains the
  accepted startup/cancellation cleanup, while configured factories keep independent
  settings and Identity's production/demo safeguards.
- `apps/api/app/main.py` delegates to that lifecycle and retains accepted
  main.settings/main.lifespan/pool/storage probe hooks; no duplicated private-domain
  implementation. `scripts/check_boundaries.py` allows only these exact composition
  imports, including the narrow compatibility facade.
- `apps/api/app/domains/identity/migration_runner.py` and its tests now require
  17files/head20261025013000,37tables/33functions/43triggers. Reviewed-image and
  target/partial-schema/prefix/TLS protections remain; live flags stay closed.
- `scripts/check_database.py` and `database/tests/native-checks.sh` retain both sets
  of seven smokes, combined inventory and full rollback/reapply. The disposable
  checker removes later Search forwards before historical Identity upgrade tests;
  only matching Identity checks run at those historical heads. Current Search SQL
  requires category_code and runs at the full head. A transient overbroad count
  edit affected a synthetic digest expectation; restored its original33value and
  reran the full real lifecycle. Published SQL was never edited.
- Identity's application composition tests now verify real regular/temporary
  cookies reach actual Wanted and Saved empty-page reads, without consumer doubles.
  The offline review-checker's fixture now builds all14upstream migrations rather
  than assuming the first11files are the full accepted base.

Validation passed:70initial focused tests,10final composition tests; strict mypy
for5reconciled modules; full make check all11gates, Black254files,
1791Python/21skipped,94data,223web/2skipped. Separate registered disposable store
workflow passed21tests/3optional model-dependent skips, and actual PostgreSQL18.6
17file clean/head/repeat, seven smokes, Identity upgrade/atomicity/down/reapply and
retirement rollback guards passed. Native harness syntax passed; no new macOS or
live/cloud check is claimed. Logs: /tmp/clip-id-ready-main-focused.log,
/tmp/clip-id-ready-main-types.log, /tmp/clip-id-ready-main-check.log,
/tmp/clip-id-ready-main-database.log, /tmp/clip-id-ready-main-stores.log.

Source/docs whitespace passes excluding accepted raw .log transcripts, which
retain their original trailing whitespace byte-for-byte. Pinned Gitleaks passed.
Manifest/candidate now record17files and the accepted base; exact source revision
will be refreshed from the merge commit, without approving image/live execution.

Newly visible consumer follow-up: accepted Search wantedApi.ts, like Listings'
request helper, sends cookies/JSON but no X-CLIP-Request/CSRF headers. Protected
browser writes need coordinated public/shared request integration before real
Identity enablement; no private consumer source was changed to hide the gap.
The existing image RDS-root trust gap also remains. Neither prevents this local
main integration; both remain real runtime/browser readiness gates. Current peer/
CI/real schema/role/URL/IAM/proxy/provider/device/retention checks remain pending;
no ID-READY/Step14 acceptance or authorization for a remote merge is inferred.


Review source finalized 2026-10-25 17:09:30 UTC: local merge commit `42e9cd9320cff5a5e15f3ba8eb5e95a31164082a`
contains accepted main `6c860603bdd81a98485e721d789b557c5d433948` and the two autonomous Identity commits.
Manifest/candidate source, runner source,17file head and manifest SHA refreshed to
that exact implementation; all image/independent/affected-owner/live DDL approvals
remain pending and live flags remain closed. Cross-owner handoff now compares
that merged implementation with accepted main and refreshes its source inventory,
current test counts and newly visible Search browser-CSRF follow-up. This metadata
refresh changes no code and is not reviewer acceptance. Full checks cited above
remain valid for the identical implementation. No push or PR/cloud action.


## RDS image trust correction — 2026-10-25 18:00:39 UTC

Aditya authorized this Step12 checkpoint; A reserved the shared Dockerfile scope
and found no open PR/current shared-writer conflict (remote main6c86060 unchanged).
No task-definition gap: this implements the existing verify-full/system runtime
requirement, not a provider/URI/security-policy redesign. Peer/affected-owner and
human result verification remain pending. [Shared decision](../../decisions/identity-rds-system-trust.md),
[public roots/provenance](../../../apps/api/app/domains/identity/certificates/README.md),
and [sanitized image/check evidence](id-01-step-12/image-trust-local.json).

Changed code/configuration:

- `apps/api/Dockerfile` installs three pinned official regional roots before USER,
  preserving distribution CAs. It sets SSL_CERT_FILE to the installed standard
  `/etc/ssl/certs/ca-certificates.crt`; verify-full/system and application startup
  controls remain. No CA download occurs during build.
- Identity's certificates directory contains three public self-signed CA .crt
  files and a manifest with official HTTPS source, complete-bundle/file/DER SHA,
  subjects and validity. No intermediate, server, synthetic certificate or private
  key is included. Certificate README describes update/review and inheritance.
- `test_image_trust.py` verifies cryptographic pins/purpose/expiry and the actual
  locally selected image: exact current fingerprints, all distribution roots,
  non-root metadata, intended CA path, real libpq TLS/hostname behavior and default
  health/protected API. It requires an opt-in image; ordinary aggregate runs only
  public-data integrity and explicitly skips the three image-dependent tests.
- `migration_fixtures.py` exposes its existing owned container handle so image
  checks share only that disposable TLS network namespace. Existing17runner tests
  still pass; no fixture/cloud target discovery or application code change.

The initial native image added roots but bundled libpq still looked for
`/host/tmp/libpq.build/cert.pem`, while Python used Debian's store. An earlier
process-only test trust override had hidden that difference. A stronger test using
the actual default file failed, exposing it. The final image explicitly chooses
the standard OS CA file, as supported by PostgreSQL's system-root semantics.
Final TLS proof uses the shipped setting without changing it in the test. Only a
temporary read-only container bind mount augments that same public CA file with
the synthetic server's root; no image/system file is mutated or synthetic root
baked in. Valid SQL verifies, unknown CA and wrong hostname both fail. No real
RDS connection or inference about its current leaf/CA configuration was made.

Final native ARM64 image73e716fe663f:151trusted roots, including all148distribution
roots and3regional roots; UID10001. Allowlisted178-file source-only build context
excluded credentials/caches/tests. Optional Hybrid Dockerfile is unchanged and
inherits the correction only from a rebuilt corrected parent. AMD64/Hybrid actual
build/verification remains pending on suitable approved hardware; no emulation,
VM, registry publication, AWS resource API, secret retrieval, provider send or
cloud deployment was performed. Public CA HTTPS download alone was used.

Checks passed:4explicit image tests;17existing migration-runner regressions;
full make check all11gates, Black255files,1792Python/24skipped,94data,
223web/2skipped, real PostgreSQL18.6 combined17file lifecycle and Gitleaks. Three of
the aggregate Python skips are opt-in image checks that passed separately. Native
image build and certificate/TLS behavior are real; live runtime/provider/browser
and final ID-READY acceptance are still pending. Current migration review package
remains locally consistent/ready_for_live:false. Source/docs links/whitespace pass.
Owned test containers/build contexts were cleaned; the local image remains for
review. See the artifact for exact source hashes, image ID, logs and pending gates.


## Shared browser transport result — 2026-10-25 19:00:23 UTC

Aditya verified the previous local image checkpoint and authorized this described
CSRF integration. A reserved the bounded helper/adapter/demo scope; remote main
remained6c86060 with no open PRs at inspection. No new task-definition gap: the
reviewed cookie/CSRF contract covers the required operations. The local audit found
normal Identity unprefixed requests missed Vite's /api proxy, and isolated demos
needed a reviewed CSRF response double. Both are handled without client fallback
or private-feature imports. Suraj/Mohit retain ownership and review of their narrow
adapter/test-fixture changes. [Decision](../../decisions/browser-session-transport.md),
[exact source/check evidence](id-01-step-12/browser-transport-local.json).

Changed implementation and its relationships:

- `shared/http/sessionFetch.ts` supplies the technical HTTP layer: same-origin
  credentials/mode, no-store, redirect refusal, safe rooted paths, ten-second
  linked cancellation through complete JSON receipt, marker and fresh protected
  CSRF preflight. Failed/malformed token responses prevent the write; no cache,
  persistent storage or automatic replay. Only seven reviewed public auth writes
  omit CSRF; a read-only parity audit matches the actual middleware's list.
- Identity `api.ts` delegates to it, retains its validators/safe uncertainty state,
  uses /api normally and unprefixed explicit Identity preview. The shared deadline
  replaces its duplicate timer. Microsoft callback page/origin/build guards stay.
- Listings `listingsApi.ts` and Search `wantedApi.ts` change only transport calls
  and safe error mapping. Listings preserves all RequestInit header forms. Business
  schemas, class/resource checks, component/public exports, operation keys and
  existing owner-controlled idempotent upload retry behavior stay. S3 bytes still
  use the separate XHR and only server-required presigned headers.
- Shared `application.py` exposes a CSRF response double only in the already-guarded
  dedicated synthetic Listings profile. It precedes hosted SPA fallback. Normal
  and production profiles gain no synthetic endpoint; real Identity cannot coexist
  with the demo caller. Existing local Listings/Search browser harnesses install
  the test-owned `browser_csrf_fixtures.py` helper under their existing transport
  guards. Nothing imports that helper into normal/production startup.
- New shared/helper tests and narrow existing fixture updates separate valid CSRF
  preflight responses from unchanged feature payload/validator assertions. Native
  Headers/linked signals replace old representation-identity expectations, while
  explicit cancellation/header tests verify the behavior. Existing Identity UI
  fixture routes now match the actual normal /api prefix and valid token lengths.

Actual `test_browser_transport.py` starts one owned loopback HTTP server over real
17-migration PostgreSQL and runs the actual TS adapters via session-fetch-http.test.ts.
Real Identity sessions/CSRF and domain services authorize regular Listings
availability, regular Wanted create/edit and temporary Wanted create; missing
CSRF, cross-session token race and temporary seller requests deny, and logout
prevents the next business write at preflight. SQL confirms exactly two requests
and one availability revision change. Signing/mail/image metadata and browser
Origin/cookie/proxy handling are synthetic; there is no public test-auth/OTP-inbox
route. Initial seed/assertion errors were corrected to canonical atomic publication,
24hour upload lifetime and public ListingDetail (revision checked in SQL instead).
No published migration, business constraint or response schema was relaxed.

Checks passed:32shared transport cases;22demo/existing composition cases;
actual TS/HTTP/SQL test; strict mypy2modules; full make check all11gates,
Black258files,1800Python/24skipped,94data,257web/3skipped, current contracts,
boundaries, build, real PostgreSQL lifecycle and Gitleaks. One normal web skip is
this privately configured HTTP test, which runs and passes inside the Python gate;
the other two are existing native Search opt-ins. Physical browser/device, live
provider/proxy/deployment and full Step14 acceptance are not claimed. Owned server/
socket/containers are cleaned and transient synthetic cookies are redacted in logs.

Applicable checklist review: shared paths reserved, reviewed contract maintained,
no cross-feature private import, source/data privacy and no fake default activation,
source/command/evidence docs updated, all applicable local checks performed.
Current app images must be rebuilt from the latest reviewed source before live
use; the earlier ARM64 CA image is evidence for its pinned source, not this new UI.
AMD64/Hybrid, real schema/login/URL/IAM/proxy/provider/browser/retention and human/
peer/CI/authorized merge gates still prevent ID-READY completion. No cloud resource
API, secret lookup, send, teammate message, push or deployment. Result awaits human
verification; no further numbered checkpoint is started.

Owner-review source refreshed 2026-10-25 19:07:04 UTC to implementation
`7bc5b6083caac673ce264b6daa6675d5ddf3a20f` against accepted main6c86060. The single cross-owner handoff
now includes the current image fix and browser adapters, removes superseded local
header-gap claims, and regenerates its complete shared/other-owner path inventory.
No code changed during this metadata refresh; all recorded local checks remain
valid, owner/human verification and live gates remain pending.

## Morning user acceptance run — preparation only

This checklist prepares the user-controlled browser checks after the separately
approved schema, runtime, HTTPS/proxy, provider, and deployment work is complete.
It is not approval to query AWS, read secrets, migrate, deploy, or send mail; it is
not evidence that ID-READY has passed. Use the exact deployed revision and the
approved application origin (expected `https://clip-iisc.site`). Stop if the sign-in
page is not served by that revision or the HTTPS/API origin is unexpected.

1. Open `/sign-in` in a clean browser session. Confirm the Microsoft button is
   enabled only on the intended HTTPS app origin. Sign in with the user's IISc
   account through Microsoft's normal consent flow. Expect return to the app with
   a regular account session. Refresh once and confirm the session remains valid;
   then sign out and confirm a fresh visit no longer shows the signed-in state.
   Do not copy authorization codes, ID/access tokens, cookies, or browser storage.
2. Start temporary registration with the user's approved Gmail-controlled address.
   Expect the generic acknowledgement, then a six-digit message from
   `verify@clip-iisc.site`; check inbox and spam. Use the newest valid code and a
   password of at least eight characters. Expect an authenticated temporary
   account whose UI states the 14-day lifetime. Refresh once and confirm it remains
   signed in. Do not request duplicate codes unless the UI cooldown permits it.
3. Sign out, use “Forgot password” for that same temporary account, and verify a
   reset message arrives. Use the latest valid code and a new password, then sign
   in with the new password. Expect the temporary account class and original
   expiry to remain unchanged. Do not deliberately submit incorrect codes or
   passwords during this smoke check.
4. Record only the deployed revision, UTC time, browser/device, pass/fail per flow,
   observed account class and temporary expiry, and whether each expected message
   reached inbox or spam. Never record email addresses, OTPs, passwords, cookies,
   tokens, contact values, or provider credentials in repository evidence. Report
   failures with a sanitized screenshot or exact UI message and stop repeated
   sends after an unexpected result.

The run depends on the morning gates: current reviewed AMD64 image; exact shared
schema and separate Identity login/URL; scoped task-role permissions and persistent
keys; current sender/provider configuration with the approved controlled-recipient
allowlist; HTTPS/proxy/API routing; and the intended frontend flag/revision. The
user performs the Microsoft account and inbox actions. Mobile-browser usability (not phone-number/SMS verification),
affected-owner review, hosted CI, and the full Step14 consumer matrix remain
separate checks; Step14 is outside current ID-READY scope.

### Additional runtime activation and ingress gate — offline source audit

The image is not the only remaining implementation prerequisite. Current source
and Terraform show:

- `apps/api/app/main.py` keeps default startup Identity-unbound. The local
  implementation now supports a separate explicit `CLIP_IDENTITY_RUNTIME_ENABLED`
  test-only path, which loads real dependencies and installs the existing handlers
  at startup. It requires `CLIP_ENVIRONMENT=test`, Microsoft plus dual email,
  `CLIP_DEBUG=false`, the separate Listings DB URL, and exact HTTPS origins.
  Production remains rejected and the flag defaults false.
- `identity_runtime.py`/`prepare_local_identity` is an explicit local/test
  operator command. It reads fixed Identity SSM references only when invoked and
  refuses `serve_web_app`; it is not a hosted ASGI startup path.
- `create_app` can place Identity routes under `/api` when the explicitly enabled
  test app serves its bundled UI. Otherwise Identity retains its unprefixed API
  paths and the external same-origin `/api` proxy must strip the prefix.
- The shared ECS task currently sets only `CLIP_ENVIRONMENT=production` and
  `CLIP_DEBUG=false`. It has no Identity selector/runtime flag, database URL
  injection, or Identity parameter access. The Identity database URL parameter
  is not provisioned; the separate Listings URL is also not in this task definition.
- The shared API task uses private bridge networking and the Terraform service
  module declares no public listener or inbound rule. No source record currently
  binds the public app origin to this service or defines a trusted HTTPS proxy
  hop. Identity's browser middleware requires HTTPS and rejects untrusted Origins;
  enabling arbitrary forwarded-header trust would be unsafe.

Therefore do not treat the production frontend build or image as enough to run
the morning account checks. Before enabling the new code path, inspect the current
domain/DNS/hosting route and shared ingress, select the exact same-origin HTTPS
path, and review how the application will trust that proxy and receive its
separate Listings/Identity DB and SSM configuration. The likely low-complexity
shape is the existing API image serving the UI and `/api` on one HTTPS origin, but
that remains an inference until the actual listener/host is identified. No AWS
state was queried for this audit.


## Post-merge shared runtime plan

Prepared2026-10-26 06:32:23 UTC by Aditya(A)'s agent, from merged main
`3d6c2709d93f42bda0b4a6645c633780387c99b8` (PR #14). Aditya confirms Suraj's
review/merge; the PR is closed. This supersedes open-review claims for that
implementation, not the historical evidence or future runtime-change reviews.
Current17migration hashes match the manifest, head20261025013000; expected shared
inventory37tables/33functions/43triggers remains subject to exact preflight.

Authentication is Microsoft sign-in for regular users or **email OTP** for temporary
activation/reset. There is no phone-number/SMS authentication requirement.
Mobile-browser checks concern responsive website behavior only.

### Ordered checkpoints

| Checkpoint | Output and checks | Gate |
|---|---|---|
| 1. Source/environment discovery | Pin merged source; verify manifest; inspect current target identity, shared workload/writer state, RDS namespace/tracker metadata, IAM/SSM reference metadata and domain/DNS/HTTPS route. Identify the actual same-origin ingress and proxy hop. | Local source portion completed. Live inspection, resource startup and secret reads are not performed/authorized by this document. Present an exact bounded inspection window first; avoid decrypted secrets where metadata suffices. |
| 2. Shared schema | Final reviewed image/manifest; fresh four-domain preflight; strict17file apply and read-only version/head/inventory postchecks. | Exact account/target/source/image/DDL approval and exclusive operator window. Stop on manual/partial/unknown schema, concurrent writer, unsafe logging or TLS failure. |
| 3. Application DB credentials | Separate Identity login/grants and private `/clip/test/identity/database-url`; establish the separate Listings URL with its owner. Verify effective privileges and denied cross-domain/DDL access. | Separate role/password/secret-publication approval after schema checks. No master credential in app; no assumed Listings login name/secret path or credential rotation. Preserve stable auth keys. |
| 4. Runtime/IAM/provider configuration | Narrow task access to approved Identity SSM references, separate Listings URL injection, Microsoft/dual selectors and real test startup; privately rotated Resend key. Review verify@ SES FromAddress transition if SES enabled. | Review exact IAM/resources/config diff before apply. Resend primary permits progress without SES production access; sandbox recipients remain constrained. No wildcard secret access. |
| 5. Image and HTTPS ingress | Current immutable AMD64 image with verified regional RDS roots and bundled UI; same-origin HTTPS app/API and exact trusted proxy handling. Test health, certificate/hostname validation, cookie/Origin/CSRF and sign-in callback routing. | Actual route discovery must precede selecting listener/certificate/DNS resources. Separate build/publish/deployment/ingress approval, scoped writer coordination and cost plan. Never reuse the synthetic Listings HTTP demo as real-auth ingress. |
| 6. Real runtime acceptance | Approved Microsoft user, temporary email registration/sign-in/reset and receipt, logout/revocation/expiry, profile/contact privacy and available consumer smoke checks. Verify retention operation and safe cleanup; record sanitized desktop/mobile-browser results. | Separate exact provider-send/test-identity/data/cleanup scope; human handles Microsoft/inbox interaction. Local provider successes are retained but not counted as hosted proof. No full Step14 matrix. |
| 7. ID-READY closeout | Task-wide requirement/checklist review, source-bound evidence, current checks/review for new changes, human milestone acceptance and work-log milestone update. | Keep milestone unaccepted until required real integration succeeds. ID-01 itself stays in progress for later steps. |

### Scope for the first live request — draft, not authorization

Use existing account335523638354, profileadityalaxmi1, ap-south-1, original
`clip-shared-test-postgres`/clip_test and shared test ECS resources. Verify resource
IDs/class/AZ/endpoint against recorded inventory; no implicit class/AZ/network
substitution. Recheck Suraj's active workloads before starting or stopping anything.
The prior migration candidate's one-task/host,60minute/$1 operating ceiling and
20minute startup limit are proposed bounds only, not current prices or a budget
approval. No automatic capacity-start retry. A new exact UTC window/operator and
current cost assumptions must be established before execution.

Separate read-only AWS/DNS discovery from private SQL access: obtain metadata first;
if stopped RDS needs starting for catalogs, request its bounded start/tunnel/secret
read/cleanup scope before doing so. Never query live credentials/data merely to
fill this document. Record only safe target/version/permission/schema metadata.
The existing apply candidate is still non-executable; refresh its source/manifest
review provenance after this merge before requesting actual DDL approval.

For apply, preserve committed migration prefixes on failure; no down/drop/reset,
automatic adoption/replay, global grants repair or restore. Role setup must retain
its atomic transaction and refuse existing/ambiguous role state; ambiguous commit
requires metadata inspection before retry. Cleanup closes only owned task/tunnel/
host resources; stop RDS/zero shared capacity only while exclusive and safe for
other owners. Preserve shared data, secrets, network and other domains' resources.

Runtime configuration must use the existing explicitly guarded **test** startup:
`CLIP_ENVIRONMENT=test`, debug/development auth off, Microsoft and dual email,
`CLIP_IDENTITY_RUNTIME_ENABLED=true`, exact approved HTTPS origins and separate
Listings DB URL. Production remains rejected; do not relax that guard to fit the
old production-only ECS task definition. IAM/secret injection, HTTPS ingress and
actual startup must be reviewed together before enabling this path.

Acceptance evidence contains revision/image digest, UTC time, config/reference
versions, safe check outcomes and cleanup status. Never retain OTPs, passwords,
tokens, cookies, email/contact values or decrypted provider/key/URL contents.
Docs-only plan checks: manifest equality, relative links and whitespace. No new
full application test run or live state assertion is implied.


### Marketplace connection audit — 2026-10-26 06:38:54 UTC

Aditya authorized starting the integrated connection preparation. Read the existing
[Listings/Search deployment handoff](../../architecture/listings-search-deployment.md),
application lifespan, Settings, S3 adapter, shared ECS task and Listings Terraform.
The implementation is already connected internally; remaining release work is
configuration, permissions, artifacts, initialization and actual integration checks.
This checkpoint changes documentation only and does not authorize another owner's
Terraform edits. Use the original public adapters; do not create replacement services.

| Feature | Existing connection / exact release inputs | Required deployed check |
|---|---|---|
| Identity | Guarded hosted test startup, exact HTTPS origins, Microsoft/dual mail, fixed three SSM references and separate Identity role/URL. | Regular IISc and temporary email activation/reset/session flows; no SMS. |
| Listings / Keyword / Wanted / Saved | `application_lifespan` creates real stores and public Listings access from the same `CLIP_DATABASE_URL` pool. Search needs no separate database or HTTP bridge. | Real regular create/edit/read/availability and temporary seller denial; Keyword filters/pagination, Wanted CRUD/draft matching, Saved CRUD/isolation/unavailable-target handling. |
| Images | Existing `S3ListingsImageStorage` selected by `CLIP_STORAGE_PROVIDER=s3`, `CLIP_IMAGE_BUCKET`, `CLIP_IMAGE_REGION`, `CLIP_IMAGE_KEY_PREFIX`. Task role needs reviewed object operations; bucket CORS needs actual HTTPS origin and signed request headers. | Authorized initiate/PUT/confirm/read/display with approved synthetic files, private objects, type/size/owner/expiry failures; image-backed detail/discovery/Saved. |
| Hybrid | Existing `Dockerfile.hybrid` plus pinned AMD64 Python/wheels/model contexts, Hybrid read and worker flags and absolute interpreter/model paths. | Real inference, new/edit invalidation and worker updates, current-source coverage, useful safe unavailable behavior; no performance/NFR claim. |
| Hybrid initialization | Existing packaged `search_pipeline.py`: separately approved prepare, bounded queue, worker processing/status, activation after complete coverage for pinned pipeline ID. | Exact host/database/role/pipeline checks and complete current vector coverage before serving; startup must not silently activate/backfill. |
| UI / HTTPS | Bundled UI via `CLIP_SERVE_WEB_APP=true`, real auth and same-origin `/api`; public TLS/listener/domain mapping still needs discovery. | Static routes/callback/API mapping, cookies and CSRF, account-scoped state reset, image/search flows. |

Listings Terraform records bucket `clip-test-listings-images-ap-south-1-li02`,
run-scoped prefix `listings/test/<run-id>` and isolated task roles/permissions.
Those are source records, not current live-state proof or approved integrated
prefix/IAM configuration. Review with Suraj before selecting a persistent shared
prefix, CORS origin or runtime role. Do not invoke the LI-02 demo start/stop route,
reuse its synthetic caller or disposable DB, or delete its owner's objects.
The `/clip/test/listings-database-url` name appears in that isolated root; do not
assume its current value/role is appropriate for the shared database.

Hybrid packaging/bootstrap is part of the full non-Conversations deployment scope;
it is not silently omitted to claim all Search modes work. Confirm artifact
availability and source hashes locally, coordinate Search's role/pipeline setup
with Mohit, then propose exact build/resources/bootstrap mutations. Start with
one API process: up to10command+2Hybrid-read+1worker DB connections. The old512MiB
foundation task is not evidence of sufficient model memory; sizing remains an
explicit release decision supported by measurement, not a guessed unchanged value.
The Identity-only least-privilege role must never be broadened for Search jobs.

Conversations, offers/selection, wanted-response thread creation, deliberate
conversation contact sharing and notifications remain visibly unavailable through
their public boundaries. Do not count their failure as working marketplace flows.
These connections do not accept full Step14 or other owners' final milestones.

#### Next proposed action: metadata-only discovery

Request approval for one read-only inspection, maximum15minutes, using existing
profileadityalaxmi1/account335523638354/ap-south-1. Inspect STS caller identity;
RDS instance status/endpoint/security metadata; shared ECS service/task-definition/
capacity and EC2/ASG metadata; applicable IAM policy documents; SSM names/types/
versions only; known Listings bucket CORS/public-access/encryption/policy metadata;
ELB/listener/target-group, certificate and hosted-zone record metadata where
accessible; and public DNS/TLS for clip-iisc.site. Restrict queries to CLIP resources
and do not enumerate application rows, object contents or decrypted parameters.
No resource start/stop, SQL connection, secret decryption, Terraform plan/apply,
provider request/email, artifact push, DNS/IAM mutation or deployment. No running
compute is created. Stop on wrong account or unavailable authorization; report
unknowns rather than infer absence. This request does not approve later changes.

After approval, record sanitized findings and prepare the exact change set for
review. A live DB catalog probe, AMD64 build, pipeline initialization and any paid
runtime window each retain their separate scoped execution approval.


### Approved metadata discovery result — 2026-10-26 06:44:03 UTC

Aditya explicitly approved the15minute metadata-only scope. Completed in under
three minutes against confirmed account335523638354/profileadityalaxmi1/Mumbai;
[source-bound sanitized evidence](id-01-step-12/cloud-metadata-20261026T064141Z.json).
The sandbox's first network check failed; the network-enabled account check and
resource queries succeeded. No resource was started, stopped or modified.

| Connection | Observed live result | Next concrete work |
|---|---|---|
| Shared RDS | Original resource stopped,18.6/t4g.micro/ap-south-1a/private, expected resource ID and CA. | Separate exclusive start/tunnel/catalog-check and migration approval; current schema/roles unknown. |
| Shared app | Cluster/ASG hosts0, service desired/running/pending0. Task:1 still original foundation image,256CPU/512MiB, no secrets, only environment/debug names and no LB. | Reviewed immutable integrated image and complete runtime task/configuration; measured Hybrid sizing rather than assuming512MiB. |
| Credentials | Identity auth-key/email route and Listings URL SecureStrings listed, allv1; Identity DB URL absent from prefix metadata listing. | Provision Identity login/URL after schema; privately validate Listings URL target/role under separate read approval. Name presence does not establish shared DB compatibility. |
| Shared task role | One inline SES policy, no attached policies; condition still no-reply@. No S3/Identity SSM grant in these policies. | Reviewed exact runtime IAM/secret injection and verify@ SES sender transition. No broad secret or cross-domain data grants. |
| Images | Existing Listings bucket private-blocked/AES256; CORS only active demo's HTTP origin. | Coordinate shared prefix/object rights and HTTPS-origin CORS with Suraj; preserve current demo access. |
| Domain/HTTPS | Public apex A/AAAA queries succeeded with no address answers; nameservers launch1/2.spaceship.net. Local apex/www resolution failed, so TLS unavailable. No matching Route53 zone and no ACM certificate listed in this account/region. | Prepare reviewed certificate/validation/HTTPS-listener/domain-record route using actual DNS operator. Do not assume Route53 manages the domain or request registrar credentials in chat. |
| Other-owner runtime | Separate Listings cluster has1host/1running task; clip-li02-demo HTTP80 listener has healthy instance target at18001. | Preserve all current resources/work; coordinate window and any image bucket or listener changes with Suraj. Old stopped-demo evidence is superseded for this snapshot. |

Next checkpoint is local preparation of the runtime/IAM/HTTPS and storage changes,
with owner coordination for shared paths, followed by exact review/approvals.
A stopped original shared cluster does not mean all CLIP workloads are idle.
Do not reuse cleanup logic that would stop/delete the active Listings demo.
No secret contents, objects, business rows or provider deliveries were inspected.
All17schema versions, role grants, model readiness and actual runtime acceptance
remain unverified live; this metadata check does not accept ID-READY.


### Runtime policy and HTTPS preparation — 2026-10-26 06:50:29 UTC

Aditya verified discovery and requested continued local preparation, including
HTTPS if straightforward. Current writer Aditya(A) reserves new shared
`https-certificate.tf` and its README section for this increment; existing shared
service/network/IAM code and Listings/Search-owned roots remain unchanged.
Shared state owns this application-wide certificate under the canonical Terraform
ownership rules; no domain state adopts the shared origin.

Prepared concrete review artifacts:

- [Shared HTTPS certificate source](../../../infra/terraform/shared/test/https-certificate.tf):
  opt-in, default disabled, apex clip-iisc.site only, RSA2048/DNS validation,
  non-exportable ACM default, explicit review date and prevent-destroy protection.
  Outputs expose only ARN and public validation CNAMEs. No validation waiter,
  Route53 resources, listener, compute or DNS mutation. The shared README explains
  full-plan scope and retention/cleanup. This resource is not yet provisioned.
- [Runtime configuration proposal](../../../infra/terraform/shared/test/service.tf):
  exact test-mode selectors/origin; app-role GetParameter for only the three fixed
  Identity references; execution-role GetParameters for the proposed Listings URL
  injection. Separates task/execution responsibilities and excludes master/probe
  access. Explicit unresolved image/S3/prefix/recipient/Hybrid/proxy items make it
  non-deployable; it is not a guessed ECS task definition or approved policy apply.

HTTPS route: validated ACM certificate in Mumbai, reviewed shared ALB HTTPS443
listener and exact integrated target group, HTTP redirect as appropriate, apex
ALIAS to the selected ALB at Spaceship. Preserve existing MX/SPF/DKIM/DMARC and
Suraj's demo origin/listener/CORS. Spaceship documents ALIAS for apex hostnames;
do not pin transient ALB IPs or put an ordinary CNAME at the apex. No DNS migration
or registrar credentials are required. Exact ALB choice, public subnet topology,
SG-only target access, trusted proxy source and ongoing cost remain review items;
do not mutate the active LI-02 ALB without its owner's review.

The certificate can be requested/validated before the app is ready. An issued
certificate alone does not activate HTTPS or authenticate the app. ACM's standard
non-exportable certificate has no certificate charge; ALB/runtime charges are
separate and need the exact reviewed deployment cost/cap plan. References:
[AWS HTTPS listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listener.html),
[DNS validation/renewal](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html),
[ACM pricing](https://aws.amazon.com/certificate-manager/pricing/),
[Spaceship apex ALIAS](https://www.spaceship.com/en-GB/knowledgebase/spaceship-mcp/).

Next proposed gate: approve non-applying full Terraform planning in existing
shared/test state/account335523638354/ap-south-1, with certificate flag enabled,
proposed review date2026-10-27, current service phase/stopped API and all original
private inputs preserved through their existing approved secure path. No new secret
read is authorized. Expected scope exactly1ACM addition/no other changes. Desired
verify@ source differs from live no-reply, so a full plan may expose that or other
drift: stop, summarize safely and seek review rather than hide it with targeting.
Save plan privately outside Git; inspect and report checksum/safe scope only.
Certificate apply still needs approval for that exact plan; after apply, provide
public CNAME name/value for the human DNS operator, then verify issuance separately.
No DNS/listener/service operation is bundled into certificate-plan approval.

Checks: PATH Terraform1.16.5 was correctly rejected; reran backend-free checks
using existing pinned1.15.9. All four roots passed validation; formatting passed.
No backend initialization, AWS plan/apply, secret read or app/provider action.
Other code tests are not needed for this declarative preparation. JSON/link/diff
and secret scanning complete the local review; ID-READY remains incomplete.


### Certificate planning preflight — 2026-10-26 06:57:25 UTC

Aditya approved non-applying certificate planning and explicitly retained all other
marketplace deployments in scope. Confirmed account335523638354; initialized the
existing shared/test backend with pinned Terraform1.15.9/default workspace. Private
preparation directory `/tmp/clip-id01-https-plan-us1a7pkp` is0700; inputs and init
log are0600 and outside Git. Preserved original service/stopped-API/image/version
inputs from prior private preparation; enabled only the certificate proposal with
review date2026-10-27. Read existing approved shared state in process memory to
preserve the exact sandbox recipient ARN privately; never printed recipient/state.
Operator session credentials stayed in process memory. No app-secret read occurred.

The retained input files contain no ephemeral master/probe passwords, and neither
is present in the process environment. The shared root explicitly requires these
existing write-only inputs for planning; their version counters remain1. No dummy
value, omission, targeted plan, source rewrite or password rotation was used to
bypass this requirement. **Backend initialization succeeded; saved plan has not
been created.** Earlier approval explicitly excluded new secret reads, so pause
before two SSM decryptions, not after attempting an invalid substitute plan.

Exact additional proposed scope: once each, decrypt only
`/clip/test/database-master-password` and `/clip/test/database-probe-password`
under the already selected operator/account/region; capture into process memory
and Terraform ephemeral environment inputs, never files/arguments/logs/evidence.
Continue the already approved full non-applying certificate plan with private
output/save and sanitized checksum/resource-action review. No SQL/RDS start,
secret write/rotation, task start, provider send or apply. If source/live sender or
other drift adds changes, report and stop before apply; plan approval does not
approve those mutations. All apply operations remain separately gated.

Full deployment scope retained in order: reviewed schema and separate role/URLs;
Identity/provider IAM/config; S3 shared prefix/role/CORS with Suraj; current AMD64
image and Keyword/Wanted/Saved; Hybrid model/worker/bootstrap/sizing with Mohit;
HTTPS listener/DNS/trusted proxy and real integrated acceptance. Certificate
validation can overlap preparation of these connections, but does not replace any.
No one else's active runtime was changed or contacted.


### Saved HTTPS certificate plan — 2026-10-26 06:59:49 UTC

Aditya explicitly approved two one-time master/probe parameter decryptions for
non-applying planning. Verified both SecureString references at version1; values
went only to process memory/ephemeral Terraform environment, never arguments or
files/logs. Correct account confirmed, original version counters unchanged.
Full Terraform1.15.9 plan completed successfully (detailed exit2 = changes).
[Sanitized exact review](id-01-step-12/https-certificate-plan-review.json).

Private saved plan `/tmp/clip-id01-https-plan-us1a7pkp/https-certificate.tfplan`,0600,
SHA256 `9f7d85f76e72a4d955d2224e11086a9909d79c134f37827d7d4159f71c04c741`.
It contains **one create and one in-place update, zero replacements/deletions**:

- Create `aws_acm_certificate.identity_https[0]` for clip-iisc.site, DNS validation,
  RSA2048, review date2026-10-27. No listener, DNS or compute is created by this.
- Update `aws_iam_role_policy.api_identity_email[0]` sender condition from
  no-reply@ to verify@. Parsed policies are otherwise identical, preserving exact
  resources/recipient/action. This is a previously desired but unapplied change;
  it exceeds certificate-only scope and therefore needs explicit approval too.

Refresh reports only computed RDS latest_restorable_time and role inline-policy
metadata drift; neither means an additional RDS/role resource action. No changes
to database credentials, tasks/services, ASG/network/storage or active Listings demo.
No apply or email send performed. Source/hash/plan actions and0600checks passed;
existing Terraform validation remains applicable, no source changed this increment.

Exact next proposal: up to15minutes, apply only this checksum in existing
account335523638354/Mumbai/shared/test state, approve the two actions above,
retain certificate for the deployment, verify resource/sender metadata and obtain
public validation CNAME for human Spaceship entry. Standard non-exportable ACM
certificate has no certificate fee; this adds no running compute/listener. Preserve
all other resources. Abort on checksum/source/state mismatch or unexpected actions;
no automatic credential read retry, IAM reversal or cleanup. Apply requires the
same ephemeral inputs; approval should explicitly include one fresh read of each
existing master/probe parameter if needed by Terraform. No SQL/start/send, DNS or
listener mutation is bundled; certificate removal/sender rollback is separately
reviewed. If Terraform rejects the plan as stale, stop and prepare a new plan for
review rather than silently replan/apply.

Schema, roles, Identity, images, Listings/Search/Wanted/Saved/Hybrid and eventual
HTTPS listener/DNS/trusted-proxy deployment remain tracked; certificate creation
is only the first independent preparatory deployment action.


### Certificate requested and sender updated — 2026-10-26 07:04:31 UTC

Aditya explicitly approved the exact saved two-action plan and fresh one-time
master/probe reads for apply. Rechecked plan/certificate-source hashes and account;
passwords used only in process memory/ephemeral Terraform inputs. Applied saved
SHA2569f7d85f76e72a4d955d2224e11086a9909d79c134f37827d7d4159f71c04c741
successfully, with no automatic retry/replan. [Sanitized result](id-01-step-12/https-certificate-apply-result.json).

Certificate `arn:aws:acm:ap-south-1:335523638354:certificate/a9775d00-2af5-4b12-990d-1ce9795f1859`
for clip-iisc.site is PENDING_VALIDATION, export DISABLED. Applied task-role sender
condition verified as verify@clip-iisc.site. No provider mail was sent.

Human DNS action at existing Spaceship provider: add CNAME host
`_2bfe7e93e85073296eb175def8bb245a` (full name
`_2bfe7e93e85073296eb175def8bb245a.clip-iisc.site.`), target
`_11c10845a76a4820548879213899012f.wzccmgtwzk.acm-validations.aws.`;
use default TTL. This is public certificate validation, not email authentication
and not the site's address record. Preserve MX/SPF/DKIM/DMARC and keep this CNAME
for renewal. No DNS write performed by the agent; verify public resolution and
ACM issuance after the human confirms entry. HTTPS is not live yet: listener,
apex ALIAS and integrated app remain separately gated deployments.

Post-apply metadata checks: original RDS remains stopped/t4g.micro; shared API
revision1desired/running/pending0; separate Listings demo retains1host/1running
and0pending. No app deployment, task/DB startup, SQL, S3/CORS, network or demo
mutation. Certificate retained for upcoming deployment, review date2026-10-27;
future cleanup/sender reversal requires its own exact plan approval. Other
marketplace connections remain pending in the ordered runtime plan.


DNS follow-up2026-10-26 07:08:19 UTC: Aditya reports the CNAME added. Public
DNS-over-HTTPS lookup returned the exact ACM-required CNAME target (TTL1800).
ACM remained PENDING_VALIDATION in two checks, with no listener association.
No record correction is indicated by this evidence; issuance remains pending,
not a failure or completed HTTPS endpoint. [Updated safe result](id-01-step-12/https-certificate-apply-result.json).
No DNS/resource change, secret read or send in this verification. Retain the
record for renewal; later recheck issuance before listener deployment.


### Database/runtime connection package — 2026-10-26 07:12:03 UTC

Aditya requested the current changes committed first, then local database/runtime
preparation and an ACM recheck. Certificate/discovery package committed6f37b0b;
Gitleaks/JSON/links/whitespace passed. No push or extra commit authorized.

Refreshed [migration review candidate](id-01-step-12/shared-migration-apply-review.json)
against6f37b0b, retaining original comparison provenance and explicit image/DDL
pending gates. All17file paths/hashes still match, head20261025013000. Recorded
current runner/setup/role source hashes and Suraj's human-confirmed PR14 merge
without representing it as image or live SQL approval. No manifest-review bypass.
Expanded [runtime proposal](../../../infra/terraform/shared/test/service.tf)
with exact target, two-role/URL responsibilities, operation/publication ordering,
connection budgets and refusal/recovery rules.

Material finding: the existing Listings lifecycle script is explicitly for
`clip_test_listings`, gives its demo role database ownership and includes teardown.
It is not a safe shared database login/migration route. Its URL parameter name
alone does not justify injecting that value into the shared app. No decrypted URL
was read. Preserve the active demo and its current credential. The local Identity
demo creates a separate disposable marketplace role with broad existing local
table grants; that does not establish reviewed shared runtime privileges either.

Identity's14table least-privilege role/setup already exists and remains separate.
The shared marketplace pool covers Listings plus Search/Wanted/Saved; B/C must
confirm required explicit table/sequence/function/catalogue access, Hybrid read/
worker limits and operator pipeline privileges. No invented grants, owner role,
private Identity table reads, or reuse of the isolated bootstrap. This is the
remaining implementation/review boundary before a safe shared role apply.

Next bounded live checkpoint to request separately: original shared RDS start,
existing one-sleep-task/private-tunnel route and read-only four-namespace/tracker/
role/logging catalog inspection. Keep shared API stopped, no migrations/role/grant/
URL writes, no provider sends, no Listings demo start/stop. Use existing fixed
account/resource/class/AZ with named exclusive original-resource window, explicit
caps/deadline/one private admin-secret read and owned cleanup. Previous one-hour/
$1/20minute-start bounds are proposals, not fresh execution approval or cost proof.
After metadata, finalize image/first-apply review and the safe marketplace-role
setup; apply schema/roles/secret publication only through separately verified
increments. No live DB connection occurred during this preparation.


ACM recheck2026-10-26 07:13:33 UTC: certificate **ISSUED**, DNS validation
SUCCESS, expiration2027-05-11 23:59:59 UTC, no resource association. Updated
[certificate evidence](id-01-step-12/https-certificate-apply-result.json) and cloud
inventory. No secret reads/resource writes for this check; HTTPS listener and
application deployment remain pending. Database/runtime preparation is documentation
and proposed configuration only; no code behavior changed or full tests rerun.


## 2026-10-26 demo and deployment handoff

The [consolidated outcome/cleanup handoff](id-01-step-12/demo-postmortem-20261026.md)
replaces duplicate local notes and expired recovery/preflight requests. The original
RDS eventually started; the 17-migration chain, separate Identity/marketplace
roles and secure URL publication have actual recorded results. The executed
migration manifest is archived with exact bytes; the reusable default is no
longer armed with the consumed live approval.

AMD64 image/task IAM/private S3 were prepared and retained. Managed ingress was
rejected by AWS; a temporary EC2 TLS proxy was used and later removed. Hosted
human account/image/Search acceptance was not obtained. No-photo local workaround
and recovery/proxy ingress source are gone; the one-to-eight image contract holds.

Last recorded cleanup has API/host0, released public IP and deleted demo ingress;
RDS was last observed stopping, so final stopped state remains unknown. User-managed
A record removal and service state/live revision reconciliation remain outstanding.
No cloud query, state/DNS edit, apply or secret read is authorized by Git cleanup.

The retained Terraform runtime is now explicitly opt-in with a private nonempty
controlled-recipient list. Default-off foundation startup remains valid; activation
requires reviewed DB/IAM/image/HTTPS inputs. Existing marketplace grants do not
cover Hybrid embedding/pipeline operations. Keep those real integrations and new
peer/CI review pending; ID-READY is not accepted.


The historical runtime JSON proposal was superseded by the retained shared service/
variables/IAM/S3 source and removed during cleanup. Earlier preparation links now
lead to that implementation; exact old proposal bytes remain in commit1bb0eb9.
Historical execution/approval receipts are preserved separately from reusable
future-run review defaults.
