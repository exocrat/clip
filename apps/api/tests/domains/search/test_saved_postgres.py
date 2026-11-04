"""Real Search saved persistence/HTTP with reviewed Listings state scripts.

Listings target/resolver providers are still missing; snapshots here are explicit
fixtures, not a replacement upstream implementation or real integration proof.
Only the verified runner's owned database may be seeded or changed.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI
import httpx2
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.contracts.domain_types import (
    ListingSummary,
    SaveTargetResult,
    SavedListingState,
)
from app.core.auth import CallerContext, require_caller
from app.core.errors import install_error_handlers
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.search.saved import SavedService
from app.domains.search.saved_store import PostgresSavedStore
from app.domains.search.saved_routes import router, saved_service
from apps.api.tests.domains.listings.test_embedding_postgres import (
    connect,
    target,
    seed_listing,
    retire,
)
from apps.api.tests.domains.listings.test_hybrid_read_postgres import live_listing
from apps.api.tests.domains.search.test_wanted_postgres import Dependencies
from apps.api.tests.domains.search.doubles.saved_listings import SavedListingsDouble


def test_native_saved_private_pairs_pages_transitions_retries_and_race():
    asyncio.run(exercise(target()))


async def exercise(value):
    """Keep owned immutable origins; remove only retired image fixture metadata."""
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
        actors = [uuid4(), uuid4()]
        identifiers = []
        async with pool.connection() as connection:
            await connection.execute(
                "INSERT INTO identity.users(id,account_class,status,display_name,activated_at,expires_at) VALUES"
                "(%s,'regular','active','Synthetic saved owner',NULL,NULL),"
                "(%s,'temporary','active','Synthetic temporary saver',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP+interval '336 hours')",
                tuple(actors),
            )
            for index in range(23):
                identifiers.append(
                    await live_listing(
                        connection,
                        964000 + index,
                        now,
                        "Synthetic saved " + str(index),
                        "Controlled saved fixture",
                        price=10000,
                    )
                )
        listing_store = PostgresListingsStore(pool, 500000)
        provider = SavedListingsDouble()

        async def snapshot(identifier):
            """Prepare a public fixture from this owned source's actual current row.

            This explicit test setup is not the missing public resolver. Runtime
            fixture methods return only scripts and never query private tables.
            """
            view = await listing_store.read_listing(identifier)
            assert view is not None
            return ListingSummary.model_validate(
                view.model_dump(include=set(ListingSummary.model_fields))
            )

        for identifier in identifiers:
            provider.targets[identifier] = SaveTargetResult(
                listing_id=identifier, discoverable=True
            )
            provider.states[identifier] = SavedListingState(
                listing_id=identifier, listing=await snapshot(identifier), retired=False
            )
        identity = Dependencies(set(actors))
        store = PostgresSavedStore(pool)
        service = SavedService(store, provider, identity)
        current = [
            CallerContext(
                actors[0], "regular", datetime.now(UTC) + timedelta(minutes=5)
            )
        ]
        app = FastAPI()
        install_error_handlers(app)
        app.include_router(router)
        app.dependency_overrides[require_caller] = lambda: current[0]
        app.dependency_overrides[saved_service] = lambda: service
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = identifiers[0]
            path = "/me/saved-listings/" + str(first)

            async def put(identifier):
                """Use distinct retry UUIDs to prove pair-level idempotency."""
                return await client.put(
                    "/me/saved-listings/" + str(identifier),
                    json={"operation_id": str(uuid4())},
                )

            results = await asyncio.gather(*[put(first) for _ in range(3)])
            assert all(result.status_code == 200 for result in results)
            original = results[0].json()
            assert all(result.json() == original for result in results)
            assert set(original) == {"listing_id", "saved_at"}
            statuses = await client.get(
                "/me/saved-listings/status",
                params=[
                    ("listing_ids", str(first)),
                    ("listing_ids", str(identifiers[1])),
                ],
            )
            assert statuses.status_code == 200
            assert statuses.json()["items"] == [
                {"listing_id": str(first), "saved": True},
                {"listing_id": str(identifiers[1]), "saved": False},
            ]
            assert statuses.headers["cache-control"] == "private, no-store"
            current[0] = CallerContext(
                actors[1], "temporary", datetime.now(UTC) + timedelta(minutes=5)
            )
            assert (await client.get("/me/saved-listings")).json()["items"] == []
            assert (await put(first)).status_code == 200
            current[0] = CallerContext(
                actors[0], "regular", datetime.now(UTC) + timedelta(minutes=5)
            )
            async with pool.connection() as connection:
                await connection.execute(
                    "UPDATE listings.sale_listings SET availability='unavailable' WHERE id=%s",
                    (first,),
                )
            provider.targets[first] = SaveTargetResult(
                listing_id=first, discoverable=False
            )
            provider.states[first] = SavedListingState(
                listing_id=first, listing=await snapshot(first), retired=False
            )
            view = await client.get("/me/saved-listings")
            assert (
                view.status_code == 200
                and view.json()["items"][0]["listing"]["availability"] == "unavailable"
            )
            assert view.headers["cache-control"] == "private, no-store"
            provider.fail = True
            assert (await client.get("/me/saved-listings")).status_code == 503
            assert (await put(first)).json() == original
            removed = await client.delete(path)
            assert removed.status_code == 204 and removed.content == b""
            assert (await client.delete(path)).status_code == 204
            provider.fail = False
            assert (await client.get("/me/saved-listings")).json()["items"] == []
            assert (await put(first)).status_code == 404
            current[0] = CallerContext(
                actors[1], "temporary", datetime.now(UTC) + timedelta(minutes=5)
            )
            assert (await client.get("/me/saved-listings")).json()["items"][0][
                "listing_id"
            ] == str(first)
            current[0] = CallerContext(
                actors[0], "regular", datetime.now(UTC) + timedelta(minutes=5)
            )
            assert (
                await client.get("/me/saved-listings?user_id=" + str(actors[1]))
            ).status_code == 422
            assert (
                await client.put(
                    path, json={"operation_id": str(uuid4()), "user_id": str(actors[1])}
                )
            ).status_code == 422

            bulk = identifiers[1:22]
            assert all(
                result.status_code == 200
                for result in await asyncio.gather(
                    *[put(identifier) for identifier in bulk]
                )
            )
            async with pool.connection() as connection:
                await connection.execute(
                    "UPDATE search.saved_listings SET created_at=%s WHERE user_id=%s",
                    (now, actors[0]),
                )
            page1 = (await client.get("/me/saved-listings")).json()
            page2 = (await client.get("/me/saved-listings?page=2")).json()
            expected = sorted(bulk, reverse=True)
            assert [row["listing_id"] for row in page1["items"] + page2["items"]] == [
                str(identifier) for identifier in expected
            ]
            assert page1["has_next"] is True and page2["has_next"] is False
            calls = [call for call in provider.calls if call[0] == "summaries"]
            assert calls[-2] == ("summaries", actors[0], tuple(expected[:20]))
            assert calls[-1] == ("summaries", actors[0], tuple(expected[20:]))
            provider.fail = True
            assert (await client.get("/me/saved-listings")).status_code == 503
            provider.fail = False

            # Explicitly schedule availability change after a successful target
            # snapshot, before its response reaches Search. That race is allowed.
            racing = identifiers[22]
            provider.pause_target = racing
            task = asyncio.create_task(put(racing))
            try:
                await asyncio.wait_for(provider.target_checked.wait(), timeout=2)
                async with pool.connection() as connection:
                    await connection.execute(
                        "UPDATE listings.sale_listings SET availability='unavailable' WHERE id=%s",
                        (racing,),
                    )
                provider.targets[racing] = SaveTargetResult(
                    listing_id=racing, discoverable=False
                )
                provider.states[racing] = SavedListingState(
                    listing_id=racing, listing=await snapshot(racing), retired=False
                )
                provider.resume_target.set()
                assert (await asyncio.wait_for(task, timeout=5)).status_code == 200
                assert await store.existing(actors[0], racing) is not None
            finally:
                provider.resume_target.set()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)

            # Seed a historical save of an old unavailable source, then exercise
            # real parent retirement. Public resolver output remains an explicit
            # current-state fixture; no shadow upstream resolver is implemented.
            async with pool.connection() as connection:
                retired = await seed_listing(connection, 964100, now=now)
                await connection.execute(
                    "INSERT INTO search.saved_listings(user_id,listing_id,created_at) VALUES(%s,%s,%s)",
                    (actors[0], retired, now - timedelta(days=199)),
                )
                await retire(connection, retired)
            provider.targets[retired] = SaveTargetResult(
                listing_id=retired, discoverable=False
            )
            provider.states[retired] = SavedListingState(
                listing_id=retired, listing=None, retired=True
            )
            saved = (await client.get("/me/saved-listings?page_size=100")).json()[
                "items"
            ]
            marker = next(row for row in saved if row["listing_id"] == str(retired))
            assert (
                set(marker) == {"listing_id", "saved_at", "listing", "retired"}
                and marker["listing"] is None
                and marker["retired"] is True
            )
            assert await store.existing(actors[0], retired) is not None
            assert (
                await client.delete("/me/saved-listings/" + str(retired))
            ).status_code == 204
            assert (
                await client.delete("/me/saved-listings/" + str(retired))
            ).status_code == 204
            assert await store.existing(actors[0], retired) is None
            assert (
                await client.get("/me/saved-listings?page_size=21")
            ).status_code == 422
    finally:
        try:
            if retired is not None:
                # No object existed; isolate only this owned retired fixture's
                # metadata from other cleanup tests, keeping immutable parents.
                async with pool.connection() as connection:
                    rows = await (
                        await connection.execute(
                            "DELETE FROM listings.images WHERE listing_id=%s AND retired_at IS NOT NULL RETURNING upload_id",
                            (retired,),
                        )
                    ).fetchall()
                    if rows:
                        await connection.execute(
                            "DELETE FROM listings.image_uploads WHERE id=ANY(%s)",
                            ([row["upload_id"] for row in rows],),
                        )
        finally:
            await pool.close()
