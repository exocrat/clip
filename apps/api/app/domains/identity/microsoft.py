"""Private Microsoft v2 token validation; never creates a browser session.

Only the production factory uses public Microsoft discovery/JWKS. Test injection
supplies real synthetic RSA keys, never an authentication bypass in API wiring.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import secrets
import ssl
import threading
import time
from typing import Any, Callable, Protocol
from urllib.request import HTTPSHandler, HTTPRedirectHandler, ProxyHandler, build_opener
from uuid import UUID

import jwt

from app.core.config import Settings
from app.core.errors import ERRORS, PublicError

CLIENT_ID = "ab3a63e3-d4db-4c3c-b4bf-ac5f7573ffbb"
DISCOVERY = (
    "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"
)
JWKS = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
ISSUER = "https://login.microsoftonline.com/{tenantid}/v2.0"


@dataclass(frozen=True)
class MicrosoftIdentity:
    """Verified claims for private account mapping, not a session/caller context."""

    issuer: str = field(repr=False)
    subject: str = field(repr=False)
    email: str | None = field(repr=False)
    expires_at: datetime = field(repr=False)


class KeySource(Protocol):
    """Resolve only an RSA signing key bound to the expected Microsoft issuer."""

    def resolve(self, kid: str, issuer: str) -> jwt.PyJWK: ...


class NoRedirects(HTTPRedirectHandler):
    """Do not follow provider redirects to another origin or arbitrary URL."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def fetch_document(url: str) -> dict[str, Any]:
    """Read bounded public metadata over verified TLS without ambient proxies.

    No token, destination, credentials or URL derived from JWT input is sent.
    Socket timeout is three seconds; this is not an overall DNS/request deadline.
    """
    if url not in (DISCOVERY, JWKS):
        raise PublicError(ERRORS[503])
    try:
        opener = build_opener(
            ProxyHandler({}),
            HTTPSHandler(context=ssl.create_default_context()),
            NoRedirects(),
        )
        with opener.open(url, timeout=3) as response:
            data = response.read(262145)
        if len(data) > 262144:
            raise ValueError("Oversized metadata")
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError("Invalid metadata")
        return value
    except Exception:
        raise PublicError(ERRORS[503]) from None


class MicrosoftKeys:
    """Bounded shared metadata cache with key-issuer binding and refresh control.

    Cache lifetime is five minutes; unknown kids may trigger one refresh at most
    every30 seconds. An expired cache/provider failure fails closed. One lock
    coalesces concurrent lookups. No credentials or token bodies are cached.
    """

    def __init__(
        self,
        load: Callable[[str], dict[str, Any]] = fetch_document,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Bind transport/clock; construction makes no network call."""
        self._load = load
        self._clock = clock
        self._keys: list[dict[str, Any]] = []
        self._loaded_at = float("-inf")
        self._attempted_at = float("-inf")
        self._lock = threading.Lock()

    def _refresh(self, moment: float) -> None:
        """Validate fixed discovery/key documents before replacing the cache."""
        self._attempted_at = moment
        try:
            discovery = self._load(DISCOVERY)
            if (
                discovery.get("issuer") != ISSUER
                or discovery.get("jwks_uri") != JWKS
                or "RS256"
                not in discovery.get("id_token_signing_alg_values_supported", [])
            ):
                raise ValueError("Untrusted discovery")
            keys = self._load(JWKS).get("keys")
            if not isinstance(keys, list) or not 1 <= len(keys) <= 128:
                raise ValueError("Invalid keys")
            if not all(isinstance(key, dict) for key in keys):
                raise ValueError("Invalid key record")
            self._keys = keys
            self._loaded_at = moment
        except Exception:
            raise PublicError(ERRORS[503]) from None

    def resolve(self, kid: str, issuer: str) -> jwt.PyJWK:
        """Select one signing key whose own issuer matches the token tenant."""
        with self._lock:
            moment = self._clock()
            if moment - self._loaded_at >= 300:
                if moment - self._attempted_at < 30:
                    raise PublicError(ERRORS[503])
                self._refresh(moment)
            matches = [key for key in self._keys if key.get("kid") == kid]
            if not matches and moment - self._attempted_at >= 30:
                self._refresh(moment)
                matches = [key for key in self._keys if key.get("kid") == kid]
            if len(matches) != 1:
                raise PublicError(ERRORS[401])
            key = matches[0]
            if (
                key.get("kty") != "RSA"
                or key.get("use") != "sig"
                or key.get("alg", "RS256") != "RS256"
                or key.get("issuer") not in (ISSUER, issuer)
            ):
                raise PublicError(ERRORS[401])
            try:
                return jwt.PyJWK.from_dict(key, algorithm="RS256")
            except Exception:
                raise PublicError(ERRORS[503]) from None


class MicrosoftTokenValidator:
    """Verify a Microsoft v2 assertion before applying the exact-domain policy.

    expected_nonce must come from a trusted server-bound login attempt, never
    from a browser-supplied expected value. Attempt creation/consumption, PKCE,
    state and session issuance are separate gates before any HTTP wiring.
    """

    def __init__(self, keys: KeySource) -> None:
        """Inject a key resolver; actual application selection uses from_settings."""
        self._keys = keys

    @classmethod
    def from_settings(cls, settings: Settings) -> "MicrosoftTokenValidator":
        """Keep this incomplete private integration unavailable in production."""
        if (
            settings.identity_provider != "microsoft"
            or settings.environment == "production"
        ):
            raise PublicError(ERRORS[503])
        return cls(MicrosoftKeys())

    def verify(self, token: str, *, expected_nonce: str) -> MicrosoftIdentity:
        """Return minimal verified evidence or generic401/503, never JWT details."""
        try:
            if (
                not isinstance(token, str)
                or not 1 <= len(token) <= 16384
                or not isinstance(expected_nonce, str)
                or not 16 <= len(expected_nonce) <= 512
            ):
                raise ValueError("Invalid assertion input")
            header = jwt.get_unverified_header(token)
            if (
                header.get("alg") != "RS256"
                or header.get("typ") != "JWT"
                or "crit" in header
            ):
                raise ValueError("Unsupported token header")
            kid = header.get("kid")
            if not isinstance(kid, str) or not 1 <= len(kid) <= 256:
                raise ValueError("Invalid key identifier")
            # Untrusted tid is used only to construct an expected issuer from a
            # UUID. It never selects a network URL, user or authorization outcome.
            untrusted = jwt.decode(token, options={"verify_signature": False})
            tenant = untrusted.get("tid")
            if not isinstance(tenant, str) or str(UUID(tenant)) != tenant:
                raise ValueError("Invalid tenant identifier")
            issuer = ISSUER.replace("{tenantid}", tenant)
            key = self._keys.resolve(kid, issuer)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                audience=CLIENT_ID,
                issuer=issuer,
                options={
                    "require": [
                        "exp",
                        "iat",
                        "iss",
                        "aud",
                        "sub",
                        "tid",
                        "ver",
                        "nonce",
                    ],
                    "strict_aud": True,
                },
                leeway=0,
            )
            if claims["ver"] != "2.0" or claims["tid"] != tenant:
                raise ValueError("Invalid token version/tenant")
            if any(type(claims[name]) is not int for name in ("exp", "iat")):
                raise ValueError("Invalid numeric date")
            if "nbf" in claims and type(claims["nbf"]) is not int:
                raise ValueError("Invalid numeric date")
            if claims["exp"] <= claims["iat"]:
                raise ValueError("Invalid token lifetime")
            subject = claims["sub"]
            nonce = claims["nonce"]
            if not isinstance(subject, str) or not 1 <= len(subject) <= 255:
                raise ValueError("Invalid subject")
            if not isinstance(nonce, str) or not secrets.compare_digest(
                nonce, expected_nonce
            ):
                raise ValueError("Invalid nonce")
            # The owner's Entra test tenant may use its onmicrosoft.com users
            # as regular accounts. Match the signed tenant and exact username
            # domain; never infer membership from an unsigned token or email alone.
            username = claims.get("preferred_username")
            object_id = claims.get("oid")
            test_identity = (
                tenant == "19d07278-f040-4722-8202-b1174cf3a4d3"
                and isinstance(object_id, str)
                and str(UUID(object_id)) == object_id
                and isinstance(username, str)
                and username.isascii()
                and username.count("@") == 1
                and bool(username.split("@")[0])
                and "#" not in username
                and not any(c.isspace() or ord(c) < 33 for c in username)
                and username.split("@")[1].lower() == "medheadityagmail.onmicrosoft.com"
            )
            email = claims.get("email")
            if email is None and test_identity:
                pass
            else:
                if (
                    not isinstance(email, str)
                    or not 3 <= len(email) <= 254
                    or not email.isascii()
                    or any(
                        c.isspace() or ord(c) < 33 or c in '<>"(),;:\\' for c in email
                    )
                    or email.count("@") != 1
                ):
                    raise ValueError("Invalid email")
                local, domain = email.split("@")
                if (
                    not local
                    or local.startswith(".")
                    or local.endswith(".")
                    or ".." in local
                    or (domain.lower() != "iisc.ac.in" and not test_identity)
                ):
                    raise ValueError("Ineligible email domain")
            return MicrosoftIdentity(
                issuer, subject, email, datetime.fromtimestamp(claims["exp"], UTC)
            )
        except PublicError:
            raise
        except Exception:
            raise PublicError(ERRORS[401]) from None
