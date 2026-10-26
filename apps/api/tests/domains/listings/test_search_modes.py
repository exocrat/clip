"""Public mode dispatch/transport tests; SQL and model behavior have native tests."""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.contracts.domain_types import ListingQuery
from app.core.errors import ERRORS, PublicError
from app.core.pagination import Page
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.browse_validation import normalize_query
from apps.api.tests.domains.listings.test_browse_contract import application

NOW = datetime(2026, 10, 25, tzinfo=UTC)
MODULE = "app.domains.listings.postgres_store"


@pytest.mark.parametrize("mode", ["keyword", "hybrid"])
@pytest.mark.parametrize(
    "sort", ["created_desc", "price_asc", "price_desc", "relevance"]
)
@pytest.mark.parametrize("text", [None, "  ", " vehicle "])
def test_mode_text_sort_dispatch(mode, sort, text):
    """Normalize before I/O; blank relevance fails, blank Hybrid uses keyword SQL."""

    async def exercise():
        helper = object()
        store = PostgresListingsStore(AsyncMock(), 500000, hybrid_helper=helper)
        connection = object()
        entered = []

        @asynccontextmanager
        async def connect():
            entered.append(True)
            yield connection

        store._connection = connect
        page = Page((), 1, 20, False)
        with (
            patch(
                MODULE + ".read_browse_page", AsyncMock(return_value=page)
            ) as keyword,
            patch(
                MODULE + ".search_hybrid_page", AsyncMock(return_value=page)
            ) as hybrid,
        ):
            request = ListingQuery(q=text, search_mode=mode, sort=sort)
            if sort == "relevance" and not (text or "").strip():
                with pytest.raises(PublicError) as error:
                    await store.browse_available_listings(request, NOW)
                assert error.value.spec == ERRORS[422]
                assert not entered
                keyword.assert_not_awaited()
                hybrid.assert_not_awaited()
                return
            assert await store.browse_available_listings(request, NOW) == page
            normalized = normalize_query(request)
            if mode == "hybrid" and normalized.q:
                hybrid.assert_awaited_once_with(
                    connection,
                    helper,
                    normalized,
                    NOW,
                    500000,
                    relevance=sort == "relevance",
                )
                keyword.assert_not_awaited()
            else:
                keyword.assert_awaited_once_with(
                    connection,
                    normalized,
                    NOW,
                    500000,
                    expanded_search=True,
                    keyword_relevance=sort == "relevance",
                )
                hybrid.assert_not_awaited()

    asyncio.run(exercise())


def test_unconfigured_hybrid_fails_before_pool_without_keyword_fallback():
    async def exercise():
        pool = AsyncMock()
        store = PostgresListingsStore(pool, 500000)
        with patch(MODULE + ".read_browse_page", AsyncMock()) as keyword:
            with pytest.raises(PublicError) as error:
                await store.browse_available_listings(
                    ListingQuery(q="food cold", search_mode="hybrid"), NOW
                )
            assert error.value.spec == ERRORS[503]
            pool.connection.assert_not_called()
            keyword.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize("mode", ["keyword", "hybrid"])
@pytest.mark.parametrize(
    "sort", ["created_desc", "price_asc", "price_desc", "relevance"]
)
def test_http_forwards_registered_fields(mode, sort):
    app, store = application()
    with TestClient(app) as client:
        response = client.get(
            "/listings", params={"q": " bicyle ", "search_mode": mode, "sort": sort}
        )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    query = store.browse_available_listings.await_args.args[0]
    assert (query.search_mode, query.sort, query.q) == (mode, sort, "bicyle")


@pytest.mark.parametrize(
    "params",
    [
        {"search_mode": "semantic"},
        {"search_mode": ""},
        {"search_mode": "Hybrid", "q": "book"},
        {"sort": "relevance"},
        {"q": "  ", "sort": "relevance", "search_mode": "hybrid"},
    ],
)
def test_invalid_http_input_is_safe_uncached422_before_store(params):
    app, store = application()
    with TestClient(app) as client:
        response = client.get("/listings", params=params)
    assert response.status_code == 422
    assert response.headers["cache-control"] == "private, no-store"
    store.browse_available_listings.assert_not_awaited()


@pytest.mark.parametrize(
    "authenticated,eligible,status",
    [(False, True, 401), (True, False, 403), (True, True, 503)],
)
def test_hybrid_auth_precedes_retrieval_and_errors_are_uncached(
    authenticated, eligible, status
):
    app, store = application(
        authenticated=authenticated, eligible=eligible, failure=503
    )
    with TestClient(app) as client:
        response = client.get(
            "/listings", params={"q": "food cold", "search_mode": "hybrid"}
        )
    assert response.status_code == status
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["error"]["code"] == ERRORS[status].code
    if status != 503:
        store.browse_available_listings.assert_not_awaited()


def test_missing_helper_does_not_mask_invalid_active_catalogue_filter():
    """An invalid known catalogue remains422 rather than capability503."""

    async def exercise():
        store = PostgresListingsStore(AsyncMock(), 500000)

        @asynccontextmanager
        async def connect():
            yield object()

        store._connection = connect
        with patch(
            MODULE + ".validate_catalogue_filters",
            AsyncMock(side_effect=PublicError(ERRORS[422])),
        ) as validate:
            with pytest.raises(PublicError) as error:
                await store.browse_available_listings(
                    ListingQuery(
                        q="book", search_mode="hybrid", category_code="unknown"
                    ),
                    NOW,
                )
            assert error.value.spec == ERRORS[422]
            validate.assert_awaited_once()

    asyncio.run(exercise())
