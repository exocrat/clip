-- migrate:up
-- Cooperating migration transactions share a CLIP advisory key. dbmate 2.36
-- has no global migration-lock flag; one operator still serializes CLI runs.
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- Provisional PD-08 baseline: Mohit approved the schema/product choices and
-- explicitly permitted implementation before affected-owner review. This DDL
-- supplies storage integrity, never authentication, crypto or domain APIs.
-- Fail rather than adopting an existing domain namespace or unrelated tables.
CREATE SCHEMA identity;
CREATE SCHEMA listings;
CREATE SCHEMA search;
CREATE SCHEMA conversations;

-- Identity owns lifecycle, private contacts and local temporary credentials.
CREATE TABLE identity.users (
    id uuid PRIMARY KEY,
    account_class text NOT NULL CHECK (account_class IN ('regular', 'temporary')),
    status text NOT NULL CHECK (status IN ('pending', 'active', 'revoked')),
    display_name text,
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activated_at timestamptz(6),
    expires_at timestamptz(6),
    revoked_at timestamptz(6),
    profile_removed_at timestamptz(6),
    revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
    CONSTRAINT user_temporary_lifetime CHECK (
        (account_class = 'regular' AND expires_at IS NULL)
        OR (account_class = 'temporary' AND (
            (activated_at IS NULL AND expires_at IS NULL AND status <> 'active')
            OR (activated_at IS NOT NULL AND expires_at IS NOT NULL
                AND expires_at - activated_at = INTERVAL '336 hours')
        ))
    ),
    CONSTRAINT user_activation_time CHECK (activated_at IS NULL OR activated_at >= created_at),
    CONSTRAINT user_profile_removal CHECK (
        profile_removed_at IS NULL OR (display_name IS NULL AND (
            status = 'revoked' OR (account_class = 'temporary'
                AND expires_at IS NOT NULL AND profile_removed_at >= expires_at)
        ))
    )
);
CREATE INDEX users_temporary_expiry ON identity.users (expires_at)
    WHERE account_class = 'temporary';

CREATE TABLE identity.external_identities (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    provider text NOT NULL CHECK (provider <> ''),
    issuer text NOT NULL CHECK (issuer <> ''),
    subject text NOT NULL CHECK (subject <> ''),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (provider, issuer, subject)
);
CREATE INDEX external_identities_user ON identity.external_identities (user_id);

CREATE TABLE identity.contacts (
    user_id uuid PRIMARY KEY REFERENCES identity.users ON DELETE RESTRICT,
    email text CHECK (email IS NULL OR email <> ''),
    phone text CHECK (phone IS NULL OR phone <> ''),
    upi_id text CHECK (upi_id IS NULL OR upi_id <> ''),
    updated_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE identity.temporary_credentials (
    user_id uuid PRIMARY KEY REFERENCES identity.users ON DELETE RESTRICT,
    login_email_key text NOT NULL UNIQUE CHECK (login_email_key <> ''),
    password_hash text NOT NULL CHECK (password_hash <> ''),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    password_changed_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
    CHECK (password_changed_at >= created_at)
);

CREATE TABLE identity.sessions (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    token_digest bytea NOT NULL UNIQUE CHECK (octet_length(token_digest) > 0),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at timestamptz(6) NOT NULL,
    revoked_at timestamptz(6),
    CHECK (expires_at > created_at),
    CHECK (revoked_at IS NULL OR revoked_at >= created_at)
);
CREATE INDEX sessions_user_revocation ON identity.sessions (user_id, revoked_at);
CREATE INDEX sessions_expiry ON identity.sessions (expires_at);

CREATE TABLE identity.otp_challenges (
    id uuid PRIMARY KEY,
    user_id uuid REFERENCES identity.users ON DELETE RESTRICT,
    target_lookup_digest bytea NOT NULL CHECK (octet_length(target_lookup_digest) > 0),
    verifier bytea NOT NULL CHECK (octet_length(verifier) > 0),
    purpose text NOT NULL CHECK (purpose IN ('initial_verification', 'password_reset')),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at timestamptz(6) NOT NULL,
    consumed_at timestamptz(6),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    resend_count integer NOT NULL DEFAULT 0 CHECK (resend_count >= 0),
    last_sent_at timestamptz(6),
    CHECK (expires_at > created_at),
    CHECK (consumed_at IS NULL OR consumed_at BETWEEN created_at AND expires_at),
    CHECK (last_sent_at IS NULL OR last_sent_at >= created_at),
    CHECK (purpose <> 'password_reset' OR user_id IS NOT NULL)
);
CREATE INDEX otp_target_purpose ON identity.otp_challenges
    (target_lookup_digest, purpose, created_at DESC);
CREATE INDEX otp_expiry ON identity.otp_challenges (expires_at);
CREATE INDEX otp_user ON identity.otp_challenges (user_id);

-- This digest is an opaque, sensitive enrollment guard, not a raw email or
-- credential. ID-01 must supply reviewed normalization/key rotation semantics.
CREATE TABLE identity.temporary_enrollments (
    id uuid PRIMARY KEY,
    login_digest bytea NOT NULL CHECK (octet_length(login_digest) > 0),
    digest_key_version text NOT NULL CHECK (digest_key_version <> ''),
    first_activated_at timestamptz(6) NOT NULL,
    original_expires_at timestamptz(6) NOT NULL,
    user_id uuid UNIQUE REFERENCES identity.users ON DELETE SET NULL,
    UNIQUE (digest_key_version, login_digest),
    CHECK (original_expires_at - first_activated_at = INTERVAL '336 hours')
);
COMMENT ON TABLE identity.temporary_enrollments IS
    'Per-key uniqueness only: Identity must serialize normalized enrollment and check retained key versions; this table alone does not prove cross-key non-renewal.';

-- Listings owns catalogues and authoritative item/image/selection state.
CREATE TABLE listings.categories (
    id uuid PRIMARY KEY,
    code text NOT NULL UNIQUE CHECK (code <> ''),
    label text NOT NULL CHECK (label <> ''),
    sensitive_category boolean NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE listings.conditions (
    code text PRIMARY KEY CHECK (code <> ''),
    label text NOT NULL CHECK (label <> ''),
    active boolean NOT NULL DEFAULT true
);

-- Nullable physical content permits only a trusted retired-row state. Live
-- rows still require price, negotiability and all FR-04 text/catalogue fields.
CREATE TABLE listings.sale_listings (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    title text CHECK (title IS NULL OR (char_length(title) BETWEEN 1 AND 120
        AND title ~ '[^[:space:]]')),
    description text CHECK (description IS NULL OR (char_length(description) BETWEEN 1 AND 5000
        AND description ~ '[^[:space:]]')),
    category_id uuid REFERENCES listings.categories ON DELETE RESTRICT,
    condition_code text REFERENCES listings.conditions ON DELETE RESTRICT,
    asking_price_paise bigint CHECK (asking_price_paise >= 0 AND asking_price_paise % 100 = 0),
    negotiable boolean,
    pickup_area text CHECK (pickup_area IS NULL OR (char_length(pickup_area) BETWEEN 1 AND 120
        AND pickup_area ~ '[^[:space:]]')),
    available_from timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    available_until timestamptz(6),
    availability text NOT NULL CHECK (availability IN ('available', 'unavailable')),
    proof_available boolean,
    selected_buyer_id uuid REFERENCES identity.users ON DELETE RESTRICT,
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    retirement_eligible_since timestamptz(6),
    retired_at timestamptz(6),
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('pg_catalog.english'::regconfig,
            coalesce(title, '') || ' ' || coalesce(description, ''))
    ) STORED,
    revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
    CHECK (available_until IS NULL OR available_until > available_from),
    CHECK (selected_buyer_id IS NULL OR selected_buyer_id <> owner_id),
    CONSTRAINT listing_live_or_retired CHECK (
        (retired_at IS NULL AND title IS NOT NULL AND description IS NOT NULL
            AND category_id IS NOT NULL AND condition_code IS NOT NULL
            AND asking_price_paise IS NOT NULL AND negotiable IS NOT NULL
            AND pickup_area IS NOT NULL)
        OR (retired_at IS NOT NULL AND availability = 'unavailable'
            AND title IS NULL AND description IS NULL AND category_id IS NULL
            AND condition_code IS NULL AND asking_price_paise IS NULL
            AND negotiable IS NULL AND pickup_area IS NULL
            AND proof_available IS NULL AND selected_buyer_id IS NULL)
    )
);
CREATE INDEX sale_owner ON listings.sale_listings (owner_id, created_at DESC, id DESC);
CREATE INDEX sale_recency ON listings.sale_listings (availability, created_at DESC, id DESC)
    WHERE retired_at IS NULL;
CREATE INDEX sale_price ON listings.sale_listings (availability, asking_price_paise, id)
    WHERE retired_at IS NULL;
CREATE INDEX sale_category ON listings.sale_listings (category_id);
CREATE INDEX sale_condition ON listings.sale_listings (condition_code);
CREATE INDEX sale_selected_buyer ON listings.sale_listings (selected_buyer_id);
CREATE INDEX sale_retirement ON listings.sale_listings (retirement_eligible_since)
    WHERE retired_at IS NULL;
CREATE INDEX sale_full_text ON listings.sale_listings USING gin (search_vector);

CREATE TABLE listings.image_uploads (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    object_key text NOT NULL UNIQUE CHECK (object_key <> ''),
    state text NOT NULL CHECK (state IN ('pending', 'confirmed', 'failed', 'expired')),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at timestamptz(6) NOT NULL,
    confirmed_at timestamptz(6),
    failure_code text,
    CHECK (expires_at - created_at = INTERVAL '24 hours'),
    CHECK ((state = 'confirmed') = (confirmed_at IS NOT NULL)),
    CHECK (confirmed_at IS NULL OR confirmed_at BETWEEN created_at AND expires_at),
    CHECK (failure_code IS NULL OR failure_code ~ '^[a-z][a-z0-9_]{0,63}$')
);
CREATE INDEX uploads_owner_state ON listings.image_uploads (owner_id, state);
CREATE INDEX uploads_expiry ON listings.image_uploads (state, expires_at);

CREATE TABLE listings.images (
    id uuid PRIMARY KEY,
    listing_id uuid NOT NULL REFERENCES listings.sale_listings ON DELETE RESTRICT,
    upload_id uuid NOT NULL UNIQUE REFERENCES listings.image_uploads ON DELETE RESTRICT,
    object_key text NOT NULL UNIQUE CHECK (object_key <> ''),
    position integer NOT NULL CHECK (position >= 0),
    media_type text NOT NULL CHECK (media_type IN ('image/jpeg', 'image/png', 'image/webp')),
    size_bytes bigint NOT NULL CHECK (size_bytes BETWEEN 1 AND 10485760),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    retired_at timestamptz(6)
);
CREATE INDEX images_listing ON listings.images (listing_id);
CREATE UNIQUE INDEX images_live_position ON listings.images (listing_id, position)
    WHERE retired_at IS NULL;

-- Search owns wanted requests and private saved references, not listing writes.
CREATE TABLE search.wanted_requests (
    id uuid PRIMARY KEY,
    author_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    title text CHECK (title IS NULL OR (char_length(title) BETWEEN 1 AND 120
        AND title ~ '[^[:space:]]')),
    description text CHECK (description IS NULL OR (char_length(description) BETWEEN 1 AND 5000
        AND description ~ '[^[:space:]]')),
    category_id uuid REFERENCES listings.categories ON DELETE RESTRICT,
    budget_paise bigint CHECK (budget_paise >= 0 AND budget_paise % 100 = 0),
    status text NOT NULL CHECK (status IN ('open', 'unavailable')),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at timestamptz(6),
    retired_at timestamptz(6),
    revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
    CHECK ((status = 'open' AND closed_at IS NULL)
        OR (status = 'unavailable' AND closed_at IS NOT NULL)),
    CONSTRAINT request_live_or_retired CHECK (
        (retired_at IS NULL AND title IS NOT NULL AND description IS NOT NULL AND category_id IS NOT NULL)
        OR (retired_at IS NOT NULL AND status = 'unavailable' AND title IS NULL
            AND description IS NULL AND category_id IS NULL AND budget_paise IS NULL)
    )
);
CREATE INDEX wanted_recency ON search.wanted_requests (status, created_at DESC, id DESC)
    WHERE retired_at IS NULL;
CREATE INDEX wanted_author ON search.wanted_requests (author_id, created_at DESC, id DESC);
CREATE INDEX wanted_category ON search.wanted_requests (category_id);
CREATE INDEX wanted_closure ON search.wanted_requests (closed_at) WHERE retired_at IS NULL;
CREATE TABLE search.saved_listings (
    user_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    listing_id uuid NOT NULL REFERENCES listings.sale_listings ON DELETE RESTRICT,
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, listing_id)
);
CREATE INDEX saves_recency ON search.saved_listings (user_id, created_at DESC, listing_id DESC);
CREATE INDEX saves_listing ON search.saved_listings (listing_id);

-- Conversations owns private origins, participant read state and opaque
-- encrypted content. These relations confer no client authorization.
CREATE TABLE conversations.threads (
    id uuid PRIMARY KEY,
    listing_id uuid REFERENCES listings.sale_listings ON DELETE RESTRICT,
    wanted_request_id uuid REFERENCES search.wanted_requests ON DELETE RESTRICT,
    initiator_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    counterparty_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_activity_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    next_sequence bigint NOT NULL DEFAULT 1 CHECK (next_sequence > 0),
    CHECK ((listing_id IS NOT NULL)::integer + (wanted_request_id IS NOT NULL)::integer = 1),
    CHECK (initiator_id <> counterparty_id),
    CHECK (last_activity_at >= created_at)
);
CREATE UNIQUE INDEX thread_buyer_listing ON conversations.threads (listing_id, initiator_id)
    WHERE listing_id IS NOT NULL;
CREATE UNIQUE INDEX thread_responder_request ON conversations.threads (wanted_request_id, initiator_id)
    WHERE wanted_request_id IS NOT NULL;
CREATE INDEX threads_counterparty ON conversations.threads (counterparty_id, created_at DESC, id);
CREATE INDEX threads_initiator ON conversations.threads (initiator_id, created_at DESC, id);
CREATE INDEX threads_request ON conversations.threads (wanted_request_id);
CREATE INDEX threads_activity ON conversations.threads (last_activity_at);

CREATE TABLE conversations.members (
    conversation_id uuid NOT NULL REFERENCES conversations.threads ON DELETE RESTRICT,
    user_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    last_read_sequence bigint NOT NULL DEFAULT 0 CHECK (last_read_sequence >= 0),
    read_at timestamptz(6),
    joined_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reminder_episode_start_sequence bigint CHECK (reminder_episode_start_sequence > 0),
    reminder_sent_at timestamptz(6),
    PRIMARY KEY (conversation_id, user_id),
    CHECK (reminder_sent_at IS NULL OR reminder_episode_start_sequence IS NOT NULL)
);
CREATE INDEX members_user ON conversations.members (user_id, conversation_id);

CREATE TABLE conversations.public_key_versions (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    version bigint NOT NULL CHECK (version > 0),
    public_key_material bytea NOT NULL CHECK (octet_length(public_key_material) BETWEEN 1 AND 16384),
    protocol_id text NOT NULL CHECK (protocol_id <> ''),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    retired_at timestamptz(6),
    UNIQUE (user_id, version),
    CHECK (retired_at IS NULL OR retired_at >= created_at)
);
CREATE UNIQUE INDEX public_key_active ON conversations.public_key_versions (user_id)
    WHERE retired_at IS NULL;

CREATE TABLE conversations.entries (
    id uuid PRIMARY KEY,
    conversation_id uuid NOT NULL REFERENCES conversations.threads ON DELETE RESTRICT,
    sequence bigint NOT NULL CHECK (sequence > 0),
    sender_id uuid NOT NULL,
    client_operation_id uuid NOT NULL,
    kind text NOT NULL CHECK (kind IN ('message', 'offer', 'contact_share')),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    content_deleted_at timestamptz(6),
    UNIQUE (conversation_id, sequence),
    UNIQUE (conversation_id, sender_id, client_operation_id),
    FOREIGN KEY (conversation_id, sender_id) REFERENCES conversations.members ON DELETE RESTRICT,
    CHECK (content_deleted_at IS NULL OR content_deleted_at >= created_at)
);

CREATE TABLE conversations.encrypted_payloads (
    entry_id uuid PRIMARY KEY REFERENCES conversations.entries ON DELETE RESTRICT,
    protocol_id text NOT NULL CHECK (protocol_id <> ''),
    envelope_version integer NOT NULL CHECK (envelope_version > 0),
    sender_key_version_id uuid NOT NULL REFERENCES conversations.public_key_versions ON DELETE RESTRICT,
    recipient_key_version_id uuid NOT NULL REFERENCES conversations.public_key_versions ON DELETE RESTRICT,
    envelope bytea NOT NULL CHECK (octet_length(envelope) BETWEEN 1 AND 65536),
    CHECK (sender_key_version_id <> recipient_key_version_id)
);
CREATE INDEX payload_sender_key ON conversations.encrypted_payloads (sender_key_version_id);
CREATE INDEX payload_recipient_key ON conversations.encrypted_payloads (recipient_key_version_id);

CREATE TABLE conversations.offers (
    id uuid PRIMARY KEY,
    conversation_id uuid NOT NULL REFERENCES conversations.threads ON DELETE RESTRICT,
    buyer_id uuid NOT NULL,
    current_revision bigint,
    next_revision bigint NOT NULL CHECK (next_revision > 0),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    history_deleted_at timestamptz(6),
    UNIQUE (conversation_id, buyer_id),
    FOREIGN KEY (conversation_id, buyer_id) REFERENCES conversations.members ON DELETE RESTRICT,
    CHECK ((current_revision IS NOT NULL AND current_revision > 0
            AND current_revision < next_revision AND history_deleted_at IS NULL)
        OR (current_revision IS NULL AND history_deleted_at IS NOT NULL)),
    CHECK (history_deleted_at IS NULL OR history_deleted_at >= created_at)
);
CREATE INDEX offers_buyer ON conversations.offers (buyer_id);
CREATE TABLE conversations.offer_revisions (
    offer_id uuid NOT NULL REFERENCES conversations.offers ON DELETE RESTRICT,
    revision bigint NOT NULL CHECK (revision > 0),
    entry_id uuid NOT NULL UNIQUE REFERENCES conversations.entries ON DELETE RESTRICT,
    amount_paise bigint NOT NULL CHECK (amount_paise >= 0 AND amount_paise % 100 = 0),
    status text NOT NULL CHECK (status IN ('submitted', 'withdrawn')),
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (offer_id, revision)
);
-- Deferred only for the deliberate offer/current-revision insertion cycle.
ALTER TABLE conversations.offers ADD CONSTRAINT offers_current_revision
    FOREIGN KEY (id, current_revision) REFERENCES conversations.offer_revisions (offer_id, revision)
    DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE conversations.contact_shares (
    entry_id uuid PRIMARY KEY REFERENCES conversations.entries ON DELETE RESTRICT
);

-- No email address, plaintext, ciphertext or provider response in job records.
CREATE TABLE conversations.notification_intents (
    id uuid PRIMARY KEY,
    conversation_id uuid NOT NULL REFERENCES conversations.threads ON DELETE RESTRICT,
    recipient_id uuid NOT NULL,
    trigger_entry_id uuid REFERENCES conversations.entries ON DELETE RESTRICT,
    event_kind text NOT NULL CHECK (event_kind IN ('new_conversation', 'unread_reminder')),
    deduplication_key text NOT NULL UNIQUE CHECK (deduplication_key <> ''),
    due_at timestamptz(6) NOT NULL,
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending', 'leased', 'sent', 'suppressed', 'failed')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5),
    lease_until timestamptz(6),
    lease_token uuid,
    created_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamptz(6),
    expires_at timestamptz(6) NOT NULL,
    unread_episode_start_sequence bigint,
    unread_through_sequence bigint,
    FOREIGN KEY (conversation_id, recipient_id) REFERENCES conversations.members ON DELETE RESTRICT,
    CHECK (expires_at - due_at = INTERVAL '24 hours'),
    CHECK ((state = 'leased' AND lease_until IS NOT NULL AND lease_token IS NOT NULL)
        OR (state <> 'leased' AND lease_until IS NULL AND lease_token IS NULL)),
    CHECK ((state IN ('sent', 'suppressed', 'failed')) = (completed_at IS NOT NULL)),
    CHECK ((event_kind = 'unread_reminder' AND unread_episode_start_sequence > 0
            AND unread_through_sequence >= unread_episode_start_sequence
            AND unread_episode_start_sequence IS NOT NULL AND unread_through_sequence IS NOT NULL)
        OR (event_kind = 'new_conversation' AND unread_episode_start_sequence IS NULL
            AND unread_through_sequence IS NULL))
);
CREATE INDEX notification_due ON conversations.notification_intents (state, due_at, id);
CREATE INDEX notification_read_lookup ON conversations.notification_intents (conversation_id, recipient_id);
CREATE INDEX notification_trigger ON conversations.notification_intents (trigger_entry_id);
COMMENT ON TABLE conversations.notification_intents IS
    'Durable storage only: CN-01/CN-03 must atomically create intents with source writes, fence leases and recheck live read/recipient state before external dispatch.';

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- Explicit disposable-local rollback only. RESTRICT/no CASCADE intentionally
-- fails if a later migration or unrelated object still depends on this baseline.
DROP TABLE conversations.notification_intents;
DROP TABLE conversations.contact_shares;
ALTER TABLE conversations.offers DROP CONSTRAINT offers_current_revision;
DROP TABLE conversations.offer_revisions;
DROP TABLE conversations.offers;
DROP TABLE conversations.encrypted_payloads;
DROP TABLE conversations.entries;
DROP TABLE conversations.public_key_versions;
DROP TABLE conversations.members;
DROP TABLE conversations.threads;
DROP TABLE search.saved_listings;
DROP TABLE search.wanted_requests;
DROP TABLE listings.images;
DROP TABLE listings.image_uploads;
DROP TABLE listings.sale_listings;
DROP TABLE listings.conditions;
DROP TABLE listings.categories;
DROP TABLE identity.temporary_enrollments;
DROP TABLE identity.otp_challenges;
DROP TABLE identity.sessions;
DROP TABLE identity.temporary_credentials;
DROP TABLE identity.contacts;
DROP TABLE identity.external_identities;
DROP TABLE identity.users;
DROP SCHEMA conversations;
DROP SCHEMA search;
DROP SCHEMA listings;
DROP SCHEMA identity;
