-- Storage-only checks; synthetic data and all writes roll back.
BEGIN;
DO $$ BEGIN
    IF left(current_database(), 10) <> 'clip_test_' THEN
        RAISE EXCEPTION 'OTP smoke requires a disposable database';
    END IF;
END $$;
CREATE FUNCTION pg_temp.reject_otp(command text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    BEGIN EXECUTE command;
    EXCEPTION WHEN check_violation THEN RETURN;
    END;
    RAISE EXCEPTION 'OTP negative control unexpectedly accepted';
END $$;
INSERT INTO identity.otp_key_binding(key_version,lookup_fingerprint,verifier_fingerprint,encryption_fingerprint)
VALUES ('synthetic-smoke',decode(repeat('11',32),'hex'),decode(repeat('22',32),'hex'),decode(repeat('33',32),'hex'));
INSERT INTO identity.otp_verification_windows(key_version,target_digest,purpose,latest_challenge_id,expires_at)
VALUES ('synthetic-smoke',decode(repeat('44',32),'hex'),'initial_verification',gen_random_uuid(),CURRENT_TIMESTAMP + INTERVAL '10 minutes');
SELECT pg_temp.reject_otp('UPDATE identity.otp_verification_windows SET failures=4');
SELECT pg_temp.reject_otp('UPDATE identity.otp_verification_windows SET failures=-1');
SELECT pg_temp.reject_otp('UPDATE identity.otp_verification_windows SET target_digest=decode(''00'',''hex'')');
INSERT INTO identity.otp_challenges(id,target_lookup_digest,verifier,purpose,expires_at)
VALUES (gen_random_uuid(),decode('55','hex'),decode('66','hex'),'initial_verification',CURRENT_TIMESTAMP + INTERVAL '10 minutes');
SELECT pg_temp.reject_otp('UPDATE identity.otp_challenges SET encrypted_target=decode(repeat(''77'',64),''hex'')');
SELECT pg_temp.reject_otp('UPDATE identity.otp_challenges SET key_version=''synthetic-smoke''');
SELECT pg_temp.reject_otp('UPDATE identity.otp_challenges SET superseded_at=created_at-INTERVAL ''1 second''');
ROLLBACK;
