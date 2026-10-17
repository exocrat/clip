# Terraform change workflow

This workflow applies to every Terraform change in `infra/terraform/`. It is a review and safety procedure, not an authorization to create or change AWS resources. All four team members may approve and apply an explicitly reviewed plan. Everyone shares cleanup responsibility; the person who starts the resources has first responsibility for cleanup.

## 1. Identify and inspect the target

- Identify the owning root configuration, task/resource owner, exact state key, and whether the resources are bootstrap, shared test, or domain-exclusive. Follow [`docs/architecture/terraform-ownership.md`](../../docs/architecture/terraform-ownership.md); never duplicate another root's resources.
- Confirm the intended AWS account is `335523638354`, Region is `ap-south-1`, environment, and approved credentials/profile. Do not guess a profile, account, or target.
- Before any cloud planning operation, verify the CLI identity, for example `aws sts get-caller-identity --profile <approved-profile>`, and confirm the result is account `335523638354`. Replace the placeholder with the profile explicitly approved for the operation; do not put credentials or tokens in commands or files.
- Check the current inventory, resource owner, budget/cost headroom, state/backend readiness, permissions, and any existing resources. Stop if the state owner or contents, target, or resource ownership is uncertain.

## 2. Run local checks

From the repository root, run:

```sh
bash scripts/terraform-static-check.sh
git status --short
```

The static-check script checks Terraform formatting and validates initialized provider schemas with backend initialization disabled. It does not create a plan or contact AWS. Review the Git status and ensure no state, state backup, saved plan, variable/credential file, or sensitive generated output is staged. Keep `.terraform.lock.hcl` tracked so provider selection/checksums remain reproducible.

## 3. Prepare and review an exact plan

Planning against a remote backend is allowed only after the exact backend/state key, AWS target, access, and the resource design are ready and approved for planning. Initialize the selected root with its approved backend only after backend creation/migration gates have passed. Never plan against an assumed account, a different state key, or an unapproved environment.

Write any saved plan to a protected location outside the repository with owner-only access. A saved plan may contain sensitive values. For example, after replacing the placeholders with the selected root and a private plan path:

```sh
terraform -chdir=infra/terraform/<root> plan -out=/private/path/<change-id>.tfplan
sha256sum /private/path/<change-id>.tfplan
terraform -chdir=infra/terraform/<root> show -no-color /private/path/<change-id>.tfplan
```

Inspect the plan in a secure session; do not paste raw plan output, state, credentials, or sensitive outputs into chat, tickets, or ordinary logs. Share only the minimum nonsensitive review summary and the plan checksum. Review the exact account, Region, environment, state key, resource addresses, additions, changes, replacements and deletions, tags, access/exposure, data handling, rollback/recovery, test duration, and cleanup owner. Include an expected-cost estimate and its basis; Terraform's plan alone is not a cost estimate.

Obtain explicit human approval for that exact plan/checksum, target, cost, exposure, rollback, retention, and cleanup before applying. Any configuration, state, target, or plan change invalidates the approval; create and review a fresh plan. Never apply an unreviewed, stale, or mismatched plan.

## 4. Apply only the approved plan

After approval, apply the exact protected saved plan—not a new implicit plan—and confirm the checksum still matches the reviewed artifact:

```sh
sha256sum /private/path/<change-id>.tfplan
terraform -chdir=infra/terraform/<root> apply /private/path/<change-id>.tfplan
```

The team member applying must independently confirm that target, root, state key, plan checksum, and approval match. If anything differs, stop and return to planning/review. Do not use `-auto-approve` to bypass the human gate or apply from an unreviewed plan.

## 5. Verify, record, and clean up

- Verify the deployed resources against the approved plan: ownership, tags, security/exposure, health, expected outputs, and that no unexpected resources or deletions occurred. Handle sensitive outputs privately and never add their values to Git or the work log.
- Update the non-secret resource inventory with the task, owner, account/Region, state key, resource identifiers, tags, status, expected spend/retention, verification evidence, and cleanup action. Record the exact code revision, plan checksum, approver, applier, and verification result in the task work log.
- Clean up only resources owned by the task/root and only after an exact cleanup plan has received separate human review and approval. Verify the resulting state and inventory; preserve resources, state, and versions owned by other tasks.
- Everyone is responsible for cleanup, with the starter of the resources responsible first. Transfer that responsibility explicitly if the starter becomes unavailable.

## Stop and recovery conditions

Stop without applying if identity, Region, root/state key, ownership, permissions, approval, cost, or plan contents do not match; if the plan includes unexpected replacements/deletions or exposure; or if Terraform reports an unexplained lock/state conflict. Do not delete a lock manually, force-push state, or retry a failed migration blindly. Follow the bootstrap recovery runbook and obtain a reviewed recovery decision. No backend provisioning, state migration, AWS resource mutation, or cleanup is authorized merely by this document.
