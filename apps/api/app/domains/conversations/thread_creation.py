"""Conversations-owned creation of Listing and Wanted Request threads."""

from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from psycopg import Error as PsycopgError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import (
    AccountClass,
    AccountEligibility,
    ConversationStartResult,
    ExistingWantedConversationLookup,
    ExistingListingConversationLookup,
    ListingConversationContext,
    WantedConversationContext,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
from app.domains.identity.public import check_account_eligibility

AccountEligibilityCheck = Callable[
    [UUID, AccountClass | None], Awaitable[AccountEligibility]
]


class PostgresThreadCreationOperations:
    """Create or find exact-pair threads without reading origin-owner tables.

    Listings and Search pass server-resolved origin/member context. Identity's
    public eligibility callable is injected, and all thread/member/initial
    notification rows commit together. The application entry point does not
    import or wire this private Conversations implementation.
    """

    def __init__(
        self,
        pool: AsyncConnectionPool,
        eligibility_check: AccountEligibilityCheck = check_account_eligibility,
    ) -> None:
        """Retain the shared pool and typed Identity public operation."""
        self._pool = pool
        self._eligibility_check = eligibility_check

    @staticmethod
    def _unavailable() -> PublicError:
        """Return a generic dependency error without driver or SQL details."""
        return PublicError(ERRORS[503])

    async def _require_eligible(
        self, user_id: UUID, required_class: AccountClass | None
    ) -> None:
        """Ask Identity for current eligibility; fail closed on dependency errors."""
        try:
            result = await self._eligibility_check(user_id, required_class)
        except PublicError:
            raise
        except Exception:
            raise self._unavailable() from None
        if not result.eligible:
            raise PublicError(ERRORS[403])

    async def open_or_create_listing_conversation(
        self, caller: CallerContext, request: ListingConversationContext
    ) -> ConversationStartResult:
        """Open the buyer/listing pair, allowing a retry to return its thread."""
        caller.require_current()
        if caller.user_id == request.owner_id:
            raise PublicError(ERRORS[403])
        await self._require_eligible(caller.user_id, caller.account_class)
        await self._require_eligible(request.owner_id, "regular")
        return await self._open_or_create_pair(
            insert_sql=(
                "INSERT INTO conversations.threads "
                "(id, listing_id, initiator_id, counterparty_id) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (listing_id, initiator_id) "
                "WHERE listing_id IS NOT NULL DO NOTHING RETURNING id"
            ),
            lookup_sql=(
                "SELECT id, counterparty_id FROM conversations.threads "
                "WHERE listing_id = %s AND initiator_id = %s"
            ),
            origin_id=request.listing_id,
            caller_id=caller.user_id,
            counterparty_id=request.owner_id,
        )

    async def find_existing_listing_conversation(
        self, caller: CallerContext, request: ExistingListingConversationLookup
    ) -> ConversationStartResult | None:
        """Read only the authenticated buyer's pair; never create on an old origin.

        Listings guards retirement/availability in its own transaction. Both
        regular and eligible temporary buyers may reopen their existing thread;
        the owner still needs current regular eligibility through Identity.
        """
        caller.require_current()
        await self._require_eligible(caller.user_id, caller.account_class)
        try:
            async with self._pool.connection() as connection:
                row = await (
                    await connection.execute(
                        "SELECT id,counterparty_id FROM conversations.threads "
                        "WHERE listing_id=%s AND initiator_id=%s",
                        (request.listing_id, caller.user_id),
                    )
                ).fetchone()
        except PsycopgError, PoolTimeout:
            raise self._unavailable() from None
        if row is None:
            return None
        await self._require_eligible(row[1], "regular")
        return ConversationStartResult(conversation_id=row[0], created=False)

    async def open_or_create_wanted_conversation(
        self, caller: CallerContext, request: WantedConversationContext
    ) -> ConversationStartResult:
        """Open a regular responder/request pair with a safe concurrent retry."""
        caller.require_current()
        if caller.account_class != "regular" or caller.user_id == request.author_id:
            raise PublicError(ERRORS[403])
        await self._require_eligible(caller.user_id, "regular")
        await self._require_eligible(request.author_id, None)
        return await self._open_or_create_pair(
            insert_sql=(
                "INSERT INTO conversations.threads "
                "(id, wanted_request_id, initiator_id, counterparty_id) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (wanted_request_id, initiator_id) "
                "WHERE wanted_request_id IS NOT NULL DO NOTHING RETURNING id"
            ),
            lookup_sql=(
                "SELECT id, counterparty_id FROM conversations.threads "
                "WHERE wanted_request_id = %s AND initiator_id = %s"
            ),
            origin_id=request.request_id,
            caller_id=caller.user_id,
            counterparty_id=request.author_id,
        )

    async def find_existing_wanted_conversation(
        self, caller: CallerContext, request: ExistingWantedConversationLookup
    ) -> ConversationStartResult | None:
        """Read only the authenticated responder/request pair after closure or timeout.

        Never call create from this path. Missing data returns None; Identity or
        storage failure stays an error, so Search cannot mistake it for absence.
        """
        caller.require_current()
        if caller.account_class != "regular":
            raise PublicError(ERRORS[403])
        await self._require_eligible(caller.user_id, "regular")
        try:
            async with self._pool.connection() as connection:
                cursor = await connection.execute(
                    "SELECT id, counterparty_id FROM conversations.threads "
                    "WHERE wanted_request_id = %s AND initiator_id = %s",
                    (request.request_id, caller.user_id),
                )
                row = await cursor.fetchone()
        except PsycopgError, PoolTimeout:
            raise self._unavailable() from None
        if row is None:
            return None
        await self._require_eligible(row[1], None)
        return ConversationStartResult(conversation_id=row[0], created=False)

    async def _open_or_create_pair(
        self,
        *,
        insert_sql: str,
        lookup_sql: str,
        origin_id: UUID,
        caller_id: UUID,
        counterparty_id: UUID,
    ) -> ConversationStartResult:
        """Serialize pair uniqueness and atomically add members/notification."""
        candidate_id = uuid4()
        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    cursor = await connection.execute(
                        insert_sql,
                        (candidate_id, origin_id, caller_id, counterparty_id),
                    )
                    created = await cursor.fetchone()
                    if created is None:
                        cursor = await connection.execute(
                            lookup_sql, (origin_id, caller_id)
                        )
                        existing = await cursor.fetchone()
                        if existing is None:
                            # A committed pair cannot disappear: references are
                            # retained and no delete path is allowed here.
                            raise self._unavailable()
                        if existing[1] != counterparty_id:
                            raise PublicError(ERRORS[409])
                        return ConversationStartResult(
                            conversation_id=existing[0], created=False
                        )

                    conversation_id = created[0]
                    await connection.execute(
                        "INSERT INTO conversations.members "
                        "(conversation_id, user_id) VALUES (%s, %s), (%s, %s)",
                        (
                            conversation_id,
                            caller_id,
                            conversation_id,
                            counterparty_id,
                        ),
                    )
                    await connection.execute(
                        "INSERT INTO conversations.notification_intents "
                        "(id, conversation_id, recipient_id, event_kind, "
                        "deduplication_key, due_at, expires_at) "
                        "SELECT %s, thread.id, %s, 'new_conversation', %s, "
                        "thread.created_at, thread.created_at + INTERVAL '24 hours' "
                        "FROM conversations.threads AS thread WHERE thread.id = %s",
                        (
                            uuid4(),
                            counterparty_id,
                            f"new_conversation:{conversation_id}:{counterparty_id}",
                            conversation_id,
                        ),
                    )
                    return ConversationStartResult(
                        conversation_id=conversation_id, created=True
                    )
        except PublicError:
            raise
        except PsycopgError, PoolTimeout:
            # Creation may have committed before a network failure became
            # visible; the caller can retry the exact pair safely.
            raise self._unavailable() from None
