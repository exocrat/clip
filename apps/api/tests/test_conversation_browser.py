"""Test-only harness guards: no live provider, existing target or actual browser."""

from uuid import uuid4
import asyncio

from fastapi.testclient import TestClient
import pytest

from scripts.conversation_browser import browser_app, validate_environment


@pytest.fixture
def applications(tmp_path, monkeypatch):
    """Only stub HTML and idle pools; these tests never connect to a database."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    for name in (
        "CLIP_DATABASE_URL",
        "CLIP_DATABASE_DSN",
        "DATABASE_URL",
        "CLIP_IDENTITY_PROVIDER",
        "CLIP_EMAIL_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(
        "<html><body><div id='root'></div></body></html>"
    )
    actor, listing, conversation = uuid4(), uuid4(), uuid4()

    def no_database_connection():
        """Guard-only tests must never invoke the harness's real SQL providers."""
        raise AssertionError("Guard test unexpectedly accessed the database")

    # No route used here acquires a connection from these lazy zero-minimum pools.
    return actor, [
        browser_app(
            "postgresql://localhost/unused",
            no_database_connection,
            actor,
            listing,
            conversation,
            port,
            dist=tmp_path,
        )
        for port in (5273, 5274)
    ]


def client(app, port=5273, *, peer="127.0.0.1"):
    """Set actual test transport peer/host; forwarded headers grant nothing."""
    return TestClient(app, base_url=f"http://127.0.0.1:{port}", client=(peer, 41000))


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"CLIP_ENVIRONMENT": "production"},
        {"CLIP_ENVIRONMENT": "local"},
        {"CLIP_ENVIRONMENT": "test", "CLIP_DATABASE_URL": "synthetic"},
        {"CLIP_ENVIRONMENT": "test", "CLIP_DATABASE_DSN": "synthetic"},
        {"CLIP_ENVIRONMENT": "test", "CLIP_EMAIL_PROVIDER": "ses"},
    ],
)
def test_refuses_implicit_or_external_environment(environment):
    with pytest.raises(ValueError):
        validate_environment(environment)


def test_actor_is_fixed_and_no_identity_selector_or_auth_bypass_exists(applications):
    actor, apps = applications
    with client(apps[0]) as browser:
        response = browser.get(
            "/api/me",
            headers={"X-User-ID": str(uuid4()), "X-Account-Class": "temporary"},
        )
        assert response.json()["user_id"] == str(actor)
        assert response.json()["account_class"] == "regular"
        assert response.headers["Cache-Control"] == "no-store"
        assert browser.get("/api/test-login").status_code == 404
        assert "LOCAL E2EE TEST" in browser.get("/my/conversations").text


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://foreign.invalid"},
        {"Host": "foreign.invalid:5273"},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
def test_foreign_request_is_denied_before_session_or_key_access(applications, headers):
    _, apps = applications
    with client(apps[0]) as browser:
        response = browser.get("/api/auth/csrf", headers=headers)
        assert response.status_code == 403
        assert "csrf_token" not in response.text


def test_forwarded_loopback_cannot_replace_real_peer(applications):
    _, apps = applications
    with client(apps[0], peer="192.0.2.27") as browser:
        assert (
            browser.get("/api/me", headers={"X-Forwarded-For": "127.0.0.1"}).status_code
            == 403
        )


def test_writes_require_origin_marker_and_this_sides_token_and_logout_ends_actor(
    applications,
):
    _, apps = applications
    with client(apps[0]) as first, client(apps[1], 5274) as second:
        own = first.get("/api/auth/csrf").json()["csrf_token"]
        other = second.get("/api/auth/csrf").json()["csrf_token"]
        valid = {
            "Origin": "http://127.0.0.1:5273",
            "X-CLIP-Request": "1",
            "X-CSRF-Token": own,
        }
        for missing in valid:
            assert (
                first.delete(
                    "/api/auth/session",
                    headers={k: v for k, v in valid.items() if k != missing},
                ).status_code
                == 403
            )
        assert (
            first.delete(
                "/api/auth/session", headers=valid | {"X-CSRF-Token": other}
            ).status_code
            == 403
        )
        assert first.delete("/api/auth/session", headers=valid).status_code == 204
        assert first.get("/api/me").status_code == 401
        assert first.get("/api/auth/csrf").status_code == 401
        assert second.get("/api/me").status_code == 200


def test_normal_application_does_not_install_harness_routes():
    from app.application import create_app
    from app.core.config import Settings

    with TestClient(create_app(Settings(environment="test"))) as browser:
        assert browser.get("/api/me").status_code == 404
        assert browser.get("/api/test-login").status_code == 404
        assert "LOCAL E2EE TEST" not in browser.get("/").text


@pytest.mark.parametrize("failure", [False, True])
def test_bounded_server_group_stops_both_on_timeout_or_startup_failure(
    monkeypatch, failure
):
    """Lifecycle probe only; no sockets, background listener or Docker is opened."""
    from scripts import conversation_browser as harness

    servers = []

    class Server:
        def __init__(self, config):
            self.started = False
            self.should_exit = False
            self.finished = False
            servers.append(self)

        async def serve(self, *, sockets):
            try:
                if failure and self is servers[0]:
                    return
                self.started = True
                while not self.should_exit:
                    await asyncio.sleep(0.001)
            finally:
                self.finished = True

    monkeypatch.setattr(harness.uvicorn, "Config", lambda *args, **kwargs: None)
    monkeypatch.setattr(harness.uvicorn, "Server", Server)
    if failure:
        with pytest.raises(RuntimeError, match="failed to start"):
            asyncio.run(harness.serve_apps([None, None], [None, None], 0))
    else:
        asyncio.run(harness.serve_apps([None, None], [None, None], 0))
    assert len(servers) == 2
    assert all(server.should_exit and server.finished for server in servers)
