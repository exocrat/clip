"""Test-only scripted notification provider for synthetic recipients."""

from collections import deque

from app.domains.conversations.notifications.provider import NotificationDeliveryFailure


class FakeNotificationSender:
    """Return scripted outcomes; capture only non-sensitive intent IDs."""

    def __init__(self, outcomes):
        """Bind a finite sequence so unexpected extra sends fail the test."""
        self._outcomes = deque(outcomes)
        self.intent_ids = []

    async def __call__(self, claim, recipient):
        """Reject non-synthetic addresses and deliver only a scripted result."""
        if not recipient.email.endswith("@example.invalid") or not self._outcomes:
            raise AssertionError("Unexpected test delivery")
        self.intent_ids.append(claim.intent_id)
        outcome = self._outcomes.popleft()
        if outcome != "delivered":
            raise NotificationDeliveryFailure(outcome)
