# DEC-05 — Dedicated low-privilege PostgreSQL probe login

**Date:** 2026-10-19

**Origin:** PD-16 Steps 4, 8, and 10.

## Question
Which database identity should the one-shot PostgreSQL connectivity probe use?

## Options considered
- Reuse the RDS master login, which would give the probe administrative database access.
- Create a separate login for the probe, which adds a one-time setup task and a second credential.

## Selected choice
Create `clip_test_probe` in the synthetic `clip_test` database through a separate one-shot setup task. Give it LOGIN, connection limit 2, and only explicit CONNECT on `clip_test`; set `NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS`. Revoke the test database's default PUBLIC CONNECT and TEMPORARY grants and the `public` schema's default PUBLIC CREATE grant before granting the probe login. Verify it has no role memberships, database create/temp access, schema create access, or table/sequence data privileges. The probe task receives only this login's SecureString.

The setup task receives the master and probe SecureString references and creates the login once. Its task execution role can read only those two parameters; the probe task execution role can read only the probe parameter. Both task roles have no AWS permissions. Use psql's `\password` prompt so the cleartext probe password is not sent as SQL, suppress SQL diagnostics, and log only a safe success/failure message. The approved operator runs the fixed task definitions without command, image, or environment overrides.

## Rationale
The connectivity check needs to prove authentication and `SELECT 1`, not database administration. Separate task roles and parameter scopes prevent the routine probe from receiving the RDS master credential. Removing the new test database's broad default grants makes the probe's effective database privileges match its limited explicit grant. Future test/application logins must receive their own explicit grants.

## Implications
PD-16's base phase stores the master credential in a write-only Parameter Store SecureString and uses it for RDS creation. The later service phase adds the single-line probe SecureString, setup/probe task definitions, and distinct execution-role policies. Step 10 runs setup before probe and checks the privilege boundary. Verify PostgreSQL statement logging will not capture password-setting statements; the task uses psql's password prompt and emits no SQL diagnostics. The selected AWS-managed `aws/ssm` key is not a per-secret decryption boundary, so the design depends on exact SSM parameter permissions and the account's IAM policy; effective account permissions remain unverified. No secret value belongs in Terraform plans/state, task definitions, outputs, logs, or Git. See the [accepted foundation handoff](../status/foundation-handoff.md), [secret-handling record](../environment/secret-handling.md), and [shared test Terraform root](../../infra/terraform/shared/test/README.md).

## PD-16 Step 10 revision — 2026-10-19

User approved a runtime logging guard after RDS metadata returned unset values. Check effective settings in the same bounded psql session before any ACL/role/password changes; fail closed on statement logging, duration/transaction sampling, failed-statement logging (`log_min_error_statement` must be `panic`), or enabled pgAudit/auto_explain logging. The initial check-only revision rejected live settings before mutation. User then approved transaction-local suppression: conditionally use `set_config(..., true)` for error-statement (`panic`), statement (`none`) and duration/sample-duration (`-1`) logging, then retain the full effective-setting guard. Commit/rollback restores prior values; no parameter group, role defaults, grants or other connections change. Existing nonzero transaction sampling still aborts, because sampling may already have selected the transaction at BEGIN; enabled pgAudit/auto_explain also remains a blocker. Missing SET privileges abort before mutation without grants/fallback. Deployment and rerun each retain explicit approval gates. Existing psql password prompting still prevents cleartext SQL, while this guard also protects the password verifier from statement logs. [PostgreSQL logging settings](https://www.postgresql.org/docs/18/runtime-config-logging.html) and [psql password handling](https://www.postgresql.org/docs/18/app-psql.html). [Transaction-local setting lifetime](https://www.postgresql.org/docs/18/sql-set.html). This is a PD-16-specific check, not a complete audit of every external logging agent.

## Approver
User in the current session; name not recorded.

## Supersedes
None.
