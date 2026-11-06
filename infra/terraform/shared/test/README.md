# Shared test Terraform root

PD-16 owns the shared test-environment root and state key `shared/test/terraform.tfstate`; use the default Terraform workspace. The S3 backend points to the bucket in `infra/terraform/bootstrap/versions.tf` and the exact shared/test state key; Step 4 local checks remain backend-free. Step 5 checks local/remote state collisions before `terraform init -reconfigure`; never plan against the implicit local backend. The root uses Terraform 1.15.9 and its locked AWS provider. `deployment_phase` is mandatory with no default; `base` enables the VPC, one-AZ NAT/ECS/RDS base and the RDS-subnet-only second AZ, while `service` additionally enables the API service plus separate one-shot database-login setup and probe tasks. Backend-free format/schema validation needs no real variable values; if explicitly selecting an empty local configuration, use `disabled` only without planning against deployed state. Cloud plans use `-input=false` with reviewed phase-specific inputs. The API uses bridge port mapping 8000→18000 for SSM port forwarding and creates no inbound security-group rule. [DEC-05](../../../../docs/decisions/private-postgresql-probe-login.md) records the probe-login boundary: setup can fetch the master and probe parameters; the probe can fetch only its own credential; neither task role receives AWS permissions.

## RDS stop and easy resume

The [RDS operation guide](../../../../docs/environment/shared-test-rds-operations.md)
contains its target checks and stop/start command sequence. The last recorded cloud
state is in the [cloud inventory](../../../../docs/environment/cloud-inventory.md);
it is not a live view. The prior idle deadline and saved plan inputs are no longer
current evidence. Treat the checked-in PD-16 JSON inputs as historical templates:
refresh every target and value, prepare a new plan, and obtain approval for the
exact action before any operation. Starting RDS reuses the database and credentials
but does not enable ECS or require infrastructure recreation.

## ECS capacity lifecycle

`api_service_enabled` defaults to `false`; it sets the ECS API service desired count to zero. The ECS capacity provider starts with zero hosts and defaults to a one-host maximum. For the experiment baseline and NFR-06 recovery plan, the later [runtime capacity decision](../../../../docs/decisions/experiment-runtime-capacity.md) requires two healthy ECS tasks on separate hosts while running. Set both `api_service_desired_count=2` and `ecs_host_max_size=2` in the exact reviewed plan; the configuration refuses two requested tasks with a one-host maximum. Verify current capacity and cost before applying. Disabling the API service after workloads and one-shot tasks finish sets its desired count to zero and lets ECS drain/terminate empty hosts. Verify zero tasks and hosts; do not wait for enabled API tasks to exit first. The root EBS volume is deleted with its host. ECS scale-in may take about 15 minutes after the cluster becomes empty. One-shot tasks use the cluster's default capacity-provider strategy and can request a host while they run.

To resume after a run, first start RDS and wait until it is available. Then prepare and review a saved Terraform plan with `api_service_enabled=true`, and apply only after approval for that exact plan. After workloads and one-shot tasks finish, prepare/review/apply a separate plan retaining `deployment_phase=service` with `api_service_enabled=false`; wait for API tasks to stop and the host to drain/terminate, then verify zero tasks/hosts. If this stalls, stop and review diagnosis/cost action; do not terminate shared capacity manually. Review the account, Region, backend key, exact changes, cost, and plan checksum for each plan. Never stop or terminate the Auto Scaling group's instance directly. Stop RDS after the tasks have exited, using the reviewed operator procedure below; RDS actions need their own explicit authorization and an approved non-root identity. `aws rds stop-db-instance` and `start-db-instance` are operations, not Terraform plan changes. RDS storage and backups remain while it is stopped, and AWS may automatically restart it after seven consecutive days; the selected full-stack idle teardown is after 96 hours.

For each run, record the operator, exact hours/expiry, expected cost, and remaining USD 25 reserve before starting. If the full `shared/test` stack is idle for 96 hours, cleanup takes two separately reviewed applies: if RDS is stopped, start it only with separate authorization and wait until available because AWS does not allow modifying a stopped DB instance. Then set `db_deletion_protection=false` (default `true`) in a plan that changes no other resource, and apply only after separate review/approval. Verify protection is off. Follow the manual image-cleanup procedure below to empty and verify the exact ECR repository, then prepare a fresh full destroy plan against the updated state. Review and separately approve the checksum of each plan. The destroy review must include the no-final-snapshot behavior, ECR repository/images, and exact resources to be deleted. Never reuse a destroy plan prepared before deletion protection was disabled, and never destroy the PD-15 state backend or its versioned state during PD-16 cleanup. These instructions describe a future gated workflow; this documentation does not authorize or run any AWS operation.

## Database-task deadlines

Both database scripts allow 10 seconds to connect, 30 seconds per SQL statement or lock wait, and 60 seconds for the complete psql process, followed by at most 5 seconds to force termination. The selected immutable PostgreSQL client image must contain GNU `timeout`; verify this before approving its task definitions. The scripts fail safely if that tool is missing, override unlimited caller timeout settings, suppress client diagnostics, and return nonzero on failure or timeout. A task failure needs investigation before any retry; a timeout does not prove that no work committed. These limits bound the database client, not ECS scheduling or the complete approved cloud window.

The setup script checks effective logging in its bounded psql session before any ACL, role or credential change. It rejects statement/error/duration/transaction-sampled logging and enabled pgAudit/auto_explain logging; `log_min_error_statement` must be `panic`. Unset RDS metadata does not pass this check. The approved correction conditionally suppresses statement/error/duration logging with transaction-local `set_config(..., true)` before rechecking. Prior settings return on commit/rollback. Existing transaction sampling, enabled audit/explain logging or denied SET privileges still abort before mutation; no parameter-group changes, grants or automatic retries. Runtime RDS support remains unverified. See [DEC-05](../../../../docs/decisions/private-postgresql-probe-login.md).

## ECR retention and manual cleanup

Keep the repository and accumulated images during ordinary service stop/start cycles. Review storage usage periodically and manually remove old images when needed. Retain the exact image digests required by current deployments, restart plans and intended rollbacks. No lifecycle policy or automatic image deletion is configured.

A full 96-hour-idle teardown still removes the repository. Before that separately approved destroy:

1. Verify the operator, account, Region and exact repository from the inventory. Review its image digests and any remaining task/service references.
2. Obtain explicit approval for the exact images to delete. Periodic cleanup removes only selected unused images; full teardown must remove all images after confirming they are no longer needed.
3. Delete those approved images manually through ECR, re-list the repository, and verify it is empty. Stop on failure and inspect the result before retrying.
4. Prepare, review and apply the fresh Terraform destroy plan under the existing approval gates. Terraform then deletes the empty repository. Record image cleanup and destroy outcomes separately.

Keep Terraform's default refusal to delete a populated repository; do not bypass it with force deletion. This procedure and the [decision record](../../../../docs/decisions/database-task-deadlines-and-manual-image-cleanup.md) authorize no AWS operation by themselves.

## RDS operation templates

RDS operation templates, after confirming the instance identifier and approval. Set `approved_profile` to the operator’s explicitly approved non-root profile (the current session approved `adityalaxmi1`); do not rely on the root default. Set `approved_instance_id` to the reviewed DB identifier. Verify STS identifies the approved IAM principal in account `335523638354` before executing only the separately approved operation. These are individual templates, not a script to execute top to bottom. The CLI has no `db-instance-stopped` waiter: after stop, poll status read-only with the bounded procedure in the operation plan until `stopped`; do not treat one `stopping` response as completion:

```sh
aws sts get-caller-identity --profile "${approved_profile:?Select the approved non-root profile}"
aws rds stop-db-instance --profile "${approved_profile:?}" --db-instance-identifier "${approved_instance_id:?Select the approved DB}" --region ap-south-1
aws rds describe-db-instances --profile "${approved_profile:?}" --db-instance-identifier "${approved_instance_id:?}" --region ap-south-1 --query 'DBInstances[0].DBInstanceStatus' --output text
aws rds start-db-instance --profile "${approved_profile:?}" --db-instance-identifier "${approved_instance_id:?}" --region ap-south-1
aws rds wait db-instance-available --profile "${approved_profile:?}" --db-instance-identifier "${approved_instance_id:?}" --region ap-south-1
```

Do not run these templates during local validation or without the separate target/operation approval.

The RDS master password is supplied only to Terraform's ephemeral variable, RDS write-only `password_wo`, and base-phase Parameter Store `value_wo`. The separate, single-line probe password uses an ephemeral variable and service-phase `value_wo`. The pinned provider requires the value/version pairs whenever those resources are active, even for unchanged credentials: supply master for base plans/applies and both master/probe for service plans/applies. Retrieve existing approved SecureString versions into the Terraform child’s memory; for initial probe creation, retain its newly generated value securely until apply. Preserve version counters, check parameter metadata for drift, and never rotate as a side effect of start/stop or teardown preparation. Terraform omits ephemeral/write-only values from saved plans/state; re-supply the same values on apply and stop for a freshly reviewed plan if they change or become unavailable. Rotation/version bumps require separate approval. See [DEC-11](../../../../docs/decisions/terraform-write-only-credential-inputs.md). See [Terraform write-only arguments](https://developer.hashicorp.com/terraform/language/manage-sensitive-data/write-only). Never commit either password, include it in an ordinary variable file, print it, or put it in an output, tag, user data, task-definition environment field, or log. ECS task definitions contain only SecureString references. The setup task uses psql's `\password` prompt and suppresses SQL diagnostics; the probe task sees only the probe parameter. AWS-managed Parameter Store encryption is used, with task execution policies scoped to exact parameter ARNs. The user selected base-plan inputs: VPC `10.64.0.0/20`, NAT subnet `10.64.0.0/24`, active private subnet `10.64.1.0/24` in `ap-south-1a`, RDS-subnet-only `10.64.2.0/24` in `ap-south-1b`, `db.t4g.micro` PostgreSQL 18.6 with 20 GiB gp3, 1-day RDS backup retention (AWS accepted it in the recorded Step 6 apply), 7-day CloudWatch log retention, no final snapshot, and cleanup review date 2026-10-23. API/PostgreSQL-client image digests remain required only for the later service phase.

Run the repository's pinned backend-free checks with `make terraform-check`. For Step 5, verify the PD-15 backend/migration gates, absence of local shared/test state, complete cost/retention inputs, and explicit authorization for the non-applying plan. Initialize with `terraform init -reconfigure`, never `-migrate-state`, and do not plan against local state. For initial base provisioning, explicitly pass `deployment_phase=base` and `api_service_enabled=false`. For service deployment and later service stop/start plans, retain `deployment_phase=service`. **Never omit the phase in a cloud plan: omission fails with `-input=false`; explicit `disabled` is empty only against empty state; against populated state it proposes resource deletion. Changing `service` back to `base` also removes service-phase resources.** Preserve all approved non-secret inputs between plans and inspect every create/update/delete; a checksum identifies the reviewed artifact but does not establish that its changes are safe. The [approved phase-selection decision](../../../../docs/decisions/terraform-deployment-phase.md) removes the default; cloud plans use `-input=false`. Configuration changes invalidate earlier plan approval; review a fresh plan before any apply. Use the verified non-root `adityalaxmi1` profile for apply and other non-root cloud operations. [DEC-06](../../../../docs/decisions/terraform-planning-identity.md) records the identity decision. Each changed saved plan must be inspected and explicitly approved by exact checksum before apply. See [Terraform ownership boundaries](../../../../docs/architecture/terraform-ownership.md) and the [Terraform change workflow](../../README.md).

## Reviewed ECS image pin — ID-01 Step 2

The host image is pinned to the existing deployed `ami-0c10ee7b040aa465e` through
`local.ecs_ami_id`; ordinary IAM plans no longer refresh a mutable recommended
AMI. See the [decision](../../../../docs/decisions/shared-test-ecs-image-pin.md).
This is an approved source correction, pending fresh cloud-plan verification;
no launch-template update or compute start has been applied. Future image
upgrades and launches retain their separate approval and verification gates.

## SES sandbox controlled-recipient scope — ID-01 Step 2

The real task-role diagnostic identified a denial on the verified recipient's
SES identity. `identity-email.tf` accepts the sensitive optional
`ses_sandbox_recipient_identity_arn`, adding only that exact identity alongside
the sender domain while retaining `ses:SendEmail` and the exact FromAddress.
Pass the approved value privately through `TF_VAR_ses_sandbox_recipient_identity_arn`;
never commit/print the address or ARN. IAM and protected Terraform state retain
it; sensitivity masks normal rendered output, not state access.

Preserve this input in subsequent shared sandbox plans. Omitting it proposes
removing the added resource and can restore the sandbox delivery failure; inspect
that diff deliberately. Once SES production access/configuration is reviewed,
remove the test-recipient resource through a separately reviewed plan and verify
normal delivery. This is a sandbox test exception, not the production recipient
model. All original exact plan, role-ownership and cloud approval gates remain.


## Shared application HTTPS certificate preparation

`https-certificate.tf` adds an opt-in ACM DNS-validated public certificate for
`clip-iisc.site` in this shared root/state, because the HTTPS origin serves every
feature. It defaults disabled; no DNS/listener/compute change is included.
`https_certificate_enabled=true` requires an explicitly reviewed
`https_certificate_review_date`. The expected full certificate-phase plan adds
exactly one ACM certificate with no other changes/replacements/deletions.
Preserve current deployment phase and all existing inputs, including private
sandbox recipient, passwords' write-only versions, stopped API and pinned image.
A fresh full root plan is mandatory; stop on drift or unrelated sender-policy
changes. Do not use a targeted apply to hide those changes.

Outputs supply public CNAME records for the existing Spaceship DNS operator;
there is no assumed Route53 zone or blocking validation resource. Keep CNAMEs
for managed renewal. The certificate does not make the application available:
validation, shared listener/proxy and later deploy remain separate approvals.
`prevent_destroy` blocks accidental teardown if its flag/phase is disabled;
actual removal requires a deliberate reviewed source/cleanup change.
The certificate review date overrides historical tags for this resource only.


Applied2026-10-26: the reviewed full plan included the certificate addition plus
an explicitly approved existing SES sender-condition update to verify@; no other
resource actions. The certificate is now retained in shared state. Future plans
must preserve `https_certificate_enabled=true` and its reviewed date unless
certificate removal is deliberately reviewed; omission/default false is not a
safe continuation input. See the last recorded certificate state in the
[cloud inventory](../../../../docs/environment/cloud-inventory.md).


## Retained Identity and image runtime preparation

The shared bucket in `listings-images.tf` and scoped task/execution policies track
resources retained after the 2026-10-26 demo. Do not remove those declarations to
clean up local history: a later apply would propose deleting retained resources.
The normal API image build accepts `VITE_MICROSOFT_SIGN_IN_ENABLED` (default false).
Real runtime remains opt-in through `identity_runtime_enabled=true` and a private,
nonempty `identity_test_recipients` list of at most five. This restores a valid
disabled default instead of deploying the demo's incomplete email configuration.
No real addresses belong in source. Keep `api_service_enabled=false` until the
exact image, DB references, provider inputs and trusted HTTPS ingress are reviewed.

The current private marketplace role has no Hybrid pipeline/table privileges;
Hybrid deployment/role/model initialization remains separately reviewed work.
The approved refresh-only reconciliation recorded state serial18 with service
revision2 matching live. Before any future apply, review a fresh full normal plan
and preserve the retained certificate flag/date and original write-only versions.
Neither these local changes nor a successful local check authorizes state refresh,
remote apply, DNS changes or runtime restart. See the
[consolidated demo handoff](../../../../docs/evaluation/identity/id-01-step-12/demo-postmortem-20261026.md).


## Optional Identity HTTPS test proxy — local proposal

`identity-https-proxy.tf` defaults off. It declares one dedicated t3.micro public
proxy, fixed private peer10.64.0.10, private API SG rule, EIP/association and a
custom SSM-only role/profile with no parameter/secret reads. It requires the
observed ECS host address and explicit review date; no guessed upstream or DNS
mutation. The new API command is activated only with Identity runtime enabled:
raw access logs off, exact proxy trust if present, no forwarded trust otherwise.
Default Identity-off container command and shared instance-type default are
unchanged. The proxy schedules a compute stop after240minutes; its IP/volume and
shared ECS/RDS still need operator-reviewed cleanup. A direct proxy uses Caddy
ACME, not the retained non-exportable ACM certificate. This adds no SSH listener.

Run the registered safe mock wrapper plus normal Terraform checks before review.
No real plan/apply/start/reset is authorized by passing them. See the
[Step13 preparation and planning request](../../../../docs/evaluation/identity/id-01-step-13/README.md).

## ID-01 Step14 consumer runtime preparation — not applied

`conversations_runtime_enabled=false` and `hybrid_runtime_enabled=false` preserve
the prior default task capacity (256CPU/512MiB). Opt-in Conversations injects
`CLIP_DATABASE_DSN` from the exact SecureString
`/clip/test/conversations/database-url`; a dedicated execution-role policy reads
only that parameter. This configuration does not create the parameter/login,
set a password or grant SQL rights. Review the Step14 local SQL proposal with
Rahul before a separate exact provisioning plan.

Hybrid requires the reviewed optional AMD64 image, offline artifact contexts,
and explicit flags. Set reviewed `api_task_cpu`/`api_task_memory_mib` inputs
(at least512/2048 for Hybrid), inspect host fit and total pool connections, then
prepare/queue/activate the serving pipeline through the approved operator path.
These caps are preparation guards, not measured sizing or NFR evidence. Both
options require the real Identity profile. Existing service count, networking,
S3 scope, credentials and retained stopped resources are unchanged until an
exact cloud plan is approved and applied. No runtime startup auto-creates SQL
roles or activates a pipeline. Backend-free mock plans are local checks only.

## NFR-07 isolated restore smoke

`nfr07-smoke.tf` is disabled by default. It provisions a separate stopped service,
ALB host rule, target group and three write-only database parameters for the
restore test. Its fixed host is `restore.clip-iisc.site`; it requires the
reviewed certificate/DNS/Microsoft registration and real Identity profile.
Follow the [timed provisioning procedure](../../../../docs/evaluation/predeployment-gap-tools.md)
and approve both preprovisioning and activation plans before cloud changes.
