# ID-01 Step 2 — exact SES permission plan review

2026-10-23 06:13:13 UTC; Aditya (A), `task/id-01-identity` based on `44cd8ff`,
reviewed uncommitted source. Approved sensitivity correction implemented and fresh
non-applying plan completed. Result awaits human verification/exact apply approval.

## Exact saved plan
- Private path: `/tmp/clip-id01-ses-final-plan-8smeuxtm/ses-permission.tfplan`.
- SHA-256: `baa80880c96c379289a90a482a888aac9cc5d087aba40e211a17677a18695e9a`.
- Terraform 1.15.9, AWS provider 6.69.1; state serial before plan 8.
- Account `335523638354`, region `ap-south-1`, IAM profile/user `adityalaxmi1`.
- Root `infra/terraform/shared/test`, default workspace; S3 bucket
  `clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0`, key
  `shared/test/terraform.tfstate`.

## Verified scope
Exactly one create: `aws_iam_role_policy.api_identity_email[0]`, policy name
`clip-shared-test-identity-email`, existing role `clip-shared-test-api-task`.
Policy JSON exactly matches the human-reviewed proposal: only `ses:SendEmail`,
resource `arn:aws:ses:ap-south-1:335523638354:identity/clip-iisc.site`, exact
`ses:FromAddress` condition `no-reply@clip-iisc.site`.
Zero other updates, replacements or deletes. Existing AMI and its sensitivity
metadata are preserved; no launch-template/ASG change remains. Removed obsolete
data-source state is not an AWS managed-resource deletion.

Fresh preflight: original RDS stopped, ECS cluster/service zero tasks, ASG zero
hosts/desired capacity, verified SES domain/DKIM, sending enabled/healthy,
production access false. Secret versions matched 1; no rotation. Existing
credentials absent from saved-plan members, rendered output and captured logs.
Artifacts have private permissions; state lock confirmed absent (404).

## Checks and changed source
`base.tf` now uses `sensitive(local.ecs_ami_id)`: same pinned image, preserving the
prior SSM-derived sensitivity marker. Terraform format check initially flagged
alignment; formatted the changed block and reran pinned `make terraform-check`:
format/backend-free initialization/validation passed for both roots.
`git diff --check` passed. Decision/work-log updated; no unrelated runtime code
changed in this increment. Source hashes for the exact root are recorded in
[plan-source-hashes.json](plan-source-hashes.json).

## Proposed exact apply — separate approval required
Apply only the saved path/checksum above after rechecking checksum, source hashes,
provider lock, account/backend/workspace and state freshness. Preserve all inputs,
service phase and disabled API service. Re-read existing version-1 master/probe
SecureStrings only into child memory to supply required ephemeral values; never
persist/print/rotate them. One apply, ten-minute cap, no concurrent operator.
Stop for stale plan, changed source/state/credential versions, wrong identity,
missing input, or any scope mismatch. Do not generate/apply a substitute plan.

Expected addition is IAM permission only; no compute startup, deployment,
network exposure, new email identity or sending is authorized. No additional
runtime resource cost is expected; ordinary API/state request charges remain,
with a planning/apply request budget target below USD 0.01 excluding existing
retained infrastructure costs. After apply, verify exact attached inline policy,
state result/lock release and unchanged zero compute. No email test is included.

Policy stays until separately reviewed removal/project cleanup. Reversal is a
new reviewed plan removing this one inline policy; do not delete the shared role
or other permissions. Existing idle cleanup deadline is unchanged. A failed or
partial apply requires inspection and reporting, not an automatic retry/rollback.
No apply, AWS resource change, deployment or email send occurred in this checkpoint.
Step 2 remains partial until permission/runtime delivery and production gates pass.
