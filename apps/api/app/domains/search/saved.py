"""Private save/unsave and current saved-state resolution via public Listings."""

import asyncio
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from app.contracts.domain_types import (
    PageResult,
    ListingSummary,
    SaveTargetResult,
    SavedListingAck,
    SavedListingState,
    SavedListingView,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
import app.domains.listings.public as listings_public
from app.domains.search.draft_matches import DraftIdentity
from app.domains.search.saved_store import PostgresSavedStore
from app.domains.search.wanted import PublicWantedDependencies
from app.domains.search.wanted_models import WantedPage


class SavedListingsBoundary(Protocol):
    """Only reviewed new-save check and same-caller saved-page summary resolver."""

    async def read_save_target(
        self, caller: CallerContext, listing_id: UUID
    ) -> SaveTargetResult:
        """Confirm current discoverability for a new reference, without details."""
        ...

    async def read_saved_listing_summaries(
        self, caller: CallerContext, listing_ids: tuple[UUID, ...]
    ) -> tuple[SavedListingState, ...]:
        """Resolve only IDs read from this caller's page; unavailable is retained."""
        ...


class SavedService:
    """Require live eligibility and fresh public state, never stale saved content."""

    def __init__(
        self,
        store: PostgresSavedStore,
        listings: SavedListingsBoundary = listings_public,
        identity: DraftIdentity | None = None,
    ):
        """Use real public defaults; explicit fixtures are test-only composition."""
        self.store, self.listings = store, listings
        self.identity = PublicWantedDependencies() if identity is None else identity

    async def authorize(self, caller: CallerContext) -> None:
        """Both account classes allowed; context expiry and live revocation precede SQL."""
        caller.require_current()
        try:
            async with asyncio.timeout(2):
                eligible = await self.identity.eligible(caller.user_id)
        except NotImplementedError, TimeoutError, OSError:
            raise PublicError(ERRORS[503]) from None
        if type(eligible) is not bool:
            raise PublicError(ERRORS[503])
        if not eligible:
            raise PublicError(ERRORS[403])

    async def save(self, caller: CallerContext, identifier: UUID) -> SavedListingAck:
        """Existing pair is idempotent; a new pair requires current save-target success.

        Duplicate acknowledgement reveals no listing content, including after
        unavailability/retirement. A target changing after its successful check
        does not invalidate the reference. No operation-content receipt is needed:
        the reviewed pair uniqueness itself defines save idempotency.
        """
        await self.authorize(caller)
        existing = await self.store.existing(caller.user_id, identifier)
        if existing is not None:
            return existing
        try:
            async with asyncio.timeout(2):
                target = await self.listings.read_save_target(caller, identifier)
            if (
                not isinstance(target, SaveTargetResult)
                or target.listing_id != identifier
                or type(target.discoverable) is not bool
            ):
                raise PublicError(ERRORS[503])
            if not target.discoverable:
                raise PublicError(ERRORS[404])
        except NotImplementedError, TimeoutError, OSError, ValidationError:
            raise PublicError(ERRORS[503]) from None
        return await self.store.save(caller.user_id, identifier)

    async def unsave(self, caller: CallerContext, identifier: UUID) -> None:
        """No Listings lookup or content access is needed to remove one's own pair."""
        await self.authorize(caller)
        await self.store.unsave(caller.user_id, identifier)

    async def listing(
        self, caller: CallerContext, page: WantedPage
    ) -> PageResult[SavedListingView]:
        """Resolve a complete fresh page; bad/missing states fail the whole response."""
        await self.authorize(caller)
        references, has_next = await self.store.page(caller.user_id, page)
        if not references:
            return PageResult(
                items=[], page=page.page, page_size=page.page_size, has_next=has_next
            )
        identifiers = tuple(row.listing_id for row in references)
        try:
            async with asyncio.timeout(2):
                states = await self.listings.read_saved_listing_summaries(
                    caller, identifiers
                )
            if not isinstance(states, tuple) or len(states) != len(identifiers):
                raise PublicError(ERRORS[503])
            mapped = {}
            for raw in states:
                if not isinstance(raw, SavedListingState):
                    raise PublicError(ERRORS[503])
                if type(raw.retired) is not bool or (
                    raw.listing is not None
                    and not isinstance(raw.listing, ListingSummary)
                ):
                    raise PublicError(ERRORS[503])
                # Revalidate field dictionaries, avoiding serializers on a broken
                # producer model; do not log/coerce malformed current-state data.
                data = dict(raw)
                if raw.listing is not None:
                    data["listing"] = dict(raw.listing)
                state = SavedListingState.model_validate(data, strict=True)
                if (
                    state.listing_id in mapped
                    or (state.retired != (state.listing is None))
                    or (
                        state.listing is not None
                        and state.listing.listing_id != state.listing_id
                    )
                ):
                    raise PublicError(ERRORS[503])
                mapped[state.listing_id] = state
            if set(mapped) != set(identifiers):
                raise PublicError(ERRORS[503])
        except NotImplementedError, TimeoutError, OSError, ValidationError:
            raise PublicError(ERRORS[503]) from None
        return PageResult[SavedListingView](
            items=[
                SavedListingView(
                    listing_id=row.listing_id,
                    saved_at=row.saved_at,
                    listing=mapped[row.listing_id].listing,
                    retired=mapped[row.listing_id].retired,
                )
                for row in references
            ],
            page=page.page,
            page_size=page.page_size,
            has_next=has_next,
        )
