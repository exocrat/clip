# ID-01 Step 2 — real task-role SES authorization denial diagnosed

Recorded 2026-10-23 16:57:21 UTC; Aditya (A), branch task/id-01-identity,
reviewed diagnostic source committed at faf6c69. Aditya explicitly approved the
[exact runtime plan](runtime-diagnostic-approval.md). Renewed local login after
preflight expiration; repeated all guards before one live invocation.

## Preflight and execution

Approved operator/account335523638354, region ap-south-1; exact task :1,
immutable image digest, application/execution roles, disabled default container
settings and sender-scoped policy matched. No unexpected role boundary or
attached managed policy. Verified sender/controlled recipient, DKIM and sending
health; sandbox/production-access false, account-wide sent baseline2 (not
attribution evidence). All shared ECS services/tasks/hosts and ASG were idle.
Pinned ECS AMI available, correct publisher/architecture, launch template and
private subnet matched. Current AWS catalog c7i-flex.large rate USD0.08479/hour.
Diagnostic wrapper SHA and exact command matched the approved source.

Window start 2026-10-23T16:53:18.302041+00:00; expiry 2026-10-23T17:38:18.302041+00:00.
One new marker/token, one RunTask invocation with private anonymous-memory JSON.
Task `arn:aws:ecs:ap-south-1:335523638354:task/clip-shared-test/8d59687bbf7f446d84591adf7a81f1e6` accepted and ran on owned host `i-093fdd05f7b394ef5`.
Exact image digest
`sha256:3ef8b13d3b102dc97e67d79d91e43eb8d4b2cc02fbabb45cf6001c8a93eddd1d`
verified. Stopped 2026-10-23T16:55:57.259000+00:00, exit1, EssentialContainerExited.
The only log record was:

```json
{"outcome":"failed_or_uncertain","stage":"ses_submission","category":"permission_denied","error_code":"AccessDeniedException"}
```

No unexpected lines, raw exception, address, message content, credential or
provider response retained. One submission attempt; SDK retry disabled; no resend.

## Conclusion and limits

The real wrapper passed settings, signed task-role identity and actual SES client
creation, then SES rejected the submission as AccessDeniedException. This confirms
authorization denial under the application task role; successful local operator
delivery does not establish that role's effective authorization. Prior IAM
simulation allowed the reviewed sender scope but did not predict this actual
service rejection. Exact denied resource/condition or policy layer remains
unresolved because raw provider messages are intentionally excluded. Do not
assert a specific missing permission, widen Resource to wildcard, or blame
network connectivity/credential discovery based on this result.

## Prompt cleanup verified

After STOPPED, repeated guards across all tasks/services and ASG min0/max1
confirmed the sole host belonged to this run and no other work needed capacity.
One approved SetDesiredCapacity(0) invocation followed promptly; no alarm or
managed-scaling/draining configuration changed. At 2026-10-23T16:57:09.886355+00:00:
owned host terminated, root `vol-07e5d27895688b25a` deleted, cluster tasks/registered
hosts and ASG desired/instances zero. No other workload stopped. RDS calls0;
no DB secret, data, inspection or lifecycle action. Managed15-minute behavior
remains unchanged underneath; development-end removal of prompt-cleanup override
is still a release gate. Completed within45-minute/USD1 approved bounds; actual
billing is delayed and no measured spend is claimed.

Image/task definition/log proof retained, builder remains removed. Private
sanitized metadata/controller checkpoint: `/tmp/clip-id01-diagnostic-kx45689b`. No new image, Terraform/app
source change, IAM mutation, commit, push or merge. Next human verifies this
diagnostic/cleanup result, then selects a focused read-only authorization audit
and reviews any concrete permission/configuration proposal. Permission changes
and another send need separate approvals. Step2 and ID-READY remain incomplete;
SES production access is still pending.

## Read-only authorization audit — 2026-10-23 17:02:14 UTC

At Aditya's request for a fix, inspected current task role and SES setup without
mutation or send. Role has exactly the reviewed inline sender policy, no managed
policy/boundary. Sender domain verified, no configuration-set association and no
identity resource policies. SES has two identities; no separately configured
no-reply sender-address identity. CloudTrail management-event lookup for SendEmail
over16:50–17:00 UTC returned no events; this is not proof no request occurred.

Independent single-resource IAM simulations with the exact FromAddress context:
sender-domain ARN allowed; sender-address ARN and controlled-recipient ARN each
implicitDeny, no missing context keys. Initial multi-resource simulation produced
one aggregate denial; separated resource checks avoid misattributing that result.
These simulations cannot identify which resource SES actually evaluated or prove
that adding sender/recipient resources fixes the live request. AWS's documented
SES identity-scoping guidance permits domain identities; absence of explicit
address scope is therefore a lead, not a confirmed configuration defect.

Recommended next diagnostic must classify the denied action/resource and denial
reason from the SDK response in memory, emitting only approved resource classes
and reason flags, never arbitrary text or inbox address. Then prepare the exact
minimal Terraform-managed policy/configuration correction for review. Do not add
Resource wildcard, broad SES managed policies, or recipient identity permission
solely because the simulator denies an ungranted resource. New live diagnostic
requires reviewed command/approval; current task remains stopped/cleaned up.

Reference: https://docs.aws.amazon.com/ses/latest/dg/control-user-access.html
and https://docs.aws.amazon.com/service-authorization/latest/reference/list_sesv2.html.
