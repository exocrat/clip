-- migrate:up
-- Seller selection is private tracking; only availability commands close a listing.
CREATE OR REPLACE FUNCTION listings.guard_origin() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    anchor timestamptz;
    moment timestamptz := statement_timestamp();
BEGIN
    IF TG_OP = 'INSERT' AND NEW.retired_at IS NOT NULL THEN
        RAISE EXCEPTION 'New origins must contain live required fields' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' AND (NEW.id IS DISTINCT FROM OLD.id
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
        OR (OLD.retired_at IS NOT NULL AND (to_jsonb(NEW) - 'search_vector')
            IS DISTINCT FROM (to_jsonb(OLD) - 'search_vector'))) THEN
        RAISE EXCEPTION 'Origin identity or retired content cannot be rewritten' USING ERRCODE = '23514';
    END IF;
    IF TG_TABLE_NAME = 'sale_listings' THEN
        IF TG_OP = 'UPDATE' AND NEW.owner_id IS DISTINCT FROM OLD.owner_id THEN
            RAISE EXCEPTION 'Listing owner is immutable' USING ERRCODE = '23514';
        END IF;
        IF NEW.selected_buyer_id IS NOT NULL AND (TG_OP = 'INSERT'
            OR NEW.selected_buyer_id IS DISTINCT FROM OLD.selected_buyer_id) THEN
            IF NEW.retired_at IS NOT NULL THEN
                RAISE EXCEPTION 'Selection requires a non-retired listing' USING ERRCODE = '23514';
            END IF;
        END IF;
        IF TG_OP = 'UPDATE' THEN
            anchor := OLD.retirement_eligible_since;
            IF anchor IS NULL AND OLD.available_until <= moment THEN
                anchor := greatest(OLD.available_until, OLD.created_at);
            END IF;
        END IF;
        IF NEW.availability = 'unavailable' OR NEW.available_until <= moment THEN
            NEW.retirement_eligible_since := coalesce(anchor,
                CASE WHEN NEW.available_until <= moment
                    THEN greatest(NEW.available_until, NEW.created_at) ELSE moment END);
        ELSE
            NEW.retirement_eligible_since := NULL;
        END IF;
        anchor := NEW.retirement_eligible_since;
    ELSE
        IF TG_OP = 'UPDATE' AND NEW.author_id IS DISTINCT FROM OLD.author_id THEN
            RAISE EXCEPTION 'Wanted Request author is immutable' USING ERRCODE = '23514';
        END IF;
        IF NEW.status = 'open' THEN
            NEW.closed_at := NULL;
        ELSIF TG_OP = 'INSERT' THEN
            NEW.closed_at := coalesce(NEW.closed_at, NEW.created_at);
        ELSIF OLD.status = 'open' THEN
            NEW.closed_at := moment;
        ELSE
            NEW.closed_at := OLD.closed_at;
        END IF;
        anchor := NEW.closed_at;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.retired_at IS NULL AND NEW.retired_at IS NOT NULL
        AND (NEW.retired_at > moment OR anchor IS NULL
            OR anchor > moment - INTERVAL '4320 hours') THEN
        RAISE EXCEPTION 'Origin retirement requires 180 continuously inactive days' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

-- migrate:down
CREATE OR REPLACE FUNCTION listings.guard_origin() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    anchor timestamptz;
    moment timestamptz := statement_timestamp();
BEGIN
    IF TG_OP = 'INSERT' AND NEW.retired_at IS NOT NULL THEN
        RAISE EXCEPTION 'New origins must contain live required fields' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' AND (NEW.id IS DISTINCT FROM OLD.id
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
        OR (OLD.retired_at IS NOT NULL AND (to_jsonb(NEW) - 'search_vector')
            IS DISTINCT FROM (to_jsonb(OLD) - 'search_vector'))) THEN
        RAISE EXCEPTION 'Origin identity or retired content cannot be rewritten' USING ERRCODE = '23514';
    END IF;
    IF TG_TABLE_NAME = 'sale_listings' THEN
        IF TG_OP = 'UPDATE' AND NEW.owner_id IS DISTINCT FROM OLD.owner_id THEN
            RAISE EXCEPTION 'Listing owner is immutable' USING ERRCODE = '23514';
        END IF;
        IF NEW.selected_buyer_id IS NOT NULL AND (TG_OP = 'INSERT'
            OR NEW.selected_buyer_id IS DISTINCT FROM OLD.selected_buyer_id) THEN
            IF NEW.retired_at IS NOT NULL OR NEW.availability <> 'available'
                OR NEW.available_from > moment OR NEW.available_until <= moment THEN
                RAISE EXCEPTION 'Selection requires a currently available listing' USING ERRCODE = '23514';
            END IF;
        END IF;
        IF TG_OP = 'UPDATE' THEN
            anchor := OLD.retirement_eligible_since;
            IF anchor IS NULL AND OLD.available_until <= moment THEN
                anchor := greatest(OLD.available_until, OLD.created_at);
            END IF;
        END IF;
        IF NEW.availability = 'unavailable' OR NEW.available_until <= moment THEN
            NEW.retirement_eligible_since := coalesce(anchor,
                CASE WHEN NEW.available_until <= moment
                    THEN greatest(NEW.available_until, NEW.created_at) ELSE moment END);
        ELSE
            NEW.retirement_eligible_since := NULL;
        END IF;
        anchor := NEW.retirement_eligible_since;
    ELSE
        IF TG_OP = 'UPDATE' AND NEW.author_id IS DISTINCT FROM OLD.author_id THEN
            RAISE EXCEPTION 'Wanted Request author is immutable' USING ERRCODE = '23514';
        END IF;
        IF NEW.status = 'open' THEN
            NEW.closed_at := NULL;
        ELSIF TG_OP = 'INSERT' THEN
            NEW.closed_at := coalesce(NEW.closed_at, NEW.created_at);
        ELSIF OLD.status = 'open' THEN
            NEW.closed_at := moment;
        ELSE
            NEW.closed_at := OLD.closed_at;
        END IF;
        anchor := NEW.closed_at;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.retired_at IS NULL AND NEW.retired_at IS NOT NULL
        AND (NEW.retired_at > moment OR anchor IS NULL
            OR anchor > moment - INTERVAL '4320 hours') THEN
        RAISE EXCEPTION 'Origin retirement requires 180 continuously inactive days' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
