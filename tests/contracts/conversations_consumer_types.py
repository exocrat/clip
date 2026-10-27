"""Mypy probe for a typed consumer of Conversations' retirement interface."""

from app.contracts.domain_types import (
    OriginActivityRequest,
    OriginOwnerContext,
    OriginRetirementCommand,
)
from app.domains.conversations.public import ConversationsPublic


async def retire_origin(
    conversations: ConversationsPublic,
    context: OriginOwnerContext,
    activity_request: OriginActivityRequest,
    retirement_command: OriginRetirementCommand,
) -> None:
    """Exercise the typed call shape consumers will inject and invoke."""
    await conversations.get_origin_activity(context, activity_request)
    await conversations.mark_origin_retired(context, retirement_command)
