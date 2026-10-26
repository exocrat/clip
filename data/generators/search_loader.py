"""Opt-in local PostgreSQL fixture loader, not a final or production data path.

Only the fixed clip_test_search_preview database and clip_search_preview role
over an explicit local Unix socket are accepted. The caller must separately
prepare that empty migrated test database. There is no create/reset/delete,
network host, URL, ambient database setting, authentication or storage fallback.
Real PostgreSQL execution is a pending integration check until actually run.
"""

import argparse
from datetime import UTC, datetime
import os
from pathlib import Path
from typing import Any

import psycopg

from .search_preview import ROOT, read_corpus, validate_corpus

DATABASE = "clip_test_search_preview"
ROLE = "clip_search_preview"


def require_local_preview(socket_dir: str, isolated: bool) -> Path:
    """Check explicit test opt-in before connecting; never read ambient DB URLs."""
    if (
        not isolated
        or os.environ.get("CLIP_ENVIRONMENT") != "test"
        or os.environ.get("CLIP_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
    ):
        raise ValueError(
            "Explicit isolated test mode without ambient database URLs required"
        )
    path = Path(socket_dir)
    if (
        not path.is_absolute()
        or not path.is_dir()
        or path.is_symlink()
        or any(parent.is_symlink() for parent in path.parents)
    ):
        raise ValueError("An ordinary absolute local Unix socket directory is required")
    return path


def load_corpus(
    connection: psycopg.Connection[tuple[Any, ...]], bundle: dict[str, Any]
) -> dict[str, Any]:
    """Atomically insert validated synthetic rows into a fresh fixture database.

    Server identity is checked before writes; exclusive table locks serialize
    the empty-target check and inserts. Any error rolls back all rows. Catalogue
    IDs are resolved from active codes, never assumed from random seed UUIDs.
    PostgreSQL computes its own vector and enforces deferred image/FK checks.
    Image metadata refers only to non-existent preview keys, never live objects.
    """
    validate_corpus(bundle)
    # Attachments must still be within their 24-hour confirmation window at
    # INSERT time. Historical listing timestamps would create expired uploads.
    # This is load audit metadata, not part of the logical corpus fingerprint.
    upload_confirmed_at = datetime.now(UTC)
    with connection.transaction():
        connection.execute("SET LOCAL statement_timeout = '30s'")
        connection.execute("SET LOCAL lock_timeout = '5s'")
        connection.execute("SET LOCAL TIME ZONE 'UTC'")
        target = connection.execute(
            "SELECT current_database(), current_user, inet_server_addr()"
        ).fetchone()
        if target != (DATABASE, ROLE, None):
            raise ValueError("Refusing a non-preview PostgreSQL target")
        connection.execute(
            "LOCK TABLE identity.users, listings.sale_listings, listings.image_uploads, listings.images IN ACCESS EXCLUSIVE MODE"
        )
        counts = connection.execute(
            "SELECT (SELECT count(*) FROM identity.users), (SELECT count(*) FROM listings.sale_listings), (SELECT count(*) FROM listings.image_uploads), (SELECT count(*) FROM listings.images)"
        ).fetchone()
        if counts != (0, 0, 0, 0):
            raise ValueError(
                "Preview database is not empty; reset/overwrite unsupported"
            )
        versions = {
            row[0]
            for row in connection.execute(
                "SELECT version FROM public.schema_migrations"
            ).fetchall()
        }
        expected_versions = {
            path.name.split("_", 1)[0]
            for path in (ROOT / "database/migrations").glob("*.sql")
        }
        if versions != expected_versions:
            raise ValueError("Preview database migrations do not match the checkout")
        categories = dict(
            connection.execute(
                "SELECT code, id FROM listings.categories WHERE active"
            ).fetchall()
        )
        conditions = {
            row[0]
            for row in connection.execute(
                "SELECT code FROM listings.conditions WHERE active"
            ).fetchall()
        }
        if any(
            row["category_code"] not in categories
            or row["condition_code"] not in conditions
            for row in bundle["listings"]
        ):
            raise ValueError("Required active catalogue entries are missing")
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO identity.users (id, account_class, status, display_name, created_at) VALUES (%s,%s,%s,%s,%s)",
                [
                    (
                        u["id"],
                        u["account_class"],
                        u["status"],
                        u["display_name"],
                        u["created_at"],
                    )
                    for u in bundle["users"]
                ],
            )
            for row in bundle["listings"]:
                cursor.execute(
                    """INSERT INTO listings.sale_listings
                    (id, owner_id, title, description, category_id, condition_code,
                     asking_price_paise, negotiable, pickup_area, proof_available,
                     availability, available_from, available_until, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        row["id"],
                        row["owner_id"],
                        row["title"],
                        row["description"],
                        categories[row["category_code"]],
                        row["condition_code"],
                        row["asking_price_paise"],
                        row["negotiable"],
                        row["pickup_area"],
                        row["proof_available"],
                        row["availability"],
                        row["available_from"],
                        row["available_until"],
                        row["created_at"],
                        row["updated_at"],
                    ),
                )
                key = f"synthetic-search-preview/{row['image_id']}"
                cursor.execute(
                    """INSERT INTO listings.image_uploads
                    (id, owner_id, operation_id, object_key, state, created_at, expires_at,
                     confirmed_at, requested_media_type, requested_size_bytes, confirmed_media_type, confirmed_size_bytes)
                    VALUES (%s,%s,%s,%s,'confirmed',%s,%s::timestamptz + interval '24 hours',%s,'image/png',1,'image/png',1)""",
                    (
                        row["image_id"],
                        row["owner_id"],
                        row["image_id"],
                        key,
                        upload_confirmed_at,
                        upload_confirmed_at,
                        upload_confirmed_at,
                    ),
                )
                cursor.execute(
                    """INSERT INTO listings.images
                    (id, listing_id, upload_id, object_key, position, media_type, size_bytes, created_at)
                    VALUES (%s,%s,%s,%s,0,'image/png',1,%s)""",
                    (
                        row["image_id"],
                        row["id"],
                        row["image_id"],
                        key,
                        row["created_at"],
                    ),
                )
        connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
        observed = connection.execute(
            "SELECT (SELECT count(*) FROM identity.users), (SELECT count(*) FROM listings.sale_listings), (SELECT count(*) FROM listings.images)"
        ).fetchone()
        expected = (
            len(bundle["users"]),
            len(bundle["listings"]),
            len(bundle["listings"]),
        )
        if observed != expected:
            raise ValueError("Loaded fixture counts do not match the corpus")
    return {
        "preview_only": True,
        "counts": bundle["manifest"]["observed_counts"],
        "logical_data_fingerprint": bundle["manifest"]["logical_data_fingerprint"],
        "image_objects_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    """Read a validated named run and connect locally with fixed database/role.

    Passwords/URLs are never CLI inputs; libpq environment overrides are
    rejected so they cannot redirect the fixed target.
    Failures emit one safe diagnostic without SQL, connection details or values.
    """
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--name", required=True)
    parser.add_argument("--socket-dir", required=True)
    parser.add_argument("--isolated-preview", action="store_true")
    args, unknown = parser.parse_known_args(argv)
    if unknown:
        parser.error("Unknown options; custom database targets/reset unsupported")
    try:
        path = require_local_preview(args.socket_dir, args.isolated_preview)
        bundle = read_corpus(args.name)
        # Hostaddr/service can override host/dbname despite explicit kwargs.
        # Reject rather than mutate global environment or log supplied values.
        if any(key.startswith("PG") for key in os.environ):
            raise ValueError("Ambient libpq configuration is unsupported")
        with psycopg.connect(
            host=str(path),
            dbname=DATABASE,
            user=ROLE,
            connect_timeout=5,
            passfile="/dev/null",
            autocommit=True,
        ) as connection:
            receipt = load_corpus(connection, bundle)
    except ValueError, OSError, psycopg.Error:
        parser.error(
            "Local fixture load refused or failed; verify test mode, empty migrated target and corpus"
        )
    print(receipt["logical_data_fingerprint"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
