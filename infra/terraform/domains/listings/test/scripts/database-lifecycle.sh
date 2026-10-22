#!/bin/sh
# Fixed, bounded database operations for the isolated LI-02 ECS tasks.
# Credentials arrive only through ECS secret injection and are never printed.
set +x

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

for tool in psql timeout sed; do
  command -v "$tool" >/dev/null 2>&1 || fail 'Listings database task failed; a required client tool is unavailable.'
done

: "${PGHOST:?Listings database task failed; database endpoint is not configured.}"
: "${PGPORT:?Listings database task failed; database port is not configured.}"
: "${PGUSER:?Listings database task failed; database login is not configured.}"
: "${PGPASSWORD:?Listings database task failed; database credential is unavailable.}"
: "${PGDATABASE:?Listings database task failed; database target is not configured.}"

# Do not inherit unbounded libpq or PostgreSQL work limits from the task.
export PGCONNECT_TIMEOUT=10
export PGOPTIONS='-c statement_timeout=30000 -c lock_timeout=30000'

psql_fixed() {
  # Both SQL and diagnostics stay out of CloudWatch; callers print only a
  # fixed status line after the bounded client process has completed.
  timeout --signal=TERM --kill-after=5s 60s psql \
    --no-psqlrc --quiet --set=ON_ERROR_STOP=1 \
    --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
    --dbname="$PGDATABASE" "$@" >/dev/null 2>&1
}

psql_query() {
  # Return only the fixed metadata query's value to a command substitution.
  # Keep diagnostics private; unlike write commands, these callers need stdout
  # to distinguish absent objects, verified ownership, and an idle database.
  timeout --signal=TERM --kill-after=5s 60s psql \
    --no-psqlrc --quiet --set=ON_ERROR_STOP=1 \
    --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
    --dbname="$PGDATABASE" --tuples-only --no-align "$@" 2>/dev/null
}

database_url_password() {
  : "${CLIP_DATABASE_URL:?Listings database task failed; URL secret is unavailable.}"
  # The operator-generated URL uses a random 64-character hex password.
  # Restrict its full shape and compare its host/port to the RDS endpoint in
  # this fixed task definition before using the password.
  parsed=$(printf '%s' "$CLIP_DATABASE_URL" | sed -nE \
    's#^postgresql://clip_test_listings_app:([0-9a-f]{64})@([^/:?#]+):([0-9]+)/clip_test_listings\?sslmode=require$#\1 \2 \3#p')
  [ -n "$parsed" ] || fail 'Listings database task failed; URL target did not match the isolated database contract.'
  url_password=${parsed%% *}
  endpoint=${parsed#* }
  [ "$endpoint" != "$parsed" ] || fail 'Listings database task failed; URL target did not match the isolated database contract.'
  url_host=${endpoint%% *}
  url_port=${endpoint#* }
  [ "$url_port" != "$endpoint" ] || fail 'Listings database task failed; URL target did not match the isolated database contract.'
  [ "$url_host" = "$PGHOST" ] && [ "$url_port" = "$PGPORT" ] \
    || fail 'Listings database task failed; URL endpoint did not match the shared test RDS endpoint.'
  printf '%s' "$url_password"
}

bootstrap() {
  [ "$PGDATABASE" = 'clip_test' ] && [ "$PGUSER" != 'clip_test_listings_app' ] \
    || fail 'Listings database bootstrap refused an unexpected admin connection target.'
  app_password=$(database_url_password)

  existing=$(psql_query --command="SELECT (EXISTS (SELECT 1 FROM pg_database WHERE datname = 'clip_test_listings'))::int || ' ' || (EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'clip_test_listings_app'))::int") \
    || fail 'Listings database bootstrap could not inspect the isolated target.'
  case "$existing" in
    '0 0') ;;
    '0 1'|'1 0'|'1 1') fail 'Listings database bootstrap found existing database state; run the reviewed stop cleanup before retrying.' ;;
    *) fail 'Listings database bootstrap received an invalid inspection result; preserve the database state.' ;;
  esac

  if {
    cat <<'SQL'
BEGIN;
DO $local_logging$
BEGIN
  IF current_setting('log_transaction_sample_rate')::double precision <> 0 THEN
    RAISE EXCEPTION 'database setup requires transaction sampling disabled before BEGIN';
  END IF;
  PERFORM set_config('log_statement', 'none', true);
  PERFORM set_config('log_min_duration_statement', '-1', true);
  PERFORM set_config('log_min_error_statement', 'panic', true);
  PERFORM set_config('log_min_duration_sample', '-1', true);
  PERFORM set_config('log_statement_sample_rate', '0', true);
  PERFORM set_config('log_parameter_max_length', '0', true);
  PERFORM set_config('log_parameter_max_length_on_error', '0', true);
END
$local_logging$;
DO $logging_guard$
BEGIN
  IF current_setting('log_statement') <> 'none'
    OR current_setting('log_min_duration_statement')::integer <> -1
    OR current_setting('log_min_error_statement') <> 'panic'
    OR current_setting('log_min_duration_sample')::integer <> -1
    OR current_setting('log_statement_sample_rate')::double precision <> 0
    OR current_setting('log_transaction_sample_rate')::double precision <> 0
    OR current_setting('log_parameter_max_length')::integer <> 0
    OR current_setting('log_parameter_max_length_on_error')::integer <> 0
    OR lower(coalesce(current_setting('pgaudit.log', true), 'none')) NOT IN ('none', '')
    OR coalesce(current_setting('auto_explain.log_min_duration', true), '-1') <> '-1'
  THEN RAISE EXCEPTION 'database setup requires reviewed safe statement logging'; END IF;
END
$logging_guard$;
CREATE ROLE clip_test_listings_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 12;
\password clip_test_listings_app
SQL
    printf '%s\n' "$app_password" "$app_password"
    cat <<'SQL'
COMMIT;
CREATE DATABASE clip_test_listings OWNER clip_test_listings_app TEMPLATE template0 ENCODING 'UTF8';
SQL
  } | timeout --signal=TERM --kill-after=5s 60s psql \
      --no-psqlrc --quiet --set=ON_ERROR_STOP=1 \
      --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
      --dbname=clip_test >/dev/null 2>&1; then
    :
  else
    fail 'Listings database bootstrap failed or timed out; inspect the ECS task result without exposing credentials.'
  fi

  PGDATABASE=clip_test_listings psql_fixed <<'SQL' \
    || fail 'Listings database bootstrap could not apply the isolated database grants.'
REVOKE CONNECT, TEMPORARY ON DATABASE clip_test_listings FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE clip_test_listings TO clip_test_listings_app;
DO $verify$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'clip_test_listings_app'
      AND rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
      AND NOT rolinherit AND NOT rolreplication AND NOT rolbypassrls
      AND rolconnlimit = 12
  ) OR NOT EXISTS (
    SELECT 1 FROM pg_database
    WHERE datname = 'clip_test_listings'
      AND pg_get_userbyid(datdba) = 'clip_test_listings_app'
  ) THEN RAISE EXCEPTION 'isolated Listings database owner or role attributes did not match'; END IF;
END
$verify$;
SQL
  printf '%s\n' 'Isolated Listings database bootstrap passed.'
}

seed() {
  [ "$PGDATABASE" = 'clip_test_listings' ] && [ "$PGUSER" = 'clip_test_listings_app' ] \
    || fail 'Listings seed refused an unexpected database/login target.'
  app_password=$(database_url_password)
  PGPASSWORD="$app_password" psql_fixed <<'SQL' \
    || fail 'Synthetic Listings seller seed failed; inspect the ECS task result.'
BEGIN;
INSERT INTO identity.users (id, account_class, status, display_name, activated_at)
VALUES (
  '10000000-0000-4000-8000-000000000001',
  'regular', 'active', 'Synthetic Listings Demo Seller', CURRENT_TIMESTAMP
)
ON CONFLICT (id) DO NOTHING;
DO $verify$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM identity.users
    WHERE id = '10000000-0000-4000-8000-000000000001'
      AND account_class = 'regular' AND status = 'active'
      AND display_name = 'Synthetic Listings Demo Seller'
      AND expires_at IS NULL AND revoked_at IS NULL AND profile_removed_at IS NULL
  ) THEN RAISE EXCEPTION 'synthetic demo seller row did not match'; END IF;
END
$verify$;
COMMIT;
SQL
  printf '%s\n' 'Synthetic Listings seller seed passed.'
}

cleanup() {
  [ "$PGDATABASE" = 'clip_test' ] && [ "$PGUSER" != 'clip_test_listings_app' ] \
    || fail 'Listings cleanup refused an unexpected admin connection target.'
  state=$(psql_query --command="SELECT (EXISTS (SELECT 1 FROM pg_database WHERE datname = 'clip_test_listings'))::int || ' ' || (EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'clip_test_listings_app'))::int") \
    || fail 'Listings cleanup could not inspect the isolated target.'
  case "$state" in
    '0 0')
      printf '%s\n' 'Isolated Listings database cleanup already passed.'
      return
      ;;
    '0 1')
      psql_fixed --command='DROP ROLE clip_test_listings_app' \
        || fail 'Listings cleanup found an orphaned role with dependencies; inspect before retrying.'
      printf '%s\n' 'Orphaned isolated Listings login cleanup passed.'
      return
      ;;
    '1 0') fail 'Listings cleanup found a database without its dedicated owner role; refusing destructive repair.' ;;
    '1 1') ;;
    *) fail 'Listings cleanup received an invalid inspection result; preserve the database state.' ;;
  esac
  owner=$(psql_query --command="SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = 'clip_test_listings'") \
    || fail 'Listings cleanup could not verify the isolated database owner.'
  [ "$owner" = 'clip_test_listings_app' ] \
    || fail 'Listings cleanup found a database not owned by the dedicated Listings role.'
  psql_fixed <<'SQL' || fail 'Listings cleanup could not terminate connections to the isolated database.'
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'clip_test_listings' AND pid <> pg_backend_pid();
SQL
  psql_fixed <<'SQL' || fail 'Listings cleanup failed; inspect the ECS task result without exposing credentials.'
DROP DATABASE clip_test_listings;
DROP ROLE clip_test_listings_app;
SQL
  printf '%s\n' 'Isolated Listings database cleanup passed.'
}

check_idle() {
  [ "$PGDATABASE" = 'clip_test' ] && [ "$PGUSER" != 'clip_test_listings_app' ] \
    || fail 'Listings idle check refused an unexpected admin connection target.'
  result=$(psql_query --command="SELECT count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND backend_type = 'client backend'") \
    || fail 'Listings shared-database idle check failed; preserve the shared RDS state.'
  case "$result" in
    ''|*[!0-9]*) fail 'Listings idle check received an invalid inspection result; preserve the shared RDS state.' ;;
  esac
  [ "$result" = '0' ] || fail 'Other database clients are connected; preserving the shared RDS state.'
  printf '%s\n' 'Shared RDS has no other PostgreSQL client sessions.'
}

case "${1:-}" in
  bootstrap) bootstrap ;;
  seed) seed ;;
  cleanup) cleanup ;;
  check-idle) check_idle ;;
  *) fail 'Listings database task refused an unknown fixed action.' ;;
esac
