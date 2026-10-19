# DEC-03 — Cloud resource naming and tags

**Date:** 2026-10-17

**Revision:** 2026-10-19 — user approved narrow existing-resource exceptions during PD-16 audit reconciliation.

## Question
How should future CLIP cloud resources be named and tagged consistently across services?

## Options considered
- Use the earlier scope/purpose-oriented name and `CleanupBy` tag convention.
- Use a shorter environment/resource/region/unique-suffix name and a small stable set of project/accountability/expiry tags, adapting to service constraints.

## Selected choice
Where supported by the service, name resources `clip-<environment>-<resource>-ap-south-1-<unique-suffix>` using lowercase ASCII letters, digits, and hyphens. Apply tags `Project=CLIP`, `Environment=<approved environment>`, `Owner=<named accountable person>`, `Task=<task ID or domain>`, and `ExpiresOn=YYYY-MM-DD`.

Service-specific naming/tag limits and unsupported or inapplicable fields must be documented as narrow exceptions with the resource identifier, reason, accountable owner, and expiry/cleanup handling. Names and tags must not contain credentials, secrets, personal email addresses, account IDs, or user/listing data. The convention does not authorize resource creation, modification, or adoption of existing resources.

## Existing PD-15/16 exceptions — approved 2026-10-19

Retain existing deployed PD-15/16 names, including the account-qualified state bucket and `clip-shared-test-*` names, to avoid replacing deployed resources or moving state merely for naming compliance. The [inventory](../environment/cloud-inventory.md#pd-1516-recorded-deployment--2026-10-19) lists known identifiers; additional existing identifiers must be inventoried before relying on them. These names lack the prescribed structure, and the bucket contains an account ID; these are explicit existing-resource exceptions, not approval for new nonconforming names. Future resources retain the original convention.

Resources remain shared team property. The current contributor explicitly volunteered as operator; their personal name has not been recorded and must not be inferred from stream/IAM labels. Record a durable name/contact before cross-contributor handoff. Existing `Owner=shared-team` is a documented tag deviation, not silently changed by this approval; any tag-only correction needs its own reviewed cloud plan unless separately accepted as an exception. Preserve the selected cleanup review date and per-action/idle cleanup gates. No rename, replacement, retag or cloud operation is authorized by this revision.

**Revision approver:** User in the current session, approving recommendation E; name not recorded.

## Rationale
Rahul selected a simple, region-explicit name and consistent project, environment, accountability, task, and expiry metadata for resources created through later reviewed infrastructure plans.

## Implications
PD-14 cloud inventory and environment records use this convention. Future infrastructure plans should implement it for supported resources and state exact exceptions. Existing account resources remain excluded from CLIP use unless separately reviewed and approved.

## Approver
Rahul

## Supersedes
The earlier Step 7 naming/tagging convention in [cloud inventory](../environment/cloud-inventory.md).
