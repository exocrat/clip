"""Process-level PostgreSQL pool construction for domain-owned database work."""

from collections.abc import Callable
from typing import Protocol

from psycopg_pool import AsyncConnectionPool


class PoolLifecycle(Protocol):
    """The narrow pool lifecycle used by FastAPI and deterministic tests."""

    async def open(self, wait: bool = False, timeout: float = 30.0) -> None: ...

    async def close(self, timeout: float = 5.0) -> None: ...


PoolFactory = Callable[[str], PoolLifecycle]


def create_async_connection_pool(conninfo: str) -> AsyncConnectionPool:
    """Build a lazy, conservatively bounded pool without connecting immediately.

    The zero minimum avoids startup connections; one maximum connection is a
    safe initial local bound until deployment capacity is reviewed. Callers
    own open/close lifecycle, while domain providers acquire their own sessions.
    """
    return AsyncConnectionPool(
        conninfo=conninfo,
        min_size=0,
        max_size=1,
        open=False,
    )
