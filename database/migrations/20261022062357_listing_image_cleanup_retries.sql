-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Keep retry timing next to the private object reference. A cleanup failure
-- delays only that object so one unavailable S3 key cannot block later work.
ALTER TABLE listings.image_uploads
    ADD COLUMN cleanup_retry_after timestamptz(6);

ALTER TABLE listings.images
    ADD COLUMN cleanup_retry_after timestamptz(6);

CREATE INDEX image_uploads_cleanup_due
    ON listings.image_uploads
        (expires_at, id) INCLUDE (cleanup_retry_after);

CREATE INDEX images_cleanup_due
    ON listings.images
        (retired_at, id) INCLUDE (cleanup_retry_after)
    WHERE retired_at IS NOT NULL;

COMMENT ON COLUMN listings.image_uploads.cleanup_retry_after IS
    'Next eligible retry time for deleting an expired unattached S3 image; null means never attempted.';
COMMENT ON COLUMN listings.images.cleanup_retry_after IS
    'Next eligible retry time for deleting a retired S3 image; null means never attempted.';

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

DROP INDEX listings.images_cleanup_due;
DROP INDEX listings.image_uploads_cleanup_due;

ALTER TABLE listings.images
    DROP COLUMN cleanup_retry_after;

ALTER TABLE listings.image_uploads
    DROP COLUMN cleanup_retry_after;
