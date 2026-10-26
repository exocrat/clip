-- Rollback-only synthetic session/rate/attempt constraints, not provider evidence.
BEGIN;
DO $$ BEGIN
 IF left(current_database(),10)<>'clip_test_' THEN RAISE EXCEPTION 'Disposable database required'; END IF;
END $$;
CREATE FUNCTION pg_temp.reject_session(command text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 BEGIN EXECUTE command; EXCEPTION WHEN check_violation THEN RETURN; END;
 RAISE EXCEPTION 'Session negative control unexpectedly accepted';
END $$;
INSERT INTO identity.users(id,account_class,status) VALUES('e2700000-0000-4000-8000-000000000001','regular','active');
INSERT INTO identity.sessions(id,user_id,token_digest,expires_at,last_seen_at)
VALUES('e2700000-0000-4000-8000-000000000002','e2700000-0000-4000-8000-000000000001',decode(repeat('11',32),'hex'),CURRENT_TIMESTAMP+INTERVAL '7 days',CURRENT_TIMESTAMP);
SELECT pg_temp.reject_session('UPDATE identity.sessions SET last_seen_at=created_at-INTERVAL ''1 second''');
SELECT pg_temp.reject_session('UPDATE identity.sessions SET token_digest=decode(''00'',''hex'')');
SELECT pg_temp.reject_session('UPDATE identity.sessions SET expires_at=created_at+INTERVAL ''8 days''');
SELECT pg_temp.reject_session('UPDATE identity.sessions SET last_seen_at=expires_at+INTERVAL ''1 second''');
INSERT INTO identity.microsoft_login_attempts(token_digest,created_at,expires_at) VALUES(decode(repeat('22',32),'hex'),CURRENT_TIMESTAMP,CURRENT_TIMESTAMP+INTERVAL '10 minutes');
SELECT pg_temp.reject_session('UPDATE identity.microsoft_login_attempts SET expires_at=created_at+INTERVAL ''11 minutes''');
SELECT pg_temp.reject_session('UPDATE identity.microsoft_login_attempts SET consumed_at=expires_at+INTERVAL ''1 second''');
ROLLBACK;
