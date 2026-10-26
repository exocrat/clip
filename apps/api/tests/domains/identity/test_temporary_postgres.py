"""Actual PostgreSQL OTP transactions/races with synthetic in-memory mail capture."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
from pathlib import Path
import re
import secrets
from uuid import uuid4

import psycopg
import pytest

from app.core.errors import PublicError
from app.domains.identity.temporary_challenges import PostgresTemporaryChallenges
from app.domains.identity.temporary_crypto import TemporaryKeys

NOW = datetime(2030, 1, 1, tzinfo=UTC)
SOURCE = ip_address("192.0.2.17")
EMAIL = "synthetic@example.invalid"
ROOT = Path(__file__).resolve().parents[5]


class Capture:
    """Keep only synthetic test messages in memory; never use a network sender."""

    def __init__(self):
        self.messages = []

    def send(self, recipient, subject, body):
        self.messages.append((recipient, body))


@pytest.fixture
def otp(disposable_database):
    """Reset only this module's disposable test database and inject controlled time."""
    with disposable_database() as c:
        c.execute(
            "TRUNCATE identity.otp_operations, identity.otp_send_reservations, "
            "identity.otp_verification_windows, identity.otp_key_binding, identity.otp_challenges, "
            "identity.temporary_credentials, identity.temporary_enrollments, identity.users CASCADE"
        )
    keys = TemporaryKeys("synthetic-v1", *(secrets.token_bytes(32) for _ in range(3)))
    clock = [NOW]
    service = PostgresTemporaryChallenges(disposable_database, keys, lambda: clock[0])
    return service, keys, clock, disposable_database


def issue(
    otp, email=EMAIL, purpose="initial_verification", operation=None, source=SOURCE
):
    service, _, clock, _ = otp
    request = service.start(email, purpose, operation or uuid4(), source)
    capture = Capture()
    if request.delivery is None:
        return request, None
    assert request.delivery.dispatch(capture, now=clock[0])
    code = re.search(r"Use ([0-9]{6}) to", capture.messages[0][1]).group(1)
    return request, code


def denied(status, action):
    with pytest.raises(PublicError) as error:
        action()
    assert error.value.spec.status == status
    assert str(error.value) == error.value.spec.code


def incorrect(code):
    return ("0" if code[0] != "0" else "1") + code[1:]


def proof_only(connection, proof):
    """Observe transaction-local proof without implementing a later account mutation."""
    assert connection.info.transaction_status == psycopg.pq.TransactionStatus.INTRANS
    assert proof.email == EMAIL and proof.purpose == "initial_verification"
    return proof.challenge_id


def test_success_persistence_privacy_and_single_consumption(otp):
    service, keys, _, connect = otp
    request, code = issue(otp)
    with connect() as c:
        row = c.execute(
            "SELECT verifier, encrypted_target, attempts FROM identity.otp_challenges"
        ).fetchone()
        assert len(row[0]) == 32 and row[0] != code.encode()
        assert EMAIL.encode() not in row[1] and row[2] == 0
        assert c.execute("SELECT count(*) FROM identity.users").fetchone()[0] == 0
        assert c.execute("SELECT count(*) FROM identity.sessions").fetchone()[0] == 0
    assert (
        service.consume(request.challenge_id, "initial_verification", code, proof_only)
        == request.challenge_id
    )
    denied(
        422,
        lambda: service.consume(
            request.challenge_id, "initial_verification", code, proof_only
        ),
    )


def test_duplicate_race_returns_original_ack_and_one_ticket(otp):
    service, _, clock, connect = otp
    operation = uuid4()
    with ThreadPoolExecutor(max_workers=16) as pool:
        requests = list(
            pool.map(
                lambda _: service.start(
                    EMAIL, "initial_verification", operation, SOURCE
                ),
                range(16),
            )
        )
    assert len({request.challenge_id for request in requests}) == 1
    assert sum(request.delivery is not None for request in requests) == 1
    clock[0] += timedelta(days=2)
    replay = service.start(EMAIL.upper(), "initial_verification", operation, SOURCE)
    assert replay.challenge_id == requests[0].challenge_id
    assert replay.expires_at == NOW + timedelta(minutes=10)
    assert replay.delivery is None
    with connect() as c:
        assert (
            c.execute("SELECT count(*) FROM identity.otp_send_reservations").fetchone()[
                0
            ]
            == 1
        )


def test_new_operation_race_cannot_bypass_cooldown(otp):
    service, _, _, connect = otp

    def call(_):
        try:
            return service.start(EMAIL, "initial_verification", uuid4(), SOURCE)
        except PublicError as error:
            assert error.spec.status == 429
            return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(call, range(16)))
    assert sum(result is not None for result in results) == 1
    with connect() as c:
        assert (
            c.execute("SELECT count(*) FROM identity.otp_operations").fetchone()[0] == 1
        )


def test_failures_survive_resend_latest_code_only_and_third_try_can_succeed(otp):
    service, _, clock, connect = otp
    first, code = issue(otp)
    for _ in range(2):
        denied(
            422,
            lambda: service.consume(
                first.challenge_id, "initial_verification", incorrect(code), proof_only
            ),
        )
    clock[0] += timedelta(minutes=9)
    latest, current = issue(otp)
    denied(
        422,
        lambda: service.consume(
            first.challenge_id, "initial_verification", code, proof_only
        ),
    )
    clock[0] = NOW + timedelta(minutes=18)
    assert (
        service.consume(
            latest.challenge_id, "initial_verification", current, proof_only
        )
        == latest.challenge_id
    )
    with connect() as c:
        assert (
            c.execute(
                "SELECT failures FROM identity.otp_verification_windows"
            ).fetchone()[0]
            == 2
        )
        assert c.execute(
            "SELECT expires_at FROM identity.otp_verification_windows"
        ).fetchone()[0] == NOW + timedelta(minutes=19)


def test_three_failures_block_resend_until_latest_expiry(otp):
    service, _, clock, connect = otp
    first, code = issue(otp)
    denied(
        422,
        lambda: service.consume(
            first.challenge_id, "initial_verification", incorrect(code), proof_only
        ),
    )
    clock[0] += timedelta(minutes=9)
    latest, current = issue(otp)
    # Bad code syntax also spends an attempt for an active challenge.
    for bad in ("not-a-code", incorrect(current)):
        denied(
            422,
            lambda: service.consume(
                latest.challenge_id, "initial_verification", bad, proof_only
            ),
        )
    clock[0] = latest.expires_at - timedelta(microseconds=1)
    denied(
        429,
        lambda: service.consume(
            latest.challenge_id, "initial_verification", current, proof_only
        ),
    )
    denied(429, lambda: issue(otp))
    clock[0] = latest.expires_at
    denied(
        422,
        lambda: service.consume(
            latest.challenge_id, "initial_verification", current, proof_only
        ),
    )
    fresh, fresh_code = issue(otp)
    assert (
        service.consume(
            fresh.challenge_id, "initial_verification", fresh_code, proof_only
        )
        == fresh.challenge_id
    )
    with connect() as c:
        assert (
            c.execute(
                "SELECT failures FROM identity.otp_verification_windows"
            ).fetchone()[0]
            == 0
        )


def test_wrong_attempt_race_cannot_exceed_three(otp):
    service, _, _, connect = otp
    request, code = issue(otp)

    def fail(_):
        try:
            service.consume(
                request.challenge_id,
                "initial_verification",
                incorrect(code),
                proof_only,
            )
            pytest.fail("Wrong code accepted")
        except PublicError as error:
            return error.spec.status

    with ThreadPoolExecutor(max_workers=16) as pool:
        statuses = list(pool.map(fail, range(16)))
    assert statuses.count(422) == 3 and statuses.count(429) == 13
    with connect() as c:
        assert (
            c.execute("SELECT attempts FROM identity.otp_challenges").fetchone()[0] == 3
        )
        assert (
            c.execute(
                "SELECT failures FROM identity.otp_verification_windows"
            ).fetchone()[0]
            == 3
        )


def test_correct_code_race_only_invokes_callback_once(otp):
    service, _, _, _ = otp
    request, code = issue(otp)
    calls = []

    def apply(c, proof):
        calls.append(proof.challenge_id)
        return proof.challenge_id

    def consume(_):
        try:
            return service.consume(
                request.challenge_id, "initial_verification", code, apply
            )
        except PublicError as error:
            assert error.spec.status == 422
            return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(consume, range(16)))
    assert calls == [request.challenge_id]
    assert sum(result is not None for result in results) == 1


def test_callback_failure_rolls_back_consumption_and_its_mutation(otp):
    service, _, _, connect = otp
    request, code = issue(otp)

    def failed(c, proof):
        c.execute(
            "UPDATE identity.otp_challenges SET attempts = 1 WHERE id = %s",
            (proof.challenge_id,),
        )
        raise RuntimeError("PRIVATE_CALLBACK_DATA")

    denied(
        503,
        lambda: service.consume(
            request.challenge_id, "initial_verification", code, failed
        ),
    )
    with connect() as c:
        assert c.execute(
            "SELECT consumed_at, attempts FROM identity.otp_challenges"
        ).fetchone() == (None, 0)
    assert (
        service.consume(request.challenge_id, "initial_verification", code, proof_only)
        == request.challenge_id
    )


def test_target_limits_cross_purpose_and_hour_boundary(otp):
    service, _, clock, connect = otp
    for index in range(6):
        clock[0] = NOW + timedelta(minutes=index)
        issue(otp, purpose="initial_verification" if index % 2 else "password_reset")
    clock[0] = NOW + timedelta(minutes=6)
    denied(429, lambda: issue(otp))
    clock[0] = NOW + timedelta(hours=1)
    issue(otp)
    with connect() as c:
        assert (
            c.execute("SELECT count(*) FROM identity.otp_send_reservations").fetchone()[
                0
            ]
            == 7
        )


def test_source_limit_across_targets_and_hour_boundary(otp):
    service, _, clock, connect = otp
    for index in range(100):
        request = service.start(
            f"synthetic{index}@example.invalid", "password_reset", uuid4(), SOURCE
        )
        assert request.delivery is None
    denied(
        429,
        lambda: service.start(
            "extra@example.invalid", "password_reset", uuid4(), SOURCE
        ),
    )
    # Different source has its own budget; never accept a browser header string.
    service.start(
        "extra@example.invalid", "password_reset", uuid4(), ip_address("192.0.2.18")
    )
    denied(422, lambda: service.start(EMAIL, "password_reset", uuid4(), "192.0.2.17"))
    clock[0] += timedelta(hours=1)
    issue(otp, purpose="password_reset")


def seed_temporary(otp):
    """Synthetic active account fixture only; not a Step6 activation implementation."""
    service, keys, clock, connect = otp
    # Adopt keys before the synthetic credential state exists.
    service.start("bootstrap@example.invalid", "password_reset", uuid4(), SOURCE)
    identifier = uuid4()
    with connect() as c:
        c.execute(
            "INSERT INTO identity.users (id,account_class,status,created_at,activated_at,expires_at) "
            "VALUES (%s,'temporary','active',%s,%s,%s)",
            (identifier, NOW, NOW, NOW + timedelta(days=14)),
        )
        c.execute(
            "INSERT INTO identity.temporary_credentials (user_id,login_email_key,password_hash) VALUES (%s,%s,'synthetic-not-a-real-hash')",
            (identifier, keys.credential_key(EMAIL)),
        )
        c.execute(
            "INSERT INTO identity.temporary_enrollments (id,login_digest,digest_key_version,first_activated_at,original_expires_at,user_id) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (
                uuid4(),
                keys.target_digest(EMAIL),
                keys.version,
                NOW,
                NOW + timedelta(days=14),
                identifier,
            ),
        )
    return identifier


def test_reset_uses_login_identifier_and_rechecks_account_state(otp):
    service, _, _, connect = otp
    user = seed_temporary(otp)
    request, code = issue(otp, purpose="password_reset")
    denied(
        422,
        lambda: service.consume(
            request.challenge_id, "initial_verification", code, proof_only
        ),
    )
    with connect() as c:
        c.execute(
            "UPDATE identity.users SET status='revoked',revoked_at=%s WHERE id=%s",
            (NOW, user),
        )
    denied(
        409,
        lambda: service.consume(
            request.challenge_id, "password_reset", code, lambda c, p: p.user_id
        ),
    )
    with connect() as c:
        assert (
            c.execute("SELECT consumed_at FROM identity.otp_challenges").fetchone()[0]
            is None
        )


def test_active_reset_proof_and_no_reenrollment_or_contact_lookup(otp):
    service, keys, clock, connect = otp
    user = seed_temporary(otp)
    with connect() as c:
        c.execute(
            "INSERT INTO identity.contacts(user_id,email) VALUES (%s,'editable@example.invalid')",
            (user,),
        )
    request, code = issue(otp, purpose="password_reset")
    result = service.consume(
        request.challenge_id, "password_reset", code, lambda c, p: (p.user_id, p.email)
    )
    assert result == (user, EMAIL)
    clock[0] += timedelta(minutes=1)
    suppressed, no_code = issue(otp)
    assert suppressed.delivery is None and no_code is None
    wrong_contact = service.start(
        "editable@example.invalid", "password_reset", uuid4(), SOURCE
    )
    assert wrong_contact.delivery is None


def test_key_change_fails_closed_and_legacy_adoption_requires_review(otp):
    service, keys, clock, connect = otp
    issue(otp)
    other = TemporaryKeys(
        keys.version, secrets.token_bytes(32), keys.verifier, keys.target_encryption
    )
    changed = PostgresTemporaryChallenges(connect, other, lambda: clock[0])
    denied(503, lambda: changed.start(EMAIL, "initial_verification", uuid4(), SOURCE))
    with connect() as c:
        c.execute(
            "TRUNCATE identity.password_login_windows,identity.otp_operations,identity.otp_send_reservations,identity.otp_verification_windows,identity.otp_key_binding"
        )
    denied(
        503,
        lambda: service.start(
            "another@example.invalid", "initial_verification", uuid4(), SOURCE
        ),
    )


def test_occupied_migration_rollback_refuses_to_erase_security_state(otp):
    _, _, _, connect = otp
    issue(otp)
    migration = (
        ROOT / "database/migrations/20261023192856_identity_otp_transactions.sql"
    ).read_text()
    down = migration.split("-- migrate:down", 1)[1]
    with connect() as c:
        with pytest.raises(psycopg.errors.CheckViolation):
            with c.transaction():
                c.execute(down, prepare=False)
        assert (
            c.execute("SELECT count(*) FROM identity.otp_operations").fetchone()[0] == 1
        )
        assert (
            c.execute("SELECT count(*) FROM identity.otp_challenges").fetchone()[0] == 1
        )


def test_unknown_and_known_reset_have_identical_failed_attempt_statuses(otp):
    service, _, _, connect = otp
    seed_temporary(otp)
    known, code = issue(otp, purpose="password_reset")
    unknown = service.start(
        "unknown@example.invalid", "password_reset", uuid4(), SOURCE
    )
    assert unknown.delivery is None
    for request in (known, unknown):
        for _ in range(3):
            denied(
                422,
                lambda: service.consume(
                    request.challenge_id,
                    "password_reset",
                    "invalid-code",
                    lambda c, p: pytest.fail("Invalid proof"),
                ),
            )
        denied(
            429,
            lambda: service.consume(
                request.challenge_id,
                "password_reset",
                "invalid-code",
                lambda c, p: pytest.fail("Invalid proof"),
            ),
        )


def test_committed_reservation_survives_uncertain_ses_without_retry(otp):
    from app.core.config import Settings
    from app.domains.identity.email import SesEmailSender

    class UncertainClient:
        def __init__(self):
            self.calls = 0

        def send_email(self, **kwargs):
            self.calls += 1
            raise TimeoutError("PRIVATE_PROVIDER_DETAIL")

    service, _, clock, connect = otp
    operation = uuid4()
    request = service.start(EMAIL, "initial_verification", operation, SOURCE)
    client = UncertainClient()
    sender = SesEmailSender(
        Settings(
            environment="test", email_provider="ses", ses_test_recipients=(EMAIL,)
        ),
        client,
    )
    with connect() as c:
        # The reservation is already visible on another connection before send.
        assert (
            c.execute("SELECT count(*) FROM identity.otp_operations").fetchone()[0] == 1
        )
    assert not request.delivery.dispatch(sender, now=clock[0])
    retry = service.start(EMAIL, "initial_verification", operation, SOURCE)
    assert retry.delivery is None and retry.challenge_id == request.challenge_id
    assert not request.delivery.dispatch(sender, now=clock[0])
    assert client.calls == 1


def test_transaction_failure_leaves_no_partial_challenge_or_send_ticket(otp):
    service, _, _, connect = otp
    with connect() as c:
        c.execute(
            "CREATE FUNCTION identity.reject_otp_test() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic rejection'; END $$"
        )
        c.execute(
            "CREATE TRIGGER reject_otp_test BEFORE INSERT ON identity.otp_operations FOR EACH ROW EXECUTE FUNCTION identity.reject_otp_test()"
        )
    try:
        denied(503, lambda: issue(otp))
        with connect() as c:
            for table in (
                "otp_challenges",
                "otp_operations",
                "otp_send_reservations",
                "otp_verification_windows",
                "otp_key_binding",
            ):
                assert (
                    c.execute("SELECT count(*) FROM identity." + table).fetchone()[0]
                    == 0
                )
    finally:
        with connect() as c:
            c.execute("DROP TRIGGER reject_otp_test ON identity.otp_operations")
            c.execute("DROP FUNCTION identity.reject_otp_test()")


def test_enrollment_guard_prevents_renewal_after_credential_cleanup(otp):
    service, _, clock, connect = otp
    user = seed_temporary(otp)
    clock[0] += timedelta(days=14)
    with connect() as c:
        c.execute(
            "DELETE FROM identity.temporary_credentials WHERE user_id=%s", (user,)
        )
    for purpose in ("initial_verification", "password_reset"):
        request, code = issue(otp, purpose=purpose)
        assert request.delivery is None and code is None
        clock[0] += timedelta(minutes=1)
    with connect() as c:
        assert (
            c.execute("SELECT count(*) FROM identity.temporary_enrollments").fetchone()[
                0
            ]
            == 1
        )
