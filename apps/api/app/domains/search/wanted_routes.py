"""Reviewed wanted HTTP operations; no cleanup or synthetic auth route."""

from collections.abc import Callable, Coroutine
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException

from app.contracts.domain_types import (
    ErrorEnvelope,
    ConversationStartResult,
    StartWantedResponse,
    DraftMatchResult,
    PageResult,
    WantedRequestId,
    WantedRequestOwnerView,
    WantedRequestPublic,
)
from app.core.auth import CallerContext, require_caller
from app.core.errors import (
    ERRORS,
    PublicError,
    public_error_handler,
    validation_error_handler,
    http_error_handler,
)
from app.domains.search.wanted import PublicWantedDependencies, WantedService
from app.domains.search.draft_matches import DraftMatchService
from app.domains.search.wanted_response import WantedResponseService
from app.domains.search.wanted_models import (
    WantedCreate,
    DraftTitle,
    WantedPage,
    WantedPatch,
    WantedState,
)


class PrivateWantedRoute(APIRoute):
    """Apply no-store to successes and safe authentication/validation failures."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """Preserve shared error sanitizers without changing other domains."""
        handler = super().get_route_handler()

        async def private_response(request: Request) -> Response:
            """Never cache signed-in availability or owner-management responses."""
            try:
                response = await handler(request)
            except PublicError as exc:
                response = await public_error_handler(request, exc)
            except RequestValidationError as exc:
                response = await validation_error_handler(request, exc)
            except HTTPException as exc:
                response = await http_error_handler(request, exc)
            response.headers["Cache-Control"] = "private, no-store"
            return response

        return private_response


router = APIRouter(route_class=PrivateWantedRoute)
_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorEnvelope, "description": HTTPStatus(code).phrase}
    for code in (400, 401, 403, 404, 409, 422, 429, 500, 503)
}


def wanted_service(request: Request) -> WantedService:
    """Reuse configured storage and real public adapters; absent storage is503."""
    store = getattr(request.app.state, "wanted_store", None)
    if store is None:
        raise PublicError(ERRORS[503])
    return WantedService(
        store,
        PublicWantedDependencies(
            getattr(request.app.state, "listings_public", None),
            getattr(request.app.state, "search_identity", None),
        ),
    )


Caller = Annotated[CallerContext, Depends(require_caller)]
Service = Annotated[WantedService, Depends(wanted_service)]
Paging = Annotated[WantedPage, Query()]


def draft_match_service(request: Request) -> DraftMatchService:
    """Borrow the same Listings provider as other Search operations."""
    listings = getattr(request.app.state, "listings_public", None)
    identity = getattr(request.app.state, "search_identity", None)
    if listings is None:
        return DraftMatchService(identity=identity)
    return DraftMatchService(listings, identity)


@router.post(
    "/wanted-requests/draft-matches",
    response_model=DraftMatchResult,
    operation_id="search_match_draft_title",
    summary="search_match_draft_title",
    responses=_ERRORS,
)
async def match_draft(
    caller: Caller,
    service: Annotated[DraftMatchService, Depends(draft_match_service)],
    body: DraftTitle,
) -> DraftMatchResult:
    """Transient possible matches only; no wanted create/update side effect."""
    return await service.match(caller, body)


@router.get(
    "/wanted-requests",
    response_model=PageResult[WantedRequestPublic],
    operation_id="search_list_open_wanted_requests",
    summary="search_list_open_wanted_requests",
    responses=_ERRORS,
)
async def list_open(caller: Caller, service: Service, query: Paging) -> Any:
    """List only current open non-pending requests, without author identity."""
    return await service.listing(caller, query)


@router.get(
    "/me/wanted-requests",
    response_model=PageResult[WantedRequestOwnerView],
    operation_id="search_list_my_wanted_requests",
    summary="search_list_my_wanted_requests",
    responses=_ERRORS,
)
async def list_own(caller: Caller, service: Service, query: Paging) -> Any:
    """Read only caller-owned non-retired requests including unavailable ones."""
    return await service.listing(caller, query, own=True)


@router.post(
    "/wanted-requests",
    response_model=WantedRequestOwnerView,
    status_code=201,
    operation_id="search_create_wanted_request",
    summary="search_create_wanted_request",
    responses=_ERRORS,
)
async def create(
    caller: Caller, service: Service, body: WantedCreate
) -> WantedRequestOwnerView:
    """Create under the trusted actor and return the reviewed owner projection."""
    return await service.create(caller, body)


@router.get(
    "/wanted-requests/{request_id}",
    response_model=WantedRequestPublic | WantedRequestOwnerView,
    operation_id="search_read_wanted_request",
    summary="search_read_wanted_request",
    responses=_ERRORS,
)
async def read(
    request_id: WantedRequestId, caller: Caller, service: Service
) -> WantedRequestPublic | WantedRequestOwnerView:
    """Use the safe owner exception only for unavailable non-retired detail."""
    return await service.read(caller, request_id)


@router.patch(
    "/wanted-requests/{request_id}",
    response_model=WantedRequestOwnerView,
    operation_id="search_update_wanted_request",
    summary="search_update_wanted_request",
    responses=_ERRORS,
)
async def edit(
    request_id: WantedRequestId, caller: Caller, service: Service, body: WantedPatch
) -> WantedRequestOwnerView:
    """Apply only explicitly supplied fields with revision/retry protection."""
    return await service.edit(caller, request_id, body)


@router.put(
    "/wanted-requests/{request_id}/availability",
    response_model=WantedRequestOwnerView,
    operation_id="search_change_wanted_request_state",
    summary="search_change_wanted_request_state",
    responses=_ERRORS,
)
async def state(
    request_id: WantedRequestId, caller: Caller, service: Service, body: WantedState
) -> WantedRequestOwnerView:
    """Close or reopen the author's same request without deleting its history."""
    return await service.state(caller, request_id, body)


def response_service(request: Request) -> WantedResponseService:
    """Use configured Search store and real public Identity/Conversations defaults."""
    store = getattr(request.app.state, "wanted_store", None)
    if store is None:
        raise PublicError(ERRORS[503])
    conversations = getattr(request.app.state, "conversations_public", None)
    return (
        WantedResponseService(store, conversations=conversations)
        if conversations is not None
        else WantedResponseService(store)
    )


@router.post(
    "/wanted-requests/{request_id}/conversations",
    response_model=ConversationStartResult,
    status_code=201,
    operation_id="search_start_wanted_response",
    summary="search_start_wanted_response",
    responses={**_ERRORS, 200: {"model": ConversationStartResult, "description": "OK"}},
)
async def respond_to_request(
    request_id: WantedRequestId,
    caller: Caller,
    service: Annotated[WantedResponseService, Depends(response_service)],
    body: StartWantedResponse,
    response: Response,
) -> ConversationStartResult:
    """Pair uniqueness defines retries; validated operation UUID is not a new C field."""
    result = await service.respond(caller, request_id)
    response.status_code = 201 if result.created else 200
    return result
