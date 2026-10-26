"""Bounded spelling alternatives for reviewed vocabulary, never a general speller.

Exact PostgreSQL-normalized phrases take precedence in the caller. This helper
compares raw ASCII spellings only; it does not stem words, inspect listing text,
load a dictionary, log queries or guess arbitrary brand/product vocabulary.
"""

from dataclasses import dataclass
from typing import Mapping, Sequence

from app.domains.listings.vocabulary import Vocabulary

POLICY_VERSION = "known-vocabulary-typos-v1"
MAX_CORRECTED_GROUPS = 2
MAX_PHRASE_CHECKS = 512
MAX_WORD_LENGTH = 32


class TypoBudgetExceeded(ValueError):
    """Require the caller's complete original-query fallback, never partial edits."""


@dataclass
class TypoBudget:
    """Content-free per-query work/correction counters; never retained globally."""

    checks: int = 0
    corrections: int = 0


@dataclass(frozen=True)
class TypoMatch:
    """One unambiguous concept owner and input width; contains no user text."""

    term: str
    width: int


def edit_cost(source: str, target: str, maximum: int) -> int | None:
    """Count insertion/deletion/substitution/adjacent swap within at most2 edits.

    Words are <=32characters; a swap uses the row two positions back and cannot
    repeatedly edit overlapping transpositions. Return None beyond the bound.
    This is spelling distance only, never semantic similarity or normalization.
    """
    if (
        type(maximum) is not int
        or not 1 <= maximum <= 2
        or not 1 <= len(source) <= MAX_WORD_LENGTH
        or not 1 <= len(target) <= MAX_WORD_LENGTH
        or abs(len(source) - len(target)) > maximum
    ):
        return None
    previous = list(range(len(target) + 1))
    before_previous = previous
    for i, left in enumerate(source, start=1):
        current = [i]
        for j, right in enumerate(target, start=1):
            value = min(
                previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (left != right)
            )
            if i > 1 and j > 1 and left == target[j - 2] and source[i - 2] == right:
                value = min(value, before_previous[j - 2] + 1)
            current.append(value)
        before_previous, previous = previous, current
    return previous[-1] if previous[-1] <= maximum else None


def find_typo(
    tokens: Sequence[str],
    position: int,
    vocabulary: Vocabulary,
    normalized: Mapping[str, str],
    budget: TypoBudget,
) -> TypoMatch | None:
    """Find the longest unique closest owner after exact phrase matching failed.

    Require one changed word per phrase, same initial letter, input>=5letters,
    target>=4; allow one edit, or two when both words have>=7letters. Thus
    bicyle/bycicle can reach bicycle while short ambiguous words stay literal.
    Equivalent normalized words cost zero. Equal nearest owners are ambiguous;
    aliases for the same owner do not create false ambiguity. No reverse taxonomy
    edges or literal-only targets are introduced. Two corrections/512phrase
    comparisons bound a query; overflow raises for whole-query fallback.
    """
    literal = {
        tuple(normalized[word] for word in phrase.split())
        for phrase in vocabulary.literal_only
    }
    for width in range(min(vocabulary.max_phrase_words, len(tokens) - position), 0, -1):
        source = tokens[position : position + width]
        if tuple(normalized[word] for word in source) in literal:
            continue
        candidates: list[tuple[int, str]] = []
        for concept in vocabulary.concepts:
            for phrase in (concept.term, *concept.aliases):
                target = phrase.split()
                if len(target) != width:
                    continue
                budget.checks += 1
                if budget.checks > MAX_PHRASE_CHECKS:
                    raise TypoBudgetExceeded("typo_budget")
                cost = changed = 0
                for left, right in zip(source, target):
                    if normalized[left] == normalized[right]:
                        continue
                    if (
                        not normalized[left]
                        or len(left) < 5
                        or len(right) < 4
                        or left[0] != right[0]
                    ):
                        break
                    distance = edit_cost(
                        left, right, 2 if min(len(left), len(right)) >= 7 else 1
                    )
                    if distance is None:
                        break
                    cost += distance
                    changed += 1
                    if changed > 1:
                        break
                else:
                    if changed == 1:
                        candidates.append((cost, concept.term))
        if candidates:
            best = min(cost for cost, _ in candidates)
            owners = {term for cost, term in candidates if cost == best}
            if len(owners) != 1:
                # Do not try a shorter corrected prefix of an ambiguous phrase.
                return None
            budget.corrections += 1
            if budget.corrections > MAX_CORRECTED_GROUPS:
                raise TypoBudgetExceeded("typo_budget")
            return TypoMatch(owners.pop(), width)
    return None
