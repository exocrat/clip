"""UUIDv4 generation and canonical opaque wire identifiers."""

from uuid import UUID, uuid4


def new_id() -> UUID:
    """Generate an entity/request identifier without embedding creation time."""
    return uuid4()


def parse_id(value: str) -> UUID:
    """Parse a UUIDv4 string, rejecting alternate compact/URN wire forms."""
    if not isinstance(value, str):
        raise ValueError("Expected a UUIDv4 string")
    try:
        identifier = UUID(value)
    except ValueError, AttributeError:
        raise ValueError("Expected a UUIDv4 string") from None
    if identifier.version != 4 or str(identifier) != value.lower():
        raise ValueError("Expected a hyphenated UUIDv4 string")
    return identifier


def format_id(value: UUID) -> str:
    """Serialize a validated UUIDv4 to lowercase hyphenated text."""
    if not isinstance(value, UUID) or value.version != 4:
        raise ValueError("Expected a UUIDv4 identifier")
    return str(value)
