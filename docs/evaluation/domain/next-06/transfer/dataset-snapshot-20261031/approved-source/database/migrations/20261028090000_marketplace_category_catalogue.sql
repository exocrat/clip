-- NEXT-03: retain existing catalogue codes/assignments and add Sports & fitness.
-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

UPDATE listings.categories SET label = 'Electronics' WHERE code = 'electronics';
UPDATE listings.categories SET label = 'Home appliances' WHERE code = 'appliances';
INSERT INTO listings.categories (id, code, label, sensitive_category)
VALUES (gen_random_uuid(), 'sports_fitness', 'Sports & fitness', false);

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Restrictive foreign keys prevent rollback while any listing or wanted request
-- still uses the new category. Existing category assignments are never rewritten.
DELETE FROM listings.categories WHERE code = 'sports_fitness';
UPDATE listings.categories SET label = 'Other electronics' WHERE code = 'electronics';
UPDATE listings.categories SET label = 'Appliances' WHERE code = 'appliances';
