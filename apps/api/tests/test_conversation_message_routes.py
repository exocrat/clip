"""Fail-closed routing checks for the mounted public Conversations router."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.core.auth import CallerContext, require_caller
from app.core.config import Settings
from app.core.errors import ERRORS
from app.main import create_app
from app.contracts.domain_types import EntryPage, PageResult, ConversationSummary
from app.domains.conversations import routes


@pytest.fixture
def query_client(monkeypatch):
    """Capture parsed HTTP values without claiming database/auth integration."""
    captured = []
    app = create_app(Settings(environment="test"))
    actor = CallerContext(uuid4(), "regular", datetime.now(UTC) + timedelta(hours=1))
    app.dependency_overrides[require_caller] = lambda: actor
    monkeypatch.setattr(routes, "_pool", lambda request: None)

    async def inbox(self, caller, query):
        captured.append(query)
        return PageResult[ConversationSummary](
            items=[], page=query.page, page_size=query.page_size, has_next=False
        )

    async def entries(self, caller, conversation_id, query):
        captured.append(query)
        return EntryPage(
            items=[], scanned_through_sequence=query.after_sequence, has_more=False
        )

    monkeypatch.setattr(routes.PostgresConversationQueries, "list_mine", inbox)
    monkeypatch.setattr(routes.PostgresMessageOperations, "read_entries", entries)
    with TestClient(app) as client:
        yield client, captured


@pytest.mark.parametrize("size", [20, 50, 100])
def test_browser_inbox_and_entry_query_strings_parse_to_bounded_integers(
    query_client, size
):
    """Use the actual browser URL shape; JSON/body-model tests miss this boundary."""
    client, captured = query_client
    response = client.get(f"/conversations?view=all&page=1&page_size={size}")
    assert response.status_code == 200
    assert response.json()["page_size"] == size
    assert type(captured[-1].page_size) is int
    response = client.get(
        f"/conversations/{uuid4()}/entries?after_sequence=0&page_size={size}"
    )
    assert response.status_code == 200
    assert captured[-1].after_sequence == 0 and captured[-1].page_size == size


@pytest.mark.parametrize(
    "query",
    [
        "page_size=100.0",
        "page_size=21",
        "page_size=true",
        "page=1.0",
        "page=0",
        "page_size=",
        "offer_min_paise=100.0",
        "offer_min_paise=101",
    ],
)
def test_invalid_inbox_numeric_parameters_are_still_rejected(query_client, query):
    client, captured = query_client
    assert client.get("/conversations?" + query).status_code == 422
    assert captured == []


@pytest.mark.parametrize(
    "query",
    [
        "page_size=100.0",
        "page_size=21",
        "page_size=false",
        "after_sequence=-1",
        "after_sequence=1.0",
    ],
)
def test_invalid_entry_numeric_parameters_are_rejected(query_client, query):
    client, captured = query_client
    assert client.get(f"/conversations/{uuid4()}/entries?" + query).status_code == 422
    assert captured == []


def test_optional_offer_bounds_parse_without_relaxing_money_rules(query_client):
    client, captured = query_client
    assert (
        client.get(
            "/conversations?offer_min_paise=100&offer_max_paise=200&page_size=50"
        ).status_code
        == 200
    )
    assert captured[-1].offer_min_paise == 100
    assert captured[-1].offer_max_paise == 200


def test_message_routes_require_server_authenticated_identity_context():
    """A client-supplied ID cannot create membership or replace Identity context."""
    app = create_app(Settings(environment="test"))
    conversation_id = uuid4()

    with TestClient(app) as client:
        for path in (
            f"/conversations/{conversation_id}/entries",
            f"/conversations/{conversation_id}/read-state",
        ):
            response = client.get(path)
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "unauthenticated"


def test_authenticated_request_without_a_database_fails_closed():
    """The public router never reports success when its required store is absent."""
    app = create_app(Settings(environment="test"))
    caller = CallerContext(
        user_id=uuid4(),
        account_class="regular",
        valid_until=datetime.now(UTC) + timedelta(hours=1),
    )
    app.dependency_overrides[require_caller] = lambda: caller

    with TestClient(app) as client:
        response = client.get(f"/conversations/{uuid4()}/read-state")

    assert response.status_code == ERRORS[503].status
    assert response.json()["error"]["code"] == "dependency_unavailable"
