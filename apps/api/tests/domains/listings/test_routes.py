"""HTTP query parsing for owner-only Listings routes."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.domain_types import PageResult
from app.core.auth import CallerContext, require_caller
from app.core.errors import install_error_handlers
from app.domains.listings.routes import ListingManagementPage, _service, router

USER_ID = UUID("10000000-0000-4000-8000-000000000001")


class _Service:
    """Capture the page sent by HTTP without replacing pagination validation."""

    def __init__(self) -> None:
        self.page: ListingManagementPage | None = None

    async def list_mine(
        self, caller: CallerContext, page: ListingManagementPage
    ) -> PageResult:
        self.page = page
        return PageResult(
            items=[], page=page.page, page_size=page.page_size, has_next=False
        )


def _client() -> tuple[TestClient, _Service]:
    """Install a fixed caller and narrow service fake around the actual router."""
    application = FastAPI()
    install_error_handlers(application)
    application.include_router(router)
    service = _Service()
    application.dependency_overrides[require_caller] = lambda: CallerContext(
        USER_ID, "regular", datetime.now(UTC) + timedelta(minutes=5)
    )
    application.dependency_overrides[_service] = lambda: service
    return TestClient(application), service


@pytest.mark.parametrize("page_size", [20, 50, 100])
def test_my_listings_accepts_supported_query_page_sizes(page_size: int) -> None:
    client, service = _client()
    with client:
        response = client.get(f"/me/listings?page=2&page_size={page_size}")
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 2,
        "page_size": page_size,
        "has_next": False,
    }
    assert service.page is not None
    assert (service.page.page, service.page.page_size) == (2, page_size)


@pytest.mark.parametrize("query", ["page_size=30", "page_size=20.0", "page=1.0"])
def test_my_listings_rejects_noncontract_pagination(query: str) -> None:
    client, service = _client()
    with client:
        response = client.get(f"/me/listings?{query}")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert service.page is None
