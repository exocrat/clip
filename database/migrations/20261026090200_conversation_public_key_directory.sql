-- migrate:up
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- Public material only. Operation results retain reservations so retries never
-- consume a second one-time key, even after the peer changes its active bundle.
CREATE TABLE conversations.public_prekeys (
    bundle_id uuid NOT NULL REFERENCES conversations.public_key_versions ON DELETE RESTRICT,
    key_type text NOT NULL CHECK (key_type IN ('ecPreKey', 'kemOneTimePreKey')),
    key_id numeric NOT NULL CHECK (key_id >= 0 AND key_id = trunc(key_id)),
    material jsonb NOT NULL CHECK (jsonb_typeof(material) = 'object'),
    consumed boolean NOT NULL DEFAULT false,
    PRIMARY KEY (bundle_id, key_type, key_id)
);
CREATE INDEX public_prekeys_available ON conversations.public_prekeys (bundle_id, key_type, key_id)
    WHERE NOT consumed;
CREATE TABLE conversations.key_directory_operations (
    user_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    operation_id uuid NOT NULL,
    request jsonb NOT NULL CHECK (jsonb_typeof(request) = 'object'),
    result jsonb NOT NULL CHECK (jsonb_typeof(result) = 'object'),
    PRIMARY KEY (user_id, operation_id)
);

-- migrate:down
-- Local/test rollback only: never silently erase published keys or retry state.
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
LOCK TABLE conversations.public_prekeys, conversations.key_directory_operations IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM conversations.public_prekeys)
        OR EXISTS (SELECT 1 FROM conversations.key_directory_operations) THEN
        RAISE EXCEPTION 'Refuse rollback with real key-directory state';
    END IF;
END $$;
DROP TABLE conversations.key_directory_operations;
DROP TABLE conversations.public_prekeys;
