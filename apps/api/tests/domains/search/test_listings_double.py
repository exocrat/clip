"""Exercise the Search-owned Listings boundary using shared synthetic fixtures."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.core.pagination import Page
from app.contracts.domain_types import (
    ListingQuery,
    ListingSummary,
    SaveTargetResult,
    SavedListingState,
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


@pytest.mark.parametrize("state", ["unavailable", "future", "ended"])
def test_discovery_exclusion_does_not_remove_existing_saved_summary(
    state, synthetic_ids, synthetic_clock, regular_caller
):
    """Explicit fixture snapshots preserve the distinct public operation contracts.

    This exercises a test double, not a saved API/provider or SQL implementation.
    A seller flag can remain available after the window ends; only the separately
    scripted save-target operation supplies new-save discoverability here.
    """
    page = listing_page(synthetic_ids)
    listing = page.items[0].model_copy(deep=True)
    if state == "unavailable":
        listing.availability = "unavailable"
    elif state == "future":
        listing.available_from = synthetic_clock.now + timedelta(seconds=1)
    else:
        listing.available_until = synthetic_clock.now
    saved = SavedListingState(
        listing_id=synthetic_ids.listing_id, listing=listing, retired=False
    )
    empty = Page((), 1, 20, False)
    double = SearchListingsDouble(
        synthetic_ids,
        synthetic_clock.now,
        make_provider_scenarios(empty, empty),
        saved={synthetic_ids.listing_id: saved},
        save_targets={
            synthetic_ids.listing_id: SaveTargetResult(
                listing_id=synthetic_ids.listing_id, discoverable=False
            )
        },
    )
    assert (
        asyncio.run(
            double.query_available_listings(regular_caller, ListingQuery())
        ).items
        == ()
    )
    target = asyncio.run(
        double.read_save_target(regular_caller, synthetic_ids.listing_id)
    )
    assert target.discoverable is False
    resolved = asyncio.run(
        double.read_saved_listing_summaries(regular_caller, (synthetic_ids.listing_id,))
    )
    assert resolved == (saved,)
    assert (
        resolved[0].listing is not None and resolved[0].listing.title == listing.title
    )


def test_retired_saved_reference_has_no_retired_content(
    synthetic_ids, synthetic_clock, regular_caller
):
    """The reviewed fixture marker contains only the ID/null detail/retired flag."""
    marker = SavedListingState(
        listing_id=synthetic_ids.listing_id, listing=None, retired=True
    )
    page = Page((), page=1, page_size=20, has_next=False)
    double = SearchListingsDouble(
        synthetic_ids,
        synthetic_clock.now,
        make_provider_scenarios(page, page),
        saved={synthetic_ids.listing_id: marker},
        save_targets={},
    )
    result = asyncio.run(
        double.read_saved_listing_summaries(regular_caller, (synthetic_ids.listing_id,))
    )
    assert result[0].model_dump(mode="json") == {
        "listing_id": str(synthetic_ids.listing_id),
        "listing": None,
        "retired": True,
    }
    with pytest.raises(PublicError) as failure:
        asyncio.run(double.read_save_target(regular_caller, synthetic_ids.listing_id))
    assert failure.value.spec.status == 404


@pytest.mark.parametrize(
    "reason,status", [("denied", 403), ("timeout", 503), ("unavailable", 503)]
)
def test_saved_resolution_failure_fails_whole_page_without_partial_stale_success(
    reason, status, synthetic_ids, synthetic_clock, regular_caller
):
    """A valid first fixture must not hide a failed second dependency result."""
    page = listing_page(synthetic_ids)
    saved = SavedListingState(
        listing_id=synthetic_ids.listing_id, listing=page.items[0], retired=False
    )
    double = SearchListingsDouble(
        synthetic_ids,
        synthetic_clock.now,
        make_provider_scenarios(page, page),
        saved={
            synthetic_ids.listing_id: saved,
            synthetic_ids.other_listing_id: Fail(reason),
        },
    )
    with pytest.raises(PublicError) as failure:
        asyncio.run(
            double.read_saved_listing_summaries(
                regular_caller,
                (synthetic_ids.listing_id, synthetic_ids.other_listing_id),
            )
        )
    assert failure.value.spec.status == status


def test_save_target_failure_is_not_inferred_from_available_saved_summary(
    synthetic_ids, synthetic_clock, regular_caller
):
    """A stale display fixture cannot override a separately unavailable dependency."""
    page = listing_page(synthetic_ids)
    saved = SavedListingState(
        listing_id=synthetic_ids.listing_id, listing=page.items[0], retired=False
    )
    double = SearchListingsDouble(
        synthetic_ids,
        synthetic_clock.now,
        make_provider_scenarios(page, page),
        saved={synthetic_ids.listing_id: saved},
        save_targets={synthetic_ids.listing_id: Fail("unavailable")},
    )
    assert asyncio.run(
        double.read_saved_listing_summaries(regular_caller, (synthetic_ids.listing_id,))
    ) == (saved,)
    with pytest.raises(PublicError) as failure:
        asyncio.run(double.read_save_target(regular_caller, synthetic_ids.listing_id))
    assert failure.value.spec.status == 503


def test_fixture_rejects_retired_plaintext_and_mismatched_reference_ids(
    synthetic_ids, synthetic_clock
):
    """Do not let inconsistent doubles weaken the reviewed privacy boundary."""
    page = listing_page(synthetic_ids)
    invalid = SavedListingState(
        listing_id=synthetic_ids.listing_id, listing=page.items[0], retired=True
    )
    with pytest.raises(ValueError):
        SearchListingsDouble(
            synthetic_ids,
            synthetic_clock.now,
            make_provider_scenarios(page, page),
            saved={synthetic_ids.listing_id: invalid},
        )
    target = SaveTargetResult(
        listing_id=synthetic_ids.other_listing_id, discoverable=False
    )
    with pytest.raises(ValueError):
        SearchListingsDouble(
            synthetic_ids,
            synthetic_clock.now,
            make_provider_scenarios(page, page),
            save_targets={synthetic_ids.listing_id: target},
        )


def test_saved_resolution_checks_expiry_and_batch_bound(
    synthetic_ids, synthetic_clock, regular_caller, unauthenticated_callers
):
    """Private boundary fixtures never bypass shared expiry or the 100-ID limit."""
    double = make_double(synthetic_ids, synthetic_clock, listing_page(synthetic_ids))
    with pytest.raises(PublicError) as failure:
        asyncio.run(
            double.read_saved_listing_summaries(
                regular_caller, (synthetic_ids.listing_id,) * 101
            )
        )
    assert failure.value.spec.status == 422
    with pytest.raises(PublicError) as failure:
        asyncio.run(
            double.read_saved_listing_summaries(
                unauthenticated_callers["expired"], (synthetic_ids.listing_id,)
            )
        )
    assert failure.value.spec.status == 401
