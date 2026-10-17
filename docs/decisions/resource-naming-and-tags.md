# DEC-03 — Cloud resource naming and tagging convention

**Date:** 2026-10-17

## Question
What common names and tags should CLIP use so resources can be identified, assigned, and cleaned up consistently across AWS services?

## Options considered
- Let each task choose names and tags independently. This is flexible but makes ownership, inventory, and cleanup inconsistent.
- Use one project prefix and a small common tag set while allowing service-specific constraints. This is consistent without assuming every AWS service supports the same name or tags.

## Selected choice
- Where the service permits, name resources using the lowercase pattern `clip-<environment>-<resource>-ap-south-1-<unique-suffix>`.
- Follow each service's character, length, and uniqueness rules. Resolve the exact name and unique suffix in the reviewed resource plan before creation.
- Apply the following tags wherever the resource type supports them: `Project=CLIP`; `Environment=<approved environment identifier>`; `Owner=<named person accountable for the resource and cleanup>`; `Task=<owning task ID or approved domain slug>`; `ExpiresOn=<YYYY-MM-DD cleanup/expiry review date>`.
- The person starting a resource has first cleanup responsibility. The Owner tag identifies the named person accountable for the resource and cleanup; record any distinction in the plan.
- Do not put credentials, secret values, personal email addresses, or other sensitive data in resource names or tags. If a service does not support a tag or the expiry convention, record that limitation in the approved plan and inventory.
- The Terraform state bucket retains its specific naming pattern from DEC-02: `clip-tfstate-335523638354-ap-south-1-<unique-suffix>`.

## Rationale
A shared project prefix and ownership/lifecycle tags improve account-wide discovery and cleanup. Allowing service-specific constraints avoids invalid names or implying that every service supports tags. Requiring an approved plan to select exact names and dates keeps this convention separate from authorization to create resources.

## Implications
Later cloud plans must include exact resource names, tag values, and expiry/review dates (or explain unsupported fields). The environment guide records this convention. This decision does not authorize resource creation, adoption, modification, or cleanup.

## Approver
Rahul (D), who verified the PD-14 Step 7 naming/tagging convention on 2026-10-17.

## Supersedes
The proposed general tag-field list in [DEC-02](terraform-backend-design.md); DEC-02's specific Terraform state-bucket name pattern remains in force.
