# NEXT-06 Step 3 — create-only isolated database setup

State: prepared and locally rehearsed; not approved or executed in AWS.
The verified schema scope is accepted main/corpus29, not shared runtime32.
This increment stops before credential activation, object/data loading or deployment.

## Exact proposed action

Use the hash-bound `database-setup-controller.proposed.py.txt` and
`database-setup-command-review.json`. The controller reuses the successfully
executed private admin window's exact account335523638354/profilemohitmahapa1/
Mumbai targets, host/RDS/ASG/idle checks, one named setup-secret read and owned
SSM tunnel. Its management-call expressions match that executed route. Never use
root or the other account. No deployment, scale, replacement, network or IAM change.

1. Verify every bound dependency and all29migration hashes before starts. Refuse
   local port15432 in use, changed target/source, non-stopped resources or shared
   workload/ASG drift. Start only existing RDS then existing host; require SSM
   Online, exclusive use and the already-suspended Launch/Terminate protections.
2. Open one owned private remote-host tunnel, verify listener ownership, read
   `/clip/test/database-master-password` once into memory. Connect as fixed setup
   login `clip_test_admin` to existing control database `clip_test` over verified
   hostname TLS/private loopback route; verify18.6/session/privacy settings.
   Its DDL connection has readonly OFF explicitly; statement timeout60s, lock5s,
   idle transaction60s. This is a newly requested write scope, not the old
   read-only approval. No master credential in app, files, env, SQL or evidence.
3. Refuse if `clip_next06_reference` or either proposed role already exists.
   Check existing application database ACLs: if any grants CONNECT to PUBLIC,
   stop before changes. NOINHERIT does not defeat PUBLIC rights. Never revoke
   another database's ACLs as a workaround. PostgreSQL/RDS system databases are
   explicitly excluded; this is application isolation, not a claim of denying
   access to standard system catalogs.
4. In one transaction create only `clip_next06_loader` and
   `clip_next06_runtime`: NOLOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOINHERIT,
   NOREPLICATION, NOBYPASSRLS, connection limit2. Set only these new roles' fixed
   privacy defaults. No password, authentication secret, membership grant or
   existing role/password change. Both roles remain unable to sign in.
5. Record create attempt durably. Create only `clip_next06_reference`, owned by
   `clip_test_admin`, TEMPLATEtemplate0, UTF8/localeC, **ALLOW_CONNECTIONS false**.
   Revoke PUBLIC privileges only on this new database and grant CONNECT only to
   the still-inactive loader. Then enable database connections. The setup owner
   retains owner access; runtime receives no access. This closes the transient
   default-PUBLIC window without changing shared32database.
6. Connect as setup owner to the new database, prove exact session/privacy/
   transport and no user relations. In one transaction create dbmate-compatible
   `public.schema_migrations(version varchar NOT NULL PRIMARY KEY)`, execute
   exactly the29bound UP sections in order and record their versions. The
   source loader rejects changed files/set/version/options; no DOWN migrations,
   source edits, constraint/trigger bypass or existing-data adoption.
7. In that same transaction revoke PUBLIC on only the new public schema and
   grant the inactive loader precisely:

   | Scope | Rights | Purpose |
   |---|---|---|
   | public, identity, listings schemas | USAGE | Tracker and owned bulk SQL |
   | identity.users; listings.sale_listings, image_uploads, images | SELECT, INSERT, UPDATE | Four-table bulk load, projections, required exclusive/trigger row locks |
   | listings.categories, conditions, embedding_pipelines; public.schema_migrations | SELECT | Catalogue, fresh pipeline and exact schema guards |
   | listings.embedding_generations | SELECT, INSERT, DELETE | Existing invoker trigger's invalidation/queue statements, including when registry is empty |

   No ownership, schema CREATE, catalogue UPDATE, data-table DELETE/TRUNCATE,
   Conversations access or role administration. Runtime remains NOLOGIN with no
   grants. Verify29actual migration versions and both roles' disabled/negative
   privilege flags and lack of inherited memberships before committing.
8. Save sanitized stage/result evidence. Close SQL, terminate owned plugin and
   SSMsession, and stop/verify exact host/RDS even after failure. Repeat the
   exclusive-idle/ASG guards before disruptive cleanup. Never disrupt unexpected
   other-owner workloads. No success from accepted asynchronous stop requests.

## Partial failure, retention and approval boundaries

Roles commit before CREATE DATABASE, which cannot be transactional. Record before
and after database creation; an uncertain outcome is never retried or adopted.
Migration/grant failure rolls back its transaction; already committed new database
and inactive roles remain for exact reviewed recovery. No automatic DROP, reset,
password rotation, shared ACL repair or resource deletion. A subsequent call
refuses existing names. Record remaining artifacts; cloud compute still closes.

Proposed limit: same60minwork+15mincleanup/160management calls/USD1incremental
envelope and published Mumbai base0.0322USD/h from the prior approved proposal.
At75min the conservative base allowance is0.04025USD, excluding credits/network/
existing storage/baseline/tax; this is not a hard billing cap. Database contents
share existing20GiBallocation; no resize is authorized. Stop resources after this
window rather than waiting online. RDS can auto-restart after seven stopped days.

Only29canonical migration/catalogue seeds and roles/ACLs are prepared here, not
5,000user/1,000listing business rows. No new Parameter Store value is written.
The next separately reviewed load package must create/publish and activate the
restricted loader credential, select/approve the S3prefix/effective access,
verify fresh target/current catalogue/500000paise runtime threshold and real
1,000PUT/GETbyte checks before atomic SQL insertion. Runtime credentials/grants,
normal real Identity/media workflows, Linuxmodel/helper/vector processing and
final source/labels/reproducibility/freeze remain their original gates. Current
22human judgments and December1cutoff are unchanged; DATA-READY stays incomplete.
Independent source/affected-owner review and exact cloud action approval remain
required; this preparation itself authorizes no cloud write or publication.

## Local proof and important limits

`scripts/evaluation/reference_database_setup.py` is an inert explicit operator
helper; it contains the fixed create-only procedure and guards.
`scripts/evaluation/reference_setup_local.py --local-rehearsal` owns a new private
native PostgreSQL18.6/Unix-only cluster using existing pinned tools, creates a
canonical dbmate baseline and compares complete schema-only dumps (ignoring only
random pg_dump restrict tokens and owner/ACL metadata). It then activates the
loader **only in that native fixture**, executes actual shared bulk SQL and tests
negative permissions. Proposed cloud setup never activates either login.
`data/tests/test_reference_database_setup.py` adds refusal, source-binding,
write-order and uncertain-create/no-retry controls. No production code or
canonical generator/migration/contract bytes were changed.

Native successful receipt: `/private/tmp/clip-next06-reference-e5z8b3im/setup-result.json`.
Canonical schema comparison hash: aa72c9257b62de8897bb187d7a32f3d00a3da6481477b9a4fe66d2408f881bd1.
Actual restricted-role SQL checks verified5000users/1000listings/1000image references/
1000owners/800available/1000text vectors and GINindex. Eight forbidden-operation
checks passed, plus denial of CONNECT to the other application fixture database
and TEMP on the new target. Runtime had no CONNECT and stayed NOLOGIN. Native
cluster verified stopped. Planned image keys are SQL references only: this is not
S3/media/real Identity/runtime32/ML acceptance. Original real integration remains.

Initial local trials found sandbox-blocked shared memory (external local-only
permission used), tracker varchar length mismatch (corrected to exact dbmate),
a restricted login unnecessarily trying to set superuser logging GUCs (now uses
admin-set role defaults), and trigger-required generation-table rights (added
only actual invoker operations). Every initialized trial cluster was stopped;
no trial touched cloud or source photos. Keep failed/successful evidence distinct.

Current [preparation/check evidence](database-setup-preparation-result.json) and [retained final native receipt](database-setup-native-result.json). Full data suite232passed, Black337files, boundaries0. All37source/dependency hashes match; no cloud API in this increment.
