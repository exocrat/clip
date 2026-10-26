-- migrate:up
-- LI-01: pickup area is optional; keep all other live/retired content invariants.
SET LOCAL statement_timeout = '60s';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

ALTER TABLE listings.sale_listings DROP CONSTRAINT listing_live_or_retired;
ALTER TABLE listings.sale_listings ADD CONSTRAINT listing_live_or_retired CHECK (
    (retired_at IS NULL AND title IS NOT NULL AND description IS NOT NULL
        AND category_id IS NOT NULL AND condition_code IS NOT NULL
        AND asking_price_paise IS NOT NULL AND negotiable IS NOT NULL)
    OR (retired_at IS NOT NULL AND availability = 'unavailable'
        AND title IS NULL AND description IS NULL AND category_id IS NULL
        AND condition_code IS NULL AND asking_price_paise IS NULL
        AND negotiable IS NULL AND pickup_area IS NULL
        AND proof_available IS NULL AND selected_buyer_id IS NULL)
);

-- migrate:down
-- Refuse data loss/fabricated pickup areas when reverting to the required field.
SET LOCAL statement_timeout = '60s';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM listings.sale_listings WHERE retired_at IS NULL AND pickup_area IS NULL) THEN
        RAISE EXCEPTION 'Cannot require pickup area while live listings without an area exist'
            USING ERRCODE = '23514';
    END IF;
END;
$$;

ALTER TABLE listings.sale_listings DROP CONSTRAINT listing_live_or_retired;
ALTER TABLE listings.sale_listings ADD CONSTRAINT listing_live_or_retired CHECK (
    (retired_at IS NULL AND title IS NOT NULL AND description IS NOT NULL
        AND category_id IS NOT NULL AND condition_code IS NOT NULL
        AND asking_price_paise IS NOT NULL AND negotiable IS NOT NULL
        AND pickup_area IS NOT NULL)
    OR (retired_at IS NOT NULL AND availability = 'unavailable'
        AND title IS NULL AND description IS NULL AND category_id IS NULL
        AND condition_code IS NULL AND asking_price_paise IS NULL
        AND negotiable IS NULL AND pickup_area IS NULL
        AND proof_available IS NULL AND selected_buyer_id IS NULL)
);
