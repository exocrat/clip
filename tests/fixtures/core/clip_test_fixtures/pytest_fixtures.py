"""Opt-in pytest fixtures using approved shared types, without provider overrides."""

from collections.abc import Mapping
from types import MappingProxyType

import pytest

from app.core.auth import CallerContext
from app.core.errors import ERRORS, ErrorSpec
from clip_test_fixtures.samples import make_synthetic_clock, make_synthetic_ids


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
