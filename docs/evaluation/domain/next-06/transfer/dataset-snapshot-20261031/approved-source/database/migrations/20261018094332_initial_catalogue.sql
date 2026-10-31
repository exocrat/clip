-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- Only Mohit-approved catalogue configuration is seeded. No users, contacts,
-- listings, cryptographic material, threshold values or evaluation data.
-- PostgreSQL's built-in UUIDv4 generator needs no extension; stable public
-- catalogue codes, rather than environment-specific UUIDs, identify seed rows.
INSERT INTO listings.categories (id, code, label, sensitive_category) VALUES
    (gen_random_uuid(), 'mobile_phone', 'Mobile phones', true),
    (gen_random_uuid(), 'laptop', 'Laptops', true),
    (gen_random_uuid(), 'electronics', 'Other electronics', false),
    (gen_random_uuid(), 'furniture', 'Furniture', false),
    (gen_random_uuid(), 'books', 'Books and study materials', false),
    (gen_random_uuid(), 'bicycles', 'Bicycles', false),
    (gen_random_uuid(), 'appliances', 'Appliances', false),
    (gen_random_uuid(), 'other', 'Other', false);
INSERT INTO listings.conditions (code, label) VALUES
    ('new', 'New / unused'),
    ('like_new', 'Like new'),
    ('good', 'Good'),
    ('fair', 'Fair');

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- RESTRICT FKs protect any application rows referencing catalogue entries.
DELETE FROM listings.conditions WHERE code IN ('new', 'like_new', 'good', 'fair');
DELETE FROM listings.categories WHERE code IN
    ('mobile_phone', 'laptop', 'electronics', 'furniture', 'books', 'bicycles', 'appliances', 'other');
