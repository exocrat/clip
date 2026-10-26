"""Exercise the real ASGI health route without network or cloud dependencies."""

from fastapi.testclient import TestClient

from app.application import create_app
from app.core.config import Settings


def test_health_in_test_mode_exposes_only_process_status():
    """Compose a test-mode app and verify the safe HTTP health response."""
    app = create_app(Settings(environment="test"))
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}
    assert app.debug is False
