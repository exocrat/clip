-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Search's reviewed catalogue interface exposes immutable codes, not category
-- UUIDs. Schema migration alone may resolve the old cross-domain reference.
-- ALTER TYPE rewrites values without firing request update/lifecycle triggers:
-- titles, revisions, timestamps and pending-operation state must stay unchanged.
ALTER TABLE search.wanted_requests DROP CONSTRAINT wanted_requests_category_id_fkey;
CREATE FUNCTION search._migrate_wanted_category_to_code(uuid) RETURNS text
LANGUAGE sql STABLE STRICT AS 'SELECT code FROM listings.categories WHERE id=$1';
ALTER TABLE search.wanted_requests ALTER COLUMN category_id TYPE text
    USING search._migrate_wanted_category_to_code(category_id);
ALTER TABLE search.wanted_requests RENAME COLUMN category_id TO category_code;
DROP FUNCTION search._migrate_wanted_category_to_code(uuid);
ALTER TABLE search.wanted_requests ADD CONSTRAINT wanted_requests_category_code_fkey
    FOREIGN KEY (category_code) REFERENCES listings.categories(code) ON DELETE RESTRICT;
-- PostgreSQL carries the existing live/retired check and wanted_category index
-- through the type/column change. Retired NULL references remain NULL.
COMMENT ON COLUMN search.wanted_requests.category_code IS
    'Listings immutable category code validated through its public catalogue interface; no private category UUID lookup in Search application code.';

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Restore the original UUID reference using the restrictive code FK's mapping.
-- This supports nonempty rollback without changing author/state/revision data.
ALTER TABLE search.wanted_requests DROP CONSTRAINT wanted_requests_category_code_fkey;
CREATE FUNCTION search._migrate_wanted_category_to_id(text) RETURNS uuid
LANGUAGE sql STABLE STRICT AS 'SELECT id FROM listings.categories WHERE code=$1';
ALTER TABLE search.wanted_requests ALTER COLUMN category_code TYPE uuid
    USING search._migrate_wanted_category_to_id(category_code);
ALTER TABLE search.wanted_requests RENAME COLUMN category_code TO category_id;
DROP FUNCTION search._migrate_wanted_category_to_id(text);
ALTER TABLE search.wanted_requests ADD CONSTRAINT wanted_requests_category_id_fkey
    FOREIGN KEY (category_id) REFERENCES listings.categories(id) ON DELETE RESTRICT;
COMMENT ON COLUMN search.wanted_requests.category_id IS NULL;
