"""Fail-closed caller and target checks for the isolated cloud rehearsal only."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.auth import CallerContext
from app.core.config import ISOLATED_LISTINGS_TEST_DATABASE

ISOLATED_TEST_SELLER_ID = UUID("10000000-0000-4000-8000-000000000001")
ISOLATED_LISTINGS_TEST_DATABASE_ROLE = "clip_test_listings_app"


class IsolatedListingsTestIdentity:
    """Approve only the fixed synthetic seller in the dedicated test database."""

    async def account_is_eligible(self, user_id: UUID) -> bool:
        """Never treat a client-supplied or otherwise unknown ID as eligible."""
        return user_id == ISOLATED_TEST_SELLER_ID


def isolated_test_caller() -> CallerContext:
    """Create trusted server context without reading request headers or body."""
    return CallerContext(
        ISOLATED_TEST_SELLER_ID,
        "regular",
        datetime.now(UTC) + timedelta(hours=8),
    )


async def require_isolated_test_database(
    pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]],
) -> None:
    """Require the dedicated DB and least-privilege app login before serving."""
    async with pool.connection() as connection:
        cursor = await connection.execute("""
            SELECT current_database() AS database_name,
                current_user AS current_role,
                session_user AS login_role,
                role.rolsuper AS is_superuser,
                role.rolcreatedb AS can_create_database,
                role.rolcreaterole AS can_create_role,
                role.rolreplication AS can_replicate,
                role.rolbypassrls AS can_bypass_row_security
            FROM pg_roles AS role
            WHERE role.rolname = current_user
            """)
        target = await cursor.fetchone()
    if (
        target is None
        or target["database_name"] != ISOLATED_LISTINGS_TEST_DATABASE
        or target["current_role"] != ISOLATED_LISTINGS_TEST_DATABASE_ROLE
        or target["login_role"] != ISOLATED_LISTINGS_TEST_DATABASE_ROLE
        or target["is_superuser"]
        or target["can_create_database"]
        or target["can_create_role"]
        or target["can_replicate"]
        or target["can_bypass_row_security"]
    ):
        raise RuntimeError("Isolated Listings test caller target check failed")
