# ID-01 Step 2 — corrected live task failed; owned cleanup verified

Final runtime/cleanup evidence, 2026-10-23 10:14:29 UTC. Aditya explicitly approved one corrected
idempotent request under the one-email/one-host/45-minute/USD1 and guarded-cleanup
scope. Same private token/marker reused; schema and anonymous memory input
validated offline; fresh preflight passed. No RDS calls or secret reads.

## Actual execution
Window start 09:55:23.140122 UTC, expiry 10:40:23.140122 UTC. Exact :1 task
`arn:aws:ecs:ap-south-1:335523638354:task/clip-shared-test/f5352e809bfb4d5e87f1d72f6aff8e6f`
accepted PROVISIONING, then ran on verified new owned test host
`i-06514fe65a4232752` (expected AMI/type/private subnet, no public IP).
Task ran the exact published image and stopped 09:58:02.847 UTC with exit1 /
EssentialContainerExited. Only application log was `failed_or_uncertain`;
no unexpected log lines. No second task or send attempt performed.

SES aggregate sent count remained 1, identical to baseline; this is account-wide,
not attribution proof. Aditya reported no test email received. Delivery check
failed/pending; do not classify exit1 as harmless tooling or provider success.

## Read-only diagnosis and limits
CloudTrail GetCallerIdentity event `dbb9f148-6d0e-467f-a0b3-8d5c50c54299` at
09:58:01 UTC shows the application task role without an error. Sender domain
remains verified, DKIM on, no default configuration set; task role has no
permissions boundary or attached policies. Exact sender-scoped SES permission
simulation returned allowed with no missing context. These are not actual send
acceptance or proof of the precise failure. No policy was widened.

The smoke command deliberately suppresses provider exception text and emits a
single safe failure outcome. Exact mail-transport exception/cause therefore
unresolved; do not invent a retry classification. Before another live test,
prepare a narrowly reviewed diagnostic that exposes only safe stage/error-code
categories, never recipient/content/credentials/raw exception, and obtain fresh
approval. Existing image can potentially run a separately reviewed diagnostic
command; no new command or task is authorized by this evidence.

## Actual cleanup verified
Existing managed scaling triggered its low alarm after 15 one-minute evaluation
periods and returned ASG desired capacity to zero. No guarded manual fallback
was used. On 2026-10-23 10:14:07.756278 UTC, verified owned host
`i-06514fe65a4232752` terminated and root `vol-028a4fa0eea059363` absent;
cluster running/pending/registered zero, API service disabled and ASG desired/
instances zero. No other task/workload was stopped or host terminated manually.
Completed before the 10:40:23 UTC expiry. Task definition/image/log proof retained
for diagnostic handoff, not removed without their later cleanup approval.
Private sanitized run/identity/outcome/cleanup checkpoints:
`/tmp/clip-id01-email-corrected-0u3n2juw/`.
No stop/start/read of Suraj's RDS, service enablement, new image/source change,
extra commit or automatic resend. Step 2 and ID-READY remain incomplete.

The identity event's session was separately confirmed to match this exact task,
not merely another caller using the same role. Human no-email observation is
recorded without mailbox content. `git diff --check` passed. No source change or
new live test selected during cleanup. Next human verifies this failed integration
and cleanup result, then selects the [safe diagnostic proposal](runtime-diagnostic-next.md)
before any additional send. Do not mark Step 2 complete.
