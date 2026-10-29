"""Private keyword rank construction/transport only; native order tested separately."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.contracts.domain_types import ListingQuery
from app.core.errors import ERRORS, PublicError
from app.domains.listings.browse_store import browse_statement, read_browse_page
from apps.api.tests.domains.listings.test_lexical_expansion import scripted_plan

NOW = datetime(2026, 10, 24, tzinfo=UTC)


def test_rank_tiers_bound_queries_private_projection_and_no_cutoff():
    """Ranks belong only in ORDER BY; membership/filter predicates are unchanged."""
    request = ListingQuery(
        q="red bicyle",
        page=2,
        page_size=50,
        category_code="bicycles",
        condition_code="good",
        negotiable=False,
        min_price_paise=0,
        max_price_paise=50000,
    )
    compiled = scripted_plan(request.q)
    sql, values = browse_statement(
        request, NOW, 500000, text_query=compiled, keyword_relevance=True
    )
    assert sql.count("%s") == len(values) and values[-2:] == (51, 50)
    assert request.q not in sql and request.q in values
    before, order = sql.split("ORDER BY CASE WHEN", 1)
    # The inner image-reference subquery has its own ORDER BY and remains unchanged.
    assert "ts_rank_cd" not in before
    assert "THEN 1 ELSE 0 END DESC" in order
    assert order.count("ts_rank_cd(listing.search_vector,") == 2
    assert ", 0)" in order and "END DESC, listing.id ASC" in order
    assert "category.code = ANY(%s)" in before
    assert "listing_condition.code = ANY(%s)" in before
    assert (
        "listing.negotiable = %s" in before
        and "asking_price_paise >= %s" in before
        and "asking_price_paise <= %s" in before
    )
    assert "embedding_" not in sql and "LIMIT" not in before
    assert "ts_rank_cd" not in sql.split("FROM listings.sale_listings", 1)[0]


@pytest.mark.parametrize("sort", ["created_desc", "price_asc", "price_desc"])
def test_defaults_and_expanded_membership_unchanged(sort):
    request = ListingQuery(q="vehicle", sort=sort)
    compiled = scripted_plan("vehicle")
    plain = browse_statement(request, NOW, 500000)
    assert plain == browse_statement(request, NOW, 500000, keyword_relevance=False)
    expanded, _ = browse_statement(request, NOW, 500000, text_query=compiled)
    relevant, _ = browse_statement(
        request, NOW, 500000, text_query=compiled, keyword_relevance=True
    )
    assert "ts_rank_cd" not in expanded
    assert (
        expanded.split("ORDER BY listing.", 1)[0]
        == relevant.split("ORDER BY CASE WHEN", 1)[0]
    )


@pytest.mark.parametrize("q", [None, "", "   "])
def test_blank_relevance_is422_before_database_or_compiler(q):
    async def exercise():
        connection = AsyncMock()
        with patch(
            "app.domains.listings.browse_store.compile_expansion", AsyncMock()
        ) as compiler:
            with pytest.raises(PublicError) as raised:
                await read_browse_page(
                    connection, ListingQuery(q=q), NOW, 500000, keyword_relevance=True
                )
        assert raised.value.spec == ERRORS[422] and raised.value.details[0].field == "q"
        compiler.assert_not_awaited()
        connection.execute.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize("flag", [1, "true", None])
def test_private_flag_cannot_coerce(flag):
    with pytest.raises(ValueError, match="private relevance flag"):
        browse_statement(
            ListingQuery(q="vehicle"),
            NOW,
            500000,
            text_query=scripted_plan("vehicle"),
            keyword_relevance=flag,
        )


@pytest.mark.parametrize(
    "compiled",
    [
        None,
        scripted_plan("book"),
        replace(scripted_plan("vehicle"), vocabulary_fingerprint="wrong"),
    ],
)
def test_rank_cannot_use_another_query_or_vocabulary(compiled):
    with pytest.raises(ValueError, match="bound compiled query"):
        browse_statement(
            ListingQuery(q="vehicle"),
            NOW,
            500000,
            text_query=compiled,
            keyword_relevance=True,
        )


def test_relevance_implies_compiler_once_without_semantic_constructor_or_metadata():
    async def exercise():
        connection = AsyncMock()
        cursor = AsyncMock()
        cursor.fetchall.return_value = []
        connection.execute.return_value = cursor
        compiler = AsyncMock(return_value=scripted_plan("vehicel"))
        with (
            patch("app.domains.listings.browse_store.compile_expansion", compiler),
            patch(
                "app.domains.listings.embedding_client.SemanticHelper.__init__",
                side_effect=AssertionError("Keyword must not construct a model"),
            ) as constructor,
        ):
            result = await read_browse_page(
                connection,
                ListingQuery(q=" vehicel "),
                NOW,
                500000,
                keyword_relevance=True,
            )
        assert result.items == () and result.has_next is False
        compiler.assert_awaited_once_with(connection, "vehicel")
        constructor.assert_not_called()
        assert connection.execute.await_count == 1
        sql, values = connection.execute.await_args.args
        assert "bicycle" in values and "ts_rank_cd" in sql and "embedding_" not in sql

    asyncio.run(exercise())


def test_parser_sensitive_values_are_parameters_in_membership_and_rank():
    q = "bicycle'); SELECT 1; --"
    sql, values = browse_statement(
        ListingQuery(q=q),
        NOW,
        500000,
        text_query=scripted_plan(q),
        keyword_relevance=True,
    )
    assert q not in sql and values.count(q) >= 4 and sql.count("%s") == len(values)
