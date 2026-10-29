-- Identity retains only encrypted login destinations for notification delivery.
-- migrate:up
CREATE TABLE identity.notification_destinations (
    user_id uuid PRIMARY KEY REFERENCES identity.users ON DELETE RESTRICT,
    ciphertext bytea NOT NULL CHECK (octet_length(ciphertext) >= 29),
    key_version text NOT NULL CHECK (key_version <> ''),
    updated_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE identity.notification_destinations IS
    'Identity-owned encrypted login addresses; no plaintext recipient in Conversations.';

-- migrate:down
DROP TABLE identity.notification_destinations;
