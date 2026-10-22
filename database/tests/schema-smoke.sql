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
    retirement_item uuid := gen_random_uuid();
    upload uuid := gen_random_uuid();
    image uuid := gen_random_uuid();
    retirement_upload uuid := gen_random_uuid();
    retirement_image uuid := gen_random_uuid();
    thread uuid := gen_random_uuid();
    message uuid := gen_random_uuid();
    operation uuid := gen_random_uuid();
    retirement_operation uuid := gen_random_uuid();
    receipt_operation uuid := gen_random_uuid();
    create_receipt_operation uuid := gen_random_uuid();
    seller_key uuid := gen_random_uuid();
    buyer_key uuid := gen_random_uuid();
    outsider_key uuid := gen_random_uuid();
    offer uuid := gen_random_uuid();
    offer_entry uuid := gen_random_uuid();
    reminder uuid := gen_random_uuid();
    message_time timestamptz;
    category uuid;
    rejected boolean;
    receipt_duplicate_rejected boolean;
    receipt_count bigint;
    create_receipt_duplicate_rejected boolean;
    create_receipt_count bigint;
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

    INSERT INTO conversations.origin_retirement_operations
        (operation_id, origin_kind, origin_id, cutoff_utc, outcome, marked_count)
        VALUES (retirement_operation, 'listing', item, statement_timestamp(), 'marked', 0);
    rejected := false;
    BEGIN
        INSERT INTO conversations.origin_retirement_operations
            (operation_id, origin_kind, origin_id, cutoff_utc, outcome, marked_count)
            VALUES (gen_random_uuid(), 'listing', item, statement_timestamp(),
                'blocked_recent_activity', 1);
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    IF NOT rejected THEN
        RAISE EXCEPTION 'Blocked retirement result accepted a nonzero marked count';
    END IF;

    INSERT INTO listings.sale_listings
        (id, owner_id, title, description, category_id, condition_code,
            asking_price_paise, negotiable, pickup_area, availability)
        VALUES (item, seller, 'Synthetic books', 'Controlled database fixture', category,
            'good', 0, true, 'Synthetic pickup area', 'available');
    INSERT INTO listings.image_uploads
        (id, owner_id, object_key, operation_id, state, created_at, expires_at, confirmed_at,
            confirmed_media_type, confirmed_size_bytes)
        VALUES (upload, seller, 'test/' || image::text, upload, 'confirmed', CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP + INTERVAL '24 hours', CURRENT_TIMESTAMP, 'image/png', 1);
    INSERT INTO listings.images (id, listing_id, upload_id, object_key, position, media_type, size_bytes)
        VALUES (image, item, upload, 'test/' || image::text, 0, 'image/png', 1);
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;

    -- This second, old synthetic listing lets the smoke check the saved
    -- command result and its removal at retirement without touching a thread.
    INSERT INTO listings.sale_listings
        (id, owner_id, title, description, category_id, condition_code,
            asking_price_paise, negotiable, pickup_area, availability,
            created_at, available_from, available_until)
        VALUES (retirement_item, seller, 'Receipt cleanup fixture',
            'Synthetic receipt cleanup test', category, 'good', 0, true,
            'Synthetic pickup area', 'unavailable',
            statement_timestamp() - INTERVAL '200 days',
            statement_timestamp() - INTERVAL '200 days',
            statement_timestamp() - INTERVAL '190 days');
    INSERT INTO listings.image_uploads
        (id, owner_id, object_key, operation_id, state, created_at, expires_at, confirmed_at,
            confirmed_media_type, confirmed_size_bytes)
        VALUES (retirement_upload, seller, 'test/' || retirement_image::text, retirement_upload,
            'confirmed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '24 hours',
            CURRENT_TIMESTAMP, 'image/png', 1);
    INSERT INTO listings.images (id, listing_id, upload_id, object_key, position, media_type, size_bytes)
        VALUES (retirement_image, retirement_item, retirement_upload,
            'test/' || retirement_image::text, 0, 'image/png', 1);
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;

    INSERT INTO listings.owner_command_results
        (listing_id, command_kind, operation_id, request_payload, result_payload)
        VALUES (retirement_item, 'availability', receipt_operation,
            jsonb_build_object('expected_revision', 1, 'availability', 'unavailable'),
            jsonb_build_object('listing_id', retirement_item, 'revision', 2));
    IF NOT EXISTS (
        SELECT 1 FROM listings.owner_command_results
        WHERE listing_id = retirement_item AND command_kind = 'availability'
            AND operation_id = receipt_operation
            AND request_payload ->> 'availability' = 'unavailable'
            AND result_payload ->> 'revision' = '2'
    ) THEN
        RAISE EXCEPTION 'Owner command request/result was not retained';
    END IF;
    receipt_duplicate_rejected := false;
    BEGIN
        INSERT INTO listings.owner_command_results
            (listing_id, command_kind, operation_id, request_payload, result_payload)
            VALUES (retirement_item, 'availability', receipt_operation,
                jsonb_build_object('expected_revision', 1, 'availability', 'available'),
                jsonb_build_object('listing_id', retirement_item, 'revision', 2));
    EXCEPTION WHEN unique_violation THEN receipt_duplicate_rejected := true;
    END;
    IF NOT receipt_duplicate_rejected THEN
        RAISE EXCEPTION 'Duplicate owner command key was accepted';
    END IF;
    INSERT INTO listings.create_command_results
        (owner_id, operation_id, listing_id, request_payload, result_payload)
        VALUES (seller, create_receipt_operation, retirement_item,
            jsonb_build_object('title', 'Receipt cleanup fixture',
                'description', 'Synthetic receipt cleanup test'),
            jsonb_build_object('listing_id', retirement_item,
                'title', 'Receipt cleanup fixture'));
    IF NOT EXISTS (
        SELECT 1 FROM listings.create_command_results
        WHERE owner_id = seller AND operation_id = create_receipt_operation
            AND listing_id = retirement_item
            AND request_payload ->> 'title' = 'Receipt cleanup fixture'
            AND result_payload ->> 'listing_id' = retirement_item::text
    ) THEN
        RAISE EXCEPTION 'Create request/result was not retained for retry';
    END IF;
    UPDATE listings.images SET retired_at = statement_timestamp()
        WHERE id = retirement_image;
    UPDATE listings.sale_listings SET retired_at = statement_timestamp(),
        title = NULL, description = NULL, category_id = NULL, condition_code = NULL,
        asking_price_paise = NULL, negotiable = NULL, pickup_area = NULL,
        proof_available = NULL, selected_buyer_id = NULL
        WHERE id = retirement_item;
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;
    SELECT count(*) INTO receipt_count FROM listings.owner_command_results
        WHERE listing_id = retirement_item;
    IF receipt_count <> 0 THEN
        RAISE EXCEPTION 'Retirement kept a saved owner command result';
    END IF;
    SELECT count(*) INTO create_receipt_count FROM listings.create_command_results
        WHERE owner_id = seller AND operation_id = create_receipt_operation
            AND listing_id = retirement_item AND request_payload IS NULL
            AND result_payload IS NULL;
    IF create_receipt_count <> 1 THEN
        RAISE EXCEPTION 'Retirement did not keep exactly one content-free create key';
    END IF;
    rejected := false;
    BEGIN
        UPDATE listings.create_command_results
            SET request_payload = jsonb_build_object('title', 'Restored content'),
                result_payload = jsonb_build_object('title', 'Restored content')
            WHERE owner_id = seller AND operation_id = create_receipt_operation;
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    IF NOT rejected THEN
        RAISE EXCEPTION 'Retired create receipt accepted content restoration';
    END IF;
    create_receipt_duplicate_rejected := false;
    BEGIN
        INSERT INTO listings.create_command_results
            (owner_id, operation_id, listing_id, request_payload, result_payload)
            VALUES (seller, create_receipt_operation, item,
                jsonb_build_object('title', 'Second listing'),
                jsonb_build_object('listing_id', item));
    EXCEPTION WHEN unique_violation THEN create_receipt_duplicate_rejected := true;
    END;
    IF NOT create_receipt_duplicate_rejected THEN
        RAISE EXCEPTION 'Retired create operation key allowed a second listing';
    END IF;

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
    UPDATE listings.sale_listings
        SET selected_buyer_id = buyer, selected_conversation_id = thread
        WHERE id = item;
    IF NOT EXISTS (
        SELECT 1 FROM listings.sale_listings
        WHERE id = item AND selected_buyer_id = buyer
            AND selected_conversation_id = thread
    ) THEN
        RAISE EXCEPTION 'Selected buyer/conversation pair was not retained';
    END IF;
    rejected := false;
    BEGIN
        UPDATE listings.sale_listings SET selected_conversation_id = NULL WHERE id = item;
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Unpaired selected buyer was accepted'; END IF;
    rejected := false;
    BEGIN
        UPDATE listings.image_uploads SET confirmed_size_bytes = NULL WHERE id = upload;
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Incomplete confirmed image metadata was accepted'; END IF;
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
