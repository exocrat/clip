-- NEXT-03 Step 2: use title case for catalogue labels shown across the app.
-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

UPDATE listings.categories SET label = CASE code
    WHEN 'mobile_phone' THEN 'Mobile Phones'
    WHEN 'laptop' THEN 'Laptops'
    WHEN 'electronics' THEN 'Electronics'
    WHEN 'furniture' THEN 'Furniture'
    WHEN 'books' THEN 'Books and Study Materials'
    WHEN 'bicycles' THEN 'Bicycles'
    WHEN 'appliances' THEN 'Home Appliances'
    WHEN 'sports_fitness' THEN 'Sports & Fitness'
    WHEN 'other' THEN 'Other'
    ELSE label
END
WHERE code IN (
    'mobile_phone', 'laptop', 'electronics', 'furniture', 'books', 'bicycles',
    'appliances', 'sports_fitness', 'other'
);

UPDATE listings.conditions SET label = CASE code
    WHEN 'new' THEN 'New / Unused'
    WHEN 'like_new' THEN 'Like New'
    WHEN 'good' THEN 'Good'
    WHEN 'fair' THEN 'Fair'
    ELSE label
END
WHERE code IN ('new', 'like_new', 'good', 'fair');

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

UPDATE listings.categories SET label = CASE code
    WHEN 'mobile_phone' THEN 'Mobile phones'
    WHEN 'laptop' THEN 'Laptops'
    WHEN 'electronics' THEN 'Electronics'
    WHEN 'furniture' THEN 'Furniture'
    WHEN 'books' THEN 'Books and study materials'
    WHEN 'bicycles' THEN 'Bicycles'
    WHEN 'appliances' THEN 'Home appliances'
    WHEN 'sports_fitness' THEN 'Sports & fitness'
    WHEN 'other' THEN 'Other'
    ELSE label
END
WHERE code IN (
    'mobile_phone', 'laptop', 'electronics', 'furniture', 'books', 'bicycles',
    'appliances', 'sports_fitness', 'other'
);

UPDATE listings.conditions SET label = CASE code
    WHEN 'new' THEN 'New / unused'
    WHEN 'like_new' THEN 'Like new'
    WHEN 'good' THEN 'Good'
    WHEN 'fair' THEN 'Fair'
    ELSE label
END
WHERE code IN ('new', 'like_new', 'good', 'fair');
