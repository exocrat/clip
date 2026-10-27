"""Actual owner services/SQL with synthetic HTTP auth on the disposable DB.

Real cookie sessions belong to the next integration checkpoint. These tests do
not substitute thread fixtures for the Listing start command being exercised.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient
import psycopg
from psycopg.errors import LockNotAvailable
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
import pytest

from app.contracts.domain_types import (
    AvailabilityChange,
    ExistingListingConversationLookup,
)
from app.core.auth import require_caller
from app.core.errors import PublicError, install_error_handlers
from app.core.runtime_bindings import runtime_scope
from app.domains.conversations.provider import PostgresConversationServices
from app.domains.identity.capabilities import PostgresCapabilities
from app.domains.listings.integrations import PublicListingsIdentity
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.routes import router
from app.domains.listings.service import ListingsService
from test_thread_creation import (
    TEST_DATABASE_DSN,
    caller,
    run_scenario,
    seed_users_and_listing,
)

pytestmark = pytest.mark.skipif(
    TEST_DATABASE_DSN is None,
    reason="run through the disposable Conversations database harness",
)


@asynccontextmanager
async def environment(
    pool, *, temporary=False, provider_type=PostgresConversationServices
):
    """Own the dictionary pool; bind actual Identity eligibility for both domains."""
    owner, buyer, listing = await seed_users_and_listing(
        pool, temporary_buyer=temporary
    )
    identity = PostgresCapabilities(
        lambda: psycopg.connect(TEST_DATABASE_DSN), lambda: datetime.now(UTC)
    )
    async with AsyncConnectionPool(
        TEST_DATABASE_DSN,
        kwargs={"row_factory": dict_row},
        min_size=0,
        max_size=4,
        open=False,
    ) as origin_pool:
        store = PostgresListingsStore(origin_pool, 10000)
        provider = provider_type(pool)
        service = ListingsService(
            store, PublicListingsIdentity(), conversations=provider
        )
        actor = caller(buyer, "temporary" if temporary else "regular")
        app = FastAPI()
        install_error_handlers(app)
        app.include_router(router)
        app.state.listings_store = store
        app.state.listings_identity = PublicListingsIdentity()
        app.state.listings_conversations = provider
        app.dependency_overrides[require_caller] = lambda: actor
        with runtime_scope(
            {"identity.check_account_eligibility": identity.check_account_eligibility}
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield SimpleNamespace(
                    app=app,
                    owner=owner,
                    buyer=buyer,
                    listing=listing,
                    store=store,
                    provider=provider,
                    service=service,
                    actor=actor,
                    client=client,
                )


async def close(state):
    """Use the real owner command to change availability."""
    view = await state.store.read_listing(state.listing)
    await state.service.change_availability(
        caller(state.owner),
        state.listing,
        AvailabilityChange(
            expected_revision=view.revision,
            availability="unavailable",
            available_from=view.available_from,
            available_until=view.available_until,
            operation_id=uuid4(),
        ),
    )


@pytest.mark.parametrize("temporary", [False, True])
def test_http_create_reopen_and_unavailable_pair_isolation(temporary):
    async def scenario(pool):
        async with environment(pool, temporary=temporary) as state:
            url = f"/listings/{state.listing}/conversations"
            body = {"operation_id": str(uuid4())}
            assert (await state.client.post(url, json={})).status_code == 422
            assert (
                await state.client.post(url, json=body | {"owner_id": str(state.owner)})
            ).status_code == 422
            created = await state.client.post(url, json=body)
            assert created.status_code == 201
            repeat = await state.client.post(url, json=body)
            assert repeat.status_code == 200 and not repeat.json()["created"]
            assert repeat.json()["conversation_id"] == created.json()["conversation_id"]
            await close(state)
            reopened = await state.client.post(url, json=body)
            assert reopened.status_code == 200 and reopened.json() == repeat.json()
            async with pool.connection() as connection:
                assert (
                    await (
                        await connection.execute(
                            "SELECT count(*) FROM conversations.threads WHERE listing_id=%s",
                            (state.listing,),
                        )
                    ).fetchone()
                )[0] == 1
                assert (
                    await (
                        await connection.execute(
                            "SELECT count(*) FROM conversations.notification_intents WHERE conversation_id=%s",
                            (UUID(created.json()["conversation_id"]),),
                        )
                    ).fetchone()
                )[0] == 1
            assert (
                await state.provider.find_existing_listing_conversation(
                    caller(state.owner),
                    ExistingListingConversationLookup(listing_id=state.listing),
                )
                is None
            )
            _, stranger, _ = await seed_users_and_listing(pool)
            with pytest.raises(PublicError) as absent:
                await state.service.start_conversation(caller(stranger), state.listing)
            assert absent.value.spec.status == 404
            with pytest.raises(PublicError) as self_chat:
                await state.service.start_conversation(
                    caller(state.owner), state.listing
                )
            assert self_chat.value.spec.status == 403
            async with pool.connection() as connection:
                await connection.execute(
                    "UPDATE listings.sale_listings SET retirement_pending_operation_id=%s,retirement_pending_cutoff_utc=clock_timestamp() WHERE id=%s",
                    (uuid4(), state.listing),
                )
            assert (await state.client.post(url, json=body)).status_code == 404

    run_scenario(scenario)


def test_concurrent_calls_create_one_pair():
    async def scenario(pool):
        async with environment(pool) as state:
            results = await asyncio.gather(
                *(
                    state.service.start_conversation(state.actor, state.listing)
                    for _ in range(2)
                )
            )
            assert sorted(result.created for result in results) == [False, True]
            assert results[0].conversation_id == results[1].conversation_id

    run_scenario(scenario)


def test_guard_serializes_owner_change_without_blocking_thread_fk():
    class PausedProvider(PostgresConversationServices):
        """Pause after the origin lock, before the real independent thread insert."""

        def __init__(self, pool):
            super().__init__(pool)
            self.entered, self.release = asyncio.Event(), asyncio.Event()

        async def open_or_create_listing_conversation(self, actor, request):
            self.entered.set()
            await self.release.wait()
            return await super().open_or_create_listing_conversation(actor, request)

    async def scenario(pool):
        async with environment(pool, provider_type=PausedProvider) as state:
            task = asyncio.create_task(
                state.service.start_conversation(state.actor, state.listing)
            )
            try:
                await asyncio.wait_for(state.provider.entered.wait(), timeout=1)
                async with pool.connection() as connection:
                    with pytest.raises(LockNotAvailable):
                        async with connection.transaction():
                            await connection.execute(
                                "SELECT id FROM listings.sale_listings WHERE id=%s FOR UPDATE NOWAIT",
                                (state.listing,),
                            )
            finally:
                state.provider.release.set()
            assert (await task).created
            await close(state)

    run_scenario(scenario)


def test_closed_first_never_creates_and_revoked_buyer_is_denied():
    async def scenario(pool):
        async with environment(pool) as state:
            await close(state)
            url = f"/listings/{state.listing}/conversations"
            assert (
                await state.client.post(url, json={"operation_id": str(uuid4())})
            ).status_code == 404
            async with pool.connection() as connection:
                assert (
                    await (
                        await connection.execute(
                            "SELECT count(*) FROM conversations.threads WHERE listing_id=%s",
                            (state.listing,),
                        )
                    ).fetchone()
                )[0] == 0
                await connection.execute(
                    "UPDATE identity.users SET status='revoked',revoked_at=clock_timestamp() WHERE id=%s",
                    (state.buyer,),
                )
            assert (
                await state.client.post(url, json={"operation_id": str(uuid4())})
            ).status_code == 403

    run_scenario(scenario)
