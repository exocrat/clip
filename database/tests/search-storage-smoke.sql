-- SE-02 Step2 storage proof only, not auth/API/cross-domain integration.
-- Own every fixture in this rollback transaction; refuse ordinary databases.
BEGIN;
DO $$
BEGIN
    IF left(current_database(), 10) <> 'clip_test_' THEN
        RAISE EXCEPTION 'Search storage smoke requires a clip_test_ database';
    END IF;
END;
$$;

DO $$
DECLARE
    author uuid := gen_random_uuid();
    other_user uuid := gen_random_uuid();
    request uuid := gen_random_uuid();
    free_request uuid := gen_random_uuid();
    item uuid := gen_random_uuid();
    upload uuid := gen_random_uuid();
    image uuid := gen_random_uuid();
    category uuid;
    bad jsonb;
    rejected boolean;
    anchor timestamptz;
    saved_at timestamptz;
BEGIN
    SELECT id INTO STRICT category FROM listings.categories WHERE code = 'books';
    INSERT INTO identity.users (id, account_class, status, display_name) VALUES
        (author, 'regular', 'active', 'Synthetic Search storage author'),
        (other_user, 'regular', 'active', 'Synthetic Search storage saver');

    -- Reuse the existing nullable-budget/live-content schema, not new tables.
    INSERT INTO search.wanted_requests
        (id, author_id, title, description, category_code, budget_paise, status)
        VALUES (request, author, 'Synthetic books wanted', 'Controlled storage fixture', 'books', NULL, 'open'),
            (free_request, author, 'Synthetic free books', 'Controlled storage fixture', 'books', 0, 'open');
    IF NOT EXISTS (SELECT 1 FROM search.wanted_requests WHERE id=request AND budget_paise IS NULL AND closed_at IS NULL)
        OR NOT EXISTS (SELECT 1 FROM search.wanted_requests WHERE id=free_request AND budget_paise=0) THEN
        RAISE EXCEPTION 'Unstated and zero budgets were not distinct';
    END IF;
    UPDATE search.wanted_requests SET description='Changed synthetic description' WHERE id=free_request;
    IF (SELECT budget_paise FROM search.wanted_requests WHERE id=free_request) <> 0 THEN
        RAISE EXCEPTION 'Unrelated update changed budget';
    END IF;
    UPDATE search.wanted_requests SET budget_paise=NULL WHERE id=free_request;
    IF NOT EXISTS (SELECT 1 FROM search.wanted_requests WHERE id=free_request AND budget_paise IS NULL) THEN
        RAISE EXCEPTION 'Explicit budget clear failed';
    END IF;

    -- Only controlled invalid fields vary; each subtransaction must be rejected.
    FOR bad IN SELECT value FROM jsonb_array_elements(jsonb_build_array(
        jsonb_build_object('title', ''),
        jsonb_build_object('title', '   '),
        jsonb_build_object('title', repeat('x', 121)),
        jsonb_build_object('description', NULL),
        jsonb_build_object('description', repeat('x', 5001)),
        jsonb_build_object('budget_paise', -100),
        jsonb_build_object('budget_paise', 1),
        jsonb_build_object('status', 'invalid'),
        jsonb_build_object('author_id', gen_random_uuid()),
        jsonb_build_object('category_code', 'synthetic_missing_code')
    )) LOOP
        rejected := false;
        BEGIN
            INSERT INTO search.wanted_requests
                (id, author_id, title, description, category_code, budget_paise, status)
                VALUES (gen_random_uuid(), coalesce((bad->>'author_id')::uuid, author),
                    coalesce(bad->>'title', 'Synthetic valid title'),
                    CASE WHEN bad ? 'description' THEN bad->>'description' ELSE 'Synthetic valid description' END,
                    coalesce(bad->>'category_code', 'books'),
                    (bad->>'budget_paise')::bigint, coalesce(bad->>'status', 'open'));
        EXCEPTION WHEN check_violation OR foreign_key_violation THEN rejected := true;
        END;
        IF NOT rejected THEN RAISE EXCEPTION 'Invalid wanted storage fixture was accepted'; END IF;
    END LOOP;

    -- closed_at is the existing continuous-unavailability anchor. An edit must
    -- preserve it; reopen clears it. An old closed fixture proves a later close
    -- starts at server time rather than inheriting the previous inactivity span.
    INSERT INTO search.wanted_requests
        (id, author_id, title, description, category_code, status, created_at, closed_at)
        VALUES (gen_random_uuid(), author, 'Synthetic closed request', 'Controlled fixture', 'books',
            'unavailable', statement_timestamp()-INTERVAL '20 days', statement_timestamp()-INTERVAL '10 days')
        RETURNING id, closed_at INTO request, anchor;
    UPDATE search.wanted_requests SET description='Changed closed fixture', status='unavailable' WHERE id=request;
    IF (SELECT closed_at FROM search.wanted_requests WHERE id=request) IS DISTINCT FROM anchor THEN
        RAISE EXCEPTION 'Continuous closure anchor changed during edit';
    END IF;
    UPDATE search.wanted_requests SET status='open' WHERE id=request;
    IF NOT EXISTS (SELECT 1 FROM search.wanted_requests WHERE id=request AND closed_at IS NULL) THEN
        RAISE EXCEPTION 'Reopen did not reset closure anchor';
    END IF;
    UPDATE search.wanted_requests SET status='unavailable' WHERE id=request;
    IF NOT EXISTS (SELECT 1 FROM search.wanted_requests WHERE id=request AND closed_at>anchor) THEN
        RAISE EXCEPTION 'Reclose inherited old inactivity span';
    END IF;
    rejected := false;
    BEGIN
        UPDATE search.wanted_requests SET author_id=other_user WHERE id=request;
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Wanted author changed'; END IF;
    rejected := false;
    BEGIN
        UPDATE search.wanted_requests SET retirement_pending_operation_id=gen_random_uuid() WHERE id=request;
    EXCEPTION WHEN check_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Incomplete retirement operation pair accepted'; END IF;
    UPDATE search.wanted_requests SET retirement_pending_operation_id=gen_random_uuid(),
        retirement_pending_cutoff_utc=statement_timestamp()-INTERVAL '90 days' WHERE id=request;
    UPDATE search.wanted_requests SET retirement_pending_operation_id=NULL, retirement_pending_cutoff_utc=NULL WHERE id=request;

    -- Fixture-only writes supply upstream rows; Search application code must
    -- use the reviewed Listings/Identity public interfaces instead.
    INSERT INTO listings.sale_listings
        (id, owner_id, title, description, category_id, condition_code, asking_price_paise, negotiable, availability)
        VALUES (item, author, 'Synthetic saved book', 'Controlled storage fixture', category, 'good', 0, true, 'available');
    INSERT INTO listings.image_uploads
        (id, owner_id, object_key, operation_id, state, created_at, expires_at, confirmed_at, confirmed_media_type, confirmed_size_bytes)
        VALUES (upload, author, 'test/'||image::text, upload, 'confirmed', CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP+INTERVAL '24 hours', CURRENT_TIMESTAMP, 'image/png', 1);
    INSERT INTO listings.images (id, listing_id, upload_id, object_key, position, media_type, size_bytes)
        VALUES (image, item, upload, 'test/'||image::text, 0, 'image/png', 1);
    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;
    INSERT INTO search.saved_listings (user_id, listing_id) VALUES (other_user, item)
        RETURNING created_at INTO saved_at;
    rejected := false;
    BEGIN
        INSERT INTO search.saved_listings (user_id, listing_id) VALUES (other_user, item);
    EXCEPTION WHEN unique_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Duplicate saved pair accepted'; END IF;
    INSERT INTO search.saved_listings (user_id, listing_id) VALUES (other_user, item) ON CONFLICT DO NOTHING;
    IF (SELECT created_at FROM search.saved_listings WHERE user_id=other_user AND listing_id=item) IS DISTINCT FROM saved_at THEN
        RAISE EXCEPTION 'Duplicate save replaced original time';
    END IF;
    INSERT INTO search.saved_listings (user_id, listing_id) VALUES (author, item);
    UPDATE listings.sale_listings SET availability='unavailable' WHERE id=item;
    IF (SELECT count(*) FROM search.saved_listings WHERE listing_id=item) <> 2 THEN
        RAISE EXCEPTION 'Unavailability removed saved references';
    END IF;
    -- Preserve references rather than cascading user/listing deletion. Existing
    -- retired-origin smoke separately proves content clearing/retired guards.
    IF (SELECT count(*) FROM pg_constraint WHERE conrelid='search.saved_listings'::regclass
        AND contype='f' AND confdeltype='r') <> 2 THEN
        RAISE EXCEPTION 'Saved user/listing foreign keys must restrict deletion';
    END IF;
    rejected := false;
    BEGIN
        INSERT INTO search.saved_listings (user_id, listing_id) VALUES (other_user, gen_random_uuid());
    EXCEPTION WHEN foreign_key_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Missing listing save accepted'; END IF;
    rejected := false;
    BEGIN
        INSERT INTO search.saved_listings (user_id, listing_id) VALUES (gen_random_uuid(), item);
    EXCEPTION WHEN foreign_key_violation THEN rejected := true;
    END;
    IF NOT rejected THEN RAISE EXCEPTION 'Missing saver accepted'; END IF;
    IF (SELECT count(*) FROM pg_indexes WHERE schemaname='search' AND indexname IN
        ('wanted_recency','wanted_author','wanted_category','wanted_closure','saves_recency','saves_listing')) <> 6 THEN
        RAISE EXCEPTION 'Required wanted/saved access indexes missing';
    END IF;
END;
$$;
SET CONSTRAINTS ALL IMMEDIATE;
ROLLBACK;
