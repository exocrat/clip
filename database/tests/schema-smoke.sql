-- Disposable storage smoke, not a provider/crypto/auth/NFR test. Every record
-- is synthetic and the final rollback leaves catalogue/migration state alone.
-- A validated disposable-target runner must supply the connection (Step 6's
-- native-checks.sh currently does). The name check refuses an ordinary
-- application database before any fixture writes.
BEGIN;
DO $$
BEGIN
    IF left(current_database(), 10) <> 'clip_test_' THEN
        RAISE EXCEPTION 'Schema smoke requires an explicitly named clip_test_ database';
    END IF;
END;
$$;

DO $$
DECLARE
    seller uuid := gen_random_uuid();
    buyer uuid := gen_random_uuid();
    outsider uuid := gen_random_uuid();
    item uuid := gen_random_uuid();
    upload uuid := gen_random_uuid();
    image uuid := gen_random_uuid();
    thread uuid := gen_random_uuid();
    message uuid := gen_random_uuid();
    operation uuid := gen_random_uuid();
    seller_key uuid := gen_random_uuid();
    buyer_key uuid := gen_random_uuid();
    outsider_key uuid := gen_random_uuid();
    offer uuid := gen_random_uuid();
    offer_entry uuid := gen_random_uuid();
    reminder uuid := gen_random_uuid();
    message_time timestamptz;
    category uuid;
    rejected boolean;
    sequence_head bigint;
BEGIN
    IF (SELECT count(*) FROM listings.categories) <> 8
        OR (SELECT count(*) FROM listings.conditions) <> 4 THEN
        RAISE EXCEPTION 'Expected the approved initial catalogue';
    END IF;
    SELECT id INTO STRICT category FROM listings.categories WHERE code = 'books';
    INSERT INTO identity.users (id, account_class, status, display_name) VALUES
        (seller, 'regular', 'active', 'Synthetic seller'),
        (buyer, 'regular', 'active', 'Synthetic buyer'),
        (outsider, 'regular', 'active', 'Synthetic outsider');

    INSERT INTO listings.sale_listings
        (id, owner_id, title, description, category_id, condition_code,
            asking_price_paise, negotiable, pickup_area, availability)
        VALUES (item, seller, 'Synthetic books', 'Controlled database fixture', category,
            'good', 0, true, 'Synthetic pickup area', 'available');
    INSERT INTO listings.image_uploads
        (id, owner_id, object_key, state, created_at, expires_at, confirmed_at)
        VALUES (upload, seller, 'test/' || image::text, 'confirmed', CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP + INTERVAL '24 hours', CURRENT_TIMESTAMP);
    INSERT INTO listings.images (id, listing_id, upload_id, object_key, position, media_type, size_bytes)
        VALUES (image, item, upload, 'test/' || image::text, 0, 'image/png', 1);
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;

    -- Scalar money/optionality checks preserve zero while refusing missing or
    -- fractional-rupee seller prices. No fixture emits contacts or payloads.
    rejected := false;
    BEGIN
        UPDATE listings.sale_listings SET asking_price_paise = NULL WHERE id = item;
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Missing seller price was accepted'; END IF;
    rejected := false;
    BEGIN
        UPDATE listings.sale_listings SET asking_price_paise = 12550 WHERE id = item;
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Fractional-rupee price was accepted'; END IF;

    rejected := false;
    BEGIN
        DELETE FROM listings.images WHERE id = image;
        SET CONSTRAINTS ALL IMMEDIATE;
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    SET CONSTRAINTS ALL DEFERRED;
    IF NOT rejected THEN RAISE EXCEPTION 'Last usable image removal was accepted'; END IF;

    INSERT INTO search.wanted_requests (id, author_id, title, description, category_id, budget_paise, status)
        VALUES (gen_random_uuid(), buyer, 'Synthetic wanted books', 'Controlled request fixture', category, NULL, 'open'),
            (gen_random_uuid(), buyer, 'Synthetic free books', 'Controlled free request fixture', category, 0, 'open');
    INSERT INTO search.saved_listings (user_id, listing_id) VALUES (buyer, item);
    rejected := false;
    BEGIN
        INSERT INTO search.saved_listings (user_id, listing_id) VALUES (buyer, item);
    EXCEPTION WHEN unique_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Duplicate saved pair was accepted'; END IF;

    INSERT INTO conversations.threads (id, listing_id, initiator_id, counterparty_id)
        VALUES (thread, item, buyer, seller);
    INSERT INTO conversations.members (conversation_id, user_id) VALUES (thread, buyer), (thread, seller);
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;
    rejected := false;
    BEGIN
        INSERT INTO conversations.threads (id, listing_id, initiator_id, counterparty_id)
            VALUES (gen_random_uuid(), item, buyer, seller);
    EXCEPTION WHEN unique_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Duplicate buyer/listing conversation was accepted'; END IF;
    rejected := false;
    BEGIN
        INSERT INTO conversations.members (conversation_id, user_id) VALUES (thread, outsider);
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Third conversation participant was accepted'; END IF;

    -- Deliberately fake opaque bytes validate storage shape only; they are not
    -- cryptographic fixtures, real keys or a successful encryption claim.
    INSERT INTO conversations.public_key_versions (id, user_id, version, public_key_material, protocol_id)
        VALUES (seller_key, seller, 1, decode('01', 'hex'), 'synthetic-storage-test'),
            (buyer_key, buyer, 1, decode('02', 'hex'), 'synthetic-storage-test'),
            (outsider_key, outsider, 1, decode('03', 'hex'), 'synthetic-storage-test');
    INSERT INTO conversations.entries (id, conversation_id, sender_id, client_operation_id, kind)
        VALUES (message, thread, buyer, operation, 'message');
    rejected := false;
    BEGIN
        INSERT INTO conversations.encrypted_payloads
            (entry_id, protocol_id, envelope_version, sender_key_version_id, recipient_key_version_id, envelope)
            VALUES (message, 'synthetic-storage-test', 1, buyer_key, outsider_key, decode('00', 'hex'));
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Outsider envelope key was accepted'; END IF;
    INSERT INTO conversations.encrypted_payloads
        (entry_id, protocol_id, envelope_version, sender_key_version_id, recipient_key_version_id, envelope)
        VALUES (message, 'synthetic-storage-test', 1, buyer_key, seller_key, decode('00', 'hex'));
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;
    IF NOT EXISTS (SELECT 1 FROM conversations.members WHERE conversation_id = thread AND user_id = seller
        AND reminder_episode_start_sequence = 1) THEN
        RAISE EXCEPTION 'Incoming message did not initialize an unread episode';
    END IF;
    SELECT next_sequence INTO sequence_head FROM conversations.threads WHERE id = thread;
    rejected := false;
    BEGIN
        INSERT INTO conversations.entries (id, conversation_id, sender_id, client_operation_id, kind)
            VALUES (gen_random_uuid(), thread, buyer, operation, 'message');
    EXCEPTION WHEN unique_violation THEN rejected := true;
    END;
    IF NOT rejected OR (SELECT next_sequence FROM conversations.threads WHERE id = thread) <> sequence_head THEN
        RAISE EXCEPTION 'Duplicate operation changed committed entry ordering';
    END IF;

    rejected := false;
    BEGIN
        UPDATE conversations.members SET last_read_sequence = 100 WHERE conversation_id = thread AND user_id = seller;
        SET CONSTRAINTS ALL IMMEDIATE;
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    SET CONSTRAINTS ALL DEFERRED;
    IF NOT rejected THEN RAISE EXCEPTION 'Read acknowledgement beyond the head was accepted'; END IF;

    SELECT created_at INTO message_time FROM conversations.entries WHERE id = message;
    rejected := false;
    BEGIN
        INSERT INTO conversations.notification_intents
            (id, conversation_id, recipient_id, event_kind, deduplication_key, due_at,
                expires_at, unread_episode_start_sequence, unread_through_sequence)
            VALUES (gen_random_uuid(), thread, seller, 'unread_reminder',
                'unread_reminder:' || thread::text || ':' || seller::text || ':1',
                message_time + INTERVAL '1 hour', message_time + INTERVAL '25 hours', 1, 1);
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Reminder deadline was detached from its source'; END IF;
    INSERT INTO conversations.notification_intents
        (id, conversation_id, recipient_id, event_kind, deduplication_key, due_at,
            expires_at, unread_episode_start_sequence, unread_through_sequence)
        VALUES (reminder, thread, seller, 'unread_reminder',
            'unread_reminder:' || thread::text || ':' || seller::text || ':1',
            message_time + INTERVAL '15 minutes', message_time + INTERVAL '24 hours 15 minutes', 1, 1);
    UPDATE conversations.members SET last_read_sequence = 1, read_at = statement_timestamp()
        WHERE conversation_id = thread AND user_id = seller;
    UPDATE conversations.notification_intents SET state = 'suppressed', completed_at = statement_timestamp()
        WHERE id = reminder;
    IF EXISTS (SELECT 1 FROM conversations.members WHERE conversation_id = thread AND user_id = seller
        AND reminder_episode_start_sequence IS NOT NULL) THEN
        RAISE EXCEPTION 'Read catch-up failed to end the unread episode';
    END IF;

    INSERT INTO conversations.entries (id, conversation_id, sender_id, client_operation_id, kind)
        VALUES (offer_entry, thread, buyer, gen_random_uuid(), 'offer');
    INSERT INTO conversations.offers (id, conversation_id, buyer_id, current_revision, next_revision)
        VALUES (offer, thread, buyer, 1, 2);
    INSERT INTO conversations.offer_revisions (offer_id, revision, entry_id, amount_paise, status)
        VALUES (offer, 1, offer_entry, 0, 'submitted');
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;
    UPDATE listings.sale_listings SET availability = 'unavailable' WHERE id = item;
    IF NOT EXISTS (SELECT 1 FROM search.saved_listings WHERE user_id = buyer AND listing_id = item) THEN
        RAISE EXCEPTION 'Availability change removed a saved reference';
    END IF;

    -- Retention may purge history but must preserve the single logical offer.
    UPDATE conversations.offers SET current_revision = NULL, history_deleted_at = statement_timestamp() WHERE id = offer;
    UPDATE conversations.entries SET content_deleted_at = statement_timestamp() WHERE id = offer_entry;
    DELETE FROM conversations.offer_revisions WHERE offer_id = offer;
    SET CONSTRAINTS ALL IMMEDIATE;
    IF NOT EXISTS (SELECT 1 FROM conversations.offers WHERE id = offer AND current_revision IS NULL
        AND next_revision = 2 AND history_deleted_at IS NOT NULL) THEN
        RAISE EXCEPTION 'Offer history purge lost its uniqueness guard';
    END IF;
    RAISE NOTICE 'PD-08 synthetic storage smoke passed; all fixture changes will roll back';
END;
$$;
ROLLBACK;
