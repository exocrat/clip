"""Spelling/planning checks; PostgreSQL tests separately prove actual matching."""

import pytest

from app.domains.listings.typo_tolerance import (
    edit_cost,
    TypoBudget,
    TypoBudgetExceeded,
    find_typo,
    MAX_PHRASE_CHECKS,
)
from app.domains.listings.vocabulary import load_vocabulary
from app.domains.listings.lexical_expansion import normalization_inputs
from apps.api.tests.domains.listings.test_lexical_expansion import scripted_plan


@pytest.mark.parametrize(
    "source,target,cost",
    [
        ("bicyle", "bicycle", 1),
        ("bycicle", "bicycle", 2),
        ("phnoe", "phone", 1),
        ("tabel", "table", 1),
        ("boook", "book", 1),
        ("frige", "fridge", 1),
        ("refridgerator", "refrigerator", 1),
        ("bicycle", "bicycle", 0),
    ],
)
def test_bounded_edit_operations(source, target, cost):
    assert edit_cost(source, target, 2) == cost
    assert edit_cost(target, source, 2) == cost
    if cost == 2:
        assert edit_cost(source, target, 1) is None


@pytest.mark.parametrize(
    "source,target,limit",
    [
        ("bcy", "bicycle", 2),
        ("a" * 33, "a" * 32, 2),
        ("cycle", "cycle", True),
        ("cycle", "cycle", 3),
        ("cycle", "cycle", 0),
        ("", "book", 1),
    ],
)
def test_distance_caps(source, target, limit):
    assert edit_cost(source, target, limit) is None


@pytest.mark.parametrize(
    "query,expected",
    [
        ("bicyle", "bicycle"),
        ("bycicle", "bicycle"),
        ("PHNOE", "phone"),
        ("boook", "book"),
        ("frige", "refrigerator"),
        ("tabel", "table"),
        ("vehicel", "vehicle"),
        ("mobile phnoe", "phone"),
        ("notbook computer", "laptop"),
        ("washing machnie", "washing machine"),
    ],
)
def test_unique_typos_reach_only_controlled_concepts(query, expected):
    result = scripted_plan(query)
    assert result.outcome == "typo_expanded"
    assert result.parameters[0] == query and expected in result.parameters
    assert query not in result.sql
    assert len(result.parameters) <= 49


@pytest.mark.parametrize(
    "query",
    [
        "bike",
        "notebook",
        "display",
        "bookcase",
        "quasar",
        "deks",
        "fone",
        "carx",
        "tablex",
        "cicycle",
        "a" * 120,
    ],
)
def test_short_literal_ambiguous_unrelated_and_initial_errors_stay_plain(query):
    result = scripted_plan(query)
    assert result.outcome == "no_concept" and result.parameters == (query,)


def test_exact_normalized_matches_win_and_direction_stays_one_way():
    exact = scripted_plan("tables", replacements={"tables": "table"})
    assert exact.outcome == "expanded" and "tablet" not in exact.parameters
    broad = scripted_plan("vehicel")
    assert {"bicycle", "motorcycle", "car", "scooter"} <= set(broad.parameters)
    narrow = scripted_plan("bicyle")
    assert "vehicle" not in narrow.parameters and "car" not in narrow.parameters


def test_multiword_requirements_and_original_nonadjacent_matches_preserved():
    result = scripted_plan("red mobile phnoe")
    assert result.parameters[0] == "red mobile phnoe"
    assert result.sql.count(" && ") == 1 and "red" in result.parameters
    assert "mobile phone" in result.parameters and "phraseto_tsquery" in result.sql
    # Both corrected groups still require every independent word.
    both = scripted_plan("red bicyle phnoe")
    assert both.outcome == "typo_expanded" and both.sql.count(" && ") == 2
    multiple = scripted_plan("moblie phnoe")
    assert "moblie" in multiple.parameters and " && " in multiple.sql


def test_correction_and_work_budgets_fall_back_whole_query():
    query = "bicyle boook phnoe"
    result = scripted_plan(query)
    assert result.outcome == "typo_budget" and result.parameters == (query,)
    vocabulary = load_vocabulary()
    normalized = {word: word for word in normalization_inputs("bicyle", vocabulary)}
    with pytest.raises(TypoBudgetExceeded, match="typo_budget"):
        find_typo(
            ["bicyle"], 0, vocabulary, normalized, TypoBudget(checks=MAX_PHRASE_CHECKS)
        )


def test_same_owner_aliases_are_not_false_ambiguity():
    """Equidistant aliases may agree on one concept instead of competing owners."""
    from dataclasses import replace

    vocabulary = load_vocabulary()
    vocabulary = replace(
        vocabulary,
        concepts=tuple(
            (
                replace(concept, aliases=(*concept.aliases, "cyclet", "cyclex"))
                if concept.term == "bicycle"
                else concept
            )
            for concept in vocabulary.concepts
        ),
    )
    result = scripted_plan("cyclez", vocabulary)
    assert result.outcome == "typo_expanded"
    assert {"cycle", "bicycle", "cyclet", "cyclex"} <= set(result.parameters)


def test_close_real_word_is_preserved_but_can_add_an_extra_match():
    """Known-vocabulary distance cannot decide every unknown word's intent."""
    result = scripted_plan("chain")
    assert result.outcome == "typo_expanded"
    assert result.parameters[0] == "chain" and "chair" in result.parameters
