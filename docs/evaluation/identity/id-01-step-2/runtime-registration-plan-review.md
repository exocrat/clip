# ID-01 Step 2 — exact task registration and temporary-resource cleanup plan

2026-10-23 09:21:09 UTC; Aditya approved proceeding with RDS excluded from the
idle condition, leaving Suraj's database activity untouched. Generated one full
non-applying plan after fresh independent ownership/unused-resource/image and
ECS service/cluster/ASG idle preflight. No RDS calls or secret-value reads.
No apply, registration, resource deletion, task start or email send occurred.

## Exact saved plan
Private file:
`/tmp/clip-id01-smoke-registration-plan-zt8xjq6e/registration-cleanup.tfplan`.
SHA-256: `9ab6ac28c11664c096b63bc434b2d5b7903928bb52b34adb61093473a6c2f1bf`.
Terraform 1.15.9 / AWS 6.69.1, Identity state serial before plan 2.
Source/lock/container-file hashes:
[runtime-registration-source-hashes.json](runtime-registration-source-hashes.json).

Account `335523638354`, `ap-south-1`, IAM profile/user `adityalaxmi1`, default
workspace, root `infra/terraform/domains/identity/test`, existing PD-15 state
bucket, key `domains/identity/test/terraform.tfstate`. No shared-state change.
Explicit inputs `builder_enabled=false`, `email_smoke_task_enabled=true`.

## Observed managed-resource scope
One create: `aws_ecs_task_definition.email_smoke[0]`.
Four deletes:
- `aws_iam_instance_profile.builder[0]`
- `aws_iam_role.builder[0]`
- `aws_iam_role_policy.builder[0]`
- `aws_security_group.builder[0]`

No update/replacement or other create/delete. Deleted IAM objects exactly
`clip-test-id01-amd64-builder`; group exactly `sg-00f275fda4e0f5104`. Profile
has no live association and group no ENI. Original builder/root remain absent;
Terraform's refresh reconciliation is expected, not a new termination request.
No shared API role, network, RDS, ECR image, ECS service/capacity-provider change.

New task family `clip-test-identity-email-ap-south-1-id01`, EC2/AMD64/bridge,
256 CPU/512 MiB, source `52186a0` image pinned to verified registry digest
`sha256:3ef8b13d3b102dc97e67d79d91e43eb8d4b2cc02fbabb45cf6001c8a93eddd1d`.
Existing task/execution role ARNs and log group verified. Container config equals
source after ignoring environment-list ordering: provider alphabetically sorts
names without changing values. Initial strict list-equality assertion failed;
inspected this same saved plan and verified every actual field/value, without
rerunning or changing source. No approval/recipient values or port mappings.
Email provider disabled by default; registration does not launch a task.

## Checks/evidence
Fresh caller/backend/workspace/ownership/in-use/image checks passed; Identity
root only. Original ECS service/cluster and ASG idle guards retained. RDS excluded
per explicit user direction, not implicitly treated as stopped. No DB credentials
required or read. State lock released (404); saved artifacts private. Existing
pinned local Terraform/JSON checks remain valid; `git diff --check` passed.

## Exact apply approval requested
Apply only this saved path/checksum after rechecking source/lock hashes,
identity/backend/workspace/state freshness, exact five-address action map,
unused cleanup profile/group, task-family ownership, image/role configuration
and ECS/ASG idle state. Leave RDS untouched and outside this condition. Stop on
any changed target/source/state or new dependency; no substitute plan or retry.
One apply, ten-minute cap; no secrets or new compute resources.

After apply, verify exact task registration/roles/command/digest/disabled defaults,
four named resources absent, state/lock result and unchanged ECS/ASG capacity.
Do not call RunTask or change service, host, DB, image or recipient identities.
Task definition may be ACTIVE in ECS but no task is launched. A live one-message
run, its compute window and cleanup need their own later exact approval.

Normal state/API charges only for this proposal; incremental request budget
target below USD 0.01 excludes retained infrastructure. Account forecast review
remains deferred by Aditya; no credit assumption. Existing shared idle deadline
unchanged. Keep registered definition and published image for bounded test;
subsequent removal/recreation requires another reviewed plan. If apply fails,
inspect/report partial state, do not repair or restore builder roles automatically.
This apply cannot accept Step 2 or ID-READY: actual runtime delivery and production
access remain pending, along with later Identity implementation gates.
