-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Existing revisions lack the original optimistic-concurrency input. Do not
-- infer it from revision-1: a new revision after history purge can expect NULL.
-- New writes opt in; legacy rows remain readable but cannot claim exact replay.
-- Metadata lives with the revision so approved history cleanup removes it too.
ALTER TABLE conversations.offer_revisions
    ADD COLUMN request_recorded boolean NOT NULL DEFAULT false,
    ADD COLUMN request_expected_revision bigint,
    ADD CONSTRAINT offer_request_revision CHECK (
        (NOT request_recorded AND request_expected_revision IS NULL)
        OR (request_recorded
            AND (request_expected_revision IS NULL
                OR (request_expected_revision > 0 AND request_expected_revision = revision - 1))
            AND (status <> 'withdrawn' OR request_expected_revision IS NOT NULL))
    );

COMMENT ON COLUMN conversations.offer_revisions.request_recorded IS
    'Exact-retry input recorded by the CN-02 service; false for legacy/storage fixtures.';
COMMENT ON COLUMN conversations.offer_revisions.request_expected_revision IS
    'Original expected revision, including NULL after retained history was purged; removed with revision history.';

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM conversations.offer_revisions WHERE request_recorded) THEN
        RAISE EXCEPTION 'Rollback refused while recorded offer requests exist';
    END IF;
END;
$$;
ALTER TABLE conversations.offer_revisions
    DROP CONSTRAINT offer_request_revision,
    DROP COLUMN request_expected_revision,
    DROP COLUMN request_recorded;
