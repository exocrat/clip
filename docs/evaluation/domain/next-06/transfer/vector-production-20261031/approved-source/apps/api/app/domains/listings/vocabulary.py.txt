"""Validate the curated vocabulary artifact; no query expansion or runtime wiring.

The immutable artifact is reviewed separately from activation. It carries no
listing IDs, judgments, executable SQL or public category replacements.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any


@dataclass(frozen=True)
class Concept:
    """An item term, equivalent aliases and direct one-way narrower concepts."""

    term: str
    aliases: tuple[str, ...]
    narrower: tuple[str, ...]


@dataclass(frozen=True)
class Vocabulary:
    """Immutable validated version, bounds and source fingerprint for later use."""

    version: str
    fingerprint: str
    concepts: tuple[Concept, ...]
    literal_only: tuple[str, ...]
    max_concepts_per_query: int
    max_alternatives_per_concept: int
    max_total_alternatives: int
    max_phrase_words: int


def _require(condition: bool) -> None:
    """Reject malformed controlled configuration with a content-free diagnostic."""
    if not condition:
        raise ValueError("Invalid search vocabulary")


def _fields(value: object, fields: set[str]) -> dict[str, Any]:
    """Reject unknown configuration fields rather than silently interpreting them."""
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("Invalid search vocabulary")
    return value


def _terms(value: object, max_words: int) -> tuple[str, ...]:
    """Require unique lowercase ASCII phrases; SQL/operator text is never a term."""
    if not isinstance(value, list):
        raise ValueError("Invalid search vocabulary")
    result: list[str] = []
    for item in value:
        _require(isinstance(item, str))
        _require(bool(re.fullmatch(r"[a-z]+(?: [a-z]+)*", item)))
        _require(len(item.split()) <= max_words and len(item) <= 120)
        result.append(item)
    _require(len(set(result)) == len(result))
    return tuple(result)


def validate_vocabulary(document: object) -> Vocabulary:
    """Validate shape, alias ownership, direct acyclic edges and expansion bounds.

    Child aliases contribute to a parent's one-hop budget. Recursive expansion
    is deliberately not defined. This validates configuration, not PostgreSQL
    lexemes, matching quality, category assignment or semantic inference.
    """
    doc = _fields(
        document,
        {"format_version", "vocabulary_version", "limits", "literal_only", "concepts"},
    )
    _require(type(doc["format_version"]) is int and doc["format_version"] == 1)
    version = doc["vocabulary_version"]
    _require(
        isinstance(version, str)
        and bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version))
    )
    limits = _fields(
        doc["limits"],
        {
            "max_concepts_per_query",
            "max_alternatives_per_concept",
            "max_total_alternatives",
            "max_phrase_words",
        },
    )
    _require(all(type(value) is int and 1 <= value <= 128 for value in limits.values()))
    _require(limits["max_phrase_words"] <= 3)
    _require(limits["max_alternatives_per_concept"] <= limits["max_total_alternatives"])
    literal = _terms(doc["literal_only"], limits["max_phrase_words"])
    _require(isinstance(doc["concepts"], list) and 0 < len(doc["concepts"]) <= 128)
    concepts: list[Concept] = []
    owned: set[str] = set(literal)
    for value in doc["concepts"]:
        row = _fields(value, {"term", "aliases", "narrower"})
        term = _terms([row["term"]], limits["max_phrase_words"])[0]
        aliases = _terms(row["aliases"], limits["max_phrase_words"])
        narrower = _terms(row["narrower"], limits["max_phrase_words"])
        names = {term, *aliases}
        _require(len(names) == len(aliases) + 1 and not owned.intersection(names))
        owned.update(names)
        concepts.append(Concept(term, aliases, narrower))
    by_term = {concept.term: concept for concept in concepts}
    for concept in concepts:
        _require(
            all(
                child in by_term and child != concept.term for child in concept.narrower
            )
        )
        alternatives = {concept.term, *concept.aliases}
        for child in concept.narrower:
            alternatives.update((child, *by_term[child].aliases))
        _require(len(alternatives) <= limits["max_alternatives_per_concept"])
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(term: str) -> None:
        """Reject accidental taxonomy cycles even though expansion is one-hop."""
        _require(term not in visiting)
        if term in visited:
            return
        visiting.add(term)
        for child in by_term[term].narrower:
            visit(child)
        visiting.remove(term)
        visited.add(term)

    for term in by_term:
        visit(term)
    fingerprint = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    return Vocabulary(version, fingerprint, tuple(concepts), literal, **limits)


def load_vocabulary() -> Vocabulary:
    """Read only the adjacent controlled artifact; no arbitrary input path/network."""
    path = Path(__file__).with_name("search_vocabulary.json")
    return validate_vocabulary(json.loads(path.read_text(encoding="utf-8")))
