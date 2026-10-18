#!/usr/bin/env bash
# Exercise the wrapper's destructive/remote-target boundaries with a simulated
# Docker executable. No engine, database, registry or provider is contacted.
set -euo pipefail
set +x
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
scratch=$(mktemp -d "${TMPDIR:-/tmp}/clip-db-safety.XXXXXX")
# Cleanup is restricted to this test's newly created, private temporary tree.
trap 'rm -rf -- "$scratch"' EXIT
mkdir "$scratch/bin" "$scratch/runtime"

cat > "$scratch/bin/docker" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
expected_password=${MOCK_PASSWORD:-FAKE_LOCAL_ONLY_safety_test}
printf '%s\n' "$*" >> "$MOCK_LOG"
if [[ ${1:-} == context ]]; then
  case ${2:-} in
    show) echo desktop-linux ;;
    inspect)
      if [[ "$SCENARIO" == remote ]]; then echo tcp://example.invalid:2376
      else echo unix:///tmp/clip-simulated-docker.sock; fi
      ;;
  esac
  exit 0
fi
[[ ${1:-} == --context && ${2:-} == desktop-linux ]] || exit 90
shift 2
case ${1:-} in
  info) echo linux ;;
  compose)
    # An explicit file/project and empty env-file must survive every call.
    [[ "$*" == *'--project-name clip-local'* && "$*" == *'--env-file /dev/null'* && "$*" == *"--file $MOCK_ROOT/docker-compose.yml"* ]] || exit 91
    ;;
  volume)
    case ${2:-} in
      ls) echo clip-local_clip_local_postgres_data ;;
      inspect)
        if [[ "$SCENARIO" == wrong-volume ]]; then echo unrelated-project
        else echo 'clip-local|clip_local_postgres_data'; fi
        ;;
      rm) [[ ${3:-} == clip-local_clip_local_postgres_data && $# == 3 ]] || exit 92 ;;
      *) exit 93 ;;
    esac
    ;;
  ps)
    if [[ "$SCENARIO" == absent ]]; then exit 0; fi
    echo 123abc
    if [[ "$SCENARIO" == multiple ]]; then echo 456def; fi
    ;;
  inspect)
    if [[ "$SCENARIO" == metadata-warning ]]; then
      printf 'Simulated nonfatal diagnostic: %s\n' "$expected_password" >&2
    fi
    case "$*" in
      *HostConfig*)
        if [[ "$SCENARIO" == public-port ]]; then echo 0.0.0.0:5432
        else echo 127.0.0.1:5432; fi
        ;;
      *Mounts*)
        if [[ "$SCENARIO" == wrong-mount ]]; then echo 'volume|unrelated|/var/lib/postgresql'
        else echo 'volume|clip-local_clip_local_postgres_data|/var/lib/postgresql'; fi
        ;;
      *)
        if [[ "$SCENARIO" == wrong-clone ]]; then echo 'clip-local|postgres|/unrelated/clone|postgres:18.6-bookworm'
        else echo "clip-local|postgres|$MOCK_ROOT|postgres:18.6-bookworm"; fi
        ;;
    esac
    ;;
  exec)
    [[ ${PGPASSWORD:-} == "$expected_password" ]] || exit 94
    [[ "$*" == *'--host=127.0.0.1'* && "$*" == *'--dbname=clip_local'* ]] || exit 95
    echo 1
    ;;
  run)
    # Private-clone regression: migration reads must use the contributor identity
    # while keeping the tool filesystem read-only and all capabilities dropped.
    [[ "$*" == *"--user $(id -u):$(id -g)"* && "$*" == *'--read-only'* && "$*" == *'--cap-drop ALL'* ]] || exit 97
    [[ ${DATABASE_URL:-} == "postgres://clip_local:${expected_password}@127.0.0.1:5432/clip_local?sslmode=disable&connect_timeout=5" ]] || exit 96
    [[ "$*" == *'--network container:123abc'* && "$*" == *'--env DATABASE_URL'* && "$*" == *'ghcr.io/amacneil/dbmate:2.36.0'* && "$*" == *'--env-file /dev/null'* ]] || exit 97
    [[ "$*" == *'--no-dump-schema migrate --strict' || "$*" == *'--no-dump-schema status' ]] || exit 97
    # The complete credential-bearing URL must stay in the environment. A
    # password can also occur legitimately inside resource/argument names.
    [[ "$*" != *'postgres://clip_local:'* ]] || exit 98
    if [[ "$SCENARIO" == diagnostic ]]; then
      echo "Simulated failure: ${DATABASE_URL}" >&2
      exit 7
    fi
    if [[ "$SCENARIO" == diagnostic-stdout ]]; then
      echo "Simulated failure: ${DATABASE_URL}"
      exit 7
    fi
    if [[ "$SCENARIO" == diagnostic-success ]]; then
      echo "Simulated success: ${DATABASE_URL}"
    fi
    ;;
  stop) [[ ${2:-} == --time && ${3:-} == 10 && ${4:-} == 123abc && $# == 4 ]] || exit 99 ;;
  container) [[ ${2:-} == rm && ${3:-} == 123abc && $# == 3 ]] || exit 100 ;;
  *) exit 101 ;;
esac
MOCK
chmod +x "$scratch/bin/docker"

# Each case starts with a clean environment and captures exact child status.
# Failed guards must not reach any lifecycle/DDL/destructive Docker operation.
cases=0
test_password=FAKE_LOCAL_ONLY_safety_test
run_case() {
  local scenario=$1 expected=$2 code=0
  shift 2
  : > "$scratch/calls"
  env -i PATH="$scratch/bin:/usr/bin:/bin" HOME="$scratch" TMPDIR="$scratch/runtime" \
    LC_ALL=C MOCK_ROOT="$root" MOCK_LOG="$scratch/calls" SCENARIO="$scenario" \
    CLIP_LOCAL_POSTGRES_PASSWORD="$test_password" MOCK_PASSWORD="$test_password" "$@" \
    > "$scratch/output" 2>&1 || code=$?
  [[ $code == "$expected" ]] || { cat "$scratch/output"; echo "FAIL $scenario: status $code"; exit 1; }
  if [[ "$test_password" == FAKE_LOCAL_ONLY_safety_test ]]; then
    ! /usr/bin/grep -q FAKE_LOCAL_ONLY_safety_test "$scratch/output" || { echo 'FAIL: password exposed'; exit 1; }
  fi
  cases=$((cases + 1))
}

# Successful wiring exercises exact local args without a real Docker engine.
for action in start wait migrate status stop; do
  run_case local 0 /bin/bash "$root/database/local-db.sh" "$action"
done
run_case local 0 /bin/bash "$root/database/local-db.sh" reset --confirm-delete-local-data
/usr/bin/grep -q 'volume rm clip-local_clip_local_postgres_data$' "$scratch/calls"
! /usr/bin/grep -Eq 'down|prune|--force' "$scratch/calls" || { echo 'FAIL: broad deletion operation'; exit 1; }

for scenario in remote wrong-volume wrong-clone public-port wrong-mount multiple; do
  run_case "$scenario" 1 /bin/bash "$root/database/local-db.sh" reset --confirm-delete-local-data
  ! /usr/bin/grep -Eq ' (stop|run|exec|container rm|volume rm) | up ' "$scratch/calls" || { echo 'FAIL: refusal reached an operation'; exit 1; }
done
run_case absent 1 /bin/bash "$root/database/local-db.sh" migrate
! /usr/bin/grep -q ' run ' "$scratch/calls" || { echo 'FAIL: absent container reached dbmate'; exit 1; }
run_case confirmation 1 /bin/bash "$root/database/local-db.sh" reset
[[ ! -s "$scratch/calls" ]]
run_case arguments 1 /bin/bash "$root/database/local-db.sh" migrate --url postgres://example.invalid/production
[[ ! -s "$scratch/calls" ]]
run_case override 1 env DATABASE_URL=postgres://example.invalid/production /bin/bash "$root/database/local-db.sh" migrate
[[ ! -s "$scratch/calls" ]]
run_case override 1 env DOCKER_HOST=tcp://example.invalid:2376 /bin/bash "$root/database/local-db.sh" start
[[ ! -s "$scratch/calls" ]]
run_case override 1 env COMPOSE_REMOVE_ORPHANS=true /bin/bash "$root/database/local-db.sh" start
[[ ! -s "$scratch/calls" ]]
run_case missing-password 1 env -u CLIP_LOCAL_POSTGRES_PASSWORD /bin/bash "$root/database/local-db.sh" start
[[ ! -s "$scratch/calls" ]]
run_case unsafe-password 1 env CLIP_LOCAL_POSTGRES_PASSWORD='FAKE@invalid/url' /bin/bash "$root/database/local-db.sh" migrate
[[ ! -s "$scratch/calls" ]]
run_case diagnostic 7 /bin/bash "$root/database/local-db.sh" migrate
! /usr/bin/grep -q FAKE_LOCAL_ONLY_safety_test "$scratch/output" || { echo 'FAIL: diagnostic exposed password'; exit 1; }
/usr/bin/grep -q '\[REDACTED\]' "$scratch/output"

# Common valid passwords overlap volume names, IDs, bindings, image tags or
# punctuation. Metadata must remain raw internally through readiness/migration.
for test_password in local 123abc 127.0.0.1 18.6 -; do
  for action in status migrate; do
    run_case local 0 /bin/bash "$root/database/local-db.sh" "$action"
  done
done
test_password=FAKE_LOCAL_ONLY_safety_test

# Keep successful-query stderr out of parsed metadata, and sanitize diagnostic
# stdout on both failure and success without hiding the real command status.
run_case metadata-warning 0 /bin/bash "$root/database/local-db.sh" status
/usr/bin/grep -q '\[REDACTED\]' "$scratch/output"
run_case diagnostic-stdout 7 /bin/bash "$root/database/local-db.sh" migrate
/usr/bin/grep -q '\[REDACTED\]' "$scratch/output"
run_case diagnostic-success 0 /bin/bash "$root/database/local-db.sh" migrate
/usr/bin/grep -q '\[REDACTED\]' "$scratch/output"

# A stale/busy lock must survive unchanged, with no lifecycle operation.
mkdir "$scratch/runtime/clip-local-database-$(id -u).lock"
run_case lock 1 /bin/bash "$root/database/local-db.sh" start
[[ -d "$scratch/runtime/clip-local-database-$(id -u).lock" ]]
! /usr/bin/grep -q ' compose ' "$scratch/calls" || { echo 'FAIL: busy lock reached Compose'; exit 1; }
printf 'PASS: %s local wrapper safety/wiring cases (simulated Docker only).\n' "$cases"
