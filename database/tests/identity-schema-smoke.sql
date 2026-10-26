-- Identity storage checks only: no real token/password/OTP/provider behavior.
-- All fixture writes and temporary helpers are rolled back, including failures.
BEGIN;
DO $$
BEGIN
    IF left(current_database(), 10) <> 'clip_test_' THEN
        RAISE EXCEPTION 'Identity smoke requires an explicitly disposable database';
    END IF;
END;
$$;
CREATE TEMP TABLE identity_smoke_scope (marker boolean) ON COMMIT DROP;
-- Only fixed synthetic statements from this file reach this negative-test helper.
-- Compare SQLSTATE without emitting statement/private payload on unexpected errors.
CREATE FUNCTION pg_temp.expect_identity_rejection(command text, expected_state text DEFAULT '23514')
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE command;
    EXCEPTION WHEN OTHERS THEN
        IF SQLSTATE = expected_state THEN RETURN; END IF;
        RAISE EXCEPTION 'Unexpected SQLSTATE in Identity negative check: %', SQLSTATE;
    END;
    RAISE EXCEPTION 'Identity storage accepted an invalid fixture';
END;
$$;

DO $$
DECLARE
    regular_id uuid := gen_random_uuid();
    other_id uuid := gen_random_uuid();
    temporary_id uuid := gen_random_uuid();
    mapping_id uuid := gen_random_uuid();
    enrollment_id uuid := gen_random_uuid();
    column_name text;
    mutation text;
BEGIN
    INSERT INTO identity.users (id, account_class, status, display_name, created_at)
    VALUES (regular_id, 'regular', 'active', repeat('界', 80), '2026-01-01 00:00:00+00'),
        (other_id, 'regular', 'pending', NULL, '2026-01-01 00:00:00+00');
    INSERT INTO identity.users
        (id, account_class, status, created_at, activated_at, expires_at)
    VALUES (temporary_id, 'temporary', 'active', '2026-01-01 00:00:00+00',
        '2026-01-01 05:30:00+05:30', '2026-01-15 05:30:00+05:30');
    -- Count Unicode code points, not bytes; preserve the contract's null/empty cases.
    UPDATE identity.users SET display_name = '' WHERE id = regular_id;
    UPDATE identity.users SET display_name = NULL WHERE id = regular_id;
    UPDATE identity.users SET display_name = repeat('界', 80) WHERE id = regular_id;
    PERFORM pg_temp.expect_identity_rejection(format(
        'UPDATE identity.users SET display_name = repeat(''x'', 81) WHERE id = %L', regular_id));
    PERFORM pg_temp.expect_identity_rejection(
        'INSERT INTO identity.users (id, account_class, status, display_name) VALUES (gen_random_uuid(), ''regular'', ''active'', repeat(''x'', 81))');

    INSERT INTO identity.contacts (user_id, email, phone, upi_id)
    VALUES (regular_id, repeat('界', 254), repeat('x', 254), repeat('y', 254));
    FOREACH column_name IN ARRAY ARRAY['email', 'phone', 'upi_id'] LOOP
        PERFORM pg_temp.expect_identity_rejection(format(
            'UPDATE identity.contacts SET %I = repeat(''x'', 255) WHERE user_id = %L', column_name, regular_id));
        -- Original nonempty checks still apply; API format rules remain Step9.
        PERFORM pg_temp.expect_identity_rejection(format(
            'UPDATE identity.contacts SET %I = '''' WHERE user_id = %L', column_name, regular_id));
    END LOOP;
    UPDATE identity.contacts SET email = NULL, phone = NULL, upi_id = NULL WHERE user_id = regular_id;

    -- A revocation records an aware event at/after creation, paired with status.
    UPDATE identity.users SET status = 'revoked', revoked_at = '2026-01-01 00:00:00+00' WHERE id = regular_id;
    PERFORM pg_temp.expect_identity_rejection(format(
        'UPDATE identity.users SET revoked_at = NULL WHERE id = %L', regular_id));
    PERFORM pg_temp.expect_identity_rejection(format(
        'UPDATE identity.users SET status = ''active'' WHERE id = %L', regular_id));
    PERFORM pg_temp.expect_identity_rejection(format(
        'UPDATE identity.users SET revoked_at = ''2025-12-31 23:59:59+00'' WHERE id = %L', regular_id));
    PERFORM pg_temp.expect_identity_rejection(format(
        'UPDATE identity.users SET status = ''revoked'' WHERE id = %L', other_id));
    PERFORM pg_temp.expect_identity_rejection(format(
        'UPDATE identity.users SET revoked_at = ''2026-01-01 01:00:00+00'' WHERE id = %L', other_id));

    INSERT INTO identity.external_identities (id, user_id, provider, issuer, subject, created_at)
    VALUES (mapping_id, other_id, 'synthetic', 'https://issuer.example.invalid',
        'synthetic-subject', '2026-01-01 00:00:00+00');
    UPDATE identity.external_identities SET subject = subject WHERE id = mapping_id;
    FOREACH mutation IN ARRAY ARRAY[
        'id = gen_random_uuid()',
        format('user_id = %L', regular_id),
        'provider = ''other''',
        'issuer = ''https://other.example.invalid''',
        'subject = ''other-subject''',
        'created_at = created_at + INTERVAL ''1 second'''
    ] LOOP
        PERFORM pg_temp.expect_identity_rejection(format(
            'UPDATE identity.external_identities SET %s WHERE id = %L', mutation, mapping_id));
    END LOOP;
    PERFORM pg_temp.expect_identity_rejection(format(
        'INSERT INTO identity.external_identities (id, user_id, provider, issuer, subject) VALUES (gen_random_uuid(), %L, ''synthetic'', ''https://issuer.example.invalid'', ''synthetic-subject'')', regular_id), '23505');
    PERFORM pg_temp.expect_identity_rejection(
        'INSERT INTO identity.external_identities (id, user_id, provider, issuer, subject) VALUES (gen_random_uuid(), gen_random_uuid(), ''synthetic'', ''https://issuer.example.invalid'', ''missing-parent'')', '23503');

    -- Original activation/lifetime/enrollment protections must survive migration.
    PERFORM pg_temp.expect_identity_rejection(format(
        'UPDATE identity.users SET expires_at = expires_at + INTERVAL ''1 hour'' WHERE id = %L', temporary_id));
    PERFORM pg_temp.expect_identity_rejection(format(
        'UPDATE identity.users SET activated_at = activated_at + INTERVAL ''1 day'', expires_at = expires_at + INTERVAL ''1 day'' WHERE id = %L', temporary_id));
    PERFORM pg_temp.expect_identity_rejection(format(
        'UPDATE identity.users SET account_class = ''regular'' WHERE id = %L', temporary_id));
    INSERT INTO identity.temporary_enrollments
        (id, login_digest, digest_key_version, first_activated_at, original_expires_at, user_id)
    VALUES (enrollment_id, decode('01', 'hex'), 'synthetic-key', '2026-01-01 00:00:00+00',
        '2026-01-15 00:00:00+00', temporary_id);
    PERFORM pg_temp.expect_identity_rejection(format(
        'DELETE FROM identity.temporary_enrollments WHERE id = %L', enrollment_id));
    IF (SELECT expires_at - activated_at FROM identity.users WHERE id = temporary_id) <> INTERVAL '336 hours'
        OR EXISTS (SELECT 1 FROM information_schema.columns AS fields
            WHERE fields.table_schema = 'identity'
            AND fields.column_name IN ('created_at', 'activated_at', 'expires_at', 'revoked_at',
                'profile_removed_at', 'updated_at', 'password_changed_at', 'consumed_at',
                'last_sent_at', 'first_activated_at', 'original_expires_at')
            AND fields.data_type <> 'timestamp with time zone') THEN
        RAISE EXCEPTION 'Identity lifetime or aware timestamp representation changed';
    END IF;
END;
$$;
ROLLBACK;
