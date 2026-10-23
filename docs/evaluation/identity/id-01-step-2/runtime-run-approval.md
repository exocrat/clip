# ID-01 Step 2 — exact one-task, one-email runtime approval request

Prepared 2026-10-23 09:35:46 UTC after Aditya verified task registration and full
builder cleanup and directed continuation. Read-only preparation only. No task,
host, API service or database started, no message sent. No Terraform source change.

## Exact target and message
Operator Aditya, non-root profile `adityalaxmi1`, account `335523638354`, region
`ap-south-1`. Reserve one exclusive ECS test window beginning after approval,
record exact UTC start and expiry (start + 45 minutes) before the request. Shared
ECS/capacity changes are serialized; this is not permission to interfere with
another operator. Leave Suraj's RDS work entirely outside this operation: no RDS
calls, stop/start, schema/data access, secret retrieval or database cleanup.

One RunTask request using exact definition
`arn:aws:ecs:ap-south-1:335523638354:task-definition/clip-test-identity-email-ap-south-1-id01:1`,
cluster `clip-shared-test`, explicit `clip-shared-test-capacity` strategy
base/weight 1, count 1, execute-command disabled. No launchType shortcut.
Image fixed to verified digest
`sha256:3ef8b13d3b102dc97e67d79d91e43eb8d4b2cc02fbabb45cf6001c8a93eddd1d`,
source `52186a0`, task role `clip-shared-test-api-task` and reviewed execution
role. No latest revision/image, changed command or extra recipient.

Private runtime overrides: test mode, SES provider, explicit smoke approval and
exactly one human-selected verified inbox. No address committed in this request,
logs or evidence. One fixed subject `CLIP email delivery test`; generic body from
the approved image says it contains no verification code or account action.
No account/OTP/password/contact operation. No second send or automatic retry.
The [proposal wrapper](runtime-run.proposed.json) is deliberately not directly
executable as CLI input and contains an empty recipient placeholder.

## Read-only facts and final preflight
Preparation snapshot:
- SES production access false, sending enabled, enforcement HEALTHY, 200/day and
  1/second; aggregate sent count 1, not attributed to this test. Sender domain/DKIM
  and selected recipient verified. Recheck remaining quota before sending.
- Task definition :1 ACTIVE, exact reviewed image/command/roles and disabled
  defaults. Reverify signed caller, policy/trust and image/config digest.
- Cluster running/pending/registered hosts zero; API service desired/running/
  pending zero. ASG `clip-shared-test-ecs-host` min0/max1/desired0, no instances.
  Capacity provider ACTIVE, managed scaling ENABLED target100, step min/max1,
  live warmup0, draining enabled and managed termination protection disabled.
- Shared launch template `lt-0327bb81cb3269f0b`, version1, c7i-flex.large, AMI
  `ami-0c10ee7b040aa465e`, private subnet `subnet-0c9df7ababd0154bc`, encrypted
  30 GiB delete-on-termination root. AMI available/x86_64, OwnerAlias amazon,
  ECS publisher `591542846629`, deprecation 2028-10-15. Initial generic Amazon
  Linux-owner assumption was corrected after inspecting the actual ECS image;
  no AMI or launch-template change. This is provenance/availability evidence,
  not a claim of independent vulnerability scanning.

At execution recheck every target/role/config and idle ECS/ASG condition. Stop if
other tasks, desired service work, hosts, a concurrent ECS operator or mismatches
appear; never clear someone else's tasks to make the preflight pass. Published
image, task definition, existing networking/policies/provider remain unchanged.
No new cluster/service/role/scheduler/NAT/security group/resource definition.

## Bounded execution and privacy
Generate one unique clientToken/startedBy run marker, retain only safe IDs. Send
request JSON to the CLI over stdin; capture provider output only in memory and
extract task/status fields without storing overrides/recipient. On uncertain
RunTask response, discover by that run marker and inspect; do not issue another
request. Reject API failures or more than one resulting task. Save approved UTC
window, exact task ARN and any newly launched host ID for cleanup provenance.

Managed scaling may launch one existing c7i-flex.large host (ASG maximum1); startup
limit 15 minutes. One 256 CPU/512 MiB container, no ports/ingress/execute-command.
Verify image digest, expected host/subnet/no public address, task-role binding
and placement; report any readiness mismatch. The command has a 45-second process
alarm including task credential discovery and provider I/O, 3/5-second socket
timeouts and one total SES attempt. No script, role, template, scaling-policy,
AMI or application-service changes. No retry/fake fallback after uncertainty.

Poll to STOPPED and inspect only safe exit/outcome fields and the content-free
log stream `/ecs/clip-shared-test`, prefix `identity-email-smoke`. Do not persist
raw DescribeTasks overrides/CloudTrail message payloads or recipient. AWS-restricted
ECS metadata/audit necessarily receives the destination configuration; application
logs/evidence exclude it. Allow only fixed `submission_accepted` or
`failed_or_uncertain` application outcomes. Never print credentials, message body,
recipient or raw provider errors. Exit0/accepted proves adapter submission after
signed task-role verification, not inbox receipt. Aditya then confirms receipt
and sender privately without forwarding the email or sharing verification codes.

## Exact cleanup and guarded fallback included in requested approval
Stop only this run's task if still active at startup/execution deadline or on
failure/uncertainty. No second task/send. Let existing managed scaling return the
new host to zero; verify actual termination/root-disk deletion and ASG/cluster
capacity zero. Scale-in can take many minutes; keep monitoring within the window.
Do not stop unrelated tasks, drain another owner's host or alter RDS/API service.

Proposed guarded backstop, explicitly part of this approval request: if by minute
35 the owned task is STOPPED but the one host has not scaled in, reverify no other
RUNNING/PENDING/PROVISIONING tasks, no desired service work, ASG min0/max1 and that
the sole instance launched during this exclusive run. Only under all these guards,
set desired capacity of `clip-shared-test-ecs-host` to 0 once using
`SetDesiredCapacity`; preserve min/max, template, managed-scaling policies and
other settings. Then verify that exact owned host terminated and its root volume
deleted before minute45. Terraform ignores runtime desired capacity in this
shared root; this is a bounded runtime cleanup action, not source reconfiguration.
If any other workload/owner appears, stop only our task and report the conflict;
do not force shared scale-in. Seek precise recovery approval rather than claiming
cleanup or extending the window. This backstop is not authorized until this exact
run plan is approved. No unreviewed termination of other instances is permitted.

Keep task definition/image/log evidence for review; deleting those needs a later
reviewed cleanup plan. All builder resources are already removed; no builder
recreation or shared infrastructure teardown. With concurrent RDS activity, do
not claim full-environment shutdown or independently reset its shared idle clock.
Record only the owned ECS test window/result; shared deadline/other operator's
cleanup remains coordinated separately.

## Cost and acceptance
Current AWS Price List SKU `PJEXMS8DQB62Z58U` gives Mumbai Linux shared
c7i-flex.large USD 0.08479/hour. Forty-five minutes approximately USD 0.06359;
30 GiB gp3 over that time approximately USD 0.00285 using recorded USD 0.0912/
GB-month and 720-hour month. One-GB NAT allowance at USD 0.056/GB adds USD 0.056,
about USD 0.123 before mail/log/request/tax/variable charges. Existing retained
NAT/RDS/storage costs excluded. Proposed incremental run cap USD 1; this is an
operator limit, not an AWS hard spending cap. Budget forecast review remains
deferred by Aditya; no credit/zero-cost assumption. Stop new work at limits,
complete authorized owned cleanup and report delayed billing separately.

Success needs one actual role/adapter submission, safe logs, human inbox receipt,
and verified owned task/host cleanup. Failed/uncertain submission or missing inbox
receipt remains pending and must not trigger resend. Sandbox production access
remains a separate gate, and this test does not implement Identity schema/API/UI,
accept ID-READY or finish ID-01.

Approve exactly one task/one-message run and the described existing-host startup,
owned-task stop and guarded idle-host return-to-zero, within 45 minutes/USD 1.
No DB action, additional resources, API service enablement, new image upload,
application feature implementation or other send is included.

## Primary references
- [Standalone tasks and provisioning](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/standalone-tasks.html)
- [Managed scaling behavior](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/managed-scaling-behavior.html)
- [RunTask capacity strategy and token](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_RunTask.html)

## First invocation outcome — 2026-10-23 09:49:29 UTC

The explicitly approved first CLI invocation failed; no task/host observed and
no automatic retry. Offline validation identifies `/dev/stdin` JSON parsing as
reproducibly failing while an anonymous memory-file transport passes. See the
[result](runtime-attempt-result.md) and [fresh corrected-request approval](runtime-retry-approval.md).
The former stdin transport instruction above is superseded only if that fresh
retry is approved; all resource/send/cost/cleanup boundaries remain unchanged.
