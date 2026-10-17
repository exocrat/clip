# Secret Reference and Access Procedure

**Canonical path:** `docs/environment/secret-handling.md`

This template contains NO secret values. PD-03 initializes it, PD-14 records the approved shared secret manager/access method, and ID-01/CN-03/other owners add their configured references when actually needed. The agent must not ask the human to paste passwords/MFA/OTP/private keys/access keys/tokens in chat or commit them. Local environment files remain untracked. Real secrets belong in the selected manager/access-controlled channel, never fixtures/logs/evidence.

## Current status — 2026-10-17

### Shared application/project secrets

| Field | Status |
|---|---|
| Shared manager/access-controlled channel | **Selected by Rahul on 2026-10-17:** AWS Systems Manager Parameter Store, `SecureString`, Standard tier, for static project secrets. It is not configured yet; no parameter was created and no cloud service/resource was changed. |
| Planned account/region | Account `335523638354`, region `ap-south-1`; these are the verified project target, not evidence that Parameter Store currently contains project values. |
| Cost/limits | AWS lists Standard parameters as having no additional Parameter Store charge, with a 4 KB value limit and up to 10,000 standard parameters per account/Region. KMS/key choices or other associated services may have separate costs; check before setup. See [Parameter Store pricing](https://aws.amazon.com/systems-manager/pricing/) and [tier limits](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html). |
| Encryption/access warning | **Selected by Rahul on 2026-10-17:** use the AWS-managed `aws/ssm` KMS key. AWS documents that this key's policy allows all IAM principals in the account to use KMS Decrypt; a principal still needs the relevant Systems Manager permission to retrieve a parameter. This is account-wide decryption capability, not per-secret separation. No key or policy was created or changed, and effective IAM permissions have not been verified. See [restricting access to SecureString parameters](https://docs.aws.amazon.com/systems-manager/latest/userguide/ps-restrict-decryption.html). |
| Parameter path/reference names | **Convention selected by Rahul on 2026-10-17:** `/<project>/<environment>/<parameter-name>`, concretely `/clip/{dev|test|staging|prod}/{lower-kebab-case-name}`. For example, `/clip/dev/database-url` is a name example only; no parameter exists. Keep parameter names non-secret. IAM access to a path must be reviewed for recursive descendant access before setup; see [Parameter Store IAM setup guidance](https://docs.aws.amazon.com/systems-manager/latest/userguide/parameter-store-setting-up.html). |
| Secret references | None configured; provider and database references remain not configured. Do not invent reference names or store values here. |
| Manager ownership | Shared responsibility: all four current team members—Aditya, Suraj, Mohit, and Rahul—are intended to read, write, and manage Parameter Store secrets. No single primary maintainer/change-window operator is designated. |
| Intended human access group | Rahul explicitly directed that all four team members—Aditya, Suraj, Mohit, and Rahul—have read/write/manage access to the project parameters. This is intended policy only; no AWS policy has been configured or verified. |
| Access role and permissions | Exact IAM identities and parameter-path permissions are not established. The requested access is broad: all four are intended to read, write, and manage project parameters; with `aws/ssm`, account IAM principals may also have KMS decrypt capability as described above. No IAM/KMS policy changes were made. Coding-agent access remains least-privilege, with no AWS permission changes or agent grants. |
| Rotation/revocation | Rahul chose manual rotation and has not decided a cadence. For a planned change: issue a replacement with the provider, update the Parameter Store `SecureString`, verify the application uses the replacement, then revoke the prior credential. If compromise is suspected, revoke the exposed credential promptly, issue/store a replacement, and verify the application; never restore a compromised value from history. Standard tier does not rotate credentials automatically. Record the cadence and any overlap window per provider before use; cadence remains an open decision. |
| Unavailable-access recovery | Rahul chose this minimal procedure: (1) for an accidental bad update with no exposure, use Parameter Store history to restore the last known-good version and verify consumers; (2) for suspected exposure, revoke/reissue at the provider and update Parameter Store—do not restore the exposed value; (3) for access/decryption failure, each team member should sign in with their own authorized identity, verify account/region, and have an authorized team administrator inspect/restore SSM/KMS permissions; if no team member can regain access, contact Aditya as the user-reported account owner/admin. Do not disable/delete the KMS key as a troubleshooting shortcut. This is a documented procedure, not a tested recovery; actual IAM permissions remain unverified. |

If a task needs an application/provider/database secret before the parameter path, access policy, and effective IAM permissions are verified, stop that dependent setup. The `aws/ssm` key strategy and path convention are selected, but no AWS parameters or access policies have been configured. Never substitute chat, email, repository files, fixtures, or logs as a secret store.

### Per-contributor AWS CLI sign-in (not a shared secret store)

Rahul's local profile `clip-project` uses interactive `aws login --profile clip-project`; the read-only identity check `aws sts get-caller-identity --profile clip-project` verified account `335523638354` and IAM user `arn:aws:iam::335523638354:user/rahulkoyye` on 2026-10-17. Project resources use `ap-south-1`. The profile name is local configuration, not a shared credential reference. Each contributor must use their own authorized identity and must not share cached session credentials. See [AWS CLI sign-in](README.md#aws-cli-sign-in) and [cloud inventory](cloud-inventory.md).

| Access-control field | Current evidence/status |
|---|---|
| AWS account owner/admin | Rahul reports Aditya owns the account and all team members have administrator access; this was not independently audited. |
| Effective permissions | Not fully verified. On 2026-10-17, read-only `iam:GetUser`, `iam:ListAttachedUserPolicies`, and `iam:ListGroupsForUser` calls were denied for Rahul's identity (the earlier `iam:ListAccountAliases` call was also denied). IAM attachments and effective permissions are unknown; this does not establish the reported administrator access or prove least privilege. No IAM permission changes were made. Do not infer least privilege or grant an agent broad access. |
| Plan/apply responsibility | Any team member may approve/apply an exact approved infrastructure plan; Aditya owns billing alerts; cleanup is shared with the resource creator first responsible. These are workflow roles, not proof of IAM permissions. |
| Local session sign-out | `aws logout --profile clip-project` removes the local profile session when appropriate. This is not a verified central revocation procedure. |
| Central revocation/recovery | Not documented or verified. Confirm the proper identity/grant revocation and access-restoration procedure with the account administrator before relying on it. After sign-in, verify the returned account/identity; stop on mismatch. |

### Verified billing notification reference

The AWS account `335523638354` has the verified one-year budget `CLIP-Account-Actual-Spend-From-2026-10-17` (2026-10-17 through 2027-10-17), USD 200 reference amount, with actual incurred-spend notifications above USD 50, 80, 100, 120, and 130. All thresholds are configured for `adityalaxmi1@iisc.ac.in`, `surajs2@iisc.ac.in`, `mohitmahapa1@iisc.ac.in`, and `rahulkoyye@iisc.ac.in`; credits are excluded from the cost basis. This is an account-specific notification, not a spending cap or a secret-access control. Details and limitations are in [cloud inventory](cloud-inventory.md). Rahul verified the budget configuration.

No secret values, keys, tokens, passwords, MFA codes, or local credential files are recorded here. Existing provider/database references are added by their owning tasks only after an approved access method is configured and verified.

Read approved access procedure before asking; request access just in time only for the assigned step. If human-only account/device work is needed, give exact safe actions and expected non-secret output, wait and verify afterward. A missing access method/prerequisite blocks its dependent operation. Provider setup/auth/permitted-recipient behavior must not weaken production security or send to fabricated real addresses.
