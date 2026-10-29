# DEC-09 — Database-task deadlines and manual image cleanup

**Date:** 2026-10-19

**Origin:** PR #7 review corrections; PD-16 Steps 7–10 and 13–14.

## Question
How should database smoke tasks stop when blocked, and how should image retention coexist with full test-environment teardown?

## Options considered
- Leave database checks without a deadline, or enforce connection, SQL/lock and total-client limits.
- Automatically purge images, or retain them across stop/start cycles and clean them manually.

## Selected choice
Bound each database client's connection to 10 seconds, each SQL statement or lock wait to 30 seconds, and total psql execution to 60 seconds plus at most 5 seconds to force termination. Require GNU `timeout` in the reviewed PostgreSQL client image. Missing tools and timeout/failure exit nonzero with safe diagnostics. This does not bound ECS task placement or replace the approved cloud window.

Keep accumulated ECR images during normal stop/start cycles, monitor storage, and clean unused images manually. Preserve current/restart/rollback image digests during periodic cleanup. Full teardown after 96 idle hours still requires explicit approval to manually delete the exact images, verification that the repository is empty, and then the separately reviewed Terraform destroy. Keep Terraform's default refusal to delete a populated repository. No automatic purge or forced deletion is selected.

## Rationale
Database checks must stop rather than hold an EC2 host indefinitely. Manual image cleanup is sufficient for the project's expected image volume and retains control over deletion.

## Implications
The [shared Terraform runbook](../../infra/terraform/shared/test/README.md), [command index](../environment/commands.md) and [accepted foundation handoff](../status/foundation-handoff.md) carry these rules. Test normal, unavailable and blocked database behavior. No AWS operation, secret access, image deletion/publication or environment teardown is authorized by this decision.

## Approver
Suraj (B), current session: agreed to DB deadlines and verified the manual-cleanup/full-teardown clarification. Numeric limits implement the proposed local smoke-check window; implementation result remains subject to step verification.

## Supersedes
The implication that Terraform itself deletes images during PD-16 teardown. Other cleanup, budget, ownership, state-retention and exact cloud-action approval gates remain.
