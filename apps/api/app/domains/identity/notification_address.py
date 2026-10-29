"""Protect an account's login destination for the notification recipient port.

This module performs no persistence, logging, provider calls or key discovery.
"""

from dataclasses import dataclass, field
import asyncio
from collections.abc import Callable
from datetime import datetime
import json
import secrets
from uuid import UUID

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.domains.identity.temporary_crypto import TemporaryKeys
from app.contracts.domain_types import NotificationRecipient, NotificationWorkerContext
from app.core.errors import ERRORS, PublicError
from app.core.runtime_bindings import runtime_claim
from app.core.timestamps import as_utc
from app.domains.identity.capabilities import PostgresCapabilities


def _normalize_address(email: str) -> str:
    """Accept validated login addresses without making Microsoft sign-in stricter."""
    if (
        not isinstance(email, str)
        or not 3 <= len(email) <= 254
        or not email.isascii()
        or email.count("@") != 1
        or any(c.isspace() or ord(c) < 33 or c in '<>"(),;:\\' for c in email)
    ):
        raise ValueError("Invalid notification address")
    local, domain = email.split("@")
    if (
        not local
        or not domain
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
    ):
        raise ValueError("Invalid notification address")
    return email.lower()


@dataclass(frozen=True)
class NotificationAddressCipher:
    """Derive a distinct purpose key and bind each ciphertext to its account.

    The supplied key version must remain available for decrypting stored rows;
    key rotation requires a separately reviewed migration/re-encryption plan.
    """

    keys: TemporaryKeys = field(repr=False)

    def _key(self) -> bytes:
        """Derive an independent AES-256 key from the existing protected key."""
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"clip-notification-address-v1",
        ).derive(self.keys.target_encryption)

    def _aad(self, user_id: UUID) -> bytes:
        """Prevent copying a ciphertext to a different user or key version."""
        if not isinstance(user_id, UUID) or user_id.version != 4:
            raise ValueError("Invalid account")
        return json.dumps(
            ["clip-notification-address-v1", self.keys.version, str(user_id)],
            separators=(",", ":"),
        ).encode()

    def encrypt(self, user_id: UUID, email: str) -> bytes:
        """Encrypt a normalized login address with a fresh random nonce."""
        value = _normalize_address(email)
        nonce = secrets.token_bytes(12)
        return nonce + AESGCM(self._key()).encrypt(
            nonce, value.encode(), self._aad(user_id)
        )

    def decrypt(self, user_id: UUID, ciphertext: bytes, version: str) -> str:
        """Authenticate a stored address; reject wrong account, key or version."""
        if version != self.keys.version or len(ciphertext) < 29:
            raise ValueError("Notification address unavailable")
        value = (
            AESGCM(self._key())
            .decrypt(ciphertext[:12], ciphertext[12:], self._aad(user_id))
            .decode()
        )
        if _normalize_address(value) != value:
            raise ValueError("Notification address unavailable")
        return value

    def save_in(self, connection, user_id: UUID, email: str) -> None:
        """Store only ciphertext in the caller's existing account transaction."""
        encrypted = self.encrypt(user_id, email)
        connection.execute(
            "INSERT INTO identity.notification_destinations(user_id,ciphertext,key_version) "
            "VALUES (%s,%s,%s) ON CONFLICT(user_id) DO UPDATE SET "
            "ciphertext=EXCLUDED.ciphertext,key_version=EXCLUDED.key_version,updated_at=clock_timestamp()",
            (user_id, encrypted, self.keys.version),
        )


class NotificationRecipientResolver:
    """Resolve one Identity-owned recipient only under a trusted worker claim."""

    def __init__(
        self,
        connect: Callable,
        clock: Callable[[], datetime],
        keys: TemporaryKeys,
        permit: object,
    ):
        """Bind private dependencies and a server-held permit, without opening a DB."""
        if permit is None:
            raise ValueError("Worker permit required")
        self._connect, self._clock = connect, clock
        self._cipher, self._permit = NotificationAddressCipher(keys), permit

    async def resolve(
        self, context: NotificationWorkerContext, recipient_id: UUID
    ) -> NotificationRecipient | None:
        """Return a current eligible login address; never expose it to HTTP callers."""
        if (
            not isinstance(context, NotificationWorkerContext)
            or runtime_claim("identity.notification_worker") is not self._permit
        ):
            raise PublicError(ERRORS[403])

        def read():
            try:
                with self._connect() as c:
                    row = c.execute(
                        "SELECT u.account_class,u.status,u.created_at,u.activated_at,u.expires_at,u.profile_removed_at,"
                        "n.ciphertext,n.key_version FROM identity.users u LEFT JOIN identity.notification_destinations n ON n.user_id=u.id WHERE u.id=%s",
                        (recipient_id,),
                    ).fetchone()
                    if (
                        not PostgresCapabilities._active(row, as_utc(self._clock()))
                        or row[6] is None
                    ):
                        return None
                    return NotificationRecipient(
                        recipient_id=recipient_id,
                        email=self._cipher.decrypt(recipient_id, bytes(row[6]), row[7]),
                    )
            except Exception:
                raise PublicError(ERRORS[503]) from None

        return await asyncio.to_thread(read)

    async def allows(self, recipient_id: UUID) -> bool:
        """Check fresh account eligibility and email preference for trusted worker use."""
        if runtime_claim("identity.notification_worker") is not self._permit:
            raise PublicError(ERRORS[403])

        def read():
            try:
                with self._connect() as c:
                    row = c.execute(
                        "SELECT account_class,status,created_at,activated_at,expires_at,profile_removed_at,conversation_email_enabled FROM identity.users WHERE id=%s",
                        (recipient_id,),
                    ).fetchone()
                    return bool(
                        PostgresCapabilities._active(row, as_utc(self._clock()))
                        and row[6]
                    )
            except Exception:
                raise PublicError(ERRORS[503]) from None

        return await asyncio.to_thread(read)
