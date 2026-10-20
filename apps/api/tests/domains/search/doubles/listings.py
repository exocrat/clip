"""Search-owned deterministic Listings double for contract-boundary tests."""

from collections import deque
from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
from app.core.pagination import Page
from app.contracts.domain_types import (
    AvailableListingQuery,
    Category,
    CategoryCode,
    CategoryDisplay,
    ListingId,
    ListingSummary,
    SaveTargetResult,
    SavedListingState,
)
from app.domains.listings.public import ListingsPublic
from clip_test_fixtures import Fail, ProviderScenarios, Return, SyntheticIds


class SearchListingsDouble(ListingsPublic):
    """Implement Search's Listings dependency with synthetic, scripted results.

    The fake checks only the shared trusted-context expiry helper and a synthetic
    known-ID set. It does not authenticate requests, access persistence, or claim
    to implement Listings behavior. Failures map to safe shared error classes.
    """

    def __init__(
        self,
        ids: SyntheticIds,
        now: datetime,
        query_scenarios: ProviderScenarios[Page[ListingSummary]],
        saved: Mapping[ListingId, SavedListingState] | None = None,
        query_outcomes: Sequence[Fail | Return[Page[ListingSummary]]] | None = None,
    ) -> None:
        """Copy test-owned duplicate results and references for deterministic reads."""
        self._known_ids = {ids.listing_id}
        self._query_results = deque(
            query_outcomes if query_outcomes is not None else query_scenarios.duplicate
        )
        self._saved = dict(saved or {})
        self._now = now

    async def query_available_listings(
        self, caller: CallerContext, request: AvailableListingQuery
    ) -> Page[ListingSummary]:
        """Return one scripted page, or a safe failure without inventing success."""
        del request
        caller.require_current(self._now)
        if not self._query_results:
            raise AssertionError("Search Listings scenario script exhausted")
        result = self._query_results.popleft()
        if isinstance(result, Fail):
            status = {
                "denied": 403,
                "invalid": 422,
                "timeout": 503,
                "unavailable": 503,
            }[result.reason]
            raise PublicError(ERRORS[status])
        return result.value

    async def read_save_target(
        self, caller: CallerContext, listing_id: ListingId
    ) -> SaveTargetResult:
        """Return only the discoverability flag for a known synthetic listing."""
        caller.require_current(self._now)
        if listing_id not in self._known_ids:
            raise PublicError(ERRORS[404])
        return SaveTargetResult(listing_id=listing_id, discoverable=True)

    async def read_saved_listing_summaries(
        self, caller: CallerContext, listing_ids: tuple[ListingId, ...]
    ) -> tuple[SavedListingState, ...]:
        """Resolve only the supplied Search-owned references in their input order."""
        caller.require_current(self._now)
        if len(listing_ids) > 100:
            raise PublicError(ERRORS[422])
        return tuple(self._saved[item] for item in listing_ids if item in self._saved)

    async def read_active_categories(self) -> tuple[Category, ...]:
        """Return a stable, synthetic catalogue entry for consumer tests."""
        return (Category(code="synthetic-category", label="Synthetic category"),)

    async def read_category_display(
        self, codes: tuple[CategoryCode, ...]
    ) -> tuple[CategoryDisplay, ...]:
        """Echo requested codes with a test-only label; no product category claim."""
        return tuple(
            CategoryDisplay(code=code, label="Synthetic category", active=True)
            for code in sorted(set(codes))
        )
