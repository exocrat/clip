-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- The reviewed owner view returns the conversation paired with the selected
-- buyer. Store that reference locally instead of reading Conversations tables
-- when rendering Listings management views.
ALTER TABLE listings.sale_listings
    ADD COLUMN selected_conversation_id uuid;

-- Create/edit commands receive upload IDs only. Persist the metadata verified
-- by the future LI-02 confirmation handler so Listings can attach the object
-- without trusting file details sent by the create/edit caller.
ALTER TABLE listings.image_uploads
    ADD COLUMN confirmed_media_type text,
    ADD COLUMN confirmed_size_bytes bigint;

-- Existing attached image rows already contain verified metadata; copy it to
-- their upload receipt. Unattached historical confirmations stay unusable by
-- the Listings writer until their verifier records metadata again.
UPDATE listings.image_uploads AS upload
SET confirmed_media_type = image.media_type,
    confirmed_size_bytes = image.size_bytes
FROM listings.images AS image
WHERE image.upload_id = upload.id;

ALTER TABLE listings.image_uploads
    ADD CONSTRAINT upload_confirmed_metadata_pair
        CHECK ((confirmed_media_type IS NULL) = (confirmed_size_bytes IS NULL)),
    ADD CONSTRAINT upload_confirmed_media_type
        CHECK (confirmed_media_type IS NULL OR confirmed_media_type IN
            ('image/jpeg', 'image/png', 'image/webp')),
    ADD CONSTRAINT upload_confirmed_size
        CHECK (confirmed_size_bytes IS NULL OR confirmed_size_bytes BETWEEN 1 AND 10485760);

COMMENT ON COLUMN listings.image_uploads.confirmed_media_type IS
    'Actual object media type recorded by LI-02 after storage inspection; client-declared type is not authoritative.';
COMMENT ON COLUMN listings.image_uploads.confirmed_size_bytes IS
    'Actual object size recorded by LI-02 after storage inspection; client-declared size is not authoritative.';

-- Do not read Conversations-owned threads to infer this Listings-owned value.
-- If a populated installation has an old buyer selection without its stored
-- conversation ID, fail closed below; resolve it through the Conversations
-- public interface before applying the migration.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM listings.sale_listings
        WHERE (selected_buyer_id IS NULL) <> (selected_conversation_id IS NULL)
    ) THEN
        RAISE EXCEPTION 'Existing selected buyer needs a Listings/Conversations API-resolved conversation before migration'
            USING ERRCODE = 'check_violation';
    END IF;
END;
$$;

ALTER TABLE listings.sale_listings
    ADD CONSTRAINT sale_selected_conversation_fkey
        FOREIGN KEY (selected_conversation_id)
        REFERENCES conversations.threads(id) ON DELETE RESTRICT,
    ADD CONSTRAINT sale_selection_pair_check
        CHECK ((selected_buyer_id IS NULL) = (selected_conversation_id IS NULL));

COMMENT ON COLUMN listings.sale_listings.selected_conversation_id IS
    'Conversation reference paired with selected_buyer_id; populated only after Listings validates membership through the Conversations public interface.';

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

ALTER TABLE listings.image_uploads
    DROP CONSTRAINT upload_confirmed_size,
    DROP CONSTRAINT upload_confirmed_media_type,
    DROP CONSTRAINT upload_confirmed_metadata_pair,
    DROP COLUMN confirmed_size_bytes,
    DROP COLUMN confirmed_media_type;

ALTER TABLE listings.sale_listings
    DROP CONSTRAINT sale_selection_pair_check,
    DROP CONSTRAINT sale_selected_conversation_fkey,
    DROP COLUMN selected_conversation_id;
