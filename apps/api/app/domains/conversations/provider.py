"""Concrete implementations injected through the declared Conversations ports."""

from psycopg import Error as PsycopgError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import (
    ListingThreadParticipantCheck,
    ParticipantCheck,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
from app.domains.conversations.origin_retirement import (
    PostgresOriginRetirementOperations,
)
from app.domains.conversations.thread_creation import PostgresThreadCreationOperations
from app.domains.conversations.offers import PostgresOfferOperations


class PostgresConversationServices(
    PostgresThreadCreationOperations,
    PostgresOriginRetirementOperations,
    PostgresOfferOperations,
):
    """Bind implemented creation/lookup/retirement ports without sharing sessions.

    Caller eligibility uses Identity's request-scoped public runtime binding.
    Offer persistence uses the same pool and the public Identity eligibility binding.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        """Retain one tuple-row pool; each operation owns its connection/transaction."""
        PostgresThreadCreationOperations.__init__(self, pool)
        PostgresOriginRetirementOperations.__init__(self, pool)
        PostgresOfferOperations.__init__(self, pool)

    async def check_listing_thread_participant(
        self, caller: CallerContext, request: ListingThreadParticipantCheck
    ) -> ParticipantCheck:
        """Confirm the seller/listing/buyer/thread relationship using owned rows only."""
        caller.require_current()
        try:
            async with self._pool.connection() as connection:
                cursor = await connection.execute(
                    "SELECT EXISTS (SELECT 1 FROM conversations.threads "
                    "WHERE id = %s AND listing_id = %s AND initiator_id = %s "
                    "AND counterparty_id = %s)",
                    (
                        request.conversation_id,
                        request.listing_id,
                        request.candidate_user_id,
                        caller.user_id,
                    ),
                )
                row = await cursor.fetchone()
        except PsycopgError, PoolTimeout:
            raise PublicError(ERRORS[503]) from None
        if row is None:
            raise PublicError(ERRORS[503])
        return ParticipantCheck(is_participant=row[0])
