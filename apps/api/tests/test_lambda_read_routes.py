"""Offline HTTP contract checks for the restricted Lambda read app."""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx2
import pytest
from psycopg import OperationalError

from app.application import create_app
from app.contracts.domain_types import ListingDetail, ListingSummary
from app.core.auth import CallerContext, require_caller
from app.core.config import Settings
from app.core.errors import ERRORS, PublicError
from app.core.pagination import Page
from app.domains.listings.browse import ListingsBrowseService
from app.domains.listings.browse_routes import browse_service
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.routes import _service

USER_ID = UUID("10000000-0000-4000-8000-000000000001")
LISTING_ID = UUID("20000000-0000-4000-8000-000000000002")
NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


class _EligibleIdentity:
    """Synthetic Identity contract response used only by these local tests."""

    async def account_is_eligible(self, _user_id: UUID) -> bool:
        return True


class _BrowseStore:
    """Capture the validated public query without contacting PostgreSQL."""

    def __init__(self) -> None:
        self.query = None

    async def browse_available_listings(self, query, _now):
        self.query = query
        return Page((), query.page, query.page_size, False)


class _DetailService:
    """Return one fixed contract object or a safe public error for detail tests."""

    def __init__(self, result: ListingDetail | None = None) -> None:
        self.result = result

    async def read_detail(self, _caller: CallerContext, listing_id: UUID):
        if self.result is None:
            raise PublicError(ERRORS[404])
        assert listing_id == self.result.listing_id
        return self.result


class _FailingPool:
    """Raise one synthetic pool/database error before any connection is opened."""

    def __init__(self, failure: Exception) -> None:
        self.failure = failure

    @asynccontextmanager
    async def connection(self):
        raise self.failure
        yield None


async def _caller() -> CallerContext:
    """Supply an explicitly test-only trusted principal at the auth boundary."""
    return CallerContext(USER_ID, "regular", datetime(2099, 1, 1, tzinfo=UTC))


def _app() -> object:
    """Compose the actual read-only app without entering its resource lifespan."""
    return create_app(Settings(environment="test"), listings_read_only=True)


def _bind_browse(application, store, identity) -> None:
    """Inject reviewed test adapters without running synchronous setup code."""

    async def service_provider():
        return ListingsBrowseService(store, identity)

    application.dependency_overrides[browse_service] = service_provider


def _request(application, method: str, path: str):
    """Send one in-process ASGI request; no socket or external service is used."""

    async def run():
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=application),
            base_url="http://test",
        ) as client:
            return await client.request(method, path)

    return asyncio.run(run())


def test_lambda_browse_preserves_filters_pagination_and_response_contract():
    application = _app()
    store = _BrowseStore()
    _bind_browse(application, store, _EligibleIdentity())
    application.dependency_overrides[require_caller] = _caller

    response = _request(
        application,
        "GET",
        "/api/listings?page=2&page_size=50&category_code=books"
        "&category_code=electronics&min_price_paise=1000&search_mode=hybrid"
        "&q=used%20laptop&sort=relevance",
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 2,
        "page_size": 50,
        "has_next": False,
    }
    assert response.headers["cache-control"] == "private, no-store"
    assert store.query is not None
    assert store.query.category_code == ["books", "electronics"]
    assert store.query.min_price_paise == 1000
    assert (store.query.page, store.query.page_size) == (2, 50)
    assert (store.query.search_mode, store.query.q, store.query.sort) == (
        "hybrid",
        "used laptop",
        "relevance",
    )


@pytest.mark.parametrize(
    ("path", "expected_status", "expected_code"),
    [
        ("/api/listings", 401, "unauthenticated"),
        ("/api/listings?min_price_paise=101", 422, "validation_error"),
    ],
)
def test_lambda_auth_and_invalid_query_use_safe_error_envelopes(
    path: str, expected_status: int, expected_code: str
):
    application = _app()
    store = _BrowseStore()
    _bind_browse(application, store, _EligibleIdentity())
    if expected_status == 422:
        application.dependency_overrides[require_caller] = _caller

    response = _request(application, "GET", path)

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
    assert "101" not in str(response.json()["error"])
    assert response.headers["cache-control"] == "private, no-store"


def test_lambda_browse_denies_ineligible_account():
    application = _app()
    store = _BrowseStore()

    class IneligibleIdentity:
        async def account_is_eligible(self, _user_id: UUID) -> bool:
            return False

    _bind_browse(application, store, IneligibleIdentity())
    application.dependency_overrides[require_caller] = _caller

    response = _request(application, "GET", "/api/listings")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert store.query is None


def _detail_fixture() -> ListingDetail:
    """Supply fixed public fields for both compositions, independently of responses."""
    return ListingDetail(
        listing_id=LISTING_ID,
        title="Synthetic book",
        description="Offline route fixture",
        category_code="books",
        category_label="Books",
        condition_code="good",
        condition_label="Good",
        asking_price_paise=10_000,
        original_price_paise=None,
        negotiable=False,
        pickup_area=None,
        available_from=NOW,
        available_until=None,
        availability="available",
        sensitive_purchase=False,
        image_ids=[],
        proof_available=None,
    )


def test_lambda_detail_preserves_identity_and_not_found_semantics():
    application = _app()
    application.dependency_overrides[require_caller] = _caller
    detail = _detail_fixture()

    async def detail_provider():
        return _DetailService(detail)

    application.dependency_overrides[_service] = detail_provider

    response = _request(application, "GET", f"/api/listings/{LISTING_ID}")

    assert response.status_code == 200
    assert response.json()["listing_id"] == str(LISTING_ID)

    async def missing_detail_provider():
        return _DetailService()

    application.dependency_overrides[_service] = missing_detail_provider
    missing = _request(application, "GET", f"/api/listings/{LISTING_ID}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "failure", [TimeoutError(), OperationalError("synthetic DB failure")]
)
def test_lambda_database_and_pool_timeout_fail_safely(failure: Exception):
    application = _app()
    store = PostgresListingsStore(_FailingPool(failure), 500_000)
    _bind_browse(application, store, _EligibleIdentity())
    application.dependency_overrides[require_caller] = _caller

    response = _request(application, "GET", "/api/listings")

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "dependency_unavailable",
        "message": "Required dependency unavailable",
    }
    assert response.headers["x-request-id"]
    assert "synthetic DB failure" not in response.text


@pytest.mark.parametrize(
    ("scenario", "expected_status"),
    [
        ("browse", 200),
        ("hybrid", 200),
        ("detail", 200),
        ("invalid", 422),
        ("unauthenticated", 401),
        ("forbidden", 403),
        ("not_found", 404),
        ("database_failure", 503),
        ("pool_timeout", 503),
    ],
)
def test_ecs_and_lambda_read_response_parity(
    scenario: str, expected_status: int, tmp_path: Path, monkeypatch
):
    """Compare hosted ECS and narrow Lambda routes with identical synthetic ports.

    Only resource lifespans and Identity/data adapters are omitted. Both real app
    compositions mount their own routes at /api; a disposable web build satisfies
    ECS's static-file requirement. This tests serialization and route semantics,
    not ALB/Web Adapter behavior, real sessions, SQL or Hybrid ranking.
    """
    import app.application as composition

    web_root = tmp_path / "web"
    (web_root / "assets").mkdir(parents=True)
    (web_root / "index.html").write_text("Offline parity fixture", encoding="utf-8")
    real_path = composition.Path
    monkeypatch.setattr(
        composition,
        "Path",
        lambda value: web_root if value == "/app/web" else real_path(value),
    )
    detail = _detail_fixture()
    first = ListingSummary.model_validate(
        detail.model_dump(exclude={"proof_available"})
    )
    second = first.model_copy(update={"listing_id": USER_ID, "title": "Second fixture"})

    class OrderedStore(_BrowseStore):
        """Return deliberately non-ID-sorted results to detect serialization reorder."""

        async def browse_available_listings(self, query, now):
            await super().browse_available_listings(query, now)
            return Page((first, second), query.page, query.page_size, True)

    class ParityIdentity:
        async def account_is_eligible(self, _user_id: UUID) -> bool:
            return scenario != "forbidden"

    snapshots = []
    queries = []
    for read_only in (False, True):
        application = create_app(
            Settings(environment="test", serve_web_app=not read_only),
            listings_read_only=read_only,
        )
        store = OrderedStore()
        browse_store = store
        if scenario in {"database_failure", "pool_timeout"}:
            failure = (
                OperationalError("synthetic private database diagnostic")
                if scenario == "database_failure"
                else TimeoutError()
            )
            browse_store = PostgresListingsStore(_FailingPool(failure), 500_000)
        _bind_browse(application, browse_store, ParityIdentity())
        if scenario != "unauthenticated":
            application.dependency_overrides[require_caller] = _caller

        async def detail_provider():
            return _DetailService(None if scenario == "not_found" else detail)

        application.dependency_overrides[_service] = detail_provider
        path = "/api/listings?page=2&page_size=50&category_code=books&category_code=electronics"
        if scenario == "hybrid":
            path += "&q=used%20laptop&search_mode=hybrid&sort=relevance"
        elif scenario == "invalid":
            path = "/api/listings?min_price_paise=101"
        elif scenario in {"detail", "not_found"}:
            path = f"/api/listings/{LISTING_ID}"
        response = _request(application, "GET", path)
        assert response.status_code == expected_status
        body = response.json()
        headers = dict(response.headers)
        # Correlation IDs intentionally differ per request. Validate their binding
        # before excluding only that generated value from the equality check.
        request_id = headers.pop("x-request-id")
        UUID(request_id)
        if expected_status != 200:
            assert body.pop("request_id") == request_id
            assert body["error"] == {
                "code": ERRORS[expected_status].code,
                "message": ERRORS[expected_status].message,
                **(
                    {"details": [{"field": "query", "code": "invalid_value"}]}
                    if scenario == "invalid"
                    else {}
                ),
            }
        elif scenario == "detail":
            assert body == detail.model_dump(mode="json")
        else:
            assert body == {
                "items": [
                    first.model_dump(mode="json"),
                    second.model_dump(mode="json"),
                ],
                "page": 2,
                "page_size": 50,
                "has_next": True,
            }
            assert headers["cache-control"] == "private, no-store"
        snapshots.append((response.status_code, headers, body))
        queries.append(store.query)

    assert snapshots[0] == snapshots[1]
    assert queries[0] == queries[1]
    if scenario in {"browse", "hybrid"}:
        assert queries[0].category_code == ["books", "electronics"]
        if scenario == "hybrid":
            assert (queries[0].q, queries[0].search_mode, queries[0].sort) == (
                "used laptop",
                "hybrid",
                "relevance",
            )
