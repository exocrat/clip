# ID-01 Step 2 — controlled-recipient SES authorization correction

2026-10-23 17:11:43 UTC. Aditya directed urgent diagnosis/fix/verification and
approved all proposed plans. Enhanced actual diagnostic identified the denied
resource as the controlled recipient identity. Exit1/AccessDeniedException; no
other cause claimed. Its host/root were removed and ECS/ASG zero verified
17:10:41.527682 UTC; RDS calls0 in that runtime window.

## Source/target and minimal change

Writer/operator Aditya, task/id-01-identity; shared path reservation limited to
infra/terraform/shared/test/identity-email.tf and related setup/evidence records.
Account335523638354/profile adityalaxmi1, ap-south-1. Existing policy
clip-shared-test-identity-email on clip-shared-test-api-task remains owned by
shared/test state, not attached/mutated by a domain Terraform root.

Source adds optional sensitive ses_sandbox_recipient_identity_arn input, exact
account/region/email-identity validation with wildcard refusal. Existing statement
Resource becomes sender domain plus this one controlled verified recipient ARN.
Only ses:SendEmail, same no-reply@clip-iisc.site FromAddress condition; no broad
managed policy, identity wildcard, SES administration or secret permission.
Real recipient is supplied privately in process environment, not source or logs.
It remains in access-controlled IAM/Terraform state; sensitive masks rendering.
Preserve this private input on later sandbox plans. After production-access and
configuration review, deliberately remove it and verify delivery anew.

## Exact plan/apply boundaries

Pinned Terraform1.15.9/AWS6.69.1, existing S3 backend shared/test/terraform.tfstate,
default workspace. Full refresh-enabled plan, no -target or refresh suppression.
Preserve service phase, API disabled, all existing approved inputs and write-only
secret versions1. Refresh reads shared AWS metadata including RDS; no start/stop,
SQL connection, schema/data access or database update. Existing approved master/
probe SecureStrings supplied only ephemerally in child memory because provider
requires them on unchanged write-only resources; no logging/persisting/rotation.

One private saved plan; review checksum/source hashes and exactly one inline
policy UPDATE, zero other managed changes. Reject drift, replacements or any DB,
network, task-definition, host/template, service or IAM role change. Recheck
operator/backend/source/state and idle ECS window before exact-plan apply.
No substitution or automatic retry. Verify attached policy exact two resources,
unchanged sender condition, state/lock and unchanged compute after apply.
Request budget target USD0.01 excluding retained costs;10-minute plan/apply bounds.
Rollback is a reviewed plan removing the exact optional resource, not deleting
shared role or other permissions. No implicit rollback after partial failure.

After successful correction, one separate corrected verification run within the
user-approved fix/verification sequence: same :1/image/command guards, one email,
45-minute/USD1 cap, one host maximum, new token/marker, prompt guarded cleanup.
Human receipt still required. Failed verification stops further sends. Production
access, later Identity flows, ID-READY, commits/push/merge remain outside this fix.
