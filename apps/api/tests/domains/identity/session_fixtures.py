"""Real session/HTTP fixture: owned disposable SQL, synthetic keys/mail/assertions."""

from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
import re
import secrets
from types import SimpleNamespace
from uuid import uuid4

from pydantic import SecretStr
import pytest

from app.domains.identity.cleanup import IdentityCleanup
from app.domains.identity.http import BrowserPolicy, create_identity_app
from app.domains.identity.sessions import IdentitySessions
from app.domains.identity.temporary_crypto import TemporaryKeys

EMAIL = "session-fixture@example.invalid"
PASSWORD = SecretStr("synthetic-session-passphrase")
SOURCE = ip_address("192.0.2.27")
ORIGIN = "https://clip-iisc.site"
HEADERS = {"Origin": ORIGIN, "X-CLIP-Request": "1"}


class CaptureMail:
    """Synthetic recording transport only; code remains transient test memory."""

    def __init__(self):
        self.messages = []
        self.fail = False

    def send(self, recipient, subject, body):
        self.messages.append((recipient, subject, body))
        if self.fail:
            raise TimeoutError("PRIVATE_PROVIDER_DETAIL")

    def code(self):
        return re.search(r"Use ([0-9]{6}) to", self.messages[-1][2]).group(1)


@pytest.fixture
def identity_runtime(disposable_database, signed_tokens):
    """Reset only this module's fresh DB; production never installs these inputs."""
    with disposable_database() as c:
        c.execute(
            "TRUNCATE identity.microsoft_login_attempts,identity.auth_source_events,identity.password_login_windows,identity.otp_operations,identity.otp_send_reservations,identity.otp_verification_windows,identity.otp_key_binding,identity.otp_challenges,identity.temporary_credentials,identity.temporary_enrollments,identity.users CASCADE"
        )
    keys = TemporaryKeys("synthetic-v1", *(secrets.token_bytes(32) for _ in range(3)))
    clock = [datetime(2030, 1, 1, tzinfo=UTC)]
    service = IdentitySessions(disposable_database, keys, lambda: clock[0])
    mail = CaptureMail()
    policy = BrowserPolicy((ORIGIN,))
    app = create_identity_app(
        service, policy, mail, signed_tokens.validator(), lambda: clock[0]
    )
    return SimpleNamespace(
        service=service,
        keys=keys,
        clock=clock,
        connect=disposable_database,
        mail=mail,
        policy=policy,
        app=app,
        cleanup=IdentityCleanup(disposable_database, lambda: clock[0]),
    )


def challenge(state, purpose="initial_verification", email=EMAIL):
    """Exercise actual reservation/protection with offline mail capture."""
    if purpose == "password_reset":
        state.clock[0] += timedelta(minutes=1)  # Respect cross-purpose OTP cooldown.
    result = state.service.challenges.start(email, purpose, uuid4(), SOURCE)
    assert result.delivery is not None
    assert result.delivery.dispatch(state.mail, now=state.clock[0])
    return result, state.mail.code()


def activate(state, email=EMAIL):
    """Use actual activation/session transaction, never direct synthetic account rows."""
    request, code = challenge(state, email=email)
    return state.service.activate(request.challenge_id, code, PASSWORD)


@pytest.fixture
def temporary_state(identity_runtime):
    """Create approved lifecycle scenarios through actual owned services.

    Returns the original grant so tests can probe stale context/cookies. Expiry
    advances trusted time; revocation uses the real internal operation. No raw
    SQL account fabrication or public fake-auth endpoint is installed.
    """

    def create(mode):
        if mode not in {"active", "expired", "revoked"}:
            raise ValueError("Unknown synthetic lifecycle scenario")
        grant = activate(identity_runtime)
        if mode == "expired":
            identity_runtime.clock[0] += timedelta(days=14)
        elif mode == "revoked":
            identity_runtime.service.revoke_account(grant.identity.caller.user_id)
        return grant

    return create
