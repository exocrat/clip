# Shared test RDS stop and resume procedure

This procedure describes the former PD-16 target, `clip-shared-test-postgres`.
Its last recorded state is in the [cloud inventory](cloud-inventory.md), not a
live view. Verify caller, exact resource, current users and ECS capacity before
acting. Each stop or start needs its own exact approval; this procedure and any
older deadline or plan do not authorize an operation.

## Target and boundary

- Account `335523638354`, Region `ap-south-1`, environment `test`.
- Approved non-root profile for this session: `adityalaxmi1`; recheck STS before any operation. Another operator must use their separately approved profile.
- DB identifier `clip-shared-test-postgres`; recorded resource ID `db-PYRRZJPVKPGHIXDAHUWATXGH7A`. Require both to match the preflight, not just a matching name.
- Related cluster `clip-shared-test`; source-defined ASG `clip-shared-test-ecs-host`. Confirm exact identifiers before use.
- Intended mutation: stop this one existing DB instance. No delete, snapshot request, password change, IAM change, image upload, Terraform plan/apply or ECS/ASG mutation. Keep storage, backups, encryption and deletion protection. No database contents or secret values are read.
- Inspect current status first: available permits the reviewed stop; stopped means report already stopped and do not repeat; any other status, changed identity/resource, active task/instance or unexpected configuration means stop and ask. Check nobody else is using the DB before stopping it; zero ECS tasks does not prove absence of other clients.

## Preflight (read-only; perform only as part of the authorized operation)

```sh
aws sts get-caller-identity --profile adityalaxmi1 --query '{Account:Account,Arn:Arn}'
aws rds describe-db-instances --profile adityalaxmi1 --region ap-south-1 --db-instance-identifier clip-shared-test-postgres --query 'DBInstances[0].{Id:DBInstanceIdentifier,ResourceId:DbiResourceId,Status:DBInstanceStatus,Public:PubliclyAccessible,Encrypted:StorageEncrypted,Protection:DeletionProtection,Retention:BackupRetentionPeriod}'
aws ecs describe-clusters --profile adityalaxmi1 --region ap-south-1 --clusters clip-shared-test --query '{Clusters:clusters[].{Name:clusterName,Running:runningTasksCount,Pending:pendingTasksCount},Failures:failures}'
aws autoscaling describe-auto-scaling-groups --profile adityalaxmi1 --region ap-south-1 --auto-scaling-group-names clip-shared-test-ecs-host --query 'AutoScalingGroups[].{Name:AutoScalingGroupName,Desired:DesiredCapacity,Instances:Instances[].InstanceId}'
```

Require the exact non-root caller/account, exact DB ID/resource ID, private/encrypted DB with protection on and one-day retention, one matching cluster with zero running/pending tasks and no failure entries, and one matching ASG at desired zero with no instances. Missing results are failures, not zero capacity. If real services have since been deployed, use the separately reviewed service shutdown procedure first. Record safe status/timestamp summaries, not full provider output or secrets.

## Stop (requires approval for this exact target/action)

```sh
aws rds stop-db-instance --profile adityalaxmi1 --region ap-south-1 --db-instance-identifier clip-shared-test-postgres --query 'DBInstance.{Id:DBInstanceIdentifier,Status:DBInstanceStatus}'
# No db-instance-stopped waiter exists in the installed CLI. Poll read-only
# every 15 seconds, at most 40 times; never repeat the stop automatically.
attempt=0
while [ "$attempt" -lt 40 ]; do
  rds_status=$(aws rds describe-db-instances --profile adityalaxmi1 --region ap-south-1 --db-instance-identifier clip-shared-test-postgres --query 'DBInstances[0].DBInstanceStatus' --output text) || break
  [ "$rds_status" != stopped ] || break
  [ "$rds_status" = stopping ] || break
  attempt=$((attempt + 1))
  sleep 15
done
# Stop this procedure on failure/unexpected state; require stopped before closeout.
[ "${rds_status:-unknown}" = stopped ] || { printf '%s\n' 'Stop unconfirmed; inspect status, do not retry stop automatically'; exit 1; }
aws rds describe-db-instances --profile adityalaxmi1 --region ap-south-1 --db-instance-identifier clip-shared-test-postgres --query 'DBInstances[0].{Id:DBInstanceIdentifier,ResourceId:DbiResourceId,Status:DBInstanceStatus}'
```

On status-poll timeout/error, inspect a fresh read-only status and report it; do not retry the mutation, change permissions or restart automatically. Confirm stopped with the same resource ID, record UTC completion and operator, and update inventory/work log. This is an RDS operator action, not Terraform drift repair. Do not change `deployment_phase` to stop compute.

## Easy resume (separate action approval; also the rollback route)

Recheck identity/target as above; if already available, report that instead of repeating start. If stopped and the start is approved:

```sh
aws rds start-db-instance --profile adityalaxmi1 --region ap-south-1 --db-instance-identifier clip-shared-test-postgres --query 'DBInstance.{Id:DBInstanceIdentifier,Status:DBInstanceStatus}'
aws rds wait db-instance-available --profile adityalaxmi1 --region ap-south-1 --db-instance-identifier clip-shared-test-postgres
aws rds describe-db-instances --profile adityalaxmi1 --region ap-south-1 --db-instance-identifier clip-shared-test-postgres --query 'DBInstances[0].{Id:DBInstanceIdentifier,ResourceId:DbiResourceId,Status:DBInstanceStatus}'
```

Starting retains the same database/storage/credentials; no recreation or secret rotation is intended. Availability is not an authenticated SQL check. ECS remains at zero until the separately approved service plan with `deployment_phase=service` and `api_service_enabled=true` is applied. Record each run's operator, hours/expiry and budget before resuming. An approved stop does not preapprove a later start.

## Cost and cleanup

Stopping removes DB compute cost, not NAT, storage, backups, logs or backend costs.
RDS may automatically restart after seven consecutive stopped days. The old
PD-16 96-hour cleanup deadline expired in 2026; it is not a current expiry. Use
the active task's reviewed budget/window and the [DEC-12 cost note](../decisions/foundation-cost-review-precision.md)
for planning. Teardown still needs separate approvals for starting a stopped DB,
changing deletion protection and applying a fresh destroy plan. Preserve the
PD-15 backend and its state versions. No automatic teardown or restart is set up.
