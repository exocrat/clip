"""Reviewed private saved-listing HTTP operations, sharing Search error/cache policy."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.contracts.domain_types import (
    ListingId,
    PageResult,
    SaveListingRequest,
    SavedListingAck,
    SavedListingView,
)
from app.core.auth import CallerContext, require_caller
from app.core.errors import ERRORS, PublicError
from app.domains.search.saved import SavedService
from app.domains.search.wanted_models import WantedPage
from app.domains.search.wanted_routes import PrivateWantedRoute, _ERRORS

router = APIRouter(route_class=PrivateWantedRoute)


def saved_service(request: Request) -> SavedService:
    """Use configured Search persistence plus real public defaults; fail closed."""
    store = getattr(request.app.state, "saved_store", None)
    if store is None:
        raise PublicError(ERRORS[503])
    return SavedService(store)


Caller = Annotated[CallerContext, Depends(require_caller)]
Service = Annotated[SavedService, Depends(saved_service)]


@router.get(
    "/me/saved-listings",
    response_model=PageResult[SavedListingView],
    operation_id="search_list_saved_listings",
    summary="search_list_saved_listings",
    responses=_ERRORS,
)
async def list_saved(
    caller: Caller, service: Service, query: Annotated[WantedPage, Query()]
) -> PageResult[SavedListingView]:
    """Only the trusted caller's page, resolved to current safe public state."""
    return await service.listing(caller, query)


@router.put(
    "/me/saved-listings/{listing_id}",
    response_model=SavedListingAck,
    operation_id="search_save_listing",
    summary="search_save_listing",
    responses=_ERRORS,
)
async def save_listing(
    listing_id: ListingId, caller: Caller, service: Service, body: SaveListingRequest
) -> SavedListingAck:
    """Operation UUID is validated; pair uniqueness is the reviewed retry identity."""
    return await service.save(caller, listing_id)


@router.delete(
    "/me/saved-listings/{listing_id}",
    status_code=204,
    operation_id="search_unsave_listing",
    summary="search_unsave_listing",
    responses=_ERRORS,
)
async def unsave_listing(
    listing_id: ListingId, caller: Caller, service: Service
) -> Response:
    """Absent is successful, and no caller-selected user ID is accepted."""
    await service.unsave(caller, listing_id)
    return Response(status_code=204)
