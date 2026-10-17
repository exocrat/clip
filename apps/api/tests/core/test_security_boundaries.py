"""Adversarial caller provenance and actual production-startup guards.

All claims and contexts are synthetic. Test-only middleware establishes positive
controls; no credential verifier, provider, domain route, or public bypass exists.
"""

from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess
import sys
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.testclient import TestClient
import pytest

from app.core.auth import CallerContext, require_caller
from app.core.config import load_settings

SERVER_ID = UUID("123e4567-e89b-42d3-a456-426614174000")
CLIENT_ID = "123e4567-e89b-42d3-a456-426614174001"
FUTURE = datetime(2100, 1, 1, tzinfo=UTC)
PAST = datetime(2000, 1, 1, tzinfo=UTC)
CLAIMS = {
    "user_id": CLIENT_ID,
    "account_class": "regular",
    "eligible": True,
    "owner": True,
    "valid_until": "2100-01-01T00:00:00.000000Z",
}

# Each input surface is exercised independently so an ignored body cannot mask a
# header bypass. The combined case also tries internal-looking scope/state names.
ATTACKS = [
    ("empty", {}),
    (
        "headers",
        {
            "headers": {
                "X-User-ID": CLIENT_ID,
                "X-Account-Class": "regular",
                "X-Eligible": "true",
                "X-Owner": "true",
                "X-Development-Auth": "true",
                "Authorization": "Bearer synthetic-invalid-credential",
            }
        },
    ),
    ("query", {"params": CLAIMS}),
    ("body", {"json": CLAIMS}),
    (
        "cookies",
        {
            "headers": {
                "Cookie": "user_id="
                + CLIENT_ID
                + "; account_class=regular; eligible=true; owner=true"
            }
        },
    ),
    (
        "combined",
        {
            "params": CLAIMS,
            "json": {
                **CLAIMS,
                "clip.caller": CLAIMS,
                "scope": {"clip.caller": CLAIMS},
                "state": {"caller": CLAIMS},
            },
            "headers": {
                "X-User-ID": CLIENT_ID,
                "X-Account-Class": "regular",
                "Authorization": "Bearer synthetic-invalid-credential",
                "Cookie": "user_id=" + CLIENT_ID,
            },
        },
    ),
]


def add_protected_route(app):
    """Bind the real caller dependency to a route owned solely by this test."""

    @app.post("/protected")
    async def protected(caller: Annotated[CallerContext, Depends(require_caller)]):
        """Return only synthetic verified facts to distinguish server/client data."""
        return {"user_id": str(caller.user_id), "account_class": caller.account_class}


class ServerCallerMiddleware:
    """Test-only server wiring; deliberately reads no HTTP claims or credentials."""

    def __init__(self, app, caller):
        """Bind a fixed synthetic context supplied by test setup, never a client."""
        self.app = app
        self.caller = caller

    async def __call__(self, scope, receive, send):
        """Populate the internal slot only for requests in this private test app."""
        if scope["type"] == "http":
            scope["clip.caller"] = self.caller
        await self.app(scope, receive, send)


@pytest.mark.parametrize(
    ("case", "request_options"), ATTACKS, ids=[case for case, _ in ATTACKS]
)
def test_client_claims_cannot_create_trusted_caller(core_app, case, request_options):
    """Forged IDs/classes/eligibility/ownership cannot authenticate any input path."""
    add_protected_route(core_app)
    with TestClient(core_app) as client:
        response = client.post("/protected", **request_options)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "user_id" not in response.json()
    assert CLIENT_ID not in response.text


@pytest.mark.parametrize(
    ("case", "request_options"), ATTACKS, ids=[case for case, _ in ATTACKS]
)
def test_client_claims_cannot_replace_server_context(core_app, case, request_options):
    """Positive controls rule out a broken route and prove client claims lose."""
    caller = CallerContext(SERVER_ID, "temporary", FUTURE)
    add_protected_route(core_app)
    core_app.add_middleware(ServerCallerMiddleware, caller=caller)
    with TestClient(core_app) as client:
        response = client.post("/protected", **request_options)
    assert response.status_code == 200
    assert response.json() == {"user_id": str(SERVER_ID), "account_class": "temporary"}


def test_client_future_deadline_cannot_revive_expired_context(core_app):
    """A future validity claim cannot extend the server-established deadline."""
    add_protected_route(core_app)
    core_app.add_middleware(
        ServerCallerMiddleware, caller=CallerContext(SERVER_ID, "regular", PAST)
    )
    with TestClient(core_app) as client:
        response = client.post("/protected", params=CLAIMS, json=CLAIMS)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_reserved_test_settings_do_not_create_a_public_auth_bypass(
    core_app, monkeypatch
):
    """Explicit local fake flags reserve fixtures; they never authenticate headers."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    monkeypatch.setenv("CLIP_IDENTITY_PROVIDER", "fake")
    monkeypatch.setenv("CLIP_EMAIL_PROVIDER", "fake")
    monkeypatch.setenv("CLIP_DEVELOPMENT_AUTH", "true")
    settings = load_settings()
    assert settings.identity_provider == "fake" and settings.development_auth is True
    add_protected_route(core_app)
    with TestClient(core_app) as client:
        response = client.post(
            "/protected", headers={"X-User-ID": CLIENT_ID}, json=CLAIMS
        )
    assert response.status_code == 401


def run_startup(overrides):
    """Import the real entry point in a fresh bounded, credential-free child.

    This reaches the same configuration boundary as Uvicorn without opening a
    listener. No developer CLIP/AWS settings or provider secrets are inherited.
    """
    api_root = Path(__file__).resolve().parents[2]
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.main import app, settings; print('startup-ready')",
        ],
        cwd=api_root,
        env={
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(api_root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            **overrides,
        },
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.mark.parametrize(
    ("overrides", "expected_setting"),
    [
        ({"CLIP_IDENTITY_PROVIDER": "fake"}, "CLIP_IDENTITY_PROVIDER"),
        ({"CLIP_EMAIL_PROVIDER": "fake"}, "CLIP_EMAIL_PROVIDER"),
        ({"CLIP_DEVELOPMENT_AUTH": "true"}, "CLIP_DEVELOPMENT_AUTH"),
        ({"CLIP_DEBUG": "true"}, "CLIP_DEBUG"),
        (
            {
                "CLIP_IDENTITY_PROVIDER": "fake",
                "CLIP_EMAIL_PROVIDER": "fake",
                "CLIP_DEVELOPMENT_AUTH": "true",
            },
            "CLIP_IDENTITY_PROVIDER",
        ),
        (
            {"CLIP_IDENTITY_PROVIDER": "synthetic-unsupported-provider"},
            "CLIP_IDENTITY_PROVIDER",
        ),
    ],
    ids=[
        "fake-identity",
        "fake-email",
        "development-auth",
        "debug",
        "combined",
        "unsupported-provider",
    ],
)
def test_real_production_startup_rejects_unsafe_provider_controls(
    overrides, expected_setting
):
    """Unsafe production configuration aborts import instead of selecting a fake."""
    result = run_startup({"CLIP_ENVIRONMENT": "production", **overrides})
    assert result.returncode != 0
    assert "startup-ready" not in result.stdout
    assert "ConfigurationError: Invalid API configuration" in result.stderr
    assert expected_setting in result.stderr
    assert "synthetic-unsupported-provider" not in result.stderr
    assert "input_value" not in result.stderr


@pytest.mark.parametrize(
    "overrides",
    [
        {"CLIP_ENVIRONMENT": "production"},
        {
            "CLIP_ENVIRONMENT": "production",
            "CLIP_IDENTITY_PROVIDER": "disabled",
            "CLIP_EMAIL_PROVIDER": "disabled",
            "CLIP_DEVELOPMENT_AUTH": "false",
            "CLIP_DEBUG": "false",
        },
        {
            "CLIP_ENVIRONMENT": "local",
            "CLIP_IDENTITY_PROVIDER": "fake",
            "CLIP_EMAIL_PROVIDER": "fake",
            "CLIP_DEVELOPMENT_AUTH": "true",
        },
        {
            "CLIP_ENVIRONMENT": "test",
            "CLIP_IDENTITY_PROVIDER": "fake",
            "CLIP_EMAIL_PROVIDER": "fake",
            "CLIP_DEVELOPMENT_AUTH": "true",
        },
    ],
    ids=[
        "production-defaults",
        "production-explicit-safe",
        "local-explicit-test-controls",
        "test-explicit-test-controls",
    ],
)
def test_real_startup_accepts_safe_configuration_positive_controls(overrides):
    """Allowed imports prove rejection tests are not merely failing dependencies.

    Local/test acceptance proves only configuration selection, never a working
    identity/email adapter. Production defaults provide liveness only.
    """
    result = run_startup(overrides)
    assert result.returncode == 0
    assert result.stdout.strip() == "startup-ready"
    assert "ConfigurationError" not in result.stderr
