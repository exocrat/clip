# ID-01 Step13 — Micro build and read-only database window

Prepared by Aditya's agent, 2026-10-28 05:09:13 UTC. **Original scope subsequently approved and partially executed; see outcomes below.**
Aditya selected a native AMD64 `t3.micro` build; no local AMD64 execution is assumed.
This is an internal Step13 checkpoint, not readiness acceptance or schema approval.

## Bound source and tools

- Application commit: `3433ae7773206c762209c08d3ca00a23ed776e9f`.
- Allowlisted tracked archive: `/tmp/clip-id01-build-plan-7xddjfnq/source.tar`;
  2,488,320bytes/233files, SHA256
  `09b9a396929d50a9667e7ef7e7f274cbea7251ad5772a8dfc8a3523580a2b14c`.
- Includes root Python/npm manifests/locks, `apps/api/app`, API Dockerfile/ignore,
  `apps/web` and generated contracts. No working-tree changes, credentials,
  environment files, caches, `.git`, `node_modules` or built `dist`.
- Host helpers are reviewed separately by their hashes in the adjacent proposal
  JSON. They are operator tools, not application image inputs. Changed source or
  helpers require review before execution. Do not claim uncommitted helpers are
  part of the application commit.

## Requested cloud/secret scope

Account335523638354, profile/admitted operator `adityalaxmi1`/Aditya,
ap-south-1 shared/test, exclusive window ≤4hours, $2 incremental operator stop
threshold, not an automatic billing cap. Recheck idle shared and isolated Listings
clusters and unchanged stopped/private/protected RDS before starting anything.

1. Create the owned one-off ASG scale-down at actual start+4hours; temporarily set
   `clip-shared-test-ecs-host` min1/max1/desired1 using LT3 `t3.micro`. Set only the
   new host to Standard CPU credits. Keep API service desired0, Identity/proxy off.
2. Start retained `clip-shared-test-postgres` concurrently for later inspection.
   No new database, host role, policy, bucket, subnet, IP or inbound rule.
3. Via SSM RunShellScript, verify Python3/Docker25/timeout/swap tools, architecture,
   disk and available memory. Abort on missing tools, other work, unsupported
   memory/swap limits or unexpected target; no automatic installation or resize.
4. Install only the two hash-checked helper files on this owned host. Run the
   transfer helper with a fresh private directory
   `/var/tmp/clip-id01-build-3433ae777320` and the exact source archive hash.
   Use `AWS-StartPortForwardingSession`, host port18765/local18765, to access only
   the helper's loopback interface. No public port, SSH or signed URL.
5. POST the exact archive to `/source.tar` through that tunnel. Receiver streams
   ≤100MiB, verifies SHA256 and permits one upload. GET serves only completed
   `/image.tar` and `/result.json`; no browsing, credential files or extraction.
6. Run the native build helper with those exact directory/hash/commit arguments.
   It validates the archive paths/types, then creates2GiB swap on the existing
   encrypted root (no extra EBS). Sequential Docker25 legacy build, per-step
   RAM512MiB/combined RAM+swap1536MiB, timeout45minutes. Two-stage concurrency is
   not attempted. Build args: Microsoft button=true, public-demo=false.
7. Verify linux/amd64, UID10001, default-disabled Identity, bounded loopback HTTP
   health/bundled UI and Docker health. This smoke runs without DB/auth/provider
   values; it is not actual Identity activation or API memory acceptance.
   Save the image and SHA256 to completed artifacts. Download over the tunnel,
   verify archive/image IDs, then `docker load` into the existing local Unix-socket
   daemon for publication. Storing/pushing an AMD64 image needs no local execution.
8. Publish only this verified image to
   `335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api`, new tag
   `id01-step13-3433ae777320`. Refuse an existing tag; no latest/overwrites. Use
   local AWS ECR token via stdin into an owner-only temporary Docker config; no
   token in arguments/logs/host, no added host IAM. Verify registry manifest digest
   and architecture/config against built image; record immutable ECR URI. Stop on
   ambiguity, do not automatically republish. Retain accepted ECR image for later
   deployment; publication does not authorize task-definition/service changes.
9. Through `AWS-StartPortForwardingSessionToRemoteHost` on the owned host, forward
   local15432 to the exact RDS endpoint below. Read/decrypt **only** existing
   `/clip/test/database-master-password` once into local process memory. No probe,
   application-DSN, authentication-key or email-provider value read. Scope includes
   this password's use for a read-only SQL session, beyond earlier TF-only use.
10. Run the catalog inspection below, save only sanitized metadata. No app table
    contents, contacts, conversation text, credential columns or SQL query text
    from other sessions. Keep database login and catalog output local/private;
    commit only reviewed aggregate migration/schema/role findings.
11. Close owned tunnels/server/smoke container; remove owned temporary Docker
    credentials/context/download after verifying durable image evidence. Terminate
    only the owned host/root, restore ASG min0/max1/desired0, stop RDS when still
    exclusive and remove the owned schedule after confirmed cleanup. Preserve
    shared NAT/network, images, keys, grants, databases and other-owner resources.

No migration, reset/drop, role/grant/password change, synthetic application rows,
provider call, email, API/proxy activation, DNS or Git publication is in scope.

## Exact read-only inspection boundary

Verify RDS resource `db-PYRRZJPVKPGHIXDAHUWATXGH7A`, engine18.6,
database `clip_test`, login/session user `clip_test_admin`, endpoint
`clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com`.
Use psycopg from the existing locked local environment, host=that endpoint,
hostaddr=127.0.0.1, port15432, sslmode=verify-full, reviewed regional CA roots plus
system roots. No TLS downgrade; no psql installation is required.

Connection startup sets default_transaction_read_only=on and approved privacy
logging options from `identity.database_setup.LOGGING`. In the bounded transaction
set READ ONLY, statement_timeout5s, lock_timeout3s; verify current/session user,
database, TLS, current read-only and logging settings before further inspection.
Abort on mismatch; roll back and close at completion/failure. Fixed queries only:

```sql
SELECT current_database(),current_user,session_user,
       current_setting('transaction_read_only');
SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid();
SELECT nspname FROM pg_namespace
 WHERE nspname IN ('identity','listings','search','conversations') ORDER BY 1;
SELECT n.nspname,c.relkind,count(*) FROM pg_class c
 JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('identity','listings','search','conversations')
 GROUP BY 1,2 ORDER BY 1,2;
SELECT n.nspname,count(*) FROM pg_proc p
 JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname IN ('identity','listings','search','conversations')
 GROUP BY 1 ORDER BY 1;
SELECT n.nspname,count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
 JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE NOT t.tgisinternal
   AND n.nspname IN ('identity','listings','search','conversations')
 GROUP BY 1 ORDER BY 1;
SELECT c.relkind FROM pg_class c
 WHERE c.oid=to_regclass('public.schema_migrations');
SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,
       rolinherit,rolreplication,rolbypassrls,rolconnlimit
 FROM pg_roles WHERE starts_with(rolname,'clip_test_') ORDER BY rolname;
SELECT count(*) FROM pg_stat_activity
 WHERE datname=current_database() AND pid<>pg_backend_pid()
   AND backend_type='client backend';
```

Only if tracker metadata proves an ordinary base table, read
`SELECT version FROM public.schema_migrations ORDER BY version LIMIT 1001`;
reject >1000 rows or unexpected type/versions. Do not invoke app functions or
read application rows. Compare returned versions to the reviewed23-file manifest;
historical17-prefix evidence is not permission to auto-upgrade. Catalog role
flags do not prove effective grants; the subsequent exact bootstrap/runtime-grant
review still needs its full ACL/membership checks and separate approval. Observe
other client sessions without reading their identities/query text; stop on any
unexpected concurrent client before any later mutation is proposed.

## Limits, failures and cleanup

Prior measurement:916MiB total/ECS memory,537MiB idle available. Swap is explicitly
part of this proposed build trial, not permission for more RAM/hosts. Stop on OOM,
timeouts, disk<10GiB, unsupported limits, bad hashes, failed smoke/TLS/privacy or
unexpected workload/state. No automatic retry/resize, broad cleanup or SQL repair.

At four hours Micro+RDS public compute estimate is$0.1288, excluding root EBS,
NAT/package/image transfer, retained storage, ECR, logs and tax. Standard credits
can slow the build. $2 is a conservative operating threshold, not a verified bill
or spend-enforcement mechanism. No account billing/credit assumption. Cancel and
clean up if progress/cost cannot stay within bounds. Scheduled scale-down covers
EC2 only; RDS must be stopped by the operator after AWS permits it.

## Local verification and remaining gates

Three real loopback transfer tests pass; first test run exposed incorrect test
connection context management, corrected with explicit close before success.
Shell syntax and embedded Python parsing pass. Command help is inert; no host
build, transfer tunnel, ECR publication or SQL has run. Final source/secret checks
are recorded in the work log. The exact window/publication/secret-use scope above
requires human approval before execution. Actual API sizing, clean bootstrap,
runtime roles, HTTPS, provider/browser and retention acceptance stay pending.

Primary references: [AWS Session Manager forwarding](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html),
[Docker legacy build limits](https://docs.docker.com/reference/cli/docker/image/build/),
[Docker memory/swap](https://docs.docker.com/engine/containers/resource_constraints/).

## Results and pending build-only retry

The resumed catalog inspection passed TLS/privacy/read-only gates and found the
exact17-version prefix,37tables/33functions/43triggers and0other client sessions.
No app rows or DDL. Full effective-ACL/bootstrap acceptance is still pending.
The native build hit Node's JavaScript heap ceiling during TypeScript compilation;
canceled without publication or automatic retry. Kernel OOM was not established.

Prepared correction: API Dockerfile accepts optional CLIP_WEB_BUILD_NODE_OPTIONS
only in the web build stage. Empty default preserves ordinary builds; no runtime
ENV changes. Micro helper requests --max-old-space-size=768 while retaining
512MiB RAM/1536MiB RAM+swap limits and the existing2GiB encrypted-root swap.
Heap can use that swap; this is a proposed bounded trial, not measured native
success. Real local ARM64 typecheck and Vite bundle pass with this allowance.
Transfer/helper host-grammar regressions4pass. The earlier Python3.9 syntax
correction and test are included in the pending code review.

Retry needs human verification/commit and exact changed-build approval. Bind the
new commit/archive to the source-tree hash in adjacent JSON. Publish only its new
heap768 tag, never the old source tag. One private Micro, Standard CPU credits,
45minute build maximum, same original09:17:07UTC deadline/$2 threshold, guarded
cleanup; do not start if remaining time cannot fit build/transfer/cleanup. No
automatic extension/retry. RDS stays stopped: no SQL or secret read is needed for
this build-only retry. No API/proxy/deployment/provider change.

## Approved retry outcome — 2026-10-28 09:06:27 UTC

The pending retry above was subsequently human-verified/approved and committed
at2b292ad. Same Micro/RAM/swap limits succeeded; C7i was unnecessary. Corrected
the smoke harness's missing explicit serve-web flag, then checked/exported the
same image successfully. A pre-publication transfer timeout was recovered with
a fresh private tunnel/copy; archive SHA and registry-config binding passed.
Image is retained at immutable digest `sha256:bfa7316c26f683654f5c4b3f40e9817876db5afd79f8f13af978a8841fbde8f8` in the approved
shared API repository/tag. No deployment occurred. Owned host is terminated;
ASG/API0 and RDS stopped; owned schedule/tunnel/auth/transfer archive cleaned.
[Full immutable URI and safe receipt](preflight-and-proposal.json).
Clean database bootstrap/grants and all actual Identity activation/HTTPS/provider
checks still need separate scopes/approvals. This outcome does not authorize
repeating the old plan or extending its expired/consumed window.
