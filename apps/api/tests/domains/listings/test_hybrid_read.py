"""Private read construction/error contracts; native SQL/model proof is separate."""

import asyncio
from dataclasses import replace
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import httpx2
from fastapi import FastAPI
import pytest
from psycopg.pq import TransactionStatus

from app.contracts.domain_types import ListingQuery
from app.core.errors import ERRORS, PublicError, public_error_handler
from app.domains.listings.embedding_client import (
    EncodedQuery,
    HelperUnavailable,
    HelperBusy,
)
from app.domains.listings.embedding_types import default_pipeline_spec
from app.domains.listings.hybrid_read import (
    bind_query,
    hybrid_statement,
    read_hybrid_page,
    search_hybrid_page,
)
from apps.api.tests.domains.listings.test_lexical_expansion import scripted_plan

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
VECTOR = (1.0,) + (0.0,) * 383


def binding(text="vehicle"):
    """Coordinate query tests binding/math only, never pretends to run a model."""
    return bind_query(text, default_pipeline_spec(), VECTOR)


def transport(result=None):
    """Script only driver transport; no SQL evaluator/ranking/readiness emulator."""
    connection = MagicMock()
    connection.autocommit = True
    connection.info.transaction_status = TransactionStatus.IDLE
    cursor = AsyncMock()
    cursor.fetchone.return_value = (
        result
        if result is not None
        else {
            "ready": True,
            "category_valid": True,
            "condition_valid": True,
            "items": [],
        }
    )
    connection.execute = AsyncMock(return_value=cursor)
    return connection


def test_snapshot_sql_parameterization_filter_order_and_private_projection():
    request = ListingQuery(
        q="vehicel",
        page=2,
        page_size=50,
        category_code="bicycles",
        condition_code="good",
        negotiable=False,
        min_price_paise=0,
        max_price_paise=10000,
        sort="price_asc",
    )
    sql, params = hybrid_statement(
        request, NOW, 500000, binding("vehicel"), scripted_plan("vehicel")
    )
    assert sql.count("%s") == len(params) and params[-2:] == (51, 50)
    assert "vehicel" not in sql and "vehicel" in params
    assert (
        "listing.retired_at IS NULL" in sql
        and "retirement_pending_operation_id IS NULL" in sql
    )
    assert (
        "listing.available_from<=input.now" in sql
        and "listing.available_until>input.now" in sql
    )
    assert (
        "category.code=ANY(%s)" in sql
        and "listing_condition.code=ANY(%s)" in sql
        and "listing.negotiable=%s" in sql
    )
    assert (
        "listing.asking_price_paise>=%s" in sql
        and "listing.asking_price_paise<=%s" in sql
    )
    assert "generation.state='ready'" in sql and "embedding_source_fingerprint" in sql
    assert "complete IS DISTINCT FROM true" in sql and "pipeline.state='serving'" in sql
    assert "scored.asking_price_paise ASC, scored.listing_id ASC" in sql
    assert "generation_id" not in sql.split("jsonb_build_object(", 1)[1]
    assert "source_fingerprint" not in sql.split("jsonb_build_object(", 1)[1]
    assert "LIMIT" not in sql.split("), page_window AS (")[0]
    relevant, _ = hybrid_statement(
        request,
        NOW,
        500000,
        binding("vehicel"),
        scripted_plan("vehicel"),
        relevance=True,
    )
    assert (
        "WHEN scored.original_match THEN 2 WHEN scored.expanded_match THEN 1 ELSE 0"
        in relevant
    )
    assert "scored.semantic_score DESC, scored.listing_id ASC" in relevant


def test_marketplace_price_cap_remains_exact_and_is_bound():
    request = ListingQuery(
        q="vehicle", min_price_paise=1_000_000_000, max_price_paise=1_000_000_000
    )
    sql, values = hybrid_statement(
        request, NOW, 500000, binding(), scripted_plan("vehicle")
    )
    assert request.min_price_paise in values and request.max_price_paise in values
    assert "listing.asking_price_paise>=%s" in sql
    assert "listing.asking_price_paise<=%s" in sql


@pytest.mark.parametrize(
    "bad",
    [
        "query",
        "compiler",
        "vocabulary",
        "model",
        "vector",
        "time",
        "threshold",
        "relevance",
    ],
)
def test_wrong_binding_or_configuration_refused(bad):
    request = ListingQuery(q="vehicle")
    bound = binding()
    compiled = scripted_plan("vehicle")
    now = NOW
    threshold = 500000
    relevance = False
    if bad == "query":
        bound = binding("book")
    if bad == "compiler":
        compiled = scripted_plan("book")
    if bad == "vocabulary":
        compiled = replace(compiled, vocabulary_fingerprint="wrong")
    if bad == "model":
        bound = replace(bound, spec=replace(bound.spec, canonical_encoding="{}"))
    if bad == "vector":
        bound = replace(bound, vector=(0.0,) * 384)
    if bad == "time":
        now = NOW.replace(tzinfo=None)
    if bad == "threshold":
        threshold = True
    if bad == "relevance":
        relevance = "yes"
    with pytest.raises(ValueError):
        hybrid_statement(request, now, threshold, bound, compiled, relevance=relevance)


@pytest.mark.parametrize(
    "result",
    [
        {"ready": False, "category_valid": True, "condition_valid": True, "items": []},
        {"ready": 1, "category_valid": True, "condition_valid": True, "items": []},
        {
            "ready": True,
            "category_valid": True,
            "condition_valid": True,
            "items": "bad",
        },
        {
            "ready": True,
            "category_valid": True,
            "condition_valid": True,
            "items": [{"private": "forbidden"}],
        },
    ],
)
def test_unready_or_malformed_results_raise_only_safe503(result):
    async def exercise():
        connection = transport(result)
        with patch(
            "app.domains.listings.hybrid_read.compile_expansion",
            AsyncMock(return_value=scripted_plan("vehicle")),
        ):
            with pytest.raises(PublicError) as raised:
                await read_hybrid_page(
                    connection, ListingQuery(q="vehicle"), NOW, 500000, binding()
                )
        assert (
            raised.value.spec == ERRORS[503]
            and str(raised.value) == "dependency_unavailable"
        )

    asyncio.run(exercise())


def test_invalid_catalogue422_takes_priority_over_missing_coverage():
    async def exercise():
        connection = transport(
            {
                "ready": False,
                "category_valid": False,
                "condition_valid": True,
                "items": [],
            }
        )
        with patch(
            "app.domains.listings.hybrid_read.compile_expansion",
            AsyncMock(return_value=scripted_plan("vehicle")),
        ):
            with pytest.raises(PublicError) as raised:
                await read_hybrid_page(
                    connection,
                    ListingQuery(q="vehicle", category_code="invalid"),
                    NOW,
                    500000,
                    binding(),
                )
        assert (
            raised.value.spec == ERRORS[422]
            and raised.value.details[0].field == "category_code"
        )

    asyncio.run(exercise())


def test_empty_ready_page_and_one_result_statement_not_separate_coverage_read():
    async def exercise():
        connection = transport()
        compiler = AsyncMock(return_value=scripted_plan("vehicle"))
        with patch("app.domains.listings.hybrid_read.compile_expansion", compiler):
            page = await read_hybrid_page(
                connection, ListingQuery(q="vehicle"), NOW, 500000, binding()
            )
        assert page.items == () and page.has_next is False
        assert (
            connection.execute.await_count == 3
        )  # two local bounds plus one result SELECT
        sql, _ = connection.execute.await_args.args
        assert "AS ready" in sql and "'listing_id'" in sql

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "failure",
    [HelperUnavailable("fixed"), HelperBusy("fixed"), TimeoutError("private")],
)
def test_helper_failure_is503_and_never_keyword_fallback(failure):
    async def exercise():
        helper = MagicMock()
        helper.encode_query = AsyncMock(side_effect=failure)
        connection = transport()
        with pytest.raises(PublicError) as raised:
            await search_hybrid_page(
                connection, helper, ListingQuery(q="vehicle"), NOW, 500000
            )
        assert raised.value.spec == ERRORS[503]
        connection.execute.assert_not_awaited()

    asyncio.run(exercise())


def test_helper_bridge_uses_original_trimmed_text_and_refuses_outer_transaction():
    async def exercise():
        helper = MagicMock()
        helper.spec = default_pipeline_spec()
        helper.encode_query = AsyncMock(return_value=EncodedQuery(VECTOR, 1))
        connection = transport()
        with patch(
            "app.domains.listings.hybrid_read.compile_expansion",
            AsyncMock(return_value=scripted_plan("vehicel")),
        ):
            assert (
                await search_hybrid_page(
                    connection, helper, ListingQuery(q=" vehicel "), NOW, 500000
                )
            ).items == ()
        helper.encode_query.assert_awaited_once_with("vehicel")
        connection.info.transaction_status = TransactionStatus.INTRANS
        with pytest.raises(PublicError):
            await search_hybrid_page(
                connection, helper, ListingQuery(q="vehicle"), NOW, 500000
            )
        assert helper.encode_query.await_count == 1

    asyncio.run(exercise())


def test_blank_text_rejected_before_helper_and_cancellation_propagates():
    async def exercise():
        helper = MagicMock()
        helper.encode_query = AsyncMock(side_effect=asyncio.CancelledError())
        connection = transport()
        with pytest.raises(PublicError) as raised:
            await search_hybrid_page(
                connection, helper, ListingQuery(q=" "), NOW, 500000
            )
        assert raised.value.spec == ERRORS[422]
        helper.encode_query.assert_not_awaited()
        with pytest.raises(asyncio.CancelledError):
            await search_hybrid_page(
                connection, helper, ListingQuery(q="vehicle"), NOW, 500000
            )

    asyncio.run(exercise())


def test503_is_controlled_http_response_and_next_request_still_works():
    """Test-only route exercises existing common handler; mounts no public feature."""

    async def exercise():
        app = FastAPI()
        app.add_exception_handler(PublicError, public_error_handler)

        @app.get("/private-test-only")
        async def probe():
            with patch(
                "app.domains.listings.hybrid_read.compile_expansion",
                AsyncMock(return_value=scripted_plan("vehicle")),
            ):
                await read_hybrid_page(
                    transport(
                        {
                            "ready": False,
                            "category_valid": True,
                            "condition_valid": True,
                            "items": [],
                        }
                    ),
                    ListingQuery(q="vehicle"),
                    NOW,
                    500000,
                    binding(),
                )

        @app.get("/still-alive")
        async def alive():
            return {"ok": True}

        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/private-test-only")
            assert response.status_code == 503 and response.json() == {
                "error": {
                    "code": "dependency_unavailable",
                    "message": "Required dependency unavailable",
                }
            }
            assert (await client.get("/still-alive")).json() == {"ok": True}

    asyncio.run(exercise())


@pytest.mark.parametrize("threshold", [0, 500000, ((2**63 - 1) // 100) * 100, 10**30])
def test_policy_threshold_matches_keyword_without_bigint_overflow(threshold):
    """Large accepted policy values flag no stored prices in either mode."""
    from app.core.config import Settings
    from app.domains.listings.browse_store import browse_statement

    Settings(sensitive_purchase_threshold_paise=threshold)
    request = ListingQuery(q="vehicle")
    _, keyword = browse_statement(request, NOW, threshold)
    _, hybrid = hybrid_statement(
        request, NOW, threshold, binding(), scripted_plan("vehicle")
    )
    expected = min(threshold, ((2**63 - 1) // 100) * 100)
    assert keyword[0] == hybrid[4] == expected
