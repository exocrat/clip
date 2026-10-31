-- migrate:up
-- Legacy names remain stored. Only valid unambiguous names are claimed; all other
-- members choose a Handle at next setup without changing any account reference.
ALTER TABLE identity.users ADD COLUMN handle_ready boolean NOT NULL DEFAULT false;
UPDATE identity.users u SET handle_ready = true
WHERE display_name ~ '^[A-Za-z0-9_]{3,30}$'
  AND profile_removed_at IS NULL
  AND NOT EXISTS (SELECT 1 FROM identity.users other
      WHERE other.id <> u.id AND lower(other.display_name) = lower(u.display_name));
ALTER TABLE identity.users ADD CONSTRAINT users_claimed_handle_valid
    CHECK (NOT handle_ready OR display_name ~ '^[A-Za-z0-9_]{3,30}$' AND display_name IS NOT NULL);
CREATE UNIQUE INDEX users_claimed_handle_unique ON identity.users(lower(display_name))
    WHERE handle_ready AND profile_removed_at IS NULL;
-- Identity-owned public projection: no email/contact/provider data is exposed.
CREATE VIEW identity.participant_profiles AS
SELECT id AS user_id,
    CASE WHEN handle_ready AND profile_removed_at IS NULL AND status = 'active'
         THEN display_name ELSE NULL END AS handle,
    CASE WHEN profile_removed_at IS NULL AND status = 'active'
         THEN account_class ELSE NULL END AS account_class
FROM identity.users;

-- migrate:down
DROP VIEW identity.participant_profiles;
DROP INDEX identity.users_claimed_handle_unique;
ALTER TABLE identity.users DROP CONSTRAINT users_claimed_handle_valid, DROP COLUMN handle_ready;
