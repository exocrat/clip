"""Bounded Identity-only retention, dry-run by default; no scheduler is enabled.

Preserve users, contacts, enrollment/operation lifetime markers and key bindings.
Each candidate is rechecked under compatible target/user locks in its own bounded
transaction. Explicit runtime target/apply approval is separate from this code.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from psycopg.pq import TransactionStatus

from app.core.errors import ERRORS, PublicError
from app.core.timestamps import as_utc
from app.domains.identity.temporary_challenges import (
    Database,
    PostgresTemporaryChallenges,
)


@dataclass(frozen=True)
class CleanupResult:
    """Counts only: no identifiers, targets, credential or ciphertext data."""

    dry_run: bool
    counts: dict[str, int]


class IdentityCleanup:
    """Apply approved retention to explicitly injected fresh connections/time."""

    def __init__(self, connect: Callable[[], Database], clock: Callable[[], datetime]):
        """Construction performs no database call or automatic cleanup."""
        self._connect = connect
        self._clock = clock

    def run(self, *, apply: bool = False, batch_size: int = 100) -> CleanupResult:
        """Select at most batch_size per table; default is count-only, never delete.

        Terminal credential hashes are immediately eligible so an approved hourly
        run can meet the within24-hour deadline. No schedule/deadline claim exists
        until deployment enables and verifies the separately approved job.
        """
        if type(batch_size) is not int or not 1 <= batch_size <= 1000:
            raise ValueError("Invalid cleanup batch")
        now = as_utc(self._clock())
        day = now - timedelta(hours=24)
        week = now - timedelta(days=7)
        # Fixed code-owned identifiers/conditions only; values are SQL parameters.
        rules = (
            (
                "otp_challenges",
                "id",
                "LEAST(expires_at,consumed_at,superseded_at)<=%s",
                day,
                "target_lookup_digest",
            ),
            (
                "sessions",
                "id",
                "LEAST(expires_at,revoked_at,last_seen_at+INTERVAL '24 hours')<=%s",
                week,
                "user_id",
            ),
            (
                "temporary_credentials",
                "user_id",
                "EXISTS(SELECT 1 FROM identity.users u WHERE u.id=user_id AND (u.status='revoked' OR (u.account_class='temporary' AND u.expires_at<=%s)))",
                now,
                "user_id",
            ),
            (
                "microsoft_login_attempts",
                "token_digest",
                "LEAST(expires_at,consumed_at)<=%s",
                day,
                None,
            ),
            (
                "auth_source_events",
                "id",
                "created_at<=%s",
                day - timedelta(minutes=15),
                None,
            ),
            (
                "otp_send_reservations",
                "challenge_id",
                "created_at<=%s",
                day - timedelta(hours=1),
                "target_digest",
            ),
        )
        counts = {}
        try:
            for table, identifier, condition, cutoff, lock_column in rules:
                extra = (
                    "," + lock_column
                    if lock_column and lock_column != identifier
                    else ""
                )
                with self._connect() as c:
                    self._fresh(c)
                    with c.transaction():
                        self._timeouts(c)
                        candidates = c.execute(
                            f"SELECT {identifier}{extra} FROM identity.{table} WHERE {condition} ORDER BY {identifier} LIMIT %s",
                            (cutoff, batch_size),
                        ).fetchall()
                count = 0
                for candidate in candidates:
                    if not apply:
                        count += 1
                        continue
                    with self._connect() as c:
                        self._fresh(c)
                        with c.transaction():
                            self._timeouts(c)
                            if lock_column == "user_id":
                                user = (
                                    candidate[0]
                                    if identifier == "user_id"
                                    else candidate[1]
                                )
                                c.execute(
                                    "SELECT id FROM identity.users WHERE id=%s FOR UPDATE",
                                    (user,),
                                )
                            elif lock_column:
                                PostgresTemporaryChallenges._lock(
                                    c, "otp-target", candidate[1]
                                )
                            result = c.execute(
                                f"DELETE FROM identity.{table} WHERE {identifier}=%s AND {condition} RETURNING {identifier}",
                                (candidate[0], cutoff),
                            ).fetchone()
                            count += int(result is not None)
                counts[table] = count
            # Composite window identities need all key columns; never drop a
            # replacement live window after a candidate was selected as expired.
            for table, purpose in (
                ("otp_verification_windows", True),
                ("password_login_windows", False),
            ):
                columns = "key_version,target_digest" + (",purpose" if purpose else "")
                with self._connect() as c:
                    self._fresh(c)
                    with c.transaction():
                        self._timeouts(c)
                        candidates = c.execute(
                            f"SELECT {columns} FROM identity.{table} WHERE expires_at<=%s ORDER BY {columns} LIMIT %s",
                            (day, batch_size),
                        ).fetchall()
                count = 0
                for row in candidates:
                    if not apply:
                        count += 1
                        continue
                    with self._connect() as c:
                        self._fresh(c)
                        with c.transaction():
                            self._timeouts(c)
                            PostgresTemporaryChallenges._lock(c, "otp-target", row[1])
                            where = "key_version=%s AND target_digest=%s" + (
                                " AND purpose=%s" if purpose else ""
                            )
                            result = c.execute(
                                f"DELETE FROM identity.{table} WHERE {where} AND expires_at<=%s RETURNING key_version",
                                (*row, day),
                            ).fetchone()
                            count += int(result is not None)
                counts[table] = count
            return CleanupResult(not apply, counts)
        except Exception:
            # A partially applied bounded run may have committed earlier items;
            # rerunning rechecks eligibility and is safe. Never claim all-or-none.
            raise PublicError(ERRORS[503]) from None

    @staticmethod
    def _fresh(c: Database) -> None:
        """Do not run destructive work inside an ambient caller transaction."""
        if c.info.transaction_status != TransactionStatus.IDLE:
            raise PublicError(ERRORS[503])

    @staticmethod
    def _timeouts(c: Database) -> None:
        """Bound retention locks/statements without changing global database state."""
        c.execute("SET LOCAL lock_timeout='3s'")
        c.execute("SET LOCAL statement_timeout='5s'")
