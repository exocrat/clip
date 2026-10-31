-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Main owns retirement columns/ledger. Harden only local Conversations guards;
-- preserve the published schema and its canonical no-write marker name.
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
        OR (OLD.participant_writes_disabled_at IS NOT NULL
            AND NEW.participant_writes_disabled_at IS DISTINCT FROM OLD.participant_writes_disabled_at)
    ) THEN
        RAISE EXCEPTION 'Thread identity, ordering and retirement marker are immutable' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

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
    IF NOT FOUND OR thread.participant_writes_disabled_at IS NOT NULL THEN
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
        IF NOT FOUND OR thread.participant_writes_disabled_at IS NOT NULL THEN
            RAISE EXCEPTION 'Participant writes are disabled for this conversation' USING ERRCODE = '23514';
        END IF;
        UPDATE conversations.threads SET last_activity_at = greatest(last_activity_at, clock_timestamp())
            WHERE id = thread.id;
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Preserve immutable references; use the documented retirement path' USING ERRCODE = '23514';
END;
$$;

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Restore the published guard definitions without deleting retirement data.
CREATE OR REPLACE FUNCTION conversations.guard_thread() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (NEW.id IS DISTINCT FROM OLD.id
        OR NEW.listing_id IS DISTINCT FROM OLD.listing_id
        OR NEW.wanted_request_id IS DISTINCT FROM OLD.wanted_request_id
        OR NEW.initiator_id IS DISTINCT FROM OLD.initiator_id
        OR NEW.counterparty_id IS DISTINCT FROM OLD.counterparty_id
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
        OR NEW.next_sequence < OLD.next_sequence
        OR NEW.last_activity_at < OLD.last_activity_at) THEN
        RAISE EXCEPTION 'Thread identity and ordering cannot be rewritten' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

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
    IF NOT FOUND OR thread.participant_writes_disabled_at IS NOT NULL THEN
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
    RETURN NEW;
END;
$$;

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
        IF NOT FOUND OR thread.participant_writes_disabled_at IS NOT NULL THEN
            RAISE EXCEPTION 'Participant writes are disabled for this conversation' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Preserve immutable references; use the documented retirement path' USING ERRCODE = '23514';
END;
$$;
