"""Runtime/authoritative OpenAPI parity at the actual browse HTTP boundary.

Scripted typed store pages isolate transport and authorization outcomes only.
Native matching/filtering/ranking remains in test_browse_postgres and cannot
be accepted from these ASGI checks or generated declaration-only handlers.
"""

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.contracts.domain_types import ListingSummary
from app.core.auth import CallerContext, require_caller
from app.core.errors import ERRORS, PublicError, install_error_handlers
from app.core.pagination import Page
from app.domains.listings.browse_routes import router
from contracts.source.types import ErrorEnvelope as ReviewedError
from contracts.source.types import ListingSummary as ReviewedSummary
from contracts.source.types import PageResult as ReviewedPage

ROOT = Path(__file__).resolve().parents[5]
USER = UUID("10000000-0000-4000-8000-000000000001")
ITEM = UUID("20000000-0000-4000-8000-000000000001")


def reviewed_document():
    """Read the generated, freshness-checked authoritative document from this clone."""
    return json.loads((ROOT / "contracts/generated/openapi.json").read_text())


def expanded(document, schema):
    """Resolve only local schema references, never networks or external resources."""
    if isinstance(schema, list):
        return [expanded(document, value) for value in schema]
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        assert set(schema) == {"$ref"}
        reference = schema["$ref"]
        assert reference.startswith("#/components/schemas/")
        value = document
        for part in reference[2:].split("/"):
            value = value[part.replace("~1", "/").replace("~0", "~")]
        return expanded(document, value)
    return {key: expanded(document, value) for key, value in schema.items()}


def application(*, authenticated=True, eligible=True, stored=True, failure=None):
    """Install real router/error handlers with explicitly synthetic dependencies."""
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(router)
    if authenticated:
        app.dependency_overrides[require_caller] = lambda: CallerContext(
            USER, "regular", datetime.now(UTC) + timedelta(hours=1)
        )
    summary = ListingSummary(
        listing_id=ITEM,
        title="Synthetic contract bicycle",
        description="Controlled public summary",
        category_code="bicycles",
        category_label="Bicycles",
        condition_code="good",
        condition_label="Good",
        asking_price_paise=0,
        negotiable=False,
        pickup_area=None,
        available_from=datetime(2026, 1, 1, tzinfo=UTC),
        available_until=None,
        availability="available",
        sensitive_purchase=False,
        image_ids=[],
    )

    async def result(query, now):
        """Return a scripted transport page, not a query/filter implementation."""
        del now
        if failure is not None:
            raise PublicError(ERRORS[failure])
        return Page((summary,), query.page, query.page_size, False)

    store = SimpleNamespace(browse_available_listings=AsyncMock(side_effect=result))
    if stored:
        app.state.listings_store = store
    app.state.listings_browse_identity = SimpleNamespace(
        account_is_eligible=AsyncMock(return_value=eligible)
    )
    return app, store


def test_runtime_query_and_response_schemas_match_reviewed_operation():
    """Compare dereferenced success/error schemas, not just generated model names."""
    app, _ = application()
    runtime = app.openapi()
    reviewed = reviewed_document()
    actual = runtime["paths"]["/listings"]["get"]
    expected = reviewed["paths"]["/listings"]["get"]
    assert (
        actual["operationId"] == expected["operationId"] == "listings_query_available"
    )
    assert actual["parameters"] == expected["parameters"]
    assert set(actual["responses"]) == set(expected["responses"])
    for status in actual["responses"]:
        actual_schema = actual["responses"][status]["content"]["application/json"][
            "schema"
        ]
        expected_schema = expected["responses"][status]["content"]["application/json"][
            "schema"
        ]
        assert expanded(runtime, actual_schema) == expanded(reviewed, expected_schema)


@pytest.mark.parametrize(
    "query",
    [
        {},
        {"q": "quasar telescope"},
        {
            "category_code": "bicycles",
            "condition_code": "good",
            "min_price_paise": "0",
            "max_price_paise": "100",
            "negotiable": "false",
            "sort": "price_asc",
            "page": "2",
            "page_size": "50",
        },
        {"sort": "price_desc", "page_size": "100"},
    ],
)
def test_actual_http_success_validates_against_reviewed_source_response(query):
    """Use actual serialized wire bytes and editable-source response models."""
    app, store = application()
    with TestClient(app) as client:
        response = client.get("/listings", params=query)
    assert response.status_code == 200
    body = response.json()
    validated = ReviewedPage[ReviewedSummary].model_validate_json(response.text)
    assert validated.model_dump(mode="json") == body
    assert response.headers["cache-control"] == "private, no-store"
    assert set(body["items"][0]) == set(ReviewedSummary.model_fields)
    store.browse_available_listings.assert_awaited_once()


@pytest.mark.parametrize(
    "case,status",
    [
        ("anonymous", 401),
        ("denied", 403),
        ("invalid", 422),
        ("missing-store", 503),
        ("provider-unavailable", 503),
    ],
)
def test_actual_error_response_matches_reviewed_envelope_and_status(case, status):
    """Failures retain their declared status and do not disclose rejected values."""
    app, store = application(
        authenticated=case != "anonymous",
        eligible=case != "denied",
        stored=case != "missing-store",
        failure=503 if case == "provider-unavailable" else None,
    )
    params = {"sort": "synthetic-private-invalid"} if case == "invalid" else {}
    with TestClient(app) as client:
        response = client.get("/listings", params=params)
    assert response.status_code == status
    assert str(status) in reviewed_document()["paths"]["/listings"]["get"]["responses"]
    parsed = ReviewedError.model_validate_json(response.text)
    assert parsed.error.code == ERRORS[status].code
    assert "synthetic-private-invalid" not in response.text
    assert "items" not in response.json()
    if case != "provider-unavailable":
        store.browse_available_listings.assert_not_awaited()
