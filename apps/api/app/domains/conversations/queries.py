"""Participant-scoped inbox and summary reads over Conversations-owned state."""

from typing import Any
from uuid import UUID

from psycopg import Error as PsycopgError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import (
    ConversationQuery,
    ConversationSummary,
    ConversationUnreadCount,
    CurrentOfferSummary,
    PageResult,
)
from app.core.auth import CallerContext
from app.core.errors import ERRORS, FieldError, PublicError


class PostgresConversationQueries:
    """Read summaries without loading origins, message bodies, or peer receipts."""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def unread_count(self, caller: CallerContext) -> ConversationUnreadCount:
        """Aggregate only this authenticated member's unread peer messages."""
        caller.require_current()
        try:
            async with self._pool.connection() as connection:
                cursor = await connection.execute(
                    "SELECT count(*) FROM conversations.members member JOIN conversations.entries entry "
                    "ON entry.conversation_id = member.conversation_id WHERE member.user_id = %s "
                    "AND entry.sequence > member.last_read_sequence AND entry.kind IN ('message', 'contact_share') AND entry.sender_id <> member.user_id",
                    (caller.user_id,),
                )
                row = await cursor.fetchone()
                return ConversationUnreadCount(unread_count=row[0] if row else 0)
        except PsycopgError, PoolTimeout:
            raise PublicError(ERRORS[503]) from None

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
        if query.group_by:

            def key(row: ConversationSummary) -> str:
                return (
                    str(row.counterparty_user_id)
                    if query.group_by == "person"
                    else f"{row.origin_kind}:{row.origin_id}"
                )

            keys = list(dict.fromkeys(key(row) for row in rows))
            allowed = set(keys[: query.page_size])
            return PageResult[ConversationSummary](
                items=[row for row in rows if key(row) in allowed],
                page=query.page,
                page_size=query.page_size,
                has_next=len(keys) > query.page_size,
            )
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
        if query.marketplace_mode != "all":
            buying = "((thread.listing_id IS NOT NULL AND thread.initiator_id = member.user_id) OR (thread.wanted_request_id IS NOT NULL AND thread.counterparty_id = member.user_id))"
            predicates.append(
                buying if query.marketplace_mode == "buying" else f"NOT {buying}"
            )
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
            f"SELECT thread.id AS conversation_id, {origin_kind} AS origin_kind, {origin_id} AS origin_id, thread.initiator_id, "
            f"thread.initiator_id = member.user_id AS initiated, {peer} AS peer_id, thread.last_activity_at, "
            "member.last_read_sequence, (SELECT count(*) FROM conversations.entries AS entry "
            "WHERE entry.conversation_id = thread.id AND entry.kind IN ('message', 'contact_share') "
            "AND entry.sender_id <> member.user_id AND entry.sequence > member.last_read_sequence) AS unread_count, "
            "offer.id, revision.revision, revision.amount_paise, revision.status, revision.created_at, profile.handle, profile.account_class "
            "FROM conversations.threads AS thread JOIN conversations.members AS member "
            "ON member.conversation_id = thread.id "
            "LEFT JOIN conversations.offers AS offer ON offer.conversation_id = thread.id "
            "LEFT JOIN conversations.offer_revisions AS revision "
            "ON revision.offer_id = offer.id AND revision.revision = offer.current_revision "
            f"LEFT JOIN identity.participant_profiles profile ON profile.user_id = {peer} "
            f"WHERE {' AND '.join(predicates)} ORDER BY {ordering} LIMIT %s OFFSET %s"
        )
        if query.group_by and conversation_id is None:
            # Rank authorized groups before paging; at most twenty threads per
            # group are loaded. Thread continuation uses the ordinary filtered API.
            base = statement.rsplit(" ORDER BY ", 1)[0]
            parameters = parameters[:-2]
            grouping = (
                "peer_id::text"
                if query.group_by == "person"
                else "origin_kind || ':' || origin_id::text"
            )
            statement = (
                f"WITH base AS ({base}), keyed AS (SELECT base.*, {grouping} AS group_key FROM base), "
                "ranked AS (SELECT keyed.*, max(last_activity_at) OVER (PARTITION BY group_key) AS activity, "
                "row_number() OVER (PARTITION BY group_key ORDER BY last_activity_at DESC, conversation_id DESC) AS row_number, "
                "count(*) OVER (PARTITION BY group_key) AS group_size, "
                "sum(unread_count) OVER (PARTITION BY group_key) AS group_unread_count FROM keyed), "
                "paged AS (SELECT ranked.*, dense_rank() OVER (ORDER BY activity DESC, group_key DESC) AS group_number FROM ranked) "
                "SELECT * FROM paged WHERE group_number > %s AND group_number <= %s AND row_number <= 20 "
                "ORDER BY group_number, row_number"
            )
            parameters.extend(
                ((query.page - 1) * query.page_size, query.page * query.page_size + 1)
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
            group_has_more=len(row) > 16 and row[19] > 20,
            counterparty_handle=row[14],
            counterparty_account_class=row[15],
            group_unread_count=row[20] if len(row) > 20 else 0,
        )
