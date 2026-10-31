# NEXT-06 private administrative inventory — exact next-window proposal

State: prepared locally, not approved or executed in AWS. Both resources were
last verified stopped at 2026-10-30 18:20:36 UTC. This is the next part of original
Step 3; no DATA-READY or real-load gate is waived.

## Why this route

The marketplace role was deliberately denied `public.schema_migrations` access:
see `docs/evaluation/identity/id-01-step-12/marketplace-runtime-role-result-20261026T104412Z.json`.
The latest failure therefore matches an existing boundary. Preserve it; do not
add migration/Identity privileges to that application role. Existing setup work
uses login `clip_test_admin`, database `clip_test`, and the single parameter
`/clip/test/database-master-password` through private SSM forwarding. This proposal
requests that setup route only for read-only catalog inspection. The operator is
still IAM user `mohitmahapa1`, not AWS root; a database setup login is distinct.

## Exact execution and outputs

1. Verify all hashes in `admin-inventory-command-review.json`, including helper,
   controller, existing SDK bridge/cleanup helper, local plugin and regional CA.
   Require local loopback15432 unused. Recheck account335523638354/ap-south-1,
   non-root IAM user, exact stopped existing RDS/EC2/type/endpoint/security groups,
   idle ECS cluster/service and safe ASG membership with Launch/Terminate already
   suspended. Any drift refuses before starts; no IAM/ASG/network changes.
2. Start existing `clip-shared-test-postgres` and then `i-086045c48487471de` using
   the same previously reviewed polling/limits. No new host, Docker image,
   deployment or scaling. Require SSM Online and repeat idle/ASG guards.
3. Open exactly one `AWS-StartPortForwardingSessionToRemoteHost` session on that
   host, remote fixed RDS hostname/5432 to local127.0.0.1:15432. Use repository-local
   signed ARM64 Session Manager1.2.896.0. Verify the actual listener belongs to
   the owned plugin process group before retrieving credentials. No remote shell
   command, host credential read or extra host permission is involved.
4. Operator SDK decrypts only `/clip/test/database-master-password` once into
   process memory. Connect using fixed `clip_test`/`clip_test_admin`, RDS hostname
   plus loopback hostaddr, verify-full TLS with the reviewed Mumbai CA bundle,
   PostgreSQL18.6 and exact session identity. Startup options enforce readonly,
   5s statement/1s lock/5s idle limits and privacy logging. Verify these and
   pgaudit/auto_explain safety before catalog reads. No credential is in SQL,
   files, database DSN logs, environment, plugin input or evidence. The standard
   plugin interface carries its separate ephemeral SSM channel token in private
   child arguments; plugin output is discarded, not recorded.
5. Run only the fixed queries in `scripts/evaluation/reference_admin_inventory.py`:
   up to100 migration versions, four domain schema names, exact proposed loader/
   runtime role existence/flags, and proposed `clip_next06_reference` existence.
   Return bounded catalog metadata or fixed failure stage/SQLSTATE. No application
   table data, existing passwords, active query text, DDL, GRANT or data writes.
   Missing/denied/malformed state aborts without repair or stronger fallback.
6. Close the owned SQL connection, terminate only the owned plugin process group
   and SSM session, then stop/verify the exact host and RDS started by this window.
   Preserve another operator's workload if unexpected drift appears and escalate.
   Save sanitized timing/count/result/cleanup evidence. Stop before database
   creation, migrations, roles, object uploads or pipeline/deployment changes.

The proposed executable controller is `admin-inventory-controller.proposed.py.txt`;
its exact SHA and every dependency SHA are bound in `admin-inventory-command-review.json`.
Execute only after approval, from this clone using its `.venv/bin/python`.

## Limits, decisions and remaining gates

Same pricing basis and target safeguards as `start-access-load-proposal.md`:
USD1 incremental estimate envelope, 60min work plus15min cleanup, at most160
management calls, no automatic SDK retries; RDS readiness20min, host/SSM5min each,
tunnel readiness30s and SQL statement5s. Extra SSM StartSession/TerminateSession
replace the remote shell request. Existing storage/backups remain chargeable;
RDS auto-restarts after seven stopped days. No scheduler or billing hard cap.

This window supplies actual metadata needed to review creation of an isolated
NEXT-06 database and restricted roles. It does not authorize creation, grants,
1,000 S3 object PUTs, SQL population, migrations, model packaging or deployment.
Those require exact later action packages/affected-owner reviews. Existing22
human judgments and December1 cutoff remain unchanged. If access is denied,
report it; do not request broad policies automatically.

## Local checks and installation evidence

Only public AWS downloads and local preparation occurred. The official signed
macOS package passed `pkgutil --check-signature` outside the sandbox: AMZN Mobile
LLC(94KV3E626L), trusted Apple notarization. Initial sandbox verification could
not contact macOS trust services; the approved external check succeeded. Copied
only its user-space payload to `.tools/session-manager/1.2.896.0`; no package
installer, LaunchDaemon, sudo installation or global link. Binary reports1.2.896.0
and Mach-O arm64. Mumbai CA bundle parsed as three CA certificates. Exact hashes,
sources and boundaries are in the review JSON. These local checks do not establish
permission to open a real SSM session or use the administrative credential.
