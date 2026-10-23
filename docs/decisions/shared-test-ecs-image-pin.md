# Pin the shared test ECS host image

**Date:** 2026-10-23
**Origin:** ID-01 Step 2 shared-role non-applying plan scope correction.

## Question
How should an IAM-only change avoid an unrelated host-image upgrade?

## Options considered
- Include the refreshed recommended ECS AMI and resulting launch-template/ASG updates in a separate infrastructure upgrade review.
- Pin the existing deployed image so ordinary plans preserve it.

## Selected choice
Pin `ami-0c10ee7b040aa465e`, the image in the deployed shared test launch-template
version 1, as `local.ecs_ami_id` in `infra/terraform/shared/test/locals.tf`.
Remove the mutable recommended-image SSM data source and reference this constant
from the launch template through `sensitive(local.ecs_ami_id)` to retain the
prior SSM-derived sensitivity metadata. The first pinned-image plan showed
identical values but an unwanted update removing that marker; Aditya approved
preserving it. This preserves the current account/region-specific
image; it does not select a new image, restart hosts or bypass Terraform refresh.

## Rationale
The [non-applying plan](../evaluation/identity/id-01-step-2/cloud-plan-result.md)
refreshed the recommendation to `ami-08e0d7fb58f08ac36`, unexpectedly proposing
launch-template and ASG updates alongside an SES IAM policy. Aditya approved
preserving the existing image instead of expanding this permission-only change.

## Implications
Shared test account `335523638354`, region `ap-south-1`, PD-16-owned root/state.
The pin does not prove ongoing patch/security currency or future launchability.
Before future compute runs, review the image's availability and suitability;
image upgrades need an explicit source change and their own reviewed plan/checks.
A fresh full non-applying plan must confirm the intended one-policy-create scope;
local validation cannot establish cloud convergence. Preserve stopped compute,
service phase and all approved inputs. No apply or live send is authorized here.

## Approver
Aditya (A), approved the existing-image pin correction on 2026-10-23.

## Supersedes
The shared test root's implicit latest-recommendation lookup behavior only.
