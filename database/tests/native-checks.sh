#!/usr/bin/env bash
# PD-08 Step 6: native macOS verification, separate from Compose acceptance.
# Arguments are tool locations only; the script creates its own private cluster
# and never accepts an existing PGDATA, database URL, host, or production target.
set -euo pipefail
set +x
[[ $# == 2 || ( $# == 3 && ( ${3:-} == --listings-store || ${3:-} == --embedding-worker || ${3:-} == --search-calibration || ${3:-} == --hybrid-read ) ) ]] || { echo 'Usage: bash database/tests/native-checks.sh POSTGRES_PREFIX DBMATE_BINARY [--listings-store|--embedding-worker|--search-calibration|--hybrid-read]' >&2; exit 1; }
run_listings=false
run_worker=0
run_calibration=0
run_hybrid=0
[[ ${3:-} != --hybrid-read ]] || run_hybrid=1
[[ ${3:-} != --search-calibration ]] || run_calibration=1
[[ ${3:-} != --embedding-worker ]] || run_worker=1
[[ $# == 2 ]] || run_listings=true
[[ $(uname -s) == Darwin ]] || { echo 'This checkpoint is for native macOS only.' >&2; exit 1; }
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
pgbin=$(cd -- "$1/bin" && pwd -P)
dbmate=$(cd -- "$(dirname -- "$2")" && pwd -P)/$(basename -- "$2")
[[ $("$pgbin/postgres" --version) == 'postgres (PostgreSQL) 18.6' ]] || { echo 'Expected PostgreSQL 18.6.' >&2; exit 1; }
[[ $("$dbmate" --version) == 'dbmate version 2.36.0' ]] || { echo 'Expected dbmate 2.36.0.' >&2; exit 1; }
umask 077
evidence=$(mktemp -d /tmp/clip-pd08-native-check.XXXXXX)
cluster=$evidence/cluster
socket=$evidence/socket
mkdir "$socket"
socket_directories=$socket
adapter_socket=
if [[ "$run_listings" == true ]]; then
  adapter_root=$(mktemp -d /tmp/clip-listings-test-XXXXXX)
  adapter_socket=$adapter_root/pgsocket
  mkdir "$adapter_socket"
  socket_directories=$socket,$adapter_socket
fi
printf 'Native check evidence: %s\n' "$evidence"

# Always stop only this newly created cluster; retain source logs/data for review.
# A stop failure must not turn an otherwise passing run into reported success.
cleanup() {
  local code=$?
  trap - EXIT
  if "$pgbin/pg_ctl" -D "$cluster" status >/dev/null 2>&1; then
    if ! "$pgbin/pg_ctl" -D "$cluster" --mode=fast --wait stop > "$evidence/stop.log" 2>&1; then
      echo 'Failed to stop the temporary cluster; inspect stop.log.' >&2
      code=1
    fi
  fi
  printf 'Native checks exit: %s; evidence retained at %s\n' "$code" "$evidence"
  exit "$code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Remove ambient provider/PG/dbmate configuration from every child invocation.
clean_env() { env -i PATH="$pgbin:/usr/bin:/bin" LC_ALL=C TZ=UTC "$@"; }

# Local trust is restricted to the owner's private socket directory; TCP host
# authentication rejects everything and listen_addresses is empty. No password.
clean_env "$pgbin/initdb" --pgdata="$cluster" --username=clip_native_test \
  --encoding=UTF8 --locale=C --auth-local=trust --auth-host=reject \
  > "$evidence/initdb.log" 2>&1
clean_env "$pgbin/pg_ctl" -D "$cluster" --log="$evidence/server.log" --wait \
  --options="-k $socket_directories -p 55438 -c listen_addresses='' -c timezone=UTC -c log_timezone=UTC" start \
  > "$evidence/start.log" 2>&1
clean_env "$pgbin/createdb" --host="$socket" --port=55438 \
  --username=clip_native_test clip_test_native

# All SQL and migrations target only the freshly created clip_test_ database.
sql() {
  clean_env "$pgbin/psql" --no-psqlrc --host="$socket" --port=55438 \
    --username=clip_native_test --dbname=clip_test_native \
    --set=ON_ERROR_STOP=1 --tuples-only --no-align "$@"
}
migrate() {
  local operation=$1
  shift
  if [[ "$operation" == migrate ]]; then set -- --strict "$@"; fi
  clean_env DATABASE_URL="postgres://clip_native_test@localhost:55438/clip_test_native?host=$socket&sslmode=disable" \
    "$dbmate" --env-file /dev/null --migrations-dir "$root/database/migrations" \
    --no-dump-schema "$operation" "$@"
}

# Check clean apply, repeat application and schema inventory at both clean heads.
check_head() {
  [[ $(sql --command 'SELECT max(version) FROM public.schema_migrations') == 20261029182500 ]]
  [[ $(sql --command 'SELECT count(*) FROM public.schema_migrations') == 32 ]]
  [[ $(sql --command "SELECT count(*) FROM pg_tables WHERE schemaname IN ('identity','listings','search','conversations')") == 41 ]]
  [[ $(sql --command 'SELECT count(*) FROM listings.categories') == 9 ]]
  [[ $(sql --command 'SELECT count(*) FROM listings.conditions') == 4 ]]
  [[ $(sql --command 'SHOW server_version_num') == 180006 ]]
  [[ $(sql --command 'SHOW listen_addresses') == '' ]]
  [[ $(sql --command "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('identity','listings','search','conversations')") == 36 ]]
  [[ $(sql --command "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE NOT t.tgisinternal AND n.nspname IN ('identity','listings','search','conversations')") == 46 ]]
}

# Snapshot ordered runtime definitions rather than OIDs, fixture UUIDs or dump
# timestamps, so clean rollback/reapply can be compared meaningfully.
inventory() {
  sql --command "
    SELECT definition FROM (
      SELECT concat_ws('|', 'column', n.nspname, c.relname, a.attname,
        format_type(a.atttypid,a.atttypmod), a.attnotnull, a.attgenerated,
        pg_get_expr(d.adbin,d.adrelid)) AS definition
      FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
      JOIN pg_namespace n ON n.oid=c.relnamespace
      LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
      WHERE a.attnum>0 AND NOT a.attisdropped AND c.relkind='r'
        AND n.nspname IN ('identity','listings','search','conversations')
      UNION ALL
      SELECT concat_ws('|','constraint',n.nspname,c.relname,k.conname,pg_get_constraintdef(k.oid,true))
      FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
      JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname IN ('identity','listings','search','conversations')
      UNION ALL
      SELECT concat_ws('|','index',schemaname,tablename,indexname,indexdef)
      FROM pg_indexes WHERE schemaname IN ('identity','listings','search','conversations')
      UNION ALL
      SELECT concat_ws('|','function',n.nspname,p.proname,pg_get_functiondef(p.oid))
      FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      WHERE n.nspname IN ('identity','listings','search','conversations')
      UNION ALL
      SELECT concat_ws('|','trigger',n.nspname,c.relname,t.tgname,pg_get_triggerdef(t.oid,true))
      FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
      JOIN pg_namespace n ON n.oid=c.relnamespace WHERE NOT t.tgisinternal
        AND n.nspname IN ('identity','listings','search','conversations')
    ) objects ORDER BY definition COLLATE \"C\""
}

sql --command "SELECT current_database(), version(), current_setting('server_encoding'), (SELECT datcollate FROM pg_database WHERE datname = current_database())" > "$evidence/connectivity.log"
migrate migrate > "$evidence/apply-first.log" 2>&1
check_head
inventory > "$evidence/inventory-first.txt"
migrate status > "$evidence/status-first.log" 2>&1
migrate migrate > "$evidence/repeat-migrate.log" 2>&1
check_head
sql --file "$root/database/tests/schema-smoke.sql" > "$evidence/smoke-first.log" 2>&1
sql --file "$root/database/tests/embedding-smoke.sql" > "$evidence/embedding-first.log" 2>&1
sql --file "$root/database/tests/search-storage-smoke.sql" > "$evidence/search-storage-first.log" 2>&1
sql --file "$root/database/tests/retired-origin-smoke.sql" > "$evidence/retirement-first.log" 2>&1
sql --file "$root/database/tests/identity-schema-smoke.sql" > "$evidence/identity-first.log" 2>&1
sql --file "$root/database/tests/identity-otp-smoke.sql" > "$evidence/otp-first.log" 2>&1
sql --file "$root/database/tests/identity-session-smoke.sql" > "$evidence/session-first.log" 2>&1

# No fixture commits remain after the smoke rollback; down/up is confined to
# this disposable database and is not the persistent Compose-volume reset.
for revision in $(seq 1 29); do migrate rollback > "$evidence/rollback-$revision.log" 2>&1; done
[[ $(sql --command 'SELECT count(*) FROM public.schema_migrations') == 0 ]]
[[ $(sql --command "SELECT count(*) FROM pg_namespace WHERE nspname IN ('identity','listings','search','conversations')") == 0 ]]
migrate migrate > "$evidence/apply-second.log" 2>&1
check_head
sql --file "$root/database/tests/schema-smoke.sql" > "$evidence/smoke-second.log" 2>&1
sql --file "$root/database/tests/embedding-smoke.sql" > "$evidence/embedding-second.log" 2>&1
sql --file "$root/database/tests/search-storage-smoke.sql" > "$evidence/search-storage-second.log" 2>&1
sql --file "$root/database/tests/retired-origin-smoke.sql" > "$evidence/retirement-second.log" 2>&1
sql --file "$root/database/tests/identity-schema-smoke.sql" > "$evidence/identity-second.log" 2>&1
sql --file "$root/database/tests/identity-otp-smoke.sql" > "$evidence/otp-second.log" 2>&1
sql --file "$root/database/tests/identity-session-smoke.sql" > "$evidence/session-second.log" 2>&1
inventory > "$evidence/inventory-second.txt"
cmp "$evidence/inventory-first.txt" "$evidence/inventory-second.txt"
clean_env "$pgbin/pg_dump" --host="$socket" --port=55438 --username=clip_native_test \
  --dbname=clip_test_native --schema-only --no-owner --no-privileges > "$evidence/schema.sql"
# Optional adapter target is a SECOND fresh database in this same owned cluster.
# Committed race fixtures remain here for inspection until an approved cleanup;
# they do not interfere with the empty-store migration round trip above.
if [[ "$run_listings" == true ]]; then
  sql --command 'CREATE ROLE clip_ci LOGIN'
  clean_env "$pgbin/createdb" --host="$socket" --port=55438 \
    --username=clip_native_test --owner=clip_ci clip_test_ci
  adapter_url="postgres://clip_ci@localhost:55438/clip_test_ci?host=$adapter_socket&sslmode=disable"
  clean_env DATABASE_URL="$adapter_url" "$dbmate" --env-file /dev/null \
    --migrations-dir "$root/database/migrations" --no-dump-schema migrate --strict \
    > "$evidence/adapter-migrate.log" 2>&1
  # Run saved pagination fixtures last: their committed corpus exceeds the
  # earlier mathematical bootstrap test's intentionally small batch budget.
  clean_env LISTINGS_TEST_HYBRID_MODEL="$run_hybrid" LISTINGS_TEST_SEARCH_CALIBRATION="$run_calibration" LISTINGS_TEST_EMBEDDING_WORKER_MODEL="$run_worker" LISTINGS_TEST_DATABASE_URL="$adapter_url" "$root/.venv/bin/python" -m pytest \
    "$root/apps/api/tests/domains/search/test_draft_matches_postgres.py" \
    "$root/apps/api/tests/domains/search/test_wanted_retirement_postgres.py" \
    "$root/apps/api/tests/domains/search/test_wanted_postgres.py" \
    "$root/apps/api/tests/domains/search/test_step6_postgres.py" \
    "$root/apps/api/tests/domains/search/test_wanted_response_postgres.py" \
    "$root/apps/api/tests/domains/search/test_category_migration_postgres.py" \
    "$root/apps/api/tests/domains/listings/test_postgres_store.py" \
    "$root/apps/api/tests/domains/listings/test_browse_postgres.py" \
    "$root/apps/api/tests/domains/listings/test_embedding_postgres.py" \
    "$root/apps/api/tests/domains/listings/test_embedding_worker_postgres.py" \
    "$root/apps/api/tests/domains/listings/test_hybrid_read_postgres.py" \
    "$root/tests/evaluation/test_search_calibration_postgres.py" \
    "$root/apps/api/tests/domains/listings/test_search_access_postgres.py" \
    "$root/apps/api/tests/domains/search/test_saved_postgres.py" \
    -q -W error > "$evidence/listings-tests.log" 2>&1
  cat "$evidence/listings-tests.log"
fi
printf '%s\n' 'PASS: native clean apply/head, repeat migrate, seven smoke suites twice, seventeen down migrations, clean reapply and identical runtime schema inventory.'
