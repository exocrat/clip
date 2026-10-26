"""Synthetic CSRF responses stay within explicitly approved isolated profiles."""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.application import create_app
from app.core.config import Settings
from apps.api.tests.domains.listings.browser_demo import create_demo_app
from apps.api.tests.domains.search.wanted_ui_preview import create_app as wanted_preview


def isolated_settings(**overrides):
    """Exact existing demo target contract; no connection/storage client is opened."""
    values = dict(
        environment="test",
        development_auth=True,
        database_url="postgresql://synthetic:synthetic@synthetic.invalid/clip_test_listings",
        storage_provider="s3",
        image_bucket="clip-test-listings-images-ap-south-1-li02",
        image_region="ap-south-1",
        image_key_prefix="listings/test/csrf-fixture",
        isolated_listings_test_caller=True,
        isolated_listings_max_count=10,
    )
    values.update(overrides)
    return Settings(**values)


@pytest.mark.parametrize("environment", ["local", "test", "production"])
def test_unconfigured_runtime_has_no_synthetic_csrf_endpoint(environment):
    client = TestClient(create_app(Settings(environment=environment)))
    response = client.get("/auth/csrf")
    assert response.status_code == 404
    assert "csrf_token" not in response.text
    assert client.get("/me").status_code == 404
    client.close()


def test_existing_isolated_profile_only_exposes_the_contract_double():
    client = TestClient(create_app(isolated_settings()))
    response = client.get("/auth/csrf")
    assert response.status_code == 200
    assert set(response.json()) == {"csrf_token"}
    assert 32 <= len(response.json()["csrf_token"]) <= 128
    assert response.headers["cache-control"] == "no-store"
    session = client.get(
        "/me", headers={"X-Account-Class": "temporary", "X-User-ID": "untrusted"}
    )
    assert session.status_code == 200
    assert session.json()["account_class"] == "regular"
    assert session.json()["user_id"] == "10000000-0000-4000-8000-000000000001"
    assert session.headers["cache-control"] == "no-store"
    client.close()
    with pytest.raises(ValidationError):
        isolated_settings(environment="production")


def test_hosted_demo_csrf_is_registered_before_the_spa_fallback(monkeypatch, tmp_path):
    from app import application

    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("Synthetic test UI")
    monkeypatch.setattr(application, "Path", lambda _: tmp_path)
    client = TestClient(create_app(isolated_settings(serve_web_app=True)))
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200 and "csrf_token" in response.json()
    assert response.headers["cache-control"] == "no-store"
    session = client.get("/api/me")
    assert session.status_code == 200 and session.json()["account_class"] == "regular"
    assert session.headers["cache-control"] == "no-store"
    client.close()


@pytest.mark.parametrize("factory", ["listings", "wanted"])
def test_local_browser_harnesses_support_preflight_and_keep_origin_gates(factory):
    app = (
        create_demo_app(
            "unused-synthetic-dsn", Settings(environment="test", development_auth=True)
        )
        if factory == "listings"
        else wanted_preview(SimpleNamespace())
    )
    client = TestClient(
        app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)
    )
    response = client.get("/auth/csrf")
    assert response.status_code == 200 and len(response.json()["csrf_token"]) >= 32
    denied = client.get("/auth/csrf", headers={"Origin": "https://foreign.invalid"})
    assert denied.status_code == 403 and "csrf_token" not in denied.text
    client.close()
