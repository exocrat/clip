"""Private, one-shot OTP delivery using the reviewed SES transport.

The future transactional challenge store must commit its reservation before
calling ``dispatch``. This module owns no database or public route. Tickets stay
in process memory: raw codes must never be serialized, queued, logged or stored.
Public acceptance must not depend on account eligibility or delivery outcome.
"""

from dataclasses import dataclass, field
from datetime import datetime
import secrets
from threading import Lock
from typing import Protocol
from uuid import UUID

from app.core.timestamps import as_utc
from app.domains.identity.temporary_crypto import TemporaryKeys, normalize_login


class EmailSender(Protocol):
    """Identity-private narrow transport implemented by SesEmailSender."""

    def send(self, recipient: str, subject: str, body: str) -> None:
        """Submit once; acceptance cannot establish inbox delivery."""
        ...


class OtpDelivery:
    """Hold one transient code and allow at most one transport attempt.

    A timeout may follow provider acceptance, so a failed/uncertain attempt burns
    the ticket too. Concurrent calls cannot send twice. Durable operation-ID
    deduplication must additionally be enforced by the transactional store.
    """

    def __init__(self, email: str, code: str, purpose: str, expires_at: datetime):
        """Create only from trusted challenge preparation, before persistence."""
        TemporaryKeys._purpose(purpose)
        if len(code) != 6 or not code.isascii() or not code.isdecimal():
            raise ValueError("Invalid code format")
        self._email: str | None = normalize_login(email)
        self._code: str | None = code
        self._purpose = purpose
        self._expires_at = as_utc(expires_at)
        self._lock = Lock()

    def discard(self) -> None:
        """Release references when a duplicate or ineligible reservation suppresses send."""
        with self._lock:
            self._email = None
            self._code = None

    def dispatch(self, sender: EmailSender, *, now: datetime) -> bool:
        """Attempt once after commit; return submission status, never delivery proof.

        Provider errors are reduced to false without exception text or logging.
        The owning service must keep this result private and use the same generic
        acknowledgement for eligible and ineligible targets. No retry is made.
        """
        instant = as_utc(now)
        with self._lock:
            email, code = self._email, self._code
            self._email = None
            self._code = None
        if email is None or code is None or instant >= self._expires_at:
            return False
        action = (
            "verify your temporary CLIP account"
            if self._purpose == "initial_verification"
            else "reset your temporary CLIP account password"
        )
        body = (
            f"Use {code} to {action}.\n"
            "This code expires ten minutes after it was requested. "
            "Only the newest code works.\n"
            "If you did not request this, ignore this message. "
            "Do not share this code."
        )
        try:
            sender.send(email, "CLIP temporary account verification", body)
            return True
        except Exception:
            # Custom transports must be as private as the SES adapter; never
            # propagate raw SDK/provider/user values into API errors or logs.
            return False


@dataclass(frozen=True)
class ProtectedChallenge:
    """Explicit persistence fields plus a transient ticket that must stay private.

    Store only the named protected fields, never serialize this object wholesale.
    Its ticket must be discarded unless this is a newly committed, eligible
    reservation. Consuming verification and account mutation belong to later
    transactional service wiring; this record alone grants no authority.
    """

    challenge_id: UUID
    purpose: str
    expires_at: datetime
    key_version: str
    target_digest: bytes = field(repr=False)
    encrypted_target: bytes = field(repr=False)
    verifier: bytes = field(repr=False)
    delivery: OtpDelivery = field(repr=False, compare=False)


def prepare_challenge(
    keys: TemporaryKeys,
    email: str,
    challenge_id: UUID,
    purpose: str,
    expires_at: datetime,
) -> ProtectedChallenge:
    """Generate six uniform decimal digits, retaining only a transient send ticket.

    Identity's owning transaction must enforce the ten-minute lifetime, send
    limits, current eligibility and operation deduplication before committing.
    Preparation performs no I/O and creates no user, session or enrollment guard.
    """
    target = keys.target_digest(email)
    expiry = as_utc(expires_at)
    code = f"{secrets.randbelow(1_000_000):06d}"
    return ProtectedChallenge(
        challenge_id=challenge_id,
        purpose=purpose,
        expires_at=expiry,
        key_version=keys.version,
        target_digest=target,
        encrypted_target=keys.encrypt_target(email, challenge_id, purpose, expiry),
        verifier=keys.otp_verifier(code, challenge_id, purpose, target, expiry),
        delivery=OtpDelivery(email, code, purpose, expiry),
    )
