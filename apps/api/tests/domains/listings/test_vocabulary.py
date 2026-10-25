"""Vocabulary configuration tests, independent of listing relevance judgments."""

import json
from pathlib import Path

import pytest

from app.domains.listings import vocabulary


@pytest.fixture
def document():
    """Read the actual controlled artifact for corruption checks without editing it."""
    return json.loads(
        Path(vocabulary.__file__).with_name("search_vocabulary.json").read_text()
    )


def test_versioned_vocabulary_has_multiple_item_domains():
    result = vocabulary.load_vocabulary()
    concepts = {concept.term: concept for concept in result.concepts}
    assert result.version == "1.0.0"
    assert result.fingerprint.startswith("sha256:")
    assert {
        "vehicle",
        "book",
        "furniture",
        "electronics",
        "appliance",
    } <= concepts.keys()
    assert concepts["bicycle"].aliases == ("cycle",)
    assert concepts["vehicle"].narrower == ("bicycle", "motorcycle", "car", "scooter")
    assert concepts["bicycle"].narrower == ()
    assert concepts["book"].narrower == ("textbook",)
    assert concepts["textbook"].narrower == ()
    assert result.literal_only == ("bike", "notebook", "display")
    assert "mobile phone" in concepts["phone"].aliases
    assert "notebook computer" in concepts["laptop"].aliases
    assert result.max_total_alternatives == 48


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(extra=True),
        lambda d: d.update(format_version=True),
        lambda d: d.update(vocabulary_version="latest"),
        lambda d: d["limits"].update(max_concepts_per_query=True),
        lambda d: d["limits"].update(max_total_alternatives=0),
        lambda d: d["limits"].update(max_phrase_words=4),
        lambda d: d["limits"].update(max_alternatives_per_concept=1),
        lambda d: d["concepts"][1]["aliases"].append("bike"),
        lambda d: d["concepts"][1]["aliases"].append("cycle"),
        lambda d: d["concepts"][1]["aliases"].append("car"),
        lambda d: d["concepts"][1]["aliases"].append("a | b"),
        lambda d: d["concepts"][1]["aliases"].append("four word item name"),
        lambda d: d["concepts"][0]["narrower"].append("missing"),
        lambda d: d["concepts"][0]["narrower"].append("vehicle"),
        lambda d: d["concepts"][1]["narrower"].append("vehicle"),
        lambda d: d["concepts"][0].update(extra=True),
    ],
)
def test_invalid_configuration_rejected(document, mutate):
    """Reject ambiguous ownership, unsafe phrases, cycles and unbounded settings."""
    mutate(document)
    with pytest.raises(ValueError, match="Invalid search vocabulary"):
        vocabulary.validate_vocabulary(document)


def test_fingerprint_repeatable_and_changes_with_content(document):
    original = vocabulary.validate_vocabulary(document)
    assert original == vocabulary.validate_vocabulary(document)
    document["vocabulary_version"] = "1.0.1"
    assert original.fingerprint != vocabulary.validate_vocabulary(document).fingerprint
