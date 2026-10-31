-- Add seller-stated original price and cap user-entered marketplace amounts.
-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

ALTER TABLE listings.sale_listings
    ADD COLUMN original_price_paise bigint,
    ADD CONSTRAINT listing_original_price_valid CHECK (
        original_price_paise IS NULL OR (
            original_price_paise > 0
            AND original_price_paise <= 1000000000
            AND original_price_paise % 100 = 0
        )
    ),
    ADD CONSTRAINT listing_asking_price_market_cap CHECK (
        asking_price_paise IS NULL OR asking_price_paise <= 1000000000
    );

ALTER TABLE search.wanted_requests
    ADD CONSTRAINT wanted_budget_market_cap CHECK (
        budget_paise IS NULL OR budget_paise <= 1000000000
    );

COMMENT ON COLUMN listings.sale_listings.original_price_paise IS
    'Optional seller-stated original price in whole-rupee paise; not verified by CLIP.';

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

ALTER TABLE search.wanted_requests
    DROP CONSTRAINT wanted_budget_market_cap;
ALTER TABLE listings.sale_listings
    DROP CONSTRAINT listing_asking_price_market_cap,
    DROP CONSTRAINT listing_original_price_valid,
    DROP COLUMN original_price_paise;
