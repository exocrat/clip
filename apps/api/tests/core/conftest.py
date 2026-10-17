"""Synthetic shared-core fixtures with isolated application/server logging."""

from io import StringIO
import logging

from fastapi import FastAPI
import pytest

from app.core.errors import install_error_handlers
from app.core.logging import RequestLoggingMiddleware, configure_logging


@pytest.fixture(autouse=True)
def restore_loggers():
    """Restore logger settings so captured streams/configuration never escape."""
    loggers = [
        logging.getLogger(name)
        for name in ("clip", "uvicorn", "uvicorn.error", "uvicorn.access")
    ]
    snapshots = [
        (log.handlers[:], log.level, log.propagate, log.disabled) for log in loggers
    ]
    try:
        yield
    finally:
        for log, (handlers, level, propagate, disabled) in zip(loggers, snapshots):
            log.handlers = handlers
            log.setLevel(level)
            log.propagate = propagate
            log.disabled = disabled


@pytest.fixture
def log_stream(monkeypatch):
    """Capture only synthetic JSON diagnostics; never print fixture payloads."""
    stream = StringIO()
    monkeypatch.setattr("sys.stderr", stream)
    configure_logging()
    return stream


@pytest.fixture
def core_app():
    """Build a private test app using real wiring and no external services."""
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(RequestLoggingMiddleware)
    return app
