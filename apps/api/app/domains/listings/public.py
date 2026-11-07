# Generated declaration-only listings interface; format 2. Do not edit.
"""Reviewed Listings HTTP operations and internal declaration-only callables."""

from typing import AsyncContextManager, Protocol

from app.core.auth import CallerContext
from app.core.pagination import Page

from app.contracts.domain_types import (
    AvailableListingQuery,
    Category,
    CategoryCode,
    CategoryDisplay,
    ConversationId,
    ListingDetail,
    ListingId,
    ListingManagementView,
    ListingOwnerView,
    ListingQuery,
    ListingReplacement,
    ListingSummary,
    OfferRevisionRequest,
    OfferView,
    OfferWithdrawalRequest,
    PageQuery,
    PageResult,
    ImageId,
    SaveTargetResult,
    SavedListingState,
    SelectionChange,
    StartListingConversationRequest,
    UploadInstruction,
    AvailabilityChange,
    ConfirmedImage,
    CreateListingRequest,
    ImageDelivery,
    ImageDeliveryQuery,
    ImageDeliveryBatch,
    ImageUploadRequest,
    CatalogueView,
)
from app.contracts.domain_types import ConversationStartResult


class ListingsPublic(Protocol):
    """Injectable type surface used by consumers and their isolated test doubles."""

    async def query_available_listings(
        self, caller: CallerContext, request: AvailableListingQuery
    ) -> Page[ListingSummary]:
        """Read the authoritative currently available listing page."""
        ...

    def conversation_write_guard(
        self, caller: CallerContext, listing_id: ListingId
    ) -> AsyncContextManager[bool]:
        """Hold the listing availability lock across a conversation write."""
        ...

    async def read_save_target(
        self, caller: CallerContext, listing_id: ListingId
    ) -> SaveTargetResult:
        """Check whether one listing can be newly saved."""
        ...

    async def read_saved_listing_summaries(
        self, caller: CallerContext, listing_ids: tuple[ListingId, ...]
    ) -> tuple[SavedListingState, ...]:
        """Resolve a bounded page of caller-owned saved listing references."""
        ...

    async def read_active_categories(self) -> tuple[Category, ...]:
        """Read active category codes for a new assignment."""
        ...

    async def read_category_display(
        self, codes: tuple[CategoryCode, ...]
    ) -> tuple[CategoryDisplay, ...]:
        """Read labels for retained category codes, including inactive values."""
        ...


HTTP_OPERATIONS = (
    {
        "method": "GET",
        "path": "/images/delivery",
        "operation_id": "listings_get_image_delivery_batch",
        "query": ImageDeliveryQuery,
        "response": ImageDeliveryBatch,
    },
    {
        "method": "GET",
        "path": "/listings",
        "operation_id": "listings_query_available",
        "query": ListingQuery,
        "response": PageResult[ListingSummary],
    },
    {
        "method": "GET",
        "path": "/listings/{listing_id}",
        "operation_id": "listings_read_detail",
        "path_parameters": {"listing_id": ListingId},
        "response": ListingDetail,
    },
    {
        "method": "GET",
        "path": "/me/listings",
        "operation_id": "listings_list_mine",
        "query": PageQuery,
        "response": PageResult[ListingManagementView],
    },
    {
        "method": "GET",
        "path": "/catalogue",
        "operation_id": "listings_read_catalogue",
        "response": CatalogueView,
    },
    {
        "method": "POST",
        "path": "/image-uploads",
        "operation_id": "listings_create_image_upload",
        "body": ImageUploadRequest,
        "response": UploadInstruction,
        "status_code": 201,
    },
    {
        "method": "POST",
        "path": "/image-uploads/{upload_id}/confirm",
        "operation_id": "listings_confirm_image_upload",
        "path_parameters": {"upload_id": ImageId},
        "response": ConfirmedImage,
    },
    {
        "method": "DELETE",
        "path": "/image-uploads/{upload_id}",
        "operation_id": "listings_cancel_image_upload",
        "path_parameters": {"upload_id": ImageId},
        "status_code": 204,
    },
    {
        "method": "GET",
        "path": "/images/{image_id}/delivery",
        "operation_id": "listings_get_image_delivery",
        "path_parameters": {"image_id": ImageId},
        "response": ImageDelivery,
    },
    {
        "method": "POST",
        "path": "/listings",
        "operation_id": "listings_create",
        "body": CreateListingRequest,
        "response": ListingDetail,
        "status_code": 201,
    },
    {
        "method": "PUT",
        "path": "/listings/{listing_id}",
        "operation_id": "listings_replace",
        "path_parameters": {"listing_id": ListingId},
        "body": ListingReplacement,
        "response": ListingDetail,
    },
    {
        "method": "PUT",
        "path": "/listings/{listing_id}/availability",
        "operation_id": "listings_change_availability",
        "path_parameters": {"listing_id": ListingId},
        "body": AvailabilityChange,
        "response": ListingDetail,
    },
    {
        "method": "POST",
        "path": "/listings/{listing_id}/conversations",
        "operation_id": "listings_start_conversation",
        "path_parameters": {"listing_id": ListingId},
        "body": StartListingConversationRequest,
        "response": ConversationStartResult,
        "status_code": 201,
        "responses": {200: ConversationStartResult},
    },
    {
        "method": "PUT",
        "path": "/listings/{listing_id}/selection",
        "operation_id": "listings_set_selected_buyer",
        "path_parameters": {"listing_id": ListingId},
        "body": SelectionChange,
        "response": ListingOwnerView,
    },
    {
        "method": "PUT",
        "path": "/listings/{listing_id}/conversations/{conversation_id}/offer",
        "operation_id": "listings_submit_offer",
        "path_parameters": {"listing_id": ListingId, "conversation_id": ConversationId},
        "body": OfferRevisionRequest,
        "response": OfferView,
    },
    {
        "method": "POST",
        "path": "/listings/{listing_id}/conversations/{conversation_id}/offer-withdrawals",
        "operation_id": "listings_withdraw_offer",
        "path_parameters": {"listing_id": ListingId, "conversation_id": ConversationId},
        "body": OfferWithdrawalRequest,
        "response": OfferView,
    },
)


async def query_available_listings(
    caller: CallerContext, request: AvailableListingQuery
) -> Page[ListingSummary]:
    """Declare the authoritative available-listing query boundary.

    Listings owns filtering, availability, stable order and page slicing. The
    declaration does not query storage or fabricate an empty page.
    """
    raise NotImplementedError("declaration-only")


async def read_save_target(
    caller: CallerContext, listing_id: ListingId
) -> SaveTargetResult:
    """Declare a minimal discovery check for one Search-owned save request."""
    raise NotImplementedError("declaration-only")


async def read_saved_listing_summaries(
    caller: CallerContext, listing_ids: tuple[ListingId, ...]
) -> tuple[SavedListingState, ...]:
    """Declare bounded detail resolution for IDs from this caller's saved page."""
    raise NotImplementedError("declaration-only")


async def read_active_categories() -> tuple[Category, ...]:
    """Declare deterministic active category lookup for new assignments."""
    raise NotImplementedError("declaration-only")


async def read_category_display(
    codes: tuple[CategoryCode, ...],
) -> tuple[CategoryDisplay, ...]:
    """Declare historical category label resolution without enabling assignment."""
    raise NotImplementedError("declaration-only")
