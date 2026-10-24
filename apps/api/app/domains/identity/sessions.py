"""Real opaque sessions and credential exchanges; transport is in http.py.

Locks serialize source→target→user→session for temporary credentials; Microsoft
attempt→provider tuple→user for its final redemption. Never persist raw cookie,
password, nonce or assertion. Secrets in return objects are transport-only.
"""

import base64
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import hmac
from ipaddress import IPv4Address, IPv6Address
import secrets
from typing import Any, Callable, Iterator
from uuid import UUID

from psycopg.pq import TransactionStatus
from pydantic import SecretStr

from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
from app.core.identifiers import new_id
from app.core.timestamps import as_utc
from app.domains.identity.microsoft import MicrosoftTokenValidator
from app.domains.identity.microsoft_accounts import PostgresMicrosoftAccounts
from app.domains.identity.temporary_accounts import TemporaryActivation
from app.domains.identity.temporary_challenges import (
    Database,
    PostgresTemporaryChallenges,
    VerifiedOtp,
)
from app.domains.identity.temporary_crypto import TemporaryKeys, normalize_login
from app.domains.identity.temporary_passwords import TemporaryPasswords

ABSOLUTE = timedelta(days=7)
IDLE = timedelta(hours=24)
LOGIN_WINDOW = timedelta(minutes=15)
ATTEMPT_LIFETIME = timedelta(minutes=10)


def token_bytes(value: str | None) -> bytes:
    """Accept only canonical32-byte unpadded URL-safe secrets; hide bad values."""
    try:
        if not isinstance(value, str) or len(value) != 43:
            raise ValueError
        decoded = base64.urlsafe_b64decode(value + "=")
        if (
            len(decoded) != 32
            or base64.urlsafe_b64encode(decoded).decode().rstrip("=") != value
        ):
            raise ValueError
        return decoded
    except Exception:
        raise PublicError(ERRORS[401]) from None


def digest(value: str, purpose: str) -> bytes:
    """Domain-separate high-entropy cookie digests without a new static secret."""
    return hashlib.sha256(purpose.encode() + b":" + token_bytes(value)).digest()


def bound_value(value: str, purpose: str) -> str:
    """Derive a nonce/CSRF value without storing/revealing the cookie secret."""
    return hmac.digest(
        token_bytes(value), ("clip-" + purpose + "-v1").encode(), "sha256"
    ).hex()


@dataclass(frozen=True)
class SessionIdentity:
    """Server-established current facts, not client-supplied authorization."""

    caller: CallerContext
    session_id: UUID
    display_name: str | None = field(repr=False)


@dataclass(frozen=True)
class SessionGrant:
    """One transport-only cookie secret; serialize only identity's public fields."""

    identity: SessionIdentity
    token: SecretStr = field(repr=False)
    expires_at: datetime


@dataclass(frozen=True)
class LoginAttempt:
    """Public nonce/expiry paired with a private browser-binding cookie."""

    nonce: str = field(repr=False)
    expires_at: datetime
    token: SecretStr = field(repr=False)


class IdentitySessions:
    """Own transactional authentication, reset and revocation for HTTP composition."""

    def __init__(
        self,
        connect: Callable[[], Database],
        keys: TemporaryKeys,
        clock: Callable[[], datetime],
    ):
        """Bind explicit trusted dependencies and prepare real dummy Argon2 work."""
        self._connect = connect
        self._keys = keys
        self._clock = clock
        self.challenges = PostgresTemporaryChallenges(connect, keys, clock)
        self._activation = TemporaryActivation(self.challenges)
        self._passwords = TemporaryPasswords()
        self._dummy = self._passwords.hash(SecretStr(secrets.token_urlsafe(32)))

    @contextmanager
    def transaction(self) -> Iterator[Database]:
        """Require fresh connections, bounded SQL and unchanged protected keys."""
        try:
            with self._connect() as c:
                if c.info.transaction_status != TransactionStatus.IDLE:
                    raise PublicError(ERRORS[503])
                with c.transaction():
                    self.challenges._begin(c)
                    yield c
        except PublicError:
            raise
        except Exception:
            raise PublicError(ERRORS[503]) from None

    def _source(
        self, c: Database, address: IPv4Address | IPv6Address, now: datetime
    ) -> None:
        """Reserve every credential/attempt request under its trusted source lock."""
        source = self._keys.source_digest(address)
        self.challenges._lock(c, "auth-source", source)
        count = c.execute(
            "SELECT count(*) FROM identity.auth_source_events WHERE source_digest=%s AND created_at>%s",
            (source, now - LOGIN_WINDOW),
        ).fetchone()
        if count is None or count[0] >= 100:
            raise PublicError(ERRORS[429])
        c.execute(
            "INSERT INTO identity.auth_source_events(id,source_digest,created_at) VALUES (%s,%s,%s)",
            (new_id(), source, now),
        )

    @staticmethod
    def _account(c: Database, user: UUID, now: datetime) -> tuple[Any, ...]:
        """Lock and validate current user before any session read/write."""
        row = c.execute(
            "SELECT account_class,status,expires_at,profile_removed_at,display_name,activated_at FROM identity.users WHERE id=%s FOR UPDATE",
            (user,),
        ).fetchone()
        if (
            row is None
            or row[1] != "active"
            or row[3] is not None
            or (
                row[0] == "temporary"
                and (row[2] is None or row[5] is None or not row[5] <= now < row[2])
            )
        ):
            raise PublicError(ERRORS[401])
        return row

    def _issue(self, c: Database, user: UUID, now: datetime) -> SessionGrant:
        """Create a fresh capped session inside the owning account transaction."""
        row = self._account(c, user, now)
        expires = (
            min(now + ABSOLUTE, row[2]) if row[0] == "temporary" else now + ABSOLUTE
        )
        token = secrets.token_urlsafe(32)
        identifier = new_id()
        c.execute(
            "INSERT INTO identity.sessions(id,user_id,token_digest,created_at,expires_at,last_seen_at) VALUES (%s,%s,%s,%s,%s,%s)",
            (identifier, user, digest(token, "clip-session-v1"), now, expires, now),
        )
        identity = SessionIdentity(
            CallerContext(user, row[0], min(expires, now + IDLE)), identifier, row[4]
        )
        return SessionGrant(identity, SecretStr(token), expires)

    def activate(
        self, challenge_id: UUID, code: str, password: SecretStr
    ) -> SessionGrant:
        """Commit initial OTP, account/guard/password and first session together."""
        return self._activation.activate_with(
            challenge_id,
            code,
            password,
            lambda c, a: self._issue(c, a.user_id, a.activated_at),
        )

    def password_login(
        self, email: str, password: SecretStr, source: IPv4Address | IPv6Address
    ) -> SessionGrant:
        """Uniform real/dummy hash work; commit failed counters before401/429."""
        try:
            target = self._keys.target_digest(normalize_login(email))
            self._keys.source_digest(source)
        except ValueError:
            raise PublicError(ERRORS[422]) from None
        outcome = 401
        with self.transaction() as c:
            now = as_utc(self._clock())
            self._source(c, source, now)
            self.challenges._lock(c, "otp-target", target)
            now = as_utc(self._clock())
            prior = c.execute(
                "SELECT expires_at,failures FROM identity.password_login_windows WHERE key_version=%s AND target_digest=%s FOR UPDATE",
                (self._keys.version, target),
            ).fetchone()
            if prior is not None and now < prior[0] and prior[1] >= 5:
                outcome = 429
            else:
                row = c.execute(
                    "SELECT u.id,u.status,u.expires_at,u.profile_removed_at,t.password_hash,u.account_class FROM identity.temporary_credentials t JOIN identity.users u ON u.id=t.user_id WHERE t.login_email_key=%s FOR UPDATE OF u",
                    (self._keys.credential_key(email),),
                ).fetchone()
                eligible = (
                    row is not None
                    and row[1] == "active"
                    and row[2] is not None
                    and now < row[2]
                    and row[3] is None
                    and row[5] == "temporary"
                )
                valid = self._passwords.verify(
                    row[4] if eligible and row is not None else self._dummy, password
                )
                if eligible and valid and row is not None:
                    return self._issue(c, row[0], as_utc(self._clock()))
                failures = prior[1] + 1 if prior is not None and now < prior[0] else 1
                expires = (
                    prior[0]
                    if prior is not None and now < prior[0]
                    else now + LOGIN_WINDOW
                )
                c.execute(
                    "INSERT INTO identity.password_login_windows(key_version,target_digest,expires_at,failures) VALUES (%s,%s,%s,%s) ON CONFLICT(key_version,target_digest) DO UPDATE SET expires_at=EXCLUDED.expires_at,failures=EXCLUDED.failures",
                    (self._keys.version, target, expires, failures),
                )
        raise PublicError(ERRORS[outcome])

    def reset_password(
        self, challenge_id: UUID, code: str, password: SecretStr
    ) -> None:
        """Change password/consume OTP/revoke sessions atomically; never renew or login."""
        self._passwords.validate(password)

        def apply(c: Database, proof: VerifiedOtp) -> None:
            if proof.user_id is None:
                raise PublicError(ERRORS[422])
            encoded = self._passwords.hash(password)
            c.execute(
                "UPDATE identity.temporary_credentials SET password_hash=%s,password_changed_at=%s,revision=revision+1 WHERE user_id=%s",
                (encoded, proof.verified_at, proof.user_id),
            )
            c.execute(
                "UPDATE identity.sessions SET revoked_at=%s WHERE user_id=%s AND revoked_at IS NULL",
                (proof.verified_at, proof.user_id),
            )

        self.challenges.consume(challenge_id, "password_reset", code, apply)

    def authenticate(self, token: str | None) -> SessionIdentity:
        """Read fresh current user/session and renew idle time only while valid."""
        value = digest(token or "", "clip-session-v1")
        with self.transaction() as c:
            initial = c.execute(
                "SELECT id,user_id FROM identity.sessions WHERE token_digest=%s",
                (value,),
            ).fetchone()
            if initial is None:
                raise PublicError(ERRORS[401])
            # Account-before-session matches reset/revocation and cleanup ordering.
            now = as_utc(self._clock())
            account = self._account(c, initial[1], now)
            row = c.execute(
                "SELECT expires_at,revoked_at,last_seen_at,created_at FROM identity.sessions WHERE id=%s FOR UPDATE",
                (initial[0],),
            ).fetchone()
            now = as_utc(self._clock())
            if (
                row is None
                or row[1] is not None
                or row[2] is None
                or not row[3] <= now < min(row[0], row[2] + IDLE)
                or (account[0] == "temporary" and now >= account[2])
            ):
                raise PublicError(ERRORS[401])
            c.execute(
                "UPDATE identity.sessions SET last_seen_at=%s WHERE id=%s",
                (now, initial[0]),
            )
            deadline = (
                min(row[0], now + IDLE, account[2])
                if account[0] == "temporary"
                else min(row[0], now + IDLE)
            )
            return SessionIdentity(
                CallerContext(initial[1], account[0], deadline), initial[0], account[4]
            )

    def logout(self, token: str | None) -> None:
        """Revoke the current known session idempotently; missing/expired is401."""
        value = digest(token or "", "clip-session-v1")
        with self.transaction() as c:
            initial = c.execute(
                "SELECT id,user_id FROM identity.sessions WHERE token_digest=%s",
                (value,),
            ).fetchone()
            if initial is None:
                raise PublicError(ERRORS[401])
            now = as_utc(self._clock())
            self._account(c, initial[1], now)
            row = c.execute(
                "SELECT expires_at,last_seen_at,created_at FROM identity.sessions WHERE id=%s FOR UPDATE",
                (initial[0],),
            ).fetchone()
            if (
                row is None
                or row[1] is None
                or not row[2] <= now < min(row[0], row[1] + IDLE)
            ):
                raise PublicError(ERRORS[401])
            c.execute(
                "UPDATE identity.sessions SET revoked_at=COALESCE(revoked_at,%s) WHERE id=%s",
                (now, initial[0]),
            )

    def revoke_account(self, user: UUID) -> None:
        """Trusted internal revocation, serialized with login; no public admin surface."""
        with self.transaction() as c:
            row = c.execute(
                "SELECT id FROM identity.users WHERE id=%s FOR UPDATE", (user,)
            ).fetchone()
            if row is None:
                raise PublicError(ERRORS[404])
            now = as_utc(self._clock())
            c.execute(
                "UPDATE identity.users SET status='revoked',revoked_at=COALESCE(revoked_at,%s) WHERE id=%s",
                (now, user),
            )
            c.execute(
                "UPDATE identity.sessions SET revoked_at=COALESCE(revoked_at,%s) WHERE user_id=%s",
                (now, user),
            )

    def start_microsoft(self, source: IPv4Address | IPv6Address) -> LoginAttempt:
        """Persist only a digest for a ten-minute browser-bound one-use login attempt."""
        with self.transaction() as c:
            now = as_utc(self._clock())
            self._source(c, source, now)
            token = secrets.token_urlsafe(32)
            expires = now + ATTEMPT_LIFETIME
            c.execute(
                "INSERT INTO identity.microsoft_login_attempts(token_digest,created_at,expires_at) VALUES (%s,%s,%s)",
                (digest(token, "clip-ms-attempt-v1"), now, expires),
            )
            return LoginAttempt(
                bound_value(token, "microsoft-nonce"), expires, SecretStr(token)
            )

    def microsoft_exchange(
        self,
        token: SecretStr,
        attempt: str | None,
        source: IPv4Address | IPv6Address,
        validator: MicrosoftTokenValidator,
    ) -> SessionGrant:
        """Validate outside final transaction, then consume attempt/map/session atomically."""
        try:
            value = digest(attempt or "", "clip-ms-attempt-v1")
        except PublicError:
            value = None
        with self.transaction() as c:
            now = as_utc(self._clock())
            self._source(c, source, now)
            row = (
                c.execute(
                    "SELECT created_at,expires_at,consumed_at FROM identity.microsoft_login_attempts WHERE token_digest=%s",
                    (value,),
                ).fetchone()
                if value is not None
                else None
            )
            usable = row is not None and row[2] is None and row[0] <= now < row[1]
        if not usable or value is None or attempt is None:
            raise PublicError(ERRORS[401])
        identity = validator.verify(
            token.get_secret_value(),
            expected_nonce=bound_value(attempt, "microsoft-nonce"),
        )
        with self.transaction() as c:
            row = c.execute(
                "SELECT created_at,expires_at,consumed_at FROM identity.microsoft_login_attempts WHERE token_digest=%s FOR UPDATE",
                (value,),
            ).fetchone()
            now = as_utc(self._clock())
            if row is None or row[2] is not None or not row[0] <= now < row[1]:
                raise PublicError(ERRORS[401])
            account = PostgresMicrosoftAccounts.get_or_create_in(c, identity)
            grant = self._issue(c, account.user_id, now)
            c.execute(
                "UPDATE identity.microsoft_login_attempts SET consumed_at=%s WHERE token_digest=%s",
                (now, value),
            )
            return grant
