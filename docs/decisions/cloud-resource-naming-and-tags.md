# DEC-03 — Cloud resource naming and tags

**Date:** 2026-10-17

## Question
How should future CLIP cloud resources be named and tagged consistently across services?

## Options considered
- Use the earlier scope/purpose-oriented name and `CleanupBy` tag convention.
- Use a shorter environment/resource/region/unique-suffix name and a small stable set of project/accountability/expiry tags, adapting to service constraints.

## Selected choice
Where supported by the service, name resources `clip-<environment>-<resource>-ap-south-1-<unique-suffix>` using lowercase ASCII letters, digits, and hyphens. Apply tags `Project=CLIP`, `Environment=<approved environment>`, `Owner=<named accountable person>`, `Task=<task ID or domain>`, and `ExpiresOn=YYYY-MM-DD`.

Service-specific naming/tag limits and unsupported or inapplicable fields must be documented as narrow exceptions with the resource identifier, reason, accountable owner, and expiry/cleanup handling. Names and tags must not contain credentials, secrets, personal email addresses, account IDs, or user/listing data. The convention does not authorize resource creation, modification, or adoption of existing resources.

## Rationale
Rahul selected a simple, region-explicit name and consistent project, environment, accountability, task, and expiry metadata for resources created through later reviewed infrastructure plans.

## Implications
PD-14 cloud inventory and environment records use this convention. Future infrastructure plans should implement it for supported resources and state exact exceptions. Existing account resources remain excluded from CLIP use unless separately reviewed and approved.

## Approver
Rahul

## Supersedes
The earlier Step 7 naming/tagging convention in [cloud inventory](../environment/cloud-inventory.md).
