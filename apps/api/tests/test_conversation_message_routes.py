"""Fail-closed routing checks for the mounted public Conversations router."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.auth import CallerContext, require_caller
from app.core.config import Settings
from app.core.errors import ERRORS
from app.main import create_app


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
