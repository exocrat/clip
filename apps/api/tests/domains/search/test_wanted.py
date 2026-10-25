"""Wanted validation/auth/HTTP contracts, with explicit dependency doubles only."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.contracts.domain_types import Category, CategoryDisplay
from app.core.auth import CallerContext, require_caller
from app.core.errors import PublicError, install_error_handlers
from app.domains.search.wanted import PublicWantedDependencies, WantedService
from app.domains.search.wanted_models import (
    WantedCreate,
    WantedPage,
    WantedPatch,
    WantedState,
)
from app.domains.search.wanted_routes import router, wanted_service


def create_values(**changes):
    """Controlled valid input without user IDs or private contacts."""
    return dict(
        title="Synthetic books",
        description="Synthetic request",
        category_code="books",
        operation_id=uuid4(),
        **changes,
    )


@pytest.mark.parametrize("budget", [True, False, 1.0, 100.0, -100, 1, "100", 10**30])
def test_create_budget_rejects_coercion_and_fractional_money(budget):
    with pytest.raises(ValidationError):
        WantedCreate(**create_values(budget_paise=budget))


def test_trim_before_limit_and_patch_omission_null_zero():
    """Text bounds follow trimming; omitted nullable budget retains its intent."""
    body = create_values()
    body["title"] = "  " + "x" * 120 + " "
    assert len(WantedCreate(**body).title) == 120
    base = dict(expected_revision=1, operation_id=uuid4())
    assert "budget_paise" not in WantedPatch(**base).model_fields_set
    assert WantedPatch(**base, budget_paise=None).budget_paise is None
    assert WantedPatch(**base, budget_paise=0).budget_paise == 0
    for field in ["title", "description", "category_code"]:
        with pytest.raises(ValidationError):
            WantedPatch(**base, **{field: None})
    for text in ["", "  ", "x" * 121]:
        body["title"] = text
        with pytest.raises(ValidationError):
            WantedCreate(**body)


@pytest.mark.parametrize("revision", [True, 1.0, "1", 0, -1])
def test_exact_revision_required(revision):
    for model, extra in [(WantedPatch, {}), (WantedState, {"state": "open"})]:
        with pytest.raises(ValidationError):
            model(expected_revision=revision, operation_id=uuid4(), **extra)


@pytest.mark.parametrize(
    "values",
    [{"page": True}, {"page": 1.0}, {"page_size": 21}, {"page": 0}, {"page": 10**30}],
)
def test_page_bounds(values):
    with pytest.raises(ValidationError):
        WantedPage(**values)


@pytest.mark.parametrize("account_class", ["regular", "temporary"])
def test_auth_expiry_and_live_eligibility_before_storage(account_class):
    async def exercise():
        store, dependencies = AsyncMock(), AsyncMock()
        service = WantedService(store, dependencies)
        caller = CallerContext(
            uuid4(), account_class, datetime.now(UTC) - timedelta(seconds=1)
        )
        with pytest.raises(PublicError) as error:
            await service.listing(caller, WantedPage())
        assert error.value.spec.status == 401
        dependencies.eligible.assert_not_awaited()
        store.listing.assert_not_awaited()
        caller = CallerContext(
            caller.user_id, account_class, datetime.now(UTC) + timedelta(minutes=5)
        )
        dependencies.eligible.return_value = False
        with pytest.raises(PublicError) as error:
            await service.listing(caller, WantedPage())
        assert error.value.spec.status == 403
        store.listing.assert_not_awaited()
        dependencies.eligible.side_effect = NotImplementedError
        with pytest.raises(PublicError) as error:
            await service.listing(caller, WantedPage())
        assert error.value.spec.status == 503

    asyncio.run(exercise())


def test_catalogue_current_vs_historical_and_dependency_failure():
    async def exercise():
        dependencies = AsyncMock()
        service = WantedService(AsyncMock(), dependencies)
        dependencies.active_categories.return_value = (
            Category(code="books", label="Books"),
        )
        dependencies.category_display.return_value = (
            CategoryDisplay(code="old", label="Old", active=False),
        )
        assert await service.resolve_label("books", True) == "Books"
        assert await service.resolve_label("old", False) == "Old"
        with pytest.raises(PublicError) as error:
            await service.resolve_label("old", True)
        assert error.value.spec.status == 422
        dependencies.category_display.return_value = ()
        with pytest.raises(PublicError) as error:
            await service.resolve_label("old", False)
        assert error.value.spec.status == 503
        dependencies.active_categories.side_effect = TimeoutError
        with pytest.raises(PublicError) as error:
            await service.resolve_label("books", True)
        assert error.value.spec.status == 503

    asyncio.run(exercise())


def test_http_fails_closed_no_store_and_client_actor_claims_ignored():
    """Normal auth accepts no header/body identity; absence of storage is503."""
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get("/wanted-requests", headers={"X-User-ID": str(uuid4())})
        assert response.status_code == 401
        assert response.headers["cache-control"] == "private, no-store"
        app.dependency_overrides[require_caller] = lambda: CallerContext(
            uuid4(), "regular", datetime.now(UTC) + timedelta(minutes=1)
        )
        response = client.get("/wanted-requests")
        assert response.status_code == 503
        assert response.headers["cache-control"] == "private, no-store"


def test_real_identity_default_remains_unavailable():
    """Declaration-only public dependencies never fabricate success."""

    async def exercise():
        service = WantedService(AsyncMock(), PublicWantedDependencies())
        caller = CallerContext(
            uuid4(), "temporary", datetime.now(UTC) + timedelta(minutes=1)
        )
        with pytest.raises(PublicError) as error:
            await service.authorize(caller)
        assert error.value.spec.status == 503

    asyncio.run(exercise())


def test_wanted_http_operations_match_reviewed_schema():
    """Compare implemented wire shapes to generated contract, resolving local refs."""
    import json
    from pathlib import Path

    app = FastAPI()
    app.include_router(router)
    actual = app.openapi()
    expected = json.loads(
        (
            Path(__file__).resolve().parents[5] / "contracts/generated/openapi.json"
        ).read_text()
    )

    def shape(value, root):
        """Ignore documentation titles; retain types, requiredness and constraints."""
        if isinstance(value, dict):
            if "$ref" in value:
                node = root
                for part in value["$ref"].removeprefix("#/").split("/"):
                    node = node[part]
                return shape(node, root)
            return {
                key: shape(item, root)
                for key, item in value.items()
                if not (key in {"title", "description"} and isinstance(item, str))
            }
        if isinstance(value, list):
            return [shape(item, root) for item in value]
        return value

    for path, methods in actual["paths"].items():
        for method, operation in methods.items():
            approved = expected["paths"][path][method]
            assert operation["operationId"] == approved["operationId"]
            assert set(operation["responses"]) == set(approved["responses"])
            for status in operation["responses"]:
                assert shape(operation["responses"][status], actual) == shape(
                    approved["responses"][status], expected
                )
            assert shape(operation.get("requestBody"), actual) == shape(
                approved.get("requestBody"), expected
            )
            assert shape(operation.get("parameters", []), actual) == shape(
                approved.get("parameters", []), expected
            )


@pytest.mark.parametrize("text", ["x" * 5000, "📚" * 5000])
def test_description_limit_counts_trimmed_unicode_code_points(text):
    """The reviewed bound applies to characters, not UTF-8 byte length."""
    values = create_values()
    values["description"] = " " + text + " \n"
    assert WantedCreate(**values).description == text


@pytest.mark.parametrize("text", ["", " \n\t", "x" * 5001])
def test_description_rejects_blank_or_excess_after_trim(text):
    """API models reject invalid descriptions before any dependency/write."""
    values = create_values()
    values["description"] = text
    with pytest.raises(ValidationError):
        WantedCreate(**values)
