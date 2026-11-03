"""Explicit hosted-test composition checks; no cloud or real credentials."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx2
import pytest

from app.application import create_app
from app.core.config import ConfigurationError, Settings
from app.domains.identity.http import IdentityHttpDependencies
from app.domains.identity.microsoft import MicrosoftTokenValidator
from app.domains.listings.browse import ListingsBrowseService, PublicBrowseIdentity
from app.domains.listings.browse_routes import browse_service
from app.overflow_middleware import OverflowDependencies
from test_lambda_identity import bound_app, hosted_settings  # noqa: F401
from test_overflow_middleware import FakeClient, TARGET, TG


def test_requires_explicit_hosted_identity():
    dependencies = OverflowDependencies(FakeClient("ok"), TARGET, TG)
    with pytest.raises(ConfigurationError, match="Explicit hosted test overflow"):
        create_app(Settings(environment="test"), overflow=dependencies)


def test_refuses_mismatched_run_and_retrying_client():
    with pytest.raises(ValueError, match="Invalid overflow dependencies"):
        OverflowDependencies(FakeClient("ok"), TARGET, TG.replace("test001", "other01"))
    client = FakeClient("ok")
    client.meta.config.retries = {"total_max_attempts": 2}
    with pytest.raises(ValueError, match="Invalid overflow dependencies"):
        OverflowDependencies(client, TARGET, TG)


@pytest.mark.parametrize("outcome", ["ok", "throttle"])
def test_explicit_composition_routes_and_preserves_logging(
    bound_app, tmp_path, monkeypatch, outcome
):
    _, read_bindings, store = bound_app
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("synthetic")
    monkeypatch.setattr("app.application.Path", lambda _: tmp_path)
    full_identity = IdentityHttpDependencies(
        read_bindings.sessions,
        read_bindings.policy,
        SimpleNamespace(send=lambda *args: None),
        MagicMock(spec=MicrosoftTokenValidator),
        lambda: datetime.now(UTC),
    )
    settings = hosted_settings().model_copy(update={"serve_web_app": True})
    client = FakeClient(outcome)
    dependencies = OverflowDependencies(client, TARGET, TG)
    application = create_app(settings, identity=full_identity, overflow=dependencies)

    async def provider():
        return ListingsBrowseService(store, PublicBrowseIdentity())

    application.dependency_overrides[browse_service] = provider

    async def run():
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=application),
            base_url="https://clip-iisc.site",
        ) as http:
            return await http.get(
                "/api/listings",
                headers={"cookie": "__Host-clip_session=synthetic-cookie"},
            )

    response = asyncio.run(run())
    assert response.status_code == 200
    assert response.headers.get("x-request-id")
    assert len(client.calls) == 1
    assert application.state.overflow_counts is dependencies.counts
    if outcome == "throttle":
        read_bindings.sessions.authenticate.assert_called_once_with("synthetic-cookie")
        store.browse_available_listings.assert_awaited_once()
        assert dependencies.counts.snapshot()["capacity_fallbacks"] == 1
    else:
        assert response.json()["backend"] == "lambda"
        assert dependencies.counts.snapshot()["lambda_responses"] == 1
