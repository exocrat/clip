# ID-01 Step 2 — non-applying SES permission plan request

Prepared 2026-10-23 05:45:52 UTC. Source patch reviewed and approved by Aditya;
cloud planning/apply/live send remain separately gated.

## Exact proposed planning action
- Operator Aditya, approved interactive profile `adityalaxmi1`; verify STS account
  `335523638354` and non-root identity. Region `ap-south-1`, shared test environment.
- Terraform 1.15.9, AWS provider 6.69.1; root `infra/terraform/shared/test`, default
  workspace. Existing S3 bucket `clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0`,
  key `shared/test/terraform.tfstate`; inspect backend metadata before use. If the
  prior backend-free local checks require initialization, use `init -reconfigure`
  only with this exact existing backend; never migrate state or plan locally.
- Reserve writer Aditya on `task/id-01-identity`, file
  `infra/terraform/shared/test/identity-email.tf`. No other shared writer/open PR
  observed at the source-change checkpoint.
- Read-only identity, state/backend, IAM, SES, capacity and parameter metadata
  preflight; confirm domain/DKIM status, sandbox state and existing task role.
  Read existing master/probe SecureStrings only into child-process memory for
  required ephemeral Terraform inputs: `/clip/test/database-master-password` and
  `/clip/test/database-probe-password`. Never print, persist, rotate, regenerate,
  or change versions. Stop if access or current versions are uncertain.
- Reconcile all existing non-secret inputs with the deployed state and accepted
  shutdown records. Preserve `deployment_phase=service`,
  `api_service_enabled=false`, zero service/host capacity, images, secrets, dates,
  tags, network and database settings. No `-target` or `-refresh=false` shortcut.
- One saved `plan -input=false -lock-timeout=30s -detailed-exitcode`, bounded to
  ten minutes, private external directory 0700 and artifacts 0600. Inspect locally
  without printing state/secret-bearing output; report sanitized changes/checksum.
  Verify credentials are absent from saved/rendered review artifacts.

## Expected scope and stop conditions
Expected one create: `aws_iam_role_policy.api_identity_email[0]`, attaching
`clip-shared-test-identity-email` to `clip-shared-test-api-task`. SendEmail only,
verified domain resource, exact `no-reply@clip-iisc.site` From condition. No
network exposure, deployment, capacity increase, email or provider-account change.
Stop for wrong identity/backend/workspace, nonzero compute against the expected
idle checkpoint, unavailable secrets, lock timeout, any unrelated update,
replacement/deletion, or any plan count other than this one policy create.
Do not apply or repair unexpected drift automatically.

## Cost, rollback and retention
No new runtime resource is provisioned by planning. Normal state/SSM/API request
charges may apply; target incremental planning-request budget below USD 0.01,
excluding existing retained infrastructure spend. One plan, no load or concurrency.
Temporary S3 locking is released on normal exit; inspect lock state after failure,
never force-unlock without separate review. Preserve private plan for review/apply;
remove it after acceptance/abandonment through the approved local cleanup path.
Source rollback is removing only the new policy resource before apply. After an
approved future apply, permission removal requires a new reviewed plan/approval.
Existing compute shutdown and idle-cleanup deadline remain unchanged by planning.

## Approval requested
Authorize only the above preflight, in-memory existing credential reads, exact
backend initialization if needed, and one non-applying plan. Apply, compute
startup, deployment, recipient verification messages and test email remain excluded.

## Revised source scope — 2026-10-23 06:03:11 UTC

Aditya approved pinning the existing deployed AMI after the first plan exceeded
scope. The source now uses the [approved image pin](../../../decisions/shared-test-ecs-image-pin.md).
Request renewed approval for one fresh plan under the same target, credential,
backend, stopped-compute, ten-minute, cost, privacy and stop conditions above.
Expected scope remains exactly one SES policy create. The prior saved plan is
not an apply candidate; do not reuse it or bypass refresh/target other resources.
