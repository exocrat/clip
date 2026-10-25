"""Search-owned regular-only request responses through public Conversations.

A short origin lock serializes closure/retirement with bounded creation. Thread
storage and membership belong to Conversations; no local fake/receipt/thread is
created. Ambiguous outcomes are recovered through its stable responder pair.
"""

import asyncio
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from app.contracts.domain_types import (
    ConversationStartResult,
    ExistingWantedConversationLookup,
    WantedConversationContext,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
import app.domains.identity.public as identity_public
import app.domains.conversations.public as conversations_public

_TIMEOUT = 2.0


@dataclass(frozen=True)
class WantedResponseOrigin:
    """Minimal server-resolved origin facts; never expose author ID to HTTP."""

    author_id: UUID
    state: Literal["open", "unavailable"]
    retired: bool
    pending: bool


class ResponseStore(Protocol):
    """Hold only Search's origin lock while the public call uses its own session."""

    def response_guard(
        self, identifier: UUID
    ) -> AbstractAsyncContextManager[WantedResponseOrigin | None]:
        """Serialize ordinary owner writes while allowing FK key-share checks."""
        ...


class ResponseIdentity(Protocol):
    """Regular responder eligibility through the reviewed public Identity API."""

    async def eligible(self, actor: UUID) -> bool:
        """Check live revocation/expiry as well as trusted regular class."""
        ...


class PublicResponseIdentity:
    """No eligible fixture or credential is supplied by normal composition."""

    async def eligible(self, actor: UUID) -> bool:
        """Use explicit regular capability; the default declaration fails closed."""
        return (
            await identity_public.check_account_eligibility(
                actor, required_class="regular"
            )
        ).eligible


class ResponseConversations(Protocol):
    """Exact pair operations; no new private table/session/operation-ID input."""

    async def open_or_create_wanted_conversation(
        self, caller: CallerContext, request: WantedConversationContext
    ) -> ConversationStartResult:
        """Create or return the single request/responder thread."""
        ...

    async def find_existing_wanted_conversation(
        self, caller: CallerContext, request: ExistingWantedConversationLookup
    ) -> ConversationStartResult | None:
        """Read only that caller/request pair; never creates a closed-origin thread."""
        ...


class WantedResponseService:
    """Validate trusted caller/state and delegate; return only thread ID/created."""

    def __init__(
        self,
        store: ResponseStore,
        conversations: ResponseConversations = conversations_public,
        identity: ResponseIdentity | None = None,
    ) -> None:
        """Default providers are real public declarations; explicit doubles are tests."""
        self.store, self.conversations = store, conversations
        self.identity = PublicResponseIdentity() if identity is None else identity

    async def respond(
        self, caller: CallerContext, identifier: UUID
    ) -> ConversationStartResult:
        """Open uses create-or-existing; closed uses existing-only, never fallback create.

        Temporary denial happens before origin access. Retired/pending/missing is
        safe404; self response403. No author/participant values come from HTTP.
        Cancellation releases the local lock but may leave a committed remote
        result: retries always use the same request/responder identity.
        """
        caller.require_current()
        if caller.account_class != "regular":
            raise PublicError(ERRORS[403])
        try:
            async with asyncio.timeout(_TIMEOUT):
                eligible = await self.identity.eligible(caller.user_id)
        except NotImplementedError, TimeoutError, OSError:
            raise PublicError(ERRORS[503]) from None
        if type(eligible) is not bool:
            raise PublicError(ERRORS[503])
        if not eligible:
            raise PublicError(ERRORS[403])
        async with self.store.response_guard(identifier) as origin:
            if origin is None or origin.retired or origin.pending:
                raise PublicError(ERRORS[404])
            if origin.author_id == caller.user_id:
                raise PublicError(ERRORS[403])
            if origin.state not in {"open", "unavailable"}:
                raise PublicError(ERRORS[503])
            result: ConversationStartResult | None
            try:
                async with asyncio.timeout(_TIMEOUT):
                    if origin.state == "open":
                        result = (
                            await self.conversations.open_or_create_wanted_conversation(
                                caller,
                                WantedConversationContext(
                                    request_id=identifier, author_id=origin.author_id
                                ),
                            )
                        )
                    else:
                        result = (
                            await self.conversations.find_existing_wanted_conversation(
                                caller,
                                ExistingWantedConversationLookup(request_id=identifier),
                            )
                        )
            except PublicError:
                raise
            except Exception:
                # May have committed remotely. Never invent a result, retry a
                # new thread or disclose exception detail; keep pair-based retry.
                raise PublicError(ERRORS[503]) from None
            if result is None and origin.state == "unavailable":
                raise PublicError(ERRORS[404])
            if (
                not isinstance(result, ConversationStartResult)
                or type(result.created) is not bool
                or not isinstance(result.conversation_id, UUID)
                or (origin.state == "unavailable" and result.created)
            ):
                raise PublicError(ERRORS[503])
            return result
