"""Private temporary activation and current-account eligibility; no session/HTTP.

Account, credential, service-lifetime enrollment guard and OTP consumption commit
atomically under Step5's target lock. A cached caller is never sufficient for
current account eligibility. Public session transport/issuance remains Step7.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable
from uuid import UUID

from psycopg.pq import TransactionStatus
from pydantic import SecretStr

from app.core.auth import CallerContext
from app.core.errors import ERRORS, PublicError
from app.core.identifiers import new_id
from app.core.timestamps import as_utc
from app.domains.identity.temporary_challenges import (
    Database,
    PostgresTemporaryChallenges,
    VerifiedOtp,
)
from app.domains.identity.temporary_passwords import TemporaryPasswords

TEMPORARY_LIFETIME = timedelta(hours=336)


@dataclass(frozen=True)
class TemporaryAccount:
    """Minimal current account facts; never a session, credential or CallerContext."""

    user_id: UUID
    activated_at: datetime
    expires_at: datetime


class TemporaryActivation:
    """Create a temporary account only through the real single-use OTP boundary."""

    def __init__(self, challenges: PostgresTemporaryChallenges) -> None:
        """Bind private transactional service and fixed real password hashing."""
        self._challenges = challenges
        self._passwords = TemporaryPasswords()

    def activate(
        self, challenge_id: UUID, code: str, password: SecretStr
    ) -> TemporaryAccount:
        """Validate policy, then atomically activate after an initial-verification OTP.

        Email/identity/lifetime are recovered from the authenticated challenge,
        never taken from activation input. Replays, superseded/expired/reset codes
        and retained enrollments cannot create or renew accounts. No session is
        returned; later public wiring must complete its reviewed session response.
        """
        self._passwords.validate(password)

        def create(connection: Database, proof: VerifiedOtp) -> TemporaryAccount:
            """Run only inside consume's target-locked transaction; never commit here."""
            if proof.purpose != "initial_verification" or proof.user_id is not None:
                raise PublicError(ERRORS[422])
            password_hash = self._passwords.hash(password)
            user_id = new_id()
            activated = proof.verified_at
            expires = activated + TEMPORARY_LIFETIME
            connection.execute(
                "INSERT INTO identity.users "
                "(id,account_class,status,created_at,activated_at,expires_at) "
                "VALUES (%s,'temporary','active',%s,%s,%s)",
                (user_id, activated, activated, expires),
            )
            connection.execute(
                "INSERT INTO identity.temporary_credentials "
                "(user_id,login_email_key,password_hash,created_at,password_changed_at) "
                "VALUES (%s,%s,%s,%s,%s)",
                (
                    user_id,
                    proof.key_version + ":" + proof.target_digest.hex(),
                    password_hash,
                    activated,
                    activated,
                ),
            )
            connection.execute(
                "INSERT INTO identity.temporary_enrollments "
                "(id,login_digest,digest_key_version,first_activated_at,original_expires_at,user_id) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    new_id(),
                    proof.target_digest,
                    proof.key_version,
                    activated,
                    expires,
                    user_id,
                ),
            )
            # Initial challenges have no account before proof; bind the consumed
            # challenge to the account created by this same atomic transaction.
            connection.execute(
                "UPDATE identity.otp_challenges SET user_id=%s WHERE id=%s",
                (user_id, proof.challenge_id),
            )
            return TemporaryAccount(user_id, activated, expires)

        return self._challenges.consume(
            challenge_id, "initial_verification", code, create
        )


class PostgresTemporaryAccounts:
    """Fresh account-state gate for later protected-operation/session composition.

    CallerContext must already come from trusted session validation. This gate
    does not authenticate it or install it into request scope, and must not be
    exposed as a browser-controlled identity lookup. No eligibility cache exists.
    """

    def __init__(
        self, connect: Callable[[], Database], clock: Callable[[], datetime]
    ) -> None:
        """Use fresh trusted connections/time; never accept an ambient DB target."""
        self._connect = connect
        self._clock = clock

    def require_current(self, caller: CallerContext) -> TemporaryAccount:
        """Deny expired/revoked/pending/removed accounts despite stale caller facts.

        Call on each protected operation once session validation is wired; this
        check alone does not authorize a marketplace capability or ownership.
        Existing public routes are unchanged and integration is still required.
        """
        if not isinstance(caller, CallerContext) or caller.account_class != "temporary":
            raise PublicError(ERRORS[401])
        try:
            with self._connect() as c:
                if c.info.transaction_status != TransactionStatus.IDLE:
                    raise PublicError(ERRORS[503])
                with c.transaction():
                    c.execute("SET LOCAL lock_timeout = '3s'")
                    c.execute("SET LOCAL statement_timeout = '5s'")
                    row = c.execute(
                        "SELECT account_class,status,activated_at,expires_at,profile_removed_at "
                        "FROM identity.users WHERE id=%s",
                        (caller.user_id,),
                    ).fetchone()
                    now = as_utc(self._clock())
                    caller.require_current(now)
                    if (
                        row is None
                        or row[0] != "temporary"
                        or row[1] != "active"
                        or row[2] is None
                        or row[3] is None
                        or row[4] is not None
                        or not row[2] <= now < row[3]
                    ):
                        raise PublicError(ERRORS[401])
                    return TemporaryAccount(caller.user_id, row[2], row[3])
        except PublicError:
            raise
        except Exception:
            raise PublicError(ERRORS[503]) from None
