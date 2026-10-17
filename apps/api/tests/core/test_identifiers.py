"""Public UUID representation and rejection boundaries."""

from uuid import UUID

import pytest

from app.core.identifiers import format_id, new_id, parse_id

SYNTHETIC_ID = "123e4567-e89b-42d3-a456-426614174000"


def test_generated_identifiers_are_opaque_uuid4_strings():
    """Generated IDs use UUIDv4 and round-trip through the canonical wire form."""
    first, second = new_id(), new_id()
    assert first.version == second.version == 4
    assert first != second
    assert parse_id(format_id(first)) == first
    assert str(first) == format_id(first)


def test_uppercase_input_normalizes_to_canonical_output():
    """Input case must not create different identities or noncanonical output."""
    assert format_id(parse_id(SYNTHETIC_ID.upper())) == SYNTHETIC_ID


@pytest.mark.parametrize(
    "value",
    [
        None,
        1,
        True,
        "",
        "not-a-uuid",
        " " + SYNTHETIC_ID,
        SYNTHETIC_ID.replace("-", ""),
        "urn:uuid:" + SYNTHETIC_ID,
        "{" + SYNTHETIC_ID + "}",
        "00000000-0000-0000-0000-000000000000",
        "123e4567-e89b-12d3-a456-426614174000",
    ],
)
def test_malformed_or_wrong_version_wire_ids_are_rejected(value):
    """Reject invalid identifiers instead of silently accepting alternate forms."""
    with pytest.raises(ValueError):
        parse_id(value)


@pytest.mark.parametrize("value", [SYNTHETIC_ID, None, UUID(int=0)])
def test_formatter_requires_a_validated_uuid4(value):
    """The serializer must not stringify arbitrary or wrong-version objects."""
    with pytest.raises(ValueError):
        format_id(value)
