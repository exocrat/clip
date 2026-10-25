"""Explicit public Conversations response script; no SQL/thread implementation."""

import asyncio
from uuid import uuid4

from app.contracts.domain_types import ConversationStartResult


class ConversationsResponseDouble:
    """Model only stable pair outcomes, optional lost result and a scheduling gate."""

    def __init__(self):
        """Never selected by production composition or a browser flag."""
        self.threads = {}
        self.create_calls = []
        self.lookup_calls = []
        self.effects = 0
        self.lose_once = False
        self.pause_for = None
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def open_or_create_wanted_conversation(self, caller, request):
        """Return the exact synthetic responder pair, optionally losing its result."""
        caller.require_current()
        assert caller.account_class == "regular" and caller.user_id != request.author_id
        self.create_calls.append((caller, request))
        if request.request_id == self.pause_for:
            self.entered.set()
            await self.release.wait()
        pair = (request.request_id, caller.user_id)
        created = pair not in self.threads
        if created:
            self.threads[pair] = uuid4()
            self.effects += 1
        if self.lose_once:
            self.lose_once = False
            raise TimeoutError("controlled lost conversation result")
        return ConversationStartResult(
            conversation_id=self.threads[pair], created=created
        )

    async def find_existing_wanted_conversation(self, caller, request):
        """Read only that pair; a lookup cannot populate the synthetic map."""
        caller.require_current()
        assert caller.account_class == "regular"
        self.lookup_calls.append((caller, request))
        identifier = self.threads.get((request.request_id, caller.user_id))
        return (
            None
            if identifier is None
            else ConversationStartResult(conversation_id=identifier, created=False)
        )
