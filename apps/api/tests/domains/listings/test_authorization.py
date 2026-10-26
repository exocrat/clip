"""Check Listings response privacy and seller-only authorization boundaries."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.contracts.domain_types import (
    AvailabilityChange,
    ListingManagementView,
    ListingReplacement,
    PageQuery,
    SelectionChange,
)
from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.domains.listings.service import ListingsService

NOW = datetime(2026, 10, 21, 12, tzinfo=UTC)
OWNER_ID = uuid4()
BUYER_ID = uuid4()
OUTSIDER_ID = uuid4()
LISTING_ID = uuid4()
CONVERSATION_ID = uuid4()
IMAGE_ID = uuid4()


class _Identity:
    """Treat only the fixed test accounts as eligible."""

    async def account_is_eligible(self, user_id: UUID) -> bool:
        return user_id in {OWNER_ID, BUYER_ID, OUTSIDER_ID}


class _Store:
    """Expose one retained listing and record writes reached by the service."""

    def __init__(self, listing: ListingManagementView) -> None:
        self.listing = listing
        self.owner_list_user: UUID | None = None
        self.write_calls = 0

    async def read_listing(self, listing_id: UUID) -> ListingManagementView | None:
        return self.listing if listing_id == self.listing.listing_id else None

    async def list_owned_listings(self, owner_id: UUID, query: PageQuery):
        self.owner_list_user = owner_id
        items = (self.listing,) if owner_id == self.listing.owner_id else ()
        return SimpleNamespace(
            items=items,
            page=query.page,
            page_size=query.page_size,
            has_next=False,
        )

    async def category_and_condition_are_active(
        self, category_code: str, condition_code: str
    ) -> bool:
        return True

    async def previous_owner_command_result(self, *args):
        return None

    async def replace_listing(self, *args):
        self.write_calls += 1
        return self.listing

    async def change_availability(self, *args):
        self.write_calls += 1
        return self.listing

    async def set_selected_buyer(self, *args):
        self.write_calls += 1
        return self.listing


def _listing(*, availability: str = "available") -> ListingManagementView:
    return ListingManagementView(
        listing_id=LISTING_ID,
        title="Synthetic bicycle",
        description="Owner and public response boundary fixture",
        category_code="bicycles",
        category_label="Bicycles",
        condition_code="good",
        condition_label="Good",
        asking_price_paise=650_000,
        negotiable=False,
        pickup_area=None,
        available_from=NOW - timedelta(days=1),
        available_until=None,
        availability=availability,
        sensitive_purchase=True,
        image_ids=(IMAGE_ID,),
        proof_available=True,
        owner_id=OWNER_ID,
        revision=4,
        selected_buyer_id=BUYER_ID,
        selected_conversation_id=CONVERSATION_ID,
        created_at=NOW - timedelta(days=5),
        updated_at=NOW - timedelta(days=1),
    )


def _service(listing: ListingManagementView) -> tuple[ListingsService, _Store]:
    store = _Store(listing)
    return ListingsService(store, _Identity(), clock=lambda: NOW), store


def _caller(user_id: UUID) -> CallerContext:
    # CallerContext validates expiry against wall-clock time, independently of
    # the fixed service clock used by these behavior tests.
    return CallerContext(user_id, "regular", datetime(2099, 1, 1, tzinfo=UTC))


@pytest.mark.parametrize("viewer_id", [OWNER_ID, BUYER_ID, OUTSIDER_ID])
def test_public_detail_never_exposes_seller_or_selection_state(viewer_id: UUID):
    service, _ = _service(_listing())

    detail = asyncio.run(service.read_detail(_caller(viewer_id), LISTING_ID))
    data = detail.model_dump()

    assert data["sensitive_purchase"] is True
    assert data["proof_available"] is True
    for private_field in (
        "owner_id",
        "revision",
        "selected_buyer_id",
        "selected_conversation_id",
        "created_at",
        "updated_at",
        "upload_id",
        "object_key",
    ):
        assert private_field not in data


def test_only_owner_management_read_contains_selected_buyer_state():
    service, store = _service(_listing())

    owner_rows = asyncio.run(
        service.list_mine(_caller(OWNER_ID), PageQuery(page=1, page_size=20))
    )
    outsider_rows = asyncio.run(
        service.list_mine(_caller(OUTSIDER_ID), PageQuery(page=1, page_size=20))
    )

    assert store.owner_list_user == OUTSIDER_ID
    assert owner_rows.items[0].selected_buyer_id == BUYER_ID
    assert owner_rows.items[0].selected_conversation_id == CONVERSATION_ID
    assert outsider_rows.items == []


@pytest.mark.parametrize("command", ["replace", "availability", "selection"])
def test_non_owner_cannot_mutate_listing_or_selected_buyer(command: str):
    service, store = _service(_listing())
    if command == "replace":
        request = ListingReplacement(
            expected_revision=4,
            title="Changed bicycle",
            description="Changed description",
            category_code="bicycles",
            condition_code="good",
            asking_price_paise=650_000,
            negotiable=False,
            pickup_area=None,
            available_from=NOW - timedelta(days=1),
            available_until=None,
            proof_available=True,
            images=[{"source": "existing", "image_id": IMAGE_ID}],
            operation_id=uuid4(),
        )
        operation = service.replace(_caller(OUTSIDER_ID), LISTING_ID, request)
    elif command == "availability":
        request = AvailabilityChange(
            expected_revision=4,
            availability="unavailable",
            operation_id=uuid4(),
        )
        operation = service.change_availability(
            _caller(OUTSIDER_ID), LISTING_ID, request
        )
    else:
        request = SelectionChange(
            buyer_id=None,
            conversation_id=None,
            expected_revision=4,
            operation_id=uuid4(),
        )
        operation = service.set_selected_buyer(
            _caller(OUTSIDER_ID), LISTING_ID, request
        )

    with pytest.raises(PublicError) as captured:
        asyncio.run(operation)

    assert captured.value.spec.status == 403
    assert store.write_calls == 0


def test_unavailable_listing_is_readable_only_by_its_owner():
    service, _ = _service(_listing(availability="unavailable"))

    owner_detail = asyncio.run(service.read_detail(_caller(OWNER_ID), LISTING_ID))
    assert owner_detail.listing_id == LISTING_ID

    with pytest.raises(PublicError) as captured:
        asyncio.run(service.read_detail(_caller(BUYER_ID), LISTING_ID))
    assert captured.value.spec.status == 404


@pytest.mark.parametrize(
    ("available_from", "available_until", "availability", "publicly_visible"),
    [
        (NOW, NOW + timedelta(seconds=1), "available", True),
        (NOW + timedelta(seconds=1), None, "available", False),
        (NOW - timedelta(seconds=1), NOW, "available", False),
        (NOW - timedelta(seconds=1), None, "unavailable", False),
    ],
    ids=[
        "start-is-inclusive",
        "future-start",
        "end-is-exclusive",
        "seller-unavailable",
    ],
)
def test_public_detail_obeys_availability_window(
    available_from: datetime,
    available_until: datetime | None,
    availability: str,
    publicly_visible: bool,
):
    listing = _listing(availability=availability).model_copy(
        update={"available_from": available_from, "available_until": available_until}
    )
    service, _ = _service(listing)

    if publicly_visible:
        detail = asyncio.run(service.read_detail(_caller(BUYER_ID), LISTING_ID))
        assert detail.listing_id == LISTING_ID
    else:
        with pytest.raises(PublicError) as captured:
            asyncio.run(service.read_detail(_caller(BUYER_ID), LISTING_ID))
        assert captured.value.spec.status == 404

    # Owners keep their retained listing visible in management/detail reads.
    owner_detail = asyncio.run(service.read_detail(_caller(OWNER_ID), LISTING_ID))
    assert owner_detail.listing_id == LISTING_ID
