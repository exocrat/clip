"""Offline worker startup, bounded configuration and graceful shutdown checks."""

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from pydantic import SecretStr, ValidationError
import pytest

from app.core.config import Settings
import app.application as application_module
from app.domains.conversations.notifications import runtime


def controlled_settings(**overrides):
    """Build explicit synthetic hosted-test settings without contacting AWS."""
    values = dict(
        environment="test",
        identity_runtime_enabled=True,
        identity_provider="microsoft",
        email_provider="dual",
        database_url=SecretStr("postgresql://synthetic@localhost/clip"),
        database_dsn=SecretStr("postgresql://synthetic@localhost/clip"),
        identity_browser_origins=("https://clip-iisc.site",),
        ses_test_recipients=("synthetic@example.invalid",),
        notification_worker_enabled=True,
    )
    values.update(overrides)
    return Settings(**values)


def test_notification_runtime_defaults_off_and_rejects_unsafe_configs():
    """Default startup is idle; fakes, production and unbounded settings fail."""
    assert Settings().notification_worker_enabled is False
    assert controlled_settings().notification_batch_size == 20
    assert controlled_settings(
        notification_allow_unlisted_recipients=True
    ).notification_allow_unlisted_recipients
    for override in (
        {"environment": "production"},
        {"identity_provider": "fake"},
        {"email_provider": "fake"},
        {"ses_test_recipients": ()},
        {"database_dsn": None},
        {"notification_batch_size": 51},
        {"notification_poll_seconds": 0},
        {
            "notification_worker_enabled": False,
            "notification_allow_unlisted_recipients": True,
        },
    ):
        with pytest.raises(ValidationError):
            controlled_settings(**override)
    with pytest.raises(ValidationError):
        Settings(
            environment="production", ses_test_recipients=("synthetic@example.invalid",)
        )


def test_notification_lifecycle_starts_serial_batch_and_stops(monkeypatch):
    """Inject an offline batch and verify no provider is contacted by composition."""

    async def scenario():
        observed = []
        ran = asyncio.Event()

        async def batch(delivery, recipient, permit, clock, sender, *, max_items):
            observed.append(max_items)
            ran.set()
            return 0

        monkeypatch.setattr(runtime, "run_batch", batch)
        sessions = SimpleNamespace(
            notification_recipient_resolver=lambda permit: object()
        )
        async with runtime.notification_runtime(
            controlled_settings(), object(), SimpleNamespace(sessions=sessions)
        ):
            await asyncio.wait_for(ran.wait(), 2)
        assert observed == [20]

    asyncio.run(scenario())


def test_disabled_runtime_never_constructs_worker(monkeypatch):
    """Without the enable flag, no batch or external provider can start."""

    async def scenario():
        def unexpected(*args, **kwargs):
            raise AssertionError("worker constructed")

        monkeypatch.setattr(runtime, "PostgresNotificationDelivery", unexpected)
        async with runtime.notification_runtime(Settings(), None, None):
            pass

    asyncio.run(scenario())


def test_runtime_passes_explicit_unlisted_recipient_setting(monkeypatch):
    """The operator setting reaches the composed sender without a provider call."""

    async def scenario():
        seen = []
        ran = asyncio.Event()

        def sender(*args, **kwargs):
            seen.append(kwargs["allow_unlisted_recipients"])
            return object()

        async def batch(*args, **kwargs):
            ran.set()
            return 0

        monkeypatch.setattr(runtime, "NotificationEmailSender", sender)
        monkeypatch.setattr(runtime, "run_batch", batch)
        sessions = SimpleNamespace(
            notification_recipient_resolver=lambda permit: object()
        )
        async with runtime.notification_runtime(
            controlled_settings(notification_allow_unlisted_recipients=True),
            object(),
            SimpleNamespace(sessions=sessions),
        ):
            await asyncio.wait_for(ran.wait(), 2)
        assert seen == [True]

    asyncio.run(scenario())


def test_api_lifespan_owns_notification_lifecycle(monkeypatch):
    """Application composition enters and exits the notification lifecycle."""

    async def scenario():
        events = []
        marker = object()

        @asynccontextmanager
        async def fake_runtime(settings, pool, identity):
            assert identity is marker and pool is None
            events.append("start")
            yield
            events.append("stop")

        monkeypatch.setattr(application_module, "notification_runtime", fake_runtime)
        app = FastAPI()
        app.state.identity_dependencies = marker
        async with application_module.application_lifespan(app, Settings()):
            assert events == ["start"]
        assert events == ["start", "stop"]

    asyncio.run(scenario())
