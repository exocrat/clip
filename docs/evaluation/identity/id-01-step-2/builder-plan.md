# ID-01 Step 2 — proposed temporary AMD64 AWS builder

Prepared 2026-10-23 06:55:31 UTC. Aditya explicitly approved the local checkpoint
commit and selected a small AWS AMD64 VM in `ap-south-1`. Source committed locally
at `52186a0466feb24ffb855d9f019c78cd5a17aa39`; Black pre-commit hook passed,
worktree was clean immediately afterward. No push, image build/upload or VM launch.
This document and [Terraform proposals](builder-proposal/) are the concrete
resource/permission/cleanup design; cloud init/plan/apply still need exact approval.

## Target and ownership
- Account `335523638354`, region `ap-south-1`, AZ `ap-south-1a`, operator Aditya,
  non-root profile `adityalaxmi1`; reverify identity before planning/apply.
- Identity-exclusive resources, owned in `infra/terraform/domains/identity/test/`,
  default workspace, existing PD-15 bucket
  `clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0`, state key
  `domains/identity/test/terraform.tfstate`. Check state/object and resource-name
  collisions before init; stop on unknown existing owner/state. Do not touch
  shared state or duplicate shared networking/roles.
- Current writer Aditya on `task/id-01-identity` for the proposed Identity root;
  apply proposal files only after human design verification. Provider locked to
  AWS 6.69.1, Terraform 1.15.9; reuse the existing verified lock file.

## Exact proposed resources
Five creates: `aws_iam_role.builder[0]`, `aws_iam_role_policy.builder[0]`,
`aws_iam_instance_profile.builder[0]`, `aws_security_group.builder[0]`,
`aws_instance.builder[0]`. Explicit required `builder_enabled=true`; false is a
separately reviewed cleanup request, not a safe unattended default.
- One `t3.small` (AMD64, 2 vCPU/2 GiB), Standard CPU credits to avoid surplus
  credit billing. On-demand, no Spot interruption risk or extra instances.
- Verified available Amazon-owned AL2023 x86_64 AMI `ami-088fb12f8e8397f06`,
  owner `137112412989`, HVM, root `/dev/xvda`. AMI is pinned; no mutable lookup
  in the proposed root.
- Reuse VPC `vpc-04b0cc01cbf93cd17`, private subnet
  `subnet-0c9df7ababd0154bc` (`10.64.1.0/24`) and existing NAT
  `nat-0d7fefbad586f4bce`; subnet route confirmed active. No public IP, SSH key,
  inbound ports, new VPC/subnet/NAT or network rule in shared infrastructure.
  New dedicated security group permits outbound HTTPS only; VPC DNS resolver
  remains available. Stop if package setup needs any unreviewed egress change.
- One encrypted 20 GiB gp3 root disk, DeleteOnTermination true, IMDSv2 required,
  metadata hop limit 1. OS shutdown behavior terminate, not stop.
- Dedicated role/profile `clip-test-id01-amd64-builder`. Inline permissions allow
  SSM agent heartbeat/message channels (wildcard resources required by these
  actions), ECR upload/read-check actions only on `clip-shared-test-api`, and
  ECR registry auth token. No SES send, project Parameter Store read, DB secret,
  application task-role assumption, IAM management or resource deletion permission.
  Do not substitute the broad shared ECS instance profile. Granting ECR capability
  does not authorize pushing any image before exact artifact approval.

## Build/run boundaries
- Recheck budget, target/backend/names, AMI and shared RDS/ECS idle state; if any
  resource exists under these names, reconcile ownership instead of duplicating.
- One full non-applying Terraform plan, ten-minute limit, private 0700 directory /
  0600 artifacts and exact checksum review. Init only the approved domain key;
  no migration/force-unlock, no `-target` or refresh suppression. Expect exactly
  five creates, no shared changes/replacements/deletes. No secrets required.
- Separate exact saved-plan apply approval creates the VM. Bootstrap first arms
  a 60-minute systemd shutdown timer, then installs Docker and starts Docker/SSM.
  Require timer/termination-behavior/delete-on-termination verification before
  uploading source or building; if unavailable, stop and terminate the owned VM
  under the reviewed cleanup authorization. Boot/SSM deadline ten minutes.
- Operator sends only the allowlisted compressed source archive through bounded
  SSM command chunks (source is non-secret), checks its SHA-256 remotely, and
  extracts into a private temporary context. No Git credentials, dotenv, recipient,
  AWS tokens or local caches uploaded. No additional S3 artifact bucket needed.
- Build exactly revision `52186a0466feb24ffb855d9f019c78cd5a17aa39`, using the
  existing Dockerfile, pinned uv/runtime dependencies, native Linux AMD64.
  Proposed local tag `clip-api:id01-amd64-52186a0466fe`. One build, 20-minute
  timeout, no automatic retry or package/architecture fallback.
- Validate image platform, Python architecture/version, UID 10001, SDK/module
  presence; run default-denied smoke invocation with container network disabled
  and no recipient/credential/approval overrides. Optionally normal loopback-only
  process health under the existing image procedure. Never send email here:
  builder is not the ECS task role and the command must reject it.
- Return only sanitized image ID/size/source hash/check results. Before ECR push,
  obtain separate approval of exact built image/tag/repository; upload and digest
  verification are a later action. No API service/task deployment, application
  role use, RDS start or controlled email send under builder approval.

## Cost and budget evidence
AWS Price List read-only query on 2026-10-23:
- Mumbai Linux shared t3.small SKU `QYQXSB5RHTECU8TP`: USD 0.0224/hour.
- Mumbai gp3: USD 0.0912/GB-month; 20 GiB for one hour approximately USD 0.00253
  using a 720-hour month, before taxes/rounding.
- Existing Mumbai NAT data processing: USD 0.056/GB. A two-GB transfer allowance
  gives USD 0.112 variable processing; existing NAT hourly retention is separate.
One hour compute plus disk plus that traffic estimate is approximately USD 0.137,
excluding existing infrastructure, tax and any internet transfer/storage costs.
Proposed incremental budget cap USD 1 and lifetime one hour; no billing hard cap
is created, so operator monitors/stops work and does not assume delayed billing
is current usage. Do not leave the VM running for an approval indefinitely.

Budget snapshot: USD 5.336 actual incurred spend, USD 319.408 forecast against the
USD 200 annual reference. The forecast exceeds that reference and reflects the
account's retained-cost trajectory; this is not a refreshed credit balance or
proof that builder costs are free. Existing USD 50 actual-spend review point and
USD 25 reserve rules still apply. Preserve existing retained-infrastructure idle
cleanup deadline; this standalone builder does not authorize keeping it longer.

## Cleanup and rollback approval scope
Include termination of this one new builder and deletion of its root disk in the
future exact launch/build approval. The one-hour timer is a safeguard, not sole
proof of cleanup; verify instance terminated and volume absent. If source/image
publication is not approved before expiry, allow termination and report lost
unpublished artifact; do not silently extend runtime or push to preserve it.
New temporary profile/role/policy/group cleanup is a separate exact domain-root
removal plan (`builder_enabled=false`), preserving state/backend and unrelated
resources. No snapshots or retained disks. Never terminate shared ECS hosts or
RDS as builder cleanup. Stop on unexpected scope/failure and report partial state.

## Current local checks and approval requested
Proposal formatting and backend-free initialization/validation passed using
Terraform 1.15.9 / locked AWS 6.69.1 in an isolated temporary directory. No domain
backend initialized and no VM/IAM/security group created. `git diff --check` passed.

Approve adopting this concrete design in the Identity root and performing its
read-only collision/preflight checks, exact backend initialization and one
non-applying plan. No provisioning/apply, source upload/remote build, ECR push,
application runtime task or email is authorized by that planning approval.

## Provider references
- [T3 specifications](https://aws.amazon.com/ec2/instance-types/t3/)
- [SSM agent message APIs](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-setting-up-messageAPIs.html)
- [Scoped ECR push permissions](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push-iam.html)
- [EC2 shutdown/termination behavior](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html)
