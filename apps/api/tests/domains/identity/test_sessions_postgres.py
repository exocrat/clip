"""Actual session/password/nonce/race checks; no network provider or retained DB."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from ipaddress import ip_address
from threading import Barrier
from uuid import uuid4

import psycopg
from pydantic import SecretStr
import pytest

from app.core.errors import PublicError
from app.domains.identity.sessions import digest, bound_value
from apps.api.tests.domains.identity.session_fixtures import (
    activate,
    challenge,
    EMAIL,
    PASSWORD,
    SOURCE,
)


def denied(status, action):
    with pytest.raises(PublicError) as error:
        action()
    assert error.value.spec.status == status
    assert str(error.value) == error.value.spec.code


def test_atomic_activation_and_cookie_digest_only(identity_runtime):
    state = identity_runtime
    grant = activate(state)
    raw = grant.token.get_secret_value()
    assert raw not in repr(grant)
    identity = state.service.authenticate(raw)
    assert identity.caller.user_id == grant.identity.caller.user_id
    assert identity.caller.valid_until == state.clock[0] + timedelta(hours=24)
    with state.connect() as c:
        assert c.execute("SELECT token_digest FROM identity.sessions").fetchone()[
            0
        ] == digest(raw, "clip-session-v1")
        assert (
            c.execute("SELECT count(*) FROM identity.temporary_enrollments").fetchone()[
                0
            ]
            == 1
        )
    assert bound_value(raw, "csrf") != bound_value(raw, "microsoft-nonce")


def test_idle_timeout_exact_boundary_never_renews_expired_session(identity_runtime):
    state = identity_runtime
    grant = activate(state)
    state.clock[0] += timedelta(hours=24)
    denied(401, lambda: state.service.authenticate(grant.token.get_secret_value()))
    with state.connect() as c:
        assert c.execute("SELECT last_seen_at FROM identity.sessions").fetchone()[
            0
        ] == state.clock[0] - timedelta(hours=24)


def test_absolute_timeout_and_temporary_expiry_cap(identity_runtime):
    state = identity_runtime
    grant = activate(state)
    original = state.clock[0]
    for half_day in range(1, 14):
        state.clock[0] = original + timedelta(hours=12 * half_day)
        state.service.authenticate(grant.token.get_secret_value())
    state.clock[0] = original + timedelta(days=7)
    denied(401, lambda: state.service.authenticate(grant.token.get_secret_value()))
    state.clock[0] = original + timedelta(days=14) - timedelta(minutes=1)
    late = state.service.password_login(EMAIL, PASSWORD, SOURCE)
    assert late.expires_at == original + timedelta(days=14)
    assert late.identity.caller.valid_until == late.expires_at
    state.clock[0] = late.expires_at
    denied(401, lambda: state.service.authenticate(late.token.get_secret_value()))
    denied(401, lambda: state.service.password_login(EMAIL, PASSWORD, SOURCE))


def test_login_rotates_tokens_and_logout_is_current_only(identity_runtime):
    state = identity_runtime
    initial = activate(state)
    second = state.service.password_login(EMAIL.upper(), PASSWORD, SOURCE)
    assert initial.token != second.token
    raw = initial.token.get_secret_value()
    state.service.logout(raw)
    state.service.logout(raw)
    denied(401, lambda: state.service.authenticate(raw))
    state.service.authenticate(second.token.get_secret_value())
    denied(401, lambda: state.service.logout("bad-cookie"))


def test_known_unknown_and_revoked_failed_login_sequences_match(identity_runtime):
    state = identity_runtime
    initial = activate(state)
    wrong = SecretStr("synthetic wrong passphrase")
    for email in (EMAIL, "unknown@example.invalid"):
        for _ in range(5):
            denied(401, lambda: state.service.password_login(email, wrong, SOURCE))
        denied(429, lambda: state.service.password_login(email, wrong, SOURCE))
    denied(429, lambda: state.service.password_login(EMAIL, PASSWORD, SOURCE))
    state.clock[0] += timedelta(minutes=15)
    state.service.password_login(EMAIL, PASSWORD, SOURCE)
    state.service.revoke_account(initial.identity.caller.user_id)
    denied(401, lambda: state.service.password_login(EMAIL, PASSWORD, SOURCE))
    denied(401, lambda: state.service.authenticate(initial.token.get_secret_value()))


def test_failure_window_not_reset_by_success(identity_runtime):
    state = identity_runtime
    activate(state)
    wrong = SecretStr("synthetic wrong password")
    for _ in range(4):
        denied(401, lambda: state.service.password_login(EMAIL, wrong, SOURCE))
    state.service.password_login(EMAIL, PASSWORD, SOURCE)
    denied(401, lambda: state.service.password_login(EMAIL, wrong, SOURCE))
    denied(429, lambda: state.service.password_login(EMAIL, PASSWORD, SOURCE))


def test_source_budget_cannot_be_reset_by_target_rotation(identity_runtime):
    state = identity_runtime
    for i in range(100):
        denied(
            401,
            lambda: state.service.password_login(
                f"unknown{i}@example.invalid", PASSWORD, SOURCE
            ),
        )
    denied(
        429,
        lambda: state.service.password_login("extra@example.invalid", PASSWORD, SOURCE),
    )
    denied(
        401,
        lambda: state.service.password_login(
            "extra@example.invalid", PASSWORD, ip_address("192.0.2.28")
        ),
    )
    state.clock[0] += timedelta(minutes=15)
    denied(
        401,
        lambda: state.service.password_login("fresh@example.invalid", PASSWORD, SOURCE),
    )


def test_reset_changes_hash_consumes_and_revokes_without_renewal(identity_runtime):
    state = identity_runtime
    first = activate(state)
    second = state.service.password_login(EMAIL, PASSWORD, SOURCE)
    activated_at = state.clock[0]
    request, code = challenge(state, "password_reset")
    new = SecretStr("synthetic new passphrase")
    state.service.reset_password(request.challenge_id, code, new)
    for grant in (first, second):
        denied(401, lambda: state.service.authenticate(grant.token.get_secret_value()))
    denied(401, lambda: state.service.password_login(EMAIL, PASSWORD, SOURCE))
    result = state.service.password_login(EMAIL, new, SOURCE)
    assert result.expires_at == min(
        state.clock[0] + timedelta(days=7), activated_at + timedelta(days=14)
    )
    denied(422, lambda: state.service.reset_password(request.challenge_id, code, new))
    with state.connect() as c:
        assert c.execute(
            "SELECT expires_at-activated_at FROM identity.users"
        ).fetchone()[0] == timedelta(hours=336)


def test_concurrent_reset_and_old_password_login_cannot_leave_old_session(
    identity_runtime,
):
    state = identity_runtime
    activate(state)
    request, code = challenge(state, "password_reset")
    new = SecretStr("synthetic replacement password")
    barrier = Barrier(12)

    def call(i):
        barrier.wait(timeout=10)
        if i == 0:
            state.service.reset_password(request.challenge_id, code, new)
            return None
        try:
            return state.service.password_login(EMAIL, PASSWORD, SOURCE)
        except PublicError as error:
            assert error.spec.status in (401, 429)
            return None

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(call, range(12)))
    for grant in results:
        if grant:
            denied(
                401, lambda: state.service.authenticate(grant.token.get_secret_value())
            )
    state.clock[0] += timedelta(minutes=15)
    state.service.password_login(EMAIL, new, SOURCE)


def test_reset_failure_rolls_back_hash_consume_and_session_revocation(identity_runtime):
    state = identity_runtime
    initial = activate(state)
    request, code = challenge(state, "password_reset")
    with state.connect() as c:
        original = c.execute(
            "SELECT password_hash FROM identity.temporary_credentials"
        ).fetchone()[0]
        c.execute(
            "CREATE FUNCTION identity.reject_session_test() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rejection'; END $$"
        )
        c.execute(
            "CREATE TRIGGER reject_session_test BEFORE UPDATE ON identity.sessions FOR EACH ROW EXECUTE FUNCTION identity.reject_session_test()"
        )
    try:
        denied(
            503,
            lambda: state.service.reset_password(
                request.challenge_id, code, SecretStr("synthetic replacement password")
            ),
        )
    finally:
        with state.connect() as c:
            c.execute("DROP TRIGGER reject_session_test ON identity.sessions")
            c.execute("DROP FUNCTION identity.reject_session_test()")
            assert (
                c.execute(
                    "SELECT password_hash FROM identity.temporary_credentials"
                ).fetchone()[0]
                == original
            )
            assert (
                c.execute(
                    "SELECT consumed_at FROM identity.otp_challenges WHERE id=%s",
                    (request.challenge_id,),
                ).fetchone()[0]
                is None
            )
    state.service.authenticate(initial.token.get_secret_value())


def test_activation_session_failure_rolls_back_all_account_writes(identity_runtime):
    state = identity_runtime
    request, code = challenge(state)
    with state.connect() as c:
        c.execute(
            "CREATE FUNCTION identity.reject_insert_test() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rejection'; END $$"
        )
        c.execute(
            "CREATE TRIGGER reject_insert_test BEFORE INSERT ON identity.sessions FOR EACH ROW EXECUTE FUNCTION identity.reject_insert_test()"
        )
    try:
        denied(
            503, lambda: state.service.activate(request.challenge_id, code, PASSWORD)
        )
        with state.connect() as c:
            assert c.execute(
                "SELECT (SELECT count(*) FROM identity.users),(SELECT count(*) FROM identity.temporary_credentials),(SELECT count(*) FROM identity.temporary_enrollments)"
            ).fetchone() == (0, 0, 0)
            assert (
                c.execute("SELECT consumed_at FROM identity.otp_challenges").fetchone()[
                    0
                ]
                is None
            )
    finally:
        with state.connect() as c:
            c.execute("DROP TRIGGER reject_insert_test ON identity.sessions")
            c.execute("DROP FUNCTION identity.reject_insert_test()")
    state.service.activate(request.challenge_id, code, PASSWORD)


def test_microsoft_attempt_nonce_and_single_redemption(identity_runtime, signed_tokens):
    state = identity_runtime
    attempt = state.service.start_microsoft(SOURCE)
    raw = attempt.token.get_secret_value()
    token = SecretStr(signed_tokens.token({"nonce": attempt.nonce}))
    grant = state.service.microsoft_exchange(
        token, raw, SOURCE, signed_tokens.validator()
    )
    assert grant.identity.caller.account_class == "regular"
    denied(
        401,
        lambda: state.service.microsoft_exchange(
            token, raw, SOURCE, signed_tokens.validator()
        ),
    )
    with state.connect() as c:
        assert c.execute(
            "SELECT token_digest FROM identity.microsoft_login_attempts"
        ).fetchone()[0] == digest(raw, "clip-ms-attempt-v1")
        assert c.execute("SELECT count(*) FROM identity.users").fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM identity.sessions").fetchone()[0] == 1


def test_microsoft_nonce_mismatch_expiry_and_missing_attempt(
    identity_runtime, signed_tokens
):
    state = identity_runtime
    attempt = state.service.start_microsoft(SOURCE)
    bad = SecretStr(signed_tokens.token())
    denied(
        401,
        lambda: state.service.microsoft_exchange(
            bad, attempt.token.get_secret_value(), SOURCE, signed_tokens.validator()
        ),
    )
    denied(
        401,
        lambda: state.service.microsoft_exchange(
            bad, None, SOURCE, signed_tokens.validator()
        ),
    )
    state.clock[0] = attempt.expires_at
    valid = SecretStr(signed_tokens.token({"nonce": attempt.nonce}))
    denied(
        401,
        lambda: state.service.microsoft_exchange(
            valid, attempt.token.get_secret_value(), SOURCE, signed_tokens.validator()
        ),
    )
    with state.connect() as c:
        assert c.execute("SELECT count(*) FROM identity.sessions").fetchone()[0] == 0


def test_microsoft_attempt_race_creates_one_mapping_and_session(
    identity_runtime, signed_tokens
):
    state = identity_runtime
    attempt = state.service.start_microsoft(SOURCE)
    token = SecretStr(signed_tokens.token({"nonce": attempt.nonce}))
    validator = signed_tokens.validator()

    def exchange(_):
        try:
            return state.service.microsoft_exchange(
                token, attempt.token.get_secret_value(), SOURCE, validator
            )
        except PublicError as error:
            assert error.spec.status == 401
            return None

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(exchange, range(12)))
    assert sum(result is not None for result in results) == 1
    with state.connect() as c:
        assert c.execute(
            "SELECT (SELECT count(*) FROM identity.users),(SELECT count(*) FROM identity.external_identities),(SELECT count(*) FROM identity.sessions)"
        ).fetchone() == (1, 1, 1)


def test_microsoft_session_failure_rolls_back_mapping_and_attempt(
    identity_runtime, signed_tokens
):
    state = identity_runtime
    attempt = state.service.start_microsoft(SOURCE)
    token = SecretStr(signed_tokens.token({"nonce": attempt.nonce}))
    with state.connect() as c:
        c.execute(
            "CREATE FUNCTION identity.reject_ms_test() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rejection'; END $$"
        )
        c.execute(
            "CREATE TRIGGER reject_ms_test BEFORE INSERT ON identity.sessions FOR EACH ROW EXECUTE FUNCTION identity.reject_ms_test()"
        )
    try:
        denied(
            503,
            lambda: state.service.microsoft_exchange(
                token,
                attempt.token.get_secret_value(),
                SOURCE,
                signed_tokens.validator(),
            ),
        )
        with state.connect() as c:
            assert c.execute(
                "SELECT (SELECT count(*) FROM identity.users),(SELECT count(*) FROM identity.external_identities),(SELECT count(*) FROM identity.sessions)"
            ).fetchone() == (0, 0, 0)
            assert (
                c.execute(
                    "SELECT consumed_at FROM identity.microsoft_login_attempts"
                ).fetchone()[0]
                is None
            )
    finally:
        with state.connect() as c:
            c.execute("DROP TRIGGER reject_ms_test ON identity.sessions")
            c.execute("DROP FUNCTION identity.reject_ms_test()")
    state.service.microsoft_exchange(
        token, attempt.token.get_secret_value(), SOURCE, signed_tokens.validator()
    )


def test_unbound_legacy_session_cannot_silently_authenticate(identity_runtime):
    state = identity_runtime
    grant = activate(state)
    with state.connect() as c:
        c.execute("UPDATE identity.sessions SET last_seen_at=NULL")
    denied(401, lambda: state.service.authenticate(grant.token.get_secret_value()))
