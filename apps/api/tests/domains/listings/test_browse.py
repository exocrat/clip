"""Isolated browse HTTP/authorization checks; SQL behavior has separate real tests.

Stores return scripted contract pages only. They do not implement fake listing
filtering/ranking, authenticate users or stand in for PostgreSQL acceptance.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.contracts.domain_types import (
    AccountEligibility,
    ListingQuery,
    ListingSummary,
)
from app.core.auth import CallerContext, require_caller
from app.core.errors import ERRORS, FieldError, PublicError, install_error_handlers
from app.core.pagination import Page
from app.domains.listings.browse import ListingsBrowseService, PublicBrowseIdentity
from app.domains.listings.browse_routes import router
from app.domains.listings.browse_store import browse_statement, read_browse_page
from app.domains.listings.browse_validation import BrowseQuery
from pydantic import ValidationError

NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)
USER_ID = UUID("10000000-0000-4000-8000-000000000001")
LISTING_ID = UUID("20000000-0000-4000-8000-000000000001")


def summary() -> ListingSummary:
    """Provide only reviewed public fields with explicitly synthetic content."""
    return ListingSummary(
        listing_id=LISTING_ID,
        title="Synthetic bicycle",
        description="Synthetic fixture",
        category_code="bicycles",
        category_label="Bicycles",
        condition_code="good",
        condition_label="Good",
        asking_price_paise=0,
        negotiable=False,
        pickup_area=None,
        available_from=NOW - timedelta(days=1),
        available_until=None,
        availability="available",
        sensitive_purchase=False,
        image_ids=[],
    )


def caller(account_class="regular", expired=False) -> CallerContext:
    """Create trusted test context only; the HTTP app never reads caller headers."""
    return CallerContext(
        USER_ID, account_class, NOW + timedelta(days=-1 if expired else 1)
    )


def service(*, eligible=True):
    """Bind scripted eligibility and an empty page, without fake query behavior."""
    store = SimpleNamespace(
        browse_available_listings=AsyncMock(return_value=Page((), 1, 20, False))
    )
    identity = SimpleNamespace(account_is_eligible=AsyncMock(return_value=eligible))
    return ListingsBrowseService(store, identity, clock=lambda: NOW), store, identity


@pytest.mark.parametrize("account_class", ["regular", "temporary"])
def test_eligible_callers_reach_authorized_public_boundary(account_class):
    """Both reviewed caller classes may request browse after current eligibility."""
    subject, store, identity = service()
    result = asyncio.run(
        subject.query_available_listings(
            caller(account_class), ListingQuery(page=3, page_size=50)
        )
    )
    assert result.items == ()
    identity.account_is_eligible.assert_awaited_once_with(USER_ID)
    query, moment = store.browse_available_listings.await_args.args
    assert (query.page, query.page_size, moment) == (3, 50, NOW)


@pytest.mark.parametrize(
    "expired,eligible,status", [(True, True, 401), (False, False, 403)]
)
def test_denials_precede_data_access(expired, eligible, status):
    """Expired/revoked contexts cannot expose listing pages or presence."""
    subject, store, identity = service(eligible=eligible)
    with pytest.raises(PublicError) as failure:
        asyncio.run(
            subject.query_available_listings(caller(expired=expired), ListingQuery())
        )
    assert failure.value.spec.status == status
    store.browse_available_listings.assert_not_awaited()
    if expired:
        identity.account_is_eligible.assert_not_awaited()


@pytest.mark.parametrize(
    "filters",
    [
        {"category_code": "bicycles"},
        {"condition_code": "good"},
        {"min_price_paise": 0},
        {"max_price_paise": 100},
        {"negotiable": False},
        {"sort": "price_asc"},
        {"sort": "price_desc"},
    ],
)
def test_reviewed_filters_and_sorts_are_forwarded(filters):
    """Every supplied filter reaches the owned query, including false/zero values."""
    subject, store, _ = service()
    asyncio.run(subject.query_available_listings(caller(), ListingQuery(**filters)))
    received = store.browse_available_listings.await_args.args[0]
    assert all(getattr(received, field) == value for field, value in filters.items())


def test_whitespace_query_is_browse_and_huge_offset_is_safe():
    """Respect trimmed-empty semantics and reject SQL integer overflow safely."""
    subject, store, _ = service()
    asyncio.run(subject.query_available_listings(caller(), ListingQuery(q=" \t ")))
    store.browse_available_listings.assert_awaited_once()
    assert store.browse_available_listings.await_args.args[0].q is None
    with pytest.raises(PublicError) as failure:
        asyncio.run(
            subject.query_available_listings(caller(), ListingQuery(page=2**63))
        )
    assert failure.value.spec.status == 422


@pytest.mark.parametrize(
    "text",
    ["  bicycle  ", "the and", "bicycle | laptop", "'); SELECT pg_sleep(10); --"],
)
def test_text_is_trimmed_and_forwarded_without_client_side_matching(text):
    """Only PostgreSQL interprets normalized plain text; the service forwards it."""
    subject, store, _ = service()
    request = ListingQuery(q=text)
    asyncio.run(subject.query_available_listings(caller(), request))
    assert store.browse_available_listings.await_args.args[0].q == text.strip()
    assert request.q == text


def test_text_sql_keeps_adversarial_input_out_of_statement():
    """SQL syntax-looking text is a bound value, never executable SQL fragments."""
    text = "'); SELECT pg_sleep(10); --"
    statement, parameters = browse_statement(ListingQuery(page=2, q=text), NOW, 500000)
    assert text not in statement
    assert text in parameters
    assert statement.count("%s") == len(parameters)
    assert "plainto_tsquery('pg_catalog.english', %s)" in statement


def test_http_text_search_uses_existing_public_page_response():
    """HTTP dispatch forwards text through the reviewed operation and page envelope."""
    application, store = app()
    with TestClient(application) as client:
        response = client.get("/listings", params={"q": " bicycle "})
    assert response.status_code == 200
    assert response.json()["items"][0] == summary().model_dump(mode="json")
    assert store.browse_available_listings.await_args.args[0].q == "bicycle"


def test_identity_unavailable_never_reports_success():
    """Missing/recovering public dependencies preserve a safe unavailable outcome."""
    subject, store, identity = service()
    identity.account_is_eligible.side_effect = PublicError(ERRORS[503])
    with pytest.raises(PublicError) as failure:
        asyncio.run(subject.query_available_listings(caller(), ListingQuery()))
    assert failure.value.spec.status == 503
    store.browse_available_listings.assert_not_awaited()


def app(*, authenticate=True, store_present=True):
    """Create a test-only ASGI app with explicitly injected synthetic boundaries."""
    application = FastAPI()
    install_error_handlers(application)
    application.include_router(router)
    if authenticate:
        # The HTTP dependency validates wall-clock expiry, independently of NOW.
        application.dependency_overrides[require_caller] = lambda: CallerContext(
            USER_ID, "temporary", datetime.now(UTC) + timedelta(hours=1)
        )
    identity = SimpleNamespace(account_is_eligible=AsyncMock(return_value=True))
    store = SimpleNamespace(
        browse_available_listings=AsyncMock(
            return_value=Page((summary(),), 1, 20, False)
        )
    )
    if store_present:
        application.state.listings_store = store
    application.state.listings_browse_identity = identity
    return application, store


def test_http_response_matches_reviewed_envelope_and_summary_privacy():
    """Use the actual router and generated response type, not a mock HTTP response."""
    application, store = app()
    with TestClient(application) as client:
        response = client.get("/listings")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "page", "page_size", "has_next"}
    assert body["items"][0] == summary().model_dump(mode="json")
    assert not {
        "owner_id",
        "selected_buyer_id",
        "revision",
        "object_key",
        "proof_available",
    }.intersection(body["items"][0])
    store.browse_available_listings.assert_awaited_once()


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page=-1",
        "page=not-an-integer",
        "page_size=21",
        "page_size=1000",
        "user_id=synthetic-spoof",
        "owner_id=synthetic-spoof",
        "q=" + "x" * 121,
    ],
)
def test_malformed_or_spoofed_query_rejected(query):
    """Query validation cannot be used to select an actor or request unbounded pages."""
    application, store = app()
    with TestClient(application) as client:
        response = client.get("/listings?" + query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    store.browse_available_listings.assert_not_awaited()


def test_anonymous_and_missing_store_fail_closed():
    """Normal transport never trusts a user header or invents a successful empty page."""
    for authenticate, store_present, expected in (
        (False, True, 401),
        (True, False, 503),
    ):
        application, store = app(authenticate=authenticate, store_present=store_present)
        with TestClient(application) as client:
            response = client.get("/listings", headers={"X-User-Id": str(USER_ID)})
        assert response.status_code == expected
        store.browse_available_listings.assert_not_awaited()


def test_default_route_never_falls_back_to_synthetic_seller_eligibility():
    """Normal browse binding must use the unavailable real Identity declaration."""
    application, store = app()
    del application.state.listings_browse_identity
    seller_identity = SimpleNamespace(account_is_eligible=AsyncMock(return_value=True))
    application.state.listings_identity = seller_identity
    with TestClient(application) as client:
        response = client.get("/listings")
    assert response.status_code == 503
    store.browse_available_listings.assert_not_awaited()
    seller_identity.account_is_eligible.assert_not_awaited()


@pytest.mark.parametrize("eligible", [True, False])
def test_public_read_identity_accepts_both_classes_without_regular_only_constraint(
    monkeypatch, eligible
):
    """Verify the declared capability call, while leaving real Identity pending."""
    operation = AsyncMock(return_value=AccountEligibility(eligible=eligible))
    monkeypatch.setattr(
        "app.domains.identity.public.check_account_eligibility", operation
    )
    assert asyncio.run(PublicBrowseIdentity().account_is_eligible(USER_ID)) is eligible
    operation.assert_awaited_once_with(USER_ID, required_class=None)


@pytest.mark.parametrize("failure", [NotImplementedError, TimeoutError, OSError])
def test_public_read_identity_maps_unavailable_provider(monkeypatch, failure):
    """An absent/timed-out provider must not fall back to trusting caller claims."""
    monkeypatch.setattr(
        "app.domains.identity.public.check_account_eligibility",
        AsyncMock(side_effect=failure),
    )
    with pytest.raises(PublicError) as error:
        asyncio.run(PublicBrowseIdentity().account_is_eligible(USER_ID))
    assert error.value.spec.status == 503


@pytest.mark.parametrize(
    "query",
    [
        {"page": True},
        {"page": 1.0},
        {"page": "1.0"},
        {"page_size": "2e1"},
        {"min_price_paise": False},
        {"min_price_paise": 100.0},
        {"max_price_paise": "100.0"},
        {"min_price_paise": "1e2"},
        {"min_price_paise": -100},
        {"max_price_paise": 1},
        {"min_price_paise": 200, "max_price_paise": 100},
        {"sort": "price_asc; SELECT 1"},
        {"page": 2**63},
        {"page_size": 101},
        {"q": "🙂" * 121},
    ],
)
def test_runtime_query_rejects_coercion_reversed_ranges_and_expensive_invalid_shapes(
    query,
):
    """Preserve exact money/page types and reviewed bounds without rounding."""
    with pytest.raises(ValidationError):
        BrowseQuery.model_validate(query)


@pytest.mark.parametrize(
    "query",
    [
        "min_price_paise=100.0",
        "max_price_paise=1e2",
        "min_price_paise=-100",
        "min_price_paise=200&max_price_paise=100",
        "min_price_paise=101",
        "page=1.0",
        "page_size=20.0",
        "negotiable=maybe",
        "sort=unsafe",
    ],
)
def test_http_invalid_filters_are_value_free_and_never_reach_store(query):
    """The actual route reports shared validation errors before executing SQL."""
    application, store = app()
    with TestClient(application) as client:
        response = client.get("/listings?" + query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    store.browse_available_listings.assert_not_awaited()


def test_http_combined_filters_keep_zero_false_and_reviewed_sort():
    """Inspect forwarded contract inputs without pretending scripted pages filter."""
    application, store = app()
    with TestClient(application) as client:
        response = client.get(
            "/listings",
            params={
                "q": " bicycle ",
                "category_code": "bicycles",
                "condition_code": "good",
                "min_price_paise": 0,
                "max_price_paise": 100,
                "negotiable": "false",
                "sort": "price_desc",
                "page": 2,
                "page_size": 50,
            },
        )
    assert response.status_code == 200
    query = store.browse_available_listings.await_args.args[0]
    assert (
        query.model_dump()
        == BrowseQuery(
            q="bicycle",
            category_code="bicycles",
            condition_code="good",
            min_price_paise=0,
            max_price_paise=100,
            negotiable=False,
            sort="price_desc",
            page=2,
            page_size=50,
        ).model_dump()
    )


def test_trimmed_unicode_query_limit_and_no_selected_price_cap():
    """Count Unicode code points after trimming; do not invent a monetary cap."""
    assert BrowseQuery(q="  " + "🙂" * 120 + "  ").q == "🙂" * 120
    assert BrowseQuery(q=" \t ").q is None
    assert BrowseQuery(max_price_paise=10**100).max_price_paise == 10**100


def test_all_filter_values_are_bound_and_large_amounts_preserve_storage_semantics():
    """SQL-looking codes stay parameters; values outside bigint cannot overflow SQL."""
    code = "books' OR true --"
    query = BrowseQuery(
        category_code=code,
        condition_code="good",
        negotiable=False,
        min_price_paise=0,
        max_price_paise=100,
        sort="price_asc",
    )
    statement, parameters = browse_statement(query, NOW, 500000)
    assert code not in statement and code in parameters
    assert any(value is False for value in parameters)
    assert statement.count("%s") == len(parameters)
    large = 10**100
    empty_sql, empty_parameters = browse_statement(
        BrowseQuery(min_price_paise=large), NOW, 500000
    )
    assert "AND FALSE" in empty_sql and large not in empty_parameters
    _, all_parameters = browse_statement(
        BrowseQuery(max_price_paise=large), NOW, 500000
    )
    assert large not in all_parameters


def test_unknown_catalogue_error_is_safe_at_http_boundary():
    """The owned store's reviewed validation failure must survive HTTP composition."""
    application, store = app()
    store.browse_available_listings.side_effect = PublicError(
        ERRORS[422], (FieldError("category_code", "active_catalogue_value_required"),)
    )
    with TestClient(application) as client:
        response = client.get(
            "/listings", params={"category_code": "synthetic-missing-code"}
        )
    assert response.status_code == 422
    assert "synthetic-missing-code" not in response.text
    assert response.json()["error"]["details"] == [
        {"field": "category_code", "code": "active_catalogue_value_required"}
    ]


@pytest.mark.parametrize(
    "flags,expected",
    [
        ({"category_valid": False, "condition_valid": True}, 422),
        ({"category_valid": True, "condition_valid": False}, 422),
        (None, 503),
    ],
)
def test_catalogue_preflight_refuses_invalid_or_missing_result_without_fetching_listings(
    flags, expected
):
    """Script catalogue outcomes only; no fake listing query is implemented."""
    cursor = SimpleNamespace(fetchone=AsyncMock(return_value=flags))
    connection = SimpleNamespace(execute=AsyncMock(return_value=cursor))
    query = BrowseQuery(category_code="synthetic-missing", condition_code="good")
    with pytest.raises(PublicError) as failure:
        asyncio.run(read_browse_page(connection, query, NOW, 500000))
    assert failure.value.spec.status == expected
    connection.execute.assert_awaited_once()
    sql, parameters = connection.execute.await_args.args
    assert "synthetic-missing" not in sql and "synthetic-missing" in parameters


def test_internal_reversed_range_is_shared_error_before_store():
    """Generated types declare fields; the runtime service owns cross-field checks."""
    subject, store, _ = service()
    with pytest.raises(PublicError) as failure:
        asyncio.run(
            subject.query_available_listings(
                caller(), ListingQuery(min_price_paise=200, max_price_paise=100)
            )
        )
    assert failure.value.spec.status == 422
    store.browse_available_listings.assert_not_awaited()


def test_runtime_validation_preserves_frozen_public_query_schema():
    """Stricter parsing introduces no new fields, defaults, enums or schema bounds."""
    assert (
        BrowseQuery.model_json_schema()["properties"]
        == ListingQuery.model_json_schema()["properties"]
    )


@pytest.mark.parametrize("url", ["/listings", "/listings?q=bicycle"])
def test_repeated_reads_recheck_store_and_never_reuse_prior_response(url):
    """Script changing provider outcomes; no fake availability/filter logic is used."""
    application, store = app()
    store.browse_available_listings.side_effect = [
        Page((summary(),), 1, 20, False),
        Page((), 1, 20, False),
        Page((summary(),), 1, 20, False),
    ]
    with TestClient(application) as client:
        responses = [client.get(url) for _ in range(3)]
    assert [len(response.json()["items"]) for response in responses] == [1, 0, 1]
    assert all(
        response.headers["cache-control"] == "private, no-store"
        for response in responses
    )
    assert store.browse_available_listings.await_count == 3
    assert (
        application.state.listings_browse_identity.account_is_eligible.await_count == 3
    )


def test_dependency_failure_after_success_does_not_return_stale_page():
    """A transient store failure must be observable rather than cached success."""
    application, store = app()
    store.browse_available_listings.side_effect = [
        Page((summary(),), 1, 20, False),
        PublicError(ERRORS[503]),
        Page((summary(),), 1, 20, False),
    ]
    with TestClient(application) as client:
        responses = [client.get("/listings") for _ in range(3)]
    assert [response.status_code for response in responses] == [200, 503, 200]
    assert responses[1].json()["error"]["code"] == "dependency_unavailable"
    assert "items" not in responses[1].json()
    assert store.browse_available_listings.await_count == 3


def test_revocation_after_success_is_rechecked_before_next_store_read():
    """A previously eligible caller cannot bypass a fresh capability denial."""
    application, store = app()
    application.state.listings_browse_identity.account_is_eligible.side_effect = [
        True,
        False,
    ]
    with TestClient(application) as client:
        assert client.get("/listings").status_code == 200
        assert client.get("/listings").status_code == 403
    store.browse_available_listings.assert_awaited_once()
