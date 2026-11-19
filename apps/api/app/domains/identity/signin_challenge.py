"""Bounded, fail-closed Turnstile verification for exceptional public authentication attempts.

The challenge is not authentication. Only normal credential/nonce validation can
issue a session. Ordinary sign-ins never call this external provider.
"""

import json
import re
import ssl
from urllib.parse import urlencode, urlsplit
from urllib.request import (
    HTTPSHandler,
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from pydantic import SecretStr

from app.core.errors import ERRORS, PublicError

SITEVERIFY = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
ACTION = "clip_signin"


class NoRedirect(HTTPRedirectHandler):
    """Never forward a provider secret or challenge to a redirected endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class TurnstileVerifier:
    """Use a fixed TLS endpoint, bounded reply and deadline; retain no tokens."""

    def __init__(self, site_key: str, secret: SecretStr, origins: tuple[str, ...]):
        """Bind backend-only secret and exact hostnames from trusted browser policy."""
        if not re.fullmatch(r"[A-Za-z0-9_-]{10,256}", site_key):
            raise ValueError("Invalid Turnstile site key")
        self.site_key = site_key
        self._secret = secret
        self._hosts = {urlsplit(origin).hostname for origin in origins}

    def verify(self, token: str) -> None:
        """Reject invalid/expired/wrong-site proofs; hide all provider diagnostics."""
        if not token or len(token) > 2048 or not token.isascii():
            raise PublicError(ERRORS[429])
        try:
            opener = build_opener(
                ProxyHandler({}),
                NoRedirect(),
                HTTPSHandler(context=ssl.create_default_context()),
            )
            request = Request(
                SITEVERIFY,
                data=urlencode(
                    {"secret": self._secret.get_secret_value(), "response": token}
                ).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with opener.open(request, timeout=3) as response:
                raw = response.read(16385)
                if response.status != 200 or len(raw) > 16384:
                    raise ValueError
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError
        except Exception:
            raise PublicError(ERRORS[503]) from None
        if (
            result.get("success") is not True
            or result.get("hostname") not in self._hosts
            or result.get("action") != ACTION
        ):
            raise PublicError(ERRORS[429])
