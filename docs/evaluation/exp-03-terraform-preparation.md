# EXP-03 Terraform preparation

This is a local implementation and review record, not permission to create,
change or delete AWS resources. Rahul owns the EXP-03 Terraform work by user
direction. The shared root and its existing state remain owned as recorded in
[Terraform ownership](../architecture/terraform-ownership.md); affected-domain
and independent review still apply.

**Current direction:** Selected Listing reads go directly through the ALB. The
HTTPS listener defaults to ECS. In B, a higher-priority GET/path rule sends
selected Listing browse, Hybrid search and detail requests between ECS and a
Lambda target group using the configured fixed weight. Other methods and routes
stay on ECS. The ALB gets invoke permission scoped to the Lambda target group;
the ECS task role does not invoke Lambda. ALB weights do not provide
capacity-aware fallback: throttled or failed Lambda requests are recorded as
failures, with no same-request retry on ECS.

`infra/terraform/shared/test/exp03-lambda.tf` adds an opt-in configuration to
the existing shared test root. When disabled it creates no EXP-03 resources.
When enabled it uses the existing VPC, NAT route, ECS service and RDS; creates
a second public ALB subnet, an HTTPS ALB and an ECS target group. Configuration
A leaves the listener on its ECS default and creates no Lambda function.
Configuration B also creates a Lambda image function, scoped runtime role,
seven-day log group and Lambda target group, registers the function, and grants
the ALB permission to invoke it. A selected-read listener rule forwards only
`GET /api/listings` and single-UUID `GET /api/listings/{listing_id}` to Lambda
and ECS at the explicit weight. Multi-value headers are enabled. Other paths and
methods continue to the ECS default action. Stickiness is disabled for the
request-mix pilot. There is no ECS Lambda SDK invocation or fallback.

The IAM policy lists only the three fixed SSM parameter ARNs for application
startup. VPC ENI management requires wildcard EC2 resources; an explicit
`lambda:SourceFunctionArn` deny prevents function code from using those EC2
operations. The image contains the model and interpreters; the Terraform inputs
contain no password, cookie or SSM value. ECS and database security-group changes
remain shared-resource mutations and require exact plan and affected-owner review.
The launch template gets an additional temporary ECS ingress group; this does
**not** attach it to an existing EC2 instance or replace that instance.

## Required explicit inputs

- A run ID, expiry date, declared spend cap at or below USD 10, and bounded
  runtime in minutes. Tags record these values; **they are not an automatic
  spending or shutdown control**.
- A second-AZ public subnet CIDR, an issued project-account certificate ARN,
  and the declared run/budget/runtime/expiry inputs. Configuration B also needs
  an immutable project ECR Lambda image digest, Lambda memory, reviewed reserved
  concurrency and `exp03_selected_reads_lambda_weight_percent` from 0 to 100.
  The Lambda timeout is fixed at five seconds; the design ceiling is 2 GiB and
  20 reserved executions. Those maxima are not proof of memory fit or safe
  database capacity. Use `null` weight for A; the pilot's B weights are 100, 75,
  50 and 25 percent Lambda.
- The existing shared root's full reviewed inputs, including real Identity and
  Hybrid ECS settings, its image digest and safe access to existing secret
  references. Do not put secret values or real contacts into source, logs or
  plan review artifacts. Never use incomplete input defaults against real state.
- `exp03_selected_reads_lambda_weight_percent=null` for A. Set an explicit
  approved weight for B; changing it changes the ALB listener rule. Review the
  exact saved plan and verify the applied listener/target group before traffic.

The root guard requires the recorded `10.64.0.0/20` VPC and its three existing
`/24` subnet inputs, disallows choosing one of those managed subnets for the new
ALB subnet, and requires a declared cap/window. Recheck **all live VPC subnets**
for conflicts immediately before any change. The current snapshot showed only
`10.64.0.0/24`, `10.64.1.0/24` and `10.64.2.0/24`; `10.64.3.0/24` is a
candidate, not an approval or a guarantee that it remains free.

## Evidence and remaining gates

At 2026-11-02 UTC, read-only AWS metadata under non-root `clip-project` in
account `335523638354`, `ap-south-1` showed: the shared API service desired and
running at zero; `clip-shared-test-postgres` stopped and private; the named ECS
host and HTTPS proxy stopped; no CLIP-named load balancer; and the existing
`clip-iisc.site` ACM certificate issued and not attached. The shared ASG had
min/desired zero, max one and all its processes suspended, including Launch and
Terminate. The stopped ECS host is `t3.micro`, below the 2 GiB ECS task setting
required by the existing Hybrid guard. A launch-template change does not resize
or update that existing host. The exact approved rollout must preserve or
explicitly restore its original instance type, network groups, protection and
ASG suspension state; do not assume an automatic host replacement or terminate
the retained shared instance. Check the actual ECS registration and task
readiness, then verify the new group was removed at cleanup.

Read-only free-plan metadata reported USD 154.11 remaining credits, subject to
AWS billing delay and service eligibility. The user's separate **USD 10 maximum**
for this work still applies. Existing NAT, storage, IP and logging charges can
continue independently. A bounded plan must estimate both incremental and
relevant baseline charges, reserve headroom, define spend/time stop conditions,
and have a cleanup fallback that works if the local operator is interrupted.
This configuration does not implement such a fallback yet.

Repository history records the synthetic reference dataset in isolated database
`clip_next06_reference`, with its runtime role previously inactive. The existing
Listings SSM parameter's target has **not** been read or verified against that
database. Do not copy data, change grants or infer dataset parity; verify both
paths and the accepted fingerprint under a separately approved, scoped plan.
The public certificate, external DNS mapping, ALB-to-ECS trust, Lambda Web
Adapter headers/host, real sessions, database connection budget, model memory,
ECR permissions and real output parity are also unverified. An accepted dataset
record, a synthetically passing mock plan or a health check does not resolve them.

Before any paid or mutating operation, prepare one concrete plan specifying
exact resources, images, configuration, runtime, request limits, public
exposure, secret access, cost and credits, rollback, retained evidence and
cleanup verification. Obtain the separately required exact approval. In
particular, disabling EXP-03 later can propose destruction and a shared ECS
service/launch-template update; inspect the **full** saved plan and never apply
an unreviewed or targeted plan to hide unrelated drift.

## Local validation

The `.tftest.hcl` suite uses a mock AWS provider and synthetic inputs. It checks
disabled behavior, A/B route shape, required inputs, declared limits and subnet
rejections. The local check used a temporary copy, `terraform init
-backend=false -lockfile=readonly`, then `terraform validate` and `terraform
test` with AWS credential environment variables removed. No AWS provider call,
remote state access or real apply occurs. Mock plans cannot prove live security
groups, effective IAM, health, source identity or cleanup.

AWS references: [Lambda VPC permissions and function-code deny](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html),
[ALB forwarded headers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html),
and [Terraform security-group rule warning](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_security_group_egress_rule).
