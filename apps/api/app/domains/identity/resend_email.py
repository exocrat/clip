"""Identity-owned bounded Resend HTTPS transport, currently controlled-recipient only.

No account creation, DNS modification, ambient credentials or real send on import
or construction. Production composition remains unavailable until reviewed runtime
configuration is implemented; this adapter never changes authentication state.
"""

import json
from typing import Any
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from pydantic import SecretStr

from app.domains.identity.email import EmailUnavailable
from app.domains.identity.temporary_crypto import normalize_login


class NoEmailRedirects(HTTPRedirectHandler):
    """Prevent API credentials/message bodies following a provider redirect."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        """Refuse every redirect; the only permitted endpoint is fixed below."""
        return None


class ResendEmailSender:
    """Single plain-text submission with no SDK retry and a private API key.

    Explicit recipient allowlist retains the staged Step2 boundary. Live setup and
    general delivery require separate provider/configuration acceptance. Use a
    sending-only, domain-restricted key loaded by trusted secret composition.
    """

    def __init__(self, api_key: SecretStr, recipients: tuple[str, ...]) -> None:
        """Validate private inputs; never log/serialize a credential or recipient."""
        key = api_key.get_secret_value()
        if (
            not key
            or len(key) > 512
            or not key.isascii()
            or any(ord(c) < 33 or ord(c) > 126 for c in key)
            or not 1 <= len(recipients) <= 5
            or any(normalize_login(value) != value for value in recipients)
        ):
            raise EmailUnavailable("Invalid controlled email configuration")
        self._key, self._recipients = api_key, frozenset(recipients)
        # Ignore ambient proxy configuration; retain default HTTPS certificate and
        # hostname verification. Refuse HTTP redirects and never retry POST.
        self._opener = build_opener(
            ProxyHandler({}), HTTPSHandler(), NoEmailRedirects()
        )

    def send(self, recipient: str, subject: str, body: str) -> None:
        """Submit once to the fixed TLS endpoint; accept only a bounded success ID.

        Eight-second socket timeout is not an absolute wall-clock deadline. HTTP,
        decoding, malformed success and network errors are all private uncertainty;
        the approved outer router alone may try the other provider once.
        """
        if (
            recipient not in self._recipients
            or not subject
            or len(subject) > 120
            or any(character in subject for character in "\r\n")
            or not body
            or len(body.encode("utf-8")) > 8192
        ):
            raise EmailUnavailable("Email dispatch refused")
        request = Request(
            "https://api.resend.com/emails",
            data=json.dumps(
                {
                    "from": "verify@clip-iisc.site",
                    "to": [recipient],
                    "subject": subject,
                    "text": body,
                }
            ).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + self._key.get_secret_value(),
                "Content-Type": "application/json",
                # Identify this API client explicitly; default urllib signatures
                # were rejected with HTTP403/edge1010 in the real local test.
                "User-Agent": "CLIP-Identity/0.1",
            },
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=8) as response:
                if response.status != 200:
                    raise ValueError
                raw = response.read(4097)
                if len(raw) > 4096:
                    raise ValueError
                value = json.loads(raw)
                if (
                    not isinstance(value, dict)
                    or not isinstance(value.get("id"), str)
                    or not 1 <= len(value["id"]) <= 128
                ):
                    raise ValueError
        except Exception:
            raise EmailUnavailable(
                "Email submission unavailable or uncertain"
            ) from None
