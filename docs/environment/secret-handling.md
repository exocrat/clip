# Secret Reference and Access Procedure

**Canonical path:** `docs/environment/secret-handling.md`

This record contains no secret values. Never ask anyone to paste passwords, MFA/OTP values, private keys, access keys, tokens, or secret values in chat or commit them to the repository. Local environment files remain untracked. Real secrets belong only in the selected access-controlled store, never fixtures, logs, or evidence.

## Recorded status — 2026-10-19

Reconciled from approved deployment records through `cc04a23`; no parameter values were read during this reconciliation. October 17 access findings below remain historical and do not establish current effective permissions.

### Shared application/project secrets

| Field | Status |
|---|---|
| Shared manager/access-controlled channel | **Selected by Rahul on 2026-10-17:** AWS Systems Manager Parameter Store, Standard-tier `SecureString`, for static project secrets. Namespace `/clip/`; PD-14 selected the manager without provisioning. PD-16 subsequently records creation of the master parameter in its approved base apply. |
| Planned account/region | Account `335523638354`, region `ap-south-1`; these are the verified project target, not evidence that Parameter Store currently contains project values. |
| Cost/limits | AWS lists Standard parameters as having no additional Parameter Store charge, with a 4 KB value limit and up to 10,000 standard parameters per account/Region. KMS/key choices or other associated services may have separate costs; check before setup. See [Parameter Store pricing](https://aws.amazon.com/systems-manager/pricing/) and [tier limits](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html). |
| Encryption/access warning | **Selected by Rahul on 2026-10-17:** use the AWS-managed `aws/ssm` KMS key. AWS documents that this key's policy allows all IAM principals in the account to use KMS Decrypt; a principal still needs the relevant Systems Manager permission to retrieve a parameter. This is account-wide decryption capability, not per-secret separation. PD-14 created no key or policy; PD-16 later records base IAM roles/policies. Effective IAM permissions have not been independently verified. See [restricting access to SecureString parameters](https://docs.aws.amazon.com/systems-manager/latest/userguide/ps-restrict-decryption.html). |
| Parameter path/reference names | **Convention selected by Rahul on 2026-10-17:** simple parameter names beneath `/clip/`, using the previously selected shape `/<project>/<environment>/<parameter-name>`, concretely `/clip/{dev|test|staging|prod}/{lower-kebab-case-name}`. For example, `/clip/dev/database-url` is a name example only; no parameter exists. Keep names non-secret. |
| PD-16 test parameters | Both `/clip/test/database-master-password` and `/clip/test/database-probe-password` exist at recorded parameter/write-only version 1. Setup revision 3 and probe revision 1 ran successfully; setup execution uses both references, probe execution only its own, and both application task roles have no inline/attached policies. Exact registered policies/references were checked; broad human access is the explicit DEC-10 exception. Terraform uses ephemeral/write-only inputs; no values are recorded here. See [live checks](../evaluation/foundation/pd-16/database-retry-result.json). |
| Secret references | Recorded master reference: `/clip/test/database-master-password`, account `335523638354`, `ap-south-1`, test environment, PD-16. Probe reference `/clip/test/database-probe-password` is also provisioned; application/provider database URLs and other domain references remain unconfigured. Manual rotation/versioning and unavailable-access rules below apply. Aditya is the current PD-16 operator; registered task-reference/policy and runtime checks passed, while account-wide/all-user effective-access claims remain unverified; see the [inventory](cloud-inventory.md#pd-1516-recorded-deployment--2026-10-19). |
| Manager ownership | Shared responsibility: all four current team members—Aditya, Suraj, Mohit, and Rahul—are intended to read, write, and manage Parameter Store secrets. Aditya is explicitly the current PD-16 change-window operator; this does not replace shared ownership or establish a primary for every future provider. |
| Intended human access group | Rahul explicitly directed that all four team members—Aditya, Suraj, Mohit, and Rahul—have read/write/manage access to project parameters. Current AWS evidence identifies IAM users `rahulkoyye`, `surajs2`, and `mohitmahapa1` in `DS252-Project-Developers`; At that October 17 checkpoint Aditya was reported to use root. PD-16 later STS-verified IAM profile `adityalaxmi1` and approved it for non-root operations; see [DEC-06](../decisions/terraform-planning-identity.md). This does not prove its effective least privilege. |
| Access role and permissions | On 2026-10-17, read-only inspection found Rahul's user had attached `IAMFullAccess` and belonged to `DS252-Project-Developers`, which had attached `PowerUserAccess`; Suraj and Mohit were in that group and each had `IAMUserChangePassword` attached directly. Policy simulation returned `allowed` for the checked SSM actions on an example `/clip/dev/` ARN and KMS encrypt/decrypt actions for these three IAM users; this was not a live operation test. Aditya later reported that all four users retain `PowerUserAccess`, `IAMFullAccess` was removed, and `CLIPParameterStoreTeamAccess` was added. The latest attachments and effective permissions for all four are not independently verified. Rahul accepted broad `PowerUserAccess` as intentional and skipped least-privilege checks. All-four SSM read/write/manage access remains an intent, not a tested capability. Aditya's reported root access was not exercised. |
| Rotation/revocation | Manual rotation selected; cadence remains undecided. No rotation automation is configured. PD-16 synthetic-test credentials are provisioned at version 1; rotation/version bumps require a separate approved action, never a lifecycle side effect. Choose provider-specific cadence/overlap/revocation before later real provider credentials are used. |
| Unavailable-access recovery | No recovery strategy selected, per Rahul's latest direction. This supersedes the minimal recovery procedure recorded earlier in this file's history. If access is unavailable, pause dependent setup and ask the account owner/admin for direction; this is a safe stop condition, not a recovery plan. |

If a task needs an application/provider/database secret before the parameter path, policy attachment, and effective IAM permissions are verified, stop that dependent setup. The `aws/ssm` key strategy and path convention are selected, and no `/clip/` parameters were found by the read-only name query. Aditya reported that `CLIPParameterStoreTeamAccess` was added, but its attachment and effective permissions have not been independently verified. Never substitute chat, email, repository files, fixtures, or logs as a secret store.

### Per-contributor AWS CLI sign-in (not a shared secret store)

Rahul's local profile `clip-project` uses interactive `aws login --profile clip-project`; the read-only identity check `aws sts get-caller-identity --profile clip-project` verified account `335523638354` and IAM user `arn:aws:iam::335523638354:user/rahulkoyye` on 2026-10-17. Project resources use `ap-south-1`. The profile name is local configuration, not a shared credential reference. Each contributor must use their own authorized identity and must not share cached session credentials. See [AWS CLI sign-in](README.md#aws-cli-sign-in) and [cloud inventory](cloud-inventory.md).

| Access-control field | Current evidence/status |
|---|---|
| AWS account owner/admin | Rahul reports Aditya owns the account and all team members have administrator access; this was not independently audited. |
| Effective permissions | The 2026-10-17 IAM inspection and simulator evidence is historical. Aditya later reported `PowerUserAccess` for all four, removal of `IAMFullAccess`, and addition of `CLIPParameterStoreTeamAccess`; current attachments/effective access for all four are not independently verified. No parameter exists and no live secret operation was performed. Least-privilege checks were intentionally skipped. |
| Plan/apply responsibility | Any team member may approve/apply an exact approved infrastructure plan; Aditya owns billing alerts; cleanup is shared with the resource creator first responsible. These are workflow roles, not proof of IAM permissions. |
| Local session sign-out | `aws logout --profile clip-project` removes the local profile session when appropriate. This is not a verified central revocation procedure. |
| Central revocation/recovery | No recovery strategy is selected. The former minimal procedure has been superseded by Rahul's latest direction. Stop dependent work if access is unavailable and ask the account owner/admin; do not improvise a cloud/IAM change. |

### Verified billing notification reference

The AWS account `335523638354` has the verified one-year budget `CLIP-Account-Actual-Spend-From-2026-10-17` (2026-10-17 through 2027-10-17), USD 200 reference amount, with actual incurred-spend notifications above USD 50, 80, 100, 120, and 130. All thresholds are configured for `adityalaxmi1@iisc.ac.in`, `surajs2@iisc.ac.in`, `mohitmahapa1@iisc.ac.in`, and `rahulkoyye@iisc.ac.in`; credits are excluded from the cost basis. This is an account-specific notification, not a spending cap or a secret-access control. Details and limitations are in [cloud inventory](cloud-inventory.md). Rahul verified the budget configuration.

No secret values, keys, tokens, passwords, MFA codes, or local credential files are recorded here. Existing provider/database references are added by their owning tasks only after an approved access method is configured and verified.
## Selected shared store

- Store: AWS Systems Manager Parameter Store in account `335523638354`, Region `ap-south-1`.
- Namespace convention: simple parameter paths under `/clip/`. Each owning task/domain chooses an exact path when it has an approved need; do not create placeholder secrets or competing names.
- Secret parameter type/tier: Standard `SecureString`, encrypted with the AWS-managed Systems Manager key `alias/aws/ssm`. Do not create a customer-managed KMS key or use Advanced parameters without a separate reviewed decision.
- Non-secret shared identifiers may use SSM `String` parameters, as described in `docs/architecture/terraform-ownership.md`.
- A read-only `aws ssm describe-parameters` query for names under `/clip/` returned no parameters. No shared secret references are currently configured; domain tasks add them only when approved and needed.

## Authentication, permissions, and ownership

- Select the current operator’s explicitly approved non-root AWS CLI/SDK profile and verify caller/account before each operation; never rely on an ambient root default. Rahul’s historical sign-in uses `aws login --profile clip-project`; the PD-16 session approved `adityalaxmi1` ([DEC-06](../decisions/terraform-planning-identity.md)). A profile name is contributor-specific, not a team-wide credential. Do not place credentials or tokens in profile documentation, command arguments, Terraform configuration, or repository files.
- The team requirement is for all four members to have SSM read, write, and manage access. Aditya reported that a `CLIPParameterStoreTeamAccess` policy was added while `PowerUserAccess` was retained and `IAMFullAccess` removed. These attachments and effective permissions were not independently verified for all four members. The team intentionally deferred least-privilege checks; this is an accepted broad-access exception, not a passing least-privilege result.
- The AWS-managed `aws/ssm` key does not provide per-parameter KMS decryption isolation; the PD-16 execution-role design depends on scoped SSM parameter permissions. Existing broad account access and effective permissions remain unverified.
- PD-14 performed no parameter-value read/write/delete or KMS encryption/decryption test; PD-16 subsequently records the approved master-parameter write. No live setup/probe task or independent effective-access test is recorded. Do not infer effective access from the human-reported policy update or from the empty name listing.
- Each parameter's task/domain owner is responsible for its reference and lifecycle. The person who starts associated resources has first cleanup responsibility; shared approval and cleanup roles are in `docs/environment/cloud-inventory.md`.
- Runtime services retrieve secret values through their approved runtime role using a secret reference. Terraform configuration, modules, plans, state, outputs, tags, and ordinary logs must contain references only, never secret values.

## PD-16 human-operator exception — 2026-10-19

The user approved [DEC-10](../decisions/broad-human-operator-access.md), retaining broad non-root human operator access for PD-16 without adding a dedicated human runtime role. Actual operator metadata shows IAMFullAccess and group PowerUserAccess/CLIPParameterStoreTeamAccess. Human permission breadth is accepted, not verified as least privilege. Runtime setup/probe secret injection, empty application-role policies, scoped execution-role access and the prohibition on logging/committing secret values remain mandatory. No IAM permission or secret value changed through this decision.

## Rotation and unavailable access

- Rotation is manual. A rotation cadence has not been selected; no schedule is implied by this record.
- No separate unavailable-access recovery strategy was selected, at Rahul's direction. If access becomes unavailable, pause the dependent operation and obtain a new human decision; do not invent a recovery path or expose/copy secret values.
- Record any future parameter's non-secret reference/name, purpose, environment/account, owning task/person, approved access role/procedure, permission scope, rotation/revocation arrangement, and non-secret verification result here. Never record the parameter value, ciphertext, or session credentials.

## Current setup status

PD-16 records the master reference provisioned; the probe reference remains planned and application/provider references are deferred to their owning tasks. Reported team access and runtime permission boundaries have not been independently verified. PD-14 itself created no parameter/key/resource; later PD-16 provisioning is recorded in the [inventory](cloud-inventory.md#pd-1516-recorded-deployment--2026-10-19).
