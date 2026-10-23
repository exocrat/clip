-- Check all seeded Identity data without printing identifiers/contact values.
DO $$
BEGIN
    IF left(current_database(), 10) <> 'clip_test_' THEN
        RAISE EXCEPTION 'Identity upgrade check requires a disposable test database';
    END IF;
    IF (SELECT count(*) FROM identity.users) <> 2
        OR NOT EXISTS (SELECT 1 FROM identity.users
            WHERE id = 'e2300000-0000-4000-8000-000000000001'
            AND account_class = 'regular' AND status = 'active'
            AND display_name = 'Identity upgrade fixture' AND revision = 1
            AND created_at = '2026-01-01 00:00:00+00'::timestamptz
            AND activated_at IS NULL AND expires_at IS NULL AND revoked_at IS NULL)
        OR NOT EXISTS (SELECT 1 FROM identity.users
            WHERE id = 'e2300000-0000-4000-8000-000000000002'
            AND account_class = 'temporary' AND status = 'active'
            AND display_name IS NULL AND revision = 1
            AND created_at = '2026-01-01 00:00:00+00'::timestamptz
            AND activated_at = '2026-01-01 00:00:00+00'::timestamptz
            AND expires_at = '2026-01-15 00:00:00+00'::timestamptz
            AND revoked_at IS NULL)
        OR (SELECT count(*) FROM identity.external_identities) <> 1
        OR NOT EXISTS (SELECT 1 FROM identity.external_identities
            WHERE id = 'e2300000-0000-4000-8000-000000000003'
            AND user_id = 'e2300000-0000-4000-8000-000000000001'
            AND provider = 'synthetic' AND issuer = 'https://issuer.example.invalid'
            AND subject = 'synthetic-upgrade-subject'
            AND created_at = '2026-01-01 00:00:00+00'::timestamptz)
        OR (SELECT count(*) FROM identity.contacts) <> 1
        OR NOT EXISTS (SELECT 1 FROM identity.contacts
            WHERE user_id = 'e2300000-0000-4000-8000-000000000001'
            AND email = 'upgrade@example.invalid' AND phone IS NULL AND upi_id IS NULL
            AND updated_at = '2026-01-01 00:00:00+00'::timestamptz) THEN
        RAISE EXCEPTION 'Identity migration changed or lost pre-existing fixture data';
    END IF;
END;
$$;
