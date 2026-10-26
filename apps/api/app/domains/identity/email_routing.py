"""Private bounded real-provider failover and four-hour runtime refresh.

Trusted composition supplies a loader that reads approved live configuration and
credentials. No environment, SSM lookup, provider construction or send occurs on
import. This component alone does not enable any deployed email path.
"""

from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Callable, Literal

from app.domains.identity.email import EmailUnavailable
from app.domains.identity.temporary_delivery import EmailSender

REFRESH_SECONDS = 4 * 60 * 60


@dataclass(frozen=True)
class EmailRoute:
    """One atomic configuration snapshot; provider objects may contain secrets.

    A new snapshot replaces order and credentials together. A send keeps its
    snapshot even when another thread refreshes, so it never mixes revisions.
    """

    primary: Literal["resend", "ses"]
    resend: EmailSender = field(repr=False)
    ses: EmailSender = field(repr=False)

    def __post_init__(self) -> None:
        """Reject an unknown selector or accidentally reused provider object."""
        if self.primary not in ("resend", "ses") or self.resend is self.ses:
            raise ValueError("Invalid email route")


class RefreshingEmailSender:
    """Refresh on first use and first send after four hours, once per process.

    A failed/invalid refresh sends nothing rather than using expired settings.
    Trusted loader I/O is serialized; actual sends do not hold the refresh lock.
    There is no polling thread, persisted message, automatic retry or fake fallback.
    """

    def __init__(
        self, load: Callable[[], EmailRoute], clock: Callable[[], float] = monotonic
    ) -> None:
        """Bind explicit live loader and monotonic clock; construction performs no I/O."""
        self._load, self._clock = load, clock
        self._lock = Lock()
        self._route: EmailRoute | None = None
        self._expires = 0.0

    def _snapshot(self) -> EmailRoute:
        """Publish only a complete successful revision, redacting loader failures."""
        with self._lock:
            now = self._clock()
            if self._route is not None and now < self._expires:
                return self._route
            try:
                route = self._load()
                if not isinstance(route, EmailRoute):
                    raise ValueError
            except Exception:
                raise EmailUnavailable("Email configuration unavailable") from None
            self._route = route
            self._expires = self._clock() + REFRESH_SECONDS
            return route

    def warmup(self) -> None:
        """Validate/cache startup configuration without submitting any message.

        A successful load starts the same four-hour lifetime used by normal sends;
        no credential, recipient or provider snapshot is returned to the caller.
        """
        self._snapshot()

    def send(self, recipient: str, subject: str, body: str) -> None:
        """Try primary once, then other provider once on any reported failure.

        The identical message/OTP is reused, including after uncertain timeouts;
        both providers may therefore deliver. Success means provider acceptance,
        never inbox proof. No retry loop, third attempt or new OTP is generated.
        The owning OtpDelivery ticket still permits just one dispatch of this pair.
        """
        route = self._snapshot()
        ordered = (
            (route.resend, route.ses)
            if route.primary == "resend"
            else (route.ses, route.resend)
        )
        for sender in ordered:
            try:
                sender.send(recipient, subject, body)
                return
            except Exception:
                # Raw exceptions may contain addresses, bodies, keys or provider data.
                pass
        raise EmailUnavailable("Email submission unavailable or uncertain") from None
