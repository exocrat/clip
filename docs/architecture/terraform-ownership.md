# Terraform ownership and state boundaries

This document defines planned Terraform root configurations, state-object keys, and module ownership. It complements [DEC-01](../decisions/terraform-state-ownership.md) and [DEC-02](../decisions/terraform-backend-design.md). These boundaries do not authorize backend creation, state migration, cloud changes, or apply operations.

## Root configurations and state

Use the default Terraform workspace in each root configuration. Terraform workspaces are not an ownership or security boundary. When the approved S3 backend is later configured, each root uses its own exact state-object key:

| Root configuration | State key | Resource owner | Boundary |
|---|---|---|---|
| `infra/terraform/bootstrap/` | `bootstrap/terraform.tfstate` | PD-15 / Stream 4 (Rahul) | State-bucket bootstrap and its supporting configuration only. |
| `infra/terraform/shared/test/` | `shared/test/terraform.tfstate` | PD-16 integration owner | Shared test-environment resources only. |
| `infra/terraform/domains/identity/test/` | `domains/identity/test/terraform.tfstate` | Identity domain task owner | Identity-exclusive resources only. |
| `infra/terraform/domains/listings/test/` | `domains/listings/test/terraform.tfstate` | Listings/Images domain task owner | Listings/Images-exclusive resources only. |
| `infra/terraform/domains/search/test/` | `domains/search/test/terraform.tfstate` | Search/Wanted/Saved domain task owner | Search/Wanted/Saved-exclusive resources only. |
| `infra/terraform/domains/conversations/test/` | `domains/conversations/test/terraform.tfstate` | Conversations domain task owner | Conversations-exclusive resources only. |

Do not initialize these configurations against a remote backend until its exact bucket, target account/Region, credentials, access, plan, and migration/creation approvals pass their separate gates. The bootstrap root remains local-backend-only until the state bucket exists and migration is explicitly approved.

## Module ownership

- `infra/terraform/modules/shared/` is the home for reusable, non-secret modules that manage shared capabilities. The PD-16 owner is responsible for shared module changes and reviews.
- `infra/terraform/modules/domains/<domain>/` is the home for reusable modules owned by that domain's task owner. The initial domain slugs are `identity`, `listings`, `search`, and `conversations`.
- Root configurations compose modules only within their resource ownership boundary. A domain root must not declare or import shared resources into its state; it consumes explicitly reviewed shared identifiers and interfaces instead.
- Do not add speculative modules or cloud resources merely to populate these directories. Add a module only when an approved task identifies its capability, inputs/outputs, owner, and tests.

## Shared identifiers, secrets, and permissions

- The shared root is the source of ownership for shared resource identifiers. Publish only the explicitly needed, non-secret IDs, ARNs, and endpoints as reviewed outputs or non-secret AWS Systems Manager Parameter Store `String` parameters under the agreed `/clip/` namespace. Exact parameter names are selected when the corresponding shared resources exist; consumers must not invent competing names.
- A domain root receives only the identifiers it needs through explicit, typed module inputs or the approved non-secret parameter interface. Do not use another root's state as a general-purpose interface: Terraform remote-state access exposes the source state's outputs/state data and can create broad read access and ownership ambiguity. A consumer may reference shared resources but must not recreate, import, mutate, or delete them.
- Never pass secret values through Terraform module inputs/outputs, state, plans, resource tags, user data, or ordinary logs. Pass a secret reference (approved parameter name/ARN) only. The application/runtime retrieves the value from the approved secret store using its runtime role; prefer `SecureString` for secret values. The Terraform authoring identity should not read secret values merely to configure a resource.
- The shared root owns shared runtime roles and shared-resource policies. Each domain root owns only its domain-specific runtime roles and policies. A domain requests access to a shared capability through an explicit, reviewed interface; it must not attach permissions to or rewrite a role/policy owned by another root. Do not grant a domain direct access to another domain's private resources; cross-domain application behavior uses that domain's public contract.
- The team has selected SSM Parameter Store and simple paths under `/clip/` as the intended parameter convention. The current [secret-handling record](../environment/secret-handling.md) still says the shared access method and references are not configured. The team expectation that all four members can read, write, and manage parameters is not evidence that effective permissions have been tested. PD-14 least-privilege verification remains deferred; no IAM policy is created or approved by this design note.

These are interface and ownership rules, not a claim that parameter paths, secret references, runtime roles, or effective permissions have been provisioned. Record actual non-secret references and approved access procedures in the canonical secret-handling record when they are established.

## Change and safety rules

1. Keep each resource in exactly one root state and assign one accountable task owner before adding it.
2. Shared test resources belong to PD-16; domain roots may consume them but must not duplicate or adopt them. Domain roots manage only exclusive resources.
3. Use the root's fixed state key and default workspace. Do not use workspace names to separate environments or owners.
4. Keep state, backups, plans, credentials, and sensitive outputs out of version control and ordinary logs.
5. Follow the documented plan/review/apply/verify/cleanup gates. A task owner who starts resources has first responsibility for cleanup, with the team-wide responsibility recorded in the project operating decisions.

The exact resource inventory, module interfaces, and infrastructure permissions remain subject to the owning task's reviewed design and approval. PD-14 least-privilege verification is deferred; this document does not imply that access controls have been tested or narrowed.
