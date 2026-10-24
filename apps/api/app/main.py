"""Default ASGI entry point; reusable composition lives in app.application."""

from app.application import create_app
from app.core.config import load_settings
from app.core.logging import configure_logging

# Retain the established settings/app exports; validate before serving requests.
settings = load_settings()
configure_logging()
app = create_app(settings)
