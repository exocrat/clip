-- Persistent synthetic rows only in the runner's NEW disposable database.
-- Retain these across upgrade/down/reapply to detect data rewrites or loss.
DO $$
BEGIN
    IF left(current_database(), 10) <> 'clip_test_' THEN
        RAISE EXCEPTION 'Identity upgrade fixture requires a disposable test database';
    END IF;
END;
$$;
INSERT INTO identity.users
    (id, account_class, status, display_name, created_at, activated_at, expires_at)
VALUES
    ('e2300000-0000-4000-8000-000000000001', 'regular', 'active', 'Identity upgrade fixture',
        '2026-01-01 00:00:00+00', NULL, NULL),
    ('e2300000-0000-4000-8000-000000000002', 'temporary', 'active', NULL,
        '2026-01-01 00:00:00+00', '2026-01-01 00:00:00+00', '2026-01-15 00:00:00+00');
INSERT INTO identity.external_identities
    (id, user_id, provider, issuer, subject, created_at)
VALUES ('e2300000-0000-4000-8000-000000000003', 'e2300000-0000-4000-8000-000000000001',
    'synthetic', 'https://issuer.example.invalid', 'synthetic-upgrade-subject',
    '2026-01-01 00:00:00+00');
INSERT INTO identity.contacts (user_id, email, updated_at)
VALUES ('e2300000-0000-4000-8000-000000000001', 'upgrade@example.invalid', '2026-01-01 00:00:00+00');
