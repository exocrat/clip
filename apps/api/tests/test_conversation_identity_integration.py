"""Real cookie/CSRF/Identity SQL through the shared Conversations application.

Only Microsoft signing/mail are controlled; every database belongs to the
imported disposable fixture. No live credentials, caller override or target.
"""

from fastapi.testclient import TestClient
from apps.api.tests.domains.identity.conftest import (
    disposable_database,
    jwt_clock,
    signed_tokens,
    signing_key,
)
from apps.api.tests.domains.identity.session_fixtures import identity_runtime, HEADERS
from apps.api.tests.domains.identity.test_application_composition import (
    compose,
    regular,
)
from apps.api.tests.test_conversation_directory import public_bundle


def test_real_session_and_csrf_authorize_conversation_key_writes(
    identity_runtime, signed_tokens
):
    """Cookies establish actor identity; CSRF gates writes; logout revokes access."""
    app, _, _ = compose(identity_runtime, signed_tokens)
    with TestClient(
        app, base_url="https://clip-iisc.site", client=("192.0.2.27", 41000)
    ) as client:
        assert client.get("/conversations").status_code == 401
        session = regular(client, signed_tokens)
        assert client.get("/conversations").status_code == 200
        assert client.get("/conversations").json()["items"] == []
        assert client.get("/me/conversation-key").json() is None
        body = public_bundle().model_dump(mode="json")
        assert client.put("/me/conversation-key", json=body).status_code == 403
        csrf = client.get("/auth/csrf").json()["csrf_token"]
        headers = HEADERS | {"X-CSRF-Token": csrf}
        saved = client.put("/me/conversation-key", json=body, headers=headers)
        assert saved.status_code == 200
        assert saved.json()["user_id"] == session["user_id"]
        assert client.get("/me/conversation-key").status_code == 200
        assert client.delete("/auth/session", headers=headers).status_code == 204
        assert client.get("/conversations").status_code == 401
