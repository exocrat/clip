#!/bin/sh
# Run once from the approved private ECS task. The transaction hardens the new
# test database's default PUBLIC grants, creates only the probe login, and
# verifies its attributes/ACLs. psql's password prompt keeps cleartext out of
# SQL text; diagnostics are suppressed so logs contain only safe status lines.
set +x

# Fail within the approved smoke-check window, including lock waits. GNU
# timeout bounds the complete psql session (60 seconds plus 5 to force exit);
# connection and SQL limits fail sooner. Never inherit unlimited caller values.
export PGCONNECT_TIMEOUT=10
export PGOPTIONS='-c statement_timeout=30000 -c lock_timeout=30000'

if ! command -v timeout >/dev/null 2>&1; then
  printf '%s\n' 'database probe login setup failed; required timeout tool unavailable'
  exit 1
fi

if [ -z "${PGPASSWORD:-}" ] || [ -z "${PROBE_PASSWORD:-}" ]; then
  printf '%s\n' 'database probe login setup failed; inspect task status without exposing credentials'
  exit 1
fi

if {
  cat <<'SQL'
BEGIN;
-- Apply only the approved transaction-local logging changes. set_config's
-- true flag restores prior values on COMMIT/ROLLBACK; no parameter group,
-- role default or other connection is changed. Permission errors abort before
-- any ACL/role/password work, with no privilege grants or fallback.
DO $local_logging$
BEGIN
  -- A transaction may already have been selected for logging at BEGIN.
  -- Do not assume changing its sample rate now can undo that selection.
  IF current_setting('log_transaction_sample_rate')::double precision <> 0 THEN
    RAISE EXCEPTION 'database setup requires transaction sampling disabled before BEGIN';
  END IF;
  IF current_setting('log_min_error_statement') <> 'panic' THEN
    PERFORM set_config('log_min_error_statement', 'panic', true);
  END IF;
  IF current_setting('log_statement') <> 'none' THEN
    PERFORM set_config('log_statement', 'none', true);
  END IF;
  IF current_setting('log_min_duration_statement')::integer <> -1 THEN
    PERFORM set_config('log_min_duration_statement', '-1', true);
  END IF;
  IF current_setting('log_min_duration_sample')::integer <> -1 THEN
    PERFORM set_config('log_min_duration_sample', '-1', true);
  END IF;
END
$local_logging$;
-- Inspect effective settings in this same bounded session before any ACL,
-- role or password change. Metadata with unset defaults is not evidence.
-- Reject successful-statement logging, duration/transaction sampling, and
-- failed-statement logging (which could retain the password verifier).
-- Optional audit/explain logging still fails closed when enabled. Verify the
-- local changes rather than assuming they succeeded; never retry to bypass.
DO $logging_guard$
BEGIN
  IF current_setting('log_statement') <> 'none'
    OR current_setting('log_min_duration_statement')::integer <> -1
    OR (
      current_setting('log_min_duration_sample')::integer <> -1
      AND current_setting('log_statement_sample_rate')::double precision <> 0
    )
    OR current_setting('log_transaction_sample_rate')::double precision <> 0
    OR current_setting('log_min_error_statement') <> 'panic'
    OR lower(coalesce(current_setting('pgaudit.log', true), 'none'))
      NOT IN ('none', '')
    OR coalesce(current_setting('auto_explain.log_min_duration', true), '-1') <> '-1'
  THEN
    RAISE EXCEPTION 'database setup requires reviewed safe statement logging';
  END IF;
END
$logging_guard$;
REVOKE CONNECT, TEMPORARY ON DATABASE :"dbname" FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE ROLE clip_test_probe WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2;
GRANT CONNECT ON DATABASE :"dbname" TO clip_test_probe;
\password clip_test_probe
SQL
  printf '%s\n' "$PROBE_PASSWORD" "$PROBE_PASSWORD"
  cat <<'SQL'
DO $verify$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles
    WHERE rolname = 'clip_test_probe'
      AND rolcanlogin
      AND NOT rolsuper
      AND NOT rolcreatedb
      AND NOT rolcreaterole
      AND NOT rolinherit
      AND NOT rolreplication
      AND NOT rolbypassrls
      AND rolconnlimit = 2
  ) THEN
    RAISE EXCEPTION 'probe login role flags did not match';
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_auth_members
    WHERE member = 'clip_test_probe'::regrole
  ) THEN
    RAISE EXCEPTION 'probe login unexpectedly has role memberships';
  END IF;
  IF NOT has_database_privilege('clip_test_probe', current_database(), 'CONNECT')
    OR has_database_privilege('clip_test_probe', current_database(), 'CREATE')
    OR has_database_privilege('clip_test_probe', current_database(), 'TEMPORARY') THEN
    RAISE EXCEPTION 'probe login database privileges did not match';
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_namespace n
    WHERE n.nspname <> 'information_schema'
      AND left(n.nspname, 3) <> 'pg_'
      AND has_schema_privilege('clip_test_probe', n.oid, 'CREATE')
  ) THEN
    RAISE EXCEPTION 'probe login unexpectedly has schema-create privilege';
  END IF;
  IF EXISTS (
    SELECT 1
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname <> 'information_schema'
      AND left(n.nspname, 3) <> 'pg_'
      AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
      AND (
        has_table_privilege('clip_test_probe', c.oid, 'SELECT')
        OR has_table_privilege('clip_test_probe', c.oid, 'INSERT')
        OR has_table_privilege('clip_test_probe', c.oid, 'UPDATE')
        OR has_table_privilege('clip_test_probe', c.oid, 'DELETE')
        OR has_table_privilege('clip_test_probe', c.oid, 'TRUNCATE')
        OR has_table_privilege('clip_test_probe', c.oid, 'REFERENCES')
        OR has_table_privilege('clip_test_probe', c.oid, 'TRIGGER')
      )
  ) OR EXISTS (
    SELECT 1
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname <> 'information_schema'
      AND left(n.nspname, 3) <> 'pg_'
      AND c.relkind = 'S'
      AND (
        has_sequence_privilege('clip_test_probe', c.oid, 'USAGE')
        OR has_sequence_privilege('clip_test_probe', c.oid, 'SELECT')
        OR has_sequence_privilege('clip_test_probe', c.oid, 'UPDATE')
      )
  ) THEN
    RAISE EXCEPTION 'probe login unexpectedly has table or sequence privileges';
  END IF;
END
$verify$;
COMMIT;
SQL
} | timeout --signal=TERM --kill-after=5s 60s psql --no-psqlrc --quiet --set=ON_ERROR_STOP=1 --set=dbname="$PGDATABASE" --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" --dbname="$PGDATABASE" -f - >/dev/null 2>&1; then
  printf '%s\n' 'database probe login setup passed'
else
  printf '%s\n' 'database probe login setup failed or timed out; inspect task status without exposing credentials'
  exit 1
fi
