"""Private notification provider contract; importing it never sends email."""

from typing import Literal, Protocol

from app.contracts.domain_types import NotificationClaim, NotificationRecipient

FailureKind = Literal["transient_failure", "terminal_failure", "ambiguous"]


class NotificationDeliveryFailure(Exception):
    """A fixed safe outcome, never a raw provider response or recipient."""

    def __init__(self, kind: FailureKind) -> None:
        """Reject unknown classification rather than silently retrying it."""
        if kind not in ("transient_failure", "terminal_failure", "ambiguous"):
            raise ValueError("Invalid notification delivery outcome")
        super().__init__("Notification delivery failed")
        self.kind = kind


class NotificationSender(Protocol):
    """Submit one approved message; success is provider acceptance, not inbox receipt."""

    async def __call__(
        self, claim: NotificationClaim, recipient: NotificationRecipient
    ) -> None:
        """Submit once or raise a sanitized classified failure."""
        ...
