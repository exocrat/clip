"""Test the Listings retirement coordinator through the reviewed API contract."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.contracts.domain_types import (
    OriginActivityRequest,
    OriginActivityResult,
    OriginOwnerContext,
    OriginRetirementCommand,
    RetirementMarkerResult,
)
from app.core.errors import ERRORS, PublicError
from app.domains.listings.service import ListingsService, PendingListingRetirement
from app.domains.listings.service import RetiredListingImage

NOW = datetime(2026, 10, 20, 12, tzinfo=UTC)
LISTING_ID = uuid4()


class _RetirementStore:
    """Keep one pending Listings request and its original cutoff across retries."""

    def __init__(self, *, eligible: bool = True) -> None:
        self.eligible = eligible
        self.pending: PendingListingRetirement | None = None
        self.begin_calls = 0
        self.clear_calls: list[tuple[UUID, UUID]] = []
        self.finalize_calls: list[tuple[UUID, PendingListingRetirement]] = []
        self.retired = False
        self.cleanup_images: list[RetiredListingImage] = []
        self.cleaned_images: list[tuple[UUID, str]] = []

    async def begin_listing_retirement(
        self, listing_id: UUID, operation_id: UUID, now: datetime
    ) -> PendingListingRetirement | None:
        self.begin_calls += 1
        if self.pending is not None:
            if self.pending.operation_id != operation_id:
                raise PublicError(ERRORS[409])
            return self.pending
        if not self.eligible:
            return None
        self.pending = PendingListingRetirement(
            operation_id=operation_id,
            cutoff_utc=now - timedelta(hours=2160),
        )
        return self.pending

    async def clear_listing_retirement_pending(
        self, listing_id: UUID, operation_id: UUID
    ) -> None:
        assert self.pending is not None
        assert self.pending.operation_id == operation_id
        self.clear_calls.append((listing_id, operation_id))
        self.pending = None

    async def finalize_listing_retirement(
        self, listing_id: UUID, pending: PendingListingRetirement, now: datetime
    ) -> None:
        assert self.pending == pending
        self.finalize_calls.append((listing_id, pending))
        self.pending = None
        self.retired = True

    async def list_retired_images_for_cleanup(
        self, limit: int
    ) -> tuple[RetiredListingImage, ...]:
        return tuple(self.cleanup_images[:limit])

    async def finish_retired_image_cleanup(
        self, image_id: UUID, object_key: str
    ) -> None:
        self.cleaned_images.append((image_id, object_key))
        self.cleanup_images = [
            image for image in self.cleanup_images if image.image_id != image_id
        ]


class _ConversationsDouble:
    """Return controlled activity and marker results without private-table reads."""

    def __init__(
        self,
        activity: OriginActivityResult | None = None,
        marker_results: list[RetirementMarkerResult | Exception] | None = None,
    ) -> None:
        self.activity = activity or OriginActivityResult(
            thread_count=0, latest_participant_write_at=None
        )
        self.marker_results = list(
            marker_results or [RetirementMarkerResult(outcome="marked", marked_count=0)]
        )
        self.activity_calls: list[tuple[OriginOwnerContext, OriginActivityRequest]] = []
        self.marker_calls: list[tuple[OriginOwnerContext, OriginRetirementCommand]] = []

    async def get_origin_activity(
        self, context: OriginOwnerContext, request: OriginActivityRequest
    ) -> OriginActivityResult:
        self.activity_calls.append((context, request))
        return self.activity

    async def mark_origin_retired(
        self, context: OriginOwnerContext, request: OriginRetirementCommand
    ) -> RetirementMarkerResult:
        self.marker_calls.append((context, request))
        result = self.marker_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _service(
    store: _RetirementStore,
    conversations: _ConversationsDouble,
    image_storage: object | None = None,
) -> ListingsService:
    class _IdentityUnused:
        async def account_is_eligible(self, user_id: UUID) -> bool:
            return True

    return ListingsService(
        store,
        _IdentityUnused(),
        clock=lambda: NOW,
        conversations=conversations,
        image_storage=image_storage,
    )


def test_ineligible_listing_does_not_call_conversations() -> None:
    store = _RetirementStore(eligible=False)
    conversations = _ConversationsDouble()

    result = asyncio.run(
        _service(store, conversations).retire_eligible_listing(LISTING_ID, uuid4())
    )

    assert result is None
    assert store.pending is None
    assert conversations.activity_calls == []
    assert conversations.marker_calls == []


def test_zero_thread_listing_uses_server_cutoff_then_finalizes_local_content() -> None:
    store = _RetirementStore()
    conversations = _ConversationsDouble()
    operation_id = uuid4()

    result = asyncio.run(
        _service(store, conversations).retire_eligible_listing(LISTING_ID, operation_id)
    )

    assert result == RetirementMarkerResult(outcome="marked", marked_count=0)
    assert conversations.activity_calls == [
        (
            OriginOwnerContext(origin_kind="sale_listing"),
            OriginActivityRequest(origin_kind="sale_listing", origin_id=LISTING_ID),
        )
    ]
    request = conversations.marker_calls[0][1]
    assert request.operation_id == operation_id
    assert request.origin_id == LISTING_ID
    assert request.cutoff_utc == NOW - timedelta(hours=2160)
    assert store.finalize_calls == [
        (
            LISTING_ID,
            PendingListingRetirement(
                operation_id=operation_id, cutoff_utc=request.cutoff_utc
            ),
        )
    ]
    assert store.pending is None
    assert store.retired
    assert store.clear_calls == []


def test_recent_activity_result_clears_pending_request() -> None:
    store = _RetirementStore()
    conversations = _ConversationsDouble(
        activity=OriginActivityResult(
            thread_count=1,
            latest_participant_write_at=NOW - timedelta(days=20),
        ),
        marker_results=[
            RetirementMarkerResult(outcome="blocked_recent_activity", marked_count=0)
        ],
    )
    operation_id = uuid4()

    result = asyncio.run(
        _service(store, conversations).retire_eligible_listing(LISTING_ID, operation_id)
    )

    assert result is not None and result.outcome == "blocked_recent_activity"
    assert store.pending is None
    assert store.clear_calls == [(LISTING_ID, operation_id)]


def test_incomplete_activity_response_fails_closed_and_keeps_pending() -> None:
    store = _RetirementStore()
    conversations = _ConversationsDouble(
        activity=OriginActivityResult.model_construct(
            thread_count=1, latest_participant_write_at=None
        )
    )
    operation_id = uuid4()

    with pytest.raises(PublicError) as captured:
        asyncio.run(
            _service(store, conversations).retire_eligible_listing(
                LISTING_ID, operation_id
            )
        )

    assert captured.value.spec.status == 503
    assert store.pending is not None
    assert store.pending.operation_id == operation_id
    assert conversations.marker_calls == []


def test_unknown_marker_result_retries_same_operation_and_cutoff() -> None:
    store = _RetirementStore()
    conversations = _ConversationsDouble(
        marker_results=[
            TimeoutError("synthetic timeout"),
            RetirementMarkerResult(outcome="marked", marked_count=1),
        ]
    )
    service = _service(store, conversations)
    operation_id = uuid4()

    with pytest.raises(PublicError) as captured:
        asyncio.run(service.retire_eligible_listing(LISTING_ID, operation_id))
    assert captured.value.spec.status == 503
    first_request = conversations.marker_calls[0][1]
    assert store.pending == PendingListingRetirement(
        operation_id=operation_id, cutoff_utc=first_request.cutoff_utc
    )

    result = asyncio.run(service.retire_eligible_listing(LISTING_ID, operation_id))

    assert result == RetirementMarkerResult(outcome="marked", marked_count=1)
    assert conversations.marker_calls[1][1] == first_request
    assert store.pending is None
    assert store.retired


def test_image_cleanup_deletes_object_before_forgetting_its_key() -> None:
    image_id = uuid4()
    image = RetiredListingImage(image_id=image_id, object_key="private/listing/image")
    store = _RetirementStore()
    store.cleanup_images = [image]

    class _StorageDouble:
        def __init__(self) -> None:
            self.deleted: list[str] = []

        async def delete_object(self, object_key: str) -> None:
            self.deleted.append(object_key)

    storage = _StorageDouble()
    cleaned = asyncio.run(
        _service(store, _ConversationsDouble(), storage).cleanup_retired_image_objects()
    )

    assert cleaned == 1
    assert storage.deleted == [image.object_key]
    assert store.cleaned_images == [(image_id, image.object_key)]
    assert store.cleanup_images == []


def test_unknown_image_delete_keeps_key_for_safe_retry() -> None:
    image = RetiredListingImage(image_id=uuid4(), object_key="private/listing/image")
    store = _RetirementStore()
    store.cleanup_images = [image]

    class _StorageDouble:
        def __init__(self) -> None:
            self.calls = 0

        async def delete_object(self, object_key: str) -> None:
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("synthetic unknown delete result")

    storage = _StorageDouble()
    service = _service(store, _ConversationsDouble(), storage)

    with pytest.raises(PublicError) as first_attempt:
        asyncio.run(service.cleanup_retired_image_objects())
    assert first_attempt.value.spec.status == 503
    assert store.cleanup_images == [image]
    assert store.cleaned_images == []

    assert asyncio.run(service.cleanup_retired_image_objects()) == 1
    assert storage.calls == 2
    assert store.cleanup_images == []


def test_different_operation_cannot_replace_an_unresolved_pending_request() -> None:
    store = _RetirementStore()
    conversations = _ConversationsDouble(
        marker_results=[TimeoutError("synthetic timeout")]
    )
    service = _service(store, conversations)
    original_id = uuid4()

    with pytest.raises(PublicError):
        asyncio.run(service.retire_eligible_listing(LISTING_ID, original_id))
    original_pending = store.pending

    with pytest.raises(PublicError) as captured:
        asyncio.run(service.retire_eligible_listing(LISTING_ID, uuid4()))

    assert captured.value.spec.status == 409
    assert store.pending == original_pending
    assert len(conversations.marker_calls) == 1
