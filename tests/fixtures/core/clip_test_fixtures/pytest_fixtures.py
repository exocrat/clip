"""Opt-in pytest fixtures using approved shared types, without provider overrides."""

from collections.abc import Mapping
from types import MappingProxyType

import pytest

from app.core.auth import CallerContext
from app.core.errors import ERRORS, ErrorSpec
from clip_test_fixtures.samples import make_synthetic_clock, make_synthetic_ids
from clip_test_fixtures.scenarios import (
    AsyncBarrier,
    make_provider_scenarios,
    make_unauthenticated_callers,
    make_validation_cases,
)


@pytest.fixture
def synthetic_ids():
    """Supply schema-neutral user/listing references, fresh for each test."""
    return make_synthetic_ids()


@pytest.fixture
def synthetic_clock():
    """Supply a deterministic aware clock; callers must use it explicitly."""
    return make_synthetic_clock()


@pytest.fixture
def regular_caller(synthetic_ids, synthetic_clock):
    """Construct internal regular-user test facts; this authenticates no request."""
    return CallerContext(
        synthetic_ids.regular_user_id, "regular", synthetic_clock.valid_until
    )


@pytest.fixture
def temporary_caller(synthetic_ids, synthetic_clock):
    """Construct temporary-user facts without inventing domain permissions."""
    return CallerContext(
        synthetic_ids.temporary_user_id, "temporary", synthetic_clock.valid_until
    )


@pytest.fixture
def expected_errors() -> Mapping[int, ErrorSpec]:
    """Expose an immutable snapshot of approved error definitions, not a second registry."""
    return MappingProxyType(dict(ERRORS))


@pytest.fixture
def provider_scenarios(synthetic_ids):
    """Supply scripts with distinct synthetic listing references and no provider selection."""
    return make_provider_scenarios(
        synthetic_ids.listing_id, synthetic_ids.other_listing_id
    )


@pytest.fixture
def concurrency_barrier():
    """Supply a fresh two-task gate; tests own task creation and wait timeouts."""
    return AsyncBarrier()


@pytest.fixture
def unauthenticated_callers(synthetic_ids, synthetic_clock):
    """Supply invalid identity cases only; domain authorization remains separate."""
    return make_unauthenticated_callers(synthetic_ids, synthetic_clock)


@pytest.fixture
def validation_cases():
    """Supply immutable shared-format/boundary inputs with safe case names."""
    return make_validation_cases()
