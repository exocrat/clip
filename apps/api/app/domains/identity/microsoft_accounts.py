"""Identity-owned PostgreSQL account mapping, with no session/HTTP side effects."""

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Callable
from uuid import UUID

from psycopg import Connection
from psycopg.pq import TransactionStatus

from app.core.errors import ERRORS, PublicError
from app.core.identifiers import new_id
from app.domains.identity.microsoft import MicrosoftIdentity, MicrosoftTokenValidator


@dataclass(frozen=True)
class RegularAccount:
    """Minimal account result, not an authenticated CallerContext or session."""

    user_id: UUID
    display_name: str | None = field(repr=False)


class PostgresMicrosoftAccounts:
    """Use a caller-owned trusted connection factory; never discover a DB target.

    All writes occur in one transaction under a deterministic advisory lock for
    provider/issuer/subject. Concurrent callbacks use one mapping and account;
    uniqueness is still enforced by PostgreSQL. Token/email/nonce are not stored.
    """

    def __init__(self, connect: Callable[[], Connection[tuple[Any, ...]]]) -> None:
        """Bind fresh private connections without opening one during construction."""
        self._connect = connect

    def get_or_create(self, identity: MicrosoftIdentity) -> RegularAccount:
        """Create/retrieve an active regular account; never reactivate/prompt login."""
        try:
            with self._connect() as connection:
                if connection.info.transaction_status != TransactionStatus.IDLE:
                    raise PublicError(ERRORS[503])
                with connection.transaction():
                    return self.get_or_create_in(connection, identity)
        except PublicError:
            raise
        except Exception:
            raise PublicError(ERRORS[503]) from None

    @staticmethod
    def get_or_create_in(
        connection: Connection[tuple[Any, ...]], identity: MicrosoftIdentity
    ) -> RegularAccount:
        """Compose mapping inside the trusted caller's account/session transaction.

        Caller owns commit/rollback; validated identity is required. Provider-tuple
        advisory lock precedes account lock. No session or raw assertion is stored.
        """
        binding = json.dumps(
            ["microsoft", identity.issuer, identity.subject], separators=(",", ":")
        )
        lock = int.from_bytes(
            hashlib.sha256(binding.encode()).digest()[:8], "big", signed=True
        )
        connection.execute("SET LOCAL lock_timeout = '3s'")
        connection.execute("SET LOCAL statement_timeout = '5s'")
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (lock,))
        row = connection.execute(
            "SELECT u.id, u.display_name, u.account_class, u.status, u.profile_removed_at "
            "FROM identity.external_identities AS e JOIN identity.users AS u ON u.id = e.user_id "
            "WHERE e.provider = %s AND e.issuer = %s AND e.subject = %s FOR UPDATE OF u",
            ("microsoft", identity.issuer, identity.subject),
        ).fetchone()
        if row is not None:
            if row[2] != "regular" or row[3] != "active" or row[4] is not None:
                raise PublicError(ERRORS[401])
            return RegularAccount(row[0], row[1])
        user_id = new_id()
        connection.execute(
            "INSERT INTO identity.users (id, account_class, status) VALUES (%s, 'regular', 'active')",
            (user_id,),
        )
        connection.execute(
            "INSERT INTO identity.external_identities (id, user_id, provider, issuer, subject) "
            "VALUES (%s, %s, 'microsoft', %s, %s)",
            (new_id(), user_id, identity.issuer, identity.subject),
        )
        return RegularAccount(user_id, None)


class MicrosoftAccountService:
    """Compose real validation and mapping; does not issue cookies or callers."""

    def __init__(
        self, validator: MicrosoftTokenValidator, accounts: PostgresMicrosoftAccounts
    ) -> None:
        """Require explicit private dependencies; construction performs no I/O."""
        self._validator = validator
        self._accounts = accounts

    def authenticate(self, token: str, *, expected_nonce: str) -> RegularAccount:
        """Validate first so rejected/provider-failed tokens cannot create rows."""
        identity = self._validator.verify(token, expected_nonce=expected_nonce)
        return self._accounts.get_or_create(identity)
