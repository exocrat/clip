# Secret Reference and Access Procedure

**Canonical path:** `docs/environment/secret-handling.md`

This template contains NO secret values. PD-03 initializes it, PD-14 records the approved shared secret manager/access method, and ID-01/CN-03/other owners add their configured references when actually needed. The agent must not ask the human to paste passwords/MFA/OTP/private keys/access keys/tokens in chat or commit them. Local environment files remain untracked. Real secrets belong in the selected manager/access-controlled channel, never fixtures/logs/evidence.

## Current status — 2026-10-17

### Shared application/project secrets

| Field | Status |
|---|---|
| Shared manager/access-controlled channel | **Not selected or configured.** This is an unresolved PD-14 Step 8 dependency before application/provider/database secrets are stored. No cloud secret service was created or changed. |
| Secret references | None configured; provider and database references remain not configured. Do not invent reference names or store values here. |
| Manager owner | Unassigned. Aditya is the user-reported AWS account owner and billing-alert owner, but has not been assigned ownership of a shared secret manager. |
| Access role and permissions | Not established for a shared manager. Coding-agent access remains least-privilege and no AWS permission changes or agent grants were made. |
| Rotation/revocation | No shared-manager procedure exists yet. Define it with the selected manager and owner before adding any real reference. |
| Unavailable-access recovery | No verified recovery runbook exists for shared application secrets. Establish the owner/contact and recovery procedure when the manager is selected. |

If a task needs an application/provider/database secret before this is resolved, stop that dependent setup and ask for an approved manager, owner, access scope, rotation/revocation, and recovery procedure. Never substitute chat, email, repository files, fixtures, or logs as a secret store.

### Per-contributor AWS CLI sign-in (not a shared secret store)

Rahul's local profile `clip-project` uses interactive `aws login --profile clip-project`; the read-only identity check `aws sts get-caller-identity --profile clip-project` verified account `335523638354` and IAM user `arn:aws:iam::335523638354:user/rahulkoyye` on 2026-10-17. Project resources use `ap-south-1`. The profile name is local configuration, not a shared credential reference. Each contributor must use their own authorized identity and must not share cached session credentials. See [AWS CLI sign-in](README.md#aws-cli-sign-in) and [cloud inventory](cloud-inventory.md).

| Access-control field | Current evidence/status |
|---|---|
| AWS account owner/admin | Rahul reports Aditya owns the account and all team members have administrator access; this was not independently audited. |
| Effective permissions | Not fully verified. The alias lookup was denied for missing `iam:ListAccountAliases`; no IAM policy changes were made. Do not infer least privilege or grant an agent broad access. |
| Plan/apply responsibility | Any team member may approve/apply an exact approved infrastructure plan; Aditya owns billing alerts; cleanup is shared with the resource creator first responsible. These are workflow roles, not proof of IAM permissions. |
| Local session sign-out | `aws logout --profile clip-project` removes the local profile session when appropriate. This is not a verified central revocation procedure. |
| Central revocation/recovery | Not documented or verified. Confirm the proper identity/grant revocation and access-restoration procedure with the account administrator before relying on it. After sign-in, verify the returned account/identity; stop on mismatch. |

### Verified billing notification reference

The AWS account `335523638354` has the verified one-year budget `CLIP-Account-Actual-Spend-From-2026-10-17` (2026-10-17 through 2027-10-17), USD 200 reference amount, with actual incurred-spend notifications above USD 50, 80, 100, 120, and 130. All thresholds are configured for `adityalaxmi1@iisc.ac.in`, `surajs2@iisc.ac.in`, `mohitmahapa1@iisc.ac.in`, and `rahulkoyye@iisc.ac.in`; credits are excluded from the cost basis. This is an account-specific notification, not a spending cap or a secret-access control. Details and limitations are in [cloud inventory](cloud-inventory.md). Rahul verified the budget configuration.

No secret values, keys, tokens, passwords, MFA codes, or local credential files are recorded here. Existing provider/database references are added by their owning tasks only after an approved access method is configured and verified.

Read approved access procedure before asking; request access just in time only for the assigned step. If human-only account/device work is needed, give exact safe actions and expected non-secret output, wait and verify afterward. A missing access method/prerequisite blocks its dependent operation. Provider setup/auth/permitted-recipient behavior must not weaken production security or send to fabricated real addresses.
