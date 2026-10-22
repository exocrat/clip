-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Existing entry payloads cannot be assigned SDK metadata or recipient-only
-- retry routing by inference. Require an owner-API reconciliation before this
-- forward migration is applied to any database that already contains entries.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM conversations.entries LIMIT 1) THEN
        RAISE EXCEPTION 'conversation entries require reviewed message-transport reconciliation';
    END IF;
END;
$$;

ALTER TABLE conversations.entries
    DROP CONSTRAINT entries_kind_check,
    DROP CONSTRAINT entries_conversation_id_sender_id_client_operation_id_key;
ALTER TABLE conversations.entries
    ADD COLUMN recipient_id uuid REFERENCES identity.users ON DELETE RESTRICT;
ALTER TABLE conversations.entries
    ADD CONSTRAINT entries_kind_check
        CHECK (kind IN ('message', 'protocol_control', 'offer', 'contact_share')),
    ADD CONSTRAINT entries_control_recipient_pair CHECK (
        (kind = 'protocol_control' AND recipient_id IS NOT NULL)
        OR (kind <> 'protocol_control' AND recipient_id IS NULL)
    );
ALTER TABLE conversations.entries
    ADD CONSTRAINT entries_sender_operation_unique UNIQUE (sender_id, client_operation_id);

ALTER TABLE conversations.encrypted_payloads
    ALTER COLUMN sender_key_version_id DROP NOT NULL,
    ALTER COLUMN recipient_key_version_id DROP NOT NULL,
    ADD COLUMN protocol_version text NOT NULL CHECK (protocol_version <> ''),
    ADD COLUMN sdk_message_type text NOT NULL
        CHECK (sdk_message_type IN ('ciphertext', 'prekey_bundle', 'retry_request')),
    ADD COLUMN client_timestamp_ms bigint NOT NULL CHECK (client_timestamp_ms >= 0),
    ADD CONSTRAINT retry_payload_key_pair CHECK (
        (sdk_message_type = 'retry_request'
            AND sender_key_version_id IS NULL AND recipient_key_version_id IS NULL)
        OR (sdk_message_type <> 'retry_request'
            AND sender_key_version_id IS NOT NULL AND recipient_key_version_id IS NOT NULL
            AND sender_key_version_id <> recipient_key_version_id)
    );

CREATE OR REPLACE FUNCTION conversations.guard_entry() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    thread conversations.threads%ROWTYPE;
    assigned bigint;
    expected_recipient uuid;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Preserve entry markers; purge retained content instead' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF ROW(NEW.id, NEW.conversation_id, NEW.sequence, NEW.sender_id,
            NEW.client_operation_id, NEW.kind, NEW.recipient_id, NEW.created_at)
            IS DISTINCT FROM ROW(OLD.id, OLD.conversation_id, OLD.sequence,
                OLD.sender_id, OLD.client_operation_id, OLD.kind,
                OLD.recipient_id, OLD.created_at)
            OR (OLD.content_deleted_at IS NOT NULL
                AND NEW.content_deleted_at IS DISTINCT FROM OLD.content_deleted_at) THEN
            RAISE EXCEPTION 'Entry routing, operation identity and deletion are immutable' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;

    SELECT * INTO thread FROM conversations.threads
        WHERE id = NEW.conversation_id FOR UPDATE;
    IF NOT FOUND OR thread.participant_writes_blocked_at IS NOT NULL THEN
        RAISE EXCEPTION 'New entries are disabled for this conversation' USING ERRCODE = '23514';
    END IF;
    expected_recipient := CASE WHEN NEW.sender_id = thread.initiator_id
        THEN thread.counterparty_id ELSE thread.initiator_id END;
    IF NEW.kind = 'protocol_control' THEN
        IF NEW.recipient_id IS DISTINCT FROM expected_recipient THEN
            RAISE EXCEPTION 'Protocol controls must target the other conversation member' USING ERRCODE = '23514';
        END IF;
    ELSIF NEW.recipient_id IS NOT NULL THEN
        RAISE EXCEPTION 'Only protocol controls have a private recipient' USING ERRCODE = '23514';
    END IF;

    NEW.created_at := clock_timestamp();
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

CREATE OR REPLACE FUNCTION conversations.guard_payload() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    entry conversations.entries%ROWTYPE;
    thread conversations.threads%ROWTYPE;
    sender_key conversations.public_key_versions%ROWTYPE;
    recipient_key conversations.public_key_versions%ROWTYPE;
    expected_recipient uuid;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Message envelopes are immutable; append a new entry' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO entry FROM conversations.entries WHERE id = NEW.entry_id;
    SELECT * INTO thread FROM conversations.threads WHERE id = entry.conversation_id;
    IF entry.id IS NULL OR entry.content_deleted_at IS NOT NULL
        OR NEW.protocol_id <> 'open-e2ee-signal' OR NEW.protocol_version <> '13.0.0'
        OR NEW.envelope_version <> 1 THEN
        RAISE EXCEPTION 'Envelope protocol metadata must match the selected CLIP protocol' USING ERRCODE = '23514';
    END IF;

    IF NEW.sdk_message_type = 'retry_request' THEN
        expected_recipient := CASE WHEN entry.sender_id = thread.initiator_id
            THEN thread.counterparty_id ELSE thread.initiator_id END;
        IF entry.kind <> 'protocol_control' OR entry.recipient_id IS DISTINCT FROM expected_recipient
            OR NEW.sender_key_version_id IS NOT NULL OR NEW.recipient_key_version_id IS NOT NULL THEN
            RAISE EXCEPTION 'Retry controls require recipient-only routing and no key references' USING ERRCODE = '23514';
        END IF;
    ELSE
        IF entry.kind = 'protocol_control'
            OR (NEW.sdk_message_type = 'prekey_bundle' AND entry.kind <> 'message') THEN
            RAISE EXCEPTION 'SDK message type is incompatible with its entry kind' USING ERRCODE = '23514';
        END IF;
        SELECT * INTO sender_key FROM conversations.public_key_versions
            WHERE id = NEW.sender_key_version_id;
        SELECT * INTO recipient_key FROM conversations.public_key_versions
            WHERE id = NEW.recipient_key_version_id;
        expected_recipient := CASE WHEN entry.sender_id = thread.initiator_id
            THEN thread.counterparty_id ELSE thread.initiator_id END;
        IF sender_key.id IS NULL OR recipient_key.id IS NULL
            OR sender_key.user_id <> entry.sender_id OR recipient_key.user_id <> expected_recipient
            OR sender_key.protocol_id <> NEW.protocol_id OR recipient_key.protocol_id <> NEW.protocol_id THEN
            RAISE EXCEPTION 'Envelope key owners and protocol must match the entry participants' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION conversations.check_entry_content() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    target uuid;
    entry conversations.entries%ROWTYPE;
    payload boolean;
    share boolean;
    offer_revision boolean;
BEGIN
    IF TG_TABLE_NAME = 'entries' THEN
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;
    ELSE
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.entry_id ELSE NEW.entry_id END;
    END IF;
    SELECT * INTO entry FROM conversations.entries WHERE id = target;
    IF NOT FOUND THEN RETURN NULL; END IF;
    payload := EXISTS (SELECT 1 FROM conversations.encrypted_payloads WHERE entry_id = target);
    share := EXISTS (SELECT 1 FROM conversations.contact_shares WHERE entry_id = target);
    offer_revision := EXISTS (SELECT 1 FROM conversations.offer_revisions WHERE entry_id = target);
    IF (entry.content_deleted_at IS NOT NULL AND (payload OR share OR offer_revision))
        OR (entry.content_deleted_at IS NULL AND (
            (entry.kind IN ('message', 'protocol_control') AND (NOT payload OR share OR offer_revision))
            OR (entry.kind = 'contact_share' AND (NOT payload OR NOT share OR offer_revision))
            OR (entry.kind = 'offer' AND (NOT offer_revision OR share)))) THEN
        RAISE EXCEPTION 'Entry kind, retained payload and subtype references must agree' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;

COMMENT ON COLUMN conversations.entries.recipient_id IS
    'Set only for retry_request protocol controls; retrieval returns those entries only to this thread member.';
COMMENT ON COLUMN conversations.encrypted_payloads.client_timestamp_ms IS
    'SDK replay metadata only; never authoritative for sequence, activity, retention, or authorization.';

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM conversations.entries LIMIT 1) THEN
        RAISE EXCEPTION 'local/test rollback refused while conversation entries exist';
    END IF;
END;
$$;

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

CREATE OR REPLACE FUNCTION conversations.guard_payload() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    entry conversations.entries%ROWTYPE;
    thread conversations.threads%ROWTYPE;
    sender_key conversations.public_key_versions%ROWTYPE;
    recipient_key conversations.public_key_versions%ROWTYPE;
    other_user uuid;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Encrypted envelopes are immutable; append a new entry' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO entry FROM conversations.entries WHERE id = NEW.entry_id;
    SELECT * INTO thread FROM conversations.threads WHERE id = entry.conversation_id;
    SELECT * INTO sender_key FROM conversations.public_key_versions WHERE id = NEW.sender_key_version_id;
    SELECT * INTO recipient_key FROM conversations.public_key_versions WHERE id = NEW.recipient_key_version_id;
    other_user := CASE WHEN entry.sender_id = thread.initiator_id THEN thread.counterparty_id ELSE thread.initiator_id END;
    IF entry.id IS NULL OR entry.content_deleted_at IS NOT NULL OR sender_key.id IS NULL OR recipient_key.id IS NULL
        OR sender_key.user_id <> entry.sender_id OR recipient_key.user_id <> other_user
        OR sender_key.protocol_id <> NEW.protocol_id OR recipient_key.protocol_id <> NEW.protocol_id THEN
        RAISE EXCEPTION 'Envelope key owners and protocol must match the entry participants' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION conversations.check_entry_content() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    target uuid;
    entry conversations.entries%ROWTYPE;
    payload boolean;
    share boolean;
    offer_revision boolean;
BEGIN
    IF TG_TABLE_NAME = 'entries' THEN
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;
    ELSE
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.entry_id ELSE NEW.entry_id END;
    END IF;
    SELECT * INTO entry FROM conversations.entries WHERE id = target;
    IF NOT FOUND THEN RETURN NULL; END IF;
    payload := EXISTS (SELECT 1 FROM conversations.encrypted_payloads WHERE entry_id = target);
    share := EXISTS (SELECT 1 FROM conversations.contact_shares WHERE entry_id = target);
    offer_revision := EXISTS (SELECT 1 FROM conversations.offer_revisions WHERE entry_id = target);
    IF (entry.content_deleted_at IS NOT NULL AND (payload OR share OR offer_revision))
        OR (entry.content_deleted_at IS NULL AND (
            (entry.kind = 'message' AND (NOT payload OR share OR offer_revision))
            OR (entry.kind = 'contact_share' AND (NOT payload OR NOT share OR offer_revision))
            OR (entry.kind = 'offer' AND (NOT offer_revision OR share)))) THEN
        RAISE EXCEPTION 'Entry kind, retained payload and subtype references must agree' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;

ALTER TABLE conversations.entries
    DROP CONSTRAINT entries_control_recipient_pair,
    DROP CONSTRAINT entries_sender_operation_unique,
    DROP COLUMN recipient_id,
    ADD CONSTRAINT entries_conversation_id_sender_id_client_operation_id_key
        UNIQUE (conversation_id, sender_id, client_operation_id),
    DROP CONSTRAINT entries_kind_check,
    ADD CONSTRAINT entries_kind_check CHECK (kind IN ('message', 'offer', 'contact_share'));
ALTER TABLE conversations.encrypted_payloads
    DROP CONSTRAINT retry_payload_key_pair,
    DROP COLUMN protocol_version,
    DROP COLUMN sdk_message_type,
    DROP COLUMN client_timestamp_ms,
    ALTER COLUMN sender_key_version_id SET NOT NULL,
    ALTER COLUMN recipient_key_version_id SET NOT NULL;
