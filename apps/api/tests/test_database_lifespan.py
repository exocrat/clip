"""Exercise optional database-pool lifecycle without opening a real connection."""

from pydantic import SecretStr
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
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
