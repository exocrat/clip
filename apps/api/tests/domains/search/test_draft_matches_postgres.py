"""Real available-query/HTTP draft matching on the owned private native database.

Matching uses synthetic Identity. The independent wanted-submit probe also uses
an explicit reviewed catalogue fixture. The Listings adapter uses the real owned
browse service/store, native indexed matching and current availability predicate.
Test fixture seeding may access upstream rows; Search application code may not.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI
import httpx2
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.auth import CallerContext, require_caller
from app.core.errors import install_error_handlers
from app.domains.listings.browse import ListingsBrowseService
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.search.draft_matches import DraftMatchService
from app.domains.search.wanted import WantedService
from app.domains.search.wanted_store import PostgresWantedStore
from app.domains.search.wanted_routes import router, draft_match_service, wanted_service
from apps.api.tests.domains.listings.test_embedding_postgres import (
    connect,
    target,
    seed_listing,
    retire,
)
from apps.api.tests.domains.listings.test_hybrid_read_postgres import live_listing
from apps.api.tests.domains.search.test_wanted_postgres import Dependencies


class Identity:
    """One eligible fixture actor through each domain's reviewed auth signature."""

    def __init__(self, actor):
        self.actor = actor

    async def eligible(self, actor):
        return actor == self.actor

    async def account_is_eligible(self, actor):
        return actor == self.actor


class NativeAvailableQuery:
    """Adapt the real Listings implementation to its public query signature."""

    def __init__(self, service):
        self.service = service
        self.calls = []
        self.fail = False

    async def query_available_listings(self, caller, request):
        """Record only controlled test inputs; run real SQL rather than ranking fake."""
        self.calls.append(request)
        if self.fail:
            raise TimeoutError("controlled draft-query failure")
        return await self.service.query_available_listings(caller, request)


def test_native_draft_matches_real_availability_order_limit_and_no_persistence():
    asyncio.run(exercise(target()))


async def exercise(value):
    """Seed image-backed fixtures and verify HTTP while retaining owned origins."""
    async with await connect(value):
        pass
    pool = AsyncConnectionPool[AsyncConnection[dict]](
        value, kwargs={"row_factory": dict_row}, min_size=1, max_size=4, open=False
    )
    await pool.open()
    retired = None
    try:
        await pool.wait(timeout=5)
        now = datetime.now(UTC)
        actor = uuid4()
        identifiers = []
        async with pool.connection() as connection:
            await connection.execute(
                "INSERT INTO identity.users(id,account_class,status,display_name) VALUES(%s,'regular','active','Synthetic draft actor')",
                (actor,),
            )
            for index in range(21):
                identifier = await live_listing(
                    connection,
                    963000 + index,
                    now,
                    (
                        "Nebulaprism " + str(index)
                        if index != 20
                        else "Synthetic description-only match"
                    ),
                    (
                        "Controlled description"
                        if index != 20
                        else "Nebulaprism descriptionuniquefixture"
                    ),
                    price=10000 + index * 100,
                )
                identifiers.append(identifier)
            for index, status in enumerate(
                ["unavailable", "future", "ended", "pending"]
            ):
                await live_listing(
                    connection,
                    963100 + index,
                    now,
                    "Nebulaprism hidden " + status,
                    "Controlled hidden fixture",
                    status=status,
                )
            retired = await seed_listing(connection, 963200, now=now)
            await retire(connection, retired)
        identity = Identity(actor)
        provider = NativeAvailableQuery(
            ListingsBrowseService(
                PostgresListingsStore(pool, 500000), identity, clock=lambda: now
            )
        )
        matches = DraftMatchService(provider, identity)
        app = FastAPI()
        install_error_handlers(app)
        app.include_router(router)
        app.dependency_overrides[require_caller] = lambda: CallerContext(
            actor, "regular", datetime.now(UTC) + timedelta(minutes=5)
        )
        app.dependency_overrides[draft_match_service] = lambda: matches
        app.dependency_overrides[wanted_service] = lambda: WantedService(
            PostgresWantedStore(pool), Dependencies({actor})
        )

        async def counts():
            """Read all Search table counts to catch hidden draft/history side effects."""
            async with pool.connection() as connection:
                return await (
                    await connection.execute(
                        "SELECT (SELECT count(*) FROM search.wanted_requests) AS wanted,(SELECT count(*) FROM search.wanted_command_results) AS commands,(SELECT count(*) FROM search.saved_listings) AS saves"
                    )
                ).fetchone()

        before = await counts()
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/wanted-requests/draft-matches",
                json={"draft_title": "  Nebulaprism  "},
            )
            assert response.status_code == 200, response.text
            result = response.json()
            expected = sorted(identifiers, reverse=True)[:20]
            assert [row["listing_id"] for row in result["items"]] == [
                str(identifier) for identifier in expected
            ]
            assert result["has_more"] is True and len(result["items"]) == 20
            assert all(row["availability"] == "available" for row in result["items"])
            assert all(
                row["category_code"] == "bicycles" and row["asking_price_paise"] > 0
                for row in result["items"]
            )
            assert all(
                "owner_id" not in row and "revision" not in row and "score" not in row
                for row in result["items"]
            )
            assert response.headers["cache-control"] == "private, no-store"
            # Description-only source is still searchable by the title query.
            description = await client.post(
                "/wanted-requests/draft-matches",
                json={"draft_title": "descriptionuniquefixture"},
            )
            assert (
                description.status_code == 200 and len(description.json()["items"]) == 1
            )
            absent = await client.post(
                "/wanted-requests/draft-matches",
                json={"draft_title": "neverseencometfixture"},
            )
            assert absent.json() == {"items": [], "has_more": False}
            assert await counts() == before
            provider.fail = True
            failure = await client.post(
                "/wanted-requests/draft-matches", json={"draft_title": "Nebulaprism"}
            )
            assert failure.status_code == 503 and await counts() == before
            # Submission remains independent of matching success/failure and does
            # not inherit budget/category filters into the earlier title query.
            created = await client.post(
                "/wanted-requests",
                json=dict(
                    title="Nebulaprism",
                    description="Controlled wanted fixture",
                    category_code="books",
                    budget_paise=0,
                    operation_id=str(uuid4()),
                ),
            )
            assert created.status_code == 201, created.text
            after = await counts()
            assert (
                after["wanted"] == before["wanted"] + 1
                and after["commands"] == before["commands"] + 1
                and after["saves"] == before["saves"]
            )
            query = provider.calls[0]
            assert (
                query.q == "Nebulaprism"
                and query.sort == "created_desc"
                and query.page == 1
                and query.page_size == 20
            )
            assert (
                query.category_code is None
                and query.min_price_paise is None
                and query.max_price_paise is None
            )
    finally:
        try:
            if retired is not None:
                # Only this owned fixture's retired image/upload metadata is
                # removable. No storage object was created. Keep the immutable
                # origin and user references; do not pollute other cleanup tests.
                async with pool.connection() as connection:
                    images = await (
                        await connection.execute(
                            "DELETE FROM listings.images WHERE listing_id=%s AND retired_at IS NOT NULL RETURNING upload_id",
                            (retired,),
                        )
                    ).fetchall()
                    if images:
                        await connection.execute(
                            "DELETE FROM listings.image_uploads WHERE id=ANY(%s)",
                            ([row["upload_id"] for row in images],),
                        )
        finally:
            await pool.close()
