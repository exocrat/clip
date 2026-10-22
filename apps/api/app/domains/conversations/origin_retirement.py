"""Conversations-owned database operations for origin-retirement coordination."""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from psycopg import Error as PsycopgError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import (
    OriginActivityRequest,
    OriginActivityResult,
    OriginOwnerContext,
    OriginRetirementCommand,
    RetirementMarkerResult,
)
from app.core.errors import ERRORS, PublicError

_ORIGIN_COLUMNS = {
    "sale_listing": "listing_id",
    "wanted_request": "wanted_request_id",
}
_DATABASE_ORIGIN_KINDS = {
    "sale_listing": "listing",
    "wanted_request": "wanted_request",
}


class PostgresOriginRetirementOperations:
    """Implement the two retirement callables owned by Conversations.

    The service reads and writes only Conversations-owned tables. Its trusted
    origin context is injected by server-side domain composition; constructing
    that context is not an authentication mechanism. Every mutating operation
    is transactional, and unknown database outcomes raise a safe dependency
    error so callers keep their origin pending and retry the same operation ID.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        """Retain the process pool; connections remain owned per operation."""
        self._pool = pool

    @staticmethod
    def _require_matching_origin(context: OriginOwnerContext, origin_kind: str) -> str:
        """Ensure the server-bound owner context matches the request kind."""
        if context.origin_kind != origin_kind:
            raise PublicError(ERRORS[403])
        return _ORIGIN_COLUMNS[origin_kind]

    @staticmethod
    def _dependency_unavailable() -> PublicError:
        """Return a generic error without exposing driver, SQL, or DSN details."""
        return PublicError(ERRORS[503])

    async def get_origin_activity(
        self, context: OriginOwnerContext, request: OriginActivityRequest
    ) -> OriginActivityResult:
        """Return only thread count and latest activity for one server-bound origin."""
        column = self._require_matching_origin(context, request.origin_kind)
        query = (
            "SELECT count(*)::integer, max(last_activity_at) "
            f"FROM conversations.threads WHERE {column} = %s"
        )
        try:
            async with self._pool.connection() as connection:
                cursor = await connection.execute(query, (request.origin_id,))
                row = await cursor.fetchone()
        except PsycopgError, PoolTimeout:
            raise self._dependency_unavailable() from None
        if row is None:
            # An aggregate must always produce a row; missing state is not zero.
            raise self._dependency_unavailable()
        thread_count, latest_activity = row
        return OriginActivityResult(
            thread_count=thread_count,
            latest_participant_write_at=latest_activity,
        )

    async def mark_origin_retired(
        self, context: OriginOwnerContext, request: OriginRetirementCommand
    ) -> RetirementMarkerResult:
        """Lock, recheck, and mark all eligible threads atomically and idempotently."""
        column = self._require_matching_origin(context, request.origin_kind)
        database_kind = _DATABASE_ORIGIN_KINDS[request.origin_kind]
        thread_query = (
            "SELECT id, last_activity_at, participant_writes_blocked_at "
            f"FROM conversations.threads WHERE {column} = %s ORDER BY id FOR UPDATE"
        )

        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    # Serialize concurrent retries of this global operation ID.
                    # A hash collision only serializes unrelated calls; the
                    # operation table's primary key remains the correctness guard.
                    await connection.execute(
                        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                        (str(request.operation_id),),
                    )
                    cursor = await connection.execute(
                        "SELECT origin_kind, origin_id, cutoff_utc, outcome, marked_count "
                        "FROM conversations.origin_retirement_operations "
                        "WHERE operation_id = %s",
                        (request.operation_id,),
                    )
                    prior = await cursor.fetchone()
                    if prior is not None:
                        (
                            prior_kind,
                            prior_origin,
                            prior_cutoff,
                            prior_outcome,
                            marked_count,
                        ) = prior
                        if (
                            prior_kind != database_kind
                            or prior_origin != request.origin_id
                            or prior_cutoff != request.cutoff_utc
                        ):
                            raise PublicError(ERRORS[409])
                        return RetirementMarkerResult(
                            outcome=cast(
                                Literal[
                                    "marked",
                                    "blocked_recent_activity",
                                    "already_marked",
                                ],
                                prior_outcome,
                            ),
                            marked_count=marked_count,
                        )

                    cursor = await connection.execute(
                        thread_query, (request.origin_id,)
                    )
                    rows: Sequence[tuple[UUID, datetime, datetime | None]] = (
                        await cursor.fetchall()
                    )
                    marked_before = sum(row[2] is not None for row in rows)
                    if marked_before not in (0, len(rows)):
                        # A partial marker must be reconciled, never completed
                        # opportunistically by a new retirement request.
                        raise PublicError(ERRORS[409])

                    outcome: Literal[
                        "marked", "blocked_recent_activity", "already_marked"
                    ]
                    if rows and marked_before == len(rows):
                        # `marked_count` reports the all-existing marked set.
                        outcome = "already_marked"
                        marked_count = marked_before
                    elif any(activity > request.cutoff_utc for _, activity, _ in rows):
                        outcome = "blocked_recent_activity"
                        marked_count = 0
                    else:
                        outcome = "marked"
                        marked_count = 0
                        for thread_id, _, _ in rows:
                            await connection.execute(
                                "UPDATE conversations.threads "
                                "SET participant_writes_blocked_at = clock_timestamp() "
                                "WHERE id = %s AND participant_writes_blocked_at IS NULL",
                                (thread_id,),
                            )
                            marked_count += 1

                    await connection.execute(
                        "INSERT INTO conversations.origin_retirement_operations "
                        "(operation_id, origin_kind, origin_id, cutoff_utc, outcome, marked_count) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            request.operation_id,
                            database_kind,
                            request.origin_id,
                            request.cutoff_utc,
                            outcome,
                            marked_count,
                        ),
                    )
                    return RetirementMarkerResult(
                        outcome=outcome,
                        marked_count=marked_count,
                    )
        except PublicError:
            raise
        except PsycopgError, PoolTimeout:
            raise self._dependency_unavailable() from None
