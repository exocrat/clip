"""Explicit, default-off notification worker lifecycle for the API process."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from app.core.config import ConfigurationError, Settings
from app.domains.conversations.notifications.composition import run_batch
from app.domains.conversations.notifications.email_delivery import (
    NotificationEmailSender,
    SsmNotificationConfiguration,
)
from app.domains.conversations.notifications.scheduler import run_polling_worker
from app.domains.conversations.notifications.storage import PostgresNotificationDelivery
from app.domains.conversations.notifications.templates import render_notification

EMAIL_PARAMETER = "/clip/test/identity/email-delivery"


@asynccontextmanager
async def notification_runtime(
    settings: Settings, pool, identity
) -> AsyncIterator[None]:
    """Start one serial worker only for explicit hosted-test configuration.

    Dependencies are server-owned; no provider or secret is accessed until a
    due eligible job is dispatched. Shutdown stops polling and awaits the active
    batch before the owning database pool is closed. Production is not enabled.
    """
    if not settings.notification_worker_enabled:
        yield
        return
    if pool is None or identity is None:
        raise ConfigurationError("Notification worker dependencies unavailable")
    permit = object()
    delivery = PostgresNotificationDelivery(pool, permit)
    recipient = identity.sessions.notification_recipient_resolver(permit)
    sender = NotificationEmailSender(
        SsmNotificationConfiguration(EMAIL_PARAMETER),
        render_notification,
        profile="test",
        test_recipients=settings.ses_test_recipients,
        # The explicitly hosted real app delivers required event mail to eligible
        # users. Standalone worker probes retain their controlled-recipient flag.
        allow_unlisted_recipients=(
            settings.notification_allow_unlisted_recipients
            or settings.identity_runtime_enabled
        ),
    )
    stop = asyncio.Event()

    async def batch():
        """Run one bounded, serial batch through real owner-controlled ports."""
        return await run_batch(
            delivery,
            recipient,
            permit,
            lambda: datetime.now(UTC),
            sender,
            max_items=settings.notification_batch_size,
        )

    task = asyncio.create_task(
        run_polling_worker(
            batch, stop, interval_seconds=settings.notification_poll_seconds
        )
    )
    try:
        yield
    finally:
        stop.set()
        await task
