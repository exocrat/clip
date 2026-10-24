"""Check Listings' offer gate using the reviewed Conversations boundary.

These tests exercise Listings decisions and lock lifetime. The Conversations
double records accepted commands; it does not claim real offer persistence.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import AsyncIterator
from uuid import UUID, uuid4

import pytest

from app.contracts.domain_types import (
    ListingManagementView,
    ListingOfferCommand,
    OfferRevisionRequest,
    OfferView,
    OfferWithdrawalRequest,
)
from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.contracts.domain_types import AccountEligibility
from app.domains.identity import public as identity_public
from app.domains.listings.integrations import PublicListingsIdentity
from app.domains.listings.service import ListingsService


class _IdentityDouble:
    """Return eligibility only for the fixed synthetic account set."""

    def __init__(self, eligible: set[UUID]) -> None:
        self.eligible = eligible

    async def account_is_eligible(self, user_id: UUID) -> bool:
        return user_id in self.eligible


class _OfferStore:
    """Model the per-listing lock held by the PostgreSQL offer guard."""

    def __init__(self, listing: ListingManagementView | None) -> None:
        self.listing = listing
        self.lock = asyncio.Lock()
        self.availability_change_started = asyncio.Event()
        self.availability_change_finished = asyncio.Event()

    @asynccontextmanager
    async def listing_offer_guard(
        self, listing_id: UUID
    ) -> AsyncIterator[ListingManagementView | None]:
        async with self.lock:
            current = (
                self.listing
                if self.listing and self.listing.listing_id == listing_id
                else None
            )
            yield current

    async def make_unavailable(self) -> None:
        """Wait for an active offer command before changing seller availability."""
        self.availability_change_started.set()
        async with self.lock:
            assert self.listing is not None
            self.listing = self.listing.model_copy(
                update={"availability": "unavailable"}
            )
        self.availability_change_finished.set()


class _ConversationsDouble:
    """Record commands and optionally pause one write to expose lock ordering."""

    def __init__(self, *, pause_offer_write: bool = False) -> None:
        self.pause_offer_write = pause_offer_write
        self.commands: list[ListingOfferCommand] = []
        self.write_entered = asyncio.Event()
        self.allow_write_to_finish = asyncio.Event()

    async def persist_listing_offer(
        self, caller: CallerContext, request: ListingOfferCommand
    ) -> OfferView:
        self.commands.append(request)
        self.write_entered.set()
        if self.pause_offer_write:
            await self.allow_write_to_finish.wait()
        return OfferView(
            offer_id=request.offer_id or uuid4(),
            revision=(request.expected_revision or 0) + 1,
            amount_paise=request.amount_paise or 0,
            status="withdrawn" if request.action == "withdraw" else "submitted",
            updated_at=NOW,
            note_envelope=request.note_envelope,
        )


NOW = datetime(2026, 10, 20, 12, tzinfo=UTC)
OWNER_ID = uuid4()
BUYER_ID = uuid4()
LISTING_ID = uuid4()
CONVERSATION_ID = uuid4()
OFFER_ID = uuid4()


def _listing(*, availability: str = "available") -> ListingManagementView:
    return ListingManagementView(
        listing_id=LISTING_ID,
        title="Synthetic listing",
        description="Offer-boundary fixture",
        category_code="books",
        category_label="Books",
        condition_code="good",
        condition_label="Good",
        asking_price_paise=10_000,
        negotiable=True,
        pickup_area="Fixture area",
        available_from=NOW - timedelta(days=1),
        available_until=None,
        availability=availability,
        sensitive_purchase=False,
        image_ids=[],
        proof_available=None,
        owner_id=OWNER_ID,
        revision=1,
        selected_buyer_id=None,
        selected_conversation_id=None,
        created_at=NOW - timedelta(days=2),
        updated_at=NOW - timedelta(days=1),
    )


def _service(
    listing: ListingManagementView | None,
    *,
    eligible: set[UUID] | None = None,
    pause_offer_write: bool = False,
) -> tuple[ListingsService, _OfferStore, _ConversationsDouble]:
    store = _OfferStore(listing)
    conversations = _ConversationsDouble(pause_offer_write=pause_offer_write)
    service = ListingsService(
        store,
        _IdentityDouble(eligible if eligible is not None else {OWNER_ID, BUYER_ID}),
        clock=lambda: NOW,
        conversations=conversations,
    )
    return service, store, conversations


def _caller(user_id: UUID = BUYER_ID) -> CallerContext:
    # CallerContext checks wall-clock expiry independently of the frozen service clock.
    return CallerContext(user_id, "regular", NOW + timedelta(days=30))


@pytest.mark.parametrize(
    "expected_revision", [None, 2], ids=["first-submit", "revision"]
)
def test_submit_or_revise_offer_forwards_only_after_listing_is_discoverable(
    expected_revision: int | None,
) -> None:
    service, _, conversations = _service(_listing())
    request = OfferRevisionRequest(
        amount_paise=9_000,
        expected_revision=expected_revision,
        operation_id=uuid4(),
    )

    result = asyncio.run(
        service.submit_offer(_caller(), LISTING_ID, CONVERSATION_ID, request)
    )

    assert result.status == "submitted"
    assert conversations.commands == [
        ListingOfferCommand(
            action="submit",
            listing_id=LISTING_ID,
            conversation_id=CONVERSATION_ID,
            amount_paise=9_000,
            expected_revision=expected_revision,
            operation_id=request.operation_id,
        )
    ]


@pytest.mark.parametrize(
    "listing",
    [
        _listing(availability="unavailable"),
        _listing().model_copy(update={"available_from": NOW + timedelta(seconds=1)}),
        _listing().model_copy(update={"available_until": NOW}),
        None,
    ],
    ids=["unavailable", "not-yet-open", "window-ended", "retired-or-missing"],
)
def test_submit_offer_is_blocked_when_listing_cannot_accept_offers(
    listing: ListingManagementView | None,
) -> None:
    service, _, conversations = _service(listing)
    request = OfferRevisionRequest(amount_paise=9_000, operation_id=uuid4())

    with pytest.raises(PublicError) as captured:
        asyncio.run(
            service.submit_offer(_caller(), LISTING_ID, CONVERSATION_ID, request)
        )

    assert captured.value.spec.status in (404, 409)
    assert conversations.commands == []


def test_withdrawal_is_allowed_while_listing_is_ordinarily_unavailable() -> None:
    service, _, conversations = _service(_listing(availability="unavailable"))
    request = OfferWithdrawalRequest(
        offer_id=OFFER_ID, expected_revision=2, operation_id=uuid4()
    )

    result = asyncio.run(
        service.withdraw_offer(_caller(), LISTING_ID, CONVERSATION_ID, request)
    )

    assert result.status == "withdrawn"
    assert conversations.commands[0].action == "withdraw"
    assert conversations.commands[0].offer_id == OFFER_ID


def test_withdrawal_is_blocked_after_listing_is_retired() -> None:
    service, _, conversations = _service(None)
    request = OfferWithdrawalRequest(
        offer_id=OFFER_ID, expected_revision=2, operation_id=uuid4()
    )

    with pytest.raises(PublicError) as captured:
        asyncio.run(
            service.withdraw_offer(_caller(), LISTING_ID, CONVERSATION_ID, request)
        )

    assert captured.value.spec.status == 404
    assert conversations.commands == []


def test_offer_and_availability_change_share_the_listing_lock() -> None:
    async def scenario() -> None:
        service, store, conversations = _service(_listing(), pause_offer_write=True)
        request = OfferRevisionRequest(amount_paise=9_000, operation_id=uuid4())

        offer_task = asyncio.create_task(
            service.submit_offer(_caller(), LISTING_ID, CONVERSATION_ID, request)
        )
        await conversations.write_entered.wait()

        availability_task = asyncio.create_task(store.make_unavailable())
        await store.availability_change_started.wait()
        assert not store.availability_change_finished.is_set()

        conversations.allow_write_to_finish.set()
        result = await offer_task
        await availability_task

        assert result.status == "submitted"
        assert store.listing is not None
        assert store.listing.availability == "unavailable"

    asyncio.run(scenario())


def test_ineligible_buyer_cannot_reach_conversations_offer_write() -> None:
    service, _, conversations = _service(_listing(), eligible={OWNER_ID})
    request = OfferRevisionRequest(amount_paise=9_000, operation_id=uuid4())

    with pytest.raises(PublicError) as captured:
        asyncio.run(
            service.submit_offer(_caller(), LISTING_ID, CONVERSATION_ID, request)
        )

    assert captured.value.spec.status == 403
    assert conversations.commands == []


def test_seller_cannot_submit_an_offer_to_own_listing() -> None:
    service, _, conversations = _service(_listing())
    request = OfferRevisionRequest(amount_paise=9_000, operation_id=uuid4())

    with pytest.raises(PublicError) as captured:
        asyncio.run(
            service.submit_offer(
                _caller(OWNER_ID), LISTING_ID, CONVERSATION_ID, request
            )
        )

    assert captured.value.spec.status == 403
    assert conversations.commands == []


def test_temporary_buyer_is_denied_by_regular_identity_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temporary_user_id = uuid4()
    capability_calls: list[tuple[UUID, str | None]] = []

    async def check_account_eligibility(
        user_id: UUID, required_class: str | None = None
    ) -> AccountEligibility:
        capability_calls.append((user_id, required_class))
        return AccountEligibility(eligible=False)

    monkeypatch.setattr(
        identity_public, "check_account_eligibility", check_account_eligibility
    )
    store = _OfferStore(_listing())
    conversations = _ConversationsDouble()
    service = ListingsService(
        store,
        PublicListingsIdentity(),
        clock=lambda: NOW,
        conversations=conversations,
    )
    temporary_caller = CallerContext(
        temporary_user_id, "temporary", NOW + timedelta(days=30)
    )

    with pytest.raises(PublicError) as captured:
        asyncio.run(
            service.submit_offer(
                temporary_caller,
                LISTING_ID,
                CONVERSATION_ID,
                OfferRevisionRequest(amount_paise=9_000, operation_id=uuid4()),
            )
        )

    assert captured.value.spec.status == 403
    assert capability_calls == [(temporary_user_id, "regular")]
    assert conversations.commands == []
