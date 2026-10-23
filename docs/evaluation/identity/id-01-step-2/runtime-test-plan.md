# ID-01 Step 2 — proposed bounded ECS email test

Preparation only. Recipient verification succeeded; no publication, task
registration/start, deployment or test message is authorized by this document.
The [task definition proposal](runtime-task-definition.proposed.json) contains an
explicit unresolved image placeholder and is not an executable deployment input.

## Scope and purpose
Exercise the actual SES adapter under `clip-shared-test-api-task`, not an
operator's credentials. One generic synthetic message to the one human-selected
verified recipient; no OTP, password, account creation or database access.
Application output is only `submission_accepted` or `failed_or_uncertain`.
Acceptance is not delivery; Aditya must confirm receipt and sender privately.

## Source, image and publication gates
1. Human verifies this local command/plan increment. Preserve existing dirty
   documentation; review the exact source/dependency changes before committing.
   Normal milestone PR/independent review and eventual merge requirements remain;
   this increment cannot claim ID-READY. Arrange independent review using
   `docs/prompts/peer-review-prompt.md` for the eventual handoff.
2. Identify a reviewed source commit. Build a Linux AMD64 image using the existing
   Dockerfile and allowlisted `git archive` context; include locked dependencies
   and API source only. No recipient/config/credentials in build context/layers.
   Validate image architecture, UID 10001, module availability, production startup
   safeguards and denied smoke invocation with no credentials/network/send.
3. Separately approve publication of that exact validated image/tag to existing
   `335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api` and verify
   immutable remote digest. No new ECR repository; do not overwrite tags.
   Record the reviewed source/image manifest digest before task planning.

## Task ownership and registration gate
Proposed family `clip-test-identity-email-ap-south-1-id01` is exclusive to Identity;
manage it through the Identity test Terraform root/state, consuming reviewed
shared identifiers. Do not manually register an unmanaged revision or edit the
shared API service/task definition. Review the new domain-root design, backend
and exact no-apply task-definition plan before separate apply approval.
Only one new ECS task definition; no new cluster, service, IAM role/policy,
network, database, queue, scheduler or logging group. Task/execution roles and
log group are reused exactly as proposed. Resolve role/cluster/ECR permissions
read-only; stop rather than silently extending IAM.

## Exact proposed run boundary — requires separate approval
- Account `335523638354`, region `ap-south-1`, operator/profile `adityalaxmi1`.
- Existing cluster `clip-shared-test`, capacity provider
  `clip-shared-test-capacity`, at most one EC2 host (`c7i-flex.large`, existing
  shared max-size 1) and one 256 CPU/512 MiB test task. No task public listener,
  port mappings or new ingress. RDS and API service stay off throughout.
- Review pinned AMI availability/security suitability before launch; no implicit
  upgrade. Recheck account, current budget headroom, idle resources, exact task
  revision/digest/role and SES sender/recipient verification. Stop on mismatch.
- Runtime overrides: explicit `CLIP_EMAIL_SMOKE_APPROVED=true`, email provider
  `ses`, one-address JSON allowlist, test mode. Supply recipient privately from
  approved local configuration, never repository artifacts or printed commands.
  Recipient is task configuration visible in restricted ECS metadata/audit;
  application logs/evidence exclude it. No static AWS keys/profile overrides.
- Command verifies container-role credentials and signed STS account/role before
  dispatch. A 45-second process alarm covers credential lookup and submission;
  SES connect/read timeouts 3/5 seconds, one total SDK attempt. No retry, fallback,
  secondary recipient or automatic rerun after failure/uncertainty.
- One `RunTask` request, no service enablement. Startup limit 15 minutes; abandon
  and clean up if task cannot run. One send maximum, task deadline 45 seconds,
  total operator window 45 minutes including capacity scale-in. No load test.
- Proposed incremental run budget cap USD 1 excluding existing retained charges;
  refresh pricing/headroom before final approval. Historical foundation estimates
  are not current billing evidence. Stop new work on error or budget/time breach;
  cleanup remains required. No RDS startup or new runtime infrastructure.

## Cleanup/rollback included in final run approval
Inspect task outcome/stop reason without raw exception, body or recipient output.
Stop the owned task at deadline if still running. Let the existing capacity
provider scale the host to zero; verify cluster tasks, ASG desired/instances zero
and original RDS stopped. If scale-in misses the window, report actual status and
obtain precise shared-resource recovery approval; do not claim automatic cleanup
or change shared ASG settings without approval. Do not reset the existing idle
clock based solely on planning. Deregister/remove the owned temporary task
revision through a reviewed domain-root removal plan; image retention/removal
must be explicitly approved. Preserve other images, state, roles and resources.

## Acceptance evidence
Approved source revision, image/task digests, caller-role assertion success,
submission outcome, Aditya's delivery observation, one-message count, redacted
logs and zero-compute cleanup. No email/token/body/recipient in repository proof.
Simulator-only acceptance cannot replace inbox receipt. Production access remains
separately pending; Step 2 and ID-READY stay incomplete until required real gates.
