-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- OpenE2EE's first encrypted application send is a prekey_bundle. Like a
-- ciphertext envelope, it contains encrypted application content; it is not a
-- retry/recovery control. Allow it for contact shares so the first user action
-- in a new conversation can still be an encrypted contact share.
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
    ELSIF NEW.sdk_message_type = 'prekey_bundle' AND entry.kind NOT IN ('message', 'contact_share') THEN
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

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

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
