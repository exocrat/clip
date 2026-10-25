"""Listings-owned collection read service implemented under SE-01.

Search consumes this public query boundary instead of reading private tables.
Browse, PostgreSQL text matching, reviewed filters and stable sorts are enabled.
No fake principal/store is selected.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from app.contracts.domain_types import (
    AvailableListingQuery,
    ListingSummary,
    ListingQuery,
    UserId,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
from app.core.pagination import Page
import app.domains.identity.public as identity_public
from app.domains.listings.service import ListingsIdentity
from app.domains.listings.browse_validation import normalize_query


class BrowseStore(Protocol):
    """Narrow owned persistence operation; it returns only discovery-safe fields."""

    async def browse_available_listings(
        self, request: ListingQuery, now: datetime
    ) -> Page[ListingSummary]:
        """Apply availability, native text and reviewed filters/sort before paging."""
        ...


class PublicBrowseIdentity:
    """Check eligibility for either reviewed account class through Identity."""

    async def account_is_eligible(self, user_id: UserId) -> bool:
        """Do not reuse seller-only eligibility or infer revocation from a token."""
        try:
            result = await identity_public.check_account_eligibility(
                user_id, required_class=None
            )
        except NotImplementedError, TimeoutError, OSError:
            raise PublicError(ERRORS[503]) from None
        return result.eligible


class ListingsBrowseService:
    """Implement the public query signature over owned SQL and trusted eligibility."""

    def __init__(
        self,
        store: BrowseStore,
        identity: ListingsIdentity,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind real adapters, or explicitly supplied test-only contract doubles."""
        self._store = store
        self._identity = identity
        self._clock = clock

    async def query_available_listings(
        self, caller: CallerContext, request: AvailableListingQuery
    ) -> Page[ListingSummary]:
        """Authorize before executing normalized, bounded search/filter/sort inputs.

        Regular and temporary callers can browse. A frozen clock is injectable
        for boundary tests; production evaluates one fresh instant per request.
        Numbered pages are stable for a fixed result set, not concurrent edits.
        """
        now = self._clock()
        caller.require_current(now)
        if not await self._identity.account_is_eligible(caller.user_id):
            raise PublicError(ERRORS[403])
        return await self._store.browse_available_listings(
            normalize_query(request), now
        )
