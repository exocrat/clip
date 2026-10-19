# PD-15 Step 6 — Local-to-S3 state migration plan

**Status:** Human-approved for one execution on 2026-10-19 08:40:21 UTC, executed, and human-verified on 2026-10-19 08:45:41 UTC. Any changed target, retry, or recovery action requires renewed review and approval.

## Exact source and destination

- Source configuration: `infra/terraform/bootstrap/`, default workspace, local state `terraform.tfstate`.
- Protected backup: `/tmp/clip-pd15-state-backup.bpPBCw/bootstrap.tfstate` (directory mode `0700`, file mode `0600`). Before migration, local state matched this backup byte-for-byte. After migration the matching local file is `terraform.tfstate.backup`; `terraform.tfstate` is a zero-byte placeholder (see execution result).
- Destination: S3 bucket `clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0`, key `bootstrap/terraform.tfstate`, Region `ap-south-1`, native lockfile `bootstrap/terraform.tfstate.tflock`.
- Backend account guard: `335523638354`; workspace: `default`.

## Read-only preflight

Checked before migration planning:

- AWS caller is account `335523638354`, using its root identity as temporarily directed. This is broad account access; replace it with a dedicated low-privilege identity after the current bootstrap work.
- The exact bucket has versioning enabled, SSE-S3 (`AES256`), and a TLS-only deny policy. Step 4's read-back verified public-access blocks and bucket-owner-enforced ownership as well.
- `ListObjectVersions` returned no versions or delete markers under `bootstrap/terraform.tfstate`, so neither the state object nor its lock object currently exists.
- The protected local state and backup are both 12,725 bytes, mode `0600`, and byte-identical. The local state contains seven Terraform addresses: six managed S3 resources and the `data.aws_iam_policy_document.require_tls` data source. The expected address list is recorded below.
- The post-migration no-change plan needs the same required inputs as the approved bootstrap apply. The exact bucket, `Owner`, and `ExpiresOn` values were recovered from the protected state into `/tmp/clip-pd15-state-backup.bpPBCw/bootstrap-verify.tfvars` (mode `0600`); values are not written to the repository or displayed.
- No Terraform process was active during preflight.
- The repository pins Terraform `1.15.9`. The current PATH executable reports `1.16.5`; the available pinned Linux ARM64 binary at `/tmp/clip-pd13-tools-ns7loycc/terraform` reports `1.15.9`. Recheck the version immediately before migration and stop if that pinned binary is unavailable or reports another version.

The bucket policy read-back shows only the TLS transport deny. It does not independently prove every effective IAM, SCP, or backend permission. If the migration or lock verification reports an access error, stop; do not change IAM or retry blindly.

## Migration action

After review and separate explicit approval for this exact action:

1. Confirm no other Terraform operation is using this root or state. Recheck caller account, destination prefix is still empty, and the private backup still matches the local state.
2. From the repository root, run `/tmp/clip-pd13-tools-ns7loycc/terraform version` and require `1.15.9`; then, from `infra/terraform/bootstrap/`, run `/tmp/clip-pd13-tools-ns7loycc/terraform init -migrate-state`.
3. Terraform may prompt to copy the existing default-workspace state. Confirm only if the displayed source and destination match the paths above. If it displays a different backend, workspace, bucket, key, or any unexpected choice, cancel and stop.
4. Do not use `-reconfigure`, `-force-copy`, `-lock=false`, `terraform state push`, or an apply. The only intended remote writes are the migrated state object and Terraform's lockfile during required verification. No infrastructure resource is created, changed, or deleted.

The migrated state is about 12.7 KB. This adds normal S3 request and storage charges in the existing bucket, with no new AWS service or compute capacity. Versioning retains the state object version; do not add an expiry rule or delete prior versions as part of this step.

## Required post-migration verification

Keep the protected local backup until every check below passes:

1. `/tmp/clip-pd13-tools-ns7loycc/terraform state list` from the bootstrap root returns exactly these seven addresses, with no missing or additional entries:

   ```text
   aws_s3_bucket.terraform_state
   aws_s3_bucket_ownership_controls.terraform_state
   aws_s3_bucket_policy.require_tls
   aws_s3_bucket_public_access_block.terraform_state
   aws_s3_bucket_server_side_encryption_configuration.terraform_state
   aws_s3_bucket_versioning.terraform_state
   data.aws_iam_policy_document.require_tls
   ```

2. A non-applying `/tmp/clip-pd13-tools-ns7loycc/terraform plan -refresh=false -lock-timeout=0s -detailed-exitcode -var-file=/tmp/clip-pd15-state-backup.bpPBCw/bootstrap-verify.tfvars` completes with exit code `0` (no changes). Its default state locking must acquire and release the S3 lock successfully; if the lock is busy or any changes are proposed, stop and investigate without applying.
3. `aws s3api head-object --bucket clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0 --key bootstrap/terraform.tfstate --region ap-south-1` confirms an object exists, has a version ID, and reports `AES256`; do not download or print its contents.
4. `head-object` for `bootstrap/terraform.tfstate.tflock` reports not found after Terraform exits. Historical lock versions or delete markers can remain because bucket versioning is enabled; do not delete them. If a lock appears active, stop and verify no operation is running. Never delete a lock object manually.
5. Confirm the protected backup remains available and mode `0600`; retain it through task closeout and until the remote state and lock checks are accepted. Terraform also created an ignored `terraform.tfstate.backup` in the bootstrap directory. It matched the protected copy; its initial mode was `0664`, so it was changed to `0600`. The zero-byte ignored `terraform.tfstate` placeholder remains mode `0600`.

## Execution result — human-verified

- Terraform `1.15.9` completed `init -migrate-state` to the approved S3 backend after the expected local-to-S3 confirmation prompt.
- Remote `terraform state list` exactly matched the seven-address local baseline. The non-applying plan returned exit code `0` with `No changes`; it exercised S3 state locking. No current `.tflock` object remained afterward.
- S3 `HeadObject` returned a 12,725-byte state object with a version ID and `AES256` encryption. Bucket versioning remained enabled.
- The protected backup remains mode `0600`; Terraform's local `.tfstate.backup` matched it and is Git-ignored. No infrastructure apply or resource change occurred.
- The human verified these results and the PD-15 task-wide local acceptance audit on 2026-10-19 08:45:41 UTC. Peer review and merge remain pending under the task PR lifecycle.

## Stop and recovery conditions

If migration fails, is interrupted, the destination changes before execution, state addresses differ, the plan proposes changes, or lock/object verification fails: stop. Preserve the local state and backup and all S3 object versions. Do not retry initialization blindly, overwrite or delete remote state, edit state JSON, use `state push -force`, or remove a lock manually. Record the exact failure without state contents and review the local/remote versions before any recovery action. Any restore, force-unlock, IAM change, cleanup, or second migration attempt requires a separately reviewed action and explicit approval.
