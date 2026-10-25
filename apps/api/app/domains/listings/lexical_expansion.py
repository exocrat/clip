"""Bounded PostgreSQL-normalized query expansion, pending native activation.

Only an explicit owned-store test opt-in uses this compiler. Public routes retain
the original query path until actual native checks pass. No Python stemmer,
semantic model, raw tsquery input or in-memory retrieval is supplied.
"""

from dataclasses import dataclass
import re
from typing import Any, Mapping

from psycopg import AsyncConnection

from app.domains.listings.vocabulary import Vocabulary, load_vocabulary
from app.domains.listings.typo_tolerance import (
    TypoBudget,
    TypoBudgetExceeded,
    find_typo,
)


@dataclass(frozen=True)
class TextQuery:
    """Code-owned SQL expression plus bound values and content-free run metadata."""

    sql: str
    parameters: tuple[object, ...]
    outcome: str
    vocabulary_fingerprint: str


_PLAIN = "plainto_tsquery('pg_catalog.english', %s)"
_PHRASE = "phraseto_tsquery('pg_catalog.english', %s)"


def normalization_inputs(text: str, vocabulary: Vocabulary) -> tuple[str, ...]:
    """Collect unique casefolded tokens for one authoritative PostgreSQL lookup.

    ASCII alphabetic whitespace queries are expandable. Other input keeps the
    exact original plain-text path, avoiding a second punctuation/Unicode parser.
    """
    tokens = text.lower().split()
    for concept in vocabulary.concepts:
        for phrase in (concept.term, *concept.aliases):
            tokens.extend(phrase.split())
    for phrase in vocabulary.literal_only:
        tokens.extend(phrase.split())
    return tuple(sorted(set(tokens)))


def plan_expansion(
    text: str, vocabulary: Vocabulary, normalized: Mapping[str, str]
) -> TextQuery:
    """Consume longest normalized phrases; OR alternatives and AND whole groups.

    `normalized` must come from PostgreSQL plain-query serialization, not a
    guessed stemmer. Unit tests may script it to verify planning only. The full
    original query is ORed with expanded groups to preserve existing matches,
    including nonadjacent original multiword terms. Only added alternatives
    require phrase adjacency. Any budget/shape issue falls back as a whole.
    """

    def plain(outcome: str) -> TextQuery:
        """Preserve every original term when expansion is unsuitable or too large."""
        return TextQuery(_PLAIN, (text,), outcome, vocabulary.fingerprint)

    if not re.fullmatch(r"[A-Za-z]+(?:\s+[A-Za-z]+)*", text.strip()):
        return plain("original_input_shape")
    tokens = text.lower().split()

    def signature(phrase: str) -> tuple[str, ...]:
        """Compare PostgreSQL-normalized words while preserving phrase boundaries."""
        return tuple(normalized[token] for token in phrase.split())

    expected = normalization_inputs(text, vocabulary)
    if not all(token in normalized for token in expected):
        raise ValueError("Incomplete PostgreSQL normalization")
    signatures: dict[tuple[str, ...], str] = {}
    by_term = {concept.term: concept for concept in vocabulary.concepts}
    literal = {signature(phrase) for phrase in vocabulary.literal_only}
    for concept in vocabulary.concepts:
        for phrase in (concept.term, *concept.aliases):
            key = signature(phrase)
            if (
                not all(key)
                or key in literal
                or (key in signatures and signatures[key] != concept.term)
            ):
                raise ValueError("Ambiguous PostgreSQL vocabulary normalization")
            signatures[key] = concept.term
    groups: list[tuple[str, tuple[str, ...]]] = []
    position = 0
    recognized = False
    typo_budget = TypoBudget()
    while position < len(tokens):
        term = None
        width = 1
        for size in range(
            min(vocabulary.max_phrase_words, len(tokens) - position), 0, -1
        ):
            key = tuple(
                normalized[token] for token in tokens[position : position + size]
            )
            if key in signatures:
                term, width = signatures[key], size
                break
        # Exact normalized phrases always win. Typo alternatives identify only
        # reviewed concept owners; the complete original query remains ORed in.
        if term is None:
            try:
                corrected = find_typo(
                    tokens, position, vocabulary, normalized, typo_budget
                )
            except TypoBudgetExceeded:
                return plain("typo_budget")
            if corrected is not None:
                term, width = corrected.term, corrected.width
        original = " ".join(tokens[position : position + width])
        alternatives = [original]
        if term is not None:
            recognized = True
            concept = by_term[term]
            alternatives.extend((concept.term, *concept.aliases))
            for child in concept.narrower:
                alternatives.extend((child, *by_term[child].aliases))
        alternatives = list(dict.fromkeys(alternatives))
        # Inflected original text may add one distinct spelling to the budget.
        if len(alternatives) > vocabulary.max_alternatives_per_concept:
            return plain("expansion_budget")
        if any(normalized[token] for token in tokens[position : position + width]):
            groups.append((original, tuple(alternatives)))
        position += width
    if not recognized:
        return plain("no_concept")
    if (
        len(groups) > vocabulary.max_concepts_per_query
        or sum(len(values) for _, values in groups) > vocabulary.max_total_alternatives
    ):
        return plain("expansion_budget")
    group_sql: list[str] = []
    parameters: tuple[object, ...] = (text,)
    for original, group_alternatives in groups:
        # Original group uses plain semantics; added multiword alternatives are
        # phrases. All strings remain bound parameters, never tsquery syntax.
        expressions = [
            _PLAIN if value == original else _PHRASE for value in group_alternatives
        ]
        group_sql.append("(" + " || ".join(expressions) + ")")
        parameters += group_alternatives
    if not group_sql:
        return plain("no_concept")
    return TextQuery(
        "(" + _PLAIN + " || (" + " && ".join(group_sql) + "))",
        parameters,
        "typo_expanded" if typo_budget.corrections else "expanded",
        vocabulary.fingerprint,
    )


async def compile_expansion(
    connection: AsyncConnection[dict[str, Any]], text: str
) -> TextQuery:
    """Normalize through the same DB configuration, then build the bounded plan.

    One additional read-only round trip checks all vocabulary/query tokens.
    No caching hides a different database configuration or normalization collision.
    This is not a latency claim. Query text is not logged or persisted.
    """
    vocabulary = load_vocabulary()
    if not re.fullmatch(r"[A-Za-z]+(?:\s+[A-Za-z]+)*", text.strip()):
        return TextQuery(
            _PLAIN, (text,), "original_input_shape", vocabulary.fingerprint
        )
    cursor = await connection.execute(
        "SELECT token, plainto_tsquery('pg_catalog.english', token)::text AS normalized "
        "FROM unnest(%s::text[]) AS input(token)",
        (list(normalization_inputs(text, vocabulary)),),
    )
    rows = await cursor.fetchall()
    return plan_expansion(
        text, vocabulary, {row["token"]: row["normalized"] for row in rows}
    )
