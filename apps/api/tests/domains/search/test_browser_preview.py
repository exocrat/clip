"""Test only the labelled UI fixture transport, not search/provider functionality."""

from fastapi.testclient import TestClient
import pytest

from app.contracts.domain_types import CatalogueView, ListingSummary, PageResult
from apps.api.tests.domains.search.browser_preview import (
    create_preview_app,
    require_preview_settings,
)

HEADERS = {"X-Clip-UI-Preview": "search-fixtures", "Origin": "http://127.0.0.1:5173"}


def test_preview_requires_explicit_test_settings(monkeypatch):
    """No default/production/database-backed startup may activate this fixture app."""
    with pytest.raises(ValueError):
        require_preview_settings(True)
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    monkeypatch.setenv("CLIP_DEVELOPMENT_AUTH", "true")
    require_preview_settings(True)
    with pytest.raises(ValueError):
        require_preview_settings(False)
    monkeypatch.setenv("CLIP_DATABASE_URL", "synthetic-not-a-real-target")
    with pytest.raises(ValueError):
        require_preview_settings(True)


def test_normal_and_cross_origin_clients_cannot_consume_fixture_success():
    """The production client sends no preview header and therefore fails closed."""
    with TestClient(create_preview_app()) as client:
        assert client.get("/listings").status_code == 403
        assert (
            client.get(
                "/listings", headers={**HEADERS, "Origin": "https://example.invalid"}
            ).status_code
            == 403
        )


def test_fixture_catalogue_and_pages_follow_generated_transport_shapes():
    """The UI can inspect page/empty/loading shapes; no SQL claims follow."""
    with TestClient(create_preview_app()) as client:
        catalogue = client.get("/catalogue", headers=HEADERS)
        options = CatalogueView.model_validate(catalogue.json())
        assert len(options.categories) == 9 and len(options.conditions) == 4
        for number, count, has_next in ((1, 20, True), (2, 20, True), (3, 2, False)):
            response = client.get("/listings", params={"page": number}, headers=HEADERS)
            page = PageResult[ListingSummary].model_validate(response.json())
            assert len(page.items) == count and page.has_next is has_next
            assert response.headers["cache-control"] == "private, no-store"
        assert client.get("/listings?q=empty", headers=HEADERS).json()["items"] == []


@pytest.mark.parametrize(
    "scenario,status", [("expired", 401), ("denied", 403), ("unavailable", 503)]
)
def test_named_error_scripts_are_errors_not_simulated_auth_success(scenario, status):
    """These are deterministic display fixtures, never actual authentication evidence."""
    with TestClient(create_preview_app()) as client:
        response = client.get("/listings", params={"q": scenario}, headers=HEADERS)
    assert response.status_code == status and "error" in response.json()


def test_retry_script_fails_once_then_exposes_a_fresh_page():
    """Explicit human retry can be inspected without hiding the first failure."""
    with TestClient(create_preview_app()) as client:
        assert client.get("/listings?q=retry", headers=HEADERS).status_code == 503
        assert client.get("/listings?q=retry", headers=HEADERS).status_code == 200


@pytest.mark.parametrize("mode", ["keyword", "hybrid"])
def test_fixture_modes_and_relevance_only_prove_transport(mode):
    """Support the registered UI inputs without pretending to implement ranking."""
    with TestClient(create_preview_app()) as client:
        assert (
            client.get(
                "/listings", params={"search_mode": mode}, headers=HEADERS
            ).status_code
            == 200
        )
        assert (
            client.get(
                "/listings",
                params={"search_mode": mode, "q": "bicycle", "sort": "relevance"},
                headers=HEADERS,
            ).status_code
            == 200
        )
        assert (
            client.get(
                "/listings",
                params={"search_mode": mode, "sort": "relevance"},
                headers=HEADERS,
            ).status_code
            == 422
        )


def test_scripted_hybrid_failure_has_explicit_keyword_recovery():
    """A named outage is mode-specific, permitting a real UI recovery action."""
    with TestClient(create_preview_app()) as client:
        for mode, status in [("hybrid", 503), ("keyword", 200)]:
            response = client.get(
                "/listings",
                params={"q": "hybrid-down", "search_mode": mode, "sort": "relevance"},
                headers=HEADERS,
            )
            assert response.status_code == status
            assert response.headers["cache-control"] == "private, no-store"
        assert (
            client.get("/listings?search_mode=semantic", headers=HEADERS).status_code
            == 422
        )
