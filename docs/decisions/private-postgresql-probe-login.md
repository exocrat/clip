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
PD-16's base phase stores the master credential in a write-only Parameter Store SecureString and uses it for RDS creation. The later service phase adds the single-line probe SecureString, setup/probe task definitions, and distinct execution-role policies. Step 10 runs setup before probe and checks the privilege boundary. Verify PostgreSQL statement logging will not capture password-setting statements; the task uses psql's password prompt and emits no SQL diagnostics. The selected AWS-managed `aws/ssm` key is not a per-secret decryption boundary, so the design depends on exact SSM parameter permissions and the account's IAM policy; effective account permissions remain unverified. No secret value belongs in Terraform plans/state, task definitions, outputs, logs, or Git. See the [PD-16 task](../tasks/pre-domain-task-list.md#pd-16--review-and-provision-the-shared-cloud-test-foundation), [secret-handling record](../environment/secret-handling.md), and [shared test foundation proposal](../environment/shared-test-foundation-proposal.md).

## Approver
User in the current session; name not recorded.

## Supersedes
None.
