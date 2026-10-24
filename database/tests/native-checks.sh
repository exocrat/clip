#!/usr/bin/env bash
# PD-08 Step 6: native macOS verification, separate from Compose acceptance.
# Arguments are tool locations only; the script creates its own private cluster
# and never accepts an existing PGDATA, database URL, host, or production target.
set -euo pipefail
set +x
[[ $# == 2 ]] || { echo 'Usage: bash database/tests/native-checks.sh POSTGRES_PREFIX DBMATE_BINARY' >&2; exit 1; }
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
  --options="-k $socket -p 55438 -c listen_addresses='' -c timezone=UTC -c log_timezone=UTC" start \
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
  [[ $(sql --command 'SELECT max(version) FROM public.schema_migrations') == 20261023202807 ]]
  [[ $(sql --command 'SELECT count(*) FROM public.schema_migrations') == 7 ]]
  [[ $(sql --command "SELECT count(*) FROM pg_tables WHERE schemaname IN ('identity','listings','search','conversations')") == 30 ]]
  [[ $(sql --command 'SELECT count(*) FROM listings.categories') == 8 ]]
  [[ $(sql --command 'SELECT count(*) FROM listings.conditions') == 4 ]]
  [[ $(sql --command 'SHOW server_version_num') == 180006 ]]
  [[ $(sql --command 'SHOW listen_addresses') == '' ]]
  [[ $(sql --command "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('identity','listings','search','conversations')") == 21 ]]
  [[ $(sql --command "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE NOT t.tgisinternal AND n.nspname IN ('identity','listings','search','conversations')") == 33 ]]
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
sql --file "$root/database/tests/retired-origin-smoke.sql" > "$evidence/retirement-first.log" 2>&1
sql --file "$root/database/tests/identity-schema-smoke.sql" > "$evidence/identity-first.log" 2>&1
sql --file "$root/database/tests/identity-otp-smoke.sql" > "$evidence/otp-first.log" 2>&1
sql --file "$root/database/tests/identity-session-smoke.sql" > "$evidence/session-first.log" 2>&1

# No fixture commits remain after the smoke rollback; down/up is confined to
# this disposable database and is not the persistent Compose-volume reset.
for revision in 1 2 3 4 5 6 7; do migrate rollback > "$evidence/rollback-$revision.log" 2>&1; done
[[ $(sql --command 'SELECT count(*) FROM public.schema_migrations') == 0 ]]
[[ $(sql --command "SELECT count(*) FROM pg_namespace WHERE nspname IN ('identity','listings','search','conversations')") == 0 ]]
migrate migrate > "$evidence/apply-second.log" 2>&1
check_head
sql --file "$root/database/tests/schema-smoke.sql" > "$evidence/smoke-second.log" 2>&1
sql --file "$root/database/tests/retired-origin-smoke.sql" > "$evidence/retirement-second.log" 2>&1
sql --file "$root/database/tests/identity-schema-smoke.sql" > "$evidence/identity-second.log" 2>&1
sql --file "$root/database/tests/identity-otp-smoke.sql" > "$evidence/otp-second.log" 2>&1
sql --file "$root/database/tests/identity-session-smoke.sql" > "$evidence/session-second.log" 2>&1
inventory > "$evidence/inventory-second.txt"
cmp "$evidence/inventory-first.txt" "$evidence/inventory-second.txt"
clean_env "$pgbin/pg_dump" --host="$socket" --port=55438 --username=clip_native_test \
  --dbname=clip_test_native --schema-only --no-owner --no-privileges > "$evidence/schema.sql"
printf '%s\n' 'PASS: native clean apply/head, repeat migrate, five smoke suites twice, seven down migrations, clean reapply and identical runtime schema inventory.'
