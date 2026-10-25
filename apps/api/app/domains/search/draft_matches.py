"""Transient draft-title matches through the reviewed available Listings query.

No database/session/draft/history is owned here. Native indexed matching, current
availability, filtering and ordering are authoritative at the Listings boundary.
"""

import asyncio
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from app.contracts.domain_types import (
    AvailableListingQuery,
    DraftMatchResult,
    ListingSummary,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
from app.core.pagination import Page
import app.domains.listings.public as listings_public
from app.domains.search.wanted import PublicWantedDependencies
from app.domains.search.wanted_models import DraftTitle


class DraftIdentity(Protocol):
    """Allow eligible regular and temporary callers via public Identity."""

    async def eligible(self, actor: UUID) -> bool:
        """Return current capability, never infer it from draft content."""
        ...


class DraftListingQuery(Protocol):
    """Exact public Listings query signature; no private persistence dependency."""

    async def query_available_listings(
        self, caller: CallerContext, request: AvailableListingQuery
    ) -> Page[ListingSummary]:
        """Apply availability/text/order/page at the authoritative provider."""
        ...


class DraftMatchService:
    """Run one read-only query independently of wanted-request creation."""

    def __init__(
        self,
        listings: DraftListingQuery = listings_public,
        identity: DraftIdentity | None = None,
    ) -> None:
        """Default to real public adapters; tests inject explicit contract fixtures."""
        self.listings = listings
        self.identity = PublicWantedDependencies() if identity is None else identity

    async def match(self, caller: CallerContext, title: DraftTitle) -> DraftMatchResult:
        """Return at most20/newest public summaries or a safe dependency failure.

        An empty match set is successful. No category/budget/relevance/model
        choices are inferred from a draft. Provider failure never invokes create
        or turns into a fabricated empty result; UI submission is a separate call.
        """
        caller.require_current()
        try:
            async with asyncio.timeout(2):
                eligible = await self.identity.eligible(caller.user_id)
            if type(eligible) is not bool:
                raise PublicError(ERRORS[503])
            if not eligible:
                raise PublicError(ERRORS[403])
            query = AvailableListingQuery(
                q=title.draft_title,
                search_mode="keyword",
                sort="created_desc",
                page=1,
                page_size=20,
            )
            async with asyncio.timeout(2):
                page = await self.listings.query_available_listings(caller, query)
            if (
                not isinstance(page, Page)
                or type(page.page) is not int
                or page.page != 1
                or type(page.page_size) is not int
                or page.page_size != 20
                or type(page.has_next) is not bool
                or not isinstance(page.items, tuple)
                or len(page.items) > 20
                or (page.has_next and len(page.items) != 20)
            ):
                raise PublicError(ERRORS[503])
            items = [ListingSummary.model_validate(item) for item in page.items]
            if len({item.listing_id for item in items}) != len(items) or any(
                item.availability != "available" for item in items
            ):
                raise PublicError(ERRORS[503])
            return DraftMatchResult(items=items, has_more=page.has_next)
        except NotImplementedError, TimeoutError, OSError, ValidationError:
            raise PublicError(ERRORS[503]) from None
