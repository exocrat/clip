"""Conversations-owned, transactionally fenced notification delivery state."""

from datetime import timedelta
from uuid import uuid4

from psycopg import Error as PsycopgError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.contracts.domain_types import (
    NotificationAttemptResult,
    NotificationClaim,
    NotificationClaimRequest,
    NotificationClaimResult,
    NotificationDispatchCheck,
    NotificationDispatchContext,
    NotificationIntentState,
    NotificationWorkerContext,
)
from app.core.errors import ERRORS, PublicError
from app.core.runtime_bindings import runtime_claim

LEASE = timedelta(seconds=60)
BACKOFF = (
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
)


class PostgresNotificationDelivery:
    """Own claims and state transitions; no Identity tables or provider access."""

    def __init__(self, pool: AsyncConnectionPool, permit: object) -> None:
        """Accept only explicitly composed pool and trusted worker permit."""
        if permit is None:
            raise ValueError("Worker permit required")
        self._pool, self._permit = pool, permit

    def _authorize(self, context: NotificationWorkerContext) -> None:
        """Marker construction alone never authorizes access to private jobs."""
        if (
            not isinstance(context, NotificationWorkerContext)
            or runtime_claim("conversations.notification_worker") is not self._permit
        ):
            raise PublicError(ERRORS[403])

    @staticmethod
    async def _locked(connection, intent_id):
        """Lock thread, member then job to match producer/read lock order."""
        row = await (
            await connection.execute(
                "SELECT conversation_id,recipient_id FROM conversations.notification_intents WHERE id=%s",
                (intent_id,),
            )
        ).fetchone()
        if row is None:
            return None
        conversation_id, recipient_id = row
        await connection.execute(
            "SELECT id FROM conversations.threads WHERE id=%s FOR UPDATE",
            (conversation_id,),
        )
        member = await (
            await connection.execute(
                "SELECT last_read_sequence,reminder_episode_start_sequence,reminder_sent_at FROM conversations.members WHERE conversation_id=%s AND user_id=%s FOR UPDATE",
                (conversation_id, recipient_id),
            )
        ).fetchone()
        job = await (
            await connection.execute(
                "SELECT id,conversation_id,recipient_id,event_kind,due_at,expires_at,state,attempts,lease_token,lease_until,unread_episode_start_sequence,unread_through_sequence,next_attempt_at,dispatch_started_at,last_result_token,last_result_outcome FROM conversations.notification_intents WHERE id=%s FOR UPDATE",
                (intent_id,),
            )
        ).fetchone()
        return (job, member) if job is not None and member is not None else None

    @staticmethod
    def _read(job, member) -> bool:
        """True means the original unread episode is no longer eligible."""
        return job[3] == "unread_reminder" and (
            member[1] != job[10] or member[2] is not None
        )

    async def claim_due_notification_intents(
        self, context: NotificationWorkerContext, request: NotificationClaimRequest
    ) -> NotificationClaimResult:
        """Lease due work in bounded batches, recovering expired fenced claims."""
        self._authorize(context)
        claims = []
        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    await connection.execute("SET LOCAL lock_timeout='3s'")
                    now = (
                        await (
                            await connection.execute("SELECT clock_timestamp()")
                        ).fetchone()
                    )[0]
                    rows = await (
                        await connection.execute(
                            "SELECT id,conversation_id,recipient_id FROM conversations.notification_intents WHERE "
                            "(state='pending' OR (state='leased' AND lease_until<=%s)) "
                            "AND due_at<=%s AND (next_attempt_at IS NULL OR next_attempt_at<=%s) "
                            "ORDER BY due_at,id LIMIT %s",
                            (now, now, now, request.max_items),
                        )
                    ).fetchall()
                    # Select by due time, but lock every batch in a common order.
                    for intent_id, _, _ in sorted(
                        rows, key=lambda row: (row[1], row[2], row[0])
                    ):
                        locked = await self._locked(connection, intent_id)
                        if locked is None:
                            continue
                        job, member = locked
                        if (
                            job[6] not in ("pending", "leased")
                            or (job[6] == "leased" and job[9] > now)
                            or (job[12] is not None and job[12] > now)
                        ):
                            continue
                        if job[5] <= now or job[7] >= 5 or self._read(job, member):
                            terminal = (
                                "suppressed" if self._read(job, member) else "failed"
                            )
                            await connection.execute(
                                "UPDATE conversations.notification_intents SET state=%s,completed_at=%s,lease_token=NULL,lease_until=NULL,dispatch_started_at=NULL,updated_at=%s WHERE id=%s",
                                (terminal, now, now, intent_id),
                            )
                            continue
                        if job[6] == "leased" and job[13] is not None:
                            if job[7] < 1:
                                raise PublicError(ERRORS[503])
                            retry_at = job[13] + BACKOFF[job[7] - 1]
                            if retry_at > now:
                                await connection.execute(
                                    "UPDATE conversations.notification_intents SET state='pending',lease_token=NULL,lease_until=NULL,dispatch_started_at=NULL,next_attempt_at=%s,updated_at=%s WHERE id=%s",
                                    (retry_at, now, intent_id),
                                )
                                continue
                        token = uuid4()
                        lease_until = min(now + LEASE, job[5])
                        await connection.execute(
                            "UPDATE conversations.notification_intents SET state='leased',lease_token=%s,lease_until=%s,dispatch_started_at=NULL,next_attempt_at=NULL,updated_at=%s WHERE id=%s",
                            (token, lease_until, now, intent_id),
                        )
                        claims.append(
                            NotificationClaim(
                                intent_id=intent_id,
                                conversation_id=job[1],
                                recipient_id=job[2],
                                event_kind=job[3],
                                due_at=job[4],
                                target_sequence=job[11],
                                fencing_token=token,
                                lease_expires_at=lease_until,
                            )
                        )
        except PsycopgError, PoolTimeout:
            raise PublicError(ERRORS[503]) from None
        return NotificationClaimResult(claims=claims)

    async def read_notification_dispatch_context(
        self, context: NotificationWorkerContext, request: NotificationDispatchCheck
    ) -> NotificationDispatchContext:
        """Fence a single dispatch reservation against current member read state."""
        self._authorize(context)
        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    await connection.execute("SET LOCAL lock_timeout='3s'")
                    now = (
                        await (
                            await connection.execute("SELECT clock_timestamp()")
                        ).fetchone()
                    )[0]
                    locked = await self._locked(connection, request.intent_id)
                    if locked is None:
                        return NotificationDispatchContext(decision="defer")
                    job, member = locked
                    if (
                        job[6] != "leased"
                        or job[8] != request.fencing_token
                        or job[9] <= now
                        or job[5] <= now
                        or job[13] is not None
                    ):
                        return NotificationDispatchContext(decision="defer")
                    if self._read(job, member):
                        await connection.execute(
                            "UPDATE conversations.notification_intents SET state='suppressed',completed_at=%s,lease_token=NULL,lease_until=NULL,updated_at=%s WHERE id=%s",
                            (now, now, job[0]),
                        )
                        return NotificationDispatchContext(decision="suppress")
                    await connection.execute(
                        "UPDATE conversations.notification_intents SET attempts=attempts+1,dispatch_started_at=%s,updated_at=%s WHERE id=%s",
                        (now, now, job[0]),
                    )
                    return NotificationDispatchContext(
                        decision="send", recipient_id=job[2], target_sequence=job[11]
                    )
        except PsycopgError, PoolTimeout:
            raise PublicError(ERRORS[503]) from None

    async def record_notification_attempt(
        self, context: NotificationWorkerContext, request: NotificationAttemptResult
    ) -> NotificationIntentState:
        """Apply one fenced outcome, with bounded retry and duplicate acknowledgement."""
        self._authorize(context)
        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    await connection.execute("SET LOCAL lock_timeout='3s'")
                    now = (
                        await (
                            await connection.execute("SELECT clock_timestamp()")
                        ).fetchone()
                    )[0]
                    locked = await self._locked(connection, request.intent_id)
                    if locked is None:
                        raise PublicError(ERRORS[409])
                    job, member = locked
                    if job[14] == request.fencing_token and job[15] == request.outcome:
                        return NotificationIntentState(
                            state={"sent": "delivered", "failed": "terminal"}.get(
                                job[6], job[6]
                            ),
                            attempt_count=job[7],
                        )
                    if request.outcome == "preference_suppressed":
                        if (
                            job[6] != "leased"
                            or job[8] != request.fencing_token
                            or job[9] <= now
                        ):
                            raise PublicError(ERRORS[409])
                        await connection.execute(
                            "UPDATE conversations.notification_intents SET state='suppressed',completed_at=%s,lease_token=NULL,lease_until=NULL,dispatch_started_at=NULL,last_result_token=%s,last_result_outcome=%s,updated_at=%s WHERE id=%s",
                            (now, request.fencing_token, request.outcome, now, job[0]),
                        )
                        return NotificationIntentState(
                            state="suppressed", attempt_count=job[7]
                        )
                    if (
                        job[6] != "leased"
                        or job[8] != request.fencing_token
                        or job[9] <= now
                        or job[13] is None
                    ):
                        raise PublicError(ERRORS[409])
                    if request.outcome == "delivered":
                        state, retry_at = "sent", None
                        if (
                            job[3] == "unread_reminder"
                            and member[1] == job[10]
                            and member[2] is None
                        ):
                            await connection.execute(
                                "UPDATE conversations.members SET reminder_sent_at=%s WHERE conversation_id=%s AND user_id=%s",
                                (now, job[1], job[2]),
                            )
                    elif request.outcome == "terminal_failure" or job[7] >= 5:
                        state, retry_at = "failed", None
                    else:
                        retry_at = now + BACKOFF[job[7] - 1]
                        state = "failed" if retry_at >= job[5] else "pending"
                        if state == "failed":
                            retry_at = None
                    await connection.execute(
                        "UPDATE conversations.notification_intents SET state=%s,completed_at=%s,next_attempt_at=%s,lease_token=NULL,lease_until=NULL,dispatch_started_at=NULL,last_result_token=%s,last_result_outcome=%s,updated_at=%s WHERE id=%s",
                        (
                            state,
                            now if state != "pending" else None,
                            retry_at,
                            request.fencing_token,
                            request.outcome,
                            now,
                            job[0],
                        ),
                    )
                    return NotificationIntentState(
                        state={"sent": "delivered", "failed": "terminal"}.get(
                            state, state
                        ),
                        attempt_count=job[7],
                    )
        except PsycopgError, PoolTimeout:
            raise PublicError(ERRORS[503]) from None
