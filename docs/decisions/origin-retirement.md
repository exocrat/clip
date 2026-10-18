# Inactive origin content retirement and minimal references

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 consolidated lifecycle/storage review.

## Question
How do old listing/request details retire while saved references and conversation uniqueness remain valid?

## Options considered
- Retire original content after a finite inactivity window, retaining minimal references.
- Preserve original details indefinitely or physically cascade parent deletion into saves/conversations, conflicting with privacy or retained-reference behavior.

## Selected choice
Retire Sale Listing/Wanted Request details after 180 days continuously unavailable or past the availability end, and at least 90 days without a participant write in every associated conversation. Reopening/window edits that restore eligibility reset the inactivity clock; logout or temporary-account expiry alone is not this trigger. Apply the separately approved shorter auth/contact/conversation retention windows independently.

Remove original title, description, pickup/price/condition/category/selection details and associated image/content/offer references through the reviewed retirement path. Preserve minimal content-free origin/thread/account UUID and uniqueness references for the service's operating lifetime. Saved references may point to retired origins but expose no old details; retired origins accept no new conversation, offer or reopen. Retained identifiers/relationships are linkable data, not anonymous data.

## Rationale
Bounds old content without turning availability changes into immediate deletion or breaking saved pointers and origin-pair uniqueness.

## Implications
PD-08 specifies retirement/profile-removal timestamps, a continuous-eligibility anchor and conditional live/retired field constraints. Mandatory seller price, required fields and usable images still apply to live listings. Affected owners must review safe object cleanup, current-offer/FK/marker ordering and profile/external-identity retirement. Failed object deletion retains only the cleanup metadata needed for safe retry and is reported as pending, never falsely recorded as deleted. No blanket cascade or new public deletion endpoint is approved.

The [private-data retention policy](private-data-retention.md) still governs shorter windows and backup/restore reconciliation. Actual cleanup implementations, destructive runs, cloud resources and exact object-store operations retain their normal gates.

## Approver
Mohit (C), explicit approval of the consolidated remaining package. Affected-owner/privacy review remains pending.

## Supersedes
None; refines the previously open origin/metadata retirement policy.
