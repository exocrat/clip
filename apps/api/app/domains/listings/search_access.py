"""Real Listings operations supplied to Search by the application startup code.

All SQL stays in Listings. Search supplies only its own saved-page IDs and never
receives owner, selection, upload, object-key or other management fields.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, Error as DatabaseError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import (
    AvailableListingQuery,
    Category,
    CategoryDisplay,
    ListingSummary,
    SaveTargetResult,
    SavedListingState,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
from app.core.pagination import Page
from app.domains.listings.browse import ListingsBrowseService, PublicBrowseIdentity
from app.domains.listings.browse_store import _SUMMARY_SELECT_SQL
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.public import ListingsPublic
from app.domains.listings.service import ListingsIdentity


class ListingsSearchAccess(ListingsPublic):
    """Implement the five reviewed Listings calls over the shared app database."""

    def __init__(
        self,
        pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]],
        store: PostgresListingsStore,
        sensitive_price_threshold_paise: int,
        identity: ListingsIdentity | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Borrow existing resources; explicit test identity is supplied by tests only."""
        self.pool, self.store = pool, store
        self.identity = PublicBrowseIdentity() if identity is None else identity
        self.clock = clock
        self.threshold = min(
            sensitive_price_threshold_paise, ((2**63 - 1) // 100) * 100
        )
        self.browse = ListingsBrowseService(store, self.identity, clock)

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[AsyncConnection[dict[str, Any]]]:
        """Bound reads and hide database diagnostics behind the shared safe error."""
        try:
            async with self.pool.connection(timeout=5) as connection:
                async with connection.transaction():
                    await connection.execute("SET LOCAL statement_timeout='5s'")
                    await connection.execute("SET LOCAL lock_timeout='1s'")
                    yield connection
        except DatabaseError, PoolTimeout, TimeoutError:
            raise PublicError(ERRORS[503]) from None

    async def authorize(self, caller: CallerContext) -> datetime:
        """Require current trusted context and live eligibility for either account class."""
        now = self.clock()
        caller.require_current(now)
        if not await self.identity.account_is_eligible(caller.user_id):
            raise PublicError(ERRORS[403])
        return now

    async def query_available_listings(
        self, caller: CallerContext, request: AvailableListingQuery
    ) -> Page[ListingSummary]:
        """Use the same authorized search, availability and paging as GET /listings."""
        return await self.browse.query_available_listings(caller, request)

    async def read_active_categories(self) -> tuple[Category, ...]:
        """Reuse the real ordered catalogue for new Wanted Request assignments."""
        return tuple((await self.store.read_catalogue()).categories)

    async def read_category_display(
        self, codes: tuple[str, ...]
    ) -> tuple[CategoryDisplay, ...]:
        """Resolve retained category labels, including inactive catalogue entries."""
        if not codes:
            return ()
        async with self.connection() as connection:
            rows = await (
                await connection.execute(
                    "SELECT code,label,active FROM listings.categories WHERE code=ANY(%s::text[]) ORDER BY code",
                    (list(set(codes)),),
                )
            ).fetchall()
        if {row["code"] for row in rows} != set(codes):
            raise PublicError(ERRORS[503])
        return tuple(CategoryDisplay.model_validate(row) for row in rows)

    @asynccontextmanager
    async def conversation_write_guard(
        self, caller: CallerContext, listing_id: UUID
    ) -> AsyncIterator[bool]:
        """Keep live availability stable until the caller finishes its write."""
        await self.authorize(caller)
        async with self.store.listing_offer_guard(listing_id) as listing:
            now = self.clock()
            yield bool(
                listing is not None
                and listing.availability == "available"
                and listing.available_from <= now
                and (listing.available_until is None or now < listing.available_until)
            )

    async def read_save_target(
        self, caller: CallerContext, listing_id: UUID
    ) -> SaveTargetResult:
        """Check current discoverability without returning listing content or ownership."""
        now = await self.authorize(caller)
        async with self.connection() as connection:
            row = await (
                await connection.execute(
                    """SELECT EXISTS(SELECT 1 FROM listings.sale_listings
                WHERE id=%s AND retired_at IS NULL
                  AND retirement_pending_operation_id IS NULL
                  AND availability='available' AND available_from<=%s
                  AND (available_until IS NULL OR available_until>%s)) AS discoverable""",
                    (listing_id, now, now),
                )
            ).fetchone()
        if row is None:
            raise PublicError(ERRORS[503])
        return SaveTargetResult(listing_id=listing_id, discoverable=row["discoverable"])

    async def read_saved_listing_summaries(
        self, caller: CallerContext, listing_ids: tuple[UUID, ...]
    ) -> tuple[SavedListingState, ...]:
        """Resolve at most 100 saved IDs in one snapshot; retired content stays absent.

        Search must obtain these IDs from this caller's saved page. Listings does
        not inspect Search tables. Pending retirement or missing origin metadata
        fails the page instead of returning content or inventing retired state.
        """
        await self.authorize(caller)
        if len(listing_ids) > 100:
            raise PublicError(ERRORS[422])
        if not listing_ids:
            return ()
        statement = (
            """WITH requested AS (
            SELECT id,position FROM unnest(%s::uuid[]) WITH ORDINALITY AS ids(id,position)
        ) SELECT requested.id AS requested_id,origin.id AS origin_id,
            origin.retired_at IS NOT NULL AS retired,
            origin.retirement_pending_operation_id IS NOT NULL AS pending,
            summary.*
        FROM requested
        LEFT JOIN listings.sale_listings AS origin ON origin.id=requested.id
        LEFT JOIN LATERAL ("""
            + _SUMMARY_SELECT_SQL
            + """
            WHERE listing.id=requested.id AND listing.retired_at IS NULL
              AND listing.retirement_pending_operation_id IS NULL
        ) AS summary ON true ORDER BY requested.position"""
        )
        async with self.connection() as connection:
            rows = await (
                await connection.execute(statement, (list(listing_ids), self.threshold))
            ).fetchall()
        states = []
        for row in rows:
            if row["origin_id"] is None or row["pending"]:
                raise PublicError(ERRORS[503])
            retired = row["retired"]
            summary = (
                None
                if retired
                else ListingSummary.model_validate(
                    {name: row[name] for name in ListingSummary.model_fields}
                )
            )
            states.append(
                SavedListingState(
                    listing_id=row["requested_id"], listing=summary, retired=retired
                )
            )
        return tuple(states)
