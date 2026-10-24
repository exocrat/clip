"""Exercise upload and cleanup recovery against controlled local doubles."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.contracts.domain_types import ImageUploadRequest
from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
from app.domains.listings.service import (
    AbandonedImageUpload,
    ConfirmedImage,
    InvalidImageContent,
    ListingsService,
    PendingImageUpload,
    RetiredListingImage,
    StoredImageMetadata,
)

NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)
OWNER_ID = UUID("10000000-0000-4000-8000-000000000001")
OTHER_ID = UUID("20000000-0000-4000-8000-000000000002")
IMAGE = b"\x89PNG\r\n\x1a\n" + b"IHDR" + b"synthetic-bytes"


@pytest.fixture(autouse=True)
def _fixed_authentication_clock(monkeypatch):
    """Align auth checks with this module's existing synthetic service clock.

    The fixture's one-day sessions must not expire as the calendar advances.
    Freeze only this test module's auth clock; keep real expiry comparison and
    all production code unchanged. Pytest restores the clock after each case.
    """
    import app.core.auth as auth

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz) if tz is not None else NOW.replace(tzinfo=None)

    monkeypatch.setattr(auth, "datetime", FixedDatetime)


class _Identity:
    """Allow only the two explicit test identities."""

    async def account_is_eligible(self, user_id: UUID) -> bool:
        return user_id in {OWNER_ID, OTHER_ID}


class _ImageStore:
    """Keep synthetic upload states and cleanup references in memory."""

    def __init__(self) -> None:
        self.uploads: dict[UUID, PendingImageUpload] = {}
        self.by_operation: dict[tuple[UUID, UUID], UUID] = {}
        self.retired: list[RetiredListingImage] = []
        self.abandoned: list[AbandonedImageUpload] = []
        self.finished: list[tuple[str, UUID, str]] = []
        self.deferred: list[tuple[str, UUID, str]] = []
        self.events: list[tuple[str, str]] = []

    async def create_image_upload(
        self,
        owner_id: UUID,
        request: ImageUploadRequest,
        upload_id: UUID,
        object_key: str,
        now: datetime,
    ) -> PendingImageUpload:
        key = (owner_id, request.operation_id)
        previous_id = self.by_operation.get(key)
        if previous_id is not None:
            previous = self.uploads[previous_id]
            if (
                previous.requested_media_type != request.media_type
                or previous.requested_size_bytes != request.size_bytes
            ):
                raise PublicError(ERRORS[409])
            return previous
        upload = PendingImageUpload(
            upload_id=upload_id,
            owner_id=owner_id,
            object_key=object_key,
            operation_id=request.operation_id,
            requested_media_type=request.media_type,
            requested_size_bytes=request.size_bytes,
            state="pending",
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        self.uploads[upload_id] = upload
        self.by_operation[key] = upload_id
        return upload

    async def read_image_upload(
        self, owner_id: UUID, upload_id: UUID
    ) -> PendingImageUpload | None:
        upload = self.uploads.get(upload_id)
        return upload if upload is not None and upload.owner_id == owner_id else None

    async def confirm_image_upload(
        self,
        owner_id: UUID,
        upload_id: UUID,
        media_type: str,
        size_bytes: int,
        now: datetime,
    ):
        upload = await self.read_image_upload(owner_id, upload_id)
        if upload is None:
            raise PublicError(ERRORS[404])
        if upload.state == "confirmed":
            if (
                upload.confirmed_media_type != media_type
                or upload.confirmed_size_bytes != size_bytes
            ):
                raise PublicError(ERRORS[409])
        elif upload.state != "pending" or upload.expires_at <= now:
            raise PublicError(ERRORS[409])
        else:
            upload = replace(
                upload,
                state="confirmed",
                confirmed_media_type=media_type,
                confirmed_size_bytes=size_bytes,
            )
            self.uploads[upload_id] = upload
        return ConfirmedImage(
            upload_id=upload_id, media_type=media_type, size_bytes=size_bytes
        )

    async def reject_image_upload(
        self, owner_id: UUID, upload_id: UUID, now: datetime
    ) -> bool:
        upload = await self.read_image_upload(owner_id, upload_id)
        if upload is None:
            return False
        self.uploads[upload_id] = replace(
            upload,
            state="expired" if upload.expires_at <= now else "failed",
        )
        return True

    async def cancel_image_upload(
        self, owner_id: UUID, upload_id: UUID, now: datetime
    ) -> bool:
        return await self.reject_image_upload(owner_id, upload_id, now)

    async def list_retired_images_for_cleanup(self, limit: int):
        return tuple(self.retired[:limit])

    async def list_abandoned_uploads_for_cleanup(self, limit: int):
        return tuple(self.abandoned[:limit])

    async def finish_retired_image_cleanup(self, image_id: UUID, object_key: str):
        self.events.append(("finish_retired", object_key))
        self.finished.append(("retired", image_id, object_key))
        self.retired = [item for item in self.retired if item.image_id != image_id]

    async def defer_retired_image_cleanup(self, image_id: UUID, object_key: str):
        self.events.append(("defer_retired", object_key))
        self.deferred.append(("retired", image_id, object_key))

    async def finish_abandoned_upload_cleanup(self, upload_id: UUID, object_key: str):
        self.events.append(("finish_abandoned", object_key))
        self.finished.append(("abandoned", upload_id, object_key))
        self.abandoned = [
            item for item in self.abandoned if item.upload_id != upload_id
        ]

    async def defer_abandoned_upload_cleanup(self, upload_id: UUID, object_key: str):
        self.events.append(("defer_abandoned", object_key))
        self.deferred.append(("abandoned", upload_id, object_key))


class _ImageStorage:
    """Fake signed storage whose outcomes can be changed by each test."""

    def __init__(self) -> None:
        self.objects: dict[str, StoredImageMetadata] = {}
        self.inspect_failures: list[Exception] = []
        self.invalid_keys: set[str] = set()
        self.upload_sign_failures = 0
        self.upload_signatures: list[tuple[str, str, datetime]] = []
        self.download_signatures: list[tuple[str, datetime]] = []
        self.delete_failures: dict[str, int] = {}
        self.deleted: list[str] = []
        self.events: list[tuple[str, str]] = []

    def object_key_for(self, upload_id: UUID) -> str:
        return f"private-test/listings/{upload_id}"

    async def create_upload_url(self, object_key, media_type, expires_at):
        self.upload_signatures.append((object_key, media_type, expires_at))
        if self.upload_sign_failures:
            self.upload_sign_failures -= 1
            raise TimeoutError("synthetic presign timeout")
        return f"https://storage.invalid/{object_key}"

    async def create_download_url(self, object_key, expires_at):
        self.download_signatures.append((object_key, expires_at))
        return f"https://storage.invalid/{object_key}?read=temporary"

    async def inspect_object(self, object_key):
        if self.inspect_failures:
            raise self.inspect_failures.pop(0)
        if object_key in self.invalid_keys:
            raise InvalidImageContent
        return self.objects.get(object_key)

    async def delete_object(self, object_key):
        self.events.append(("delete", object_key))
        self.deleted.append(object_key)
        failures = self.delete_failures.get(object_key, 0)
        if failures:
            self.delete_failures[object_key] = failures - 1
            raise TimeoutError("synthetic storage timeout")


class _Fixture:
    def __init__(self) -> None:
        self.store = _ImageStore()
        self.storage = _ImageStorage()
        self.service = ListingsService(
            self.store, _Identity(), clock=lambda: NOW, image_storage=self.storage
        )

    def caller(self, user_id: UUID = OWNER_ID, account_class: str = "regular"):
        return CallerContext(user_id, account_class, NOW + timedelta(days=1))

    def request(self, **updates) -> ImageUploadRequest:
        values = {
            "media_type": "image/png",
            "size_bytes": len(IMAGE),
            "operation_id": uuid4(),
        }
        values.update(updates)
        return ImageUploadRequest(**values)

    async def create_pending(self, request: ImageUploadRequest | None = None):
        result = await self.service.create_image_upload(
            self.caller(), request or self.request()
        )
        return result, self.store.uploads[result.upload_id]


def _status(error: PublicError) -> int:
    return error.spec.status


def test_valid_upload_intent_is_owner_bound_and_url_expires_within_five_minutes():
    fixture = _Fixture()
    instruction, upload = asyncio.run(fixture.create_pending())

    assert upload.owner_id == OWNER_ID
    assert upload.object_key == fixture.storage.upload_signatures[0][0]
    assert instruction.required_headers == {
        "Content-Type": "image/png",
        "If-None-Match": "*",
    }
    assert instruction.url_expires_at == NOW + timedelta(minutes=5)


@pytest.mark.parametrize(
    "values",
    [
        {"size_bytes": 0},
        {"size_bytes": 10_485_761},
        {"media_type": "image/gif"},
    ],
    ids=["empty", "too-large", "unsupported-type"],
)
def test_upload_contract_rejects_invalid_size_or_type_before_storage(values):
    fixture = _Fixture()
    with pytest.raises(ValidationError):
        fixture.request(**values)
    assert fixture.storage.upload_signatures == []


def test_owner_cannot_confirm_or_read_another_sellers_upload():
    fixture = _Fixture()
    instruction, _ = asyncio.run(fixture.create_pending())

    with pytest.raises(PublicError) as captured:
        asyncio.run(
            fixture.service.confirm_image_upload(
                fixture.caller(OTHER_ID), instruction.upload_id
            )
        )

    assert _status(captured.value) == 404
    assert fixture.storage.inspect_failures == []
    assert fixture.storage.objects == {}


def test_ineligible_and_temporary_sellers_cannot_create_uploads():
    fixture = _Fixture()
    for caller in (
        fixture.caller(OTHER_ID, "temporary"),
        fixture.caller(uuid4()),
    ):
        with pytest.raises(PublicError) as captured:
            asyncio.run(fixture.service.create_image_upload(caller, fixture.request()))
        assert _status(captured.value) == 403
    assert fixture.store.uploads == {}
    assert fixture.storage.upload_signatures == []


def test_confirmation_inspects_bytes_once_and_duplicate_confirmation_is_safe():
    fixture = _Fixture()
    instruction, upload = asyncio.run(fixture.create_pending())
    fixture.storage.objects[upload.object_key] = StoredImageMetadata(
        media_type="image/png", size_bytes=len(IMAGE)
    )

    first = asyncio.run(
        fixture.service.confirm_image_upload(fixture.caller(), instruction.upload_id)
    )
    second = asyncio.run(
        fixture.service.confirm_image_upload(fixture.caller(), instruction.upload_id)
    )

    assert first == second
    assert fixture.store.uploads[instruction.upload_id].state == "confirmed"
    assert len(fixture.storage.inspect_failures) == 0


@pytest.mark.parametrize(
    "metadata",
    [
        StoredImageMetadata(media_type="image/jpeg", size_bytes=len(IMAGE)),
        StoredImageMetadata(media_type="image/png", size_bytes=len(IMAGE) + 1),
        StoredImageMetadata(media_type="image/png", size_bytes=10_485_761),
    ],
    ids=["type-mismatch", "declared-size-mismatch", "oversized-object"],
)
def test_invalid_or_mismatched_stored_image_is_rejected_and_not_confirmed(metadata):
    fixture = _Fixture()
    instruction, upload = asyncio.run(fixture.create_pending())
    fixture.storage.objects[upload.object_key] = metadata

    with pytest.raises(PublicError) as captured:
        asyncio.run(
            fixture.service.confirm_image_upload(
                fixture.caller(), instruction.upload_id
            )
        )

    assert _status(captured.value) == 422
    rejected = fixture.store.uploads[instruction.upload_id]
    assert rejected.state == "failed"
    assert rejected.object_key == upload.object_key
    assert rejected.confirmed_media_type is None


def test_invalid_image_bytes_are_rejected_and_key_is_preserved_for_cleanup():
    fixture = _Fixture()
    instruction, upload = asyncio.run(fixture.create_pending())
    fixture.storage.invalid_keys.add(upload.object_key)

    with pytest.raises(PublicError) as captured:
        asyncio.run(
            fixture.service.confirm_image_upload(
                fixture.caller(), instruction.upload_id
            )
        )

    assert _status(captured.value) == 422
    assert fixture.store.uploads[instruction.upload_id].state == "failed"
    assert fixture.store.uploads[instruction.upload_id].object_key == upload.object_key


def test_missing_object_stays_pending_so_the_same_intent_can_be_retried():
    fixture = _Fixture()
    instruction, upload = asyncio.run(fixture.create_pending())

    with pytest.raises(PublicError) as missing:
        asyncio.run(
            fixture.service.confirm_image_upload(
                fixture.caller(), instruction.upload_id
            )
        )
    assert _status(missing.value) == 404
    assert fixture.store.uploads[instruction.upload_id].state == "pending"

    fixture.storage.objects[upload.object_key] = StoredImageMetadata(
        media_type="image/png", size_bytes=len(IMAGE)
    )
    confirmed = asyncio.run(
        fixture.service.confirm_image_upload(fixture.caller(), instruction.upload_id)
    )
    assert confirmed.upload_id == instruction.upload_id


def test_storage_timeout_keeps_intent_pending_for_confirmation_retry():
    fixture = _Fixture()
    instruction, upload = asyncio.run(fixture.create_pending())
    fixture.storage.objects[upload.object_key] = StoredImageMetadata(
        media_type="image/png", size_bytes=len(IMAGE)
    )
    fixture.storage.inspect_failures.append(TimeoutError("private timeout detail"))

    with pytest.raises(PublicError) as captured:
        asyncio.run(
            fixture.service.confirm_image_upload(
                fixture.caller(), instruction.upload_id
            )
        )
    assert _status(captured.value) == 503
    assert "private timeout detail" not in str(captured.value)
    assert fixture.store.uploads[instruction.upload_id].state == "pending"

    confirmed = asyncio.run(
        fixture.service.confirm_image_upload(fixture.caller(), instruction.upload_id)
    )
    assert confirmed.upload_id == instruction.upload_id


def test_signing_timeout_keeps_idempotent_intent_for_retry_without_extension():
    fixture = _Fixture()
    request = fixture.request()
    fixture.storage.upload_sign_failures = 1

    with pytest.raises(PublicError) as captured:
        asyncio.run(fixture.service.create_image_upload(fixture.caller(), request))

    assert _status(captured.value) == 503
    assert len(fixture.store.uploads) == 1
    original = next(iter(fixture.store.uploads.values()))
    assert original.expires_at == NOW + timedelta(hours=24)

    instruction = asyncio.run(
        fixture.service.create_image_upload(fixture.caller(), request)
    )
    assert instruction.upload_id == original.upload_id
    assert fixture.store.uploads[original.upload_id].expires_at == original.expires_at
    assert len(fixture.store.uploads) == 1


def test_expired_intent_cannot_be_confirmed_or_revived():
    fixture = _Fixture()
    instruction, upload = asyncio.run(fixture.create_pending())
    fixture.store.uploads[instruction.upload_id] = replace(
        upload, expires_at=NOW - timedelta(seconds=1)
    )

    with pytest.raises(PublicError) as captured:
        asyncio.run(
            fixture.service.confirm_image_upload(
                fixture.caller(), instruction.upload_id
            )
        )
    assert _status(captured.value) == 409
    assert fixture.store.uploads[instruction.upload_id].state == "expired"
    assert fixture.storage.objects == {}


def test_cleanup_removes_object_before_metadata_for_retired_and_abandoned_images():
    fixture = _Fixture()
    retired = RetiredListingImage(uuid4(), "private/retired/photo")
    abandoned = AbandonedImageUpload(uuid4(), "private/abandoned/photo")
    fixture.store.retired = [retired]
    fixture.store.abandoned = [abandoned]
    fixture.storage.events = fixture.store.events

    deleted = asyncio.run(fixture.service.cleanup_image_objects(limit=2))

    assert deleted == 2
    assert fixture.storage.deleted == [retired.object_key, abandoned.object_key]
    assert fixture.store.events == [
        ("delete", retired.object_key),
        ("finish_retired", retired.object_key),
        ("delete", abandoned.object_key),
        ("finish_abandoned", abandoned.object_key),
    ]
    assert fixture.store.retired == []
    assert fixture.store.abandoned == []


@pytest.mark.parametrize("kind", ["retired", "abandoned"])
def test_failed_delete_retains_metadata_and_retries_after_unknown_outcome(kind):
    fixture = _Fixture()
    record_id = uuid4()
    key = f"private/{kind}/retry"
    if kind == "retired":
        fixture.store.retired = [RetiredListingImage(record_id, key)]
    else:
        fixture.store.abandoned = [AbandonedImageUpload(record_id, key)]
    fixture.storage.delete_failures[key] = 1
    fixture.storage.events = fixture.store.events

    with pytest.raises(PublicError) as first:
        asyncio.run(fixture.service.cleanup_image_objects())

    assert _status(first.value) == 503
    assert fixture.store.finished == []
    assert len(fixture.store.deferred) == 1
    assert fixture.store.events[0] == ("delete", key)
    assert fixture.store.events[1][0] == "defer_" + kind

    assert asyncio.run(fixture.service.cleanup_image_objects()) == 1
    assert fixture.store.finished == [(kind, record_id, key)]
    assert fixture.storage.deleted == [key, key]


@pytest.mark.parametrize("limit", [0, -1, 501, True])
def test_cleanup_refuses_invalid_or_oversized_batches(limit):
    fixture = _Fixture()
    with pytest.raises(ValueError, match="between 1 and 500"):
        asyncio.run(fixture.service.cleanup_image_objects(limit=limit))
    assert fixture.storage.deleted == []
