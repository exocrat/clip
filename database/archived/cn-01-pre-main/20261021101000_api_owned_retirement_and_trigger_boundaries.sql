-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- The origin owners keep pending request identity; Conversations keeps the
-- no-write marker and the durable result needed to make retries unambiguous.
ALTER TABLE listings.sale_listings
    ADD COLUMN retirement_pending_operation_id uuid,
    ADD COLUMN retirement_pending_cutoff_utc timestamptz(6),
    ADD CONSTRAINT listing_retirement_pending_request_pair CHECK (
        (retirement_pending_operation_id IS NULL) = (retirement_pending_cutoff_utc IS NULL)
    );
ALTER TABLE search.wanted_requests
    ADD COLUMN retirement_pending_operation_id uuid,
    ADD COLUMN retirement_pending_cutoff_utc timestamptz(6),
    ADD CONSTRAINT wanted_retirement_pending_request_pair CHECK (
        (retirement_pending_operation_id IS NULL) = (retirement_pending_cutoff_utc IS NULL)
    );
ALTER TABLE conversations.threads
    ADD COLUMN participant_writes_blocked_at timestamptz(6);

CREATE TABLE conversations.origin_retirement_operations (
    operation_id uuid PRIMARY KEY,
    origin_kind text NOT NULL CHECK (origin_kind IN ('listing', 'wanted_request')),
    origin_id uuid NOT NULL,
    cutoff_utc timestamptz(6) NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('marked', 'blocked_recent_activity', 'already_marked')),
    marked_count integer NOT NULL CHECK (marked_count >= 0),
    created_at timestamptz(6) NOT NULL DEFAULT clock_timestamp(),
    CHECK (outcome <> 'blocked_recent_activity' OR marked_count = 0)
);
CREATE INDEX origin_retirement_operations_origin
    ON conversations.origin_retirement_operations (origin_kind, origin_id, created_at DESC);

COMMENT ON TABLE conversations.origin_retirement_operations IS
    'Content-free, globally idempotent results for Conversations origin-retirement operations.';
COMMENT ON COLUMN conversations.threads.participant_writes_blocked_at IS
    'Conversations sets this under the thread lock; participant-write guards reject writes after it is set.';

-- Listings/Search triggers now inspect only their own origin rows. Eligibility,
-- membership and activity queries are made through the owning public APIs.
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
                OR NEW.available_from > moment
                OR (NEW.available_until IS NOT NULL AND NEW.available_until <= moment) THEN
                RAISE EXCEPTION 'Selection requires a currently available listing' USING ERRCODE = '23514';
            END IF;
        END IF;
        IF TG_OP = 'UPDATE' THEN
            anchor := OLD.retirement_eligible_since;
            IF anchor IS NULL AND OLD.available_until IS NOT NULL AND OLD.available_until <= moment THEN
                anchor := greatest(OLD.available_until, OLD.created_at);
            END IF;
        END IF;
        IF NEW.availability = 'unavailable' OR
            (NEW.available_until IS NOT NULL AND NEW.available_until <= moment) THEN
            NEW.retirement_eligible_since := coalesce(anchor,
                CASE WHEN NEW.available_until IS NOT NULL AND NEW.available_until <= moment
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

-- Thread identity/ordering remains local integrity. Insert-time origin and
-- account checks now belong to Listings/Search/Identity public operations.
CREATE OR REPLACE FUNCTION conversations.guard_thread() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (
        NEW.id IS DISTINCT FROM OLD.id
        OR NEW.listing_id IS DISTINCT FROM OLD.listing_id
        OR NEW.wanted_request_id IS DISTINCT FROM OLD.wanted_request_id
        OR NEW.initiator_id IS DISTINCT FROM OLD.initiator_id
        OR NEW.counterparty_id IS DISTINCT FROM OLD.counterparty_id
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
        OR NEW.next_sequence < OLD.next_sequence
        OR NEW.last_activity_at < OLD.last_activity_at
        OR (OLD.participant_writes_blocked_at IS NOT NULL
            AND NEW.participant_writes_blocked_at IS DISTINCT FROM OLD.participant_writes_blocked_at)
    ) THEN
        RAISE EXCEPTION 'Thread identity, ordering and retirement marker are immutable' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

-- Entries and retirement marking contend on the same row lock. Activity uses
-- server time after acquiring that lock, never the client's created_at value.
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
    SELECT * INTO thread FROM conversations.threads
        WHERE id = NEW.conversation_id FOR UPDATE;
    IF NOT FOUND OR thread.participant_writes_blocked_at IS NOT NULL THEN
        RAISE EXCEPTION 'New entries are disabled for this conversation' USING ERRCODE = '23514';
    END IF;
    UPDATE conversations.threads SET next_sequence = next_sequence + 1,
        last_activity_at = greatest(last_activity_at, clock_timestamp())
        WHERE id = NEW.conversation_id RETURNING next_sequence - 1 INTO assigned;
    IF assigned IS NULL OR (NEW.sequence IS NOT NULL AND NEW.sequence <> assigned)
        OR NEW.content_deleted_at IS NOT NULL THEN
        RAISE EXCEPTION 'New entries require the next server sequence and live content' USING ERRCODE = '23514';
    END IF;
    NEW.sequence := assigned;
    RETURN NEW;
END;
$$;

-- Offer policy/availability is validated by Listings. Conversations retains
-- offer-entry identity, revision, withdrawal and local no-write protections.
CREATE OR REPLACE FUNCTION conversations.guard_offer_revision() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    offer conversations.offers%ROWTYPE;
    entry conversations.entries%ROWTYPE;
    thread conversations.threads%ROWTYPE;
    previous conversations.offer_revisions%ROWTYPE;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Offer revisions are append-only' USING ERRCODE = '23514';
    END IF;
    UPDATE conversations.offers SET next_revision = next_revision
        WHERE id = NEW.offer_id RETURNING * INTO offer;
    SELECT * INTO entry FROM conversations.entries WHERE id = NEW.entry_id;
    SELECT * INTO thread FROM conversations.threads
        WHERE id = offer.conversation_id FOR UPDATE;
    IF NOT FOUND OR thread.participant_writes_blocked_at IS NOT NULL THEN
        RAISE EXCEPTION 'Participant writes are disabled for this conversation' USING ERRCODE = '23514';
    END IF;
    IF offer.id IS NULL OR entry.id IS NULL OR thread.id IS NULL OR thread.listing_id IS NULL
        OR entry.kind <> 'offer' OR entry.content_deleted_at IS NOT NULL
        OR entry.conversation_id <> offer.conversation_id OR entry.sender_id <> offer.buyer_id
        OR NEW.revision IS DISTINCT FROM offer.current_revision
        OR NEW.revision <> offer.next_revision - 1 THEN
        RAISE EXCEPTION 'Offer revision must match its current buyer entry and listing conversation' USING ERRCODE = '23514';
    END IF;
    IF NEW.status = 'withdrawn' THEN
        SELECT * INTO previous FROM conversations.offer_revisions WHERE offer_id = NEW.offer_id
            ORDER BY revision DESC LIMIT 1;
        IF previous.status IS DISTINCT FROM 'submitted' OR previous.amount_paise <> NEW.amount_paise THEN
            RAISE EXCEPTION 'Withdrawal must follow a submitted revision and retain its amount' USING ERRCODE = '23514';
        END IF;
    END IF;
    UPDATE conversations.threads SET last_activity_at = greatest(last_activity_at, clock_timestamp())
        WHERE id = thread.id;
    RETURN NEW;
END;
$$;

-- Contact-share subtype writes are also serialized with marker creation.
CREATE OR REPLACE FUNCTION conversations.reject_reference_change() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    entry conversations.entries%ROWTYPE;
    thread conversations.threads%ROWTYPE;
BEGIN
    IF TG_TABLE_NAME = 'contact_shares' AND TG_OP = 'INSERT' THEN
        SELECT * INTO entry FROM conversations.entries WHERE id = NEW.entry_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Contact share requires an existing conversation entry' USING ERRCODE = '23514';
        END IF;
        SELECT * INTO thread FROM conversations.threads
            WHERE id = entry.conversation_id FOR UPDATE;
        IF NOT FOUND OR thread.participant_writes_blocked_at IS NOT NULL THEN
            RAISE EXCEPTION 'Participant writes are disabled for this conversation' USING ERRCODE = '23514';
        END IF;
        UPDATE conversations.threads SET last_activity_at = greatest(last_activity_at, clock_timestamp())
            WHERE id = thread.id;
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Preserve immutable references; use the documented retirement path' USING ERRCODE = '23514';
END;
$$;
DROP TRIGGER share_identity ON conversations.contact_shares;
CREATE TRIGGER share_identity BEFORE INSERT OR UPDATE ON conversations.contact_shares
    FOR EACH ROW EXECUTE FUNCTION conversations.reject_reference_change();

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- This rollback is intentionally limited to an empty disposable database.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM conversations.origin_retirement_operations)
        OR EXISTS (SELECT 1 FROM listings.sale_listings
            WHERE retirement_pending_operation_id IS NOT NULL OR retirement_pending_cutoff_utc IS NOT NULL)
        OR EXISTS (SELECT 1 FROM search.wanted_requests
            WHERE retirement_pending_operation_id IS NOT NULL OR retirement_pending_cutoff_utc IS NOT NULL)
        OR EXISTS (SELECT 1 FROM conversations.threads WHERE participant_writes_blocked_at IS NOT NULL) THEN
        RAISE EXCEPTION 'Cannot roll back while retirement outcomes or markers exist' USING ERRCODE = 'check_violation';
    END IF;
END;
$$;

-- Restore the exact pre-migration trigger behavior for disposable rollback.
DROP TRIGGER share_identity ON conversations.contact_shares;
CREATE TRIGGER share_identity BEFORE UPDATE ON conversations.contact_shares
    FOR EACH ROW EXECUTE FUNCTION conversations.reject_reference_change();
CREATE OR REPLACE FUNCTION conversations.reject_reference_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Preserve immutable references; use the documented retirement path' USING ERRCODE = '23514';
END;
$$;
CREATE OR REPLACE FUNCTION listings.guard_origin() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    anchor timestamptz;
    moment timestamptz := statement_timestamp();
    target uuid;
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
    target := NEW.id;
    IF TG_TABLE_NAME = 'sale_listings' THEN
        IF TG_OP = 'INSERT' AND NOT EXISTS (SELECT 1 FROM identity.users
            WHERE id = NEW.owner_id AND account_class = 'regular' AND status = 'active') THEN
            RAISE EXCEPTION 'New listings require an active regular owner' USING ERRCODE = '23514';
        END IF;
        IF TG_OP = 'UPDATE' AND NEW.owner_id IS DISTINCT FROM OLD.owner_id THEN
            RAISE EXCEPTION 'Listing owner is immutable' USING ERRCODE = '23514';
        END IF;
        IF NEW.selected_buyer_id IS NOT NULL AND (TG_OP = 'INSERT'
            OR NEW.selected_buyer_id IS DISTINCT FROM OLD.selected_buyer_id) THEN
            IF NEW.retired_at IS NOT NULL OR NEW.availability <> 'available'
                OR NEW.available_from > moment OR NEW.available_until <= moment
                OR NOT EXISTS (SELECT 1 FROM conversations.threads WHERE listing_id = NEW.id
                    AND initiator_id = NEW.selected_buyer_id AND counterparty_id = NEW.owner_id) THEN
                RAISE EXCEPTION 'Selection requires an available listing and its conversation buyer' USING ERRCODE = '23514';
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
    IF TG_OP = 'UPDATE' AND OLD.retired_at IS NULL AND NEW.retired_at IS NOT NULL THEN
        IF NEW.retired_at > moment OR anchor IS NULL OR anchor > moment - INTERVAL '4320 hours' THEN
            RAISE EXCEPTION 'Origin retirement requires 180 continuously inactive days' USING ERRCODE = '23514';
        END IF;
        PERFORM 1 FROM conversations.threads
            WHERE (TG_TABLE_NAME = 'sale_listings' AND listing_id = target)
                OR (TG_TABLE_NAME = 'wanted_requests' AND wanted_request_id = target)
            ORDER BY id FOR UPDATE;
        IF EXISTS (SELECT 1 FROM conversations.threads
            WHERE ((TG_TABLE_NAME = 'sale_listings' AND listing_id = target)
                OR (TG_TABLE_NAME = 'wanted_requests' AND wanted_request_id = target))
            AND last_activity_at > moment - INTERVAL '2160 hours') THEN
            RAISE EXCEPTION 'Origin retirement requires 90 days without participant writes' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE OR REPLACE FUNCTION conversations.guard_thread() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    owner uuid;
    unavailable boolean;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.id IS DISTINCT FROM OLD.id OR NEW.listing_id IS DISTINCT FROM OLD.listing_id
            OR NEW.wanted_request_id IS DISTINCT FROM OLD.wanted_request_id
            OR NEW.initiator_id IS DISTINCT FROM OLD.initiator_id
            OR NEW.counterparty_id IS DISTINCT FROM OLD.counterparty_id
            OR NEW.created_at IS DISTINCT FROM OLD.created_at
            OR NEW.next_sequence < OLD.next_sequence OR NEW.last_activity_at < OLD.last_activity_at THEN
            RAISE EXCEPTION 'Thread identity and ordering cannot be rewritten' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.listing_id IS NOT NULL THEN
        UPDATE listings.sale_listings SET revision = revision WHERE id = NEW.listing_id
            RETURNING owner_id, retired_at IS NOT NULL INTO owner, unavailable;
    ELSE
        UPDATE search.wanted_requests SET revision = revision WHERE id = NEW.wanted_request_id
            RETURNING author_id, retired_at IS NOT NULL OR status <> 'open' INTO owner, unavailable;
        IF NOT EXISTS (SELECT 1 FROM identity.users WHERE id = NEW.initiator_id AND account_class = 'regular') THEN
            RAISE EXCEPTION 'Wanted Request responders must be regular accounts' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF owner IS NULL OR unavailable OR owner <> NEW.counterparty_id THEN
        RAISE EXCEPTION 'Thread participants must match an eligible origin' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
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
CREATE OR REPLACE FUNCTION conversations.guard_offer_revision() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    offer conversations.offers%ROWTYPE;
    entry conversations.entries%ROWTYPE;
    thread conversations.threads%ROWTYPE;
    item listings.sale_listings%ROWTYPE;
    previous conversations.offer_revisions%ROWTYPE;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Offer revisions are append-only' USING ERRCODE = '23514';
    END IF;
    UPDATE conversations.offers SET next_revision = next_revision WHERE id = NEW.offer_id RETURNING * INTO offer;
    SELECT * INTO entry FROM conversations.entries WHERE id = NEW.entry_id;
    SELECT * INTO thread FROM conversations.threads WHERE id = offer.conversation_id;
    SELECT * INTO item FROM listings.sale_listings WHERE id = thread.listing_id FOR UPDATE;
    IF offer.id IS NULL OR entry.id IS NULL OR entry.kind <> 'offer'
        OR entry.content_deleted_at IS NOT NULL OR entry.conversation_id <> offer.conversation_id
        OR entry.sender_id <> offer.buyer_id OR NEW.revision IS DISTINCT FROM offer.current_revision
        OR NEW.revision <> offer.next_revision - 1 OR item.retired_at IS NOT NULL THEN
        RAISE EXCEPTION 'Offer revision must match its current buyer entry and live origin' USING ERRCODE = '23514';
    END IF;
    IF NEW.status = 'submitted' AND (item.availability <> 'available'
        OR item.available_from > statement_timestamp()
        OR item.available_until <= statement_timestamp()) THEN
        RAISE EXCEPTION 'New or revised offers require current listing availability' USING ERRCODE = '23514';
    END IF;
    IF NEW.status = 'withdrawn' THEN
        SELECT * INTO previous FROM conversations.offer_revisions WHERE offer_id = NEW.offer_id
            ORDER BY revision DESC LIMIT 1;
        IF previous.status IS DISTINCT FROM 'submitted' OR previous.amount_paise <> NEW.amount_paise THEN
            RAISE EXCEPTION 'Withdrawal must follow a submitted revision and retain its amount' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP INDEX conversations.origin_retirement_operations_origin;
DROP TABLE conversations.origin_retirement_operations;
ALTER TABLE conversations.threads DROP COLUMN participant_writes_blocked_at;
ALTER TABLE search.wanted_requests DROP COLUMN retirement_pending_operation_id;
ALTER TABLE search.wanted_requests DROP COLUMN retirement_pending_cutoff_utc;
ALTER TABLE listings.sale_listings DROP COLUMN retirement_pending_operation_id;
ALTER TABLE listings.sale_listings DROP COLUMN retirement_pending_cutoff_utc;
