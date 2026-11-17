"""Verify per-client throttling without trusting browser-provided identity."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest

from app.core.auth import CallerContext
from app.core.config import Settings
from app.core.rate_limit import ApiRateLimitMiddleware


def client_for(*, read_limit=100, write_limit=10):
    """Install a controlled trusted caller boundary ahead of the real limiter."""
    app = FastAPI()
    users = {
        name: CallerContext(uuid4(), "regular", datetime.now(UTC) + timedelta(days=1))
        for name in ("one", "two")
    }

    @app.api_route("/resource", methods=["GET", "POST"])
    @app.get("/health")
    def resource(request: Request):
        return {"ok": True}

    app.add_middleware(
        ApiRateLimitMiddleware,
        read_limit=read_limit,
        write_limit=write_limit,
        api_prefix_only=False,
    )

    @app.middleware("http")
    async def trusted_identity(request, call_next):
        # This test-owned boundary stands in for Identity's verified session.
        if request.headers.get("x-test-identity") in users:
            request.scope["clip.caller"] = users[request.headers["x-test-identity"]]
        return await call_next(request)

    return TestClient(app, client=("192.0.2.1", 1234))


def test_default_limits_and_separate_authenticated_users():
    settings = Settings(environment="test")
    assert (
        settings.api_read_requests_per_minute,
        settings.api_write_requests_per_minute,
    ) == (3600, 200)
    with client_for() as client:
        one = {"x-test-identity": "one"}
        two = {"x-test-identity": "two"}
        for _ in range(10):
            assert client.post("/resource", headers=one).status_code == 200
        limited = client.post("/resource", headers=one)
        assert limited.status_code == 429
        assert int(limited.headers["retry-after"]) > 0
        assert client.post("/resource", headers=two).status_code == 200
        for _ in range(100):
            assert client.get("/resource", headers=one).status_code == 200
        assert client.get("/resource", headers=one).status_code == 429
        assert client.get("/resource", headers=two).status_code == 200
        assert client.get("/health", headers=one).status_code == 200


def test_anonymous_peer_cannot_choose_key_with_forwarded_headers():
    with client_for(write_limit=1) as client:
        assert (
            client.post(
                "/resource", headers={"x-forwarded-for": "192.0.2.2"}
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/resource", headers={"x-forwarded-for": "192.0.2.3"}
            ).status_code
            == 429
        )


def test_expired_windows_are_reclaimed(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("app.core.rate_limit.monotonic", lambda: clock[0])
    with client_for(write_limit=1) as client:
        assert client.post("/resource").status_code == 200
        assert client.post("/resource").status_code == 429
        clock[0] += 60
        assert client.post("/resource").status_code == 200


def test_active_client_capacity_fails_closed_and_recovers(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("app.core.rate_limit.monotonic", lambda: clock[0])
    monkeypatch.setattr("app.core.rate_limit.MAX_ACTIVE_CLIENTS", 1)
    with client_for() as client:
        assert (
            client.get("/resource", headers={"x-test-identity": "one"}).status_code
            == 200
        )
        assert (
            client.get("/resource", headers={"x-test-identity": "two"}).status_code
            == 429
        )
        clock[0] += 60
        assert (
            client.get("/resource", headers={"x-test-identity": "two"}).status_code
            == 200
        )


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_anonymous_and_authenticated_budgets_do_not_share_peer_allowance(method):
    """One peer's anonymous traffic and two accounts each retain their own cap."""
    with client_for(read_limit=1, write_limit=1) as client:
        assert client.request(method, "/resource").status_code == 200
        assert client.request(method, "/resource").status_code == 429
        for user in ("one", "two"):
            headers = {"x-test-identity": user}
            assert (
                client.request(method, "/resource", headers=headers).status_code == 200
            )
            assert (
                client.request(method, "/resource", headers=headers).status_code == 429
            )
