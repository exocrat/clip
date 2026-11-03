"""Private saved references in Search-owned SQL; no listing-content cache/join."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, Error as DatabaseError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import SavedListingAck
from app.core.errors import ERRORS, PublicError
from app.domains.search.wanted_models import WantedPage


class PostgresSavedStore:
    """Share an injected pool; scope every SQL operation to the trusted actor."""

    def __init__(self, pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]]):
        """Own neither connection configuration nor pool startup/shutdown."""
        self.pool = pool

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[AsyncConnection[dict[str, Any]]]:
        """Bound connection/SQL/lock waits; suppress raw database diagnostics."""
        try:
            async with self.pool.connection(timeout=5) as connection:
                async with connection.transaction():
                    await connection.execute("SET LOCAL statement_timeout='5s'")
                    await connection.execute("SET LOCAL lock_timeout='1s'")
                    yield connection
        except DatabaseError, PoolTimeout:
            raise PublicError(ERRORS[503]) from None

    async def existing(self, actor: UUID, identifier: UUID) -> SavedListingAck | None:
        """Read only this actor's pair; duplicate PUT preserves its original time."""
        async with self.connection() as connection:
            row = await (
                await connection.execute(
                    "SELECT listing_id,created_at AS saved_at FROM search.saved_listings WHERE user_id=%s AND listing_id=%s",
                    (actor, identifier),
                )
            ).fetchone()
        return None if row is None else SavedListingAck.model_validate(row)

    async def saved_ids(self, actor: UUID, identifiers: list[UUID]) -> set[UUID]:
        """Read only the current actor's requested pairs in one bounded query."""
        async with self.connection() as connection:
            rows = await (
                await connection.execute(
                    "SELECT listing_id FROM search.saved_listings WHERE user_id=%s AND listing_id=ANY(%s)",
                    (actor, identifiers),
                )
            ).fetchall()
        return {row["listing_id"] for row in rows}

    async def save(self, actor: UUID, identifier: UUID) -> SavedListingAck:
        """Serialize pair writes and keep first timestamp even across concurrent PUTs."""
        async with self.connection() as connection:
            await connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,18))",
                (f"{actor}/{identifier}",),
            )
            await connection.execute(
                "INSERT INTO search.saved_listings(user_id,listing_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
                (actor, identifier),
            )
            row = await (
                await connection.execute(
                    "SELECT listing_id,created_at AS saved_at FROM search.saved_listings WHERE user_id=%s AND listing_id=%s",
                    (actor, identifier),
                )
            ).fetchone()
            if row is None:
                raise PublicError(ERRORS[503])
            return SavedListingAck.model_validate(row)

    async def unsave(self, actor: UUID, identifier: UUID) -> None:
        """Delete only caller's pair; absent pairs are successful no-ops."""
        async with self.connection() as connection:
            await connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,18))",
                (f"{actor}/{identifier}",),
            )
            await connection.execute(
                "DELETE FROM search.saved_listings WHERE user_id=%s AND listing_id=%s",
                (actor, identifier),
            )

    async def page(
        self, actor: UUID, page: WantedPage
    ) -> tuple[list[SavedListingAck], bool]:
        """Filter actor before stable pagination; expose only actual page IDs upstream."""
        async with self.connection() as connection:
            rows = await (
                await connection.execute(
                    "SELECT listing_id,created_at AS saved_at FROM search.saved_listings WHERE user_id=%s "
                    "ORDER BY created_at DESC,listing_id DESC LIMIT %s OFFSET %s",
                    (actor, page.page_size + 1, (page.page - 1) * page.page_size),
                )
            ).fetchall()
        return [
            SavedListingAck.model_validate(row) for row in rows[: page.page_size]
        ], len(rows) > page.page_size
