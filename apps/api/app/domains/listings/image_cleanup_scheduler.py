"""In-process daily reclamation of abandoned image-upload objects (issue #69).

The per-account image quota counts reserved bytes for every ``image_uploads``
row, including cancelled/expired intents, until the stored object is confirmed
deleted and the row removed (see
``docs/decisions/image-quota-accounting-and-daily-cleanup.md``). This scheduler
performs that reclamation from inside the API process itself — no separate ECS
task, schedule, or instance — by periodically invoking the Listings-owned
``cleanup_image_objects`` path.

A PostgreSQL session advisory lock elects a single leader per cycle so that,
with more than one API replica, the pass runs once rather than once per replica.
The underlying store already claims rows with ``FOR UPDATE ... SKIP LOCKED`` in
bounded batches, so a cycle is safe alongside live request traffic; the leader
lock is purely an efficiency gate.
"""

import asyncio
import logging
from typing import Any

from psycopg_pool import AsyncConnectionPool

from app.core.errors import ERRORS, PublicError
from app.domains.listings.service import (
    ListingsIdentity,
    ListingsService,
    ListingsStore,
)

logger = logging.getLogger(__name__)

# Stable, distinctive 64-bit key for the single-leader advisory lock. It only
# needs to be constant across replicas and unlikely to collide with other
# advisory-lock users; it is unrelated to any row key.
LEADER_LOCK_KEY = 0x1143_0069_C1EA_0069

DEFAULT_INTERVAL_SECONDS = 24 * 60 * 60
# A short settle before the first cycle lets the app warm up and staggers
# replicas that all started together, so they do not contend on the lock at once.
DEFAULT_INITIAL_DELAY_SECONDS = 300
DEFAULT_BATCH_SIZE = 100
# Bound a single cycle so a large backlog cannot hold a pool connection and the
# leader lock indefinitely; the next cycle resumes any remainder.
MAX_PASSES_PER_CYCLE = 100
MIN_INTERVAL_SECONDS = 60


async def run_cleanup_cycle(
    pool: AsyncConnectionPool[Any],
    service: ListingsService,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Run one leader-gated reclamation cycle and report what it did.

    Holds the advisory lock on a dedicated session for the whole cycle so no
    other replica runs concurrently, then releases it. ``cleanup_image_objects``
    raises a 503 after deferring any uncertain delete (those rows carry a
    cooldown and the next cycle retries them), so a 503 ends the cycle rather
    than spinning on the same rows.
    """
    async with pool.connection() as connection:
        cursor = await connection.execute(
            "SELECT pg_try_advisory_lock(%s) AS held", (LEADER_LOCK_KEY,)
        )
        row = await cursor.fetchone()
        assert row is not None
        if not row["held"]:
            return {"leader": False, "deleted": 0, "passes": 0, "deferred": False}
        deleted = 0
        passes = 0
        deferred = False
        try:
            for _ in range(MAX_PASSES_PER_CYCLE):
                passes += 1
                try:
                    reclaimed = await service.cleanup_image_objects(limit=batch_size)
                except PublicError as error:
                    if error.spec is not ERRORS[503]:
                        raise
                    deferred = True
                    break
                deleted += reclaimed
                if reclaimed == 0:
                    break
        finally:
            # Release the session-level lock explicitly; it would otherwise stay
            # held on this pooled connection and block every later leader attempt.
            await connection.execute(
                "SELECT pg_advisory_unlock(%s)", (LEADER_LOCK_KEY,)
            )
    return {"leader": True, "deleted": deleted, "passes": passes, "deferred": deferred}


async def run_scheduler(
    pool: AsyncConnectionPool[Any],
    service: ListingsService,
    *,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    initial_delay_seconds: int = DEFAULT_INITIAL_DELAY_SECONDS,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> None:
    """Loop until cancelled: wait, then run one leader-gated cleanup cycle.

    A cycle failure is logged without content and never stops the loop, so a
    transient database/storage problem does not disable future reclamation.
    """
    delay = max(0, initial_delay_seconds)
    interval = max(MIN_INTERVAL_SECONDS, interval_seconds)
    try:
        while True:
            await asyncio.sleep(delay)
            delay = interval
            try:
                result = await run_cleanup_cycle(pool, service, batch_size)
            except asyncio.CancelledError:
                raise
            except Exception:
                # Content-free: never log object keys, owners, or driver detail.
                logger.warning("Listings image cleanup cycle failed")
                continue
            if result["leader"] and (result["deleted"] or result["deferred"]):
                logger.info(
                    "Listings image cleanup reclaimed %d object(s)%s",
                    result["deleted"],
                    " (some deferred to a later cycle)" if result["deferred"] else "",
                )
    except asyncio.CancelledError:
        return


def start(
    pool: AsyncConnectionPool[Any],
    store: ListingsStore,
    identity: ListingsIdentity,
    storage: Any,
    *,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    initial_delay_seconds: int = DEFAULT_INITIAL_DELAY_SECONDS,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> asyncio.Task[None]:
    """Build the cleanup service and launch the background scheduler task."""
    service = ListingsService(store, identity, image_storage=storage)
    return asyncio.create_task(
        run_scheduler(
            pool,
            service,
            interval_seconds=interval_seconds,
            initial_delay_seconds=initial_delay_seconds,
            batch_size=batch_size,
        ),
        name="listings-image-cleanup",
    )
