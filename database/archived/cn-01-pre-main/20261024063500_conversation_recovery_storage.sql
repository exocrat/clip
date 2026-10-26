-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Metadata stays with the content-free entry after payload retention. Existing
-- v1 SDK IDs are exactly the already stored operation UUID; ciphertext is not
-- inspected or rewritten. All business queries below are Conversations-local.
ALTER TABLE conversations.entries
    ADD COLUMN sdk_client_message_id text,
    ADD COLUMN recovery_for_entry_id uuid REFERENCES conversations.entries ON DELETE RESTRICT,
    ADD COLUMN recovery_requester_id uuid,
    ADD COLUMN recovery_family_id uuid,
    ADD COLUMN recovery_attempt bigint,
    ADD COLUMN recovery_kind text;
UPDATE conversations.entries SET sdk_client_message_id = client_operation_id::text
    WHERE kind IN ('message', 'protocol_control', 'contact_share');
-- Existing deferred head/content triggers fire on the metadata backfill.
-- Validate both before further DDL, including when a target has retained v1 rows.
SET CONSTRAINTS conversations.entry_content, conversations.entry_head IMMEDIATE;
SET CONSTRAINTS conversations.entry_content, conversations.entry_head DEFERRED;
ALTER TABLE conversations.entries
    ADD CONSTRAINT entries_sdk_id_bounded CHECK (
        sdk_client_message_id IS NULL OR
        (octet_length(sdk_client_message_id) BETWEEN 1 AND 128
            AND sdk_client_message_id ~ '^[ -~]+$')),
    ADD CONSTRAINT entries_sdk_id_unique UNIQUE (sender_id, sdk_client_message_id),
    ADD CONSTRAINT entries_recovery_shape CHECK (
        (recovery_for_entry_id IS NULL AND recovery_requester_id IS NULL
            AND recovery_family_id IS NULL AND recovery_attempt IS NULL AND recovery_kind IS NULL)
        OR (recovery_for_entry_id IS NOT NULL AND recovery_requester_id IS NOT NULL
            AND recovery_family_id IS NOT NULL AND recovery_attempt IS NOT NULL
            AND recovery_kind IS NOT NULL AND kind = 'protocol_control'
            AND recovery_attempt BETWEEN 1 AND 9007199254740991
            AND recovery_kind IN ('retry-request', 'resend', 'null')
            AND sdk_client_message_id IS NOT NULL
            AND sdk_client_message_id = recovery_family_id::text || ':' || recovery_kind
                || CASE WHEN recovery_attempt = 1 THEN '' ELSE ':' || recovery_attempt::text END));
CREATE UNIQUE INDEX entries_recovery_attempt_unique ON conversations.entries
    (recovery_requester_id, recovery_family_id, recovery_attempt, recovery_kind)
    WHERE recovery_family_id IS NOT NULL;
CREATE INDEX entries_recovery_target ON conversations.entries (recovery_for_entry_id)
    WHERE recovery_for_entry_id IS NOT NULL;

CREATE TABLE conversations.recovery_families (
    requester_id uuid NOT NULL,
    family_id uuid NOT NULL,
    conversation_id uuid NOT NULL REFERENCES conversations.threads ON DELETE RESTRICT,
    original_entry_id uuid NOT NULL REFERENCES conversations.entries ON DELETE RESTRICT,
    first_request_entry_id uuid NOT NULL UNIQUE REFERENCES conversations.entries
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    created_at timestamptz(6) NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (requester_id, family_id),
    FOREIGN KEY (conversation_id, requester_id) REFERENCES conversations.members ON DELETE RESTRICT
);
ALTER TABLE conversations.entries ADD CONSTRAINT entries_recovery_family_fk
    FOREIGN KEY (recovery_requester_id, recovery_family_id)
    REFERENCES conversations.recovery_families ON DELETE RESTRICT;

CREATE FUNCTION conversations.guard_recovery_family() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    original conversations.entries%ROWTYPE;
    thread conversations.threads%ROWTYPE;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'Recovery family bindings are immutable retained guards' USING ERRCODE = '23514';
    END IF;
    -- Same thread lock as participant writes and retirement; cleanup must also
    -- use it. Acquire the original row only after that lock.
    SELECT * INTO thread FROM conversations.threads WHERE id = NEW.conversation_id FOR UPDATE;
    SELECT * INTO original FROM conversations.entries WHERE id = NEW.original_entry_id FOR UPDATE;
    IF thread.id IS NULL OR thread.participant_writes_blocked_at IS NOT NULL
        OR original.id IS NULL OR original.conversation_id <> thread.id
        OR original.kind <> 'message' OR original.content_deleted_at IS NOT NULL
        OR NOT EXISTS (SELECT 1 FROM conversations.encrypted_payloads WHERE entry_id = original.id)
        OR NEW.requester_id IS DISTINCT FROM (CASE WHEN original.sender_id = thread.initiator_id
            THEN thread.counterparty_id ELSE thread.initiator_id END) THEN
        RAISE EXCEPTION 'Recovery requires the original retained chat and its recipient' USING ERRCODE = '23514';
    END IF;
    NEW.created_at := clock_timestamp();
    RETURN NEW;
END;
$$;
CREATE TRIGGER recovery_family_binding BEFORE INSERT OR UPDATE OR DELETE
    ON conversations.recovery_families FOR EACH ROW EXECUTE FUNCTION conversations.guard_recovery_family();

CREATE FUNCTION conversations.check_recovery_first_request() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM conversations.entries WHERE id = NEW.first_request_entry_id
        AND conversation_id = NEW.conversation_id AND recovery_for_entry_id = NEW.original_entry_id
        AND sender_id = NEW.requester_id AND recovery_requester_id = NEW.requester_id
        AND recovery_family_id = NEW.family_id AND recovery_kind = 'retry-request' AND recovery_attempt = 1) THEN
        RAISE EXCEPTION 'Recovery binding requires its first request in the same transaction' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER recovery_first_request AFTER INSERT ON conversations.recovery_families
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION conversations.check_recovery_first_request();

CREATE FUNCTION conversations.guard_recovery_entry() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    family conversations.recovery_families%ROWTYPE;
    original conversations.entries%ROWTYPE;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF ROW(NEW.sdk_client_message_id, NEW.recovery_for_entry_id, NEW.recovery_requester_id,
                NEW.recovery_family_id, NEW.recovery_attempt, NEW.recovery_kind)
            IS DISTINCT FROM ROW(OLD.sdk_client_message_id, OLD.recovery_for_entry_id,
                OLD.recovery_requester_id, OLD.recovery_family_id, OLD.recovery_attempt, OLD.recovery_kind) THEN
            RAISE EXCEPTION 'SDK identity and recovery routing are immutable' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.sdk_client_message_id IS NULL AND NEW.kind IN ('message', 'protocol_control', 'contact_share') THEN
        NEW.sdk_client_message_id := NEW.client_operation_id::text;
    END IF;
    IF NEW.recovery_for_entry_id IS NULL THEN
        -- No unbound suffix IDs; only a complete family can claim recovery.
        IF NEW.sdk_client_message_id IS NOT NULL AND
            NEW.sdk_client_message_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN
            RAISE EXCEPTION 'Ordinary SDK IDs must be UUID-shaped' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    SELECT * INTO family FROM conversations.recovery_families
        WHERE requester_id = NEW.recovery_requester_id AND family_id = NEW.recovery_family_id;
    SELECT * INTO original FROM conversations.entries WHERE id = NEW.recovery_for_entry_id FOR UPDATE;
    IF family.family_id IS NULL OR family.conversation_id <> NEW.conversation_id
        OR family.original_entry_id <> NEW.recovery_for_entry_id OR original.id IS NULL
        OR original.content_deleted_at IS NOT NULL
        OR NOT EXISTS (SELECT 1 FROM conversations.encrypted_payloads WHERE entry_id = original.id) THEN
        RAISE EXCEPTION 'Recovery target must match its live bound family' USING ERRCODE = '23514';
    END IF;
    IF NEW.recovery_kind = 'retry-request' THEN
        IF NEW.sender_id IS DISTINCT FROM family.requester_id THEN
            RAISE EXCEPTION 'Only the original recipient may request recovery' USING ERRCODE = '23514';
        END IF;
    ELSIF NEW.sender_id IS DISTINCT FROM original.sender_id OR NOT EXISTS (
        SELECT 1 FROM conversations.entries WHERE recovery_requester_id = family.requester_id
            AND recovery_family_id = family.family_id AND recovery_attempt = NEW.recovery_attempt
            AND recovery_kind = 'retry-request') THEN
        RAISE EXCEPTION 'Recovery responses require their original sender and accepted request attempt' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
-- entry_order executes first, acquiring the existing thread lock and enforcing
-- participant/no-write/order invariants. This supplemental guard owns new IDs.
CREATE TRIGGER entry_recovery BEFORE INSERT OR UPDATE ON conversations.entries
    FOR EACH ROW EXECUTE FUNCTION conversations.guard_recovery_entry();

ALTER TABLE conversations.encrypted_payloads DROP CONSTRAINT retry_payload_key_pair;
ALTER TABLE conversations.encrypted_payloads ADD CONSTRAINT retry_payload_key_pair CHECK (
    (sender_key_version_id IS NULL AND recipient_key_version_id IS NULL)
    OR (sdk_message_type <> 'retry_request' AND sender_key_version_id IS NOT NULL
        AND recipient_key_version_id IS NOT NULL AND sender_key_version_id <> recipient_key_version_id));

CREATE OR REPLACE FUNCTION conversations.guard_payload() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    entry conversations.entries%ROWTYPE;
    thread conversations.threads%ROWTYPE;
    original_payload conversations.encrypted_payloads%ROWTYPE;
    sender_key conversations.public_key_versions%ROWTYPE;
    recipient_key conversations.public_key_versions%ROWTYPE;
    expected_recipient uuid;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Message envelopes are immutable; append a new entry' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO entry FROM conversations.entries WHERE id = NEW.entry_id;
    SELECT * INTO thread FROM conversations.threads WHERE id = entry.conversation_id;
    expected_recipient := CASE WHEN entry.sender_id = thread.initiator_id
        THEN thread.counterparty_id ELSE thread.initiator_id END;
    IF entry.id IS NULL OR entry.content_deleted_at IS NOT NULL
        OR NEW.protocol_id <> 'open-e2ee-signal' OR NEW.protocol_version <> '13.0.0'
        OR NEW.envelope_version NOT IN (1, 2) THEN
        RAISE EXCEPTION 'Envelope protocol metadata must match the selected CLIP protocol' USING ERRCODE = '23514';
    END IF;
    IF NEW.envelope_version = 1 AND (entry.recovery_for_entry_id IS NOT NULL
        OR entry.sdk_client_message_id IS DISTINCT FROM entry.client_operation_id::text) THEN
        RAISE EXCEPTION 'Legacy envelopes cannot claim v2 SDK routing' USING ERRCODE = '23514';
    END IF;
    IF NEW.envelope_version = 2 AND entry.recovery_for_entry_id IS NULL
        AND (entry.sdk_client_message_id IS NULL OR
            entry.sdk_client_message_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$') THEN
        RAISE EXCEPTION 'New application SDK IDs must be UUIDv4' USING ERRCODE = '23514';
    END IF;
    IF NEW.sdk_message_type = 'retry_request' THEN
        IF entry.kind <> 'protocol_control' OR entry.recipient_id IS DISTINCT FROM expected_recipient
            OR NEW.sender_key_version_id IS NOT NULL OR NEW.recipient_key_version_id IS NOT NULL
            OR (NEW.envelope_version = 2 AND entry.recovery_kind IS DISTINCT FROM 'retry-request') THEN
            RAISE EXCEPTION 'Retry controls require recipient-only routing and no key references' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    IF entry.recovery_kind = 'null' THEN
        IF NEW.envelope_version <> 2 OR entry.kind <> 'protocol_control'
            OR NEW.sender_key_version_id IS NOT NULL OR NEW.recipient_key_version_id IS NOT NULL THEN
            RAISE EXCEPTION 'SDK null responses have no application key context' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    IF entry.kind = 'protocol_control' THEN
        SELECT * INTO original_payload FROM conversations.encrypted_payloads WHERE entry_id = entry.recovery_for_entry_id;
        IF NEW.envelope_version <> 2 OR entry.recovery_kind IS DISTINCT FROM 'resend'
            OR original_payload.entry_id IS NULL
            OR ROW(NEW.client_timestamp_ms, NEW.sender_key_version_id, NEW.recipient_key_version_id)
                IS DISTINCT FROM ROW(original_payload.client_timestamp_ms,
                    original_payload.sender_key_version_id, original_payload.recipient_key_version_id) THEN
            RAISE EXCEPTION 'Resends require the original application routing context' USING ERRCODE = '23514';
        END IF;
    ELSIF NEW.sdk_message_type = 'prekey_bundle' AND entry.kind <> 'message' THEN
        RAISE EXCEPTION 'SDK message type is incompatible with its entry kind' USING ERRCODE = '23514';
    END IF;
    IF entry.recovery_kind = 'retry-request' THEN
        RAISE EXCEPTION 'Retry requests must use their SDK control type' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO sender_key FROM conversations.public_key_versions WHERE id = NEW.sender_key_version_id;
    SELECT * INTO recipient_key FROM conversations.public_key_versions WHERE id = NEW.recipient_key_version_id;
    IF sender_key.id IS NULL OR recipient_key.id IS NULL OR sender_key.user_id <> entry.sender_id
        OR recipient_key.user_id <> expected_recipient OR sender_key.protocol_id <> NEW.protocol_id
        OR recipient_key.protocol_id <> NEW.protocol_id THEN
        RAISE EXCEPTION 'Envelope key owners and protocol must match the entry participants' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON TABLE conversations.recovery_families IS
    'Content-free immutable requester/family/original bindings; first request commits atomically.';
COMMENT ON COLUMN conversations.entries.sdk_client_message_id IS
    'Exact SDK ID, distinct from UUID API operation identity; retained to prevent replay after purge.';
COMMENT ON COLUMN conversations.entries.recovery_for_entry_id IS
    'Original chat marker, never another transport attempt; payload retention and membership still apply.';
COMMENT ON COLUMN conversations.entries.recipient_id IS
    'Other participant for all protocol controls, including SDK retry requests, encrypted resends and null responses.';

-- migrate:down
-- Local/test only. Do not discard v2 payloads, correlations or durable guards.
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
LOCK TABLE conversations.entries, conversations.encrypted_payloads, conversations.recovery_families
    IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM conversations.recovery_families)
        OR EXISTS (SELECT 1 FROM conversations.encrypted_payloads WHERE envelope_version = 2)
        OR EXISTS (SELECT 1 FROM conversations.entries WHERE recovery_for_entry_id IS NOT NULL
            OR (sdk_client_message_id IS NOT NULL AND sdk_client_message_id <> client_operation_id::text)) THEN
        RAISE EXCEPTION 'Refuse rollback with recovery or v2 state';
    END IF;
END $$;
DROP TRIGGER entry_recovery ON conversations.entries;
DROP FUNCTION conversations.guard_recovery_entry();
ALTER TABLE conversations.entries DROP CONSTRAINT entries_recovery_family_fk;
DROP TABLE conversations.recovery_families;
DROP FUNCTION conversations.check_recovery_first_request();
DROP FUNCTION conversations.guard_recovery_family();
ALTER TABLE conversations.entries
    DROP COLUMN sdk_client_message_id,
    DROP COLUMN recovery_for_entry_id,
    DROP COLUMN recovery_requester_id,
    DROP COLUMN recovery_family_id,
    DROP COLUMN recovery_attempt,
    DROP COLUMN recovery_kind;
ALTER TABLE conversations.encrypted_payloads DROP CONSTRAINT retry_payload_key_pair;
ALTER TABLE conversations.encrypted_payloads ADD CONSTRAINT retry_payload_key_pair CHECK (
    (sdk_message_type = 'retry_request' AND sender_key_version_id IS NULL AND recipient_key_version_id IS NULL)
    OR (sdk_message_type <> 'retry_request' AND sender_key_version_id IS NOT NULL
        AND recipient_key_version_id IS NOT NULL AND sender_key_version_id <> recipient_key_version_id));
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
        OR NEW.protocol_id <> 'open-e2ee-signal' OR NEW.protocol_version <> '13.0.0' OR NEW.envelope_version <> 1 THEN
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
        IF entry.kind = 'protocol_control' OR (NEW.sdk_message_type = 'prekey_bundle' AND entry.kind <> 'message') THEN
            RAISE EXCEPTION 'SDK message type is incompatible with its entry kind' USING ERRCODE = '23514';
        END IF;
        SELECT * INTO sender_key FROM conversations.public_key_versions WHERE id = NEW.sender_key_version_id;
        SELECT * INTO recipient_key FROM conversations.public_key_versions WHERE id = NEW.recipient_key_version_id;
        expected_recipient := CASE WHEN entry.sender_id = thread.initiator_id
            THEN thread.counterparty_id ELSE thread.initiator_id END;
        IF sender_key.id IS NULL OR recipient_key.id IS NULL OR sender_key.user_id <> entry.sender_id
            OR recipient_key.user_id <> expected_recipient OR sender_key.protocol_id <> NEW.protocol_id
            OR recipient_key.protocol_id <> NEW.protocol_id THEN
            RAISE EXCEPTION 'Envelope key owners and protocol must match the entry participants' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
COMMENT ON COLUMN conversations.entries.recipient_id IS
    'Set only for retry_request protocol controls; retrieval returns those entries only to this thread member.';
