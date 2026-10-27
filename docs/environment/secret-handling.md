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

The API now accepts `CLIP_DATABASE_DSN` as a masked process setting, but no application-specific DSN parameter reference or API runtime-role policy is configured. The existing PD-16 master and probe credentials have different purposes and must not be reused by the application. Before enabling database-backed API runtime, the owning task must select a dedicated application database principal and exact `/clip/<environment>/...` reference, then review the ECS secret mapping and execution-role access. This code step changed no SSM value, IAM policy, Terraform resource, or cloud service. Never substitute chat, email, repository files, fixtures, or logs as a secret store.

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
## ID-01 Microsoft app registration — user-reported — 2026-10-22 14:02:07 UTC

Aditya supplied these non-secret identifiers in chat; they have not been independently checked in the Microsoft portal.

| Field | Value/status |
|---|---|
| Application (client) ID | `ab3a63e3-d4db-4c3c-b4bf-ac5f7573ffbb` |
| Directory (tenant) ID | `19d07278-f040-4722-8202-b1174cf3a4d3` |
| Supported account types | Aditya confirmed the portal selection is any organizational directory plus personal Microsoft accounts on 2026-10-22 14:03:25 UTC; not independently inspected |
| SPA redirect URIs | Aditya confirmed `http://localhost:5173/auth/callback` and `https://clip-iisc.site/auth/callback` are configured on 2026-10-22 14:03:25 UTC; not independently inspected |
| Client secret | None requested or recorded; SPA uses authorization code with PKCE |

The identifiers and portal settings are human-reported and not independently inspected. The registration does not establish a validated sign-in implementation.

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

## ID-01 SES runtime access — setup partial

SES uses the task role in ECS and the operator's approved non-root profile locally;
no static SES/SMTP credential. Sender-scoped policy applied2026-10-23 06:17:00 UTC;
corrected sandbox task-role delivery/inbox/cleanup passed17:17:30. Production access
and the live verify@ sender update remain pending. See [current setup](identity-provider-setup.md)
and [historical permissions/delivery](../evaluation/identity/provider-history.md).

## ID-01 SES controlled-recipient input

`ses_sandbox_recipient_identity_arn` is the private approved verified inbox ARN.
Supply its TF_VAR input in child memory, not CLI arguments, committed tfvars or
logs. It is sensitive in Terraform rendering but present in access-controlled
state/policy/saved plans. Preserve it during sandbox work; omission removes scope.
Deployed From condition still permits no-reply@clip-iisc.site; desired source uses
verify@clip-iisc.site, awaiting exact reviewed plan/apply. Remove the recipient
scope only through reviewed production transition and verify actual sending.

## ID-01 dual email configuration

| Reference | Recorded state |
| --- | --- |
| Parameter | `/clip/test/identity/email-delivery` |
| Account/region | `335523638354` / `ap-south-1` |
| Storage | Standard SecureString, `alias/aws/ssm`, version1 |
| Private schema | version(integer1), primary(resend/ses), resend_api_key |
| Provisioning | Explicitly authorized; operator adityalaxmi1 create/decrypted read-back verified2026-10-24 14:15:45 UTC; no prior parameter overwritten. |
| Runtime access | ECS task-role permission and live application loading remain unverified. |

Keep order/key in one parameter version for the approved four-hour runtime cache.
A configuration switch without redeployment requires actual runtime retrieval,
not ECS startup-only environment injection. Verify exact task-role access before
live use. No credential value is recorded here; the key supplied in chat must be
rotated privately through an approved path. Do not request keys in chat or print
values in CLI arguments/logs/files. The local SDK's optional AWS-login dependency
was unavailable; CLI-exported temporary credentials stayed only in process memory.
This establishes operator access, not deployed runtime permission. Full outcomes
and current gates are consolidated in [provider history](../evaluation/identity/provider-history.md#resend-and-sender-outcome).


### ID-01 persistent runtime references — local preparation only

`/clip/test/identity/authentication-keys` was provisioned with explicit Aditya
approval on 2026-10-24 18:47:02 UTC: Standard SecureString version1,
AWS-managed aws/ssm key, account335523638354/ap-south-1. Metadata confirmed;
no decrypted read. `/clip/test/identity/database-url` remains proposed/unprovisioned.
The existing `/clip/test/identity/email-delivery` reference retains its reviewed
routing schema and four-hour refresh policy. No live reads were performed for
this preparation.

Authentication keys use exactly `schema_version` (integer 1), `key_version`
(a stable safe label), `lookup`, `verifier`, and `target_encryption`. The last
three are independent 32-byte random keys encoded as canonical standard base64.
Generate and persist actual values only through a separately approved private
procedure; never paste them into chat, repository, command arguments or evidence.
Duplicates, extra fields and noncanonical encodings are rejected. Bootstrap reads
keys once, verifies database commitments and never substitutes generated keys.
Key rotation requires a reviewed data migration/recovery plan.

The database reference contains an explicit private PostgreSQL URI for the
separate `clip_test_identity_app` login. Remote targets require database
`clip_test`, password and `sslmode=verify-full&sslrootcert=system`. Validate the
actual certificate chain before live use. The
[role proposal](../../database/roles/identity-runtime.sql.proposed) does not create
or change a shared role. Public grants, credential generation, role logging,
scoped SSM permissions and rollback require a concrete separately approved plan.
See the [runtime handoff](../evaluation/identity/integration.md#secure-runtime-preparation).

### ID-01 email-key rotation confirmation — 2026-10-27 18:25:58 UTC

Aditya confirms the previously chat-exposed Resend key was revoked and a
replacement stored in the existing `/clip/test/identity/email-delivery`
SecureString. This supersedes the outstanding exposed-key rotation action above.
No key value, parameter version, provider or AWS state was read by the agent;
new runtime loading/delivery is still a Step13 check. Fixed schema, four-hour
refresh, recipient restrictions and access approvals are unchanged. This does not
rotate the stable authentication keys or change database URLs. Database roles and
URLs previously labelled proposed in the historical preparation section were
subsequently provisioned; see the recorded [database preparation](../evaluation/identity/id-01-step-12/demo-postmortem-20261026.md#database-preparation).
