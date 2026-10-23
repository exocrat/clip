# ID-01 Step 2 — diagnostic runtime approval request

Prepared 2026-10-23 10:31:50 UTC. Local implementation/testing only; no new task
or email executed. Local SES delivery is human-confirmed, while ECS root cause
is unresolved. No task-definition, application image or IAM change is proposed.

## Exact bounded operation

Aditya/profile `adityalaxmi1`, account `335523638354`, region `ap-south-1`.
One task on `clip-shared-test`, capacity provider `clip-shared-test-capacity`,
exact registered definition `clip-test-identity-email-ap-south-1-id01:1`, image
`sha256:3ef8b13d3b102dc97e67d79d91e43eb8d4b2cc02fbabb45cf6001c8a93eddd1d`.
Application role `clip-shared-test-api-task`. Reuse the existing execution role,
log group and private network. No service, database, IAM, image upload or new
infrastructure definition. Existing ASG may launch at most one c7i-flex.large.

The exact command override is `python -c` followed by the complete contents of
[runtime_diagnostic.py](runtime_diagnostic.py), SHA-256
`a1ff45cff144f42804c816c7b14017976d85f6f51647f647c9d7cf6fbfdae374`.
[Request proposal](runtime-diagnostic-run.proposed.json) contains this exact source;
verify equality/hash before invocation. Overrides measure 5660 JSON characters
before replacing the empty recipient list, below ECS's 8192-character limit;
check the final private payload too. The source is transmitted in the command
rather than imported from an unbuilt image. No wrapper code download at runtime.

One generic `CLIP email delivery test` email to the previously approved verified
inbox. Inject its address privately into the environment allowlist; never save
or print it. Explicit smoke approval, test mode and SES provider remain required.
Signed role check and actual image's client factory/sender are used unchanged.
One SES attempt, no retry; 45-second process deadline includes credential/SDK I/O.
Only fixed stage/outcome/category and allowlisted service error code may be logged.
Unknown exceptions/codes stay `unclassified`; no raw payload/error/traceback.

Reserve an exclusive ECS window. Recheck signed operator/account, SES sending,
verified sender/recipient, quota, exact task image/roles/config, launch template,
AMI availability and idle ECS/ASG before launch, as described in the previous
[runtime plan](runtime-run-approval.md). Stop on mismatch or concurrent work.
RDS is excluded entirely, including inspection/start/stop/secret/database access.
Generate NEW token/startedBy marker; previous accepted request must not be reused.
Supply CLI JSON through anonymous memfd (`file:///proc/<parent-pid>/fd/<fd>`),
not the previously failing /dev/stdin mechanism. Keep raw API results in memory;
retain only sanitized task/instance/result fields. One RunTask invocation; if
uncertain, reconcile by marker and never relaunch automatically.

## Limits and prompt development cleanup

Record exact UTC start and expiry (start +45 minutes); startup limit15 minutes,
45-second application alarm, incremental cost cap USD1 excluding retained costs.
Prior recorded c7i-flex.large estimate USD0.08479/hour is historical, not current
billing; refresh before running. No budget/credit assumptions. Stop new work on
error, uncertainty or limits; complete approved owned cleanup.

Stop only this run's task on deadline/failure as necessary. After it is STOPPED,
do not wait until minute35: promptly recheck ALL tasks including provisioning,
all services' desired/pending/running counts, ASG min0/max1, and that the sole
host was launched for this exclusive run. With every guard satisfied, execute
exactly once:

```bash
aws autoscaling set-desired-capacity --auto-scaling-group-name clip-shared-test-ecs-host --desired-capacity 0 --profile adityalaxmi1 --region ap-south-1
```

Preserve ASG min/max/template, managed scaling/draining and managed alarms.
Immediately recheck guards before mutation; no force termination or termination
of another owner's workload. If conflicting work appears, do not scale shared
capacity down; retain normal managed cleanup, report conflict and seek precise
recovery approval if needed. Verify owned host terminated, root disk deleted,
ECS/ASG zero within45 minutes; no false whole-environment-shutdown claim.
Retain task definition/image/log evidence. Do not change/reset RDS's idle clock.

Development-end gate: remove prompt scale-to-zero override and verify normal
ECS managed scale-in before production. Managed 15-minute behavior stays enabled
underneath; no ECS-owned alarm is edited.

Success requires safe diagnostics, actual role-based submission, human receipt
and verified cleanup. Failure requires safe classification and cleanup, no
resend. Neither outcome alone completes Step2 or ID-READY; production access
and later Identity integration remain pending. Exact live approval is separate
from verification of this local preparation; no commit/push/merge is included.
