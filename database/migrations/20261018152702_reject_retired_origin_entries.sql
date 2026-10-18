-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- Forward correction for PR #5: preserve the published baseline and its locks.
CREATE OR REPLACE FUNCTION conversations.guard_entry() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    thread conversations.threads%ROWTYPE;
    assigned bigint;
    origin_retired_at timestamptz;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Preserve entry markers; purge retained content instead' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF ROW(NEW.id, NEW.conversation_id, NEW.sequence, NEW.sender_id, NEW.client_operation_id, NEW.kind, NEW.created_at)
            IS DISTINCT FROM ROW(OLD.id, OLD.conversation_id, OLD.sequence, OLD.sender_id,
                OLD.client_operation_id, OLD.kind, OLD.created_at)
            OR (OLD.content_deleted_at IS NOT NULL AND NEW.content_deleted_at IS DISTINCT FROM OLD.content_deleted_at) THEN
            RAISE EXCEPTION 'Entry routing, operation identity and deletion are immutable' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    SELECT * INTO thread FROM conversations.threads WHERE id = NEW.conversation_id;
    IF thread.listing_id IS NOT NULL THEN
        UPDATE listings.sale_listings SET revision = revision WHERE id = thread.listing_id
            RETURNING retired_at INTO origin_retired_at;
    ELSE
        UPDATE search.wanted_requests SET revision = revision WHERE id = thread.wanted_request_id
            RETURNING retired_at INTO origin_retired_at;
    END IF;
    -- The origin version write above both serializes retirement and reads its
    -- current state. Ordinary closure/unavailability still permits discussion;
    -- permanent retirement must reject every new entry before sequence changes.
    IF NOT FOUND OR origin_retired_at IS NOT NULL THEN
        RAISE EXCEPTION 'New entries require a non-retired origin' USING ERRCODE = '23514';
    END IF;
    UPDATE conversations.threads SET next_sequence = next_sequence + 1,
        last_activity_at = greatest(last_activity_at, NEW.created_at)
        WHERE id = NEW.conversation_id RETURNING next_sequence - 1 INTO assigned;
    IF assigned IS NULL OR (NEW.sequence IS NOT NULL AND NEW.sequence <> assigned)
        OR NEW.content_deleted_at IS NOT NULL THEN
        RAISE EXCEPTION 'New entries require the next server sequence and live content' USING ERRCODE = '23514';
    END IF;
    NEW.sequence := assigned;
    RETURN NEW;
END;
$$;

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- Restore the exact previous entry guard for disposable migration rollback.
CREATE OR REPLACE FUNCTION conversations.guard_entry() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    thread conversations.threads%ROWTYPE;
    assigned bigint;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Preserve entry markers; purge retained content instead' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF ROW(NEW.id, NEW.conversation_id, NEW.sequence, NEW.sender_id, NEW.client_operation_id, NEW.kind, NEW.created_at)
            IS DISTINCT FROM ROW(OLD.id, OLD.conversation_id, OLD.sequence, OLD.sender_id,
                OLD.client_operation_id, OLD.kind, OLD.created_at)
            OR (OLD.content_deleted_at IS NOT NULL AND NEW.content_deleted_at IS DISTINCT FROM OLD.content_deleted_at) THEN
            RAISE EXCEPTION 'Entry routing, operation identity and deletion are immutable' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    SELECT * INTO thread FROM conversations.threads WHERE id = NEW.conversation_id;
    IF thread.listing_id IS NOT NULL THEN
        UPDATE listings.sale_listings SET revision = revision WHERE id = thread.listing_id;
    ELSE
        UPDATE search.wanted_requests SET revision = revision WHERE id = thread.wanted_request_id;
    END IF;
    UPDATE conversations.threads SET next_sequence = next_sequence + 1,
        last_activity_at = greatest(last_activity_at, NEW.created_at)
        WHERE id = NEW.conversation_id RETURNING next_sequence - 1 INTO assigned;
    IF assigned IS NULL OR (NEW.sequence IS NOT NULL AND NEW.sequence <> assigned)
        OR NEW.content_deleted_at IS NOT NULL THEN
        RAISE EXCEPTION 'New entries require the next server sequence and live content' USING ERRCODE = '23514';
    END IF;
    NEW.sequence := assigned;
    RETURN NEW;
END;
$$;
