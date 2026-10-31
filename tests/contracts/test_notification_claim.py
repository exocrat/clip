"""The worker claim accepts both event kinds stored by Conversations."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from contracts.source.types import NotificationClaim


@pytest.mark.parametrize("event_kind", ["new_conversation", "unread_reminder"])
def test_notification_claim_event_kinds(event_kind):
    """Both durable event kinds must cross the reviewed worker boundary."""
    now = datetime.now(timezone.utc)
    claim = NotificationClaim(
        intent_id=uuid4(),
        conversation_id=uuid4(),
        recipient_id=uuid4(),
        event_kind=event_kind,
        due_at=now,
        fencing_token=uuid4(),
        lease_expires_at=now,
    )
    assert claim.event_kind == event_kind


def test_notification_claim_rejects_unknown_event_kind():
    """A worker must not accept an event outside the approved policy."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        NotificationClaim(
            intent_id=uuid4(),
            conversation_id=uuid4(),
            recipient_id=uuid4(),
            event_kind="unread_message",
            due_at=now,
            fencing_token=uuid4(),
            lease_expires_at=now,
        )
