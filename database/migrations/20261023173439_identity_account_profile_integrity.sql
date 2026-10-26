-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Reuse the accepted Identity tables. Validate existing rows rather than
-- trimming private data or inventing missing revocation event timestamps.
ALTER TABLE identity.users
    ADD CONSTRAINT users_display_name_length CHECK (
        display_name IS NULL OR char_length(display_name) <= 80
    ),
    ADD CONSTRAINT users_revocation_consistency CHECK (
        (status = 'revoked') = (revoked_at IS NOT NULL)
        AND (revoked_at IS NULL OR revoked_at >= created_at)
    );
ALTER TABLE identity.contacts
    ADD CONSTRAINT contacts_value_lengths CHECK (
        (email IS NULL OR char_length(email) <= 254)
        AND (phone IS NULL OR char_length(phone) <= 254)
        AND (upi_id IS NULL OR char_length(upi_id) <= 254)
    );

-- A verified provider/issuer/subject must keep its original account binding.
-- This local-row guard prevents reassignment; token verification and account
-- eligibility remain service obligations, not a claim made by this trigger.
CREATE FUNCTION identity.guard_external_identity_history() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF ROW(NEW.id, NEW.user_id, NEW.provider, NEW.issuer, NEW.subject, NEW.created_at)
        IS DISTINCT FROM
        ROW(OLD.id, OLD.user_id, OLD.provider, OLD.issuer, OLD.subject, OLD.created_at) THEN
        RAISE EXCEPTION 'Provider identity and account binding are immutable'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER external_identities_history BEFORE UPDATE ON identity.external_identities
    FOR EACH ROW EXECUTE FUNCTION identity.guard_external_identity_history();

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Remove only this migration's guards. Preserve every existing row/table/index
-- and all original lifetime, credential, enrollment and cross-domain references.
DROP TRIGGER external_identities_history ON identity.external_identities;
DROP FUNCTION identity.guard_external_identity_history();
ALTER TABLE identity.contacts DROP CONSTRAINT contacts_value_lengths;
ALTER TABLE identity.users
    DROP CONSTRAINT users_display_name_length,
    DROP CONSTRAINT users_revocation_consistency;
