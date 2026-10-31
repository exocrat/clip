-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Legacy challenges are preserved but cannot enter the new keyed service.
ALTER TABLE identity.otp_challenges
    ADD COLUMN key_version text,
    ADD COLUMN encrypted_target bytea,
    ADD COLUMN superseded_at timestamptz(6),
    ADD CONSTRAINT otp_protected_fields CHECK (
        (key_version IS NULL AND encrypted_target IS NULL)
        OR (key_version IS NOT NULL AND key_version ~ '^[a-zA-Z0-9_-]{1,32}$'
            AND encrypted_target IS NOT NULL AND octet_length(encrypted_target) >= 31
            AND octet_length(target_lookup_digest) = 32 AND octet_length(verifier) = 32)
    ),
    ADD CONSTRAINT otp_superseded_time CHECK (
        superseded_at IS NULL OR superseded_at >= created_at
    );

-- Commitments detect accidental key replacement; these are not key material.
CREATE TABLE identity.otp_key_binding (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    key_version text NOT NULL UNIQUE CHECK (key_version ~ '^[a-zA-Z0-9_-]{1,32}$'),
    lookup_fingerprint bytea NOT NULL CHECK (octet_length(lookup_fingerprint) = 32),
    verifier_fingerprint bytea NOT NULL CHECK (octet_length(verifier_fingerprint) = 32),
    encryption_fingerprint bytea NOT NULL CHECK (octet_length(encryption_fingerprint) = 32)
);

-- Minimal operation acknowledgement, separated from short-lived private state.
-- Retention horizon is NOT selected here; cleanup requires its reviewed policy.
CREATE TABLE identity.otp_operations (
    request_digest bytea PRIMARY KEY CHECK (octet_length(request_digest) = 32),
    key_version text NOT NULL REFERENCES identity.otp_key_binding (key_version),
    challenge_id uuid NOT NULL UNIQUE,
    expires_at timestamptz(6) NOT NULL
);

-- Includes suppressed/ineligible requests so their public limits match.
CREATE TABLE identity.otp_send_reservations (
    challenge_id uuid PRIMARY KEY,
    key_version text NOT NULL REFERENCES identity.otp_key_binding (key_version),
    target_digest bytea NOT NULL CHECK (octet_length(target_digest) = 32),
    source_digest bytea NOT NULL CHECK (octet_length(source_digest) = 32),
    purpose text NOT NULL CHECK (purpose IN ('initial_verification', 'password_reset')),
    created_at timestamptz(6) NOT NULL,
    expires_at timestamptz(6) NOT NULL,
    CHECK (expires_at - created_at = INTERVAL '10 minutes')
);
CREATE INDEX otp_sends_target ON identity.otp_send_reservations (key_version, target_digest, created_at DESC);
CREATE INDEX otp_sends_source ON identity.otp_send_reservations (key_version, source_digest, created_at DESC);

CREATE TABLE identity.otp_verification_windows (
    key_version text NOT NULL REFERENCES identity.otp_key_binding (key_version),
    target_digest bytea NOT NULL CHECK (octet_length(target_digest) = 32),
    purpose text NOT NULL CHECK (purpose IN ('initial_verification', 'password_reset')),
    latest_challenge_id uuid NOT NULL,
    expires_at timestamptz(6) NOT NULL,
    failures integer NOT NULL DEFAULT 0 CHECK (failures BETWEEN 0 AND 3),
    PRIMARY KEY (key_version, target_digest, purpose)
);

-- migrate:down
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- Exclude service writes between the empty-state check and destructive DDL.
LOCK TABLE identity.otp_key_binding, identity.otp_operations,
    identity.otp_send_reservations, identity.otp_verification_windows,
    identity.otp_challenges IN ACCESS EXCLUSIVE MODE;
-- Forward records contain security/replay state. Never silently discard them.
-- An occupied rollback requires a separately reviewed state migration/reset.
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM identity.otp_operations)
       OR EXISTS (SELECT 1 FROM identity.otp_send_reservations)
       OR EXISTS (SELECT 1 FROM identity.otp_verification_windows)
       OR EXISTS (SELECT 1 FROM identity.otp_key_binding)
       OR EXISTS (SELECT 1 FROM identity.otp_challenges WHERE key_version IS NOT NULL) THEN
        RAISE EXCEPTION 'Identity OTP rollback requires reviewed security-state migration' USING ERRCODE = '23514';
    END IF;
END $$;
DROP TABLE identity.otp_verification_windows;
DROP TABLE identity.otp_send_reservations;
DROP TABLE identity.otp_operations;
DROP TABLE identity.otp_key_binding;
ALTER TABLE identity.otp_challenges
    DROP CONSTRAINT otp_superseded_time,
    DROP CONSTRAINT otp_protected_fields,
    DROP COLUMN superseded_at,
    DROP COLUMN encrypted_target,
    DROP COLUMN key_version;
