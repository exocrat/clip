# PD-16 Step 10 — runtime logging guard plan

**Status:** Non-applying plan passed; exact apply approval pending. RDS remains stopped; no database task has run.

- Account/profile/region: `335523638354` / non-root `adityalaxmi1` / `ap-south-1`, shared `test`.
- Terraform 1.15.9, default workspace; existing PD-15 S3 backend and shared/test state, serial 5.
- Saved plan: `/tmp/clip-pd16-logging-guard-plan-uxf5xsb0/service.tfplan` (private external directory).
- **SHA-256:** `3ed95de0d608185564c012d1f118973750d051b1f153501dbe0c9d1006773d50`.
- **Change:** replace only `aws_ecs_task_definition.db_role_setup[0]` (one deregistration, one registration). Old setup revision 1 is deregistered; the new definition embeds the reviewed guard. API service, probe definition, RDS, network, permissions, credentials and capacity are unchanged. Container configuration matches except the command and omitted empty optional AWS arrays.
- Both credentials re-supplied ephemerally, version counters unchanged; absent from captured output, rendered plan and decompressed saved-plan entries. Lock released (404). [Safe result/source fingerprints](logging-guard-plan-result.json).

## Behavior and limits

`setup-db-role.sh` checks effective logging within its existing bounded psql session, before ACL/role/password changes. Unsafe statement/error/duration/transaction-sampled logging or enabled pgAudit/auto_explain logging aborts setup. `log_min_error_statement` must be `panic`, preventing failed statements from recording the password verifier. It does not change logging or retry automatically. This can reject ordinary PostgreSQL defaults; the actual RDS session has not been checked. On rejection, review a narrow logging decision separately rather than bypassing the guard. Existing timeouts and safe output remain unchanged. This checks PostgreSQL logging controls, not every possible external audit agent. [DEC-05 and source references](../../../decisions/private-postgresql-probe-login.md).

Shell syntax (`sh -n`) and whitespace (`git diff --check`) passed. No tests added/run; runtime SQL acceptance remains pending.

## Approval boundary, cost and recovery

Apply only this checksum after rechecking caller, source fingerprints, state, credentials and target. This replacement launches no task or host and adds no service/storage resource; existing host/NAT/storage charges continue. The existing two-hour window remains **2026-10-19 17:17:08–19:17:08 UTC**, with no automatic shutdown or extension. The previously reviewed estimate was approximately USD 0.35 for two fully active hours before variable/tail/continuing charges; latest recorded eligible estimated credits USD 179.49, budget actual USD 0.04/forecast USD 1.232. No new billing refresh is claimed.

On failure stop and inspect actual state/registered revisions; do not retry, restore the unsafe script or run SQL automatically. Recovery or rollback needs a fresh reviewed plan. Retain the PD-15 backend/state and ECR images. Existing shutdown/idle teardown gates remain unchanged. Approval of this plan does not authorize RDS start or setup/probe execution; those need exact separate action approval after the guarded revision is verified.
