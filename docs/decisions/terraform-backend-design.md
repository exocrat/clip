# DEC-02 — Terraform S3 backend and state recovery design

**Date:** 2026-10-17

## Question
Which remote Terraform backend, locking, encryption, recovery, access, naming, and environment-separation approach should CLIP use for four contributors working in the approved AWS account?

## Options considered
- Local state: no new cloud service, but each contributor would need to coordinate state copies manually and could lose or overwrite the latest state.
- HCP Terraform: supports shared remote state and run coordination, but adds an external service, account/access setup, and potentially additional cost.
- Amazon S3 backend: keeps state in the selected AWS account and supports state locking with an S3 lockfile. DynamoDB-based S3 locking was considered but is deprecated by current Terraform documentation.

## Selected choice
- Use an S3 backend in account `335523638354`, Region `ap-south-1`, with Terraform's native S3 lockfile enabled (`use_lockfile = true`). Do not use DynamoDB for locking.
- Enable S3 bucket versioning. Recover from accidental state replacement/deletion by selecting a prior object version through a reviewed recovery procedure; do not directly edit state or use `terraform state push -force`.
- Use SSE-S3 for server-side encryption at rest. S3 applies SSE-S3 to new objects by default at no additional encryption charge. Do not add a customer-managed KMS key for backend encryption in this design.
- Use separate root configurations and state-object prefixes for bootstrap, shared test infrastructure, and domain-exclusive infrastructure. Use the default Terraform workspace only; do not use workspaces as a security or ownership boundary.
- Proposed bucket-name pattern: `clip-tfstate-335523638354-ap-south-1-<unique-suffix>`. The actual globally unique name is deferred until the reviewed bootstrap plan.
- Proposed state-key patterns, with exact keys to be frozen in PD-15 Step 5:
  - `bootstrap/terraform.tfstate`
  - `shared/test/terraform.tfstate`
  - `domains/<domain>/test/terraform.tfstate`
- Backend authentication must use the approved AWS CLI/SDK credential chain for the selected account. Do not put credentials, tokens, or sensitive backend configuration in Terraform files, command arguments, or saved plans. Configure the backend's `allowed_account_ids` for account `335523638354`.
- The intended scoped backend policy grants `s3:ListBucket` only for the selected state prefixes; `s3:GetObject` and `s3:PutObject` on the exact state objects; and `s3:GetObject`, `s3:PutObject`, and `s3:DeleteObject` on their `.tflock` objects. It does not grant `s3:DeleteObject` on state objects. Permanent deletion of old object versions is reserved for a separately reviewed recovery/cleanup role.
- All four team members may approve and apply plans as previously decided. The person who starts resources has first responsibility for cleanup. These are procedural responsibilities, not enforced by S3 state permissions.
- Bucket tags follow [DEC-03](DEC-03-cloud-resource-naming-and-tags.md): `Project`, `Environment`, `Owner`, `Task`, and `ExpiresOn` where supported. Exact values will be recorded with the approved resource plan.

## Rationale
S3 keeps the state backend in the selected AWS account and avoids introducing another service. Native lockfiles avoid a separate lock table. Versioning supplies a practical recovery point for state changes, while separate keys/root configurations make the ownership boundaries from DEC-01 explicit. SSE-S3 meets the at-rest encryption requirement without adding KMS policy or key-management overhead for this small project backend.

## Implications
PD-15 Step 4 must prepare and review any required bootstrap and recovery procedure before an apply. Step 5 must freeze exact bucket/state-key/workspace/module names in `docs/architecture/terraform-ownership.md`. Step 6 must select a Terraform version that supports S3 lockfiles and validate statically without contacting remote state. Backend provisioning and any state migration remain separately gated cloud actions.

The existing `PowerUserAccess` grant remains as directed by Rahul, and least-privilege checks are deferred. Therefore this design's scoped S3 permissions and restricted old-version deletion are intended controls, not verified effective controls. No bucket policy, IAM policy, backend, bucket, state, or AWS resource is created by this decision.

## Approver
Rahul (D), who verified the Step 3 design recommendation on 2026-10-17.

## Supersedes
None

## Sources
- [Terraform S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3)
- [Terraform state and backends](https://developer.hashicorp.com/terraform/language/state/backends)
- [Amazon S3 default encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html)
- [Deleting object versions in S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeletingObjectVersions.html)
