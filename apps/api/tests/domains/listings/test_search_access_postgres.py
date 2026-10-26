"""Real Listings/Search calls and private saved state in the disposable runner.

Only account eligibility is synthetic. Real SQL supplies categories, matching,
save eligibility, unavailable summaries and content-free retired markers.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx2
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
import pytest

from app.core.auth import CallerContext, require_caller
from app.contracts.domain_types import AccountEligibility
from app.core.config import Settings
from app.core.errors import PublicError
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.search_access import ListingsSearchAccess
from apps.api.tests.domains.listings.test_embedding_postgres import (
    connect,
    target,
    seed_listing,
    retire,
)
from apps.api.tests.domains.listings.test_hybrid_read_postgres import live_listing


class Identity:
    """Approve only the two synthetic actors created for this test."""

    def __init__(self, actors):
        """Keep this test's fixed set of approved actors."""
        self.actors = actors

    async def eligible(self, actor):
        """Supply Search's test-only eligibility answer."""
        return actor in self.actors

    async def account_is_eligible(self, actor):
        """Supply the same answer through Listings' eligibility signature."""
        return await self.eligible(actor)


@asynccontextmanager
async def configured_app(value, identity, caller):
    """Run actual app startup/routes; replace only Identity inside this test process."""
    from app import main

    async def eligibility(actor, required_class=None):
        """Replace only the missing Identity operation in this isolated process."""
        return AccountEligibility(eligible=await identity.eligible(actor))

    overrides = dict(main.app.dependency_overrides)
    with (
        patch.object(
            main, "settings", Settings(environment="test", database_url=value)
        ),
        patch("app.domains.identity.public.check_account_eligibility", eligibility),
    ):
        main.app.dependency_overrides[require_caller] = caller
        try:
            async with main.lifespan(main.app):
                assert isinstance(main.app.state.listings_public, ListingsSearchAccess)
                yield main.app
        finally:
            main.app.dependency_overrides.clear()
            main.app.dependency_overrides.update(overrides)


def test_real_listings_search_categories_saved_privacy_and_retirement():
    """Exercise the actual app and SQL while honoring the runner's target guard."""
    asyncio.run(exercise(target()))


async def exercise(value):
    """Keep fixture origins for the runner's own database cleanup; touch no live DB."""
    async with await connect(value):
        pass
    pool = AsyncConnectionPool(value, kwargs={"row_factory": dict_row}, open=False)
    await pool.open()
    try:
        await pool.wait(timeout=5)
        now = datetime.now(UTC)
        actors = (uuid4(), uuid4())
        identity = Identity(actors)
        seed = uuid4().int % 1_000_000_000
        title = f"accessbicycle{seed}"
        inactive = f"inactive-{seed}"
        async with pool.connection() as connection:
            for actor in actors:
                await connection.execute(
                    "INSERT INTO identity.users(id,account_class,status,display_name) VALUES(%s,'regular','active','Synthetic access actor')",
                    (actor,),
                )
            available = await live_listing(
                connection, seed, now, title, "Public bicycle summary"
            )
            unavailable = await seed_listing(connection, seed + 1)
            retired = await seed_listing(connection, seed + 2)
            future = await live_listing(
                connection, seed + 3, now, "Future bicycle", "Fixture", status="future"
            )
            expired = await live_listing(
                connection,
                seed + 4,
                now,
                "Expired bicycle",
                "Fixture",
                status="ended",
            )
            await retire(connection, retired)
            await connection.execute(
                "INSERT INTO listings.categories(id,code,label,active,sensitive_category) VALUES(%s,%s,'Historical category',false,false)",
                (uuid4(), inactive),
            )
        store = PostgresListingsStore(pool, 500000)
        access = ListingsSearchAccess(pool, store, 500000, identity, clock=lambda: now)
        caller = CallerContext(actors[0], "regular", now + timedelta(hours=1))
        assert "bicycles" in {
            item.code for item in await access.read_active_categories()
        }
        assert inactive not in {
            item.code for item in await access.read_active_categories()
        }
        display = await access.read_category_display((inactive, "bicycles", inactive))
        assert len(display) == 2
        assert next(item for item in display if item.code == inactive).active is False
        for identifier, expected in (
            (available, True),
            (unavailable, False),
            (retired, False),
            (future, False),
            (expired, False),
            (uuid4(), False),
        ):
            assert (
                await access.read_save_target(caller, identifier)
            ).discoverable is expected

        states = await access.read_saved_listing_summaries(
            caller, (unavailable, retired, available)
        )
        assert [item.listing_id for item in states] == [unavailable, retired, available]
        assert states[0].listing.availability == "unavailable"
        assert states[1].model_dump() == {
            "listing_id": retired,
            "listing": None,
            "retired": True,
        }
        assert set(states[2].listing.model_dump()).isdisjoint(
            {"owner_id", "revision", "selected_buyer_id", "proof_available"}
        )
        with pytest.raises(PublicError) as failure:
            await access.read_saved_listing_summaries(caller, (uuid4(),))
        assert failure.value.spec.status == 503
        with pytest.raises(PublicError) as failure:
            await access.read_saved_listing_summaries(caller, (available,) * 101)
        assert failure.value.spec.status == 422
        with pytest.raises(PublicError) as failure:
            await access.read_save_target(
                CallerContext(actors[0], "regular", now - timedelta(seconds=1)),
                available,
            )
        assert failure.value.spec.status == 401
        with pytest.raises(PublicError) as failure:
            await access.read_save_target(
                CallerContext(uuid4(), "regular", now + timedelta(hours=1)), available
            )
        assert failure.value.spec.status == 403

        # Use normal startup, real Listings/Search stores and unmodified routes.
        async with (
            configured_app(value, identity, lambda: caller) as app,
            httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app), base_url="http://testserver"
            ) as client,
        ):
            response = await client.post(
                "/wanted-requests/draft-matches", json={"draft_title": title}
            )
            assert response.status_code == 200, response.text
            assert available in {
                UUID(item["listing_id"]) for item in response.json()["items"]
            }
            body = {
                "title": "Bicycle wanted",
                "description": "Synthetic request",
                "category_code": "bicycles",
                "operation_id": str(uuid4()),
            }
            response = await client.post("/wanted-requests", json=body)
            assert response.status_code == 201, response.text
            assert response.json()["category_label"] == "Bicycles"
            request_id = response.json()["request_id"]
            displayed = await client.get(f"/wanted-requests/{request_id}")
            assert displayed.status_code == 200, displayed.text
            assert displayed.json()["category_label"] == "Bicycles"
            response = await client.post(
                "/wanted-requests",
                json={**body, "category_code": inactive, "operation_id": str(uuid4())},
            )
            assert response.status_code == 422
            path = f"/me/saved-listings/{available}"
            first = await client.put(path, json={"operation_id": str(uuid4())})
            assert first.status_code == 200, first.text
            retry = await client.put(path, json={"operation_id": str(uuid4())})
            assert retry.json() == first.json()
            assert (
                await client.put(
                    f"/me/saved-listings/{unavailable}",
                    json={"operation_id": str(uuid4())},
                )
            ).status_code == 404
            caller = CallerContext(actors[1], "regular", now + timedelta(hours=1))
            assert (await client.get("/me/saved-listings")).json()["items"] == []
            assert (await client.delete(path)).status_code == 204
            caller = CallerContext(actors[0], "regular", now + timedelta(hours=1))
            page = await client.get("/me/saved-listings")
            assert len(page.json()["items"]) == 1
            assert page.json()["items"][0]["listing"]["title"] == title
            async with pool.connection() as connection:
                await connection.execute(
                    "INSERT INTO search.saved_listings(user_id,listing_id) VALUES(%s,%s)",
                    (caller.user_id, retired),
                )
            retired_page = (await client.get("/me/saved-listings")).json()["items"]
            marker = next(
                item for item in retired_page if item["listing_id"] == str(retired)
            )
            assert marker["retired"] is True and marker["listing"] is None
            assert (
                await client.delete(f"/me/saved-listings/{retired}")
            ).status_code == 204
            async with pool.connection() as connection:
                await connection.execute(
                    "UPDATE listings.sale_listings SET availability='unavailable' WHERE id=%s",
                    (available,),
                )
            page = await client.get("/me/saved-listings")
            assert page.json()["items"][0]["listing"]["availability"] == "unavailable"
            assert (
                await client.put(path, json={"operation_id": str(uuid4())})
            ).json() == first.json()
            assert (await client.delete(path)).status_code == 204
            assert (await client.get("/me/saved-listings")).json()["items"] == []
            assert (await client.delete(path)).status_code == 204
        async with pool.connection() as connection:
            await connection.execute(
                "UPDATE listings.sale_listings SET retirement_pending_operation_id=%s,retirement_pending_cutoff_utc=%s WHERE id=%s",
                (uuid4(), now - timedelta(days=90), unavailable),
            )
        with pytest.raises(PublicError) as failure:
            await access.read_saved_listing_summaries(caller, (unavailable,))
        assert failure.value.spec.status == 503
    finally:
        await pool.close()
