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

## Approved cross-domain implementation sequence

Listings owner B (Suraj) approved the following implementation direction on
2026-10-20. It preserves the existing 180-day continuous origin-eligibility
rule and separately requires every associated conversation's latest
participant-write time to be at or before the server-derived activity cutoff
(`server_now - 2160 hours`). The 90-day rule does not replace the 180-day rule.

1. Listings or Search rechecks its own origin under a short transaction, sets a
   stable `retirement_pending_operation_id`, and commits. Pending origins block
   reopening/edits, selection or offer changes that could invalidate
   retirement, and new origin conversations; they are hidden from discovery.
   This does not block participant writes in existing threads before the
   Conversations marker. The owner never holds the origin lock while calling
   Conversations.
2. The origin owner calls Conversations' `get_origin_activity` as a preflight.
   Unknown/incomplete results and dependency failures defer retirement; they
   never mean zero activity.
3. The origin owner calls `mark_origin_retired` with the same operation ID and
   cutoff `server_now - 2160 hours`, computed on the server after its
   authoritative eligibility check, never from browser input. Conversations
   locks all associated threads in ascending thread-ID order, rechecks
   server-recorded participant activity, then marks every eligible thread
   no-write in one transaction. Any too-recent thread means
   none are marked. Participant messages, offer revisions/withdrawals and
   contact shares use that same thread lock and receive server timestamps
   after acquiring it.
4. Store `origin_kind`, `origin_id`, `cutoff_utc`, outcome and marked count
   beside a globally unique operation ID. Same-ID/same-request retries return
   the original outcome; reuse for another origin or cutoff is a stable
   conflict without changes. `marked` with zero threads is success;
   `blocked_recent_activity` marks none; `already_marked` means every related
   thread was marked before this operation, and its `marked_count` is the
   number of those existing markers. Mixed marker state must stop for
   Conversations-API reconciliation.
5. A blocked result clears pending state without clearing content; a later
   attempt uses a new operation ID. An unknown result leaves the origin
   pending and retries/lookups use the same ID. Only a confirmed marker permits
   the origin owner to clear its own content, through the separately reviewed
   cleanup mechanism. If cleanup fails, keep the origin pending and retry it;
   after success, set `retired_at` and clear the pending operation ID in the
   same origin-owner transaction. No destructive content/object cleanup is
   authorized by this sequence alone.

Cross-domain business checks must not read/write another domain's tables from
a trigger, SQL function or migration, including a one-time backfill. Use the
owning domain's declared public interface. Keep approved cross-domain foreign
keys and local database protections such as sequence ordering and immutable
thread identity. PostgreSQL triggers cannot call Python public functions, so
the migration replaces only affected trigger definitions and moves
cross-domain checks to owner-service orchestration; it does not remove the
triggers wholesale.

The shared migration has one writer (Listings B/Suraj); Search C and
Conversations D review the portions affecting their domains, and A coordinates
integration at INT-01. Before applying it to any persistent database, inspect
that exact target and reconcile selected buyers/retired origins through
owner APIs. Never infer that a target is empty. The migration, shared-database
apply, and destructive content/object cleanup retain their separate review and
approval gates.

## Approver
Mohit (C), explicit approval of the consolidated remaining package. The user later confirmed the PD-08 affected-owner/privacy gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). Domain implementation must still follow the stated cleanup and ordering safeguards.

## Supersedes
None; refines the previously open origin/metadata retirement policy.
