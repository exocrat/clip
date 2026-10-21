"""The browser harness must stay isolated from deployed auth and database targets."""

import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from apps.api.tests.domains.listings.browser_demo import create_demo_app


@pytest.mark.parametrize(
    "settings",
    [
        Settings(environment="production"),
        Settings(environment="local", development_auth=True),
        Settings(environment="test"),
        Settings(
            environment="test",
            development_auth=True,
            database_url="postgresql://unused/other",
        ),
    ],
)
def test_browser_app_refuses_unsafe_activation(settings):
    """A test app cannot opt into production, default auth or an ambient database."""
    with pytest.raises(RuntimeError):
        create_demo_app("unused", settings)


@pytest.mark.parametrize(
    ("peer", "host", "origin"),
    [
        ("192.0.2.10", "127.0.0.1:8000", "http://127.0.0.1:5173"),
        ("127.0.0.1", "untrusted.invalid", "http://127.0.0.1:5173"),
        ("127.0.0.1", "127.0.0.1:8000", "https://untrusted.invalid"),
        ("127.0.0.1", "127.0.0.1:8000", None),
    ],
)
def test_browser_app_denies_nonlocal_or_cross_origin_writes(peer, host, origin):
    """Reject before touching a database, including write requests without Origin."""
    app = create_demo_app("unused", Settings(environment="test", development_auth=True))
    headers = {"host": host}
    if origin:
        headers["origin"] = origin
    client = TestClient(app, client=(peer, 12345))
    response = client.post("/__listings_demo/image", headers=headers)
    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "forbidden", "message": "Action not permitted"}
    }


def test_normal_api_never_mounts_browser_test_routes():
    """The production entry point does not expose fixture creation or fake auth."""
    # Import in a fresh process: importing app.main here would freeze its global
    # settings before the health test establishes its own environment.
    api_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.main import app; from fastapi.testclient import TestClient; "
            "assert not any(getattr(r, 'path', '').startswith('/__listings_demo') for r in app.routes); "
            "assert TestClient(app).get('/catalogue').status_code == 401",
        ],
        env={
            "PATH": os.environ["PATH"],
            "PYTHONPATH": str(api_root),
            "CLIP_ENVIRONMENT": "production",
        },
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0
