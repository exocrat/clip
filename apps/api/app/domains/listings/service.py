"""Listings-owned validation and seller/buyer command rules.

This module owns validation and authorization. Persistence and verified upload
inspection are supplied through ``ListingsStore``; no fake store is selected by
the running application.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import AsyncContextManager, Literal, Protocol
from uuid import UUID, uuid4

from app.core.auth import CallerContext
from app.core.errors import ERRORS, FieldError, PublicError
from app.core.pagination import Page
from app.contracts.domain_types import (
    AvailabilityChange,
    CategoryCode,
    CatalogueView,
    ConversationId,
    ConversationStartResult,
    ExistingListingConversationLookup,
    ListingConversationContext,
    CreateListingRequest,
    ExistingListingImage,
    ConfirmedImage,
    ImageId,
    ImageDelivery,
    ImageUploadRequest,
    ListingDetail,
    ListingId,
    ListingManagementView,
    ListingOfferCommand,
    ListingOwnerView,
    ListingReplacement,
    ListingThreadParticipantCheck,
    OfferRevisionRequest,
    OfferView,
    OfferWithdrawalRequest,
    OriginActivityRequest,
    OriginActivityResult,
    OriginOwnerContext,
    OriginRetirementCommand,
    ParticipantCheck,
    PageQuery,
    PageResult,
    RetirementMarkerResult,
    SelectionChange,
    UploadInstruction,
    UserId,
)


@dataclass(frozen=True)
class PendingListingRetirement:
    """The durable operation ID and cutoff that retries must send unchanged."""

    operation_id: UUID
    cutoff_utc: datetime


@dataclass(frozen=True)
class RetiredListingImage:
    """A retired image and its object key, retained until storage confirms deletion."""

    image_id: ImageId
    object_key: str


@dataclass(frozen=True)
class AbandonedImageUpload:
    """Expired unattached upload whose object must be removed before its row."""

    upload_id: ImageId
    object_key: str


@dataclass(frozen=True)
class PendingImageUpload:
    """Persisted owner-bound image intent, including its private object key."""

    upload_id: ImageId
    owner_id: UserId
    object_key: str
    operation_id: UUID
    requested_media_type: Literal["image/jpeg", "image/png", "image/webp"] | None
    requested_size_bytes: int | None
    state: Literal["pending", "confirmed", "failed", "expired"]
    created_at: datetime
    expires_at: datetime
    confirmed_media_type: Literal["image/jpeg", "image/png", "image/webp"] | None = None
    confirmed_size_bytes: int | None = None


@dataclass(frozen=True)
class StoredImageMetadata:
    """Verified type and actual byte count read from the stored object."""

    media_type: Literal["image/jpeg", "image/png", "image/webp"]
    size_bytes: int


@dataclass(frozen=True)
class ListingImageDeliveryTarget:
    """One retained image reference and the listing that controls its visibility."""

    listing: ListingManagementView
    object_key: str


class InvalidImageContent(Exception):
    """Stored bytes are oversized or do not match an allowed image signature."""


class ListingsImageStorage(Protocol):
    """Storage boundary for signed upload, inspection and later cleanup."""

    def object_key_for(self, upload_id: ImageId) -> str:
        """Build the private run-scoped key from a server-generated upload ID."""
        ...

    async def create_upload_url(
        self, object_key: str, media_type: str, expires_at: datetime
    ) -> str:
        """Sign one create-only upload request for a bounded time."""
        ...

    async def inspect_object(self, object_key: str) -> StoredImageMetadata | None:
        """Verify stored bytes and return their type/size, or None if absent."""
        ...

    async def delete_object(self, object_key: str) -> None:
        """Return only when deleted or already absent; raise on unknown outcomes."""
        ...

    async def create_download_url(self, object_key: str, expires_at: datetime) -> str:
        """Sign a short-lived read for one already-authorized image reference."""
        ...


class ListingsIdentity(Protocol):
    """Capability boundary to current eligibility owned by Identity."""

    async def account_is_eligible(self, user_id: UserId) -> bool:
        """Ask Identity's public capability operation; never read its tables."""
        ...


class ListingsStore(Protocol):
    """Storage boundary for Listings; adapters must enforce one transaction."""

    async def read_catalogue(self) -> CatalogueView:
        """Return active owned categories and conditions for form selection."""
        ...

    async def create_image_upload(
        self,
        owner_id: UserId,
        request: ImageUploadRequest,
        upload_id: ImageId,
        object_key: str,
        now: datetime,
    ) -> PendingImageUpload:
        """Create or replay one owner-scoped pending upload intent atomically."""
        ...

    async def read_image_upload(
        self, owner_id: UserId, upload_id: ImageId
    ) -> PendingImageUpload | None:
        """Read one upload intent only when it belongs to the authenticated owner."""
        ...

    async def confirm_image_upload(
        self,
        owner_id: UserId,
        upload_id: ImageId,
        media_type: Literal["image/jpeg", "image/png", "image/webp"],
        size_bytes: int,
        now: datetime,
    ) -> ConfirmedImage:
        """Confirm verified storage metadata in one owner-scoped transaction."""
        ...

    async def reject_image_upload(
        self, owner_id: UserId, upload_id: ImageId, now: datetime
    ) -> bool:
        """Persist invalid or expired state while retaining its object key."""
        ...

    async def cancel_image_upload(
        self, owner_id: UserId, upload_id: ImageId, now: datetime
    ) -> bool:
        """Mark an unattached intent failed for the approved cleanup path."""
        ...

    async def confirmed_images_belong_to(
        self, owner_id: UserId, image_ids: tuple[ImageId, ...]
    ) -> bool:
        """Check that every supplied image is confirmed, usable, and owner-bound."""
        ...

    async def category_and_condition_are_active(
        self, category_code: CategoryCode, condition_code: str
    ) -> bool:
        """Require active catalogue values for new and replacement listings."""
        ...

    async def create_listing(
        self,
        owner_id: UserId,
        request: CreateListingRequest,
        normalized_title: str,
        normalized_description: str,
        normalized_pickup_area: str | None,
        now: datetime,
    ) -> ListingDetail:
        """Create listing, attach confirmed uploads and save the original result atomically."""
        ...

    async def previous_create_command_result(
        self, owner_id: UserId, request: CreateListingRequest
    ) -> ListingDetail | None:
        """Replay a matching live create or conflict on changed/retired operation keys."""
        ...

    async def read_listing(self, listing_id: ListingId) -> ListingManagementView | None:
        """Read one non-retired listing with its ordered controlled references."""
        ...

    async def read_image_for_delivery(
        self, image_id: ImageId
    ) -> ListingImageDeliveryTarget | None:
        """Read an attached image and its visibility owner from one live listing."""
        ...

    async def list_owned_listings(
        self, owner_id: UserId, query: PageQuery
    ) -> Page[ListingManagementView]:
        """Return the caller's own listings in stable newest-first order."""
        ...

    async def replace_listing(
        self,
        owner_id: UserId,
        listing_id: ListingId,
        request: ListingReplacement,
        normalized_title: str,
        normalized_description: str,
        normalized_pickup_area: str | None,
        now: datetime,
    ) -> ListingManagementView:
        """Recheck uploads and replace atomically at the expected revision."""
        ...

    async def change_availability(
        self,
        owner_id: UserId,
        listing_id: ListingId,
        request: AvailabilityChange,
        now: datetime,
    ) -> ListingManagementView:
        """Apply an idempotent revision-guarded state/window change.

        The adapter owns the transaction and must update the continuous
        retirement-eligibility anchor from the approved lifecycle rules. It
        preserves buyer selection, rejects retired rows, and serializes with
        the offer guard below. It saves the request/result atomically with the
        update; retirement removes those saved results.
        """
        ...

    async def set_selected_buyer(
        self,
        owner_id: UserId,
        listing_id: ListingId,
        request: SelectionChange,
        now: datetime,
    ) -> ListingManagementView:
        """Change only the owner's buyer-selection fields at one revision.

        A set must recheck availability/window in the same write transaction;
        a clear may proceed while ordinarily unavailable. Operation-ID replay,
        owner checking, stale-revision conflict and retirement rejection are
        storage responsibilities. The original result is saved atomically;
        retirement removes it with the listing content.
        """
        ...

    async def previous_owner_command_result(
        self,
        owner_id: UserId,
        listing_id: ListingId,
        command_kind: Literal["availability", "selection"],
        request: AvailabilityChange | SelectionChange,
    ) -> ListingManagementView | None:
        """Replay an identical owner command before checking its old revision.

        The key is scoped to listing, command kind, and operation ID. The
        adapter returns the original result for the same key and typed intent,
        raises 409 if that key was used for different intent, and returns None
        when the operation has not been recorded. It must verify ownership.
        Retirement deletes these saved results, so retired commands follow the
        normal retired-state error path.
        """
        ...

    def listing_conversation_guard(
        self, listing_id: ListingId
    ) -> AsyncContextManager[ListingManagementView | None]:
        """Hold an origin-state lock compatible with the thread's FK key-share."""
        ...

    def listing_offer_guard(
        self, listing_id: ListingId
    ) -> AsyncContextManager[ListingManagementView | None]:
        """Serialize an offer call against availability changes and retirement.

        The guard yields the current non-retired listing or None and remains
        held until the caller exits. It must not expose or share a database
        session with Conversations. Its adapter must coordinate with
        ``change_availability`` and any future retirement writer.
        """
        ...

    async def begin_listing_retirement(
        self, listing_id: ListingId, operation_id: UUID, now: datetime
    ) -> PendingListingRetirement | None:
        """Check local eligibility and durably set or resume one pending request."""
        ...

    async def clear_listing_retirement_pending(
        self, listing_id: ListingId, operation_id: UUID
    ) -> None:
        """Clear only the matching pending request after a confirmed blocked result."""
        ...

    async def finalize_listing_retirement(
        self, listing_id: ListingId, pending: PendingListingRetirement, now: datetime
    ) -> None:
        """Scrub listing content and mark its images for cleanup in one transaction."""
        ...

    async def list_retired_images_for_cleanup(
        self, limit: int
    ) -> tuple[RetiredListingImage, ...]:
        """Return due retired-image work without removing its retry metadata."""
        ...

    async def defer_retired_image_cleanup(
        self, image_id: ImageId, object_key: str
    ) -> None:
        """Delay a failed deletion while retaining the retired image reference."""
        ...

    async def finish_retired_image_cleanup(
        self, image_id: ImageId, object_key: str
    ) -> None:
        """Remove image/upload metadata after storage confirms the object is absent."""
        ...

    async def list_abandoned_uploads_for_cleanup(
        self, limit: int
    ) -> tuple[AbandonedImageUpload, ...]:
        """Expire and return a bounded batch of unlinked, overdue uploads."""
        ...

    async def defer_abandoned_upload_cleanup(
        self, upload_id: ImageId, object_key: str
    ) -> None:
        """Delay a failed deletion while retaining the expired upload reference."""
        ...

    async def finish_abandoned_upload_cleanup(
        self, upload_id: ImageId, object_key: str
    ) -> None:
        """Remove an unattached upload row only after storage confirms absence."""
        ...


class ListingsConversations(Protocol):
    """Reviewed Conversations public calls used by Listings-owned commands."""

    async def open_or_create_listing_conversation(
        self, caller: CallerContext, request: ListingConversationContext
    ) -> ConversationStartResult:
        """Create the owner-authorized pair or return its existing thread."""
        ...

    async def find_existing_listing_conversation(
        self, caller: CallerContext, request: ExistingListingConversationLookup
    ) -> ConversationStartResult | None:
        """Read an exact buyer/listing pair without creating a thread."""
        ...

    async def check_listing_thread_participant(
        self, caller: CallerContext, request: ListingThreadParticipantCheck
    ) -> ParticipantCheck:
        """Confirm the candidate is the other member of this listing thread."""
        ...

    async def persist_listing_offer(
        self, caller: CallerContext, request: ListingOfferCommand
    ) -> OfferView:
        """Persist an offer mutation in Conversations-owned storage."""
        ...

    async def get_origin_activity(
        self, context: OriginOwnerContext, request: OriginActivityRequest
    ) -> OriginActivityResult:
        """Read the content-free participant activity summary for this listing."""
        ...

    async def mark_origin_retired(
        self, context: OriginOwnerContext, request: OriginRetirementCommand
    ) -> RetirementMarkerResult:
        """Request the all-or-none no-write marker for this listing's threads."""
        ...


def _field_error(field: str, code: str) -> PublicError:
    """Create a safe validation error containing field names and fixed codes only."""
    return PublicError(ERRORS[422], (FieldError(field, code),))


def _clean_text(field: str, value: str, maximum: int) -> str:
    """Trim outer whitespace and reject blank or overlong Unicode text."""
    cleaned = value.strip()
    if not cleaned:
        raise _field_error(field, "required")
    if len(cleaned) > maximum:
        raise _field_error(field, "too_long")
    return cleaned


async def _require_regular_eligible(
    caller: CallerContext, identity: ListingsIdentity
) -> None:
    """Require a current regular account using trusted server context and Identity."""
    caller.require_current()
    if caller.account_class != "regular":
        raise PublicError(ERRORS[403])
    if not await identity.account_is_eligible(caller.user_id):
        raise PublicError(ERRORS[403])


async def _require_eligible(caller: CallerContext, identity: ListingsIdentity) -> None:
    """Require a current account for buyer-side offer actions."""
    caller.require_current()
    if not await identity.account_is_eligible(caller.user_id):
        raise PublicError(ERRORS[403])


def _require_owner(caller: CallerContext, current: ListingManagementView) -> None:
    """Compare the trusted actor with the owner read from Listings storage."""
    if current.owner_id != caller.user_id:
        raise PublicError(ERRORS[403])


def _detail(view: ListingManagementView) -> ListingDetail:
    """Remove owner-only fields before returning a public detail response."""
    values = view.model_dump()
    for private_field in (
        "owner_id",
        "revision",
        "selected_buyer_id",
        "selected_conversation_id",
        "created_at",
        "updated_at",
    ):
        values.pop(private_field)
    return ListingDetail.model_validate(values)


class ListingsService:
    """Apply contract validation and owner checks around a Listings store."""

    def __init__(
        self,
        store: ListingsStore,
        identity: ListingsIdentity,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        conversations: ListingsConversations | None = None,
        image_storage: ListingsImageStorage | None = None,
    ) -> None:
        """Bind owned storage, Identity and optional Conversations/image services."""
        self._store = store
        self._identity = identity
        self._conversations = conversations
        self._clock = clock
        self._image_storage = image_storage

    async def create_image_upload(
        self, caller: CallerContext, request: ImageUploadRequest
    ) -> UploadInstruction:
        """Persist an owner-scoped intent and issue a five-minute create-only URL."""
        await _require_regular_eligible(caller, self._identity)
        if self._image_storage is None:
            raise PublicError(ERRORS[503])

        now = self._clock()
        upload_id = uuid4()
        object_key = self._image_storage.object_key_for(upload_id)
        intent = await self._store.create_image_upload(
            caller.user_id, request, upload_id, object_key, now
        )
        if (
            intent.state != "pending"
            or intent.expires_at <= now
            or intent.requested_media_type != request.media_type
            or intent.requested_size_bytes != request.size_bytes
        ):
            raise PublicError(ERRORS[409])

        url_expires_at = min(intent.expires_at, now + timedelta(minutes=5))
        try:
            upload_url = await self._image_storage.create_upload_url(
                intent.object_key, request.media_type, url_expires_at
            )
        except Exception:
            # The intent is durable. Repeating the same operation can mint a
            # fresh URL without extending the original 24-hour deadline.
            raise PublicError(ERRORS[503]) from None
        return UploadInstruction(
            upload_id=intent.upload_id,
            upload_url=upload_url,
            required_headers={
                "Content-Type": request.media_type,
                "If-None-Match": "*",
            },
            url_expires_at=url_expires_at,
        )

    async def confirm_image_upload(
        self, caller: CallerContext, upload_id: ImageId
    ) -> ConfirmedImage:
        """Confirm an owner's pending object only after inspecting its stored bytes."""
        await _require_eligible(caller, self._identity)
        if self._image_storage is None:
            raise PublicError(ERRORS[503])

        intent = await self._store.read_image_upload(caller.user_id, upload_id)
        if intent is None:
            raise PublicError(ERRORS[404])
        now = self._clock()
        if intent.state == "confirmed":
            if (
                intent.confirmed_media_type is None
                or intent.confirmed_size_bytes is None
            ):
                raise PublicError(ERRORS[503])
            return ConfirmedImage(
                upload_id=upload_id,
                media_type=intent.confirmed_media_type,
                size_bytes=intent.confirmed_size_bytes,
            )
        if intent.state != "pending":
            raise PublicError(ERRORS[409])
        if intent.expires_at <= now:
            await self._store.reject_image_upload(caller.user_id, upload_id, now)
            raise PublicError(ERRORS[409])

        try:
            stored = await self._image_storage.inspect_object(intent.object_key)
        except InvalidImageContent:
            if not await self._store.reject_image_upload(
                caller.user_id, upload_id, self._clock()
            ):
                raise PublicError(ERRORS[404])
            raise PublicError(
                ERRORS[422], (FieldError("image_upload", "invalid_image_content"),)
            ) from None
        except Exception:
            # A storage timeout has an unknown outcome. Leave the intent pending
            # so a retry can inspect the same create-only object safely.
            raise PublicError(ERRORS[503]) from None
        confirmed_at = self._clock()
        if intent.expires_at <= confirmed_at:
            await self._store.reject_image_upload(
                caller.user_id, upload_id, confirmed_at
            )
            raise PublicError(ERRORS[409])
        if stored is None:
            raise PublicError(ERRORS[404])
        if (
            stored.media_type != intent.requested_media_type
            or stored.size_bytes != intent.requested_size_bytes
            or not 1 <= stored.size_bytes <= 10_485_760
        ):
            if not await self._store.reject_image_upload(
                caller.user_id, upload_id, confirmed_at
            ):
                raise PublicError(ERRORS[404])
            raise PublicError(
                ERRORS[422], (FieldError("image_upload", "invalid_image_content"),)
            )
        return await self._store.confirm_image_upload(
            caller.user_id,
            upload_id,
            stored.media_type,
            stored.size_bytes,
            confirmed_at,
        )

    async def cancel_image_upload(
        self, caller: CallerContext, upload_id: ImageId
    ) -> None:
        """Cancel an unattached intent while retaining its key for safe cleanup."""
        await _require_eligible(caller, self._identity)
        found = await self._store.cancel_image_upload(
            caller.user_id, upload_id, self._clock()
        )
        if not found:
            raise PublicError(ERRORS[404])

    async def read_catalogue(self, caller: CallerContext) -> CatalogueView:
        """Read current catalogue labels for an eligible authenticated account."""
        await _require_eligible(caller, self._identity)
        return await self._store.read_catalogue()

    async def create(
        self, caller: CallerContext, request: CreateListingRequest
    ) -> ListingDetail:
        """Validate and create a fully image-backed listing for the signed-in seller."""
        await _require_regular_eligible(caller, self._identity)
        title = request.title.strip()
        description = request.description.strip()
        pickup_area = (
            request.pickup_area.strip() if request.pickup_area is not None else None
        )
        normalized_request = request.model_copy(
            update={
                "title": title,
                "description": description,
                "pickup_area": pickup_area,
            }
        )
        prior = await self._store.previous_create_command_result(
            caller.user_id, normalized_request
        )
        if prior is not None:
            return prior

        title = _clean_text("title", title, 120)
        description = _clean_text("description", description, 5000)
        if pickup_area is not None:
            pickup_area = _clean_text("pickup_area", pickup_area, 120)
        image_ids = tuple(request.image_upload_ids)
        if len(set(image_ids)) != len(image_ids):
            raise _field_error("image_upload_ids", "duplicates_not_allowed")
        now = self._clock()
        available_from = request.available_from or now
        if (
            request.available_until is not None
            and request.available_until <= available_from
        ):
            raise _field_error("available_until", "must_be_after_available_from")
        return await self._store.create_listing(
            caller.user_id,
            normalized_request,
            title,
            description,
            pickup_area,
            now,
        )

    async def read_detail(
        self, caller: CallerContext, listing_id: ListingId
    ) -> ListingDetail:
        """Return discoverable detail or the caller's own unavailable listing."""
        caller.require_current()
        if not await self._identity.account_is_eligible(caller.user_id):
            raise PublicError(ERRORS[403])
        view = await self._store.read_listing(listing_id)
        if view is None:
            raise PublicError(ERRORS[404])
        if view.owner_id != caller.user_id and not self._is_discoverable(view):
            raise PublicError(ERRORS[404])
        return _detail(view)

    async def get_image_delivery(
        self, caller: CallerContext, image_id: ImageId
    ) -> ImageDelivery:
        """Authorize the owning listing before signing a private S3 read URL."""
        await _require_eligible(caller, self._identity)
        if self._image_storage is None:
            raise PublicError(ERRORS[503])

        target = await self._store.read_image_for_delivery(image_id)
        if target is None:
            raise PublicError(ERRORS[404])
        if target.listing.owner_id != caller.user_id and not self._is_discoverable(
            target.listing
        ):
            # Match detail reads: a hidden listing does not disclose whether a
            # particular image ID exists.
            raise PublicError(ERRORS[404])

        now = self._clock()
        url_expires_at = now + timedelta(minutes=5)
        try:
            url = await self._image_storage.create_download_url(
                target.object_key, url_expires_at
            )
        except Exception:
            # Do not include the signed URL, object key, or provider error in
            # the public response or logs.
            raise PublicError(ERRORS[503]) from None
        return ImageDelivery(url=url, url_expires_at=url_expires_at)

    async def list_mine(
        self, caller: CallerContext, query: PageQuery
    ) -> PageResult[ListingManagementView]:
        """Return only the signed-in seller's management rows and selection state."""
        caller.require_current()
        if not await self._identity.account_is_eligible(caller.user_id):
            raise PublicError(ERRORS[403])
        page = await self._store.list_owned_listings(caller.user_id, query)
        return PageResult(
            items=list(page.items),
            page=page.page,
            page_size=page.page_size,
            has_next=page.has_next,
        )

    async def replace(
        self,
        caller: CallerContext,
        listing_id: ListingId,
        request: ListingReplacement,
    ) -> ListingDetail:
        """Replace the owner's full listing at its current revision."""
        await _require_regular_eligible(caller, self._identity)
        title = _clean_text("title", request.title, 120)
        description = _clean_text("description", request.description, 5000)
        # Explicit null clears the optional area in this full-replacement command.
        pickup_area = (
            _clean_text("pickup_area", request.pickup_area, 120)
            if request.pickup_area is not None
            else None
        )
        if not await self._store.category_and_condition_are_active(
            request.category_code, request.condition_code
        ):
            raise _field_error(
                "category_code", "active_category_and_condition_required"
            )
        image_keys = tuple(
            (
                ("existing", selection.image_id)
                if isinstance(selection, ExistingListingImage)
                else ("upload", selection.upload_id)
            )
            for selection in request.images
        )
        if len(set(image_keys)) != len(image_keys):
            raise _field_error("images", "duplicate_images_not_allowed")
        current = await self._store.read_listing(listing_id)
        if current is None:
            raise PublicError(ERRORS[404])
        if current.owner_id != caller.user_id:
            raise PublicError(ERRORS[403])
        now = self._clock()
        if (
            request.available_until is not None
            and request.available_until <= request.available_from
        ):
            raise _field_error("available_until", "must_be_after_available_from")
        view = await self._store.replace_listing(
            caller.user_id,
            listing_id,
            request,
            title,
            description,
            pickup_area,
            now,
        )
        return _detail(view)

    async def change_availability(
        self,
        caller: CallerContext,
        listing_id: ListingId,
        request: AvailabilityChange,
    ) -> ListingDetail:
        """Change seller availability/window without changing buyer selection."""
        await _require_regular_eligible(caller, self._identity)
        prior = await self._store.previous_owner_command_result(
            caller.user_id, listing_id, "availability", request
        )
        if prior is not None:
            return _detail(prior)
        current = await self._store.read_listing(listing_id)
        if current is None:
            raise PublicError(ERRORS[404])
        _require_owner(caller, current)

        # A missing start keeps the current start; a null end deliberately clears it.
        effective_start = request.available_from or current.available_from
        if (
            request.available_until is not None
            and request.available_until <= effective_start
        ):
            raise _field_error("available_until", "must_be_after_available_from")

        view = await self._store.change_availability(
            caller.user_id, listing_id, request, self._clock()
        )
        return _detail(view)

    async def set_selected_buyer(
        self,
        caller: CallerContext,
        listing_id: ListingId,
        request: SelectionChange,
    ) -> ListingOwnerView:
        """Set, replace, or clear the buyer selected by the listing's owner."""
        await _require_regular_eligible(caller, self._identity)
        prior = await self._store.previous_owner_command_result(
            caller.user_id, listing_id, "selection", request
        )
        if prior is not None:
            return ListingOwnerView.model_validate(prior.model_dump())
        current = await self._store.read_listing(listing_id)
        if current is None:
            raise PublicError(ERRORS[404])
        _require_owner(caller, current)

        has_buyer = request.buyer_id is not None
        has_conversation = request.conversation_id is not None
        if has_buyer != has_conversation:
            raise _field_error(
                "buyer_id", "buyer_and_conversation_must_both_be_set_or_cleared"
            )

        if request.buyer_id is not None and request.conversation_id is not None:
            if request.buyer_id == caller.user_id:
                raise PublicError(ERRORS[403])
            if not self._is_discoverable(current):
                raise PublicError(ERRORS[409])
            if not await self._identity.account_is_eligible(request.buyer_id):
                raise PublicError(ERRORS[403])
            conversations = self._require_conversations()
            try:
                membership = await conversations.check_listing_thread_participant(
                    caller,
                    ListingThreadParticipantCheck(
                        listing_id=listing_id,
                        conversation_id=request.conversation_id,
                        candidate_user_id=request.buyer_id,
                    ),
                )
            except NotImplementedError:
                raise PublicError(ERRORS[503]) from None
            if not membership.is_participant:
                raise PublicError(ERRORS[404])

        # The store repeats owner, revision and (when setting) availability checks
        # inside its transaction so a prior read or Conversations call cannot win
        # a race against a concurrent seller change.
        view = await self._store.set_selected_buyer(
            caller.user_id, listing_id, request, self._clock()
        )
        return ListingOwnerView.model_validate(view.model_dump())

    async def start_conversation(
        self, caller: CallerContext, listing_id: ListingId
    ) -> ConversationStartResult:
        """Serialize origin state with a bounded, independently committed chat call.

        Pair uniqueness defines retries; an ambiguous outcome can be retried
        after unavailability using the read-only port. Browser data supplies no
        owner or buyer ID. Pending/retired/missing origins are hidden by storage.
        """
        await _require_eligible(caller, self._identity)
        conversations = self._require_conversations()
        try:
            async with asyncio.timeout(2):
                async with self._store.listing_conversation_guard(
                    listing_id
                ) as current:
                    if current is None:
                        raise PublicError(ERRORS[404])
                    if current.owner_id == caller.user_id:
                        raise PublicError(ERRORS[403])
                    if not await self._identity.account_is_eligible(current.owner_id):
                        raise PublicError(ERRORS[403])
                    if self._is_discoverable(current):
                        return await conversations.open_or_create_listing_conversation(
                            caller,
                            ListingConversationContext(
                                listing_id=listing_id, owner_id=current.owner_id
                            ),
                        )
                    existing = await conversations.find_existing_listing_conversation(
                        caller, ExistingListingConversationLookup(listing_id=listing_id)
                    )
                    if existing is None:
                        raise PublicError(ERRORS[404])
                    return existing
        except NotImplementedError, TimeoutError:
            raise PublicError(ERRORS[503]) from None

    async def submit_offer(
        self,
        caller: CallerContext,
        listing_id: ListingId,
        conversation_id: ConversationId,
        request: OfferRevisionRequest,
    ) -> OfferView:
        """Gate a buyer's offer on the live listing before Conversations writes it."""
        await _require_eligible(caller, self._identity)
        conversations = self._require_conversations()

        # The owned guard keeps this state check serialized with availability and
        # retirement writes while Conversations performs its separate transaction.
        async with self._store.listing_offer_guard(listing_id) as current:
            if current is None:
                raise PublicError(ERRORS[404])
            if current.owner_id == caller.user_id:
                raise PublicError(ERRORS[403])
            if not await self._identity.account_is_eligible(current.owner_id):
                raise PublicError(ERRORS[403])
            if not self._is_discoverable(current):
                raise PublicError(ERRORS[409])
            command = ListingOfferCommand(
                action="submit",
                listing_id=listing_id,
                conversation_id=conversation_id,
                amount_paise=request.amount_paise,
                note_envelope=request.note_envelope,
                expected_revision=request.expected_revision,
                operation_id=request.operation_id,
            )
            try:
                return await conversations.persist_listing_offer(caller, command)
            except NotImplementedError:
                raise PublicError(ERRORS[503]) from None

    async def withdraw_offer(
        self,
        caller: CallerContext,
        listing_id: ListingId,
        conversation_id: ConversationId,
        request: OfferWithdrawalRequest,
    ) -> OfferView:
        """Allow the offer's buyer to withdraw while the origin is not retired."""
        await _require_eligible(caller, self._identity)
        conversations = self._require_conversations()

        async with self._store.listing_offer_guard(listing_id) as current:
            if current is None:
                raise PublicError(ERRORS[404])
            if current.owner_id == caller.user_id:
                raise PublicError(ERRORS[403])
            if not await self._identity.account_is_eligible(current.owner_id):
                raise PublicError(ERRORS[403])
            command = ListingOfferCommand(
                action="withdraw",
                listing_id=listing_id,
                conversation_id=conversation_id,
                offer_id=request.offer_id,
                expected_revision=request.expected_revision,
                operation_id=request.operation_id,
            )
            try:
                return await conversations.persist_listing_offer(caller, command)
            except NotImplementedError:
                raise PublicError(ERRORS[503]) from None

    async def retire_eligible_listing(
        self, listing_id: ListingId, operation_id: UUID
    ) -> RetirementMarkerResult | None:
        """Coordinate thread marking; leave content cleanup to its approved path.

        ``None`` means this listing is not yet eligible. Once the Listings
        store commits the pending request, every Conversations failure leaves
        that same request pending so a retry can reuse both its ID and cutoff.
        A confirmed recent-activity result clears the pending request. A
        successful marker starts Listings' local content cleanup. The database
        transaction leaves image object keys queued until storage confirms each
        object is absent.
        """
        pending = await self._store.begin_listing_retirement(
            listing_id, operation_id, self._clock()
        )
        if pending is None:
            return None

        conversations = self._require_conversations()
        context = OriginOwnerContext(origin_kind="sale_listing")
        activity_request = OriginActivityRequest(
            origin_kind="sale_listing", origin_id=listing_id
        )
        try:
            activity = await conversations.get_origin_activity(
                context, activity_request
            )
        except NotImplementedError:
            raise PublicError(ERRORS[503]) from None
        except PublicError:
            raise
        except Exception:
            raise PublicError(ERRORS[503]) from None

        if activity is None or (
            (activity.thread_count == 0)
            != (activity.latest_participant_write_at is None)
        ):
            raise PublicError(ERRORS[503])

        marker_request = OriginRetirementCommand(
            origin_kind="sale_listing",
            origin_id=listing_id,
            cutoff_utc=pending.cutoff_utc,
            operation_id=pending.operation_id,
        )
        try:
            result = await conversations.mark_origin_retired(context, marker_request)
        except NotImplementedError:
            raise PublicError(ERRORS[503]) from None
        except PublicError:
            raise
        except Exception:
            # The marker may have committed before its response was lost. Keep
            # the persisted ID and cutoff so the caller can retry exactly.
            raise PublicError(ERRORS[503]) from None

        if result is None:
            raise PublicError(ERRORS[503])

        if result.outcome == "blocked_recent_activity":
            await self._store.clear_listing_retirement_pending(
                listing_id, pending.operation_id
            )
        else:
            await self._store.finalize_listing_retirement(
                listing_id, pending, self._clock()
            )
        return result

    async def cleanup_image_objects(self, limit: int = 100) -> int:
        """Clean a bounded batch of retired images and abandoned upload objects.

        This is an internal Listings worker operation, never a public route.
        Database references are retained until S3 confirms deletion or absence.
        Failed objects receive a five-minute retry delay so newer work can
        advance through the bounded queue.
        """
        self._validate_cleanup_limit(limit)
        storage = self._image_storage
        if storage is None:
            raise PublicError(ERRORS[503])

        retired = await self._store.list_retired_images_for_cleanup(limit)
        remaining = limit - len(retired)
        abandoned = (
            await self._store.list_abandoned_uploads_for_cleanup(remaining)
            if remaining
            else ()
        )
        deleted = 0
        failed = False

        for image in retired:
            try:
                await storage.delete_object(image.object_key)
                await self._store.finish_retired_image_cleanup(
                    image.image_id, image.object_key
                )
            except Exception:
                # A timeout can hide a successful delete. Retain the reference
                # and cool it down; a later idempotent delete resolves outcome.
                failed = True
                try:
                    await self._store.defer_retired_image_cleanup(
                        image.image_id, image.object_key
                    )
                except Exception:
                    pass
                continue
            deleted += 1

        for upload in abandoned:
            try:
                await storage.delete_object(upload.object_key)
                await self._store.finish_abandoned_upload_cleanup(
                    upload.upload_id, upload.object_key
                )
            except Exception:
                failed = True
                try:
                    await self._store.defer_abandoned_upload_cleanup(
                        upload.upload_id, upload.object_key
                    )
                except Exception:
                    pass
                continue
            deleted += 1

        if failed:
            raise PublicError(ERRORS[503])
        return deleted

    async def cleanup_retired_image_objects(self, limit: int = 100) -> int:
        """Retain the earlier worker entry point for a retired-image-only pass."""
        self._validate_cleanup_limit(limit)
        storage = self._image_storage
        if storage is None:
            raise PublicError(ERRORS[503])
        images = await self._store.list_retired_images_for_cleanup(limit)
        deleted = 0
        failed = False
        for image in images:
            try:
                await storage.delete_object(image.object_key)
                await self._store.finish_retired_image_cleanup(
                    image.image_id, image.object_key
                )
            except Exception:
                failed = True
                try:
                    await self._store.defer_retired_image_cleanup(
                        image.image_id, image.object_key
                    )
                except Exception:
                    pass
                continue
            deleted += 1
        if failed:
            raise PublicError(ERRORS[503])
        return deleted

    @staticmethod
    def _validate_cleanup_limit(limit: int) -> None:
        """Keep one worker pass between one and five hundred object records."""
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("Cleanup batch limit must be between 1 and 500")

    def _require_conversations(self) -> ListingsConversations:
        """Require the explicit Conversations adapter instead of faking success."""
        if self._conversations is None:
            raise PublicError(ERRORS[503])
        return self._conversations

    def _is_discoverable(self, view: ListingManagementView) -> bool:
        """Apply the contract's live, seller-available, current-window rule."""
        now = self._clock()
        return (
            view.availability == "available"
            and now >= view.available_from
            and (view.available_until is None or now < view.available_until)
        )
