#!/usr/bin/env bash
# Local-only lifecycle entry point. Requires Bash 3.2+, Docker and Compose v2.
# This script accepts commands, never database URLs or Docker endpoints.
set -euo pipefail
set +x

# Print only fixed messages; supplied environment values must not reach errors.
die() { printf '%s\n' "$1" >&2; exit 1; }

# Keep usage available even before Docker/password setup.
usage() {
  cat <<'USAGE'
Usage: bash database/local-db.sh {start|wait|migrate|status|stop}
       bash database/local-db.sh reset --confirm-delete-local-data
Local target only: project clip-local, database clip_local, 127.0.0.1:5432.
Reset permanently deletes volume clip-local_clip_local_postgres_data.
Set CLIP_LOCAL_POSTGRES_PASSWORD in the process environment; no dotenv is read.
USAGE
}

action=${1:-help}
case "$action" in
  help|--help|-h) usage; exit 0 ;;
  start|wait|migrate|status|stop) [[ $# == 1 ]] || die 'Unexpected arguments.' ;;
  reset)
    printf '%s\n' 'WARNING: reset permanently deletes all local database data in clip-local_clip_local_postgres_data.' >&2
    [[ $# == 2 && ${2:-} == --confirm-delete-local-data ]] || die 'Reset requires --confirm-delete-local-data; no action taken.'
    ;;
  *) usage >&2; die 'Unknown command; no action taken.' ;;
esac

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
[[ "$root" != *,* ]] || die 'Repository paths containing commas are unsupported by the bind-mount syntax.'
password=${CLIP_LOCAL_POSTGRES_PASSWORD:-}
[[ -n "$password" ]] || die 'Set the local-only CLIP_LOCAL_POSTGRES_PASSWORD environment variable.'
# URL-unreserved characters need no encoding; reject rather than misroute a URL.
case "$password" in *[!a-zA-Z0-9_.~-]*) die 'Local password must use only ASCII letters, digits, underscore, dot, tilde or hyphen.' ;; esac
for variable in DATABASE_URL PGHOST PGPORT PGDATABASE PGUSER PGSERVICE PGSERVICEFILE DOCKER_HOST DOCKER_CONTEXT DOCKER_TLS_VERIFY DOCKER_CERT_PATH COMPOSE_REMOVE_ORPHANS; do
  [[ -z ${!variable:-} ]] || die 'External database/Docker target overrides are unsupported; unset them before using the local wrapper.'
done
command -v docker >/dev/null 2>&1 || die 'Docker CLI is unavailable; install/enable the contributor-local container toolchain before runtime checks.'
# Redact only messages intended for people; parsed Docker metadata stays exact.
# In particular, a password such as "local" must not change a volume name.
redacted_output() {
  local output=$1
  output=${output//"$password"/[REDACTED]}
  [[ -z "$output" ]] || printf '%s\n' "$output"
  return 0
}

# Stream diagnostic lines through redaction before they reach stderr; no raw
# diagnostic file is written. Bash 3.2 supports the process substitution below.
redacted_stderr() {
  local line
  while IFS= read -r line || [[ -n "$line" ]]; do
    redacted_output "$line" >&2
  done
}

# Capture machine-readable stdout without rewriting it and isolate stderr from
# parsed results. On failure stdout is diagnostic too: sanitize it, send it to
# stderr and preserve the code. Successful raw output stays internal.
docker_query() {
  local output code=0
  output=$(docker "$@" 2> >(redacted_stderr)) || code=$?
  if [[ $code != 0 ]]; then
    redacted_output "$output" >&2
    return "$code"
  fi
  [[ -z "$output" ]] || printf '%s\n' "$output"
  return 0
}

# Internal resource queries use the context pinned after its local endpoint check.
docker_value() { docker_query --context "$context" "$@"; }

# Human-facing Docker output is sanitized even when the command succeeds.
docker_local() {
  local output code=0
  output=$(docker_value "$@") || code=$?
  redacted_output "$output"
  return "$code"
}

# Explicit file/project/empty env-file prevent ambient Compose/.env discovery.
compose() {
  docker_local compose --project-name clip-local --project-directory "$root" \
    --env-file /dev/null --file "$root/docker-compose.yml" "$@"
}

# One cooperative operator owns all lifecycle actions per local user/project.
# Never auto-remove an existing lock; a human must inspect a stale lock first.
lock_dir=${TMPDIR:-/tmp}/clip-local-database-$(id -u).lock
(umask 077; mkdir "$lock_dir") 2>/dev/null || die 'Another local lifecycle command holds the lock, or a stale lock needs inspection.'
# Release only the empty lock acquired by this invocation.
release_lock() { rmdir "$lock_dir"; }
trap release_lock EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
context=$(docker_query context show) || die 'Cannot identify the current Docker context.'
endpoint=$(docker_query context inspect "$context" --format '{{.Endpoints.docker.Host}}') || die 'Cannot inspect the Docker context.'
case "$endpoint" in unix:///*) ;; *) die 'Only a local Unix-socket Docker context is permitted; remote Docker targets are rejected.' ;; esac
docker_local info --format '{{.OSType}}' >/dev/null
compose version --short >/dev/null
# Quiet validation never prints interpolated credentials.
compose config --quiet

volume=clip-local_clip_local_postgres_data

# Refuse removal or reuse of a volume not labeled for this exact Compose key.
validate_volume() {
  local matches labels
  matches=$(docker_value volume ls --quiet --filter "name=^${volume}$")
  [[ -z "$matches" || "$matches" == "$volume" ]] || die 'Unexpected local volume selection.'
  if [[ -n "$matches" ]]; then
    labels=$(docker_value volume inspect "$volume" --format '{{index .Labels "com.docker.compose.project"}}|{{index .Labels "com.docker.compose.volume"}}')
    [[ "$labels" == 'clip-local|clip_local_postgres_data' ]] || die 'Volume ownership labels do not match; no action taken.'
  fi
}

# Resolve one service container and validate its clone, image, port and mount.
# Stopped containers retain HostConfig bindings, so stop/reset use the same guard.
container_id=
find_container() {
  local identity bindings mounts
  container_id=$(docker_value ps --all --quiet --filter label=com.docker.compose.project=clip-local --filter label=com.docker.compose.service=postgres)
  [[ "$container_id" != *$'\n'* ]] || die 'Multiple database containers match; inspect them before continuing.'
  [[ -n "$container_id" ]] || return 0
  identity=$(docker_value inspect "$container_id" --format '{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{index .Config.Labels "com.docker.compose.project.working_dir"}}|{{.Config.Image}}')
  [[ "$identity" == "clip-local|postgres|$root|postgres:18.6-bookworm" ]] || die 'Container ownership, clone or image does not match; no action taken.'
  bindings=$(docker_value inspect "$container_id" --format '{{range index .HostConfig.PortBindings "5432/tcp"}}{{.HostIp}}:{{.HostPort}}{{end}}')
  [[ "$bindings" == '127.0.0.1:5432' ]] || die 'Database port is not the expected loopback binding.'
  mounts=$(docker_value inspect "$container_id" --format '{{range .Mounts}}{{.Type}}|{{.Name}}|{{.Destination}}{{println}}{{end}}')
  [[ "$mounts" == "volume|$volume|/var/lib/postgresql" ]] || die 'Database mounts do not match the sole local volume.'
}

# Poll authenticated TCP connectivity, not just pg_isready. Each attempt has a
# two-second connection timeout; failures are intentionally value-free.
wait_ready() {
  local attempt last_output
  [[ -n "$container_id" ]] || die 'Local database container is absent; run start first.'
  export PGPASSWORD="$password"
  for ((attempt=0; attempt<30; attempt++)); do
    if last_output=$(docker_local exec --env PGPASSWORD --env PGCONNECT_TIMEOUT=2 "$container_id" \
      psql --no-psqlrc --host=127.0.0.1 --port=5432 --username=clip_local \
      --dbname=clip_local --set=ON_ERROR_STOP=1 --tuples-only --no-align \
      --command 'SELECT 1' 2>&1); then
      printf '%s\n' 'Local PostgreSQL authenticated connectivity is ready.'
      return 0
    fi
    sleep 2
  done
  [[ -z "$last_output" ]] || printf '%s\n' "$last_output" >&2
  die 'Local database readiness timed out; inspect the local service without printing credentials.'
}

# The tool shares only the validated DB container's network namespace; it gets
# no host networking, Docker socket or arbitrary URL. Migrations are read-only.
run_dbmate() {
  local version
  local operation=("$action")
  # In dbmate 2.36.0 strict is a migrate command option, not a global flag.
  if [[ "$action" == migrate ]]; then operation+=(--strict); fi
  version=$(cat "$root/database/dbmate.version")
  [[ "$version" == '2.36.0' ]] || die 'Unexpected dbmate version; review tool changes before running.'
  wait_ready
  export DATABASE_URL="postgres://clip_local:${password}@127.0.0.1:5432/clip_local?sslmode=disable&connect_timeout=5"
  docker_local run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
    --network "container:$container_id" --env DATABASE_URL \
    --mount "type=bind,src=$root/database/migrations,dst=/db/migrations,readonly" \
    "ghcr.io/amacneil/dbmate:$version" --env-file /dev/null \
    --migrations-dir /db/migrations --no-dump-schema "${operation[@]}"
}

validate_volume
find_container
case "$action" in
  start)
    compose up --detach postgres
    find_container
    wait_ready
    ;;
  wait) wait_ready ;;
  migrate|status) run_dbmate ;;
  stop)
    if [[ -n "$container_id" ]]; then docker_local stop --time 10 "$container_id"; fi
    printf '%s\n' 'Local database stopped; named volume retained.'
    ;;
  reset)
    if [[ -n "$container_id" ]]; then
      docker_local stop --time 10 "$container_id"
      docker_local container rm "$container_id"
    fi
    validate_volume
    if [[ -n $(docker_value volume ls --quiet --filter "name=^${volume}$") ]]; then
      # No --force and no broad compose down --volumes/prune operation.
      docker_local volume rm "$volume"
    fi
    printf '%s\n' 'Only the named local database volume was removed; run start, then migrate to recreate.'
    ;;
esac
