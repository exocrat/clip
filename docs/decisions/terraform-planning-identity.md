# DEC-06 — Terraform identity for PD-16

**Date:** 2026-10-19

**Origin:** PD-16 Step 5.

## Question
Which AWS identity should PD-16 use for planning and non-root cloud operations?

## Options considered
- Pause until a scoped non-root planning identity is available.
- Use the root identity temporarily, with a narrow task and action boundary.

## Selected choice
The user authorized the configured `default` profile for PD-16 Step 5 plan preparation only; STS identifies it as the account root principal. The user later directed that the verified `adityalaxmi1` IAM user be used for non-root operations. STS confirms it belongs to account `335523638354`. Use this profile for PD-16 apply/provisioning and other non-root AWS operations, with each cloud action still subject to its exact-plan or operation approval gate.

## Rationale
The root exception enabled plan preparation while no separate identity was available. The user then supplied and authorized a non-root profile, reducing the need for root credentials in subsequent operations.

## Implications
The target remains account `335523638354`, Region `ap-south-1`, and the reviewed shared/test state. Verify the caller identity before each operation. Changed saved plans require exact checksum review and approval before apply; other cloud operations retain their separate approval gates.

## Approver
User in the current session; name not recorded.

## Supersedes
The root-only planning restriction is superseded for non-root operations by the user's authorization of `adityalaxmi1`; the exact-plan and operation approval gates remain.


## Billing-only root exception — 2026-10-19

During PD-16 Step 8 input review, IAM GetCredits was denied. The user explicitly authorized existing profile `default` (STS-verified root in account `335523638354`) for read-only billing only. It was used for STS/GetCredits to refresh eligible headroom; no root provisioning, Terraform plan, state access, IAM/SSM operation or deployment is authorized by this exception. All non-root cloud actions retain their existing exact approvals. Approver: user in the current session; personal name not recorded. The old billing receipt is recoverable through the [evaluation history guide](../evaluation/README.md).
