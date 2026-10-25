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
PD-08 specifies retirement/profile-removal timestamps, a continuous-eligibility anchor and conditional live/retired field constraints. Mandatory seller price, required fields and usable images still apply to live listings. Affected owners must review safe object cleanup, destructive current-offer/FK cleanup ordering, and profile/external-identity retirement. The API no-write-marker order and race handling are approved separately below. Failed object deletion retains only the cleanup metadata needed for safe retry and is reported as pending, never falsely recorded as deleted. No blanket cascade or new public deletion endpoint is approved.

The [private-data retention policy](private-data-retention.md) still governs shorter windows and backup/restore reconciliation. Actual cleanup implementations, destructive runs, cloud resources and exact object-store operations retain their normal gates.

## Approved API-only retirement coordination — 2026-10-20

The user approved the following coordination rule for Listings and Search to
use before their separate local content cleanup:

1. The owning domain rechecks the existing retirement eligibility rule and
   commits a unique pending operation ID and its server-derived activity
   cutoff on its own listing/request. Keep the pair together so a retry after
   restart sends the identical request. While the result is unresolved, the
   origin is hidden from discovery and cannot be reopened, edited, or used to
   start a new thread.
2. The owner calls Conversations' `get_origin_activity` as a preflight. An
   error or incomplete result fails closed and leaves the origin pending.
3. The owner calls `mark_origin_retired` with the same operation ID and
   cutoff. Conversations locks all associated threads in ascending UUID order,
   checks every participant-write time, and either marks all threads as
   no-write or marks none. Message, offer and contact-share writes take the
   same thread lock; the server sets activity time after locking. A write that
   wins first can block retirement; a marker that wins first makes the waiting
   write fail.
4. The result is `{outcome, marked_count}`. `marked` includes zero threads;
   `blocked_recent_activity` means no threads were changed; `already_marked`
   means the origin's threads already carry the marker. The same operation ID
   and request replays the saved result. Reusing an ID for a different origin
   or cutoff conflicts. A blocked result clears both pending fields and a
   later attempt uses a new ID and cutoff. An unknown result keeps both fields
   and retries with the same ID and cutoff.

This approves API calls, lock order, race behavior and retry behavior only. It
does not approve the method/order for clearing origin content, deleting image
objects, or purging Conversations content. Each domain still needs its own
cleanup method/order approval before implementing those destructive actions.
No cross-domain trigger, one-time SQL backfill, shared database session or
cascade may replace the public API calls. Migration
`20261020142319_api_owned_retirement_and_trigger_boundaries.sql` implements
the database storage and local trigger boundary. Its PostgreSQL 18.6 disposable
apply/rollback/reapply and focused marker checks passed; the native schema
inventory and corresponding C/D contract reviews remain pending. Listings
retirement coordination and its approved local cleanup now have isolated service
implementations; real Conversations and object-storage integration remain pending.

## Approved Listings-owned content/image cleanup — 2026-10-20

After Conversations confirms `marked` or `already_marked`, Listings performs
one local transaction. It verifies the same pending operation ID and cutoff,
marks the listing retired and unavailable, clears the listing's user-entered
content and buyer selection, marks attached images retired, and clears the
pending pair. Existing retirement triggers scrub create request/result payloads
and delete seller availability/selection receipts. The listing/owner IDs and
the content-free create-operation key remain; Search saved references remain
unchanged. Conversations content is not touched by this transaction.

Image rows already contain `retired_at` and the exact object key, so they serve
as durable cleanup work without a new table. A Listings-owned worker processes
only retired images whose parent listing is retired. It calls the storage
adapter with that exact key. Only after storage confirms deletion or absence
does the worker delete the image and upload rows together. A failed or unknown
storage result keeps both rows, allowing an idempotent retry. Deleting the
object before scrubbing the listing is prohibited because a failed object
delete must not leave a live listing pointing at an inaccessible image.

This approval covers the Listings local transaction and retryable image cleanup
order. It does not provide a real object-storage adapter or deploy/schedule a
worker; those real integrations remain later LI-02 work. Retired listings stay
omitted from My Listings under the current contract. Showing a content-free
retired marker remains a separate follow-up decision.

## Owner management-view follow-up

Unavailable listings must remain visible in the seller's "My Listings" view
while their listing content is retained. The user asked that owner visibility
after retirement be studied. It is not yet decided whether the retired listing
should appear there as a content-free marker or be omitted. This follow-up does
not change the approved retirement trigger, timing, or content-cleanup rules.

## Approver
Mohit (C), explicit approval of the consolidated remaining package. The user later confirmed the PD-08 affected-owner/privacy gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). Domain implementation must still follow the stated cleanup and ordering safeguards.

## Supersedes
None; refines the previously open origin/metadata retirement policy.

## Approved Search-owned request/receipt cleanup — 2026-10-25

Mohit verified the SE-02 wanted API checkpoint and approved the concrete local
order in [wanted-request retirement](../architecture/wanted-request-retirement.md):
persist/reuse the server-owned pending operation/cutoff, use Conversations public
preflight plus authoritative all-or-none marker, then lock/recheck the exact
request/pair and 180-day eligibility. In one Search transaction first clear both
JSON payloads in every wanted-command receipt, then clear request title,
description, category and budget, mark retired/unavailable, clear the pending
pair and advance revision/update time. Keep content-free request/author and
retry-key references plus existing lifecycle timestamps. A local failure rolls
back both scrub stages; unknown marker results keep the original pending pair.

Blocked-recent-activity clears only the matching pair and removes no content.
An older attempt cannot clear a newer pair. Reads hide retired content, late
retained-key retries conflict, and no request can reopen after retirement.
No other domain row, saved reference or storage object is modified/deleted.
The internal operation processes one server-selected request per explicit call;
no browser route, startup cleanup, worker/scheduler or shared/live-data run is
approved. Isolated implementation/tests now exist; actual Conversations
provider/race integration remains a required real acceptance gate.
