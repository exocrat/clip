# ID-01 Step13 — exact bootstrap candidate for human review

**Not execution approval.** Aditya confirmed all existing database records may
be discarded. No reset/grants have run. The API image remains the verified2b292ad
artifact; these operator/test changes do not change its application inputs.

## Concrete operation and preservation

Account335523638354, profile `adityalaxmi1`, ap-south-1, private protected
`clip-shared-test-postgres`, resource `db-PYRRZJPVKPGHIXDAHUWATXGH7A`, database
`clip_test`, admin `clip_test_admin`. Expected17versions/head20261025013000,
37tables and exact catalog/count fingerprint from the approved read-only window.
[Complete hash-bound input](bootstrap-execution-candidate.json).

Proposed sequence:

1. Verify source/tool/manifest/grant approvals before resource/secret operations.
   Recheck target, both clusters idle, API0 and exclusive writer. Start one
   private Micro plus retained RDS in a newly approved ≤60minute/$1 window; set
   Standard credits and timed fallback, stop new work by40minutes. No public IP,
   ingress, IAM, application task, provider, DNS or image publication changes.
2. Read only master, existing Identity DSN and marketplace DSN into memory, one
   read per reference. Require expected host/database/role, verify-full TLS and
   privacy defaults. Test actual existing logins before reset. Do not write SSM
   or rotate passwords, auth keys, provider keys or token/OTP values.
3. One dedicated administrator connection holds advisory key(1129072976,12)
   through reset, migration and restoration. Compare exact repeatable-read
   catalog, all37table counts and all17tracker versions. Acquire NOWAIT table
   locks, repeat the checks, reject column grants/RLS/external FKs/event triggers
   or any drift. Existing runner/prefix checks are unchanged.
4. In one reset transaction remove only `identity`, `listings`, `search`,
   `conversations` and `public.schema_migrations` with their exact reviewed
   dependency closure. This deletes the3users/6sessions, temporary credential,
   enrollment/key binding/auth bookkeeping and2upload references observed in
   the inventory. Reference catalogue is recreated by published migrations.
   No other database/schema/role or S3 object is deleted.
5. Run the existing pinned dbmate route for all23unchanged SQL files, head
   20261027112205; require40tables/36functions/46triggers. Migration tool is
   `ghcr.io/amacneil/dbmate@sha256:520c740c6e0ad73fde2cd1ea7e2b779aaf789d22aca8858f87a478e7094535fb`.
   Its review/manifest gate must be genuinely completed before step4. Keep
   the original pending candidate/old executed receipts intact; create a bound
   execution copy only after review, not an unreviewed flag bypass.
6. Restore only the candidate's explicit grants to existing Identity/marketplace
   roles. Preserve role OIDs/passwords/memberships/logging/database privileges;
   no CREATE/ALTER ROLE, new DSN/role, blanket ALL/future-table grants or privilege
   escalation. Verify actual existing-password TLS logins after restoration and
   exact allowed/denied table/schema rights. No synthetic shared account seeding.
7. Keep API off. Save sanitized counts/grants/digests and close every owned
   connection/tunnel. Restore ASG0/max1, terminate owned host/root, stop RDS when
   exclusive, remove owned timed fallback. Retain shared network/storage/images/
   keys and all unrelated resources. No actual bill/credit assumption.

Master reference: `/clip/test/database-master-password`.
Actual-login references: `/clip/test/identity/database-url` and
`/clip/test/listings-database-url`. No probe/auth-key/email-configuration read.
All references must retain reviewed versions; unexpected rotation stops the run.
Candidate JSON includes exact counts, catalog SHA, source SHA and table allowlist.
The private plan/read receipt contains no credential value.

## Exact additional grant request for owners

Preserve historical Identity14table/tracker grants and marketplace10table grants.
Only the following marketplace additions are proposed:

| Object | Privileges | Actual need |
| --- | --- | --- |
| `listings.embedding_pipelines` | SELECT | Invoker invalidation enumerates serving/building pipelines. |
| `listings.embedding_generations` | SELECT, INSERT, DELETE | Listing insert/update invalidates/queues derived generations; deferred constraint reads them. |
| `listings.embedding_chunks` | SELECT | Deferred generation completeness constraint counts parts. |

No pipeline/chunk writes, generation UPDATE, Identity access or Conversations
USAGE/table access is added. No SECURITY DEFINER/trigger disabling. Local tests
use a real restricted-role login with an active pipeline: normal listing trigger
queues a generation and passes its deferred check; prohibited writes and other
domain reads still fail. The test rolls back before FR-04 image acceptance and
does not claim a complete image-backed listing workflow.

Suraj/affected Listings+Search owners review these invoker-trigger privileges.
Affected schema owners review the shared reset/closure. Independent human review
of the new coordinator is still pending; its source hashes are in the candidate.
Existing merged23-file SQL review does not by itself review this new reset route.
Conversations remains denied; activating its full feature set is not an extra
ID-READY gate unless an agreed readiness consumer requires that path.

## Failure behavior and evidence

The default script entry prints documentation and cannot execute a reset. The
explicit operator API refuses live missing/invalid approval booleans and pending
manifest/image review before connecting. Safety checks use explicit exceptions,
not assertions removable with Python optimization.

Before reset commit, failure rolls back the reset. After reset commit, dbmate
commits individual files; a migration/grant/check failure preserves that exact
prefix/state and requires a recovery plan. No automatic retry/down/reset/restore,
no claim of end-to-end atomicity, no new snapshot/backup/recovery guarantee.
Connection closure releases all reentrant lock levels on success/failure.

Local real TLS checks cover17→reset→23, role OID/same-password preservation,
continuous locking, drift/column/tracker refusal, transactional reset rollback,
post-reset failure, live pre-connect gates and real restricted embedding triggers.
`make check` and the affected final Python rerun are recorded in the work log.

## Remaining gates

1. Independent and affected-owner review of this exact candidate/source.
2. Source commit/binding and actual migration-image/manifest review receipt.
3. Explicit approval for the concrete persistent reset/grant/cloud window.
4. Actual execution/verification, then separately reviewed runtime/proxy deploy,
   real Microsoft/email/session/contact/browser checks and retention cadence.

ID-READY/Step13 remain incomplete until those real checks pass. No browser or
provider evidence is inferred from local fixtures, an image smoke or SQL grants.
