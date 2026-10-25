"""Real wanted HTTP/store transactions on the owned disposable PostgreSQL target.

Only upstream Identity/catalogue are explicit contract doubles. SQL, revisions,
retry records, locks and HTTP response validation run their real implementations.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
import httpx2
from psycopg import AsyncConnection
from psycopg.errors import CheckViolation
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
import pytest

from app.contracts.domain_types import Category, CategoryDisplay
from app.core.auth import CallerContext, require_caller
from app.core.errors import install_error_handlers
from app.domains.search.wanted import WantedService
from app.domains.search.wanted_routes import router, wanted_service
from app.domains.search.wanted_store import PostgresWantedStore
from apps.api.tests.domains.listings.test_embedding_postgres import connect, target


class Dependencies:
    """Fixed eligible IDs and public code/label fixtures, no fake persistence."""

    def __init__(self, identifiers):
        self.identifiers = identifiers
        self.active = True
        self.fail = False

    async def eligible(self, actor):
        return actor in self.identifiers

    async def active_categories(self):
        if self.fail:
            raise TimeoutError
        return (Category(code="books", label="Books"),) if self.active else ()

    async def category_display(self, codes):
        if self.fail:
            raise TimeoutError
        return tuple(
            CategoryDisplay(code=code, label="Books", active=self.active)
            for code in codes
        )


def test_native_wanted_http_transactions_retries_privacy_and_races():
    asyncio.run(exercise(target()))


async def exercise(value):
    """Seed owned synthetic IDs and retain them in the runner-owned disposable DB."""
    # Gate the exact runner database before opening the pool or seeding anything.
    async with await connect(value) as gate:
        pass
    pool = AsyncConnectionPool[AsyncConnection[dict]](
        value, kwargs={"row_factory": dict_row}, min_size=1, max_size=4, open=False
    )
    await pool.open()
    await pool.wait(timeout=5)
    actors = [uuid4(), uuid4()]
    dependencies = Dependencies(set(actors))
    store = PostgresWantedStore(pool)
    service = WantedService(store, dependencies)
    current = [
        CallerContext(actors[0], "regular", datetime.now(UTC) + timedelta(minutes=5))
    ]
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(router)
    app.dependency_overrides[require_caller] = lambda: current[0]
    app.dependency_overrides[wanted_service] = lambda: service
    try:
        async with pool.connection() as connection:
            await connection.execute(
                "INSERT INTO identity.users(id,account_class,status,display_name,activated_at,expires_at) VALUES(%s,'regular','active','Synthetic wanted author',NULL,NULL),(%s,'temporary','active','Synthetic other author',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP+interval '336 hours')",
                tuple(actors),
            )
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://test"
        ) as client:

            async def post(title="Synthetic wanted books", **extra):
                body = dict(
                    title=title,
                    description="Controlled wanted HTTP fixture",
                    category_code="books",
                    operation_id=str(uuid4()),
                )
                body.update(extra)
                return await client.post("/wanted-requests", json=body), body

            created, intent = await post()
            assert created.status_code == 201, created.text
            original = created.json()
            identifier = original["request_id"]
            path = "/wanted-requests/" + identifier
            assert set(original) == {
                "request_id",
                "title",
                "description",
                "category_code",
                "category_label",
                "budget_paise",
                "created_at",
                "updated_at",
                "state",
                "revision",
            }
            assert original["budget_paise"] is None
            assert (
                await client.post("/wanted-requests", json=intent)
            ).json() == original
            assert (
                await client.post(
                    "/wanted-requests", json={**intent, "title": "Changed intent"}
                )
            ).status_code == 409
            duplicate_intent = {**intent, "operation_id": str(uuid4())}
            duplicates = await asyncio.gather(
                *[
                    client.post("/wanted-requests", json=duplicate_intent)
                    for _ in range(3)
                ]
            )
            assert all(r.status_code == 201 for r in duplicates)
            assert len({r.json()["request_id"] for r in duplicates}) == 1
            assert (await client.get(path)).json().keys() == original.keys() - {
                "state",
                "revision",
            }
            assert (await client.get("/wanted-requests")).headers[
                "cache-control"
            ] == "private, no-store"
            assert (
                await client.get("/wanted-requests?page_size=21")
            ).status_code == 422
            assert (
                await client.get("/wanted-requests?page=999999999999999999999999999")
            ).status_code == 422
            assert (
                await client.post(
                    "/wanted-requests",
                    json={
                        **intent,
                        "operation_id": str(uuid4()),
                        "author_id": str(actors[1]),
                    },
                )
            ).status_code == 422

            patch = dict(expected_revision=1, operation_id=str(uuid4()), budget_paise=0)
            changed = await client.patch(path, json=patch)
            assert changed.status_code == 200, changed.text
            changed = changed.json()
            assert changed["budget_paise"] == 0 and changed["revision"] == 2
            assert (await client.patch(path, json=patch)).json() == changed
            assert (
                await client.patch(path, json={**patch, "budget_paise": 100})
            ).status_code == 409
            stale = await client.patch(
                path,
                json={**patch, "operation_id": str(uuid4()), "title": "Stale update"},
            )
            assert stale.status_code == 409
            clear = await client.patch(
                path,
                json=dict(
                    expected_revision=2, operation_id=str(uuid4()), budget_paise=None
                ),
            )
            assert clear.status_code == 200 and clear.json()["budget_paise"] is None
            assert clear.json()["revision"] == 3
            for field in ["title", "description", "category_code"]:
                assert (
                    await client.patch(path, json={**patch, field: None})
                ).status_code == 422
            # One revision wins under concurrent distinct edit keys.
            races = await asyncio.gather(
                *[
                    client.patch(
                        path,
                        json=dict(
                            expected_revision=3,
                            operation_id=str(uuid4()),
                            title="Concurrent " + str(index),
                        ),
                    )
                    for index in range(2)
                ]
            )
            assert sorted(r.status_code for r in races) == [200, 409]
            revision = next(r.json()["revision"] for r in races if r.status_code == 200)
            close_intent = dict(
                expected_revision=revision,
                operation_id=str(uuid4()),
                state="unavailable",
            )
            closed = await client.put(path + "/availability", json=close_intent)
            assert closed.status_code == 200, closed.text
            assert (
                await client.put(path + "/availability", json=close_intent)
            ).json() == closed.json()
            assert (await client.get(path)).json()["state"] == "unavailable"
            assert identifier not in {
                r["request_id"]
                for r in (await client.get("/wanted-requests")).json()["items"]
            }
            assert identifier in {
                r["request_id"]
                for r in (await client.get("/me/wanted-requests")).json()["items"]
            }
            current[0] = CallerContext(
                actors[1], "temporary", datetime.now(UTC) + timedelta(minutes=5)
            )
            assert (await client.get(path)).status_code == 404
            assert (await client.patch(path, json=patch)).status_code == 404
            assert (
                await client.put(path + "/availability", json=close_intent)
            ).status_code == 404
            assert (await client.get("/me/wanted-requests")).json()["items"] == []
            temp_created, _ = await post(
                "Synthetic temporary request", budget_paise=100
            )
            assert temp_created.status_code == 201
            current[0] = CallerContext(
                actors[0], "regular", datetime.now(UTC) + timedelta(minutes=5)
            )
            reopen = await client.put(
                path + "/availability",
                json=dict(
                    expected_revision=closed.json()["revision"],
                    operation_id=str(uuid4()),
                    state="open",
                ),
            )
            assert reopen.status_code == 200
            dependencies.active = False
            assert (await client.get(path)).status_code == 200
            # Retry a successful create even after editing/deactivation returns
            # its original response; a new assignment must still validate active.
            assert (
                await client.post("/wanted-requests", json=intent)
            ).json() == original
            assert (await post())[0].status_code == 422
            dependencies.fail = True
            assert (await client.get(path)).status_code == 503
            dependencies.fail = False
            # Pending retirement is hidden publicly and blocks owner writes and
            # old receipt replay, while owner management remains readable.
            async with pool.connection() as connection:
                await connection.execute(
                    "UPDATE search.wanted_requests SET retirement_pending_operation_id=%s,retirement_pending_cutoff_utc=clock_timestamp()-interval '90 days' WHERE id=%s",
                    (uuid4(), identifier),
                )
            assert (
                await client.post("/wanted-requests", json=intent)
            ).status_code == 409
            assert (await client.patch(path, json=patch)).status_code == 409
            current[0] = CallerContext(
                actors[1], "temporary", datetime.now(UTC) + timedelta(minutes=5)
            )
            assert (await client.get(path)).status_code == 404
            current[0] = CallerContext(
                actors[0], "regular", datetime.now(UTC) + timedelta(minutes=5)
            )
            # Stable pages for the fixed fixture set; unavailable/pending rows cannot
            # consume public page slots. No fake SQL sorting is used.
            dependencies.active = True
            for index in range(23):
                response, _ = await post("Synthetic page " + str(index))
                assert response.status_code == 201
            async with pool.connection() as connection:
                await connection.execute(
                    "UPDATE search.wanted_requests SET updated_at=created_at WHERE author_id=%s",
                    (actors[0],),
                )
            pages = [
                (await client.get("/wanted-requests?page=" + str(n))).json()
                for n in [1, 2]
            ]
            ids = [row["request_id"] for page in pages for row in page["items"]]
            assert (
                len(ids) == len(set(ids))
                and pages[0]["has_next"]
                and not pages[1]["has_next"]
            )
            assert identifier not in ids

            # A retired origin is unreadable even to its author. A content-free
            # create key prevents a late retry from creating a replacement row.
            old_id, late_key = uuid4(), uuid4()
            async with pool.connection() as connection:
                await connection.execute(
                    "INSERT INTO search.wanted_requests(id,author_id,title,description,category_code,status,created_at,closed_at) VALUES(%s,%s,'Synthetic retired','Synthetic retired','books','unavailable',clock_timestamp()-interval '200 days',clock_timestamp()-interval '190 days')",
                    (old_id, actors[0]),
                )
                await connection.execute(
                    "UPDATE search.wanted_requests SET retired_at=statement_timestamp(),title=NULL,description=NULL,category_code=NULL,budget_paise=NULL WHERE id=%s",
                    (old_id,),
                )
                await connection.execute(
                    "INSERT INTO search.wanted_command_results(author_id,scope_id,command_kind,operation_id,request_id) VALUES(%s,%s,'create',%s,%s)",
                    (actors[0], actors[0], late_key, old_id),
                )
            old_path = "/wanted-requests/" + str(old_id)
            assert (await client.get(old_path)).status_code == 404
            assert (
                await client.put(
                    old_path + "/availability",
                    json=dict(
                        expected_revision=1, operation_id=str(uuid4()), state="open"
                    ),
                )
            ).status_code == 409
            assert (
                await client.post(
                    "/wanted-requests", json={**intent, "operation_id": str(late_key)}
                )
            ).status_code == 409

        # Storage guard must block retirement rather than retaining replay data.
        async with pool.connection() as connection:
            async with connection.transaction(force_rollback=True):
                old = uuid4()
                await connection.execute(
                    "INSERT INTO search.wanted_requests(id,author_id,title,description,category_code,status,created_at,closed_at) VALUES(%s,%s,'Synthetic old','Synthetic old','books','unavailable',clock_timestamp()-interval '200 days',clock_timestamp()-interval '190 days')",
                    (old, actors[0]),
                )
                await connection.execute(
                    "INSERT INTO search.wanted_command_results(author_id,scope_id,command_kind,operation_id,request_id,request_payload,result_payload) VALUES(%s,%s,'create',%s,%s,'{}','{}')",
                    (actors[0], actors[0], uuid4(), old),
                )
                with pytest.raises(CheckViolation, match="outcome is immutable"):
                    async with connection.transaction():
                        await connection.execute(
                            "UPDATE search.wanted_command_results SET result_payload=jsonb_build_object('changed',true) WHERE request_id=%s",
                            (old,),
                        )
                with pytest.raises(
                    CheckViolation, match="content-free command receipts"
                ):
                    async with connection.transaction():
                        await connection.execute(
                            "UPDATE search.wanted_requests SET retired_at=statement_timestamp(),title=NULL,description=NULL,category_code=NULL,budget_paise=NULL WHERE id=%s",
                            (old,),
                        )
                migration = (
                    (
                        Path(__file__).resolve().parents[5]
                        / "database/migrations/20261025013000_wanted_command_results.sql"
                    )
                    .read_text()
                    .split("-- migrate:down\n")[1]
                )
                with pytest.raises(CheckViolation):
                    async with connection.transaction():
                        await connection.execute(migration)
    finally:
        # Origins intentionally preserve immutable references. Keep these owned
        # committed fixtures in the runner's disposable database for review;
        # never disable a guard or physically delete a wanted origin to clean up.
        await pool.close()
