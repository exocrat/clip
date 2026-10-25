"""Dispatcher pacing/ownership guards; native probe proves real edit publication."""

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from psycopg import OperationalError
from psycopg_pool import PoolTimeout
import pytest

from app.domains.listings.embedding_dispatch import EmbeddingDispatcher
from app.domains.listings.embedding_worker import WorkerBusy, WorkerUnavailable

MODULE = "app.domains.listings.embedding_dispatch"


class ScriptedPool:
    """Track serial connection ownership; no SQL engine or fake model is supplied."""

    def __init__(self):
        self.active = 0
        self.borrows = 0
        self.open = AsyncMock()
        self.wait = AsyncMock()
        self.close = AsyncMock()

    @asynccontextmanager
    async def connection(self):
        self.active += 1
        self.borrows += 1
        assert self.active == 1
        try:
            yield SimpleNamespace(autocommit=True)
        finally:
            self.active -= 1


@pytest.mark.parametrize(
    "outcome,delay,processed",
    [("idle", 2, 0), ("deferred", 5, 1), ("failure_recorded", 5, 1)],
)
def test_idle_capacity_and_failed_jobs_are_paced_after_releasing_connection(
    outcome, delay, processed
):
    async def exercise():
        pool = ScriptedPool()
        helper = object()
        dispatcher = EmbeddingDispatcher("synthetic-unused", helper)
        dispatcher._pool = pool
        one = SimpleNamespace(run_one=AsyncMock(return_value=outcome))
        pauses = []

        async def pause(seconds):
            assert pool.active == 0
            pauses.append(seconds)
            raise asyncio.CancelledError()

        with (
            patch(MODULE + ".EmbeddingWorker", return_value=one) as worker,
            patch(MODULE + ".asyncio.sleep", side_effect=pause),
        ):
            with pytest.raises(asyncio.CancelledError):
                await dispatcher._run()
        assert pauses == [delay]
        assert (
            dispatcher.status.processed == processed
            and dispatcher.status.published == 0
        )
        assert dispatcher.status.last_outcome == outcome
        assert worker.call_args.args[1] is helper
        one.run_one.assert_awaited_once()

    asyncio.run(exercise())


def test_ten_job_burst_is_serial_then_yields_without_backfill():
    async def exercise():
        pool = ScriptedPool()
        dispatcher = EmbeddingDispatcher("synthetic-unused", object())
        dispatcher._pool = pool
        one = SimpleNamespace(run_one=AsyncMock(return_value="published"))
        pauses = []

        async def pause(seconds):
            assert pool.active == 0
            pauses.append(seconds)
            if seconds:
                raise asyncio.CancelledError()

        with (
            patch(MODULE + ".EmbeddingWorker", return_value=one),
            patch(MODULE + ".asyncio.sleep", side_effect=pause),
        ):
            with pytest.raises(asyncio.CancelledError):
                await dispatcher._run()
        assert pauses == [0] * 10 + [1]
        assert pool.borrows == 10 and dispatcher.status.published == 10
        assert dispatcher.status.processed == 10

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "error",
    [
        WorkerBusy("synthetic-private"),
        WorkerUnavailable("synthetic-private"),
        OperationalError("synthetic-private"),
        PoolTimeout("synthetic-private"),
        TimeoutError("synthetic-private"),
    ],
)
def test_dependency_errors_pause_without_replay_or_private_logs(error, caplog):
    async def exercise():
        pool = ScriptedPool()
        dispatcher = EmbeddingDispatcher("synthetic-unused", object())
        dispatcher._pool = pool
        one = SimpleNamespace(run_one=AsyncMock(side_effect=error))

        async def pause(seconds):
            assert seconds == 5 and pool.active == 0
            raise asyncio.CancelledError()

        with (
            patch(MODULE + ".EmbeddingWorker", return_value=one),
            patch(MODULE + ".asyncio.sleep", side_effect=pause),
        ):
            with pytest.raises(asyncio.CancelledError):
                await dispatcher._run()
        one.run_one.assert_awaited_once()
        assert (
            dispatcher.status.state == "unavailable"
            and dispatcher.status.processed == 0
        )
        assert "synthetic-private" not in caplog.text

    asyncio.run(exercise())


def test_startup_connection_failure_is_closed_and_safe(caplog):
    async def exercise():
        pool = ScriptedPool()
        pool.wait.side_effect = PoolTimeout("synthetic-private")
        dispatcher = EmbeddingDispatcher("synthetic-unused", object())
        with patch(MODULE + ".AsyncConnectionPool", return_value=pool) as factory:
            await dispatcher.start()
        assert dispatcher.status.state == "unavailable" and dispatcher._task is None
        assert factory.call_args.kwargs["max_size"] == 1
        assert factory.call_args.kwargs["kwargs"]["autocommit"] is True
        pool.close.assert_awaited_once()
        assert "synthetic-private" not in caplog.text
        await dispatcher.close()

    asyncio.run(exercise())


def test_shutdown_awaits_job_cancellation_before_pool_close_and_leaves_helper_to_owner():
    async def exercise():
        pool = ScriptedPool()
        helper = SimpleNamespace(close=AsyncMock())
        dispatcher = EmbeddingDispatcher("synthetic-unused", helper)
        entered = asyncio.Event()
        cancelled = []

        async def job():
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(True)

        async def close():
            assert cancelled == [True] and pool.active == 0

        pool.close.side_effect = close
        one = SimpleNamespace(run_one=job)
        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool),
            patch(MODULE + ".EmbeddingWorker", return_value=one),
        ):
            await dispatcher.start()
            await entered.wait()
            with pytest.raises(ValueError):
                await dispatcher.start()
            await dispatcher.close()
        assert dispatcher._task.done() and dispatcher.status.state == "stopped"
        helper.close.assert_not_awaited()
        pool.close.assert_awaited_once()

    asyncio.run(exercise())


def test_unexpected_task_error_is_visible_and_cleanup_still_closes_pool(caplog):
    async def exercise():
        pool = ScriptedPool()
        dispatcher = EmbeddingDispatcher("synthetic-unused", object())
        failed = asyncio.Event()

        async def job():
            failed.set()
            raise RuntimeError("synthetic-private-bug")

        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool),
            patch(
                MODULE + ".EmbeddingWorker", return_value=SimpleNamespace(run_one=job)
            ),
        ):
            await dispatcher.start()
            await failed.wait()
            await asyncio.sleep(0)
            assert dispatcher.status.state == "failed"
            with pytest.raises(RuntimeError):
                await dispatcher.close()
        pool.close.assert_awaited_once()
        assert "synthetic-private-bug" not in caplog.text

    asyncio.run(exercise())
