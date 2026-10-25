"""No native target needed: prove the UI harness rejects unsafe HTTP entry."""

from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from apps.api.tests.domains.search.wanted_ui_preview import create_app


@pytest.mark.parametrize(
    "host,origin,client",
    [
        ("attacker.invalid", None, "127.0.0.1"),
        ("127.0.0.1:8000", "https://attacker.invalid", "127.0.0.1"),
        ("127.0.0.1:8000", "http://localhost:5173", "127.0.0.1"),
        ("127.0.0.1:8000", None, "203.0.113.1"),
    ],
)
def test_preview_rejects_unapproved_transport_before_session_or_sql(
    host, origin, client
):
    """Without startup/cluster methods, rejection must precede fixture access."""
    app = create_app(SimpleNamespace())
    headers = {"host": host}
    if origin:
        headers["origin"] = origin
    response = TestClient(app, client=(client, 12345)).get("/me", headers=headers)
    assert response.status_code == 403
    assert "Synthetic Search author" not in response.text


def test_normal_runtime_never_imports_the_test_harness():
    """A preview file and opt-in CLI never activate synthetic auth in normal startup."""
    from pathlib import Path

    source = Path("apps/api/app/main.py").read_text()
    assert "wanted_ui_preview" not in source
    assert "PreviewDependencies" not in source
