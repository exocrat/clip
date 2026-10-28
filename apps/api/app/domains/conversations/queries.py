"""Participant-scoped inbox and summary reads over Conversations-owned state."""

from typing import Any
from uuid import UUID

from psycopg import Error as PsycopgError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import (
    ConversationQuery,
    ConversationSummary,
    CurrentOfferSummary,
    PageResult,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, FieldError, PublicError


class PostgresConversationQueries:
    """Read summaries without loading origins, message bodies, or peer receipts."""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def list_mine(
        self, caller: CallerContext, query: ConversationQuery
    ) -> PageResult[ConversationSummary]:
        """Filter authorized rows before paging; use deterministic offer/null ordering."""
        caller.require_current()
        if (
            query.offer_min_paise is not None
            and query.offer_max_paise is not None
            and query.offer_min_paise > query.offer_max_paise
        ):
            raise PublicError(ERRORS[422], (FieldError("query", "invalid_range"),))
        rows = await self._read(caller, query)
        return PageResult[ConversationSummary](
            items=rows[: query.page_size],
            page=query.page,
            page_size=query.page_size,
            has_next=len(rows) > query.page_size,
        )

    async def read_summary(
        self, caller: CallerContext, conversation_id: UUID
    ) -> ConversationSummary:
        """Use the same membership predicate for missing and nonmember safe 404s."""
        caller.require_current()
        rows = await self._read(caller, ConversationQuery(), conversation_id)
        if not rows:
            raise PublicError(ERRORS[404])
        return rows[0]

    async def _read(
        self,
        caller: CallerContext,
        query: ConversationQuery,
        conversation_id: UUID | None = None,
    ) -> list[ConversationSummary]:
        """Build parameterized owner-local SQL; only fixed identifiers select sorting."""
        predicates = ["member.user_id = %s"]
        parameters: list[Any] = [caller.user_id]
        if conversation_id is not None:
            predicates.append("thread.id = %s")
            parameters.append(conversation_id)
        if query.view != "all":
            predicates.append(
                "thread.initiator_id = %s"
                if query.view == "initiated"
                else "thread.counterparty_id = %s"
            )
            parameters.append(caller.user_id)
        origin_kind = "CASE WHEN thread.listing_id IS NOT NULL THEN 'sale_listing' ELSE 'wanted_request' END"
        origin_id = "coalesce(thread.listing_id, thread.wanted_request_id)"
        peer = "CASE WHEN thread.initiator_id = member.user_id THEN thread.counterparty_id ELSE thread.initiator_id END"
        if query.origin_kind is not None:
            predicates.append(f"{origin_kind} = %s")
            parameters.append(query.origin_kind)
        for values, expression in (
            (query.origin_id, origin_id),
            (query.counterparty_user_id, peer),
        ):
            if values:
                predicates.append(f"{expression} = ANY(%s)")
                parameters.append(values)
        if query.offer_status is not None:
            predicates.append("revision.status = %s")
            parameters.append(query.offer_status)
        for bound, operator in (
            (query.offer_min_paise, ">="),
            (query.offer_max_paise, "<="),
        ):
            if bound is not None:
                predicates.append(f"revision.amount_paise {operator} %s")
                parameters.append(bound)
        ordering = "thread.last_activity_at DESC, thread.id DESC"
        if query.sort != "last_activity_desc":
            direction = "ASC" if query.sort == "offer_amount_asc" else "DESC"
            ordering = f"revision.amount_paise {direction} NULLS LAST, {ordering}"
        parameters.extend((query.page_size + 1, (query.page - 1) * query.page_size))
        statement = (
            f"SELECT thread.id, {origin_kind}, {origin_id}, thread.initiator_id, "
            f"thread.initiator_id = member.user_id, {peer}, thread.last_activity_at, "
            "member.last_read_sequence, (SELECT count(*) FROM conversations.entries AS entry "
            "WHERE entry.conversation_id = thread.id AND entry.kind = 'message' "
            "AND entry.sender_id <> member.user_id AND entry.sequence > member.last_read_sequence), "
            "offer.id, revision.revision, revision.amount_paise, revision.status, revision.created_at "
            "FROM conversations.threads AS thread JOIN conversations.members AS member "
            "ON member.conversation_id = thread.id "
            "LEFT JOIN conversations.offers AS offer ON offer.conversation_id = thread.id "
            "LEFT JOIN conversations.offer_revisions AS revision "
            "ON revision.offer_id = offer.id AND revision.revision = offer.current_revision "
            f"WHERE {' AND '.join(predicates)} ORDER BY {ordering} LIMIT %s OFFSET %s"
        )
        try:
            async with self._pool.connection() as connection:
                cursor = await connection.execute(statement, parameters)
                rows = await cursor.fetchall()
            return [self._summary(row) for row in rows]
        except PsycopgError, PoolTimeout:
            raise PublicError(ERRORS[503]) from None

    @staticmethod
    def _summary(row: tuple[Any, ...]) -> ConversationSummary:
        """Map only the reviewed public summary and current retained offer fields."""
        offer = None
        if row[10] is not None:
            offer = CurrentOfferSummary(
                offer_id=row[9],
                revision=row[10],
                amount_paise=row[11],
                status=row[12],
                updated_at=row[13],
            )
        return ConversationSummary(
            conversation_id=row[0],
            origin_kind=row[1],
            origin_id=row[2],
            initiator_user_id=row[3],
            caller_role="initiator" if row[4] else "origin_owner",
            counterparty_user_id=row[5],
            last_activity_at=row[6],
            own_last_read_sequence=row[7],
            unread_count=row[8],
            current_offer=offer,
        )
