# PD-16 Step 10 — transaction-local logging correction

**Status:** Approved correction implemented; non-applying plan passed. Exact apply and rerun approvals pending. RDS and one API host remain running.

## Exact plan

| Field | Value |
|---|---|
| Account/profile/region | `335523638354` / non-root `adityalaxmi1` / `ap-south-1`, shared test |
| Tool/backend | Terraform 1.15.9, default workspace; existing PD-15 S3 bucket `clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0`, key `shared/test/terraform.tfstate`; state serial 6 |
| Saved artifact | `/tmp/clip-pd16-local-logging-plan-krsifpkk/service.tfplan` (private) |
| **SHA-256** | **`2930ea6ec8b2a538b7f6620967837ac0a5e6f548bb1223ac022b13b111bd2d26`** |
| Changes | Replace only `aws_ecs_task_definition.db_role_setup[0]`: one deregistration and one registration; no other create/update/delete |

Only embedded setup command changed after normalizing AWS empty optional arrays. Images, roles, secret references, environment, logs, API/probe, credentials, RDS/network/capacity remain unchanged. Both credentials supplied ephemerally with unchanged versions and absent from captured output, rendered/saved plan; lock released (404). [Result/source fingerprints](local-logging-plan-result.json).

## Script behavior and limits

`setup-db-role.sh` conditionally uses `set_config(..., true)` to suppress statement/error/duration logging within its existing transaction, then runs the full effective-setting guard before ACL/role/password changes. Error-statement threshold is `panic`, ordinary statement logging `none`, and duration/sample-duration thresholds `-1`. Prior settings return at commit/rollback; no parameter group, role default, other connection, privilege grant or global logging change. Existing timeouts/secret references/diagnostic suppression remain unchanged.

Initially nonzero transaction sampling still aborts (the transaction may already have been selected), as do enabled pgAudit/auto_explain logging, denied SET privileges or a failed effective-setting check. Actual RDS permission support is unverified; this plan registers code without executing it. Stop for diagnosis on any failure, with no automatic retries, guard weakening or grants. [DEC-05](../../../decisions/private-postgresql-probe-login.md) links the PostgreSQL setting-lifetime/logging sources.

Shell syntax (`sh -n`) and whitespace (`git diff --check`) passed. No tests added/run, no SQL rerun. Earlier failed revision 2 result remains preserved; no ACL/role/password changes occurred in that attempt.

## Apply boundary, costs and recovery

Recheck checksum/source/state/caller/credentials before applying only this plan. It replaces a definition and launches no task/host; existing RDS/one-host/NAT/storage charges continue. Original window still ends **2026-10-19 19:17:08 UTC**, no automatic shutdown or extension. Prior reviewed full-active reference approximately USD 0.35/two hours before variables/tail/continuing costs; last eligible estimated credits USD 179.49, budget actual USD 0.04/forecast USD 1.232. No new billing refresh claimed.

On apply failure preserve state/artifacts and inspect actual registered revisions before any repair. Recovery requires a fresh reviewed plan; do not restore unsafe code or run tasks automatically. Preserve PD-15 backend/state and ECR images. Existing shutdown/teardown approvals remain separate.

Apply approval **does not authorize another SQL attempt**. After registered revision/source verification, propose its exact new revision for one setup run, followed by probe revision 1 only on safe success. New task execution needs explicit approval; no old revision/overrides/retries. RDS is already available and needs no further start.
