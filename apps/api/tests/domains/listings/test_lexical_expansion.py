"""Compiler/transport checks with explicitly scripted normalization, never ranking."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.contracts.domain_types import ListingQuery
from app.domains.listings.browse_store import browse_statement
from app.domains.listings.lexical_expansion import (
    compile_expansion,
    normalization_inputs,
    plan_expansion,
)
from app.domains.listings.vocabulary import load_vocabulary


def scripted_plan(text, vocabulary=None, replacements=None):
    """Provide token identities/explicit fixtures, not an English stemmer imitation."""
    vocabulary = vocabulary or load_vocabulary()
    normalized = {token: token for token in normalization_inputs(text, vocabulary)}
    normalized.update(replacements or {})
    return plan_expansion(text, vocabulary, normalized)


def test_vehicle_directionality_and_original_preservation():
    plan = scripted_plan("vehicle")
    assert plan.outcome == "expanded"
    assert {
        "vehicle",
        "bicycle",
        "cycle",
        "motorcycle",
        "motorbike",
        "car",
        "automobile",
        "scooter",
    } <= set(plan.parameters)
    reverse = scripted_plan("cycle")
    assert set(reverse.parameters) == {"cycle", "bicycle"}
    assert "car" not in reverse.parameters
    assert plan.parameters[0] == "vehicle"


def test_books_and_textbooks_are_directional():
    plan = scripted_plan("books", replacements={"books": "book"})
    assert {"books", "book", "textbook", "text book"} <= set(plan.parameters)
    narrow = scripted_plan("textbook")
    assert "book" not in narrow.parameters
    assert "text book" in narrow.parameters


@pytest.mark.parametrize("text", ["bike", "notebook", "display", "bookcase", "quasar"])
def test_ambiguous_unknown_and_substrings_stay_plain(text):
    plan = scripted_plan(text)
    assert plan.parameters == (text,)
    assert plan.outcome == "no_concept"


def test_longest_phrase_and_independent_terms():
    laptop = scripted_plan("notebook computer")
    assert "laptop" in laptop.parameters
    assert laptop.sql.count(" && ") == 0
    phone = scripted_plan("red mobile phone")
    assert phone.sql.count(" && ") == 1
    assert "red" in phone.parameters and "smartphone" in phone.parameters
    assert "phraseto_tsquery" in phone.sql
    both = scripted_plan("book chair")
    assert both.sql.count(" && ") == 1
    assert both.parameters[0] == "book chair"


def test_stopwords_do_not_create_empty_and_group():
    plan = scripted_plan("the book", replacements={"the": ""})
    assert plan.outcome == "expanded"
    assert " && " not in plan.sql
    assert plan.parameters[0] == "the book"


@pytest.mark.parametrize(
    "text",
    [
        "vehicle | helmet",
        "bicycle'); SELECT 1; --",
        "bicycle-helmet",
        "véhicule",
        "book 123",
        "!!!",
    ],
)
def test_parser_sensitive_inputs_preserve_whole_original_query(text):
    plan = scripted_plan(text)
    assert plan.outcome == "original_input_shape"
    assert plan.parameters == (text,)
    assert text not in plan.sql


def test_case_and_phrase_normalization():
    plan = scripted_plan("MOBILE PHONES", replacements={"phones": "phone"})
    assert "smartphone" in plan.parameters
    assert plan.parameters[0] == "MOBILE PHONES"


@pytest.mark.parametrize(
    "text, settings",
    [
        (" ".join(["book"] * 13), {}),
        (" ".join(["electronics"] * 6), {}),
        ("vehicle", {"max_alternatives_per_concept": 2}),
    ],
)
def test_budgets_fall_back_as_a_whole(text, settings):
    plan = scripted_plan(text, replace(load_vocabulary(), **settings))
    assert plan.outcome == "expansion_budget"
    assert plan.parameters == (text,)


def test_missing_or_colliding_database_normalization_rejected():
    vocabulary = load_vocabulary()
    with pytest.raises(ValueError, match="Incomplete"):
        plan_expansion("vehicle", vocabulary, {})
    with pytest.raises(ValueError, match="Ambiguous"):
        scripted_plan("vehicle", replacements={"motorcycle": "bicycle"})


def test_sql_construction_preserves_filters_sort_and_parameter_count():
    text = "vehicle helmet"
    request = ListingQuery(
        q=text,
        page=2,
        negotiable=False,
        category_code="bicycles",
        min_price_paise=0,
        sort="price_asc",
    )
    now = datetime(2026, 10, 24, tzinfo=UTC)
    sql, parameters = browse_statement(
        request, now, 500000, text_query=scripted_plan(text)
    )
    assert text not in sql and text in parameters
    assert sql.count("%s") == len(parameters)
    assert "listing.search_vector @@ (" in sql
    assert "category.code = ANY(%s)" in sql and "listing.negotiable = %s" in sql
    assert "asking_price_paise >= %s" in sql
    assert "asking_price_paise ASC, listing.id ASC" in sql
    assert parameters[-2:] == (21, 20)
    assert any(value is False for value in parameters)
    baseline, values = browse_statement(request, now, 500000)
    assert "phraseto_tsquery" not in baseline
    assert "automobile" not in values


def test_async_normalization_uses_bound_postgresql_english_lookup():
    vocabulary = load_vocabulary()
    tokens = normalization_inputs("vehicle", vocabulary)
    connection = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchall.return_value = [
        {"token": token, "normalized": token} for token in tokens
    ]
    connection.execute.return_value = cursor
    plan = asyncio.run(compile_expansion(connection, "vehicle"))
    sql, values = connection.execute.await_args.args
    assert "plainto_tsquery('pg_catalog.english', token)" in sql
    assert values == (list(tokens),)
    assert plan.outcome == "expanded"
    connection.reset_mock()
    plain = asyncio.run(compile_expansion(connection, "bicycle | helmet"))
    assert plain.outcome == "original_input_shape"
    connection.execute.assert_not_awaited()


def test_default_store_path_never_calls_expansion(monkeypatch):
    """Keep activation closed even though the compiler and native opt-in exist."""
    from app.domains.listings import browse_store

    compiler = AsyncMock(side_effect=AssertionError("Expansion must stay inactive"))
    monkeypatch.setattr(browse_store, "compile_expansion", compiler)
    connection = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchall.return_value = []
    connection.execute.return_value = cursor
    page = asyncio.run(
        browse_store.read_browse_page(
            connection,
            ListingQuery(q="vehicle"),
            datetime(2026, 10, 24, tzinfo=UTC),
            500000,
        )
    )
    compiler.assert_not_awaited()
    assert page.items == ()
    sql, parameters = connection.execute.await_args.args
    assert "phraseto_tsquery" not in sql
    assert "vehicle" in parameters and "bicycle" not in parameters
