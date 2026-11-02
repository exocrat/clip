"""Normal composition/lifecycle guards; scripted resources never prove inference."""

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from psycopg import OperationalError
from psycopg_pool import PoolTimeout
import pytest

from app.core.config import Settings
from app.domains.listings.embedding_client import HelperUnavailable
from app.domains.listings.search_runtime import search_runtime, finish_search_cleanup

MODULE = "app.domains.listings.search_runtime"


def enabled():
    """Explicit synthetic targets only; all external resource factories are patched."""
    return Settings(
        database_url="postgres://synthetic-private@localhost/clip_test",
        hybrid_search_enabled=True,
        hybrid_search_interpreter="/synthetic/python",
        hybrid_search_model_dir="/synthetic/model",
    )


def resources():
    """Script lifecycle calls without spawning, reading files or connecting anywhere."""
    pool = SimpleNamespace(
        open=AsyncMock(), wait=AsyncMock(), close=AsyncMock(), connection=Mock()
    )
    helper = SimpleNamespace(start=AsyncMock(), close=AsyncMock())
    return pool, helper


def test_disabled_creates_no_pool_helper_or_worker():
    async def exercise():
        with (
            patch(MODULE + ".AsyncConnectionPool") as pools,
            patch(MODULE + ".SemanticHelper") as helpers,
        ):
            async with search_runtime(Settings()) as runtime:
                assert (
                    runtime.state == "disabled"
                    and runtime.helper is None
                    and runtime.pool is None
                )
        pools.assert_not_called()
        helpers.assert_not_called()

    asyncio.run(exercise())


def test_enabled_resources_bounded_explicit_and_closed_without_sql():
    async def exercise():
        pool, helper = resources()
        settings = enabled()
        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool) as pools,
            patch(MODULE + ".SemanticHelper", return_value=helper) as helpers,
        ):
            async with search_runtime(settings) as runtime:
                assert (
                    runtime.state == "ready"
                    and runtime.pool is pool
                    and runtime.helper is helper
                )
                kwargs = pools.call_args.kwargs
                assert kwargs["conninfo"] == settings.database_url.get_secret_value()
                assert kwargs["kwargs"]["autocommit"] is True
                assert (
                    kwargs["max_size"] == 2
                    and kwargs["timeout"] == 5
                    and kwargs["open"] is False
                )
                assert "statement_timeout=5000" in kwargs["kwargs"]["options"]
                helpers.assert_called_once_with(
                    settings.hybrid_search_interpreter, settings.hybrid_search_model_dir
                )
                pool.wait.assert_awaited_once_with(timeout=5)
                helper.start.assert_awaited_once()
                pool.connection.assert_not_called()  # no register/backfill/serving DML
        helper.close.assert_awaited_once()
        pool.close.assert_awaited_once()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "failure",
    [
        HelperUnavailable("synthetic-private-detail"),
        OSError("synthetic-private-detail"),
        TimeoutError("synthetic-private-detail"),
        PoolTimeout("synthetic-private-detail"),
        OperationalError("synthetic-private-detail"),
    ],
)
def test_expected_startup_failures_degrade_and_close_without_private_logs(
    failure, caplog
):
    async def exercise():
        pool, helper = resources()
        helper.start.side_effect = failure
        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool),
            patch(MODULE + ".SemanticHelper", return_value=helper),
        ):
            async with search_runtime(enabled()) as runtime:
                assert (
                    runtime.state == "unavailable"
                    and runtime.pool is None
                    and runtime.helper is None
                )
                helper.close.assert_awaited_once()
                pool.close.assert_awaited_once()
        assert "synthetic-private-detail" not in caplog.text
        assert "Hybrid search startup unavailable" in caplog.text

    asyncio.run(exercise())


def test_read_pool_failure_closes_without_starting_helper():
    async def exercise():
        pool, helper = resources()
        pool.wait.side_effect = PoolTimeout("controlled")
        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool),
            patch(MODULE + ".SemanticHelper", return_value=helper),
        ):
            async with search_runtime(enabled()) as runtime:
                assert runtime.state == "unavailable"
        helper.start.assert_not_awaited()
        helper.close.assert_awaited_once()
        pool.close.assert_awaited_once()

    asyncio.run(exercise())


def test_cancelled_startup_cleans_and_propagates():
    async def exercise():
        pool, helper = resources()
        entered = asyncio.Event()

        async def wait():
            entered.set()
            await asyncio.Event().wait()

        helper.start.side_effect = wait
        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool),
            patch(MODULE + ".SemanticHelper", return_value=helper),
        ):

            async def start():
                async with search_runtime(enabled()):
                    pytest.fail("Cancelled startup must never yield a runtime")

            task = asyncio.create_task(start())
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        helper.close.assert_awaited_once()
        pool.close.assert_awaited_once()

    asyncio.run(exercise())


def test_close_failure_still_closes_pool_and_remains_failure():
    async def exercise():
        pool, helper = resources()
        helper.close.side_effect = RuntimeError("controlled close failure")
        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool),
            patch(MODULE + ".SemanticHelper", return_value=helper),
        ):
            with pytest.raises(RuntimeError):
                async with search_runtime(enabled()):
                    pass
        pool.close.assert_awaited_once()

    asyncio.run(exercise())


def test_late_cancellation_does_not_skip_owned_cleanup():
    async def exercise():
        entered = asyncio.Event()
        finish = asyncio.Event()
        closed = []

        async def close():
            entered.set()
            await finish.wait()
            closed.append(True)

        task = asyncio.create_task(finish_search_cleanup(close()))
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        finish.set()
        await task
        assert closed == [True]

    asyncio.run(exercise())


@pytest.mark.parametrize("hybrid", [False, True])
def test_actual_main_composition_keeps_command_pool_transactional(monkeypatch, hybrid):
    """Use actual lifespan/composition with scripted handles; no test caller installed."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    from app import main

    settings = enabled() if hybrid else Settings(database_url="postgres://synthetic/db")
    monkeypatch.setattr(main, "settings", settings)
    base, _ = resources()
    read, helper = resources()

    async def exercise():
        application = FastAPI()
        with (
            patch.object(
                main, "AsyncConnectionPool", return_value=base
            ) as base_factory,
            patch(MODULE + ".AsyncConnectionPool", return_value=read),
            patch(MODULE + ".SemanticHelper", return_value=helper),
        ):
            async with main.lifespan(application):
                store = application.state.listings_store
                assert store._pool is base
                assert "autocommit" not in base_factory.call_args.kwargs["kwargs"]
                assert store._hybrid_pool is (read if hybrid else None)
                assert store._hybrid_helper is (helper if hybrid else None)
                assert application.dependency_overrides == {}
                assert application.state.search_runtime.state == (
                    "ready" if hybrid else "disabled"
                )
        base.close.assert_awaited_once()
        if hybrid:
            read.close.assert_awaited_once()
            helper.close.assert_awaited_once()

    asyncio.run(exercise())


def test_main_cancellation_during_base_startup_closes_pool(monkeypatch):
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    from app import main

    monkeypatch.setattr(
        main, "settings", Settings(database_url="postgres://synthetic/db")
    )
    base, _ = resources()
    base.open.side_effect = asyncio.CancelledError()

    async def exercise():
        with patch.object(main, "AsyncConnectionPool", return_value=base):
            with pytest.raises(asyncio.CancelledError):
                async with main.lifespan(FastAPI()):
                    pytest.fail("Startup cancelled")
        base.close.assert_awaited_once()

    asyncio.run(exercise())


def test_main_composition_failure_closes_hybrid_and_command_resources(monkeypatch):
    """A later adapter constructor failure cannot leak the newly opened helper/pools."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    from app import main

    settings = enabled().model_copy(update={"storage_provider": "s3"})
    monkeypatch.setattr(main, "settings", settings)
    base, _ = resources()
    read, helper = resources()

    async def exercise():
        with (
            patch.object(main, "AsyncConnectionPool", return_value=base),
            patch(MODULE + ".AsyncConnectionPool", return_value=read),
            patch(MODULE + ".SemanticHelper", return_value=helper),
            patch.object(
                main,
                "S3ListingsImageStorage",
                side_effect=RuntimeError("Controlled construction failure"),
            ),
        ):
            with pytest.raises(RuntimeError):
                async with main.lifespan(FastAPI()):
                    pytest.fail("Composition failed before serving")
        helper.close.assert_awaited_once()
        read.close.assert_awaited_once()
        base.close.assert_awaited_once()

    asyncio.run(exercise())


def test_worker_opt_in_shares_helper_and_closes_before_helper_and_read_pool():
    async def exercise():
        pool, helper = resources()
        order = []
        worker = SimpleNamespace(start=AsyncMock(), close=AsyncMock())
        worker.close.side_effect = lambda: order.append("worker")
        helper.close.side_effect = lambda: order.append("helper")
        pool.close.side_effect = lambda: order.append("read_pool")
        settings = enabled().model_copy(update={"hybrid_worker_enabled": True})
        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool),
            patch(MODULE + ".SemanticHelper", return_value=helper),
            patch(MODULE + ".EmbeddingDispatcher", return_value=worker) as dispatch,
        ):
            async with search_runtime(settings) as runtime:
                assert runtime.dispatcher is worker
                dispatch.assert_called_once_with(
                    settings.database_url.get_secret_value(), helper
                )
                worker.start.assert_awaited_once()
        assert order == ["worker", "helper", "read_pool"]

    asyncio.run(exercise())


def test_lambda_read_runtime_can_use_one_connection_without_starting_worker():
    """Keep the Lambda Hybrid read pool single-connection and worker-free."""

    async def exercise():
        pool, helper = resources()
        settings = enabled().model_copy(update={"hybrid_worker_enabled": True})
        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool) as pools,
            patch(MODULE + ".SemanticHelper", return_value=helper),
            patch(MODULE + ".EmbeddingDispatcher") as dispatch,
        ):
            async with search_runtime(
                settings,
                pool_max_size=1,
                enable_worker=False,
            ) as runtime:
                assert runtime.state == "ready"
                assert runtime.pool is pool and runtime.helper is helper
                assert runtime.dispatcher is None
                assert pools.call_args.kwargs["max_size"] == 1
                assert pools.call_args.kwargs["min_size"] == 1
                dispatch.assert_not_called()
        pool.close.assert_awaited_once()
        helper.close.assert_awaited_once()

    asyncio.run(exercise())


def test_unavailable_helper_never_starts_a_worker():
    async def exercise():
        pool, helper = resources()
        helper.start.side_effect = HelperUnavailable("controlled")
        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool),
            patch(MODULE + ".SemanticHelper", return_value=helper),
            patch(MODULE + ".EmbeddingDispatcher") as dispatch,
        ):
            async with search_runtime(
                enabled().model_copy(update={"hybrid_worker_enabled": True})
            ) as runtime:
                assert runtime.state == "unavailable" and runtime.dispatcher is None
        dispatch.assert_not_called()

    asyncio.run(exercise())


def test_worker_startup_cancellation_cleans_all_resources():
    async def exercise():
        pool, helper = resources()
        worker = SimpleNamespace(
            start=AsyncMock(side_effect=asyncio.CancelledError()), close=AsyncMock()
        )
        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool),
            patch(MODULE + ".SemanticHelper", return_value=helper),
            patch(MODULE + ".EmbeddingDispatcher", return_value=worker),
        ):
            with pytest.raises(asyncio.CancelledError):
                async with search_runtime(
                    enabled().model_copy(update={"hybrid_worker_enabled": True})
                ):
                    pytest.fail("Startup was cancelled")
        worker.close.assert_awaited_once()
        helper.close.assert_awaited_once()
        pool.close.assert_awaited_once()

    asyncio.run(exercise())


def test_worker_close_failure_still_closes_helper_and_read_pool():
    async def exercise():
        pool, helper = resources()
        worker = SimpleNamespace(
            start=AsyncMock(), close=AsyncMock(side_effect=RuntimeError("controlled"))
        )
        with (
            patch(MODULE + ".AsyncConnectionPool", return_value=pool),
            patch(MODULE + ".SemanticHelper", return_value=helper),
            patch(MODULE + ".EmbeddingDispatcher", return_value=worker),
        ):
            with pytest.raises(RuntimeError):
                async with search_runtime(
                    enabled().model_copy(update={"hybrid_worker_enabled": True})
                ):
                    pass
        helper.close.assert_awaited_once()
        pool.close.assert_awaited_once()

    asyncio.run(exercise())
