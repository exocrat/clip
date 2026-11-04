"""Process-level PostgreSQL pool construction for domain-owned database work."""

from collections.abc import Callable
from typing import Protocol

from psycopg_pool import AsyncConnectionPool

from app.core.database_transport import (
    uses_proxy,
    connection_kwargs,
    check_async_proxy_connection,
)


class PoolLifecycle(Protocol):
    """The narrow pool lifecycle used by FastAPI and deterministic tests."""

    async def open(self, wait: bool = False, timeout: float = 30.0) -> None: ...

    async def close(self, timeout: float = 5.0) -> None: ...


PoolFactory = Callable[[str], PoolLifecycle]


def create_async_connection_pool(conninfo: str) -> AsyncConnectionPool:
    """Build a lazy, conservatively bounded pool without connecting immediately.

    The zero minimum avoids startup connections; two maximum connections per
    task fit the shared Conversations role limit of four across two tasks. Callers
    own open/close lifecycle, while domain providers acquire their own sessions.
    """
    return AsyncConnectionPool(
        conninfo=conninfo,
        kwargs=connection_kwargs(conninfo),
        configure=check_async_proxy_connection,
        check=AsyncConnectionPool.check_connection if uses_proxy(conninfo) else None,
        min_size=0,
        max_size=2,
        max_waiting=32,
        timeout=2,
        open=False,
    )
