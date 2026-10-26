"""Wanted request authorization and public dependency composition.

Real defaults call reviewed public interfaces; explicit test dependency overrides
may supply contract doubles. No identity/catalogue success fallback is provided.
"""

import asyncio
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.contracts.domain_types import (
    Category,
    CategoryDisplay,
    PageResult,
    WantedRequestOwnerView,
    WantedRequestPublic,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, FieldError, PublicError
import app.domains.identity.public as identity_public
import app.domains.listings.public as listings_public
from app.domains.listings.public import ListingsPublic
from app.domains.search.wanted_models import (
    WantedCreate,
    WantedPage,
    WantedPatch,
    WantedState,
    owner_view,
    public_view,
)
from app.domains.search.wanted_store import PostgresWantedStore


class WantedIdentity(Protocol):
    """Account-class-neutral eligibility; local tests may inject a fixed actor."""

    async def eligible(self, actor: UUID) -> bool:
        """Return current account eligibility for this trusted actor."""
        ...


class WantedDependencies(Protocol):
    """Narrow reviewed Identity and Listings operations, no private state."""

    async def eligible(self, actor: UUID) -> bool:
        """Check immediate expiry/revocation for either account class."""
        ...

    async def active_categories(self) -> tuple[Category, ...]:
        """Validate new assignment using active public codes."""
        ...

    async def category_display(
        self, codes: tuple[str, ...]
    ) -> tuple[CategoryDisplay, ...]:
        """Resolve historical labels without permitting inactive assignment."""
        ...


class PublicWantedDependencies:
    """Use the injected real Listings provider and the public Identity operation."""

    def __init__(
        self,
        listings: ListingsPublic | None = None,
        identity: WantedIdentity | None = None,
    ) -> None:
        """The app supplies Listings; only explicit test composition supplies Identity."""
        self.listings = listings_public if listings is None else listings
        self.identity = identity

    async def eligible(self, actor: UUID) -> bool:
        """Use the account-class-neutral eligibility operation."""
        if self.identity is not None:
            return await self.identity.eligible(actor)
        return (
            await identity_public.check_account_eligibility(actor, required_class=None)
        ).eligible

    async def active_categories(self) -> tuple[Category, ...]:
        """No local hardcoded or private-table category fallback."""
        return await self.listings.read_active_categories()

    async def category_display(
        self, codes: tuple[str, ...]
    ) -> tuple[CategoryDisplay, ...]:
        """Return current labels, including inactive historical codes."""
        return await self.listings.read_category_display(codes)


class WantedService:
    """Authorize before persistence and project reviewed response fields only."""

    def __init__(self, store: PostgresWantedStore, dependencies: WantedDependencies):
        """Inject persistence and public adapters, never a client-selected actor."""
        self.store, self.dependencies = store, dependencies

    async def authorize(self, caller: CallerContext) -> None:
        """Current trusted context plus live eligibility; both classes allowed."""
        caller.require_current(datetime.now(UTC))
        try:
            async with asyncio.timeout(2):
                eligible = await self.dependencies.eligible(caller.user_id)
        except NotImplementedError, TimeoutError, OSError:
            raise PublicError(ERRORS[503]) from None
        if type(eligible) is not bool:
            raise PublicError(ERRORS[503])
        if not eligible:
            raise PublicError(ERRORS[403])

    async def labels(self, codes: tuple[str, ...]) -> dict[str, str]:
        """One bounded display lookup per page; fail the whole page on gaps."""
        if not codes:
            return {}
        try:
            async with asyncio.timeout(2):
                values = await self.dependencies.category_display(codes)
        except NotImplementedError, TimeoutError, OSError:
            raise PublicError(ERRORS[503]) from None
        labels = {item.code: item.label for item in values}
        if set(labels) != set(codes) or len(labels) != len(values):
            raise PublicError(ERRORS[503])
        return labels

    async def resolve_label(self, code: str, assignment: bool) -> str:
        """Active validation for assignments; historical display for retained ones."""
        if not assignment:
            return (await self.labels((code,)))[code]
        try:
            async with asyncio.timeout(2):
                values = await self.dependencies.active_categories()
        except NotImplementedError, TimeoutError, OSError:
            raise PublicError(ERRORS[503]) from None
        for item in values:
            if item.code == code:
                return item.label
        raise PublicError(
            ERRORS[422], (FieldError("category_code", "active_category_required"),)
        )

    async def create(
        self, caller: CallerContext, request: WantedCreate
    ) -> WantedRequestOwnerView:
        """Save validated create and original response atomically under retry key."""
        await self.authorize(caller)
        return await self.store.write(
            caller.user_id,
            "create",
            request.operation_id,
            None,
            request.model_dump(mode="json", exclude={"operation_id"}),
            self.resolve_label,
        )

    async def edit(
        self, caller: CallerContext, identifier: UUID, request: WantedPatch
    ) -> WantedRequestOwnerView:
        """Preserve omission/null distinctions through normalized request intent."""
        await self.authorize(caller)
        return await self.store.write(
            caller.user_id,
            "edit",
            request.operation_id,
            identifier,
            request.model_dump(
                mode="json", exclude={"operation_id"}, exclude_unset=True
            ),
            self.resolve_label,
        )

    async def state(
        self, caller: CallerContext, identifier: UUID, request: WantedState
    ) -> WantedRequestOwnerView:
        """Close/reopen the same owned row; serialized with all other row writers."""
        await self.authorize(caller)
        return await self.store.write(
            caller.user_id,
            "state",
            request.operation_id,
            identifier,
            request.model_dump(mode="json", exclude={"operation_id"}),
            self.resolve_label,
        )

    async def read(
        self, caller: CallerContext, identifier: UUID
    ) -> WantedRequestPublic | WantedRequestOwnerView:
        """Open detail is public; only an owner can see unavailable owner detail."""
        await self.authorize(caller)
        row = await self.store.read(identifier, caller.user_id)
        view = owner_view(
            row, (await self.labels((row["category_code"],)))[row["category_code"]]
        )
        return public_view(view) if row["status"] == "open" else view

    async def listing(
        self, caller: CallerContext, page: WantedPage, *, own: bool = False
    ) -> PageResult[WantedRequestPublic] | PageResult[WantedRequestOwnerView]:
        """Paginate after visibility filtering; no author/private fields returned."""
        await self.authorize(caller)
        rows, has_next = await self.store.listing(caller.user_id if own else None, page)
        labels = await self.labels(
            tuple(dict.fromkeys(row["category_code"] for row in rows))
        )
        views = [owner_view(row, labels[row["category_code"]]) for row in rows]
        if own:
            return PageResult[WantedRequestOwnerView](
                items=views, page=page.page, page_size=page.page_size, has_next=has_next
            )
        return PageResult[WantedRequestPublic](
            items=[public_view(view) for view in views],
            page=page.page,
            page_size=page.page_size,
            has_next=has_next,
        )
