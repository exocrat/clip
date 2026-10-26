-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Keep the original create response for retries while the listing content is
-- retained. The owner/operation/listing IDs survive retirement as a
-- content-free key so a late retry cannot create a second listing.
CREATE TABLE listings.create_command_results (
    owner_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    operation_id uuid NOT NULL,
    listing_id uuid NOT NULL UNIQUE REFERENCES listings.sale_listings ON DELETE RESTRICT,
    request_payload jsonb,
    result_payload jsonb,
    PRIMARY KEY (owner_id, operation_id),
    CHECK ((request_payload IS NULL) = (result_payload IS NULL)),
    CHECK (request_payload IS NULL OR jsonb_typeof(request_payload) = 'object'),
    CHECK (result_payload IS NULL OR jsonb_typeof(result_payload) = 'object')
);

COMMENT ON TABLE listings.create_command_results IS
    'Create request/result pairs retained for retries until listing retirement; retirement clears payloads but preserves the owner/operation/listing key.';
COMMENT ON COLUMN listings.create_command_results.request_payload IS
    'Validated create fields excluding operation_id; NULL with result_payload only after listing retirement.';
COMMENT ON COLUMN listings.create_command_results.result_payload IS
    'Original successful ListingDetail response; NULL with request_payload only after listing retirement.';

CREATE FUNCTION listings.guard_create_command_result() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    listing_owner uuid;
    listing_retired_at timestamptz(6);
BEGIN
    -- Serialize receipt writes with retirement, so a concurrent create retry
    -- cannot restore content after the retirement trigger has scrubbed it.
    SELECT owner_id, retired_at
        INTO listing_owner, listing_retired_at
        FROM listings.sale_listings
        WHERE id = NEW.listing_id
        FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'create command result has no listing'
            USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF NEW.owner_id IS DISTINCT FROM listing_owner THEN
        RAISE EXCEPTION 'create command result owner does not match listing'
            USING ERRCODE = 'check_violation';
    END IF;
    IF listing_retired_at IS NULL
        AND (NEW.request_payload IS NULL OR NEW.result_payload IS NULL) THEN
        RAISE EXCEPTION 'live listing create result must retain request and response'
            USING ERRCODE = 'check_violation';
    END IF;
    IF listing_retired_at IS NOT NULL
        AND (NEW.request_payload IS NOT NULL OR NEW.result_payload IS NOT NULL) THEN
        RAISE EXCEPTION 'retired listing create result must be content-free'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER create_command_results_state_guard
    BEFORE INSERT OR UPDATE OF owner_id, listing_id, request_payload, result_payload
    ON listings.create_command_results
    FOR EACH ROW
    EXECUTE FUNCTION listings.guard_create_command_result();

CREATE FUNCTION listings.scrub_create_command_results_on_retirement() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE listings.create_command_results
        SET request_payload = NULL, result_payload = NULL
        WHERE listing_id = NEW.id
            AND request_payload IS NOT NULL;
    RETURN NEW;
END;
$$;

CREATE TRIGGER listing_create_command_results_retirement
    AFTER UPDATE OF retired_at ON listings.sale_listings
    FOR EACH ROW
    WHEN (OLD.retired_at IS NULL AND NEW.retired_at IS NOT NULL)
    EXECUTE FUNCTION listings.scrub_create_command_results_on_retirement();

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

DROP TRIGGER listing_create_command_results_retirement ON listings.sale_listings;
DROP TRIGGER create_command_results_state_guard ON listings.create_command_results;
DROP FUNCTION listings.scrub_create_command_results_on_retirement();
DROP FUNCTION listings.guard_create_command_result();
DROP TABLE listings.create_command_results;
