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
