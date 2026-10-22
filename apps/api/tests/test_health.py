"""Exercise the real ASGI health route without network or cloud dependencies."""

from fastapi.testclient import TestClient


def test_health_in_test_mode_exposes_only_process_status(monkeypatch):
    """Start the app lifespan in test mode and verify its safe HTTP response."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    from app.core.config import load_settings
    from app.main import create_app

    settings = load_settings()
    assert settings.environment == "test"
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}
    assert app.debug is False
