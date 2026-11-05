"""Private transactional OTP service; no public route, account activation or session.

Fresh trusted connections, keys, time and parsed source addresses are injected.
Every participant (including later activation/reset/login code) must respect the
same target-before-user lock order. Delivery is a separate post-commit action;
HTTP wiring must acknowledge uniformly before dispatch to avoid enumeration.
"""

from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import hmac
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Callable, TypeVar
from uuid import UUID

from psycopg import Connection
from psycopg.pq import TransactionStatus

from app.core.errors import ERRORS, PublicError
from app.core.identifiers import new_id
from app.core.timestamps import as_utc
from app.core.sql_bounds import IDENTITY_BOUNDS_SQL
from app.domains.identity.temporary_crypto import TemporaryKeys, normalize_login
from app.domains.identity.temporary_delivery import OtpDelivery, prepare_challenge
from app.domains.identity.temporary_policy import (
    OTP_LIFETIME,
    RESEND_COOLDOWN,
    SOURCE_SENDS_PER_HOUR,
    TARGET_SENDS_PER_HOUR,
    VerificationLimited,
    VerificationWindow,
)

T = TypeVar("T")
Database = Connection[tuple[Any, ...]]


@dataclass(frozen=True)
class ChallengeRequest:
    """Generic public acknowledgement plus a private optional post-commit ticket.

    Serialize only challenge_id and expires_at. Never expose ticket presence,
    provider result or eligibility. Process loss after commit may lose the send;
    same-operation retries cannot recover/retry it. A deliberate new operation
    after cooldown is the recovery path, subject to ordinary send/attempt limits.
    """

    challenge_id: UUID
    expires_at: datetime
    delivery: OtpDelivery | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class VerifiedOtp:
    """Transaction-local proof passed only to the owning activation/reset callback."""

    challenge_id: UUID
    purpose: str
    user_id: UUID | None
    email: str = field(repr=False)
    target_digest: bytes = field(repr=False)
    key_version: str
    verified_at: datetime


class PostgresTemporaryChallenges:
    """Serialize source/target sends and target verifications in real PostgreSQL.

    New challenges and acknowledgements commit before one-shot dispatch. Failure
    counters commit even when verification fails. Correct verification and its
    caller-owned mutation share one transaction; callback failure rolls back
    consumption. No connection/target is discovered from ambient environment.
    """

    def __init__(
        self,
        connect: Callable[[], AbstractContextManager[Database]],
        keys: TemporaryKeys,
        clock: Callable[[], datetime],
    ) -> None:
        """Bind private dependencies without I/O; key rotation is not automatic."""
        self._connect = connect
        self._keys = keys
        self._clock = clock

    @staticmethod
    def _lock(connection: Database, label: str, digest: bytes) -> None:
        """Use domain-separated transaction advisory locks with consistent ordering."""
        key = int.from_bytes(
            hashlib.sha256(label.encode() + b":" + digest).digest()[:8],
            "big",
            signed=True,
        )
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (key,))

    def _begin(self, connection: Database) -> None:
        """Bound SQL waits and fail closed on missing/changed key commitments.

        First adoption requires no pre-existing temporary auth state. An existing
        deployment needs a reviewed migration rather than guessing old keys.
        A key/version replacement cannot silently reset enrollment/rate guards.
        """
        connection.execute(IDENTITY_BOUNDS_SQL)
        row = connection.execute(
            "SELECT key_version, lookup_fingerprint, verifier_fingerprint, encryption_fingerprint "
            "FROM identity.otp_key_binding WHERE singleton"
        ).fetchone()
        if row is None:
            self._lock(connection, "otp-key-adoption", b"singleton")
            row = connection.execute(
                "SELECT key_version, lookup_fingerprint, verifier_fingerprint, encryption_fingerprint "
                "FROM identity.otp_key_binding WHERE singleton"
            ).fetchone()
            if row is None:
                occupied = connection.execute(
                    "SELECT EXISTS(SELECT 1 FROM identity.temporary_credentials) "
                    "OR EXISTS(SELECT 1 FROM identity.temporary_enrollments) "
                    "OR EXISTS(SELECT 1 FROM identity.otp_challenges) "
                    "OR EXISTS(SELECT 1 FROM identity.auth_source_events) "
                    "OR EXISTS(SELECT 1 FROM identity.microsoft_login_attempts) "
                    "OR EXISTS(SELECT 1 FROM identity.sessions WHERE last_seen_at IS NOT NULL)"
                ).fetchone()
                if occupied is None or occupied[0]:
                    raise PublicError(ERRORS[503])
                connection.execute(
                    "INSERT INTO identity.otp_key_binding "
                    "(key_version, lookup_fingerprint, verifier_fingerprint, encryption_fingerprint) "
                    "VALUES (%s, %s, %s, %s)",
                    (self._keys.version, *self._keys.fingerprints()),
                )
                return
        if row != (self._keys.version, *self._keys.fingerprints()):
            raise PublicError(ERRORS[503])

    def _eligible(
        self, c: Database, target: bytes, purpose: str, now: datetime
    ) -> tuple[bool, UUID | None]:
        """Suppress reenrollment/unknown resets without creating phantom accounts.

        Reset locks the existing account after the target, so later reset/account
        mutations share its current state. Editable contacts never select login.
        """
        key = self._keys.version + ":" + target.hex()
        if purpose == "initial_verification":
            row = c.execute(
                "SELECT EXISTS(SELECT 1 FROM identity.temporary_enrollments "
                "WHERE digest_key_version = %s AND login_digest = %s) "
                "OR EXISTS(SELECT 1 FROM identity.temporary_credentials WHERE login_email_key = %s)",
                (self._keys.version, target, key),
            ).fetchone()
            return row is not None and not row[0], None
        row = c.execute(
            "SELECT u.id, u.account_class, u.status, u.expires_at, u.profile_removed_at "
            "FROM identity.temporary_credentials t JOIN identity.users u ON u.id = t.user_id "
            "WHERE t.login_email_key = %s FOR UPDATE OF u",
            (key,),
        ).fetchone()
        if row is None:
            return False, None
        return (
            row[1] == "temporary"
            and row[2] == "active"
            and row[3] is not None
            and now < row[3]
            and row[4] is None,
            row[0],
        )

    def start(
        self,
        email: str,
        purpose: str,
        operation_id: UUID,
        source: IPv4Address | IPv6Address,
    ) -> ChallengeRequest:
        """Reserve one generic challenge and optional send, with no provider call.

        Requests to ineligible targets consume identical send/attempt windows.
        Duplicate operations return their original ID/expiry without charging a
        send or extending expiry. Source is trusted server-resolved IP, not XFF.
        """
        try:
            normalized = normalize_login(email)
            request = self._keys.request_digest(normalized, purpose, operation_id)
            target = self._keys.target_digest(normalized)
            source_digest = self._keys.source_digest(source)
        except ValueError:
            raise PublicError(ERRORS[422]) from None
        material = None
        try:
            with self._connect() as c:
                if c.info.transaction_status != TransactionStatus.IDLE:
                    raise PublicError(ERRORS[503])
                with c.transaction():
                    self._begin(c)
                    self._lock(c, "otp-source", source_digest)
                    self._lock(c, "otp-target", target)
                    now = as_utc(self._clock())
                    old = c.execute(
                        "SELECT challenge_id, expires_at FROM identity.otp_operations WHERE request_digest = %s",
                        (request,),
                    ).fetchone()
                    if old is not None:
                        return ChallengeRequest(old[0], old[1])
                    self._send_limits(c, target, source_digest, now)
                    prior = c.execute(
                        "SELECT expires_at, failures FROM identity.otp_verification_windows "
                        "WHERE key_version = %s AND target_digest = %s AND purpose = %s FOR UPDATE",
                        (self._keys.version, target, purpose),
                    ).fetchone()
                    window = (
                        VerificationWindow(prior[0], prior[1]).resend(now)
                        if prior
                        else VerificationWindow(now + OTP_LIFETIME)
                    )
                    eligible, user_id = self._eligible(c, target, purpose, now)
                    identifier = new_id()
                    # Equal cryptographic preparation for eligible/ineligible targets.
                    material = prepare_challenge(
                        self._keys, normalized, identifier, purpose, window.expires_at
                    )
                    c.execute(
                        "UPDATE identity.otp_challenges SET superseded_at = %s "
                        "WHERE key_version = %s AND target_lookup_digest = %s AND purpose = %s "
                        "AND consumed_at IS NULL AND superseded_at IS NULL AND expires_at > %s",
                        (now, self._keys.version, target, purpose, now),
                    )
                    if eligible:
                        c.execute(
                            "INSERT INTO identity.otp_challenges "
                            "(id, user_id, target_lookup_digest, verifier, purpose, created_at, expires_at, "
                            "last_sent_at, key_version, encrypted_target) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            (
                                identifier,
                                user_id,
                                target,
                                material.verifier,
                                purpose,
                                now,
                                window.expires_at,
                                now,
                                self._keys.version,
                                material.encrypted_target,
                            ),
                        )
                    c.execute(
                        "INSERT INTO identity.otp_operations (request_digest,key_version,challenge_id,expires_at) "
                        "VALUES (%s,%s,%s,%s)",
                        (request, self._keys.version, identifier, window.expires_at),
                    )
                    c.execute(
                        "INSERT INTO identity.otp_send_reservations "
                        "(challenge_id,key_version,target_digest,source_digest,purpose,created_at,expires_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (
                            identifier,
                            self._keys.version,
                            target,
                            source_digest,
                            purpose,
                            now,
                            window.expires_at,
                        ),
                    )
                    c.execute(
                        "INSERT INTO identity.otp_verification_windows "
                        "(key_version,target_digest,purpose,latest_challenge_id,expires_at,failures) "
                        "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (key_version,target_digest,purpose) "
                        "DO UPDATE SET latest_challenge_id = EXCLUDED.latest_challenge_id, "
                        "expires_at = EXCLUDED.expires_at, failures = EXCLUDED.failures",
                        (
                            self._keys.version,
                            target,
                            purpose,
                            identifier,
                            window.expires_at,
                            window.failures,
                        ),
                    )
                if not eligible:
                    material.delivery.discard()
                return ChallengeRequest(
                    identifier,
                    window.expires_at,
                    material.delivery if eligible else None,
                )
        except VerificationLimited:
            raise PublicError(ERRORS[429]) from None
        except PublicError:
            if material is not None:
                material.delivery.discard()
            raise
        except Exception:
            if material is not None:
                material.delivery.discard()
            raise PublicError(ERRORS[503]) from None

    def _send_limits(
        self, c: Database, target: bytes, source: bytes, now: datetime
    ) -> None:
        """Count committed reservations under source-then-target locks, across purposes."""
        row = c.execute(
            "SELECT count(*), max(created_at) FROM identity.otp_send_reservations "
            "WHERE key_version = %s AND target_digest = %s AND created_at > %s",
            (self._keys.version, target, now - timedelta(hours=1)),
        ).fetchone()
        source_row = c.execute(
            "SELECT count(*) FROM identity.otp_send_reservations "
            "WHERE key_version = %s AND source_digest = %s AND created_at > %s",
            (self._keys.version, source, now - timedelta(hours=1)),
        ).fetchone()
        if row is None or source_row is None:
            raise PublicError(ERRORS[503])
        if (
            row[0] >= TARGET_SENDS_PER_HOUR
            or source_row[0] >= SOURCE_SENDS_PER_HOUR
            or (row[1] is not None and now - row[1] < RESEND_COOLDOWN)
        ):
            raise PublicError(ERRORS[429])

    def consume(
        self,
        challenge_id: UUID,
        purpose: str,
        code: str,
        apply: Callable[[Database, VerifiedOtp], T],
    ) -> T:
        """Consume once and apply owning-domain mutation atomically on the same DB.

        Callback must not send, commit, open a separate transaction/connection,
        expose proof to an untrusted caller or acquire locks in another order.
        Wrong-code failures commit before returning safe422, including bad format.
        Correct third attempt is allowed; three failures block until latest expiry.
        """
        if (
            not isinstance(challenge_id, UUID)
            or challenge_id.version != 4
            or purpose not in {"initial_verification", "password_reset"}
        ):
            raise PublicError(ERRORS[422])
        try:
            with self._connect() as c:
                if c.info.transaction_status != TransactionStatus.IDLE:
                    raise PublicError(ERRORS[503])
                with c.transaction():
                    self._begin(c)
                    initial = c.execute(
                        "SELECT target_digest, created_at, expires_at FROM identity.otp_send_reservations "
                        "WHERE challenge_id = %s AND key_version = %s AND purpose = %s",
                        (challenge_id, self._keys.version, purpose),
                    ).fetchone()
                    if initial is None:
                        raise PublicError(ERRORS[422])
                    target = initial[0]
                    self._lock(c, "otp-target", target)
                    now = as_utc(self._clock())
                    row = c.execute(
                        "SELECT expires_at, consumed_at, superseded_at, verifier, encrypted_target, user_id, created_at "
                        "FROM identity.otp_challenges WHERE id = %s FOR UPDATE",
                        (challenge_id,),
                    ).fetchone()
                    window = c.execute(
                        "SELECT latest_challenge_id, expires_at, failures FROM identity.otp_verification_windows "
                        "WHERE key_version = %s AND target_digest = %s AND purpose = %s FOR UPDATE",
                        (self._keys.version, target, purpose),
                    ).fetchone()
                    if (
                        window is None
                        or window[0] != challenge_id
                        or not initial[1] <= now < initial[2]
                        or (
                            row is not None
                            and (row[1] is not None or row[2] is not None)
                        )
                    ):
                        raise PublicError(ERRORS[422])
                    VerificationWindow(window[1], window[2]).require_available(now)
                    eligible, user_id = self._eligible(c, target, purpose, now)
                    # Suppressed/unknown reset acknowledgements spend the same
                    # failure budget, preventing enumeration via 422/429 behavior.
                    try:
                        candidate = self._keys.otp_verifier(
                            code, challenge_id, purpose, target, initial[2]
                        )
                        matches = row is not None and hmac.compare_digest(
                            row[3], candidate
                        )
                        # The reviewed reset contract permits a state-race409 only
                        # after correct proof; wrong/unknown codes remain uniform.
                        if (
                            purpose == "password_reset"
                            and matches
                            and row is not None
                            and (not eligible or user_id != row[5])
                        ):
                            raise PublicError(ERRORS[409])
                        valid = (
                            eligible
                            and row is not None
                            and user_id == row[5]
                            and matches
                        )
                    except ValueError:
                        valid = False
                    if valid and row is not None:
                        email = self._keys.decrypt_target(
                            row[4], challenge_id, purpose, target, row[0]
                        )
                        c.execute(
                            "UPDATE identity.otp_challenges SET consumed_at = %s WHERE id = %s",
                            (now, challenge_id),
                        )
                        return apply(
                            c,
                            VerifiedOtp(
                                challenge_id,
                                purpose,
                                user_id,
                                email,
                                target,
                                self._keys.version,
                                now,
                            ),
                        )
                    c.execute(
                        "UPDATE identity.otp_challenges SET attempts = attempts + 1 WHERE id = %s",
                        (challenge_id,),
                    )
                    c.execute(
                        "UPDATE identity.otp_verification_windows SET failures = failures + 1 "
                        "WHERE key_version = %s AND target_digest = %s AND purpose = %s",
                        (self._keys.version, target, purpose),
                    )
                # Raise outside transaction: otherwise counters would roll back.
                raise PublicError(ERRORS[422])
        except VerificationLimited:
            raise PublicError(ERRORS[429]) from None
        except PublicError:
            raise
        except Exception:
            raise PublicError(ERRORS[503]) from None
