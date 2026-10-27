"""Bounded, owner-local conversation retention; no scheduler or HTTP endpoint."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.core.errors import ERRORS, PublicError
from app.core.timestamps import as_utc


@dataclass(frozen=True)
class ConversationCleanupResult:
    """Aggregate counts only; omit user/thread IDs and all retained content."""

    dry_run: bool
    threads: int
    entries: int


@dataclass(frozen=True)
class ContactShareCleanupResult:
    """Aggregate counts only for independently expired contact-share payloads."""

    dry_run: bool
    contact_shares: int
    entries: int


class ConversationCleanup:
    """Purge inactive content atomically per thread, preserving integrity guards.

    Production time comes from PostgreSQL. The optional trusted clock supports
    deterministic disposable-database checks; the CLI never accepts a cutoff.
    Earlier thread transactions may commit before a later failure; reruns safely
    resume. The batch limits threads, while each thread is processed all-or-none.
    """

    def __init__(
        self,
        pool: AsyncConnectionPool,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Retain injected resources without starting any database work."""
        self._pool = pool
        self._clock = clock

    async def run(
        self, *, apply: bool = False, batch_size: int = 100
    ) -> ConversationCleanupResult:
        """Inspect at most 1–1000 inactive threads; mutate only with apply=True.

        Candidate selection is advisory. Every candidate is locked and checked
        again before counting/purging, using the same thread lock as participant
        writes. Reads and cleanup never update participant activity or sequences.
        """
        if type(batch_size) is not int or not 1 <= batch_size <= 1000:
            raise ValueError("Invalid cleanup batch")
        if type(apply) is not bool:
            raise ValueError("Invalid cleanup mode")
        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    await self._timeouts(connection)
                    row = await (
                        await connection.execute("SELECT clock_timestamp()")
                    ).fetchone()
                    if row is None:
                        raise RuntimeError("Database clock unavailable")
                    now = as_utc(self._clock() if self._clock else row[0])
                    cutoff = now - timedelta(days=90)
                    cursor = await connection.execute(
                        "SELECT t.id FROM conversations.threads t "
                        "WHERE t.last_activity_at <= %s AND EXISTS "
                        "(SELECT 1 FROM conversations.entries e "
                        "WHERE e.conversation_id=t.id AND e.content_deleted_at IS NULL) "
                        "ORDER BY t.id LIMIT %s",
                        (cutoff, batch_size),
                    )
                    candidates = await cursor.fetchall()
            threads = entries = 0
            for (thread_id,) in candidates:
                count = await self._purge_thread(thread_id, cutoff, now, apply)
                threads += int(count > 0)
                entries += count
            return ConversationCleanupResult(not apply, threads, entries)
        except Exception:
            # Do not expose SQL, driver detail, DSNs or content. Earlier threads
            # may have committed: an error is never reported as empty success.
            raise PublicError(ERRORS[503]) from None

    async def run_contact_shares(
        self, *, apply: bool = False, batch_size: int = 100
    ) -> ContactShareCleanupResult:
        """Expire each share at 30 days, locking its thread and preserving its entry."""
        if type(batch_size) is not int or not 1 <= batch_size <= 1000:
            raise ValueError("Invalid cleanup batch")
        if type(apply) is not bool:
            raise ValueError("Invalid cleanup mode")
        try:
            async with self._pool.connection() as connection:
                async with connection.transaction():
                    await self._timeouts(connection)
                    row = await (
                        await connection.execute("SELECT clock_timestamp()")
                    ).fetchone()
                    if row is None:
                        raise RuntimeError("Database clock unavailable")
                    now = as_utc(self._clock() if self._clock else row[0])
                    cutoff = now - timedelta(days=30)
                    rows = await (
                        await connection.execute(
                            "SELECT e.id, e.conversation_id FROM conversations.entries e "
                            "JOIN conversations.contact_shares s ON s.entry_id=e.id "
                            "WHERE e.kind='contact_share' AND e.content_deleted_at IS NULL "
                            "AND e.created_at <= %s ORDER BY e.id LIMIT %s",
                            (cutoff, batch_size),
                        )
                    ).fetchall()
            count = 0
            for entry_id, thread_id in rows:
                if await self._expire_contact_share(
                    entry_id, thread_id, cutoff, now, apply
                ):
                    count += 1
            return ContactShareCleanupResult(not apply, count, count)
        except Exception:
            raise PublicError(ERRORS[503]) from None

    async def _expire_contact_share(
        self,
        entry_id: UUID,
        thread_id: UUID,
        cutoff: datetime,
        now: datetime,
        apply: bool,
    ) -> bool:
        """Recheck the per-share deadline after taking the participant-write lock."""
        async with self._pool.connection() as connection:
            async with connection.transaction():
                await self._timeouts(connection)
                thread = await (
                    await connection.execute(
                        "SELECT id FROM conversations.threads WHERE id=%s FOR UPDATE",
                        (thread_id,),
                    )
                ).fetchone()
                if thread is None:
                    return False
                entry = await (
                    await connection.execute(
                        "SELECT created_at FROM conversations.entries WHERE id=%s "
                        "AND conversation_id=%s AND kind='contact_share' AND content_deleted_at IS NULL "
                        "FOR UPDATE",
                        (entry_id, thread_id),
                    )
                ).fetchone()
                if entry is None or entry[0] > cutoff:
                    return False
                if apply:
                    await self._delete_contact_share(connection, entry_id, now)
                return True

    @staticmethod
    async def _delete_contact_share(
        connection: AsyncConnection, entry_id: UUID, now: datetime
    ) -> None:
        """Remove ciphertext/subtype and set its content-free marker atomically."""
        await connection.execute(
            "DELETE FROM conversations.encrypted_payloads WHERE entry_id=%s",
            (entry_id,),
        )
        await connection.execute(
            "DELETE FROM conversations.contact_shares WHERE entry_id=%s", (entry_id,)
        )
        await connection.execute(
            "UPDATE conversations.entries SET content_deleted_at=%s "
            "WHERE id=%s AND content_deleted_at IS NULL",
            (now, entry_id),
        )

    @staticmethod
    async def _timeouts(connection: AsyncConnection) -> None:
        """Bound lock and SQL waits even on an unexpectedly large thread."""
        await connection.execute("SET LOCAL lock_timeout = '2s'")
        await connection.execute("SET LOCAL statement_timeout = '10s'")

    async def _purge_thread(
        self, thread_id: UUID, cutoff: datetime, now: datetime, apply: bool
    ) -> int:
        """Recheck activity under the participant-write lock; preserve every ID."""
        async with self._pool.connection() as connection:
            async with connection.transaction():
                await self._timeouts(connection)
                row = await (
                    await connection.execute(
                        "SELECT last_activity_at FROM conversations.threads "
                        "WHERE id=%s FOR UPDATE",
                        (thread_id,),
                    )
                ).fetchone()
                if row is None or row[0] > cutoff:
                    return 0
                row = await (
                    await connection.execute(
                        "SELECT count(*) FROM conversations.entries "
                        "WHERE conversation_id=%s AND content_deleted_at IS NULL",
                        (thread_id,),
                    )
                ).fetchone()
                if row is None:
                    raise RuntimeError("Content inventory unavailable")
                if apply and row[0]:
                    await self._purge_content(connection, thread_id, now)
                return int(row[0])

    async def _purge_content(
        self, connection: AsyncConnection, thread_id: UUID, now: datetime
    ) -> None:
        """Remove the subtype graph in FK-safe order inside the thread transaction.

        Deferred constraints verify the final graph at commit. Contact-share links
        on these 90-day-inactive threads are already beyond their 30-day lifetime;
        independent 30-day cleanup remains CN-02 work. Notification/recovery
        references, read state, keys and operation/sequence guards are retained.
        """
        await connection.execute(
            "UPDATE conversations.offers SET current_revision=NULL, "
            "history_deleted_at=%s WHERE conversation_id=%s "
            "AND history_deleted_at IS NULL",
            (now, thread_id),
        )
        await connection.execute(
            "DELETE FROM conversations.offer_revisions r USING conversations.offers o "
            "WHERE r.offer_id=o.id AND o.conversation_id=%s",
            (thread_id,),
        )
        for table in ("encrypted_payloads", "contact_shares"):
            # Table names are fixed code-owned identifiers, never user input.
            await connection.execute(
                f"DELETE FROM conversations.{table} p USING conversations.entries e "
                "WHERE p.entry_id=e.id AND e.conversation_id=%s",
                (thread_id,),
            )
        await connection.execute(
            "UPDATE conversations.entries SET content_deleted_at=%s "
            "WHERE conversation_id=%s AND content_deleted_at IS NULL",
            (now, thread_id),
        )
