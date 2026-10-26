"""HTTP composition for the reviewed Listings-owned collection query."""

from typing import Annotated
from collections.abc import Callable, Coroutine
from typing import Any
from http import HTTPStatus

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException

from app.contracts.domain_types import (
    ErrorEnvelope,
    ListingSummary,
    PageResult,
)
from app.core.auth import CallerContext, require_caller
from app.core.errors import (
    ERRORS,
    PublicError,
    public_error_handler,
    validation_error_handler,
    http_error_handler,
)
from app.domains.listings.browse import ListingsBrowseService, PublicBrowseIdentity
from app.domains.listings.browse_validation import BrowseQuery


class PrivateBrowseRoute(APIRoute):
    """Keep success and safe auth/validation/dependency failures out of caches.

    Scope this transport policy to the owned browse operation; reuse the common
    sanitizers without changing shared error vocabulary or other routes.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """Wrap dependency parsing and execution, including pre-endpoint errors."""
        handler = super().get_route_handler()

        async def private_response(request: Request) -> Response:
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


router = APIRouter(route_class=PrivateBrowseRoute)


def browse_service(request: Request) -> ListingsBrowseService:
    """Reuse the configured real store; Identity is a public dependency, not a fake.

    Explicit test harnesses can bind listings_browse_identity on their own app;
    normal startup calls the real public capability API and fails closed while
    Identity is declaration-only. The seller-only adapter is never substituted.
    """
    store = getattr(request.app.state, "listings_store", None)
    if store is None:
        raise PublicError(ERRORS[503])
    identity = getattr(request.app.state, "listings_browse_identity", None)
    return ListingsBrowseService(
        store, PublicBrowseIdentity() if identity is None else identity
    )


@router.get(
    "/listings",
    response_model=PageResult[ListingSummary],
    summary="listings_query_available",
    operation_id="listings_query_available",
    # Match the frozen common error vocabulary exactly. Declaring a status is
    # transport metadata, not evidence that a provider/rate policy is implemented.
    responses={
        code: {"model": ErrorEnvelope, "description": HTTPStatus(code).phrase}
        for code in (400, 401, 403, 404, 409, 422, 429, 500, 503)
    },
)
async def query_available_listings(
    response: Response,
    caller: Annotated[CallerContext, Depends(require_caller)],
    service: Annotated[ListingsBrowseService, Depends(browse_service)],
    query: Annotated[BrowseQuery, Query()],
) -> PageResult[ListingSummary]:
    """Return fresh available results; never permit cached availability inference."""
    page = await service.query_available_listings(caller, query)
    # Both eligibility and availability can change between requests. Keep these
    # signed-in results out of shared caches and stale browser response storage.
    response.headers["Cache-Control"] = "private, no-store"
    return PageResult(
        items=list(page.items),
        page=page.page,
        page_size=page.page_size,
        has_next=page.has_next,
    )
