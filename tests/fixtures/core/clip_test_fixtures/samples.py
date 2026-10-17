"""Immutable deterministic inputs; these are not domain records or credentials."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.identifiers import parse_id


@dataclass(frozen=True)
class SyntheticIds:
    """Opaque synthetic user/listing references with no profile or schema fields."""

    regular_user_id: UUID
    temporary_user_id: UUID
    listing_id: UUID
    other_listing_id: UUID


@dataclass(frozen=True)
class SyntheticClock:
    """Fixed aware instants for tests that pass their clock explicitly."""

    now: datetime
    valid_until: datetime
    expired_at: datetime


def make_synthetic_ids() -> SyntheticIds:
    """Return fresh deterministic UUIDv4-shaped fixtures, not production ID generation."""
    return SyntheticIds(
        regular_user_id=parse_id("00000000-0000-4000-8000-000000000001"),
        temporary_user_id=parse_id("00000000-0000-4000-8000-000000000002"),
        listing_id=parse_id("00000000-0000-4000-8000-000000000003"),
        other_listing_id=parse_id("00000000-0000-4000-8000-000000000004"),
    )


def make_synthetic_clock() -> SyntheticClock:
    """Return a fixed UTC timeline without reading the machine clock or environment."""
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return SyntheticClock(now, now + timedelta(hours=1), now - timedelta(seconds=1))
