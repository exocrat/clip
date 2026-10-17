# Terraform state bucket bootstrap and recovery

This directory contains the local-backend bootstrap configuration for the CLIP Terraform state bucket. It is a preparation artifact only. No `terraform init`, plan, apply, state migration, or AWS operation is authorized by PD-15 Step 4. The current repository `.gitignore` does not yet exclude Terraform state or plans; do not initialize or apply this configuration until PD-15 Step 6 adds and verifies those protections.

## Resources prepared

The configuration is fixed to account `335523638354` and Region `ap-south-1`. It requires an exact, globally unique bucket name beginning `clip-tfstate-335523638354-ap-south-1-`; the name must be selected and checked before planning so the target is visible for review. It enables versioning, SSE-S3, bucket-owner-enforced object ownership, all four S3 Block Public Access settings, and a bucket policy denying non-TLS requests. Terraform has `prevent_destroy` on the bucket and `force_destroy = false`; these guard Terraform behavior but do not prevent a sufficiently privileged caller from deleting the bucket directly. No lifecycle expiration or Object Lock is configured. All prior object versions are retained until a separately reviewed retention/cleanup decision.

The `resource_owner` and `cleanup_review_date` inputs are required and must be set for an approved plan. The plan output must be checked to ensure it targets only the intended bucket and these controls.

## Bootstrap and state migration procedure

1. Wait until PD-15 Step 6 has added and tested ignore rules for `.terraform/`, state files, backups, and plan files. Use an isolated task checkout and confirm that no state or plan file will be staged or committed.
2. Select an exact candidate bucket name matching the required prefix and check that it is available. Before planning, verify the intended account `335523638354` and Region `ap-south-1`. No apply or provisioning is authorized by this preparation step.
3. With the bootstrap directory still using Terraform's default local backend, initialize and create a saved plan only after the static validation workflow exists. Review the exact target, plan, and checksum with the human, including access policy, expected cost, retention, rollback, and cleanup. Apply only that reviewed plan after separate explicit approval. Never apply an unreviewed or stale plan.
4. After a separately approved apply, verify the exact bucket name and account/Region, versioning, SSE-S3, public-access block, ownership controls, TLS-only bucket policy, tags, and `prevent_destroy` configuration. Do not place Terraform state or plan contents in logs, chat, or evidence.
5. Securely back up the local bootstrap state outside the repository with owner-only access. Add the S3 backend configuration for the exact generated bucket, key `bootstrap/terraform.tfstate`, Region `ap-south-1`, `use_lockfile = true`, and `allowed_account_ids = ["335523638354"]`. Confirm the required state-object and lockfile access has been approved.
6. Only after the migration plan and recovery steps have been reviewed and explicitly approved, run Terraform backend initialization with state migration. Preserve the protected local backup until remote state and locking have been independently verified. Do not use `-reconfigure` as a substitute for migrating an existing local state.

## Failure and recovery

- If bucket creation or migration fails, stop. Preserve the local state backup and any remote object versions; do not destroy the bucket, overwrite the remote state, or retry migration blindly. Ask for review of the exact local/remote state situation and the recovery action.
- If an accidental state overwrite or delete marker occurs, identify the last known-good S3 object version and obtain approval before restoring it. Then verify the recovered state and a non-applying plan before any apply.
- Never edit state JSON by hand or use `terraform state push -force`. Any exceptional state repair requires a reviewed backup, lineage/serial checks, an exact target, and explicit approval.
- Use `terraform force-unlock` only for a lock confirmed to be stale and created by your own failed operation, after verifying that no other Terraform run is active. Do not delete a `.tflock` object manually as routine recovery.
- Do not remove the bucket or permanently delete old object versions until project closeout/retention review and separate cleanup approval.

## Remote backend block to add only after bucket approval

The placeholder below is not runnable until replaced with the exact selected bucket name and approved in the bootstrap plan:

```hcl
terraform {
  backend "s3" {
    bucket              = "<approved-generated-bucket-name>"
    key                 = "bootstrap/terraform.tfstate"
    region              = "ap-south-1"
    use_lockfile        = true
    allowed_account_ids = ["335523638354"]
  }
}
```

The backend configuration must not contain AWS credentials or secret values. Keep review/approval of the resource plan and any state migration separate from the local static Terraform checks.
