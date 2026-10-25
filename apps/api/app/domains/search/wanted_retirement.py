"""Approved, explicitly invoked wanted retirement; no route, scheduler or target.

Persist a stable pending pair before public Conversations calls. Unknown outcomes
leave that pair intact. Only a confirmed all-or-none no-write marker permits the
Search store's atomic receipt/content scrub. Real integration is a separate gate.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from app.contracts.domain_types import (
    OriginActivityRequest,
    OriginActivityResult,
    OriginOwnerContext,
    OriginRetirementCommand,
    RetirementMarkerResult,
)
from app.core.errors import ERRORS, PublicError
from app.core.timestamps import as_utc
import app.domains.conversations.public as conversations_public

_DEPENDENCY_TIMEOUT = 2.0


@dataclass(frozen=True)
class PendingWantedRetirement:
    """Server-persisted retry identity; cutoff never changes on resume."""

    operation_id: UUID
    cutoff_utc: datetime


class WantedRetirementStore(Protocol):
    """Local Search transactions only; no database session crosses this interface."""

    async def begin_retirement(
        self, identifier: UUID, now: datetime
    ) -> PendingWantedRetirement | None:
        """Lock/recheck180days and commit or resume the stable pending pair."""
        ...

    async def clear_retirement(
        self, identifier: UUID, pending: PendingWantedRetirement
    ) -> None:
        """Clear only the exact pair after a confirmed blocked result."""
        ...

    async def finalize_retirement(
        self, identifier: UUID, pending: PendingWantedRetirement, now: datetime
    ) -> None:
        """Recheck/fence then scrub all receipt and origin content atomically."""
        ...


class WantedRetirementConversations(Protocol):
    """Reviewed public contract, replaceable only by explicit test doubles."""

    async def get_origin_activity(
        self, context: OriginOwnerContext, request: OriginActivityRequest
    ) -> OriginActivityResult:
        """Return complete content-free preflight metadata for this owned origin."""
        ...

    async def mark_origin_retired(
        self, context: OriginOwnerContext, request: OriginRetirementCommand
    ) -> RetirementMarkerResult:
        """Authoritatively mark all threads or none under Conversations locks."""
        ...


class WantedRetirementService:
    """One server-selected origin per explicit call; no automatic write retries."""

    def __init__(
        self,
        store: WantedRetirementStore,
        conversations: WantedRetirementConversations = conversations_public,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Default to real public dependency; never select a fake or a DB target."""
        self.store, self.conversations, self.clock = store, conversations, clock

    async def retire(self, identifier: UUID) -> RetirementMarkerResult | None:
        """Coordinate marking and approved cleanup, retaining unknown outcomes.

        None means missing/already-retired/not yet180day-eligible. Caller identity
        is not an HTTP input: this internal maintenance method constructs only
        the server-owned wanted context. It grants no participant capability.
        """
        now = as_utc(self.clock())
        pending = await self.store.begin_retirement(identifier, now)
        if pending is None:
            return None
        # Clock regression must not turn a future cutoff into a looser activity
        # check. Keep the pending pair for a later safe retry, never replace it.
        if as_utc(pending.cutoff_utc) > now - timedelta(days=90):
            raise PublicError(ERRORS[503])
        context = OriginOwnerContext(origin_kind="wanted_request")
        try:
            async with asyncio.timeout(_DEPENDENCY_TIMEOUT):
                raw_activity = await self.conversations.get_origin_activity(
                    context,
                    OriginActivityRequest(
                        origin_kind="wanted_request", origin_id=identifier
                    ),
                )
            activity = OriginActivityResult.model_validate(raw_activity)
            if (activity.thread_count == 0) != (
                activity.latest_participant_write_at is None
            ):
                raise ValueError("Incomplete activity")
            # Preflight cannot authorize cleanup, even when it reports no recent
            # writes. The atomic marker rechecks every associated thread.
            async with asyncio.timeout(_DEPENDENCY_TIMEOUT):
                raw_result = await self.conversations.mark_origin_retired(
                    context,
                    OriginRetirementCommand(
                        origin_kind="wanted_request",
                        origin_id=identifier,
                        operation_id=pending.operation_id,
                        cutoff_utc=pending.cutoff_utc,
                    ),
                )
            result = RetirementMarkerResult.model_validate(raw_result)
            if result.outcome == "blocked_recent_activity" and result.marked_count != 0:
                raise ValueError("Partial blocked result")
        except TimeoutError, NotImplementedError, OSError, ValidationError, ValueError:
            raise PublicError(ERRORS[503]) from None
        except PublicError:
            raise
        except Exception:
            # Unknown provider exceptions may follow a committed marker. Never
            # clear/re-key or disclose provider diagnostics in this case.
            raise PublicError(ERRORS[503]) from None
        if result.outcome == "blocked_recent_activity":
            await self.store.clear_retirement(identifier, pending)
        else:
            await self.store.finalize_retirement(
                identifier, pending, as_utc(self.clock())
            )
        return result
