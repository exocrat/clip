# Durable image upload staging without public draft listings

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 consolidated lifecycle/storage review.

## Question
How can uploads be tracked before a listing has its required usable images?

## Options considered
- Separate owner-bound upload intents and verified usable image references.
- Expose incomplete listings or keep no durable upload/confirmation state, weakening publication and abandoned-object reconciliation.

## Selected choice
Use Listings-owned `image_uploads` with pending/confirmed/failed/expired state, controlled unique object key, owner and original expiry. Pending and confirmed-but-unattached intents expire 24 hours after creation. Remove abandoned-object metadata within another 24 hours after expiry/failure once cleanup is safe; preserve the object key until actual deletion/absence is confirmed. Confirmed attached intent/image references remain until their image is retired. Do not introduce a public draft listing.

## Rationale
Keeps the required-image publication invariant while supporting upload confirmation, failure and abandoned-object cleanup.

## Implications
PD-08 proposes an upload-intent FK from each usable image and conditional timestamp/state checks. LI-02 must implement actual content/size/ownership validation and locking so cleanup cannot delete a concurrently attached image. Metadata state alone does not prove object existence or successful cloud deletion. Runtime signed-URL expiry/decoder/provider details retain their own review gates, and exact cloud operations require their existing approvals.

## Approver
Mohit (C), explicit approval of the consolidated remaining package. The user later confirmed the PD-08 affected-owner/platform gates complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). LI-02 still owns implementation and cleanup-race checks.

## Supersedes
None.
