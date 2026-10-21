-- Regression for origin retirement. Run only in an isolated, administrator-owned test DB.
-- Every fixture is synthetic; rollback restores data and session-local settings.
BEGIN;
DO $$
BEGIN
    IF left(current_database(), 10) <> 'clip_test_' THEN
        RAISE EXCEPTION 'Retired-origin smoke requires a clip_test_ database';
    END IF;
END;
$$;

DO $$
DECLARE
    seller uuid := gen_random_uuid();
    buyer uuid := gen_random_uuid();
    item uuid := gen_random_uuid();
    request uuid := gen_random_uuid();
    upload uuid := gen_random_uuid();
    image uuid := gen_random_uuid();
    sale_thread uuid := gen_random_uuid();
    request_thread uuid := gen_random_uuid();
    seller_key uuid := gen_random_uuid();
    buyer_key uuid := gen_random_uuid();
    target_thread uuid;
    entry_kind text;
    entry uuid;
    rejected boolean;
    reason text;
    before_sequence bigint;
    before_activity timestamptz;
BEGIN
    INSERT INTO identity.users (id, account_class, status, created_at) VALUES
        (seller, 'regular', 'active', CURRENT_TIMESTAMP - INTERVAL '365 days'),
        (buyer, 'regular', 'active', CURRENT_TIMESTAMP - INTERVAL '365 days');
    INSERT INTO listings.sale_listings
        (id, owner_id, title, description, category_id, condition_code,
            asking_price_paise, negotiable, pickup_area, availability,
            created_at, available_from, available_until)
        SELECT item, seller, 'Synthetic old books', 'Synthetic retirement fixture',
            id, 'good', 0, true, 'Synthetic pickup', 'unavailable',
            CURRENT_TIMESTAMP - INTERVAL '200 days',
            CURRENT_TIMESTAMP - INTERVAL '200 days',
            CURRENT_TIMESTAMP - INTERVAL '190 days'
        FROM listings.categories WHERE code = 'books';
    INSERT INTO listings.image_uploads
        (id, owner_id, object_key, state, created_at, expires_at, confirmed_at)
        VALUES (upload, seller, 'test/retirement/' || image::text, 'confirmed',
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '24 hours', CURRENT_TIMESTAMP);
    INSERT INTO listings.images
        (id, listing_id, upload_id, object_key, position, media_type, size_bytes)
        VALUES (image, item, upload, 'test/retirement/' || image::text, 0, 'image/png', 1);
    INSERT INTO search.wanted_requests
        (id, author_id, title, description, category_id, status, created_at)
        SELECT request, seller, 'Synthetic old request', 'Synthetic retirement fixture',
            id, 'open', CURRENT_TIMESTAMP - INTERVAL '200 days'
        FROM listings.categories WHERE code = 'books';
    INSERT INTO conversations.threads
        (id, listing_id, wanted_request_id, initiator_id, counterparty_id,
            created_at, last_activity_at)
        VALUES (sale_thread, item, NULL, buyer, seller,
                CURRENT_TIMESTAMP - INTERVAL '200 days', CURRENT_TIMESTAMP - INTERVAL '200 days'),
            (request_thread, NULL, request, buyer, seller,
                CURRENT_TIMESTAMP - INTERVAL '200 days', CURRENT_TIMESTAMP - INTERVAL '200 days');
    INSERT INTO conversations.members (conversation_id, user_id)
        VALUES (sale_thread, buyer), (sale_thread, seller),
            (request_thread, buyer), (request_thread, seller);
    INSERT INTO conversations.public_key_versions
        (id, user_id, version, public_key_material, protocol_id, created_at)
        VALUES (seller_key, seller, 1, decode('01', 'hex'), 'synthetic-retirement-test',
                CURRENT_TIMESTAMP - INTERVAL '200 days'),
            (buyer_key, buyer, 1, decode('02', 'hex'), 'synthetic-retirement-test',
                CURRENT_TIMESTAMP - INTERVAL '200 days');
    UPDATE search.wanted_requests SET status = 'unavailable' WHERE id = request;
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;

    -- Ordinary unavailability/closure must still allow participant messages and
    -- contact shares. Historical fixture times keep the retirement age realistic.
    FOREACH target_thread IN ARRAY ARRAY[sale_thread, request_thread] LOOP
        FOREACH entry_kind IN ARRAY ARRAY['message', 'contact_share'] LOOP
            entry := gen_random_uuid();
            INSERT INTO conversations.entries
                (id, conversation_id, sender_id, client_operation_id, kind, created_at)
                VALUES (entry, target_thread, buyer, gen_random_uuid(), entry_kind,
                    CURRENT_TIMESTAMP - INTERVAL '100 days');
            INSERT INTO conversations.encrypted_payloads
                (entry_id, protocol_id, envelope_version,
                    sender_key_version_id, recipient_key_version_id, envelope)
                VALUES (entry, 'synthetic-retirement-test', 1, buyer_key, seller_key, decode('00', 'hex'));
            IF entry_kind = 'contact_share' THEN
                INSERT INTO conversations.contact_shares (entry_id) VALUES (entry);
            END IF;
        END LOOP;
    END LOOP;
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;

    -- Seed only the historic closure instant under the test administrator's
    -- session-local replica mode. No FK/identity/content changes are made here.
    -- This simulates 190 elapsed days without weakening the retirement or entry
    -- guards being tested: restore origin mode before marking/retiring.
    SET LOCAL session_replication_role = replica;
    UPDATE search.wanted_requests SET closed_at = CURRENT_TIMESTAMP - INTERVAL '190 days'
        WHERE id = request;
    UPDATE conversations.threads SET last_activity_at = CURRENT_TIMESTAMP - INTERVAL '100 days'
        WHERE id IN (sale_thread, request_thread);
    SET LOCAL session_replication_role = origin;
    -- Simulate the successful Conversations marker that the owner API must
    -- obtain before clearing an origin. The public API implementation is not
    -- part of this SQL-only test fixture.
    UPDATE conversations.threads SET participant_writes_blocked_at = clock_timestamp()
        WHERE id IN (sale_thread, request_thread);
    UPDATE listings.sale_listings SET retired_at = statement_timestamp(),
        title = NULL, description = NULL, category_id = NULL, condition_code = NULL,
        asking_price_paise = NULL, negotiable = NULL, pickup_area = NULL,
        proof_available = NULL, selected_buyer_id = NULL WHERE id = item;
    UPDATE listings.images SET retired_at = statement_timestamp() WHERE id = image;
    UPDATE search.wanted_requests SET retired_at = statement_timestamp(),
        title = NULL, description = NULL, category_id = NULL, budget_paise = NULL
        WHERE id = request;
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;

    FOREACH target_thread IN ARRAY ARRAY[sale_thread, request_thread] LOOP
        SELECT next_sequence, last_activity_at INTO before_sequence, before_activity
            FROM conversations.threads WHERE id = target_thread;
        FOREACH entry_kind IN ARRAY ARRAY['message', 'contact_share'] LOOP
            rejected := false;
            BEGIN
                entry := gen_random_uuid();
                INSERT INTO conversations.entries
                    (id, conversation_id, sender_id, client_operation_id, kind)
                    VALUES (entry, target_thread, buyer, gen_random_uuid(), entry_kind);
                INSERT INTO conversations.encrypted_payloads
                    (entry_id, protocol_id, envelope_version,
                        sender_key_version_id, recipient_key_version_id, envelope)
                    VALUES (entry, 'synthetic-retirement-test', 1, buyer_key, seller_key, decode('00', 'hex'));
                IF entry_kind = 'contact_share' THEN
                    INSERT INTO conversations.contact_shares (entry_id) VALUES (entry);
                END IF;
                SET CONSTRAINTS ALL IMMEDIATE;
            EXCEPTION WHEN check_violation THEN
                GET STACKED DIAGNOSTICS reason = MESSAGE_TEXT;
                IF reason <> 'New entries are disabled for this conversation' THEN
                    RAISE EXCEPTION 'Unexpected rejection in retired-origin regression';
                END IF;
                rejected := true;
            END;
            SET CONSTRAINTS ALL DEFERRED;
            IF NOT rejected THEN
                RAISE EXCEPTION 'Retired origin accepted new private content';
            END IF;
            IF EXISTS (SELECT 1 FROM conversations.threads WHERE id = target_thread
                AND (next_sequence <> before_sequence OR last_activity_at <> before_activity)) THEN
                RAISE EXCEPTION 'Rejected entry changed thread ordering or activity';
            END IF;
        END LOOP;
    END LOOP;
    RAISE NOTICE 'Retired-origin regression passed for messages and contact shares on both origins';
END;
$$;
ROLLBACK;
