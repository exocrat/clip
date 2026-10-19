# PD-16 test RDS stop and resume plan

**Current status — 2026-10-19 18:23:35 UTC:** RDS is stopped after the authorized live setup/probe run. ECS tasks and ASG desired/hosts are zero; original EC2 host terminated through managed scaling. [Current shutdown evidence](../evaluation/foundation/pd-16/compute-stop-result.json). DB data, credentials and images retained. No automatic scheduled shutdown was installed; separate restart/enable-plan approval still required.

**Historical initial-stop status:** User authorized the exact stop; AWS confirmed `stopped` with matching resource ID on 2026-10-19 12:52:26 UTC. The current contributor volunteered as operator and selected stopping RDS while retaining an easy restart. Preflight verified non-root caller/account, private/encrypted/protected DB with one-day retention, zero running/pending ECS tasks and zero ASG hosts. The installed CLI rejected the nonexistent stopped waiter; bounded read-only status polling confirmed completion without repeating stop. Resume has not run and needs its separate action approval. At that historical checkpoint the personal name/contact and holding deadline were not yet recorded. The current operator is now explicitly Aditya and the accepted deadline is recorded below. Existing cleanup review date: 2026-10-23.

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

## Remaining cost and expiry

Stopping removes the DB compute portion while stopped, not NAT, allocated storage, backups/logs or backend costs. Using the proposal's recorded reference rates, 96 idle hours with compute off is approximately USD 6.21 before variable charges and scale-in tail; this is not a current bill or spending cap. RDS may automatically restart after seven consecutive stopped days. The existing policy calls for separately reviewed full-stack teardown after 96 idle hours; the user accepted the idle clock **2026-10-19 18:23:35 UTC → 2026-10-23 18:23:35 UTC** (23:53:35 IST on October 23), anchored to the last confirmed full shutdown. This supersedes the earlier unaccepted first-apply-based proposal. **Aditya** is the current operator and initiates separately reviewed cleanup by this deadline if no new approved run occurs. A new approved run updates the clock; this is not automatic deletion or advance destroy approval.

No automatic teardown/cron or restart-loop suppression is installed. The operator must review retained cost and expiry. Full teardown retains its separate start-if-needed, deletion-protection-change and fresh destroy-plan approvals, and must preserve the PD-15 backend and state versions.
