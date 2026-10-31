"""Privacy-safe notification copy and trusted-link checks."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.contracts.domain_types import NotificationClaim
from app.domains.conversations.notifications.templates import render_notification


@pytest.mark.parametrize("kind", ["new_conversation", "unread_reminder"])
def test_template_includes_only_generic_copy_and_conversation_link(kind):
    """Do not include recipient, intent, token, unread sequence or private content."""
    now = datetime.now(UTC)
    claim = NotificationClaim(
        intent_id=uuid4(),
        conversation_id=uuid4(),
        recipient_id=uuid4(),
        event_kind=kind,
        due_at=now,
        fencing_token=uuid4(),
        lease_expires_at=now + timedelta(minutes=1),
        target_sequence=123456,
    )
    subject, body = render_notification(claim)
    assert f"https://clip-iisc.site/my/conversations/{claim.conversation_id}" in body
    assert all(
        str(secret) not in subject + body
        for secret in (
            claim.intent_id,
            claim.recipient_id,
            claim.fencing_token,
            claim.target_sequence,
        )
    )
    assert "\r" not in subject and "\n" not in subject


def test_template_rejects_unvalidated_or_unknown_claim():
    """Invalid route data or an unknown event cannot select unreviewed copy."""
    now = datetime.now(UTC)
    values = dict(
        intent_id=uuid4(),
        conversation_id=uuid4(),
        recipient_id=uuid4(),
        event_kind="unexpected",
        due_at=now,
        fencing_token=uuid4(),
        lease_expires_at=now,
    )
    with pytest.raises(ValueError):
        render_notification(NotificationClaim.model_construct(**values))
    values.update(event_kind="new_conversation", conversation_id="https://evil.invalid")
    with pytest.raises(ValueError):
        render_notification(NotificationClaim.model_construct(**values))
