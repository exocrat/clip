"""Pure OTP limits; the owning transactional store must serialize every update.

These immutable values do not enforce database atomicity or send email. Failed
verifications survive resends until the newest code expires. Persistence and
real integration remain required before this policy can protect a public route.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from app.core.timestamps import as_utc

OTP_LIFETIME = timedelta(minutes=10)
RESEND_COOLDOWN = timedelta(seconds=60)
TARGET_SENDS_PER_HOUR = 6
SOURCE_SENDS_PER_HOUR = 100
MAX_FAILURES = 3


class VerificationLimited(ValueError):
    """The target/purpose has exhausted its current verification window."""


@dataclass(frozen=True)
class VerificationWindow:
    """Target/purpose failure budget, expiring with its latest issued OTP.

    Callers must persist this record under the same lock as challenge issuance
    or verification. Resends preserve failures; only expiry resets the budget.
    """

    expires_at: datetime
    failures: int = 0

    def __post_init__(self) -> None:
        """Reject naive time and impossible persisted failure counts."""
        object.__setattr__(self, "expires_at", as_utc(self.expires_at))
        if type(self.failures) is not int or not 0 <= self.failures <= MAX_FAILURES:
            raise ValueError("Invalid verification window")

    def require_available(self, now: datetime) -> None:
        """Reject an exhausted live window, including for resend requests."""
        if as_utc(now) < self.expires_at and self.failures == MAX_FAILURES:
            raise VerificationLimited("Verification limit reached")

    def resend(self, now: datetime) -> "VerificationWindow":
        """Start a new ten-minute code without clearing a live failure budget."""
        instant = as_utc(now)
        self.require_available(instant)
        return VerificationWindow(
            instant + OTP_LIFETIME,
            self.failures if instant < self.expires_at else 0,
        )

    def failed(self, now: datetime) -> "VerificationWindow":
        """Charge one incorrect verification; expired codes cannot extend a window."""
        instant = as_utc(now)
        if instant >= self.expires_at:
            raise ValueError("Challenge expired")
        self.require_available(instant)
        return replace(self, failures=self.failures + 1)
