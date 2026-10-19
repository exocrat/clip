#!/bin/sh
# Authenticate only as the dedicated probe login and require SELECT 1 plus
# its database/schema privilege boundary. Suppress psql diagnostics because
# the task log should expose status, never connection details or credentials.
set +x

if [ -z "${PGPASSWORD:-}" ]; then
  printf '%s\n' 'PostgreSQL probe failed; inspect task status without exposing credentials'
  exit 1
fi

result="$(psql --no-psqlrc --quiet --tuples-only --no-align --set=ON_ERROR_STOP=1 --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" --dbname="$PGDATABASE" --command="SELECT 1 WHERE current_user = 'clip_test_probe' AND has_database_privilege(current_user, current_database(), 'CONNECT') AND NOT has_database_privilege(current_user, current_database(), 'CREATE') AND NOT has_database_privilege(current_user, current_database(), 'TEMPORARY') AND NOT has_schema_privilege(current_user, 'public', 'CREATE')" 2>/dev/null)" || {
  printf '%s\n' 'PostgreSQL probe failed; inspect task status without exposing credentials'
  exit 1
}

if [ "$result" != "1" ]; then
  printf '%s\n' 'PostgreSQL probe or privilege check failed'
  exit 1
fi

printf '%s\n' 'PostgreSQL SELECT 1 and privilege checks passed'
