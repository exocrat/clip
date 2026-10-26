"""Real atomic activation/eligibility checks in a new disposable PostgreSQL DB."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
import re
import secrets
from types import SimpleNamespace
from uuid import uuid4

from argon2 import PasswordHasher
from pydantic import SecretStr
import pytest

from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.domains.identity.temporary_accounts import (
    TemporaryActivation,
    PostgresTemporaryAccounts,
)
from app.domains.identity.temporary_challenges import PostgresTemporaryChallenges
from app.domains.identity.temporary_crypto import TemporaryKeys

NOW = datetime(2030, 1, 1, tzinfo=UTC)
EMAIL = "synthetic@example.invalid"
PASSWORD = SecretStr("synthetic-passphrase")
SOURCE = ip_address("192.0.2.25")


@pytest.fixture
def activation(disposable_database):
    """Use real Step5 storage/crypto and controlled time; reset only the owned DB."""
    with disposable_database() as c:
        c.execute(
            "TRUNCATE identity.otp_operations, identity.otp_send_reservations, "
            "identity.otp_verification_windows, identity.otp_key_binding, identity.otp_challenges, "
            "identity.temporary_credentials, identity.temporary_enrollments, identity.users CASCADE"
        )
    clock = [NOW]
    keys = TemporaryKeys("synthetic-v1", *(secrets.token_bytes(32) for _ in range(3)))
    challenges = PostgresTemporaryChallenges(
        disposable_database, keys, lambda: clock[0]
    )
    return SimpleNamespace(
        clock=clock,
        keys=keys,
        challenges=challenges,
        connect=disposable_database,
        service=TemporaryActivation(challenges),
        accounts=PostgresTemporaryAccounts(disposable_database, lambda: clock[0]),
    )


def issue(state, email=EMAIL, purpose="initial_verification"):
    """Capture a synthetic code transiently, with no live email or raw-code file."""
    request = state.challenges.start(email, purpose, uuid4(), SOURCE)

    class Capture:
        def send(self, recipient, subject, body):
            self.code = re.search(r"Use ([0-9]{6}) to", body).group(1)

    capture = Capture()
    if request.delivery is None:
        return request, None
    assert request.delivery.dispatch(capture, now=state.clock[0])
    return request, capture.code


def denied(status, action):
    with pytest.raises(PublicError) as error:
        action()
    assert error.value.spec.status == status
    assert str(error.value) == error.value.spec.code


def inventory(state):
    with state.connect() as c:
        return c.execute(
            "SELECT (SELECT count(*) FROM identity.users),"
            "(SELECT count(*) FROM identity.temporary_credentials),"
            "(SELECT count(*) FROM identity.temporary_enrollments),"
            "(SELECT count(*) FROM identity.sessions),"
            "(SELECT count(*) FROM identity.otp_challenges WHERE consumed_at IS NOT NULL)"
        ).fetchone()


def activate(state):
    request, code = issue(state)
    return state.service.activate(request.challenge_id, code, PASSWORD), request, code


def test_activation_uses_first_success_time_and_protected_login_key(activation):
    state = activation
    request, code = issue(state, email=EMAIL.upper())
    assert inventory(state) == (0, 0, 0, 0, 0)
    state.clock[0] += timedelta(minutes=7)
    account = state.service.activate(request.challenge_id, code, PASSWORD)
    assert account.activated_at == state.clock[0]
    assert account.expires_at - account.activated_at == timedelta(hours=336)
    assert inventory(state) == (1, 1, 1, 0, 1)
    with state.connect() as c:
        assert c.execute(
            "SELECT account_class,status,created_at,activated_at,expires_at FROM identity.users"
        ).fetchone() == (
            "temporary",
            "active",
            state.clock[0],
            account.activated_at,
            account.expires_at,
        )
        assert c.execute(
            "SELECT user_id,consumed_at FROM identity.otp_challenges"
        ).fetchone() == (account.user_id, account.activated_at)
        credential = c.execute(
            "SELECT login_email_key,password_hash,created_at,password_changed_at FROM identity.temporary_credentials"
        ).fetchone()
        assert (
            credential[0] == state.keys.credential_key(EMAIL)
            and EMAIL not in credential[0]
        )
        assert PasswordHasher().verify(credential[1], PASSWORD.get_secret_value())
        assert PASSWORD.get_secret_value() not in credential[1]
        assert credential[2:] == (state.clock[0], state.clock[0])
        assert c.execute(
            "SELECT login_digest,digest_key_version,first_activated_at,original_expires_at,user_id FROM identity.temporary_enrollments"
        ).fetchone() == (
            state.keys.target_digest(EMAIL),
            state.keys.version,
            account.activated_at,
            account.expires_at,
            account.user_id,
        )


def test_activation_race_creates_exactly_one_account_credential_guard(activation):
    state = activation
    request, code = issue(state)

    def call(_):
        try:
            return state.service.activate(request.challenge_id, code, PASSWORD)
        except PublicError as error:
            assert error.spec.status == 422
            return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(call, range(16)))
    assert sum(result is not None for result in results) == 1
    assert inventory(state) == (1, 1, 1, 0, 1)


def test_invalid_password_does_not_consume_otp_or_create_records(activation):
    state = activation
    request, code = issue(state)
    denied(
        422,
        lambda: state.service.activate(request.challenge_id, code, SecretStr("short")),
    )
    assert inventory(state) == (0, 0, 0, 0, 0)
    state.service.activate(request.challenge_id, code, PASSWORD)
    assert inventory(state) == (1, 1, 1, 0, 1)


@pytest.mark.parametrize("mode", ["wrong", "expired", "superseded", "reset", "missing"])
def test_unusable_otp_cannot_activate(activation, mode):
    state = activation
    request, code = issue(
        state, purpose="password_reset" if mode == "reset" else "initial_verification"
    )
    identifier = request.challenge_id
    if mode == "wrong":
        code = ("0" if code[0] != "0" else "1") + code[1:]
    elif mode == "expired":
        state.clock[0] = request.expires_at
    elif mode == "superseded":
        state.clock[0] += timedelta(minutes=1)
        issue(state)
    elif mode == "missing":
        identifier = uuid4()
    denied(422, lambda: state.service.activate(identifier, code or "000000", PASSWORD))
    assert inventory(state) == (0, 0, 0, 0, 0)


def test_replay_and_new_registration_cannot_restart_lifetime(activation):
    state = activation
    account, request, code = activate(state)
    state.clock[0] += timedelta(minutes=1)
    denied(422, lambda: state.service.activate(request.challenge_id, code, PASSWORD))
    replacement, no_code = issue(state)
    assert replacement.delivery is None and no_code is None
    assert inventory(state) == (1, 1, 1, 0, 1)
    with state.connect() as c:
        assert c.execute(
            "SELECT activated_at,expires_at FROM identity.users"
        ).fetchone() == (account.activated_at, account.expires_at)


@pytest.mark.parametrize("failure", ["hash", "credential", "enrollment"])
def test_any_activation_failure_rolls_back_every_write_and_otp(
    activation, monkeypatch, failure
):
    state = activation
    request, code = issue(state)
    if failure == "hash":

        def fail(self, password, **kwargs):
            raise RuntimeError("PRIVATE_HASH_ERROR")

        monkeypatch.setattr(PasswordHasher, "hash", fail)
    else:
        table = (
            "temporary_credentials"
            if failure == "credential"
            else "temporary_enrollments"
        )
        with state.connect() as c:
            c.execute(
                "CREATE FUNCTION identity.reject_activation_test() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rejection'; END $$"
            )
            c.execute(
                "CREATE TRIGGER reject_activation_test BEFORE INSERT ON identity."
                + table
                + " FOR EACH ROW EXECUTE FUNCTION identity.reject_activation_test()"
            )
    try:
        denied(
            503, lambda: state.service.activate(request.challenge_id, code, PASSWORD)
        )
        assert inventory(state) == (0, 0, 0, 0, 0)
    finally:
        if failure != "hash":
            with state.connect() as c:
                c.execute("DROP TRIGGER reject_activation_test ON identity." + table)
                c.execute("DROP FUNCTION identity.reject_activation_test()")
    monkeypatch.undo()
    state.service.activate(request.challenge_id, code, PASSWORD)
    assert inventory(state) == (1, 1, 1, 0, 1)


def test_exact_expiry_denies_stale_caller_and_guard_survives_credential_cleanup(
    activation,
):
    state = activation
    account, _, _ = activate(state)
    stale = CallerContext(
        account.user_id, "temporary", account.expires_at + timedelta(days=1)
    )
    state.clock[0] = account.expires_at - timedelta(microseconds=1)
    assert state.accounts.require_current(stale) == account
    state.clock[0] = account.expires_at
    stale.require_current(state.clock[0])  # Cached context alone would still pass.
    denied(401, lambda: state.accounts.require_current(stale))
    with state.connect() as c:
        c.execute(
            "DELETE FROM identity.temporary_credentials WHERE user_id=%s",
            (account.user_id,),
        )
    request, code = issue(state)
    assert request.delivery is None and code is None
    assert inventory(state) == (1, 0, 1, 0, 1)
    with state.connect() as c:
        assert c.execute(
            "SELECT activated_at,expires_at FROM identity.users"
        ).fetchone() == (account.activated_at, account.expires_at)


@pytest.mark.parametrize(
    "mode",
    [
        "revoked",
        "removed",
        "expired_context",
        "wrong_class",
        "missing",
        "pending",
        "regular",
    ],
)
def test_live_account_gate_rejects_ineligible_or_untrusted_context(activation, mode):
    state = activation
    account, _, _ = activate(state)
    identifier = account.user_id
    deadline = account.expires_at
    account_class = "temporary"
    with state.connect() as c:
        if mode in {"revoked", "removed"}:
            c.execute(
                "UPDATE identity.users SET status='revoked',revoked_at=%s WHERE id=%s",
                (state.clock[0], identifier),
            )
            if mode == "removed":
                c.execute(
                    "UPDATE identity.users SET profile_removed_at=%s WHERE id=%s",
                    (state.clock[0], identifier),
                )
        elif mode == "expired_context":
            deadline = state.clock[0]
        elif mode == "wrong_class":
            account_class = "regular"
        elif mode == "missing":
            identifier = uuid4()
        elif mode == "pending":
            identifier = uuid4()
            c.execute(
                "INSERT INTO identity.users(id,account_class,status) VALUES (%s,'temporary','pending')",
                (identifier,),
            )
        elif mode == "regular":
            identifier = uuid4()
            c.execute(
                "INSERT INTO identity.users(id,account_class,status) VALUES (%s,'regular','active')",
                (identifier,),
            )
    denied(
        401,
        lambda: state.accounts.require_current(
            CallerContext(identifier, account_class, deadline)
        ),
    )
    denied(401, lambda: state.accounts.require_current({"user_id": identifier}))


def test_wrong_code_does_not_invoke_expensive_hashing(activation, monkeypatch):
    state = activation
    request, code = issue(state)

    def forbidden(self, password, **kwargs):
        pytest.fail("Hashing ran before OTP proof")

    monkeypatch.setattr(PasswordHasher, "hash", forbidden)
    wrong = ("0" if code[0] != "0" else "1") + code[1:]
    denied(422, lambda: state.service.activate(request.challenge_id, wrong, PASSWORD))
    assert inventory(state) == (0, 0, 0, 0, 0)


def test_account_gate_database_failure_is_safe(activation):
    state = activation
    account, _, _ = activate(state)
    caller = CallerContext(account.user_id, "temporary", account.expires_at)

    def unavailable():
        raise RuntimeError("PRIVATE_DATABASE_DETAIL")

    failed = PostgresTemporaryAccounts(unavailable, lambda: state.clock[0])
    denied(503, lambda: failed.require_current(caller))
