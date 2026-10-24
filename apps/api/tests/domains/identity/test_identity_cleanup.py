"""Real bounded retention cutoffs and guard preservation in owned disposable SQL."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4
from psycopg.conninfo import make_conninfo

import pytest

from app.core.errors import PublicError
from apps.api.tests.domains.identity.session_fixtures import (
    activate,
    challenge,
    EMAIL,
    PASSWORD,
    SOURCE,
)


def count(state, table):
    with state.connect() as c:
        return c.execute("SELECT count(*) FROM identity." + table).fetchone()[0]


def test_dry_run_default_and_exact_otp_cutoff_preserve_guards(identity_runtime):
    state = identity_runtime
    activate(state)
    state.service.password_login(EMAIL, PASSWORD, SOURCE)
    start = state.clock[0]
    state.clock[0] = start + timedelta(hours=24) - timedelta(microseconds=1)
    assert state.cleanup.run().counts["otp_challenges"] == 0
    state.clock[0] = start + timedelta(hours=24)
    result = state.cleanup.run()
    assert result.dry_run and result.counts["otp_challenges"] == 1
    assert count(state, "otp_challenges") == 1
    applied = state.cleanup.run(apply=True)
    assert not applied.dry_run and applied.counts["otp_challenges"] == 1
    assert count(state, "otp_challenges") == 0
    assert count(state, "otp_operations") == 1
    assert count(state, "temporary_enrollments") == 1
    assert count(state, "temporary_credentials") == 1
    assert count(state, "sessions") == 2
    assert count(state, "otp_send_reservations") == 1
    state.clock[0] += timedelta(hours=1)
    applied = state.cleanup.run(apply=True)
    assert applied.counts["otp_send_reservations"] == 1
    assert applied.counts["otp_verification_windows"] == 1
    assert count(state, "otp_operations") == count(state, "otp_key_binding") == 1
    assert all(v == 0 for v in state.cleanup.run(apply=True).counts.values())


def test_sessions_purge_seven_days_after_idle_terminal_event(identity_runtime):
    state = identity_runtime
    grant = activate(state)
    start = state.clock[0]
    state.clock[0] = start + timedelta(days=8) - timedelta(microseconds=1)
    assert state.cleanup.run().counts["sessions"] == 0
    state.clock[0] += timedelta(microseconds=1)
    assert state.cleanup.run(apply=True).counts["sessions"] == 1
    assert count(state, "users") == count(state, "temporary_credentials") == 1


def test_hash_removal_at_permanent_expiry_preserves_original_enrollment(
    identity_runtime,
):
    state = identity_runtime
    grant = activate(state)
    user = grant.identity.caller.user_id
    state.clock[0] += timedelta(days=14) - timedelta(microseconds=1)
    assert state.cleanup.run().counts["temporary_credentials"] == 0
    state.clock[0] += timedelta(microseconds=1)
    assert state.cleanup.run(apply=True).counts["temporary_credentials"] == 1
    assert (
        count(state, "users")
        == count(state, "temporary_enrollments")
        == count(state, "otp_operations")
        == 1
    )
    result = state.service.challenges.start(
        EMAIL, "initial_verification", uuid4(), SOURCE
    )
    assert result.delivery is None


def test_revoked_hash_is_eligible_immediately_but_guard_and_contacts_survive(
    identity_runtime,
):
    state = identity_runtime
    grant = activate(state)
    user = grant.identity.caller.user_id
    with state.connect() as c:
        c.execute(
            "INSERT INTO identity.contacts(user_id,email) VALUES (%s,'private-synthetic@example.invalid')",
            (user,),
        )
    state.service.revoke_account(user)
    assert state.cleanup.run(apply=True).counts["temporary_credentials"] == 1
    assert count(state, "temporary_enrollments") == count(state, "contacts") == 1
    assert count(state, "sessions") == 1


def test_supersession_counts_as_first_unusable_event(identity_runtime):
    state = identity_runtime
    first, _ = challenge(state)
    state.clock[0] += timedelta(minutes=1)
    latest, _ = challenge(state)
    state.clock[0] += timedelta(hours=24)
    assert state.cleanup.run(apply=True).counts["otp_challenges"] == 1
    with state.connect() as c:
        assert (
            c.execute("SELECT id FROM identity.otp_challenges").fetchone()[0]
            == latest.challenge_id
        )
    assert count(state, "otp_operations") == 2


def test_batch_limit_and_repeated_apply_are_bounded(identity_runtime):
    state = identity_runtime
    activate(state)
    activate(state, email="second@example.invalid")
    state.clock[0] += timedelta(hours=24)
    assert state.cleanup.run(apply=True, batch_size=1).counts["otp_challenges"] == 1
    assert count(state, "otp_challenges") == 1
    assert state.cleanup.run(apply=True, batch_size=1).counts["otp_challenges"] == 1
    assert state.cleanup.run(apply=True, batch_size=1).counts["otp_challenges"] == 0
    for invalid in (0, -1, 1001, True):
        with pytest.raises(ValueError):
            state.cleanup.run(batch_size=invalid)


def test_cleanup_login_race_cannot_restore_expired_access(identity_runtime):
    state = identity_runtime
    activate(state)
    state.clock[0] += timedelta(days=14)

    def call(index):
        if index % 2:
            return state.cleanup.run(apply=True).counts
        try:
            state.service.password_login(EMAIL, PASSWORD, SOURCE)
            pytest.fail("Expired login restored access")
        except PublicError as error:
            assert error.spec.status in (401, 429)
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(call, range(12)))
    assert count(state, "temporary_credentials") == 0
    assert count(state, "temporary_enrollments") == 1


def test_cli_refuses_missing_credentials_without_echoing_environment():
    root = Path(__file__).resolve().parents[5]
    env = {key: os.environ[key] for key in ("HOME", "PATH")}
    result = subprocess.run(
        [
            "uv",
            "run",
            "--locked",
            "python",
            "scripts/identity_cleanup.py",
            "--expected-database",
            "clip_test_nonexistent",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "target/configuration/checks require review" in result.stderr


def test_cleaned_challenge_operation_cannot_resend(identity_runtime):
    state = identity_runtime
    operation = uuid4()
    original = state.service.challenges.start(
        EMAIL, "initial_verification", operation, SOURCE
    )
    state.clock[0] = original.expires_at + timedelta(hours=24)
    state.cleanup.run(apply=True)
    assert count(state, "otp_challenges") == 0
    replay = state.service.challenges.start(
        EMAIL, "initial_verification", operation, SOURCE
    )
    assert (
        replay.challenge_id == original.challenge_id
        and replay.expires_at == original.expires_at
        and replay.delivery is None
    )
    assert count(state, "otp_operations") == 1


def test_cli_target_check_dry_run_and_apply_only_owned_database(identity_runtime):
    state = identity_runtime
    activate(state)
    with state.connect() as c:
        # Synthetic fixture credential only, never printed or placed in argv.
        dsn = make_conninfo(c.info.dsn, password=c.info.password)
    root = Path(__file__).resolve().parents[5]
    env = {key: os.environ[key] for key in ("HOME", "PATH")}
    env["CLIP_IDENTITY_DATABASE_URL"] = dsn
    args = [
        "uv",
        "run",
        "--locked",
        "python",
        "scripts/identity_cleanup.py",
        "--expected-database",
        "clip_test_identity",
    ]
    result = subprocess.run(
        args, cwd=root, env=env, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0 and json.loads(result.stdout)["dry_run"] is True
    wrong = subprocess.run(
        args[:-1] + ["clip_test_wrong", "--apply"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert wrong.returncode == 1 and wrong.stdout == ""
    applied = subprocess.run(
        args + ["--apply"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert applied.returncode == 0 and json.loads(applied.stdout)["dry_run"] is False
    assert count(state, "users") == 1
