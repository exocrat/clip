# ID-01 Step 2 — smoke registration and builder-resource cleanup plan request

Prepared 2026-10-23 07:30:22 UTC after Aditya verified exact image publication
and VM/root-disk cleanup. Local preparation only; no new cloud call, task
registration, cleanup deletion, deployment, compute start or email in this increment.

## Source and ownership
Aditya is current writer for Identity test root `email-smoke.tf`,
`email-smoke-container.json`, `versions.tf` and linked records on
`task/id-01-identity`. No shared role/root/service source changed.
`email-smoke.tf` owns only the new task definition and ARN output;
`email-smoke-container.json` pins image/command/non-root user/logging/disabled
provider; `versions.tf` adds a required explicit task selection flag. The full
proposal JSON is refreshed from those same reviewed container settings.

## Exact proposed non-applying action
- Approved operator/profile `adityalaxmi1`, account `335523638354`, region
  `ap-south-1`. Reverify non-root identity before any cloud action.
- Terraform 1.15.9/locked AWS 6.69.1, default workspace, Identity test root,
  existing bucket `clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0`, exact
  key `domains/identity/test/terraform.tfstate`. No shared-state access/migration.
- Read-only preflight: verify original builder terminated/root volume absent;
  remaining four resources are precisely owned by this root, profile not used by
  another instance and group not attached to any interface. Inspect existing
  ECS family to prevent duplicate ownership. Verify shared task/execution role
  IDs/trust/policy, log group, published image manifest/config digest and no
  running shared compute. Missing/conflicting facts stop, not silent adoption.
- Both explicit inputs: `builder_enabled=false`, `email_smoke_task_enabled=true`.
  No database/provider password or secret reads are needed.
- If local checks require backend reconfiguration, initialize only the existing
  approved key with no state migration. One full saved plan, `-input=false`,
  `-lock-timeout=30s`, `-detailed-exitcode`, ten-minute cap. Private 0700/0600
  artifacts, sanitized review and exact checksum. No `-target`, refresh suppression
  or automatic retries. Stop on any unexpected target/state/scope change.

## Expected managed-resource changes
Exactly one create:
`aws_ecs_task_definition.email_smoke[0]`.
Exactly four deletes:
`aws_iam_role.builder[0]`, `aws_iam_role_policy.builder[0]`,
`aws_iam_instance_profile.builder[0]`, `aws_security_group.builder[0]`.
The already terminated builder instance may be removed from state during refresh;
this is expected reconciliation, not authority to terminate another instance.
No other create/update/delete/replacement permitted; no launch, shared IAM/network,
ECR image, database, ECS service/capacity provider or application changes.

## Exact task configuration proposed for registration
Family `clip-test-identity-email-ap-south-1-id01`, EC2/Linux X86_64/bridge,
256 CPU/512 MiB, task role `clip-shared-test-api-task`, execution role
`clip-shared-test-api-execution`. Non-root user 10001; no port mappings,
secret values/references or new log group. Reuses `/ecs/clip-shared-test`.
Image is exact approved source `52186a0` and immutable URI
`335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:3ef8b13d3b102dc97e67d79d91e43eb8d4b2cc02fbabb45cf6001c8a93eddd1d`.
Command `python -m app.domains.identity.email_smoke`, workdir `/app/apps/api`.
Defaults test mode, provider disabled, no approval flag or recipient. An accidental
launch refuses before provider access. Only a separately approved run may set
SES/approval/one-recipient runtime overrides. No send authorization is implied.

## Checks and gates
Pinned `make terraform-check` passed formatting/backend-free init/validation for
all three roots. Final updated-root validate and Python JSON consistency checks
passed: exact digest, one container, disabled provider, no approval/recipient,
no ports/secrets, matching full proposal and command/workdir. `git diff --check`
passed. No application code changed; Python/browser feature checks not rerun.

Approve adopting this exact configuration/cleanup design for one non-applying
plan under the target/caps above. Exact saved-plan apply remains separate: it
would remove the four unused temporary resources and register the task only,
without starting compute or sending. Runtime test will need another exact
resource/time/cost/cleanup/send approval. Production access remains pending;
Step 2 and ID-READY remain incomplete.

## Cost, rollback and retention
Planning creates no compute/mail. Normal state/API charges only; proposed
incremental planning-request budget below USD 0.01 excludes existing retained
infrastructure. Account forecast review was explicitly deferred by Aditya;
no credit balance or zero retained cost is assumed. Preserve shared idle deadline.
If plan/apply later fails, inspect partial state and report, no automatic repair.
Restoring removed builder permissions/profile/group or removing the owned task
needs a fresh reviewed plan. Published image, shared roles/log group/network and
backend retained; no unrelated cleanup authorized. State locks must release;
never force-unlock without separate review. Keep private plan for exact review.

## Approved concurrent-work boundary — 2026-10-23 09:16:33 UTC

Aditya approved proceeding while leaving Suraj's RDS activity untouched. For this
independent Identity cleanup/task-registration plan only, RDS is outside the
idle-state requirement; no RDS operation or shared-state change is allowed.
Retain ECS service/cluster/ASG idle checks, exact resource ownership/unused checks,
image/role guards and one-create/four-delete scope. This changes no apply/run/send
approval and does not authorize interfering with Suraj's work or extending its
window. Do not stop RDS to satisfy this task. The prior preflight stop remains
historical evidence, not an unresolved requirement to force database shutdown.
