"""Exercise the Search-owned Listings boundary using shared synthetic fixtures."""

import asyncio
from datetime import UTC, datetime

import pytest

from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.core.pagination import Page
from app.contracts.domain_types import (
    ListingQuery,
    ListingSummary,
    SaveTargetResult,
)
from clip_test_fixtures import Fail, Return, make_provider_scenarios
from apps.api.tests.domains.search.doubles.listings import SearchListingsDouble


def listing_page(ids):
    """Create one safe synthetic listing summary for contract consumer tests."""
    item = ListingSummary(
        listing_id=ids.listing_id,
        title="Synthetic title",
        description="Synthetic description",
        category_code="synthetic-category",
        category_label="Synthetic category",
        condition_code="synthetic-condition",
        condition_label="Synthetic condition",
        asking_price_paise=100,
        negotiable=False,
        pickup_area="Synthetic area",
        available_from=datetime(2026, 1, 1, tzinfo=UTC),
        available_until=None,
        availability="available",
        sensitive_purchase=False,
        image_ids=[],
    )
    return Page((item,), page=1, page_size=20, has_next=False)


def make_double(ids, clock, page, outcomes=None):
    """Build a fresh test-only adapter with no database or provider dependency."""
    return SearchListingsDouble(
        ids=ids,
        now=clock.now,
        query_scenarios=make_provider_scenarios(page, page),
        query_outcomes=outcomes,
    )


def test_success_and_duplicate_reads_keep_contract_shapes(
    synthetic_ids, synthetic_clock, regular_caller
):
    """Repeated read scenarios return the same typed page without new semantics."""
    page = listing_page(synthetic_ids)
    double = make_double(synthetic_ids, synthetic_clock, page)
    first = asyncio.run(double.query_available_listings(regular_caller, ListingQuery()))
    second = asyncio.run(
        double.query_available_listings(regular_caller, ListingQuery())
    )
    assert first == second == page


@pytest.mark.parametrize(
    ("failure", "status"), [("denied", 403), ("timeout", 503), ("unavailable", 503)]
)
def test_safe_failures_do_not_become_empty_success(
    failure, status, synthetic_ids, synthetic_clock, regular_caller
):
    """Denied and unavailable scripts preserve the shared safe error category."""
    page = listing_page(synthetic_ids)
    double = make_double(
        synthetic_ids,
        synthetic_clock,
        page,
        outcomes=(Fail(failure), Return(page)),
    )
    with pytest.raises(PublicError) as error:
        asyncio.run(double.query_available_listings(regular_caller, ListingQuery()))
    assert error.value.spec.status == status
    assert (
        asyncio.run(double.query_available_listings(regular_caller, ListingQuery()))
        == page
    )


def test_expired_context_is_rejected_with_shared_fixed_clock(
    synthetic_ids, synthetic_clock, unauthenticated_callers
):
    """The PD-10 expired caller is checked against the explicitly injected time."""
    expired = unauthenticated_callers["expired"]
    assert isinstance(expired, CallerContext)
    page = listing_page(synthetic_ids)
    double = make_double(synthetic_ids, synthetic_clock, page)
    with pytest.raises(PublicError) as error:
        asyncio.run(double.query_available_listings(expired, ListingQuery()))
    assert error.value.spec.status == 401


def test_missing_target_is_safe_not_found_and_repeated_target_is_stable(
    synthetic_ids, synthetic_clock, regular_caller
):
    """Unknown IDs are indistinguishable, while duplicate reads are repeatable."""
    double = make_double(synthetic_ids, synthetic_clock, listing_page(synthetic_ids))
    expected = SaveTargetResult(listing_id=synthetic_ids.listing_id, discoverable=True)
    assert (
        asyncio.run(double.read_save_target(regular_caller, synthetic_ids.listing_id))
        == expected
    )
    assert (
        asyncio.run(double.read_save_target(regular_caller, synthetic_ids.listing_id))
        == expected
    )
    with pytest.raises(PublicError) as error:
        asyncio.run(
            double.read_save_target(regular_caller, synthetic_ids.other_listing_id)
        )
    assert error.value.spec.status == 404
