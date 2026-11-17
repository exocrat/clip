"""Reclaim abandoned/expired image-upload objects on an explicitly checked target.

Dry-run by default: it only counts the upload rows currently eligible for the
next reclamation pass and touches no storage. With ``--apply`` it runs the
Listings-owned ``cleanup_image_objects`` path, which deletes each eligible S3
object and then removes its row (with the store's own retry/defer on an
uncertain delete). This is the once-daily maintenance job behind the planned
image-quota limitation; see
``docs/decisions/image-quota-accounting-and-daily-cleanup.md``.

The database DSN comes from ``CLIP_DATABASE_URL`` and the bucket configuration
from ``CLIP_IMAGE_BUCKET`` / ``CLIP_IMAGE_REGION`` / ``CLIP_IMAGE_KEY_PREFIX`` —
never argv or output. This command creates no schedule and prints counts only;
applying to a shared/persistent target keeps its own operator-run approval.
"""

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
import sys

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
from app.core.errors import ERRORS, PublicError
from app.domains.listings.integrations import PublicListingsIdentity
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.s3_storage import S3ListingsImageStorage
from app.domains.listings.service import ListingsService

# One pass asks for at most the store's own 1..500 batch bound; the outer loop
# repeats bounded passes so a single run cannot spin unboundedly on a backlog.
MAX_PASSES = 100

# Read-only estimate of rows the next apply pass would claim. It mirrors the
# eligibility predicate in PostgresListingsStore.list_abandoned_uploads_for_cleanup
# (due, not cooling down, unattached) but claims nothing and counts only the
# abandoned-upload rows, so it is an estimate, not the authoritative apply result.
_ELIGIBLE_ESTIMATE = """
SELECT count(*) AS rows,
       COALESCE(SUM(COALESCE(requested_size_bytes, confirmed_size_bytes, 10485760)), 0) AS reserved
FROM listings.image_uploads AS upload
WHERE upload.expires_at <= statement_timestamp() - INTERVAL '5 minutes'
    AND (upload.cleanup_retry_after IS NULL
        OR upload.cleanup_retry_after <= statement_timestamp())
    AND upload.state IN ('pending', 'confirmed', 'failed', 'expired')
    AND NOT EXISTS (
        SELECT 1 FROM listings.images AS image
        WHERE image.upload_id = upload.id
    )
"""


def _image_storage() -> S3ListingsImageStorage:
    """Build S3 storage from the same CLIP_IMAGE_* configuration the API uses."""
    return S3ListingsImageStorage(
        os.environ.get("CLIP_IMAGE_BUCKET", ""),
        os.environ.get("CLIP_IMAGE_REGION", ""),
        os.environ.get("CLIP_IMAGE_KEY_PREFIX", ""),
    )


async def _estimate(pool: AsyncConnectionPool) -> dict[str, int]:
    """Count the upload rows a reclamation pass would currently be eligible to claim."""
    async with pool.connection() as connection:
        cursor = await connection.execute(_ELIGIBLE_ESTIMATE)
        row = await cursor.fetchone()
    return {"eligible_rows": int(row["rows"]), "reserved_bytes": int(row["reserved"])}


async def _apply(pool: AsyncConnectionPool, batch_size: int) -> dict[str, int]:
    """Run bounded reclamation passes until a pass reclaims nothing or deferrals occur.

    ``cleanup_image_objects`` deletes retired images and abandoned-upload objects,
    then removes their rows. It raises a 503 after deferring any uncertain delete;
    those rows carry a cooldown and the next scheduled run retries them, so this
    loop records that deferrals happened and stops rather than hammering them.
    """
    # The price threshold and Identity are required by the constructors but are
    # unused by the object-cleanup path, which touches only the store and storage.
    service = ListingsService(
        PostgresListingsStore(pool, 0),
        PublicListingsIdentity(),
        image_storage=_image_storage(),
    )
    deleted = 0
    passes = 0
    deferred = False
    for _ in range(MAX_PASSES):
        passes += 1
        try:
            reclaimed = await service.cleanup_image_objects(limit=batch_size)
        except PublicError as error:
            if error.spec is not ERRORS[503]:
                raise
            # Some deletes were uncertain and have been deferred with a cooldown.
            deferred = True
            break
        deleted += reclaimed
        if reclaimed == 0:
            break
    return {"deleted": deleted, "passes": passes, "deferred": int(deferred)}


async def execute(args: argparse.Namespace) -> None:
    """Validate database, host and port on every connection; print counts only."""
    if args.expected_database in {"postgres", "template0", "template1"}:
        raise ValueError("Application database required")

    async def check_target(connection: AsyncConnection) -> None:
        """Reject a mismatched DSN before any query runs."""
        info = connection.info
        if (
            info.dbname != args.expected_database
            or info.host != args.expected_host
            or info.port != args.expected_port
        ):
            raise ValueError("Target mismatch")

    async with AsyncConnectionPool(
        os.environ["CLIP_DATABASE_URL"],
        min_size=0,
        max_size=1,
        timeout=5,
        # dict_row matches what PostgresListingsStore and the estimate query expect.
        kwargs={"autocommit": True, "connect_timeout": 3, "row_factory": dict_row},
        check=check_target,
        open=False,
    ) as pool:
        if args.apply:
            result = {"mode": "apply", **await _apply(pool, args.batch_size)}
        else:
            result = {"mode": "dry-run", **await _estimate(pool)}
    print(json.dumps(result, sort_keys=True))


def main() -> int:
    """Parse target assertions and mode; suppress private driver/config details."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--expected-host", required=True)
    parser.add_argument("--expected-port", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    # Pool retries otherwise emit private connection/driver diagnostics before
    # the CLI can replace them with its reviewed generic failure message.
    logging.getLogger("psycopg.pool").disabled = True
    try:
        if not 1 <= args.expected_port <= 65535:
            raise ValueError("Invalid target port")
        if not 1 <= args.batch_size <= 500:
            raise ValueError("Batch size must be between 1 and 500")
        asyncio.run(execute(args))
        return 0
    except Exception:
        print(
            "Listings image cleanup failed; review target/configuration/state",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
