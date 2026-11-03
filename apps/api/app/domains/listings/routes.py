"""HTTP handlers for the implemented Listings lifecycle commands."""

from typing import Annotated, Any
import re

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import field_validator, model_validator

from app.core.auth import CallerContext, require_caller
from app.core.errors import ERRORS, PublicError
from app.contracts.domain_types import (
    CreateListingRequest,
    ConfirmedImage,
    CatalogueView,
    AvailabilityChange,
    ConversationId,
    ConversationStartResult,
    StartListingConversationRequest,
    ErrorEnvelope,
    ImageDelivery,
    ImageDeliveryBatch,
    ImageDeliveryQuery,
    ListingDetail,
    ListingId,
    ImageId,
    ImageUploadRequest,
    ListingOwnerView,
    ListingReplacement,
    PageQuery,
    PageResult,
    ListingManagementView,
    OfferRevisionRequest,
    OfferView,
    OfferWithdrawalRequest,
    SelectionChange,
    UploadInstruction,
)
from app.domains.listings.service import ListingsService
from app.domains.listings.browse_routes import router as browse_router

router = APIRouter()
router.include_router(browse_router)
read_only_router = APIRouter()
read_only_router.include_router(browse_router)


class ListingManagementPage(PageQuery):
    """Parse browser query strings strictly before applying the page contract."""

    @field_validator("page", "page_size", mode="before")
    @classmethod
    def exact_integer(cls, value: Any) -> Any:
        """Accept decimal query strings while rejecting floats and booleans."""
        if isinstance(value, str) and re.fullmatch(r"[+-]?[0-9]+", value):
            try:
                return int(value)
            except ValueError:
                pass
        if type(value) is not int:
            raise ValueError("Integer page value required")
        return value

    @model_validator(mode="after")
    def bounded_offset(self) -> "ListingManagementPage":
        """Keep pagination offsets in PostgreSQL's bigint range."""
        if (self.page - 1) * self.page_size > 2**63 - 1:
            raise ValueError("Page outside supported range")
        return self


_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorEnvelope, "description": "Bad Request"},
    401: {"model": ErrorEnvelope, "description": "Unauthorized"},
    403: {"model": ErrorEnvelope, "description": "Forbidden"},
    404: {"model": ErrorEnvelope, "description": "Not Found"},
    409: {"model": ErrorEnvelope, "description": "Conflict"},
    422: {"model": ErrorEnvelope, "description": "Unprocessable Content"},
    429: {"model": ErrorEnvelope, "description": "Too Many Requests"},
    500: {"model": ErrorEnvelope, "description": "Internal Server Error"},
    503: {"model": ErrorEnvelope, "description": "Service Unavailable"},
}


def _service(request: Request) -> ListingsService:
    """Use explicitly configured adapters; never activate fake fallbacks."""
    store = getattr(request.app.state, "listings_store", None)
    identity = getattr(request.app.state, "listings_identity", None)
    if store is None or identity is None:
        raise PublicError(ERRORS[503])
    conversations = getattr(request.app.state, "listings_conversations", None)
    image_storage = getattr(request.app.state, "listings_image_storage", None)
    return ListingsService(
        store,
        identity,
        conversations=conversations,
        image_storage=image_storage,
    )


@router.post(
    "/listings/{listing_id}/conversations",
    response_model=ConversationStartResult,
    status_code=201,
    operation_id="listings_start_conversation",
    summary="listings_start_conversation",
    responses={
        **_ERROR_RESPONSES,
        200: {"model": ConversationStartResult, "description": "OK"},
    },
)
async def start_conversation(
    listing_id: ListingId,
    body: StartListingConversationRequest,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
    response: Response,
) -> ConversationStartResult:
    """Validate the operation UUID; exact authenticated pair defines retries."""
    result = await service.start_conversation(caller, listing_id)
    response.status_code = 201 if result.created else 200
    return result


@router.get(
    "/catalogue",
    response_model=CatalogueView,
    summary="listings_read_catalogue",
    operation_id="listings_read_catalogue",
    responses=_ERROR_RESPONSES,
)
async def read_catalogue(
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> CatalogueView:
    """Supply the reviewed catalogue endpoint without duplicating labels in the UI."""
    return await service.read_catalogue(caller)


@router.post(
    "/image-uploads",
    response_model=UploadInstruction,
    status_code=status.HTTP_201_CREATED,
    summary="listings_create_image_upload",
    operation_id="listings_create_image_upload",
    responses=_ERROR_RESPONSES,
)
async def create_image_upload(
    body: ImageUploadRequest,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> UploadInstruction:
    """Create a pending upload owned by the authenticated regular seller."""
    return await service.create_image_upload(caller, body)


@router.post(
    "/image-uploads/{upload_id}/confirm",
    response_model=ConfirmedImage,
    summary="listings_confirm_image_upload",
    operation_id="listings_confirm_image_upload",
    responses=_ERROR_RESPONSES,
)
async def confirm_image_upload(
    upload_id: ImageId,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> ConfirmedImage:
    """Confirm an uploaded object only for its authenticated owner."""
    return await service.confirm_image_upload(caller, upload_id)


@router.delete(
    "/image-uploads/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="listings_cancel_image_upload",
    operation_id="listings_cancel_image_upload",
    responses=_ERROR_RESPONSES,
)
async def cancel_image_upload(
    upload_id: ImageId,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> Response:
    """Cancel one owner's unattached intent, retaining its key for cleanup."""
    await service.cancel_image_upload(caller, upload_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/images/delivery",
    response_model=ImageDeliveryBatch,
    operation_id="listings_get_image_delivery_batch",
    summary="listings_get_image_delivery_batch",
    responses=_ERROR_RESPONSES,
)
async def get_image_delivery_batch(
    response: Response,
    query: Annotated[ImageDeliveryQuery, Query()],
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> ImageDeliveryBatch:
    """Resolve a bounded page without separate authentication for every photo."""
    response.headers["Cache-Control"] = "private, no-store"
    return await service.get_image_deliveries(caller, query.image_ids)


@router.get(
    "/images/{image_id}/delivery",
    response_model=ImageDelivery,
    summary="listings_get_image_delivery",
    operation_id="listings_get_image_delivery",
    responses=_ERROR_RESPONSES,
)
async def get_image_delivery(
    image_id: ImageId,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> ImageDelivery:
    """Return a short-lived S3 URL only after the listing visibility check."""
    return await service.get_image_delivery(caller, image_id)


@router.post(
    "/listings",
    response_model=ListingDetail,
    status_code=status.HTTP_201_CREATED,
    summary="listings_create",
    operation_id="listings_create",
    responses=_ERROR_RESPONSES,
)
async def create_listing(
    body: CreateListingRequest,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> ListingDetail:
    """Create a listing owned by the server-authenticated caller."""
    return await service.create(caller, body)


@router.get(
    "/listings/{listing_id}",
    response_model=ListingDetail,
    summary="listings_read_detail",
    operation_id="listings_read_detail",
    responses=_ERROR_RESPONSES,
)
async def read_listing_detail(
    listing_id: ListingId,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> ListingDetail:
    """Read public-discoverable detail or the caller's own unavailable listing."""
    return await service.read_detail(caller, listing_id)


read_only_router.add_api_route(
    "/listings/{listing_id}",
    read_listing_detail,
    methods=["GET"],
    response_model=ListingDetail,
    summary="listings_read_detail",
    operation_id="listings_read_detail",
    responses=_ERROR_RESPONSES,
)


@router.get(
    "/me/listings",
    response_model=PageResult[ListingManagementView],
    summary="listings_list_mine",
    operation_id="listings_list_mine",
    responses=_ERROR_RESPONSES,
)
async def list_my_listings(
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
    query: Annotated[ListingManagementPage, Query()],
) -> PageResult[ListingManagementView]:
    """List only the authenticated seller's management details."""
    return await service.list_mine(caller, query)


@router.put(
    "/listings/{listing_id}",
    response_model=ListingDetail,
    summary="listings_replace",
    operation_id="listings_replace",
    responses=_ERROR_RESPONSES,
)
async def replace_listing(
    listing_id: ListingId,
    body: ListingReplacement,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> ListingDetail:
    """Replace one listing only when the authenticated caller owns it."""
    return await service.replace(caller, listing_id, body)


@router.put(
    "/listings/{listing_id}/availability",
    response_model=ListingDetail,
    summary="listings_change_availability",
    operation_id="listings_change_availability",
    responses=_ERROR_RESPONSES,
)
async def change_listing_availability(
    listing_id: ListingId,
    body: AvailabilityChange,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> ListingDetail:
    """Change only the owner's availability and time window."""
    return await service.change_availability(caller, listing_id, body)


@router.put(
    "/listings/{listing_id}/selection",
    response_model=ListingOwnerView,
    summary="listings_set_selected_buyer",
    operation_id="listings_set_selected_buyer",
    responses=_ERROR_RESPONSES,
)
async def set_selected_buyer(
    listing_id: ListingId,
    body: SelectionChange,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> ListingOwnerView:
    """Select a buyer (making the listing unavailable) or clear the selection."""
    return await service.set_selected_buyer(caller, listing_id, body)


@router.put(
    "/listings/{listing_id}/conversations/{conversation_id}/offer",
    response_model=OfferView,
    summary="listings_submit_offer",
    operation_id="listings_submit_offer",
    responses=_ERROR_RESPONSES,
)
async def submit_listing_offer(
    listing_id: ListingId,
    conversation_id: ConversationId,
    body: OfferRevisionRequest,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> OfferView:
    """Gate a buyer's submit/revise/resubmit command through Listings."""
    return await service.submit_offer(caller, listing_id, conversation_id, body)


@router.post(
    "/listings/{listing_id}/conversations/{conversation_id}/offer-withdrawals",
    response_model=OfferView,
    summary="listings_withdraw_offer",
    operation_id="listings_withdraw_offer",
    responses=_ERROR_RESPONSES,
)
async def withdraw_listing_offer(
    listing_id: ListingId,
    conversation_id: ConversationId,
    body: OfferWithdrawalRequest,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsService, Depends(_service)],
) -> OfferView:
    """Send the buyer's withdrawal through the Listings command boundary."""
    return await service.withdraw_offer(caller, listing_id, conversation_id, body)
