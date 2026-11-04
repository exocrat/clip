"""Opt-in serial processing of existing jobs; never bootstrap or change a pipeline.

One dedicated autocommit connection and the API's shared helper are borrowed per
job. Durable leases/source fences/retry policy stay in EmbeddingStore/Worker.
"""

import asyncio
from dataclasses import dataclass
import logging
from typing import Any, Literal

from psycopg import AsyncConnection, Error as DatabaseError
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, PoolTimeout
from app.core.database_transport import (
    uses_proxy,
    connection_kwargs,
    check_async_proxy_connection,
)

from app.domains.listings.embedding_client import SemanticHelper, HelperUnavailable
from app.domains.listings.embedding_store import EmbeddingStore
from app.domains.listings.embedding_worker import (
    EmbeddingWorker,
    WorkerBusy,
    WorkerUnavailable,
)

Pool = AsyncConnectionPool[AsyncConnection[dict[str, Any]]]
logger = logging.getLogger(__name__)
BURST_JOBS = 10
IDLE_SECONDS = 2
YIELD_SECONDS = 1
FAILURE_SECONDS = 5


@dataclass
class DispatchStatus:
    """Internal counters/state only; never store source text, IDs or exceptions."""

    state: Literal["starting", "running", "unavailable", "failed", "stopped"] = (
        "starting"
    )
    processed: int = 0
    published: int = 0
    last_outcome: (
        Literal["idle", "published", "stale", "deferred", "failure_recorded"] | None
    ) = None


class EmbeddingDispatcher:
    """Own one background task/pool; its caller owns and closes the shared helper."""

    def __init__(self, conninfo: str, helper: SemanticHelper) -> None:
        """Bind an operator-configured target; construction performs no work."""
        self._conninfo = conninfo
        self._helper = helper
        self._pool: Pool | None = None
        self._task: asyncio.Task[None] | None = None
        self._started = False
        self.status = DispatchStatus()

    async def start(self) -> None:
        """Open one worker connection; expected failure leaves read capability usable."""
        if self._started:
            raise ValueError("Embedding dispatcher already started")
        self._started = True
        self._pool = AsyncConnectionPool(
            conninfo=self._conninfo,
            kwargs=connection_kwargs(
                self._conninfo,
                **{
                    "row_factory": dict_row,
                    "autocommit": True,
                    "options": "-c statement_timeout=5000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000",
                },
            ),
            configure=check_async_proxy_connection,
            check=(
                AsyncConnectionPool.check_connection
                if uses_proxy(self._conninfo)
                else None
            ),
            min_size=1,
            max_size=1,
            timeout=5,
            open=False,
        )
        try:
            await self._pool.open()
            await self._pool.wait(timeout=5)
        except DatabaseError, PoolTimeout, OSError, TimeoutError:
            await self._pool.close()
            self._pool = None
            self.status.state = "unavailable"
            logger.warning("Embedding dispatcher startup unavailable")
            return
        self.status.state = "running"
        self._task = asyncio.create_task(self._run(), name="listing-embedding-dispatch")
        self._task.add_done_callback(self._observe_done)

    def _observe_done(self, task: asyncio.Task[None]) -> None:
        """Expose unexpected task failure safely; close still propagates the error."""
        if not task.cancelled() and task.exception() is not None:
            self.status.state = "failed"
            logger.error("Embedding dispatcher stopped unexpectedly")

    async def _run(self) -> None:
        """Process <=10jobs per burst, yielding/pacing without replaying uncertain writes.

        Per-job20s/lease30s and durable retry limits remain in the worker/store.
        Claim/encode/publish is serial. No transaction is held during inference.
        An idle, deferred, recorded failure or dependency exception ends a burst;
        fixed pauses avoid a tight retry loop. Only due jobs can be claimed again.
        """
        assert self._pool is not None
        while True:
            for _ in range(BURST_JOBS):
                try:
                    async with self._pool.connection() as connection:
                        outcome = await EmbeddingWorker(
                            EmbeddingStore(connection), self._helper
                        ).run_one()
                except asyncio.CancelledError:
                    raise
                except (
                    WorkerBusy,
                    WorkerUnavailable,
                    HelperUnavailable,
                    DatabaseError,
                    PoolTimeout,
                    OSError,
                    TimeoutError,
                ):
                    self.status.state = "unavailable"
                    logger.warning("Embedding dispatcher dependency unavailable")
                    await asyncio.sleep(FAILURE_SECONDS)
                    break
                self.status.state = "running"
                self.status.last_outcome = outcome
                if outcome == "idle":
                    await asyncio.sleep(IDLE_SECONDS)
                    break
                self.status.processed += 1
                if outcome == "published":
                    self.status.published += 1
                if outcome in {"deferred", "failure_recorded"}:
                    await asyncio.sleep(FAILURE_SECONDS)
                    break
                await asyncio.sleep(0)
            else:
                await asyncio.sleep(YIELD_SECONDS)

    async def close(self) -> None:
        """Cancel/await active work before closing its pool; caller shields cleanup.

        Cancellation leaves committed leases recoverable by the existing expiry
        rules. No shutdown failure/retry writes are invented. Unexpected task or
        pool errors remain failures, while the pool is always attempted.
        """
        try:
            if self._task is not None:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
        finally:
            try:
                if self._pool is not None:
                    await self._pool.close()
            finally:
                if self.status.state != "failed":
                    self.status.state = "stopped"
