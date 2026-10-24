-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
ALTER TABLE identity.sessions ADD COLUMN last_seen_at timestamptz(6),
    ADD CONSTRAINT sessions_last_seen_time CHECK (last_seen_at IS NULL OR last_seen_at BETWEEN created_at AND expires_at),
    ADD CONSTRAINT sessions_bound_state CHECK (last_seen_at IS NULL OR
        (octet_length(token_digest)=32 AND expires_at-created_at<=INTERVAL '7 days'));
CREATE TABLE identity.password_login_windows (
    key_version text NOT NULL REFERENCES identity.otp_key_binding(key_version),
    target_digest bytea NOT NULL CHECK (octet_length(target_digest)=32),
    expires_at timestamptz(6) NOT NULL,
    failures integer NOT NULL CHECK (failures BETWEEN 0 AND 5),
    PRIMARY KEY(key_version,target_digest)
);
CREATE TABLE identity.auth_source_events (
    id uuid PRIMARY KEY,
    source_digest bytea NOT NULL CHECK (octet_length(source_digest)=32),
    created_at timestamptz(6) NOT NULL
);
CREATE INDEX auth_source_window ON identity.auth_source_events(source_digest,created_at DESC);
CREATE TABLE identity.microsoft_login_attempts (
    token_digest bytea PRIMARY KEY CHECK (octet_length(token_digest)=32),
    created_at timestamptz(6) NOT NULL,
    expires_at timestamptz(6) NOT NULL,
    consumed_at timestamptz(6),
    CHECK (expires_at-created_at=INTERVAL '10 minutes'),
    CHECK (consumed_at IS NULL OR consumed_at BETWEEN created_at AND expires_at)
);
-- migrate:down
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
LOCK TABLE identity.sessions,identity.password_login_windows,identity.auth_source_events,
    identity.microsoft_login_attempts IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
    IF EXISTS(SELECT 1 FROM identity.sessions WHERE last_seen_at IS NOT NULL)
       OR EXISTS(SELECT 1 FROM identity.password_login_windows)
       OR EXISTS(SELECT 1 FROM identity.auth_source_events)
       OR EXISTS(SELECT 1 FROM identity.microsoft_login_attempts) THEN
        RAISE EXCEPTION 'Identity session rollback requires reviewed security-state migration' USING ERRCODE='23514';
    END IF;
END $$;
DROP TABLE identity.microsoft_login_attempts;
DROP TABLE identity.auth_source_events;
DROP TABLE identity.password_login_windows;
ALTER TABLE identity.sessions DROP CONSTRAINT sessions_last_seen_time,DROP CONSTRAINT sessions_bound_state,DROP COLUMN last_seen_at;
