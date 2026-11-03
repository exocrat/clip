"""Batch image authorization must match detail visibility, including stale cards."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contracts.domain_types import ListingManagementView
from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.domains.listings.service import ListingsService, ListingImageDeliveryTarget


def test_batch_signs_only_visible_targets_and_checks_eligibility_once():
    """Hidden and nonexistent IDs have identical null results, without a page outage."""

    async def exercise():
        now = datetime.now(UTC)
        actor = CallerContext(uuid4(), "regular", now + timedelta(hours=1))
        visible, hidden, missing = uuid4(), uuid4(), uuid4()
        listing = ListingManagementView(
            listing_id=uuid4(),
            title="Synthetic photo fixture",
            description="Synthetic",
            category_code="books",
            category_label="Books",
            condition_code="good",
            condition_label="Good",
            asking_price_paise=0,
            original_price_paise=None,
            negotiable=False,
            pickup_area=None,
            available_from=now - timedelta(days=1),
            available_until=None,
            availability="available",
            sensitive_purchase=False,
            image_ids=[visible],
            proof_available=None,
            owner_id=uuid4(),
            revision=1,
            created_at=now,
            updated_at=now,
        )
        store, identity, storage = AsyncMock(), AsyncMock(), AsyncMock()
        identity.account_is_eligible.return_value = True
        store.read_images_for_delivery.return_value = {
            visible: ListingImageDeliveryTarget(listing, "synthetic-visible-key"),
            hidden: ListingImageDeliveryTarget(
                listing.model_copy(update={"availability": "unavailable"}),
                "synthetic-hidden-key",
            ),
        }
        storage.create_download_url.return_value = (
            "https://storage.example.invalid/synthetic"
        )
        service = ListingsService(
            store, identity, image_storage=storage, clock=lambda: now
        )
        result = await service.get_image_deliveries(
            actor, [visible, hidden, missing, visible]
        )
        assert len(result.items) == 3
        assert result.items[0].delivery.url_expires_at == now + timedelta(minutes=5)
        assert result.items[1].delivery is None and result.items[2].delivery is None
        identity.account_is_eligible.assert_awaited_once_with(actor.user_id)
        storage.create_download_url.assert_awaited_once_with(
            "synthetic-visible-key", now + timedelta(minutes=5)
        )
        identity.account_is_eligible.return_value = False
        with pytest.raises(PublicError):
            await service.get_image_deliveries(actor, [visible])
        assert store.read_images_for_delivery.await_count == 1

    asyncio.run(exercise())
