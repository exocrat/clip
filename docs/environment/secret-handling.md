# Secret Reference and Access Procedure

**Canonical path:** `docs/environment/secret-handling.md`

This template contains NO secret values. PD-03 initializes it, PD-14 records the approved shared secret manager/access method, and ID-01/CN-03/other owners add their configured references when actually needed. The agent must not ask the human to paste passwords/MFA/OTP/private keys/access keys/tokens in chat or commit them. Local environment files remain untracked. Real secrets belong in the selected manager/access-controlled channel, never fixtures/logs/evidence.

## Current status — 2026-10-17 (reconciled with latest verified direction)

### Shared application/project secrets

| Field | Status |
|---|---|
| Shared manager/access-controlled channel | **Selected by Rahul on 2026-10-17:** AWS Systems Manager Parameter Store, Standard-tier `SecureString`, for static project secrets. Namespace `/clip/`; it is not configured yet, no parameter was created, and no cloud service/resource was changed. |
| Planned account/region | Account `335523638354`, region `ap-south-1`; these are the verified project target, not evidence that Parameter Store currently contains project values. |
| Cost/limits | AWS lists Standard parameters as having no additional Parameter Store charge, with a 4 KB value limit and up to 10,000 standard parameters per account/Region. KMS/key choices or other associated services may have separate costs; check before setup. See [Parameter Store pricing](https://aws.amazon.com/systems-manager/pricing/) and [tier limits](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html). |
| Encryption/access warning | **Selected by Rahul on 2026-10-17:** use the AWS-managed `aws/ssm` KMS key. AWS documents that this key's policy allows all IAM principals in the account to use KMS Decrypt; a principal still needs the relevant Systems Manager permission to retrieve a parameter. This is account-wide decryption capability, not per-secret separation. No key or policy was created or changed, and effective IAM permissions have not been verified. See [restricting access to SecureString parameters](https://docs.aws.amazon.com/systems-manager/latest/userguide/ps-restrict-decryption.html). |
| Parameter path/reference names | **Convention selected by Rahul on 2026-10-17:** simple parameter names beneath `/clip/`, using the previously selected shape `/<project>/<environment>/<parameter-name>`, concretely `/clip/{dev|test|staging|prod}/{lower-kebab-case-name}`. For example, `/clip/dev/database-url` is a name example only; no parameter exists. Keep names non-secret. |
| Secret references | None configured; provider and database references remain not configured. Do not invent reference names or store values here. |
| Manager ownership | Shared responsibility: all four current team members—Aditya, Suraj, Mohit, and Rahul—are intended to read, write, and manage Parameter Store secrets. No single primary maintainer/change-window operator is designated. |
| Intended human access group | Rahul explicitly directed that all four team members—Aditya, Suraj, Mohit, and Rahul—have read/write/manage access to project parameters. Current AWS evidence identifies IAM users `rahulkoyye`, `surajs2`, and `mohitmahapa1` in `DS252-Project-Developers`; Aditya is reported to use the account root identity, which was not used or tested. |
| Access role and permissions | On 2026-10-17, read-only inspection found Rahul's user had attached `IAMFullAccess` and belonged to `DS252-Project-Developers`, which had attached `PowerUserAccess`; Suraj and Mohit were in that group and each had `IAMUserChangePassword` attached directly. Policy simulation returned `allowed` for the checked SSM actions on an example `/clip/dev/` ARN and KMS encrypt/decrypt actions for these three IAM users; this was not a live operation test. Aditya later reported all four users retain `PowerUserAccess` and `IAMFullAccess` was removed. The current attachment state for all four is not independently verified. Rahul explicitly accepted broad `PowerUserAccess` as intentional and skipped least-privilege checks. The all-four SSM read/write/manage setting remains an access intent, not a tested capability. Aditya's reported root access was not exercised. |
| Rotation/revocation | Manual rotation selected; cadence remains undecided. No rotation automation or credential has been configured. Choose a provider-specific cadence and overlap/revocation procedure before a real secret is used. |
| Unavailable-access recovery | No recovery strategy selected, per Rahul's latest direction. This supersedes the minimal recovery procedure recorded earlier in this file's history. If access is unavailable, pause dependent setup and ask the account owner/admin for direction; this is a safe stop condition, not a recovery plan. |

If a task needs an application/provider/database secret before the parameter path, access policy, and effective IAM permissions are verified, stop that dependent setup. The `aws/ssm` key strategy and path convention are selected, but no AWS parameters or access policies have been configured. Never substitute chat, email, repository files, fixtures, or logs as a secret store.

### Per-contributor AWS CLI sign-in (not a shared secret store)

Rahul's local profile `clip-project` uses interactive `aws login --profile clip-project`; the read-only identity check `aws sts get-caller-identity --profile clip-project` verified account `335523638354` and IAM user `arn:aws:iam::335523638354:user/rahulkoyye` on 2026-10-17. Project resources use `ap-south-1`. The profile name is local configuration, not a shared credential reference. Each contributor must use their own authorized identity and must not share cached session credentials. See [AWS CLI sign-in](README.md#aws-cli-sign-in) and [cloud inventory](cloud-inventory.md).

| Access-control field | Current evidence/status |
|---|---|
| AWS account owner/admin | Rahul reports Aditya owns the account and all team members have administrator access; this was not independently audited. |
| Effective permissions | The 2026-10-17 IAM inspection and simulator evidence is historical. Aditya later reported `PowerUserAccess` for all four and removal of `IAMFullAccess`; current attachments/effective access for all four are not independently verified. No parameter exists and no live secret operation was performed. Least-privilege checks were intentionally skipped. |
| Plan/apply responsibility | Any team member may approve/apply an exact approved infrastructure plan; Aditya owns billing alerts; cleanup is shared with the resource creator first responsible. These are workflow roles, not proof of IAM permissions. |
| Local session sign-out | `aws logout --profile clip-project` removes the local profile session when appropriate. This is not a verified central revocation procedure. |
| Central revocation/recovery | No recovery strategy is selected. The former minimal procedure has been superseded by Rahul's latest direction. Stop dependent work if access is unavailable and ask the account owner/admin; do not improvise a cloud/IAM change. |

### Verified billing notification reference

The AWS account `335523638354` has the verified one-year budget `CLIP-Account-Actual-Spend-From-2026-10-17` (2026-10-17 through 2027-10-17), USD 200 reference amount, with actual incurred-spend notifications above USD 50, 80, 100, 120, and 130. All thresholds are configured for `adityalaxmi1@iisc.ac.in`, `surajs2@iisc.ac.in`, `mohitmahapa1@iisc.ac.in`, and `rahulkoyye@iisc.ac.in`; credits are excluded from the cost basis. This is an account-specific notification, not a spending cap or a secret-access control. Details and limitations are in [cloud inventory](cloud-inventory.md). Rahul verified the budget configuration.

No secret values, keys, tokens, passwords, MFA codes, or local credential files are recorded here. Existing provider/database references are added by their owning tasks only after an approved access method is configured and verified.

Read approved access procedure before asking; request access just in time only for the assigned step. If human-only account/device work is needed, give exact safe actions and expected non-secret output, wait and verify afterward. A missing access method/prerequisite blocks its dependent operation. Provider setup/auth/permitted-recipient behavior must not weaken production security or send to fabricated real addresses.
