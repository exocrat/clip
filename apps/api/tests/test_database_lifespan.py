"""Exercise optional and combined pool ownership without external connections."""

import asyncio
from unittest.mock import MagicMock

from pydantic import SecretStr
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application import application_lifespan
from app.core.config import Settings
from app.core.database_transport import check_async_proxy_connection
from app.core.database import PoolLifecycle
from app.main import create_app


class FakePool:
    """Record lifecycle calls while deliberately providing no DB connection."""

    def __init__(self, *, fail_open: bool = False) -> None:
        self.fail_open = fail_open
        self.opened = False
        self.closed = False
        self.wait: bool | None = None

    async def open(self, wait: bool = False, timeout: float = 30.0) -> None:
        """Record lazy open; optionally simulate safe startup failure."""
        self.wait = wait
        if self.fail_open:
            raise RuntimeError("synthetic pool startup failure")
        self.opened = True

    async def close(self, timeout: float = 5.0) -> None:
        """Record orderly shutdown without touching an external database."""
        self.closed = True


def test_lifespan_opens_and_closes_injected_pool_without_database_access():
    """Keep the DSN inside construction and bind the pool only during lifespan."""
    dsn = "postgresql://clip_user:synthetic-secret@database.invalid/clip"
    settings = Settings(database_dsn=SecretStr(dsn))
    pool = FakePool()
    received: list[str] = []

    def factory(conninfo: str) -> PoolLifecycle:
        received.append(conninfo)
        return pool

    application = create_app(settings, pool_factory=factory)
    with TestClient(application) as client:
        assert pool.opened is True
        assert pool.wait is False
        assert application.state.database_pool is pool
        assert not hasattr(application.state, "origin_retirement_operations")
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    assert received == [dsn]
    assert pool.closed is True
    assert application.state.database_pool is None


def test_lifespan_without_dsn_does_not_construct_a_pool():
    """Preserve credential-free local startup and avoid implicit fallback pools."""
    called = False

    def factory(conninfo: str) -> PoolLifecycle:
        nonlocal called
        called = True
        raise AssertionError("pool factory must not be used without a DSN")

    application = create_app(Settings(), pool_factory=factory)
    with TestClient(application) as client:
        assert application.state.database_pool is None
        assert client.get("/health").json() == {"status": "ok"}
    assert called is False


def test_lifespan_closes_pool_when_open_fails():
    """Clean up a partially started pool and propagate startup failure."""
    pool = FakePool(fail_open=True)
    application = create_app(
        Settings(
            database_dsn=SecretStr("postgresql://synthetic@database.invalid/clip")
        ),
        pool_factory=lambda _conninfo: pool,
    )
    with pytest.raises(RuntimeError, match="synthetic pool startup failure"):
        with TestClient(application):
            pytest.fail("a failed pool open must prevent application startup")
    assert pool.closed is True


@pytest.mark.parametrize(
    "failure",
    [None, "marketplace_factory", "marketplace_wait", "body", "marketplace_close"],
)
@pytest.mark.parametrize("dedicated_login", [False, True])
def test_combined_lifespan_owns_both_pools_and_unwinds_failures(
    failure, dedicated_login
):
    """Exercise the actual composition context, not a copied lifecycle algorithm.

    Mock only connection-pool I/O; providers/stores and disabled Search runtime
    use their real constructors. SQL/auth integration is checked separately on
    disposable PostgreSQL. A failure in either startup or shutdown must still
    close the Conversations pool, without opening worker/provider resources.
    """
    events = []

    def recording_pool(name):
        """Record ordered async boundaries; never create sockets or background tasks."""
        pool = MagicMock(spec=AsyncConnectionPool)

        async def opened(**kwargs):
            events.append((name, "open", kwargs))

        async def waited(**kwargs):
            events.append((name, "wait", kwargs))
            if failure == "marketplace_wait":
                raise RuntimeError("synthetic private connection detail")

        async def closed():
            events.append((name, "close"))
            if name == "marketplace" and failure == "marketplace_close":
                raise RuntimeError("synthetic close failure")

        pool.open.side_effect = opened
        pool.wait.side_effect = waited
        pool.close.side_effect = closed
        return pool

    conversation_pool = recording_pool("conversations")
    marketplace_pool = recording_pool("marketplace")
    shared = "postgresql://synthetic@database.invalid/shared"
    dedicated = "postgresql://synthetic_conversations@database.invalid/shared"
    settings = Settings(
        environment="test",
        database_url=SecretStr(shared),
        database_dsn=SecretStr(dedicated) if dedicated_login else None,
    )
    application = FastAPI()

    def tuple_factory(conninfo):
        """Keep explicit Conversations override separate from marketplace settings."""
        assert conninfo == (dedicated if dedicated_login else shared)
        return conversation_pool

    def dictionary_factory(**kwargs):
        """Assert the existing bounded dictionary-row configuration is preserved."""
        assert kwargs == {
            "conninfo": shared,
            "kwargs": {"row_factory": dict_row},
            "configure": check_async_proxy_connection,
            "check": None,
            "min_size": 1,
            "max_size": 6,
            "timeout": 5,
            "max_waiting": 64,
            "open": False,
        }
        if failure == "marketplace_factory":
            raise RuntimeError("synthetic factory failure")
        return marketplace_pool

    async def exercise():
        """Check all public providers share app ownership, not database sessions."""
        async with application_lifespan(
            application,
            settings,
            pool_factory=dictionary_factory,
            conversation_pool_factory=tuple_factory,
        ):
            assert application.state.database_pool is conversation_pool
            assert (
                application.state.conversations_public
                is application.state.listings_conversations
            )
            assert application.state.listings_store is not None
            assert application.state.wanted_store is not None
            assert application.state.saved_store is not None
            assert application.state.search_runtime.state == "disabled"
            assert application.state.listings_image_storage is None
            if failure == "body":
                raise RuntimeError("synthetic body failure")

    if failure is None:
        asyncio.run(exercise())
    else:
        with pytest.raises(RuntimeError) as raised:
            asyncio.run(exercise())
        if failure == "marketplace_wait":
            assert "connection details are redacted" in str(raised.value)
            assert "synthetic private" not in str(raised.value)
    conversation_pool.close.assert_awaited_once()
    if failure != "marketplace_factory":
        marketplace_pool.close.assert_awaited_once()
        assert events[-2:] == [("marketplace", "close"), ("conversations", "close")]
    assert events[0] == ("conversations", "open", {"wait": False})
    assert application.state.database_pool is None
    assert application.state.conversations_public is None
