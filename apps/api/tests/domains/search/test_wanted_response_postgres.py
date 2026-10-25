"""Actual Search response/close locking and HTTP, with public C outcome scripts.

A separate schema-only thread fixture probes FK lock compatibility; it is not
an implementation of Conversations' public operation, uniqueness or membership.
All identifiers and records belong to the runner's fresh private database.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI
import httpx2

from app.core.auth import CallerContext, require_caller
from app.domains.search.wanted_models import WantedCreate, WantedState
from app.domains.search.wanted_routes import router, response_service
from app.domains.search.wanted_response import WantedResponseService
from app.domains.search.wanted_retirement import WantedRetirementService
from app.core.errors import install_error_handlers
from apps.api.tests.domains.search.test_wanted_retirement_postgres import harness
from apps.api.tests.domains.search.test_wanted_postgres import Dependencies
from apps.api.tests.domains.search.doubles.wanted_response import (
    ConversationsResponseDouble,
)
from apps.api.tests.domains.search.doubles.wanted_retirement import (
    ConversationsRetirementDouble,
)


def test_native_wanted_response_auth_retry_closure_and_origin_locking():
    asyncio.run(exercise())


async def exercise():
    """Prove only Search-owned semantics; actual public C integration stays pending."""
    async with harness() as h:
        responders = [uuid4(), uuid4(), uuid4()]
        async with h.pool.connection() as connection:
            for index, actor in enumerate(responders):
                await connection.execute(
                    "INSERT INTO identity.users(id,account_class,status,display_name,activated_at,expires_at) VALUES(%s,%s,'active','Synthetic response actor',"
                    "CASE WHEN %s THEN CURRENT_TIMESTAMP END,CASE WHEN %s THEN CURRENT_TIMESTAMP+interval '336 hours' END)",
                    (
                        actor,
                        "temporary" if index == 2 else "regular",
                        index == 2,
                        index == 2,
                    ),
                )
        identity = Dependencies(set(responders) | {h.author})
        provider = ConversationsResponseDouble()
        service = WantedResponseService(h.store, provider, identity)
        current = [
            CallerContext(
                responders[0], "regular", datetime.now(UTC) + timedelta(minutes=5)
            )
        ]
        app = FastAPI()
        install_error_handlers(app)
        app.include_router(router)
        app.dependency_overrides[require_caller] = lambda: current[0]
        app.dependency_overrides[response_service] = lambda: service
        tasks = []
        try:
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app), base_url="http://test"
            ) as client:

                async def create():
                    """Actual owner create transaction; no fake wanted rows/receipts."""
                    return await h.api.create(
                        h.caller,
                        WantedCreate(
                            title="Synthetic response request",
                            description="Controlled response fixture",
                            category_code="books",
                            operation_id=uuid4(),
                        ),
                    )

                async def respond(identifier, **extra):
                    """Keep current caller trusted and reject actor fields from the body."""
                    return await client.post(
                        "/wanted-requests/" + str(identifier) + "/conversations",
                        json={"operation_id": str(uuid4()), **extra},
                    )

                async def close(view):
                    """Actual owner state transaction competes for the same origin row."""
                    return await h.api.state(
                        h.caller,
                        view.request_id,
                        WantedState(
                            expected_revision=view.revision,
                            state="unavailable",
                            operation_id=uuid4(),
                        ),
                    )

                view = await create()
                created = await respond(view.request_id)
                repeated = await respond(view.request_id)
                assert created.status_code == 201 and repeated.status_code == 200
                assert (
                    created.json()["conversation_id"]
                    == repeated.json()["conversation_id"]
                )
                assert (
                    created.json()["created"] is True
                    and repeated.json()["created"] is False
                )
                assert set(repeated.json()) == {"conversation_id", "created"}
                assert repeated.headers["cache-control"] == "private, no-store"
                assert provider.create_calls[0][1].author_id == h.author
                assert (
                    await respond(view.request_id, author_id=str(responders[1]))
                ).status_code == 422
                before = (
                    len(provider.create_calls),
                    len(provider.lookup_calls),
                    provider.effects,
                )
                current[0] = h.caller
                assert (await respond(view.request_id)).status_code == 403
                current[0] = CallerContext(
                    responders[2], "temporary", datetime.now(UTC) + timedelta(minutes=5)
                )
                assert (await respond(view.request_id)).status_code == 403
                current[0] = CallerContext(
                    responders[0], "regular", datetime.now(UTC) - timedelta(seconds=1)
                )
                assert (await respond(view.request_id)).status_code == 401
                current[0] = CallerContext(
                    responders[0], "regular", datetime.now(UTC) + timedelta(minutes=5)
                )
                identity.identifiers.remove(responders[0])
                assert (await respond(view.request_id)).status_code == 403
                identity.identifiers.add(responders[0])
                assert (await respond(uuid4())).status_code == 404
                pending, _ = await h.seed()
                assert await h.store.begin_retirement(pending, h.now) is not None
                assert (await respond(pending)).status_code == 404
                retired, _ = await h.seed()
                assert (
                    await WantedRetirementService(
                        h.store,
                        ConversationsRetirementDouble(),
                        lambda: datetime.now(UTC),
                    ).retire(retired)
                ).outcome == "marked"
                assert (await respond(retired)).status_code == 404
                assert (
                    len(provider.create_calls),
                    len(provider.lookup_calls),
                    provider.effects,
                ) == before

                await close(view)
                lookup = await respond(view.request_id)
                assert (
                    lookup.status_code == 200
                    and lookup.json()["conversation_id"]
                    == created.json()["conversation_id"]
                )
                assert len(provider.create_calls) == before[0]
                current[0] = CallerContext(
                    responders[1], "regular", datetime.now(UTC) + timedelta(minutes=5)
                )
                assert (await respond(view.request_id)).status_code == 404
                assert len(provider.create_calls) == before[0]
                current[0] = CallerContext(
                    responders[0], "regular", datetime.now(UTC) + timedelta(minutes=5)
                )

                # Remote commit may precede a lost result. After closure a retry
                # must use read-only lookup, never attempt another create.
                lost = await create()
                provider.lose_once = True
                assert (await respond(lost.request_id)).status_code == 503
                lost_id = provider.threads[(lost.request_id, responders[0])]
                await close(lost)
                attempts = len(provider.create_calls)
                recovered = await respond(lost.request_id)
                assert recovered.status_code == 200 and recovered.json() == {
                    "conversation_id": str(lost_id),
                    "created": False,
                }
                assert len(provider.create_calls) == attempts

                # Dedicated integrity fixture: an independent transaction inserts
                # thread/member FKs while Search holds the origin guard. It must
                # commit, not wait behind a FOR UPDATE self-deadlock. This is a
                # schema/lock probe only, not a fake public Conversations service.
                fk = await create()
                async with h.store.response_guard(fk.request_id) as origin:
                    assert origin.author_id == h.author
                    async with h.pool.connection() as connection:
                        await connection.execute("SET LOCAL statement_timeout='500ms'")
                        thread = uuid4()
                        await connection.execute(
                            "INSERT INTO conversations.threads(id,wanted_request_id,initiator_id,counterparty_id) VALUES(%s,%s,%s,%s)",
                            (thread, fk.request_id, responders[0], h.author),
                        )
                        await connection.execute(
                            "INSERT INTO conversations.members(conversation_id,user_id) VALUES(%s,%s),(%s,%s)",
                            (thread, responders[0], thread, h.author),
                        )
                        await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

                closed_first = await create()
                await close(closed_first)
                attempts = len(provider.create_calls)
                assert (await respond(closed_first.request_id)).status_code == 404
                assert len(provider.create_calls) == attempts
                assert (closed_first.request_id, responders[0]) not in provider.threads

                # Response first: hold the real Search row while the public
                # fixture is paused; observe owner closure waiting in PostgreSQL.
                race = await create()
                provider.pause_for = race.request_id
                provider.entered.clear()
                provider.release.clear()
                response_task = asyncio.create_task(respond(race.request_id))
                tasks.append(response_task)
                await asyncio.wait_for(provider.entered.wait(), timeout=1)
                close_task = asyncio.create_task(close(race))
                tasks.append(close_task)

                async def wait_for_owner_lock():
                    """Inspect actual server wait state, not a timing-only assertion."""
                    async with h.pool.connection() as observer:
                        for _ in range(50):
                            # Activity snapshots can otherwise retain the first
                            # pre-wait observation for this observer transaction.
                            await observer.execute("SELECT pg_stat_clear_snapshot()")
                            row = await (
                                await observer.execute(
                                    "SELECT count(*) AS total FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE '%search.wanted_requests%FOR UPDATE%'"
                                )
                            ).fetchone()
                            if row["total"] > 0:
                                return
                            await asyncio.sleep(0.01)
                    raise AssertionError(
                        "Owner close never waited for response origin lock"
                    )

                await asyncio.wait_for(wait_for_owner_lock(), timeout=0.75)
                assert not close_task.done()
                provider.release.set()
                response, closed = await asyncio.wait_for(
                    asyncio.gather(response_task, close_task), timeout=3
                )
                assert response.status_code == 201 and closed.state == "unavailable"
                assert (await h.row(race.request_id))["status"] == "unavailable"
                assert (await respond(race.request_id)).json() == {
                    "conversation_id": response.json()["conversation_id"],
                    "created": False,
                }
        finally:
            provider.release.set()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            # Retain immutable references (including the schema-only FK fixture)
            # and close only this actor's public corpus for later tests.
            async with h.pool.connection() as connection:
                await connection.execute(
                    "UPDATE search.wanted_requests SET status='unavailable',revision=revision+1,updated_at=statement_timestamp() WHERE author_id=%s AND status='open' AND retired_at IS NULL",
                    (h.author,),
                )
