#!/bin/sh
# Apply only the checked-in LI-02 migrations using the pinned dbmate image.
# Suppress driver diagnostics so a failed connection cannot expose URL data.
set +x
set -eu

: "${DATABASE_URL:?Listings migration task failed; database URL is unavailable.}"

export DBMATE_MIGRATIONS_DIR=/db/migrations
export DBMATE_NO_DUMP_SCHEMA=true

if timeout --signal=TERM --kill-after=5s 60s /usr/local/bin/dbmate \
  --env-file /dev/null \
  --migrations-dir /db/migrations \
  --no-dump-schema \
  migrate --strict >/dev/null 2>&1; then
  printf '%s\n' 'Listings database migrations passed.'
else
  printf '%s\n' 'Listings database migrations failed or timed out; inspect task status without exposing credentials.' >&2
  exit 1
fi
