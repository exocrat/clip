"""Fixture-factory invariants independent of domain schemas or live providers."""

from dataclasses import FrozenInstanceError
from datetime import UTC

import pytest

from app.core.identifiers import format_id, parse_id
from app.core.timestamps import format_timestamp
from clip_test_fixtures import make_synthetic_clock, make_synthetic_ids


def test_reference_factories_are_deterministic_distinct_and_fresh():
    """Fixtures repeat across runs while different references never alias."""
    first, second = make_synthetic_ids(), make_synthetic_ids()
    assert first == second and first is not second
    values = (
        first.regular_user_id,
        first.temporary_user_id,
        first.listing_id,
        first.other_listing_id,
    )
    assert len(set(values)) == 4
    assert all(
        value.version == 4 and parse_id(format_id(value)) == value for value in values
    )


def test_fixture_clock_is_aware_fixed_and_ordered():
    """Clock fixtures never depend on wall time and serialize through shared UTC rules."""
    first, second = make_synthetic_clock(), make_synthetic_clock()
    assert first == second and first is not second
    assert first.expired_at < first.now < first.valid_until
    assert (
        first.now.tzinfo is first.valid_until.tzinfo is first.expired_at.tzinfo is UTC
    )
    assert format_timestamp(first.now) == "2026-01-01T12:00:00.000000Z"


def test_fixture_records_are_immutable_and_schema_neutral():
    """Prevent accidental cross-test mutation and speculative profile/listing fields."""
    ids = make_synthetic_ids()
    clock = make_synthetic_clock()
    with pytest.raises(FrozenInstanceError):
        ids.listing_id = ids.regular_user_id
    with pytest.raises(FrozenInstanceError):
        clock.now = clock.expired_at
    assert set(vars(ids)) == {
        "regular_user_id",
        "temporary_user_id",
        "listing_id",
        "other_listing_id",
    }
