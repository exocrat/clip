"""Wanted discovery filtering through the real Search SQL/HTTP path."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI
import httpx2
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.contracts.domain_types import Category, CategoryDisplay
from app.core.auth import CallerContext, require_caller
from app.core.errors import install_error_handlers
from app.domains.search.wanted import WantedService
from app.domains.search.wanted_routes import router, wanted_service
from app.domains.search.wanted_store import PostgresWantedStore
from apps.api.tests.domains.listings.test_embedding_postgres import connect, target


class Dependencies:
    """Reviewed eligibility and category outputs for the owned synthetic actor."""

    def __init__(self, actor):
        self.actor = actor

    async def eligible(self, actor):
        return actor == self.actor

    async def active_categories(self):
        return (
            Category(code="books", label="Books and Study Materials"),
            Category(code="bicycles", label="Bicycles"),
            Category(code="sports_fitness", label="Sports & Fitness"),
        )

    async def category_display(self, codes):
        labels = {
            "books": "Books and Study Materials",
            "bicycles": "Bicycles",
            "sports_fitness": "Sports & Fitness",
        }
        return tuple(
            CategoryDisplay(code=code, label=labels[code], active=True)
            for code in codes
        )


def test_wanted_discovery_filters_real_indexed_sql_and_public_projection():
    asyncio.run(exercise(target()))


async def exercise(value):
    """Seed isolated requests spanning text, category, budget and visibility."""
    async with await connect(value):
        pass
    pool = AsyncConnectionPool[AsyncConnection[dict]](
        value, kwargs={"row_factory": dict_row}, min_size=1, max_size=4, open=False
    )
    await pool.open()
    actor = uuid4()
    try:
        await pool.wait(timeout=5)
        async with pool.connection() as connection:
            await connection.execute(
                "INSERT INTO identity.users(id,account_class,status,display_name) "
                "VALUES(%s,'regular','active','Synthetic discovery author')",
                (actor,),
            )
            rows = [
                (
                    "Physics study request",
                    "Need a textbook for first-year study",
                    "books",
                    50000,
                    "open",
                ),
                (
                    "Campus bicycle wanted",
                    "Physics field-study equipment",
                    "bicycles",
                    150000,
                    "open",
                ),
                (
                    "Physics lab equipment",
                    "No stated budget for this request",
                    "books",
                    None,
                    "open",
                ),
                (
                    "Physics sports kit",
                    "Synthetic category filter fixture",
                    "sports_fitness",
                    100000,
                    "open",
                ),
                (
                    "Hidden physics textbook",
                    "Unavailable requests stay hidden",
                    "books",
                    75000,
                    "unavailable",
                ),
            ]
            identifiers = []
            for index, (title, description, category, budget, state) in enumerate(rows):
                identifier = uuid4()
                identifiers.append(identifier)
                await connection.execute(
                    "INSERT INTO search.wanted_requests "
                    "(id,author_id,title,description,category_code,budget_paise,status,created_at,closed_at) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,clock_timestamp()-(%s * interval '1 second'),"
                    "CASE WHEN %s='unavailable' THEN clock_timestamp() END)",
                    (
                        identifier,
                        actor,
                        title,
                        description,
                        category,
                        budget,
                        state,
                        index,
                        state,
                    ),
                )

        current = [
            CallerContext(actor, "regular", datetime.now(UTC) + timedelta(minutes=5))
        ]
        app = FastAPI()
        install_error_handlers(app)
        app.include_router(router)
        service = WantedService(PostgresWantedStore(pool), Dependencies(actor))
        app.dependency_overrides[require_caller] = lambda: current[0]
        app.dependency_overrides[wanted_service] = lambda: service
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://test"
        ) as client:
            url = (
                "/wanted-requests?q=physics"
                "&category_code=books&category_code=bicycles"
                "&min_budget_paise=50000&max_budget_paise=150000"
            )
            response = await client.get(url)
            assert response.status_code == 200, response.text
            body = response.json()
            assert {item["request_id"] for item in body["items"]} == {
                str(identifiers[0]),
                str(identifiers[1]),
            }
            assert all(
                "author_id" not in item and "phone" not in item
                for item in body["items"]
            )
            assert (
                body["page"] == 1 and body["page_size"] == 20 and not body["has_next"]
            )

            cross_field = await client.get("/wanted-requests?q=physics+textbook")
            assert cross_field.status_code == 200
            assert {item["request_id"] for item in cross_field.json()["items"]} == {
                str(identifiers[0])
            }

            # A budget bound excludes null budgets; closed requests never leak.
            budget_page = await client.get(
                "/wanted-requests?q=physics&min_budget_paise=0"
            )
            assert budget_page.status_code == 200
            budget_ids = {item["request_id"] for item in budget_page.json()["items"]}
            assert str(identifiers[2]) not in budget_ids
            assert str(identifiers[4]) not in budget_ids

            # Repeated category selection is OR; an empty result remains a valid page.
            category_page = await client.get(
                "/wanted-requests?category_code=bicycles&category_code=sports_fitness"
            )
            assert category_page.status_code == 200
            assert {item["request_id"] for item in category_page.json()["items"]} == {
                str(identifiers[1]),
                str(identifiers[3]),
            }
            assert (
                await client.get("/wanted-requests?q=not-a-real-request-word")
            ).json()["items"] == []

            for invalid in (
                "min_budget_paise=101",
                "min_budget_paise=200&max_budget_paise=100",
                "category_code=unknown_category",
                "q=" + "x" * 121,
            ):
                assert (
                    await client.get("/wanted-requests?" + invalid)
                ).status_code == 422
    finally:
        # The test target is disposable; keep immutable wanted origins intact.
        await pool.close()
