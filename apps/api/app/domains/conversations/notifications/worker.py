"""Bounded delivery orchestration using injected, owner-controlled ports.

This module starts no process and installs no provider. Composition must supply
the reviewed Conversations and Identity ports and a separately reviewed sender.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.contracts.domain_types import (
    NotificationAttemptResult,
    NotificationClaimRequest,
    NotificationClaimResult,
    NotificationDispatchCheck,
    NotificationDispatchContext,
    NotificationIntentState,
    NotificationRecipient,
    NotificationWorkerContext,
)
from app.domains.conversations.notifications.provider import (
    NotificationDeliveryFailure,
    NotificationSender,
)


class DeliveryPort(Protocol):
    """Conversations owns claims, read checks and fenced state transitions."""

    async def claim_due_notification_intents(
        self, context: NotificationWorkerContext, request: NotificationClaimRequest
    ) -> NotificationClaimResult: ...

    async def read_notification_dispatch_context(
        self, context: NotificationWorkerContext, request: NotificationDispatchCheck
    ) -> NotificationDispatchContext: ...

    async def record_notification_attempt(
        self, context: NotificationWorkerContext, request: NotificationAttemptResult
    ) -> NotificationIntentState: ...


async def process_batch(
    port: DeliveryPort,
    resolve: Callable[
        [NotificationWorkerContext, UUID], Awaitable[NotificationRecipient | None]
    ],
    send: NotificationSender,
    clock: Callable[[], datetime],
    max_items: int = 20,
    allowed: Callable[[UUID], Awaitable[bool]] | None = None,
) -> int:
    """Process one bounded batch; errors never expose provider or recipient data.

    Resolve before the final fenced read check. Unknown dependencies or expired
    leases leave the claim for lease recovery, without attempting email. A sender
    exception is ambiguous and recorded as such; it may have sent the email.
    The caller must provide preference enforcement before enabling real delivery.
    """
    context = NotificationWorkerContext()
    claims = await port.claim_due_notification_intents(
        context, NotificationClaimRequest(now_utc=clock(), max_items=max_items)
    )
    processed = 0
    for claim in claims.claims:
        try:
            recipient = await resolve(context, claim.recipient_id)
            if recipient is None or recipient.recipient_id != claim.recipient_id:
                continue
            if allowed is None or await allowed(claim.recipient_id) is not True:
                continue
            now = clock()
            if now >= claim.lease_expires_at:
                continue
            check = await port.read_notification_dispatch_context(
                context,
                NotificationDispatchCheck(
                    intent_id=claim.intent_id,
                    fencing_token=claim.fencing_token,
                    now_utc=now,
                ),
            )
            if check.decision != "send" or check.recipient_id != claim.recipient_id:
                continue
            if clock() >= claim.lease_expires_at:
                continue
            try:
                await send(claim, recipient)
                outcome = "delivered"
            except NotificationDeliveryFailure as failure:
                outcome = failure.kind
            except Exception:
                outcome = "ambiguous"
            await port.record_notification_attempt(
                context,
                NotificationAttemptResult(
                    intent_id=claim.intent_id,
                    fencing_token=claim.fencing_token,
                    outcome=outcome,
                    attempted_at=clock(),
                ),
            )
            processed += 1
        except Exception:
            # Never log exceptions: dependencies may include addresses or content.
            # A failed or uncertain fenced transition is recovered by the owner.
            continue
    return processed
