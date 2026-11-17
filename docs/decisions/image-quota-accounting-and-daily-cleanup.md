# Image-quota accounting and once-daily reclamation

**Date:** 2026-11-17

**Origin:** Red-team issue #69 triage (cancelled/expired uploads keep consuming the 200 MiB per-account image quota).

## Question
Should the per-account image-upload quota immediately stop counting a cancelled or expired upload, and how should a seller who reaches the cap be told what to do?

## Options considered
- Exclude `failed`/`expired` rows from the quota sum (or delete the row on cancel) so space frees instantly.
- Keep counting reserved bytes until a scheduled cleanup confirms the stored object is gone, reclaim space on a fixed daily cadence, and show a clear cap message meanwhile.

## Selected choice
Keep the quota as a sum of reserved bytes over **all** of an owner's `image_uploads` rows, including `failed` (cancelled) and `expired` intents, until a reclamation job deletes the object and row. A cancelled intent keeps its original ~24 h expiry; a **once-daily** reclamation runs the existing `ListingsService.cleanup_image_objects` path, which deletes the storage object and then removes the row (with its built-in retry/defer on an uncertain delete). Space therefore frees after the intent expires and the next daily run reclaims it — in practice within a couple of days, consistent with the ~48 h window already described in [image-upload-staging](./image-upload-staging.md).

The reclamation runs **in-process inside the API** (not a separate ECS task, schedule, or instance): a background task started in the application lifespan waits a configurable interval (default 24 h) and runs one cycle. With more than one API replica a PostgreSQL session advisory lock elects a single leader per cycle, so the pass runs once rather than once per replica; the store's own `FOR UPDATE … SKIP LOCKED` claim keeps it safe alongside live traffic regardless. It uses the API's existing database pool and S3 storage and the API task role (which already holds `s3:DeleteObject` on the images bucket), so it needs no new AWS resource, IAM change, or cloud approval — it ships with a normal API deploy. `CLIP_IMAGE_CLEANUP_ENABLED=false` disables it without a code change.

When a `create_image_upload` is refused at the cap, the API returns `409 conflict` carrying the field-error code `account_image_quota_exceeded` (distinct from other upload conflicts). The web client maps that code to a clear message: "You have uploaded too many images. Please delete a few images from your listings and try again in a few days," instead of the previous misleading "This photo upload expired."

This is a **deliberate, bounded limitation**, not an unknown defect: counting reserved bytes until deletion is confirmed is what prevents an upload→cancel→repeat loop from storing unbounded orphaned objects while the quota reads empty.

## Rationale
The quota's purpose is to bound **stored** bytes. Freeing a cancelled intent's quota before its object is confirmed deleted would let a client store far more than 200 MiB of orphaned objects between cleanup runs (the client holds a presigned PUT and may have already uploaded the object before cancelling). Reclaiming on a fixed daily cadence keeps the storage guarantee intact, reuses machinery that already exists, and adds no per-request S3 latency on the cancel path. A once-daily cadence is sufficient for the project's expected per-account image volume; the cost of a short cap window is an honest, actionable message rather than silent lockout.

## Implications
- API: the quota check attaches `FieldError("size_bytes", "account_image_quota_exceeded")` to the `409`; no new status code or contract enumeration is required (field-error detail codes are free-form, as with `demo_listing_limit_reached`).
- Web: `ListingsApiError` surfaces the detail `code`; the photo-upload flow shows `ACCOUNT_IMAGE_QUOTA_MESSAGE` for the capped case and keeps the expired-upload message for other `409`s.
- The daily cadence lives in `apps/api/app/domains/listings/image_cleanup_scheduler.py`, started from `_marketplace_lifespan` in `apps/api/app/application.py` when Listings has S3 storage and `CLIP_IMAGE_CLEANUP_ENABLED` is true; it is cancelled cleanly on shutdown. Two settings were added (`image_cleanup_enabled`, `image_cleanup_interval_seconds`) with deploy-safe defaults, so the live configuration needs no change.
- The entrypoint `scripts/listings_image_cleanup.py` remains as the **manual/ops** tool: dry-run (default) counts eligible rows and touches no storage; `--apply` runs the same `cleanup_image_objects` passes. It mirrors the target-DB guard and content-free output of `scripts/conversations_cleanup.py` and is useful for audits or an immediate backfill.
- Because the schedule is in the app, a normal API **deploy** both ships the clearer message and starts reclaiming — no separate cloud/infra step. Reclamation only runs while the API is up (true of any option; the quota only matters while the site serves), so a fully idle environment reclaims nothing until it is running again.
- No change is made to the quota sum, to the cancel path's `expires_at`, or to object-deletion ordering; the anti-abuse guarantee is preserved.

## Approver
Aditya (Cumulonimbus dev decision for #69), 2026-11-17. Listings remains Suraj's (B) domain; the scheduling/cloud step keeps its separate approval. This records the devs' intended design so the behaviour is a documented limitation, not an unexplained defect.

## Supersedes
None. Complements [image-upload-staging](./image-upload-staging.md) and the manual-cleanup posture in [DEC-09](./database-task-deadlines-and-manual-image-cleanup.md).
