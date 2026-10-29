# DEC-03 — Cloud resource naming and tags

**Date:** 2026-10-17

**Revision:** 2026-10-19 — user approved narrow existing-resource exceptions during PD-16 audit reconciliation and named Aditya as current operator.

## Question
How should future CLIP cloud resources be named and tagged consistently across services?

## Options considered
- Use the earlier scope/purpose-oriented name and `CleanupBy` tag convention.
- Use a shorter environment/resource/region/unique-suffix name and a small stable set of project/accountability/expiry tags, adapting to service constraints.

## Selected choice
Where supported by the service, name resources `clip-<environment>-<resource>-ap-south-1-<unique-suffix>` using lowercase ASCII letters, digits, and hyphens. Apply tags `Project=CLIP`, `Environment=<approved environment>`, `Owner=<named accountable person>`, `Task=<task ID or domain>`, and `ExpiresOn=YYYY-MM-DD`.

Service-specific naming/tag limits and unsupported or inapplicable fields must be documented as narrow exceptions with the resource identifier, reason, accountable owner, and expiry/cleanup handling. Names and tags must not contain credentials, secrets, personal email addresses, account IDs, or user/listing data. The convention does not authorize resource creation, modification, or adoption of existing resources.

## Existing PD-15/16 exceptions — approved 2026-10-19

Retain existing deployed PD-15/16 names, including the account-qualified state bucket and `clip-shared-test-*` names, to avoid replacing deployed resources or moving state merely for naming compliance. The [inventory](../environment/cloud-inventory.md) records known identifiers; additional existing identifiers must be inventoried before relying on them. These names lack the prescribed structure, and the bucket contains an account ID; these are explicit existing-resource exceptions, not approval for new nonconforming names. Future resources retain the original convention.

Resources remain shared team property. The user explicitly named Aditya as current PD-16 operator; update the assignment if responsibility changes and use existing roster/contact records for handoff. Do not infer a name from stream or IAM labels. The user explicitly approved `Owner=shared-team` for PD-16 resources, including new service-phase resources, with Aditya accountable as operator. This is a tag exception to the named-person value; it authorizes no IAM/tag mutation. Existing deployed names remain legacy exceptions; new ECS service/task-family and inline policy names follow the original region-explicit convention. The `/clip/test/database-probe-password` parameter keeps the separately approved secret namespace in DEC-05; inline IAM policies inherit accountability through their parent roles because they do not support independent resource tags. Preserve the selected cleanup review date and per-action/idle cleanup gates. No rename, replacement, retag or cloud operation is authorized by this revision.

**Revision approver:** User in the current session, approving recommendation E; name not recorded.

## Rationale
Rahul selected a simple, region-explicit name and consistent project, environment, accountability, task, and expiry metadata for resources created through later reviewed infrastructure plans.

## Implications
PD-14 cloud inventory and environment records use this convention. Future infrastructure plans should implement it for supported resources and state exact exceptions. Existing account resources remain excluded from CLIP use unless separately reviewed and approved.

## Approver
Rahul

## Supersedes
The earlier Step 7 naming/tagging convention in [cloud inventory](../environment/cloud-inventory.md).
