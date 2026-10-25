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
