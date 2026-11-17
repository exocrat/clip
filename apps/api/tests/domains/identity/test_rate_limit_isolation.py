"""Real session/SQL checks for account isolation behind one transport address.

Only the upstream signer and mail transport use the existing synthetic fixtures.
All requests use the normal application factory, cookies and Identity middleware;
the database is owned and removed by the reviewed disposable fixture.
"""

from collections import Counter
from datetime import timedelta

from fastapi.testclient import TestClient
import pytest

from app.application import create_app
from app.domains.identity.http import IdentityReadDependencies
from apps.api.tests.domains.identity.session_fixtures import HEADERS, ORIGIN
from apps.api.tests.domains.identity.test_application_composition import compose
from apps.api.tests.test_conversation_identity_integration import (
    signed_actor,
    use_actor,
)


@pytest.fixture
def limited_client(identity_runtime, signed_tokens):
    """Issue real sessions before exercising fresh, deliberately small budgets."""
    setup, settings, bindings = compose(identity_runtime, signed_tokens)
    with TestClient(setup, base_url=ORIGIN, client=("192.0.2.27", 41000)) as client:
        first = signed_actor(client, signed_tokens, "rate-first")
        second = signed_actor(client, signed_tokens, "rate-second")
    application = create_app(
        settings.model_copy(
            update={
                "api_read_requests_per_minute": 2,
                "api_write_requests_per_minute": 2,
            }
        ),
        identity=bindings,
    )
    with TestClient(
        application, base_url=ORIGIN, client=("192.0.2.27", 41000)
    ) as client:
        yield client, first, second


def test_anonymous_exhaustion_does_not_block_signed_in_accounts(limited_client):
    """Replay the reported shared-address case beyond the old peer ceiling."""
    client, first, second = limited_client
    use_actor(client, first)
    assert client.get("/me").status_code == 200
    client.cookies.clear()
    statuses = Counter(client.get("/me").status_code for _ in range(601))
    assert statuses == {401: 2, 429: 599}
    use_actor(client, first)
    assert client.get("/me").status_code == 200
    assert client.get("/me").status_code == 429
    use_actor(client, second)
    assert client.get("/me").status_code == 200


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("credential", ["missing", "forged", "revoked", "expired"])
def test_rejected_credentials_still_use_anonymous_budget(
    limited_client, identity_runtime, method, credential
):
    """Missing/invalid cookies cannot skip the quota on early Identity rejections."""
    client, first, second = limited_client
    if credential == "revoked":
        headers = use_actor(client, first)
        assert client.delete("/auth/session", headers=headers).status_code == 204
        use_actor(client, first)  # Replay the revoked cookie, not a caller override.
    elif credential == "expired":
        with identity_runtime.connect() as connection:
            connection.execute(
                "UPDATE identity.sessions SET expires_at=created_at+INTERVAL '1 second' "
                "WHERE user_id=%s",
                (first[0]["user_id"],),
            )
        identity_runtime.clock[0] += timedelta(seconds=2)
        use_actor(client, first)
    else:
        client.cookies.clear()
        if credential == "forged":
            client.cookies.set(
                identity_runtime.policy.session_cookie, "invalid-session"
            )
    statuses = []
    for index in range(3):
        headers = HEADERS | {
            "X-Forwarded-For": f"198.51.100.{index + 1}",
            "X-CLIP-User-ID": second[0]["user_id"],
        }
        response = (
            client.get("/me", headers=headers)
            if method == "GET"
            else client.post("/auth/csrf", headers=headers)
        )
        statuses.append(response.status_code)
    assert all(status in {401, 403, 405} for status in statuses[:2])
    assert statuses[2] == 429
    headers = use_actor(client, second)
    assert client.get("/me", headers=headers).status_code == 200


def test_authenticated_write_budget_is_still_per_account(limited_client):
    """Authenticated users remain limited independently for writes and reads."""
    client, first, second = limited_client
    headers = use_actor(client, first)
    responses = [
        client.patch(
            "/me/profile", headers=headers, json={"display_name": "rate_first"}
        ).status_code
        for _ in range(3)
    ]
    assert responses == [200, 200, 429]
    assert client.get("/me").status_code == 200
    headers = use_actor(client, second)
    assert (
        client.patch(
            "/me/profile", headers=headers, json={"display_name": "rate_second"}
        ).status_code
        == 200
    )


def test_read_only_profile_keeps_anonymous_and_account_budgets_separate(
    identity_runtime, signed_tokens
):
    """The session-only Lambda composition must install the same trusted gate."""
    setup, settings, bindings = compose(identity_runtime, signed_tokens)
    with TestClient(setup, base_url=ORIGIN, client=("192.0.2.27", 41000)) as client:
        actor = signed_actor(client, signed_tokens, "rate-read-only")
    application = create_app(
        settings.model_copy(
            update={
                "api_read_requests_per_minute": 2,
                "api_write_requests_per_minute": 2,
                "identity_runtime_enabled": True,
                "identity_browser_origins": bindings.policy.origins,
            }
        ),
        identity_reads=IdentityReadDependencies(bindings.sessions, bindings.policy),
        listings_read_only=True,
    )
    with TestClient(
        application, base_url=ORIGIN, client=("192.0.2.27", 41000)
    ) as client:
        for _ in range(3):
            anonymous = client.get("/api/listings", params={"search_mode": "keyword"})
        assert anonymous.status_code == 429
        use_actor(client, actor)
        assert (
            client.get("/api/listings", params={"search_mode": "keyword"}).status_code
            == 200
        )


def test_hostile_origin_is_limited_without_authentication_lookup(
    limited_client, identity_runtime, monkeypatch
):
    """Rejected browser origins spend no account allowance or session-lookup work."""
    client, first, _ = limited_client
    use_actor(client, first)

    def forbidden_lookup(_token):
        raise AssertionError("Hostile origin must be rejected before session lookup")

    with monkeypatch.context() as patch:
        patch.setattr(identity_runtime.service, "authenticate", forbidden_lookup)
        statuses = [
            client.get(
                "/me", headers={"Origin": "https://untrusted.example"}
            ).status_code
            for _ in range(3)
        ]
    assert statuses == [403, 403, 429]
    assert client.get("/me").status_code == 200
