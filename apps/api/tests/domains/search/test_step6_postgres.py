"""SE-02 coverage gaps exercised through real wanted HTTP/PostgreSQL.

Only reviewed Identity/catalogue dependencies are explicit fixtures. Request-to-
conversation capability/race checks are not faked here: that local API is absent.
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
from app.domains.search.wanted import WantedService
from app.domains.search.wanted_routes import router, wanted_service
from app.domains.search.wanted_store import PostgresWantedStore
from apps.api.tests.domains.listings.test_embedding_postgres import connect, target
from apps.api.tests.domains.search.test_wanted_postgres import Dependencies


def test_native_step6_account_budget_expiry_and_wanted_pagination_cases():
    asyncio.run(exercise(target()))


async def exercise(value):
    """Close only owned fixture requests on exit; immutable origins remain."""
    async with await connect(value):
        pass
    pool = AsyncConnectionPool[AsyncConnection[dict]](
        value, kwargs={"row_factory": dict_row}, min_size=1, max_size=4, open=False
    )
    await pool.open()
    actors = [uuid4(), uuid4(), uuid4()]
    try:
        await pool.wait(timeout=5)
        async with pool.connection() as connection:
            for index, actor in enumerate(actors):
                await connection.execute(
                    "INSERT INTO identity.users(id,account_class,status,display_name,activated_at,expires_at) "
                    "VALUES(%s,%s,'active','Synthetic Step6 actor',CASE WHEN %s THEN CURRENT_TIMESTAMP END,"
                    "CASE WHEN %s THEN CURRENT_TIMESTAMP+interval '336 hours' END)",
                    (
                        actor,
                        "temporary" if index == 1 else "regular",
                        index == 1,
                        index == 1,
                    ),
                )
        current = [
            CallerContext(
                actors[0], "regular", datetime.now(UTC) + timedelta(minutes=5)
            )
        ]
        app = FastAPI()
        install_error_handlers(app)
        app.include_router(router)
        service = WantedService(PostgresWantedStore(pool), Dependencies(set(actors)))
        app.dependency_overrides[require_caller] = lambda: current[0]
        app.dependency_overrides[wanted_service] = lambda: service
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://test"
        ) as client:
            sample = None
            for index, account_class in enumerate(["regular", "temporary"]):
                current[0] = CallerContext(
                    actors[index],
                    account_class,
                    datetime.now(UTC) + timedelta(minutes=5),
                )
                for budget in ["omitted", "null", "zero"]:
                    body = dict(
                        title="Step6 " + account_class + " " + budget,
                        description="Controlled coverage fixture",
                        category_code="books",
                        operation_id=str(uuid4()),
                    )
                    if budget != "omitted":
                        body["budget_paise"] = None if budget == "null" else 0
                    response = await client.post("/wanted-requests", json=body)
                    assert response.status_code == 201, response.text
                    created = response.json()
                    assert created["budget_paise"] == (0 if budget == "zero" else None)
                    if budget == "omitted":
                        assert (
                            await client.post(
                                "/wanted-requests", json={**body, "budget_paise": None}
                            )
                        ).json() == created
                    path = "/wanted-requests/" + created["request_id"]
                    edited = await client.patch(
                        path,
                        json=dict(
                            title="Edited Step6 title",
                            expected_revision=1,
                            operation_id=str(uuid4()),
                        ),
                    )
                    assert (
                        edited.status_code == 200
                        and edited.json()["budget_paise"] == created["budget_paise"]
                    )
                    closed = await client.put(
                        path + "/availability",
                        json=dict(
                            state="unavailable",
                            expected_revision=edited.json()["revision"],
                            operation_id=str(uuid4()),
                        ),
                    )
                    assert closed.status_code == 200
                    assert (await client.get(path)).json()["state"] == "unavailable"
                    own = (await client.get("/me/wanted-requests")).json()["items"]
                    assert created["request_id"] in {row["request_id"] for row in own}
                    current[0] = CallerContext(
                        actors[1 - index],
                        "temporary" if index == 0 else "regular",
                        datetime.now(UTC) + timedelta(minutes=5),
                    )
                    assert (await client.get(path)).status_code == 404
                    assert (
                        await client.patch(
                            path,
                            json=dict(
                                title="Other actor write",
                                expected_revision=1,
                                operation_id=str(uuid4()),
                            ),
                        )
                    ).status_code == 404
                    current[0] = CallerContext(
                        actors[index],
                        account_class,
                        datetime.now(UTC) + timedelta(minutes=5),
                    )
                    reopened = await client.put(
                        path + "/availability",
                        json=dict(
                            state="open",
                            expected_revision=closed.json()["revision"],
                            operation_id=str(uuid4()),
                        ),
                    )
                    assert (
                        reopened.status_code == 200
                        and reopened.json()["request_id"] == created["request_id"]
                    )
                    detail = (await client.get(path)).json()
                    assert set(detail) == {
                        "request_id",
                        "title",
                        "description",
                        "category_code",
                        "category_label",
                        "budget_paise",
                        "created_at",
                        "updated_at",
                    }
                    sample = created["request_id"]

            # Actual expiry rejects every implemented request operation without
            # changing owned request/receipt counts, not only a mocked read path.
            async def counts():
                """Observe only these actors' controlled rows and retry copies."""
                async with pool.connection() as connection:
                    return await (
                        await connection.execute(
                            "SELECT (SELECT count(*) FROM search.wanted_requests WHERE author_id=ANY(%s)) AS wanted,(SELECT count(*) FROM search.wanted_command_results WHERE author_id=ANY(%s)) AS commands",
                            (actors, actors),
                        )
                    ).fetchone()

            before = await counts()
            current[0] = CallerContext(
                actors[1], "temporary", datetime.now(UTC) - timedelta(microseconds=1)
            )
            expired = [
                await client.get("/wanted-requests"),
                await client.get("/me/wanted-requests"),
                await client.get("/wanted-requests/" + sample),
                await client.post(
                    "/wanted-requests",
                    json=dict(
                        title="Expired create",
                        description="Controlled fixture",
                        category_code="books",
                        operation_id=str(uuid4()),
                    ),
                ),
                await client.patch(
                    "/wanted-requests/" + sample,
                    json=dict(
                        expected_revision=1,
                        title="Expired edit",
                        operation_id=str(uuid4()),
                    ),
                ),
                await client.put(
                    "/wanted-requests/" + sample + "/availability",
                    json=dict(
                        expected_revision=1,
                        state="unavailable",
                        operation_id=str(uuid4()),
                    ),
                ),
            ]
            assert all(
                response.status_code == 401
                and response.headers["cache-control"] == "private, no-store"
                for response in expired
            )
            assert await counts() == before

            # One SQL statement creates a fixed tied-time corpus for a dedicated
            # actor, so both owner pages have an exact reproducible UUID oracle.
            current[0] = CallerContext(
                actors[2], "regular", datetime.now(UTC) + timedelta(minutes=5)
            )
            async with pool.connection() as connection:
                rows = await (
                    await connection.execute(
                        "INSERT INTO search.wanted_requests(id,author_id,title,description,category_code,status) "
                        "SELECT gen_random_uuid(),%s,'Step6 tied request','Controlled tied fixture','books','open' "
                        "FROM generate_series(1,21) RETURNING id",
                        (actors[2],),
                    )
                ).fetchall()
            expected = sorted([row["id"] for row in rows], reverse=True)
            own1 = (await client.get("/me/wanted-requests")).json()
            own2 = (await client.get("/me/wanted-requests?page=2")).json()
            assert [row["request_id"] for row in own1["items"] + own2["items"]] == [
                str(identifier) for identifier in expected
            ]
            assert own1["has_next"] is True and own2["has_next"] is False
            hidden = []
            for _ in range(2):
                created = (
                    await client.post(
                        "/wanted-requests",
                        json=dict(
                            title="Step6 newer hidden",
                            description="Controlled unavailable fixture",
                            category_code="books",
                            operation_id=str(uuid4()),
                        ),
                    )
                ).json()
                hidden.append(created["request_id"])
                assert (
                    await client.put(
                        "/wanted-requests/" + created["request_id"] + "/availability",
                        json=dict(
                            state="unavailable",
                            expected_revision=1,
                            operation_id=str(uuid4()),
                        ),
                    )
                ).status_code == 200
            public1 = (await client.get("/wanted-requests")).json()
            public2 = (await client.get("/wanted-requests?page=2")).json()
            public_ids = [
                row["request_id"] for row in public1["items"] + public2["items"]
            ]
            assert public_ids[:21] == [str(identifier) for identifier in expected]
            assert not set(hidden).intersection(public_ids)
            assert all(
                "state" not in row and "revision" not in row and "author_id" not in row
                for row in public1["items"] + public2["items"]
            )
    finally:
        try:
            # Keep later tests independent of this public corpus. Closure is
            # non-destructive; immutable origin/command references stay retained.
            async with pool.connection() as connection:
                await connection.execute(
                    "UPDATE search.wanted_requests SET status='unavailable',revision=revision+1,updated_at=statement_timestamp() WHERE author_id=ANY(%s) AND status='open' AND retired_at IS NULL",
                    (actors,),
                )
        finally:
            await pool.close()
