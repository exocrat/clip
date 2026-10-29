"""Bounded notification retention; no scheduler, CLI or automatic deletion."""

from dataclasses import dataclass
from datetime import timedelta

from psycopg_pool import AsyncConnectionPool

from app.contracts.domain_types import NotificationWorkerContext
from app.core.errors import ERRORS, PublicError
from app.domains.conversations.notifications.storage import PostgresNotificationDelivery


@dataclass(frozen=True)
class NotificationCleanupResult:
    """Return aggregate counts without intent, recipient or conversation IDs."""

    dry_run: bool
    eligible: int
    deleted: int


class NotificationCleanup:
    """Delete only expired terminal intents under the owning delivery locks."""

    def __init__(self, pool: AsyncConnectionPool, permit: object) -> None:
        """Bind trusted private dependencies; construction performs no work."""
        self._pool = pool
        self._delivery = PostgresNotificationDelivery(pool, permit)

    async def run(
        self,
        context: NotificationWorkerContext,
        *,
        apply: bool = False,
        batch_size: int = 100,
    ) -> NotificationCleanupResult:
        """Recheck up to 100 terminal rows; dry-run unless explicitly applied.

        Each candidate has a separate transaction. Errors never report a partial
        run as success; earlier commits may remain and a later run safely resumes.
        The server clock controls cutoff and expiry; clients cannot supply either.
        """
        self._delivery._authorize(context)
        if (
            type(apply) is not bool
            or type(batch_size) is not int
            or not 1 <= batch_size <= 100
        ):
            raise ValueError("Invalid notification cleanup options")
        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    await connection.execute("SET LOCAL statement_timeout='5s'")
                    now = (
                        await (
                            await connection.execute("SELECT clock_timestamp()")
                        ).fetchone()
                    )[0]
                    cutoff = now - timedelta(days=30)
                    rows = await (
                        await connection.execute(
                            "SELECT id FROM conversations.notification_intents WHERE state IN ('sent','suppressed','failed') "
                            "AND completed_at<=%s AND expires_at<=%s ORDER BY completed_at,id LIMIT %s",
                            (cutoff, now, batch_size),
                        )
                    ).fetchall()
            eligible = deleted = 0
            for (intent_id,) in rows:
                async with self._pool.connection() as connection:
                    async with connection.transaction():
                        await connection.execute("SET LOCAL lock_timeout='3s'")
                        await connection.execute("SET LOCAL statement_timeout='5s'")
                        locked = await self._delivery._locked(connection, intent_id)
                        if locked is None:
                            continue
                        row = await (
                            await connection.execute(
                                "SELECT state,completed_at,expires_at FROM conversations.notification_intents WHERE id=%s",
                                (intent_id,),
                            )
                        ).fetchone()
                        if (
                            row is None
                            or row[0] not in ("sent", "suppressed", "failed")
                            or row[1] is None
                            or row[1] > cutoff
                            or row[2] > now
                        ):
                            continue
                        eligible += 1
                        if apply:
                            cursor = await connection.execute(
                                "DELETE FROM conversations.notification_intents WHERE id=%s",
                                (intent_id,),
                            )
                            deleted += cursor.rowcount
            return NotificationCleanupResult(not apply, eligible, deleted)
        except Exception:
            raise PublicError(ERRORS[503]) from None
