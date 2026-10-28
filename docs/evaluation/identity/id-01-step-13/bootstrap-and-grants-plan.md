# ID-01 Step13 — clean bootstrap and grant review

Prepared2026-10-28 09:42:05 UTC. **Review candidate; no reset/grants/cloud action
authorized or executed by this package.** This supersedes neither published SQL
nor the separate Step12 live-review gates. Owner/operator: Aditya(A).

## Audit and verified baseline

The task's review→migrate→deploy order remains sound. The available execution
package has four material gaps, now explicit gates rather than implicit fixes:

1. Live inspection established17versions/head20261025013000 and37tables/
   33functions/43triggers, not an empty database or the required23-file chain.
   The strict runner correctly refuses that prefix. An exact reviewed reset is
   needed before the fresh-only route; never disable its prefix check.
2. Metadata so far does not establish ownership, dependency closure, effective
   ACLs/default privileges, role memberships or actual business/guard row counts.
   `DROP SCHEMA ... CASCADE` can affect objects outside the named schemas.
3. `create_identity_role` refuses an existing login. Existing Identity, marketplace,
   legacy Listings and probe roles/passwords/URLs must survive. The Identity
   proposal is a creation-era reference, not an executable reusable-login reset.
4. The historical marketplace grant receipt explicitly denies Conversations and
   embedding tables. Current `_marketplace_lifespan` plus `application_lifespan`
   falls back to the marketplace DSN for the Conversations pool. Also the invoker
   listing-embedding trigger accesses derived tables on ordinary listing writes.
   Restoring only old grants is insufficient; do not invent broad replacements.

Actual local PostgreSQL18.6/TLS checks reproduce the old grant package's denial of
Conversations and a listing insert failing on embedding privileges. They prove
the recorded package is insufficient, **not** that fresh live ACLs equal that old
receipt. A separate test confirms the candidate inventory exposes an external FK
and a view's internally owned rewrite dependency. No DROP is used by that test.

Sources: accepted main5e8d264; source2b292ad; existing23-file manifest through
20261027112205, target40tables/36functions/46triggers; canonical schema/contracts;
runtime role validators and historical role receipts. Exact hashes are in
`bootstrap-and-grants-review.json`. Image
`335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:bfa7316c26f683654f5c4b3f40e9817876db5afd79f8f13af978a8841fbde8f8`
is verified but not deployed. API image is not the separate dbmate migration tool.

## Ordered gates and outputs

| Order | Work/output | Check/dependency/decision gate |
| --- | --- | --- |
| 1 | Fresh read-only inventory and count-only baseline | Separate exact cloud/master-read approval below. No DDL. Reconcile all differences before continuing. |
| 2 | Affected-owner-approved explicit runtime grant matrix | Listings/Suraj, Search/Rahul, Conversations owners/reviewer and Identity review the current pool/trigger requirements. Review Conversations binding only if an agreed readiness consumer needs it; otherwise preserve denial and defer full Conversations acceptance. No new role/URL chosen here. |
| 3 | Implement/rehearse an explicit bootstrap coordinator and grants-only restoration | Disposable17→reset→23 rehearsal, rollback/dependency refusal, preserved role identity/credentials, actual restricted-role listing/trigger tests. Implemented and rehearsed locally; see bootstrap-live-review.md. Live review/execution pending. |
| 4 | Bind source, migration image/manifest, exact target/closure/grants and independent review | Existing candidate has image-review pending/live authorization false. Complete those reviews before destructive work; do not flip flags as a workaround. |
| 5 | Exact reset transaction, then fresh23-file migration | Separate destructive/cloud approval. Recheck target/snapshot/locks/clients; preserve partial failures. No automatic replay/adoption. |
| 6 | Explicit grants-only restoration and real-login checks | Preserve passwords/role OIDs/logging defaults/SSM versions. Read actual DSNs only with separate approved scope; no provider/auth-key reads implied. |
| 7 | Sanitized result and cleanup |23versions/head27112205,40/36/46inventory, effective grants and real-role checks; API still off. Stop owned host/RDS and remove owned sessions/fallback. |
| 8 | Separately reviewed runtime/HTTPS/provider/browser/retention checks | New immutable image deployment and actual Identity activation need their own plan. No milestone acceptance from schema or image checks alone. |

All steps remain under ID-01 Step13. The full Step14 consumer matrix stays separate.

## Gate1: proposed new read-only window

The previous09:17:07UTC window is over. This request is **not** an extension or
approval to start it. Account335523638354, `adityalaxmi1`, Mumbai shared/test;
RDS `clip-shared-test-postgres`/resource `db-PYRRZJPVKPGHIXDAHUWATXGH7A`, database
`clip_test`, administrator `clip_test_admin`, exact endpoint
`clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com`.

Proposed cap:45minutes from actual start, one private LT3 t3.micro/Standard credits,
retained db.t4g.micro RDS only, $1 incremental operator threshold, not a billing
cap. Start only after confirming both clusters idle, shared service0 and the exact
stopped/private/protected target. Create an owned scheduled ASG scale-down first;
temporary ASG min1/max1/desired1. No build, proxy, public IP/ingress, IAM, S3,
provider/send, ECR publication or application startup.

Use SSM remote-host forwarding to local15432 and verify-full TLS/public reviewed
roots. Read exactly `/clip/test/database-master-password` once into memory for
this session. No probe password, DSN, auth-key or email-configuration read/write.
Verify logging/privacy settings before queries. Execute the adjacent catalog-only
SQL under repeatable-read/read-only, statement5s/lock3s limits; private output only.

The proposed approval also includes **scalar COUNT(*) results only** for each
reviewed project base table, using quoted identifiers from the fixed four-schema
inventory. These queries access table data internally, but select no individual
record, identifier, contact, hash, payload or provider data. They are additional
to the catalog-only SQL file. Check every table, including enrollment/key guards,
sessions and upload/image references; compare catalogue8categories/4conditions
separately. Nonzero business/guard counts go to human review, never an automatic
assertion that data can be deleted. Aditya's earlier no-preservation direction
does not prove current counts are zero. Missing/unexpected objects also stop.

Capture role OIDs/flags/memberships, whitelisted logging defaults, schema/table/
function/default ACLs, extensions/event triggers and conservative dependency
graph. NULL object schema does not mean safe; extension/internal/partition owners
and textual/dynamic SQL references need explicit review. The graph is a review
aid, not a complete PostgreSQL DROP simulator or automatic allowlist generator.

Stop new inventory work by start+30minutes and begin cleanup; abort startup after
20minutes rather than beginning more work. On mismatch, timeout, unexpected
clients/objects or cap: close owned session,
restore ASG min0/max1/desired0 and terminate owned host/root; stop exclusive RDS
when AWS allows, remove owned fallback. Do not terminate other users' sessions or
repair SQL. The scheduled action covers EC2 only; RDS cleanup is operator-owned.
Retain shared network/NAT, backups/storage, keys, images and other-owner resources.
Compute estimate for45minutes is$0.02415 from already-recorded unit quotes;
excludes EBS, NAT/data, retained storage/logs/taxes. Actual bill not queried.

## Gate2: exact grant decisions still required

| Runtime principal | Existing reviewed starting point | Required review |
| --- | --- | --- |
| `clip_test_identity_app` |14Identity tables with exact per-table privileges; tracker SELECT; no other-domain access | Reuse login/OID/password. Restore only grants after reset; retain strict startup validator and logging. No role recreation or broad grants. |
| `clip_test_marketplace_app` | Explicit10Listings/Search table grants from historical receipt; no DDL/TEMP/Identity/Conversations/derived embedding grants | Inspect current live ACLs. Owners specify trigger-driven embedding access and current public Listings/Search/Wanted/Saved operations. Do not copy grants blindly. |
| Conversations pool | `database_dsn` else marketplace URL in current composition | For activated paths owners review binding and exact permissions; otherwise preserve denial. Full Conversations activation is separate from ID-READY. No credential/SSM/role creation authorized here. |
| `clip_test_listings_app`, `clip_test_probe`, admin/other roles | Existing unrelated/legacy/probe identities | Preserve role OIDs/passwords/flags/memberships and database grants. No privilege additions without owner review; flag accidental stale grants. |

Application roles must not own schemas/tables, gain CREATE/TEMP, acquire other-domain
Identity access or receive blanket ALL/default future-table grants. Preserve the
reviewed append-only Identity protections. Audit implicit PUBLIC function EXECUTE
and cross-table invoker-trigger requirements explicitly. Do not introduce
SECURITY DEFINER functions or disable triggers to hide a permission failure.

## Gate3–7: reset/migrate/restore semantics to implement after review

Proposed deletion set is only the four project schemas and
`public.schema_migrations`, including their reviewed dependency closure. It would
erase users, enrollments/permanent reuse guards, key commitments, sessions,
contacts, listings/images metadata, wanted/saved and conversation state. It is
not routine retention cleanup. Exact counts/closure and human deletion approval
are mandatory. SSM stable keys/passwords/URLs, database/role objects, other schemas/
databases and cloud/storage objects survive; S3 deletion is outside this scope.

Require a fully reviewed migration image/manifest **and grant package before
reset**, so the target is not wiped only to discover a blocked runner. Plan a
single owned admin session/coordinator holding the existing wrapper advisory key
`(1129072976,12)` across reset, migration and grant work. Current runner opens its
own connection/lock; reusing a borrowed dedicated connection or another reviewed
coordinator adaptation must be implemented/tested, not assumed. Keep the runner's
fresh/complete-only checks and migration file key intact. Never release the lock
and silently call that end-to-end serialization.

Reset is a guarded transaction; failure before commit rolls back. dbmate then
commits individual migrations, so reset+all migrations+grants are **not one atomic
transaction**. After reset commit, prior data is gone; after any migration/grant
failure keep API off, preserve the exact prefix/state and request a recovery
plan. No automatic down/drop/reset/retry. No new snapshot/restore is included;
existing backup recovery has not been verified by this plan.

Restore explicit approved grants on existing roles without ALTER ROLE/password,
new logins, URL publication or key rotation. Verify retained role OIDs/logging/
parameter versions and actual approved login behavior, not only SET ROLE as admin.
Use synthetic mutation tests only in disposable local rehearsal; never seed fake
users/listings in shared runtime. Real test accounts/provider flows come later
through the separately approved app path. Final verification must match23versions,
head20261027112205,40tables/36functions/46triggers and each owner-reviewed ACL.

## Local evidence and status

`uv run --locked pytest -q tests/test_identity_bootstrap_review.py`:3passed on
disposable TLS PostgreSQL18.6; no shared/cloud connection. The SQL candidate has
no side-effecting command beyond transaction-local settings/ROLLBACK. Tests make
an explicit isolated-only substitution of its three target predicate literals;
the live file remains pinned. No live inventory/count/reset/grant action ran.

Review source: [PostgreSQL DROP SCHEMA](https://www.postgresql.org/docs/18/sql-dropschema.html),
[internal dependencies](https://www.postgresql.org/docs/18/catalog-pg-depend.html),
[limitations of SQL dependency tracking](https://www.postgresql.org/docs/18/ddl-depend.html).
No milestone completion: owner review, independent review, full execution package,
fresh cloud/deletion approvals and actual runtime acceptance remain pending.

## Approved read-only inventory outcome — 2026-10-28 10:25:43 UTC

Snapshot10:13:49UTC passed verify-full TLS/privacy/repeatable-read gates;17versions,
37reviewed base tables,0other client sessions. The database is not empty:
3users,6session records,1temporary credential/enrollment,2upload records and
authentication/OTP/key-binding bookkeeping. No individual record/content selected.
Only categories8/conditions4 and those Identity/upload tables have rows; listing,
Wanted/Saved and Conversations business tables are empty. [Exact safe counts](bootstrap-and-grants-review.json).

All project schemas/inspected relations are admin-owned. Active Identity and
marketplace database roles have CONNECT without CREATE/TEMP; table-level matrices
match their historical references. Marketplace has no privileges on the three
embedding tables and no Conversations schema USAGE. Legacy Listings login lacks
CONNECT to this target; preserve it rather than reusing it. No event triggers,
project SECURITY DEFINER functions, project default ACLs or external FKs observed.
The conservative graph1104objects contains only project structures, associated
TOAST structures and migration-tracker structures in public. This is not a claim
that all textual dependencies/column privileges/real logins have been accepted.

Closed tunnel, terminated owned host, restored zero capacity and stopped RDS;
cleanup complete10:19:49UTC, well before45minute deadline10:53:32UTC. One master
version1 read only; no role/schema/credential/storage change. Previous statements
about no data do not replace review of these actual nonzero counts. Obtain
explicit discard direction for these database records before finalizing deletion
scope, especially lifetime enrollment/key-binding guards. No reset is authorized.

Conversations denial is a scoped integration finding, not an added requirement
to activate all Conversations features for ID-READY. Preserve it unless the exact
agreed consumer checks need access; owner review remains mandatory for any
permission expansion and for the shared schema reset itself.

## Current local preparation — 2026-10-28 11:15:49 UTC

Aditya confirmed all existing database records may be discarded, including the
observed enrollment/key-binding/authentication bookkeeping. This resolves record
disposition; it does not change credential/S3 preservation or exact live gates.
The guarded coordinator and12real local TLS rehearsal tests now pass. The
[exact reset/grant/window candidate](bootstrap-live-review.md) is ready for
independent/affected-owner review and separate live approval. No reset has run.
