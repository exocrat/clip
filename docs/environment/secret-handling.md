# Secret Reference and Access Procedure

**Canonical path:** `docs/environment/secret-handling.md`

This record contains no secret values. Never ask anyone to paste passwords, MFA/OTP values, private keys, access keys, tokens, or secret values in chat or commit them to the repository. Local environment files remain untracked. Real secrets belong only in the selected access-controlled store, never fixtures, logs, or evidence.

## Selected shared store

- Store: AWS Systems Manager Parameter Store in account `335523638354`, Region `ap-south-1`.
- Namespace convention: simple parameter paths under `/clip/`. Each owning task/domain chooses an exact path when it has an approved need; do not create placeholder secrets or competing names.
- Secret parameter type/tier: Standard `SecureString`, encrypted with the AWS-managed Systems Manager key `alias/aws/ssm`. Do not create a customer-managed KMS key or use Advanced parameters without a separate reviewed decision.
- Non-secret shared identifiers may use SSM `String` parameters, as described in `docs/architecture/terraform-ownership.md`.
- A read-only `aws ssm describe-parameters` query for names under `/clip/` returned no parameters. No shared secret references are currently configured; domain tasks add them only when approved and needed.

## Authentication, permissions, and ownership

- Authenticate using the approved AWS CLI/SDK credential chain for profile `clip-project`; the recorded CLI login command is `aws login --profile clip-project`. Do not place credentials or tokens in profile documentation, command arguments, Terraform configuration, or repository files.
- The team requirement is for all four members to have SSM read, write, and manage access. Aditya reported that a `CLIPParameterStoreTeamAccess` policy was added while `PowerUserAccess` was retained and `IAMFullAccess` removed. These attachments and effective permissions were not independently verified for all four members. The team intentionally deferred least-privilege checks; this is an accepted broad-access exception, not a passing least-privilege result.
- No parameter-value read/write/delete or KMS encryption/decryption test was performed for this task. Do not infer effective access from the human-reported policy update or from the empty name listing.
- Each parameter's task/domain owner is responsible for its reference and lifecycle. The person who starts associated resources has first cleanup responsibility; shared approval and cleanup roles are in `docs/environment/cloud-inventory.md`.
- Runtime services retrieve secret values through their approved runtime role using a secret reference. Terraform configuration, modules, plans, state, outputs, tags, and ordinary logs must contain references only, never secret values.

## Rotation and unavailable access

- Rotation is manual. A rotation cadence has not been selected; no schedule is implied by this record.
- No separate unavailable-access recovery strategy was selected, at Rahul's direction. If access becomes unavailable, pause the dependent operation and obtain a new human decision; do not invent a recovery path or expose/copy secret values.
- Record any future parameter's non-secret reference/name, purpose, environment/account, owning task/person, approved access role/procedure, permission scope, rotation/revocation arrangement, and non-secret verification result here. Never record the parameter value, ciphertext, or session credentials.

## Current setup status

The store and `/clip/` naming convention are selected, but no parameter values or references are configured. The reported access policy has not been independently inspected or tested for each team member. Provider/database secret references are deferred to the tasks that configure those integrations. No AWS parameter, permission, key, or other resource was created or changed by PD-14.
