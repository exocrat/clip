"""Listings-owned, opt-in helper/optional dispatcher lifecycle; no backfill/DDL.

The composition root owns this context per API process. Keyword/commands keep
using their existing pool even if Hybrid startup fails. Explicit helper runtime
and artifact checks are real; there is no fake or alternate-model fallback.
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import logging
from typing import Any, Literal

from psycopg import AsyncConnection, Error as DatabaseError
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, AsyncNullConnectionPool, PoolTimeout

from app.core.config import Settings
from app.domains.listings.embedding_client import SemanticHelper, HelperUnavailable
from app.domains.listings.embedding_dispatch import EmbeddingDispatcher

Pool = AsyncConnectionPool[AsyncConnection[dict[str, Any]]]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchRuntime:
    """Borrowed read dependencies valid only while the owning context is open."""

    state: Literal["disabled", "ready", "unavailable"]
    helper: SemanticHelper | None = field(default=None, repr=False)
    pool: Pool | None = field(default=None, repr=False)
    dispatcher: EmbeddingDispatcher | None = field(default=None, repr=False)


async def finish_search_cleanup(cleanup: Awaitable[None]) -> None:
    """Finish owned cleanup through late cancellation without hiding failures.

    A server can replay SIGINT at the first cleanup await. The cleanup task is
    shielded and awaited to completion; any close/reap error still propagates.
    Cancellation already propagating from the context body remains unchanged.
    """
    task = asyncio.ensure_future(cleanup)
    while True:
        try:
            await asyncio.shield(task)
            return
        except asyncio.CancelledError:
            if task.cancelled():
                raise
            if task.done():
                task.result()
                return


async def _close(
    helper: SemanticHelper | None,
    pool: Pool | None,
    dispatcher: EmbeddingDispatcher | None = None,
) -> None:
    """Await worker cancellation first, then reap helper/close read pool; attempt all."""
    try:
        if dispatcher is not None:
            await dispatcher.close()
    finally:
        try:
            if helper is not None:
                await helper.close()
        finally:
            if pool is not None:
                await pool.close()


@asynccontextmanager
async def search_runtime(
    settings: Settings,
    *,
    pool_max_size: int = 2,
    enable_worker: bool | None = None,
    retain_idle_connections: bool = True,
) -> AsyncIterator[SearchRuntime]:
    """Open one helper and a bounded dedicated autocommit read pool.

    Defaults create no resources. Explicit startup failure closes both owned
    resources, yields unavailable, and logs only a fixed safe message. Caller
    authorization, supported serving configuration and complete eligible-source
    coverage remain request prerequisites. No job registration, pipeline switch,
    schema change or backfill occurs here. A separately enabled dispatcher can
    process existing jobs only, borrowing this same helper.
    """
    if pool_max_size < 1:
        raise ValueError("Hybrid pool maximum must be positive")
    worker_enabled = (
        settings.hybrid_worker_enabled if enable_worker is None else enable_worker
    )
    pool: Pool | None = None
    helper: SemanticHelper | None = None
    dispatcher: EmbeddingDispatcher | None = None
    try:
        if not settings.hybrid_search_enabled:
            yield SearchRuntime("disabled")
            return
        assert settings.database_url is not None
        assert settings.hybrid_search_interpreter is not None
        assert settings.hybrid_search_model_dir is not None
        try:
            pool_type = (
                AsyncConnectionPool
                if retain_idle_connections
                else AsyncNullConnectionPool
            )
            pool = pool_type(
                conninfo=settings.database_url.get_secret_value(),
                kwargs={
                    "row_factory": dict_row,
                    "autocommit": True,
                    "options": "-c statement_timeout=5000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000",
                },
                min_size=1 if retain_idle_connections else 0,
                max_size=pool_max_size,
                timeout=5,
                max_waiting=32,
                open=False,
            )
            helper = SemanticHelper(
                settings.hybrid_search_interpreter, settings.hybrid_search_model_dir
            )
            await pool.open()
            await pool.wait(timeout=5)
            await helper.start()
        except (
            HelperUnavailable,
            DatabaseError,
            PoolTimeout,
            OSError,
            TimeoutError,
            ValueError,
        ):
            await finish_search_cleanup(_close(helper, pool, dispatcher))
            helper = None
            pool = None
            logger.warning("Hybrid search startup unavailable")
        if helper is not None and worker_enabled:
            dispatcher = EmbeddingDispatcher(
                settings.database_url.get_secret_value(), helper
            )
            await dispatcher.start()
        yield (
            SearchRuntime("ready", helper, pool, dispatcher)
            if helper is not None
            else SearchRuntime("unavailable")
        )
    finally:
        await finish_search_cleanup(_close(helper, pool, dispatcher))
