-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Persist the owner-scoped retry key and the metadata declared when the upload
-- intent is created. Existing upload rows predate this command API, so they get
-- their own ID as a one-time operation key; verified historical rows copy the
-- already confirmed metadata.
ALTER TABLE listings.image_uploads
    ADD COLUMN operation_id uuid,
    ADD COLUMN requested_media_type text,
    ADD COLUMN requested_size_bytes bigint;

UPDATE listings.image_uploads
SET operation_id = id,
    requested_media_type = confirmed_media_type,
    requested_size_bytes = confirmed_size_bytes;

ALTER TABLE listings.image_uploads
    ALTER COLUMN operation_id SET NOT NULL,
    ADD CONSTRAINT upload_owner_operation_unique UNIQUE (owner_id, operation_id),
    ADD CONSTRAINT upload_requested_metadata_pair
        CHECK ((requested_media_type IS NULL) = (requested_size_bytes IS NULL)),
    ADD CONSTRAINT upload_requested_media_type
        CHECK (requested_media_type IS NULL OR requested_media_type IN
            ('image/jpeg', 'image/png', 'image/webp')),
    ADD CONSTRAINT upload_requested_size
        CHECK (requested_size_bytes IS NULL OR requested_size_bytes BETWEEN 1 AND 10485760);

-- A separate guard keeps the original intent and retry identity immutable
-- without changing the existing state/confirmation guard.
CREATE FUNCTION listings.guard_upload_intent() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF ROW(NEW.operation_id, NEW.requested_media_type, NEW.requested_size_bytes)
        IS DISTINCT FROM ROW(OLD.operation_id, OLD.requested_media_type, OLD.requested_size_bytes) THEN
        RAISE EXCEPTION 'Upload request identity is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER upload_intent_history BEFORE UPDATE ON listings.image_uploads
    FOR EACH ROW EXECUTE FUNCTION listings.guard_upload_intent();

COMMENT ON COLUMN listings.image_uploads.operation_id IS
    'Owner-scoped idempotency key for creating an image upload intent.';
COMMENT ON COLUMN listings.image_uploads.requested_media_type IS
    'Client-declared type accepted for intent creation; never authoritative confirmation metadata.';
COMMENT ON COLUMN listings.image_uploads.requested_size_bytes IS
    'Client-declared size accepted for intent creation; never authoritative confirmation metadata.';

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

DROP TRIGGER upload_intent_history ON listings.image_uploads;
DROP FUNCTION listings.guard_upload_intent();

ALTER TABLE listings.image_uploads
    DROP CONSTRAINT upload_requested_size,
    DROP CONSTRAINT upload_requested_media_type,
    DROP CONSTRAINT upload_requested_metadata_pair,
    DROP CONSTRAINT upload_owner_operation_unique,
    DROP COLUMN requested_size_bytes,
    DROP COLUMN requested_media_type,
    DROP COLUMN operation_id;
