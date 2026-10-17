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

## Change and safety rules

1. Keep each resource in exactly one root state and assign one accountable task owner before adding it.
2. Shared test resources belong to PD-16; domain roots may consume them but must not duplicate or adopt them. Domain roots manage only exclusive resources.
3. Use the root's fixed state key and default workspace. Do not use workspace names to separate environments or owners.
4. Keep state, backups, plans, credentials, and sensitive outputs out of version control and ordinary logs.
5. Follow the documented plan/review/apply/verify/cleanup gates. A task owner who starts resources has first responsibility for cleanup, with the team-wide responsibility recorded in the project operating decisions.

The exact resource inventory, module interfaces, and infrastructure permissions remain subject to the owning task's reviewed design and approval. PD-14 least-privilege verification is deferred; this document does not imply that access controls have been tested or narrowed.
