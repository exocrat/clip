"""Provider contract and deterministic test-only delivery behavior."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.contracts.domain_types import (
    NotificationClaim,
    NotificationClaimResult,
    NotificationDispatchContext,
    NotificationIntentState,
    NotificationRecipient,
)
from app.domains.conversations.notifications.provider import NotificationDeliveryFailure
from app.domains.conversations.notifications.worker import process_batch
from apps.api.tests.domains.conversations.fake_notification_provider import (
    FakeNotificationSender,
)


@pytest.mark.parametrize(
    "outcome", ["delivered", "transient_failure", "terminal_failure", "ambiguous"]
)
def test_scripted_provider_result_reaches_fenced_transition(outcome):
    """A classified provider result is recorded without storing private payloads."""

    async def scenario():
        now = datetime.now(UTC)
        user = uuid4()
        claim = NotificationClaim(
            intent_id=uuid4(),
            conversation_id=uuid4(),
            recipient_id=user,
            event_kind="new_conversation",
            due_at=now,
            fencing_token=uuid4(),
            lease_expires_at=now + timedelta(minutes=1),
        )
        recorded = []

        class Port:
            async def claim_due_notification_intents(self, context, request):
                return NotificationClaimResult(claims=[claim])

            async def read_notification_dispatch_context(self, context, request):
                return NotificationDispatchContext(decision="send", recipient_id=user)

            async def record_notification_attempt(self, context, request):
                recorded.append(request.outcome)
                return NotificationIntentState(state="pending", attempt_count=1)

        async def resolve(context, user_id):
            return NotificationRecipient(
                recipient_id=user_id, email="synthetic@example.invalid"
            )

        async def allowed(user_id):
            return True

        sender = FakeNotificationSender([outcome])
        assert (
            await process_batch(Port(), resolve, sender, lambda: now, allowed=allowed)
            == 1
        )
        assert recorded == [outcome]
        assert sender.intent_ids == [claim.intent_id]

    asyncio.run(scenario())


def test_provider_failures_do_not_accept_private_error_content():
    """Failure strings are fixed and unknown classifications fail closed."""
    assert (
        str(NotificationDeliveryFailure("ambiguous")) == "Notification delivery failed"
    )
    with pytest.raises(ValueError):
        NotificationDeliveryFailure("private-provider-response")


def test_fake_rejects_non_synthetic_recipient():
    """The test-only provider refuses arbitrary destinations before recording."""

    async def scenario():
        user = uuid4()
        now = datetime.now(UTC)
        claim = NotificationClaim(
            intent_id=uuid4(),
            conversation_id=uuid4(),
            recipient_id=user,
            event_kind="new_conversation",
            due_at=now,
            fencing_token=uuid4(),
            lease_expires_at=now + timedelta(minutes=1),
        )
        sender = FakeNotificationSender(["delivered"])
        with pytest.raises(AssertionError):
            await sender(
                claim,
                NotificationRecipient(recipient_id=user, email="someone@real.invalid"),
            )
        assert sender.intent_ids == []

    asyncio.run(scenario())


def test_provider_failure_is_observable_without_private_details(caplog):
    """A provider exception emits only the fixed outcome, never its contents."""

    async def scenario():
        now, user = datetime.now(UTC), uuid4()
        claim = NotificationClaim(
            intent_id=uuid4(),
            conversation_id=uuid4(),
            recipient_id=user,
            event_kind="new_conversation",
            due_at=now,
            fencing_token=uuid4(),
            lease_expires_at=now + timedelta(minutes=1),
        )

        class Port:
            async def claim_due_notification_intents(self, context, request):
                return NotificationClaimResult(claims=[claim])

            async def read_notification_dispatch_context(self, context, request):
                return NotificationDispatchContext(decision="send", recipient_id=user)

            async def record_notification_attempt(self, context, request):
                return NotificationIntentState(state="pending", attempt_count=1)

        async def resolve(context, user_id):
            return NotificationRecipient(
                recipient_id=user_id, email="synthetic@example.invalid"
            )

        async def allowed(user_id):
            return True

        async def send(job, recipient):
            raise RuntimeError("PRIVATE PROVIDER DETAIL")

        await process_batch(Port(), resolve, send, lambda: now, allowed=allowed)

    with caplog.at_level(logging.INFO):
        asyncio.run(scenario())
    assert "notification_delivery outcome=ambiguous" in caplog.text
    assert (
        "PRIVATE" not in caplog.text and "synthetic@example.invalid" not in caplog.text
    )
