-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Keep the exact request and response for seller availability/selection retries.
-- Listings application code writes these rows atomically with the listing change.
CREATE TABLE listings.owner_command_results (
    listing_id uuid NOT NULL REFERENCES listings.sale_listings(id) ON DELETE RESTRICT,
    command_kind text NOT NULL CHECK (command_kind IN ('availability', 'selection')),
    operation_id uuid NOT NULL,
    request_payload jsonb NOT NULL CHECK (jsonb_typeof(request_payload) = 'object'),
    result_payload jsonb NOT NULL CHECK (jsonb_typeof(result_payload) = 'object'),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (listing_id, command_kind, operation_id)
);

COMMENT ON TABLE listings.owner_command_results IS
    'Saved request/result pairs for retrying seller availability and selection commands; deleted when the listing retires.';
COMMENT ON COLUMN listings.owner_command_results.request_payload IS
    'Validated request fields excluding operation_id; preserves omitted versus explicit values.';
COMMENT ON COLUMN listings.owner_command_results.result_payload IS
    'Original successful API response, replayed for the same request while the listing is retained.';

CREATE FUNCTION listings.delete_owner_command_results_on_retirement() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM listings.owner_command_results WHERE listing_id = NEW.id;
    RETURN NEW;
END;
$$;

CREATE TRIGGER listing_owner_command_results_retirement
    AFTER UPDATE OF retired_at ON listings.sale_listings
    FOR EACH ROW
    WHEN (OLD.retired_at IS NULL AND NEW.retired_at IS NOT NULL)
    EXECUTE FUNCTION listings.delete_owner_command_results_on_retirement();

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

DROP TRIGGER listing_owner_command_results_retirement ON listings.sale_listings;
DROP FUNCTION listings.delete_owner_command_results_on_retirement();
DROP TABLE listings.owner_command_results;
