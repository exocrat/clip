"""Explicit server-only assembly of Conversations and Identity delivery ports."""

from app.core.runtime_bindings import runtime_claims
from app.domains.conversations.notifications.worker import process_batch


async def run_batch(
    delivery, recipients, permit, clock, send, allowed, *, max_items=20
):
    """Run one batch under a private permit; never enable a scheduler or provider.

    The caller supplies reviewed destination and preference handling. Until the
    preference provider and actual mail adapter exist, this entry point is used
    only by explicitly composed synthetic tests.
    """
    if permit is None:
        raise ValueError("Worker permit required")
    with runtime_claims(
        {
            "conversations.notification_worker": permit,
            "identity.notification_worker": permit,
        }
    ):
        return await process_batch(
            delivery,
            recipients.resolve,
            send,
            clock,
            max_items=max_items,
            allowed=allowed,
        )
