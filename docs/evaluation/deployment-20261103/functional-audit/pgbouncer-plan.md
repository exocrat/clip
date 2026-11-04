# Shared PgBouncer replacement — release preparation

Suraj selected this pivot after the approved RDS Proxy creation returned
`FreeTierRestrictionError`. Do not upgrade the AWS account plan. Preserve the
optimized direct fallback at `6193ca7`, accepted PR32 at main `360cd16`, all
previous failures and the 100%-only pilot decision. This document is not an
approval to deploy or a claim of capacity/NFR acceptance.

Current checkpoint: Suraj selected the existing ten **unreserved** Lambda slots
for the real pilot. The pending quota request must not delay preparation or
silently change the run. New preflight/runner checks verify exact regional quota
and absence of competing functions, stopping on drift. See
[validation results](pgbouncer-validation.md) for all nine retained diagnostics.
Both isolated ECS read-burst and mixed-workload repetitions were clean; the
remaining ten-environment Lambda throttles still require the AWS pilot.

## Concrete proposed deployment

Account335523638354, Mumbai, operator`surajs2`. A separate ECS service named
`clip-test-pgbouncer-ap-south-1-exp03` runs on existing host
`i-08e368391d905310e`, private IP`10.64.1.83`, port6432. It reserves1024CPU units
and256MiB. Current host registration is2048CPU/3819MiB; planned API allocation
1024CPU/2048MiB leaves0CPU/1515MiB unreserved with the pool. There is no new
EC2/RDS size, public address, DNS change, account upgrade or load balancer.

The endpoint is pinned to this existing host. Loss/replacement of that host
requires restoring/rebinding the pool before traffic resumes; do not claim host
HA. NFR-06's existing procedure stops one **API task**, not an EC2 host. The pool
is a separate service and must never be the task selected for that exercise.
Both A and B share exactly this pool. Pool CPU overhead and host placement are
part of the disclosed experiment configuration. The host OS/ECS agent still
needs CPU time: the two task limits are ceilings, not a promise of zero host
overhead. Observe actual utilization and recovery before accepting this sizing.

Clients verify the pool's private-IP certificate using a narrowly constrained
public CA bundled in both images. The CA permits only10.64.1.83 and the reserved
name`clip-pool.invalid`. CA SHA256
`933a1c326a76ad60749aafc3f14ae8bc42312387e53aaff994fca8db9a2c1504`;
leaf expires2026-11-11T13:03:01Z. Private keys remain outside Git and images.
The existing verified RDS roots secure the upstream connection. The proposed
SSM Standard SecureString`/clip/test/pgbouncer/tls` holds the leaf/key bundle
through Terraform ephemeral inputs/write-only fields. ECS execution permission
is limited to that parameter and the three original role DSNs. PgBouncer itself
has no task IAM permissions; its private files live on a4MiB tmpfs.

## Connection and transaction policy

Transaction pooling, separate original users, no forced shared role, no wildcard
database and no fallback to direct access. Backend ceilings: Identity8,
Marketplace24, Conversations4, total36. Current role limits10/32/4 and instance
limit78 remain unchanged by this plan. Normal activation must avoid overlapping
the old direct Conversations pools with all four pooled backends: use a bounded
drain/start sequence and observe actual connections. No blanket permission or
SQL-grant changes are included.

At most160 clients, one-second pool wait, three-second backend-connect timeout,
five-second statement/idle-transaction limits and one-second lock limit. The
pool establishes defaults on every physical backend. Application transactions
retain `SET LOCAL`; automatic prepared statements are disabled on pooled paths.
Migration/admin tools keep their separate direct connection and session-lock
semantics. Session expiry/revocation and authorization queries are unchanged.
Five-second content-free pool stats go to a seven-day CloudWatch log group.

Pooled Lambda now retains bounded clients (one per domain pool), just as ECS
retains bounded clients. These idle sockets do not retain RDS transactions or
backends. Checkout checks replace expired/broken sockets before business SQL;
direct-mode Lambda still uses null pools. This is part of the shared-pool
integration, not an authorization/session cache. All client/background/admin
budgets are recorded in [connection-budget.md](connection-budget.md).

Suraj subsequently selected preparation of the AWS pilot at reserved Lambda
concurrency 20, after release approval. The historical proposed public input overlay recorded 20; selected-read offload remains 100% for B and the pool's backend
ceiling remains 36. No local concurrency-20 result is claimed: the 8-GiB local
machine cannot reliably hold twenty application copies. Repeat ECS diagnostics
in isolation, preserve the ten-environment failures, then verify concurrency 20
on AWS after image/infrastructure release, smoke checks and website review.

**Read-only quota check, 2026-11-04 14:13 UTC:** Lambda reports regional account
concurrency 10, unreserved concurrency 10 and zero functions in Mumbai. Service
Quotas reports the quota as adjustable and no existing requests. Therefore the
proposed concurrency 20 is currently blocked. AWS documents a 100-unreserved
floor for reserved concurrency, so a request for regional quota 120 has been
presented for separate approval; no request, account upgrade or deployment has
been performed. Approval timing and eligibility are not established. Exact
inventory: private `aws-concurrency-20-inventory.json` and `aws-lambda-quota.json`.
See [AWS reserved-concurrency requirements](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html).

## Ordered work and gates

1. Implement the real pool, private TLS, explicit reversible app routing,
   separate ECS service, target-plan validation, pool telemetry and native tests.
2. Test transaction/role isolation, reuse, bounded queues, dead-backend recovery,
   TLS on both legs and rejection of insecure clients. Run short unchanged-rate
   A and100%B profiles against the exact final synthetic data and reviewed cases.
   Retain failures; a local check never accepts a deployed NFR.
3. Resolve any measured capacity issue. Complete relevant application/tooling,
   Terraform, format/type/boundary/security checks and independent self-audit.
4. Prepare immutable pool/API/Lambda image artifacts and the complete Terraform
   plan from current remote state. Include cleanup of the failed managed-proxy
   support resources, or explicitly account for approved temporary retention.
   The old proxy saved plan is stale and must not be applied again.
5. Present exact changes, tests, images, costs, lifetime, rollback and plan hashes
   for the required commit/publication/integration/cloud approvals. User's batch
   approval covers preparation; resource changes and exact merge retain gates.
6. Provision the pool with app routing disabled; verify actual TLS, roles,
   source database, reuse, queue counters and endpoint reachability. Then deploy
   the same reviewed app code in A/B with routing enabled and the approved API
   CPU allocation. Freeze image revisions and connection settings.
7. Verify website behavior, photo/Saved batches, search, two-account workflows,
   routing and parity. Give Suraj the website inspection opportunity. Only then
   perform approved pilot, applicable NFRs and formal comparison.

## Cost, rollback and cleanup

No additional EC2 rental; small image storage, log and parameter API usage are
still billable. Include them and the previously created Secrets Manager objects
in the ledger. Proposed temporary pool window:24hours, incremental allowance
at mostUSD2, subject to exact plan approval; whole-project gross spend remains
belowUSD200. Billing is delayed and credits are recorded separately.

Removing `CLIP_DATABASE_PROXY_ENDPOINT` restores the direct DSNs; a reviewed
direct image/configuration remains available. Do not silently fall back after a
pool failure. Preserve database content, credentials and old images. Cleanup
removes only the named pool service/task, its private ingress/egress rules,
execution role/policy, TLS parameter and owned logs/resources as approved.
Failed RDS-proxy secrets use their existing seven-day recovery period.

## Earlier evidence (preserved; current results linked above)

Private directory:`/home/suraj/src/.clip-private/pgbouncer-20261104/`.
Native tests established reuse, bounded queues, role isolation, rollback and
replacement of a killed backend. TLS test passed real encryption on both legs,
and rejected plaintext, wrong hostname and untrusted CA. Terraform validates.
The first pooled short A burst failed:2968correct/2977issued,9HTTPerrors,
24generator drops,p951954.30ms. Its `capacity-01/` raw/report/resources are retained.
No B capacity or NFR pass is inferred. Added pool instrumentation and the next
diagnostic are pending. This is a release blocker until investigated.

The half-core pool was CPU-throttled during the100%B diagnostic. At one core,
the next A burst completed3000/3000correct,0drops/errors,p95122.88ms. B still
failed while four simulated Lambda environments queued requests despite an
empty backend queue and DB usage averaging0.615cores. The harness now offers
explicit concurrency and free-environment dispatch, with local429on exhaustion;
the next check uses the planned10environments and bounded client reuse. This
local429is a diagnostic, not a claim about ALB's exact error mapping. Prior
four-environment runs remain intact; the changed model/settings are disclosed.
The new native client-reuse/stale-client and TLS suite passed7checks. Terraform
pool lifecycle mocks passed3checks after correcting mock fixture inputs/IDs.

## Refreshed provisioning plan

Saved plan SHA-256 `0ec5a8bf4864c795f6de5b42786c77c71fbb6d341260daf9437e5232a8ae88c5`,
private `provision-v2/provision.tfplan`: eight creates, twelve deletes of failed
managed-proxy support objects, one existing DB security-group update removing
unused proxy ingress. Original SSM source DSNs, application image/routing and
resource sizes stay unchanged in this provisioning phase. Pool image manifest
`sha256:8c2321845214573815181c5391f07038efaee2feccbd9815b6369d5c4a576592`.
No apply yet. A separate activation plan must bind the reviewed API/Lambda images,
the approved 1024-unit API CPU allocation, shared pool routing and unreserved ten.
