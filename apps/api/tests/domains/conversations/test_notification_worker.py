"""Synthetic ports exercise worker ordering without sending real email."""

import asyncio
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
from app.domains.conversations.notifications.worker import process_batch

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("decision", ["send", "suppress", "defer"])
def test_worker_rechecks_read_state_before_send(decision):
    """Only an authorized fresh send decision reaches the synthetic sender."""

    async def scenario():
        recipient_id = uuid4()
        claim = NotificationClaim(
            intent_id=uuid4(),
            conversation_id=uuid4(),
            recipient_id=recipient_id,
            event_kind="unread_reminder",
            due_at=NOW,
            target_sequence=1,
            fencing_token=uuid4(),
            lease_expires_at=NOW + timedelta(minutes=1),
        )
        calls = []

        class Port:
            async def claim_due_notification_intents(self, context, request):
                return NotificationClaimResult(claims=[claim])

            async def read_notification_dispatch_context(self, context, request):
                calls.append("read")
                return NotificationDispatchContext(
                    decision=decision, recipient_id=recipient_id
                )

            async def record_notification_attempt(self, context, request):
                calls.append(request.outcome)
                return NotificationIntentState(state="delivered", attempt_count=1)

        async def resolve(context, user_id):
            calls.append("resolve")
            return NotificationRecipient(
                recipient_id=user_id, email="synthetic@example.invalid"
            )

        async def send(job, recipient):
            calls.append("send")

        async def allowed(user_id):
            return True

        count = await process_batch(Port(), resolve, send, lambda: NOW, allowed=allowed)
        assert calls == (
            ["resolve", "read", "send", "delivered"]
            if decision == "send"
            else ["resolve", "read"]
        )
        assert count == (1 if decision == "send" else 0)

    asyncio.run(scenario())


def test_missing_preference_provider_cannot_send():
    """An uncomposed preference provider never enables mail delivery."""

    async def scenario():
        user = uuid4()
        calls = []
        claim = NotificationClaim(
            intent_id=uuid4(),
            conversation_id=uuid4(),
            recipient_id=user,
            event_kind="new_conversation",
            due_at=NOW,
            fencing_token=uuid4(),
            lease_expires_at=NOW + timedelta(minutes=1),
        )

        class Port:
            async def claim_due_notification_intents(self, context, request):
                return NotificationClaimResult(claims=[claim])

        async def resolve(context, recipient):
            return NotificationRecipient(
                recipient_id=user, email="synthetic@example.invalid"
            )

        async def send(job, recipient):
            calls.append("sent")

        assert await process_batch(Port(), resolve, send, lambda: NOW) == 0
        assert calls == []

    asyncio.run(scenario())


@pytest.mark.parametrize("kind", ["new_conversation", "unread_reminder"])
def test_disabled_preference_suppresses_without_sending(kind):
    """An explicit opt-out suppresses both kinds before any provider call."""

    async def scenario():
        user = uuid4()
        claim = NotificationClaim(
            intent_id=uuid4(),
            conversation_id=uuid4(),
            recipient_id=user,
            event_kind=kind,
            due_at=NOW,
            fencing_token=uuid4(),
            lease_expires_at=NOW + timedelta(minutes=1),
        )
        calls = []

        class Port:
            async def claim_due_notification_intents(self, context, request):
                return NotificationClaimResult(claims=[claim])

            async def record_notification_attempt(self, context, request):
                calls.append(request.outcome)
                return NotificationIntentState(state="suppressed", attempt_count=0)

        async def resolve(context, recipient):
            return NotificationRecipient(
                recipient_id=user, email="synthetic@example.invalid"
            )

        async def allowed(user_id):
            return False

        async def send(job, recipient):
            calls.append("sent")

        await process_batch(Port(), resolve, send, lambda: NOW, allowed=allowed)
        assert calls == ["preference_suppressed"]

    asyncio.run(scenario())


def test_unknown_preference_defers_without_suppression():
    """Malformed or unavailable preference data cannot authorize or suppress."""

    async def scenario():
        user = uuid4()
        calls = []
        claim = NotificationClaim(
            intent_id=uuid4(),
            conversation_id=uuid4(),
            recipient_id=user,
            event_kind="new_conversation",
            due_at=NOW,
            fencing_token=uuid4(),
            lease_expires_at=NOW + timedelta(minutes=1),
        )

        class Port:
            async def claim_due_notification_intents(self, context, request):
                return NotificationClaimResult(claims=[claim])

            async def record_notification_attempt(self, context, request):
                calls.append("suppressed")

        async def resolve(context, recipient):
            return NotificationRecipient(
                recipient_id=user, email="synthetic@example.invalid"
            )

        async def unknown(user_id):
            return None

        async def send(job, recipient):
            calls.append("sent")

        assert (
            await process_batch(Port(), resolve, send, lambda: NOW, allowed=unknown)
            == 0
        )
        assert calls == []

    asyncio.run(scenario())


def test_preference_change_after_read_check_prevents_send():
    """A last-moment opt-out is checked again after dispatch reservation."""

    async def scenario():
        user, checks, outcomes = uuid4(), [], []
        claim = NotificationClaim(
            intent_id=uuid4(),
            conversation_id=uuid4(),
            recipient_id=user,
            event_kind="unread_reminder",
            due_at=NOW,
            fencing_token=uuid4(),
            lease_expires_at=NOW + timedelta(minutes=1),
        )

        class Port:
            async def claim_due_notification_intents(self, context, request):
                return NotificationClaimResult(claims=[claim])

            async def read_notification_dispatch_context(self, context, request):
                return NotificationDispatchContext(decision="send", recipient_id=user)

            async def record_notification_attempt(self, context, request):
                outcomes.append(request.outcome)
                return NotificationIntentState(state="suppressed", attempt_count=1)

        async def resolve(context, recipient):
            return NotificationRecipient(
                recipient_id=user, email="synthetic@example.invalid"
            )

        async def allowed(user_id):
            checks.append(True)
            return len(checks) == 1

        async def send(job, recipient):
            outcomes.append("sent")

        await process_batch(Port(), resolve, send, lambda: NOW, allowed=allowed)
        assert len(checks) == 2 and outcomes == ["preference_suppressed"]

    asyncio.run(scenario())


@pytest.mark.parametrize("failure", ["recipient", "expired", "sender"])
def test_worker_fails_closed_or_records_ambiguous_send(failure):
    """Missing recipient or lease cannot send; an uncertain send is not success."""

    async def scenario():
        recipient_id = uuid4()
        claim = NotificationClaim(
            intent_id=uuid4(),
            conversation_id=uuid4(),
            recipient_id=recipient_id,
            event_kind="new_conversation",
            due_at=NOW,
            fencing_token=uuid4(),
            lease_expires_at=(
                NOW if failure == "expired" else NOW + timedelta(minutes=1)
            ),
        )
        outcomes = []

        class Port:
            async def claim_due_notification_intents(self, context, request):
                return NotificationClaimResult(claims=[claim])

            async def read_notification_dispatch_context(self, context, request):
                return NotificationDispatchContext(
                    decision="send", recipient_id=recipient_id
                )

            async def record_notification_attempt(self, context, request):
                outcomes.append(request.outcome)
                return NotificationIntentState(state="pending", attempt_count=1)

        async def resolve(context, user_id):
            if failure == "recipient":
                return None
            return NotificationRecipient(
                recipient_id=user_id, email="synthetic@example.invalid"
            )

        async def send(job, recipient):
            assert failure == "sender"
            raise TimeoutError("synthetic sensitive provider response")

        async def allowed(user_id):
            return True

        await process_batch(Port(), resolve, send, lambda: NOW, allowed=allowed)
        assert outcomes == (["ambiguous"] if failure == "sender" else [])

    asyncio.run(scenario())
