"""Exercise shared pytest fixtures as a downstream API-test consumer."""

import pytest

from app.core.errors import PublicError


def test_shared_callers_use_approved_types_and_explicit_clock(
    synthetic_ids, synthetic_clock, regular_caller, temporary_caller
):
    """Synthetic contexts share explicit time without establishing HTTP authentication."""
    assert regular_caller.user_id == synthetic_ids.regular_user_id
    assert temporary_caller.user_id == synthetic_ids.temporary_user_id
    assert regular_caller.account_class == "regular"
    assert temporary_caller.account_class == "temporary"
    regular_caller.require_current(synthetic_clock.now)
    temporary_caller.require_current(synthetic_clock.now)
    with pytest.raises(PublicError) as captured:
        regular_caller.require_current(synthetic_clock.valid_until)
    assert captured.value.spec.code == "unauthenticated"


def test_expected_errors_reuse_canonical_definitions_without_mutation(expected_errors):
    """Consumers get safe common errors without introducing another registry."""
    assert expected_errors[401].code == "unauthenticated"
    assert expected_errors[403].code == "forbidden"
    assert expected_errors[422].code == "validation_error"
    with pytest.raises(TypeError):
        expected_errors[401] = expected_errors[403]
