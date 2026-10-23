# ID-01 Step 2 — exact temporary builder plan review

2026-10-23 07:05:28 UTC. Aditya approved the concrete builder design and one
non-applying domain plan; deferred broader budget/forecast review to later.
No apply, VM launch, source upload, remote build or image push has occurred.

## Exact saved plan and source
Private plan `/tmp/clip-id01-builder-plan-aa0f7ct5/builder.tfplan`.
SHA-256 `c4367471d67ad0fd90873484e01a5688a31c62f738c135087e4117cec9c7442d`.
Terraform 1.15.9 / AWS 6.69.1. Adopted root source/lock hashes are in
[builder-plan-source-hashes.json](builder-plan-source-hashes.json); application
build inputs remain exact reviewed commit `52186a0466feb24ffb855d9f019c78cd5a17aa39`.

Target account `335523638354`, region `ap-south-1`, non-root operator/profile
`adityalaxmi1`, default workspace, Identity-owned root
`infra/terraform/domains/identity/test`, existing state bucket and exact key
`domains/identity/test/terraform.tfstate`. Backend initialized after collision
checks found no state or resources under the planned names. No migration.

## Observed plan
Exactly five creates and no updates/replacements/deletions:
- `aws_iam_instance_profile.builder[0]`
- `aws_iam_role.builder[0]`
- `aws_iam_role_policy.builder[0]`
- `aws_instance.builder[0]`
- `aws_security_group.builder[0]`

One private `t3.small`, pinned Amazon AL2023 AMD64 AMI
`ami-088fb12f8e8397f06`, subnet `subnet-0c9df7ababd0154bc`, no public IP/SSH;
IMDSv2 required; HTTPS egress only. No source-defined ingress. The AWS provider
leaves ingress computed until creation: verify actual empty ingress before build.
Encrypted 20 GiB gp3 root, delete on termination. OS shutdown terminates; bootstrap
arms the one-hour timer before installing Docker. Role has only described SSM
communication and existing-repository ECR capability, no SES or project secrets.

Original RDS stopped/ECS cluster/service and ASG zero-capacity preflight passed.
No shared state/resources changed. Native source archive manifest derives from
`52186a0`; contains no recipient/credentials. State lock confirmed absent (404).
Local Terraform format/backend-free validation passed for all three roots.
`git diff --check` passed. The first inspection helper hit a missing computed
ingress key; inspected the same saved plan with correct computed-field handling,
without a second plan or source change. This is not ingress-runtime evidence.

## Exact proposed apply and bounded build — approval requested
Apply only the saved plan/checksum above after checking exact source/lock hashes,
identity/backend/workspace/state freshness, absence of collisions and unchanged
idle shared compute. No substitute plan or automatic retry. One apply, ten-minute
limit. Reject stale/changed plan or any different scope. No DB credentials needed.

After apply, verify instance AMI/type/subnet, no public IP/ingress, encrypted
DeleteOnTermination disk, exact role and termination behavior; verify the SSM agent
and expiry timer within ten minutes. Stop if a check fails. Transfer only the
allowlisted gzip archive via bounded SSM chunks, validate its manifest checksum,
then execute [the proposed build script](builder-proposal/build.sh.proposed) once.
The script builds natively with a 20-minute timeout, checks architecture/non-root
UID/imports, default-denied smoke command and normal isolated liveness. It uses
no recipient, secrets, email provider calls or public listener. Source transfer
and remote script are constrained to this one new builder; no other managed node.

Budget: same USD 1 incremental cap, one instance for at most one hour. The
[design](builder-plan.md) records rate/traffic assumptions and retained-cost
exclusions. Aditya will review account forecast later; no credit balance is
assumed. Preserve the existing shared infrastructure cleanup deadline.

Include termination of only this new builder and deletion of its root disk if
checks/build fail, on completion after approved artifact handoff, or by one-hour
expiry. Confirm termination/volume deletion. Do not leave it running for a delayed
approval. Timer is a safeguard, not a replacement for verification. If image push
is not approved before expiry, terminate and report the unpublished image lost;
do not extend runtime or push automatically. Remaining role/profile/policy/group
cleanup uses a separately reviewed exact Identity-root removal plan. Never delete
shared networking, ECR, state, roles, ECS resources or RDS for builder cleanup.

This approval would cover exact plan apply, one source upload/build/validation,
and termination of that owned VM/disk within the approved window. It excludes
ECR image push, Git push/merge, application task registration/start, deployment,
RDS/ECS startup and email sending. After build, present the exact image/tag for
separate ECR publication approval. Any changed resource/cost/permission plan
requires renewed approval.
