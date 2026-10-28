"""Transient matching consumer contracts; no fake SQL or wanted persistence."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.contracts.domain_types import ListingSummary
from app.core.auth import CallerContext, require_caller
from app.core.errors import ERRORS, PublicError, install_error_handlers
from app.core.pagination import Page
from app.domains.search.draft_matches import DraftMatchService
from app.domains.search.wanted_models import DraftTitle
from app.domains.search.wanted_routes import router, draft_match_service


def caller(account_class="regular"):
    """Keep trusted synthetic caller validity relative to actual auth time."""
    return CallerContext(
        uuid4(), account_class, datetime.now(UTC) + timedelta(minutes=5)
    )


def summary():
    """One typed public fixture, without owner/contact/selection values."""
    return ListingSummary(
        listing_id=uuid4(),
        title="Synthetic book",
        description="Controlled match fixture",
        category_code="books",
        category_label="Books",
        condition_code="good",
        condition_label="Good",
        asking_price_paise=100,
        original_price_paise=None,
        negotiable=False,
        pickup_area=None,
        available_from=datetime.now(UTC) - timedelta(days=1),
        available_until=None,
        availability="available",
        sensitive_purchase=False,
        image_ids=[uuid4()],
    )


@pytest.mark.parametrize("text", ["", "   ", "x" * 121])
def test_draft_rejects_empty_and_excess_text(text):
    with pytest.raises(ValidationError):
        DraftTitle(draft_title=text)


def test_draft_trims_before_limit_and_rejects_unreviewed_fields():
    assert len(DraftTitle(draft_title=" " + ("x" * 120) + " ").draft_title) == 120
    for extra in ["category_code", "budget_paise", "search_mode", "user_id"]:
        with pytest.raises(ValidationError):
            DraftTitle(draft_title="books", **{extra: "controlled"})


@pytest.mark.parametrize("account_class", ["regular", "temporary"])
def test_query_has_title_only_fixed_order_and_first_page(account_class):
    async def exercise():
        listings, identity = AsyncMock(), AsyncMock()
        identity.eligible.return_value = True
        listings.query_available_listings.return_value = Page(
            items=(summary(),), page=1, page_size=20, has_next=False
        )
        actor = caller(account_class)
        result = await DraftMatchService(listings, identity).match(
            actor, DraftTitle(draft_title="  cycle  ")
        )
        identity.eligible.assert_awaited_once_with(actor.user_id)
        actual_actor, query = listings.query_available_listings.await_args.args
        assert actual_actor == actor
        assert (
            query.q == "cycle"
            and query.sort == "created_desc"
            and query.search_mode == "keyword"
        )
        assert (query.page, query.page_size) == (1, 20)
        assert all(
            getattr(query, name) is None
            for name in [
                "category_code",
                "min_price_paise",
                "max_price_paise",
                "condition_code",
                "negotiable",
            ]
        )
        assert len(result.items) == 1 and result.has_more is False

    asyncio.run(exercise())


def test_empty_and_full_page_meaning():
    async def exercise():
        listings, identity = AsyncMock(), AsyncMock()
        identity.eligible.return_value = True
        service = DraftMatchService(listings, identity)
        listings.query_available_listings.return_value = Page(
            items=(), page=1, page_size=20, has_next=False
        )
        assert (
            await service.match(caller(), DraftTitle(draft_title="books"))
        ).items == []
        listings.query_available_listings.return_value = Page(
            items=tuple(summary() for _ in range(20)),
            page=1,
            page_size=20,
            has_next=True,
        )
        result = await service.match(caller(), DraftTitle(draft_title="books"))
        assert len(result.items) == 20 and result.has_more is True

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "bad",
    [
        "too_many",
        "wrong_page",
        "wrong_size",
        "duplicate",
        "unavailable",
        "short_more",
        "invalid_item",
        "invalid_items",
    ],
)
def test_invalid_provider_page_fails_closed(bad):
    async def exercise():
        listings, identity = AsyncMock(), AsyncMock()
        identity.eligible.return_value = True
        item = summary()
        kwargs = dict(items=(item,), page=1, page_size=20, has_next=False)
        if bad == "too_many":
            kwargs["items"] = tuple(summary() for _ in range(21))
        if bad == "wrong_page":
            kwargs["page"] = 2
        if bad == "wrong_size":
            kwargs["page_size"] = 50
        if bad == "duplicate":
            kwargs["items"] = (item, item)
        if bad == "unavailable":
            kwargs["items"] = (item.model_copy(update={"availability": "unavailable"}),)
        if bad == "short_more":
            kwargs["has_next"] = True
        if bad == "invalid_item":
            kwargs["items"] = ({"private_owner": "controlled"},)
        if bad == "invalid_items":
            kwargs["items"] = None
        listings.query_available_listings.return_value = Page(**kwargs)
        with pytest.raises(PublicError) as failure:
            await DraftMatchService(listings, identity).match(
                caller(), DraftTitle(draft_title="books")
            )
        assert failure.value.spec.status == 503

    asyncio.run(exercise())


@pytest.mark.parametrize("failure", [NotImplementedError, TimeoutError, OSError])
def test_provider_outage_is_not_an_empty_success(failure):
    async def exercise():
        listings, identity = AsyncMock(), AsyncMock()
        identity.eligible.return_value = True
        listings.query_available_listings.side_effect = failure("controlled")
        with pytest.raises(PublicError) as error:
            await DraftMatchService(listings, identity).match(
                caller(), DraftTitle(draft_title="books")
            )
        assert error.value.spec.status == 503

    asyncio.run(exercise())


def test_denial_expiry_and_real_default_do_not_fake_matches():
    async def exercise():
        listings, identity = AsyncMock(), AsyncMock()
        identity.eligible.return_value = False
        service = DraftMatchService(listings, identity)
        with pytest.raises(PublicError) as error:
            await service.match(caller(), DraftTitle(draft_title="books"))
        assert error.value.spec.status == 403
        listings.query_available_listings.assert_not_awaited()
        actor = CallerContext(
            uuid4(), "temporary", datetime.now(UTC) - timedelta(seconds=1)
        )
        identity.eligible.reset_mock()
        with pytest.raises(PublicError) as error:
            await service.match(actor, DraftTitle(draft_title="books"))
        assert error.value.spec.status == 401
        identity.eligible.assert_not_awaited()
        with pytest.raises(PublicError) as error:
            await DraftMatchService().match(caller(), DraftTitle(draft_title="books"))
        assert error.value.spec.status == 503

    asyncio.run(exercise())


def test_http_matching_needs_no_search_store_and_uses_private_errors():
    """Explicit typed provider fixture; all body/auth/error handling is real HTTP."""
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(router)
    listings, identity = AsyncMock(), AsyncMock()
    identity.eligible.return_value = True
    listings.query_available_listings.return_value = Page(
        items=(), page=1, page_size=20, has_next=False
    )
    app.dependency_overrides[draft_match_service] = lambda: DraftMatchService(
        listings, identity
    )
    with TestClient(app) as client:
        assert (
            client.post(
                "/wanted-requests/draft-matches", json={"draft_title": "books"}
            ).status_code
            == 401
        )
        app.dependency_overrides[require_caller] = lambda: caller("temporary")
        response = client.post(
            "/wanted-requests/draft-matches", json={"draft_title": " books "}
        )
        assert response.status_code == 200 and response.json() == {
            "items": [],
            "has_more": False,
        }
        assert response.headers["cache-control"] == "private, no-store"
        response = client.post(
            "/wanted-requests/draft-matches",
            json={"draft_title": "books", "budget_paise": 0},
        )
        assert (
            response.status_code == 422
            and response.headers["cache-control"] == "private, no-store"
        )
        listings.query_available_listings.side_effect = PublicError(ERRORS[503])
        response = client.post(
            "/wanted-requests/draft-matches", json={"draft_title": "books"}
        )
        assert (
            response.status_code == 503
            and response.headers["cache-control"] == "private, no-store"
        )
