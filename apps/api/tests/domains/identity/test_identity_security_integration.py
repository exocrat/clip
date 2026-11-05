"""Step10 missing real SQL/HTTP security journeys, using synthetic inputs only."""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest

from app.contracts.domain_types import ProfilePatch
from app.core.config import ConfigurationError, Settings
from app.core.errors import PublicError
from app.core.logging import SafeJsonFormatter
from clip_test_fixtures import Return, make_test_provider
from apps.api.tests.domains.identity.session_fixtures import (
    EMAIL,
    HEADERS,
    PASSWORD,
    SOURCE,
    activate,
)
from apps.api.tests.domains.identity.test_capabilities_http import protected_headers
from apps.api.tests.domains.identity.test_capabilities_postgres import regular
from apps.api.tests.domains.identity.test_identity_http import client, signup


@pytest.mark.parametrize("mode", ["active", "expired", "revoked"])
def test_temporary_lifecycle_fixture_uses_real_fresh_authorization(
    identity_runtime, temporary_state, mode
):
    state = identity_runtime
    grant = temporary_state(mode)
    if mode == "active":
        assert (
            state.service.authenticate(grant.token.get_secret_value()).caller
            == grant.identity.caller
        )
        assert state.service.contacts.read_contacts(grant.identity.caller).email is None
    else:
        for operation in (
            lambda: state.service.authenticate(grant.token.get_secret_value()),
            lambda: state.service.contacts.read_contacts(grant.identity.caller),
            lambda: state.service.contacts.update_profile(
                grant.identity.caller,
                ProfilePatch(display_name="Synthetic_stale_change"),
            ),
        ):
            with pytest.raises(PublicError) as error:
                operation()
            assert error.value.spec.status == 401


@pytest.mark.parametrize("environment", ["local", "test"])
def test_existing_auth_fake_is_explicit_and_does_not_install_public_auth(
    identity_runtime, environment
):
    state = identity_runtime
    caller = activate(state).identity.caller
    provider = make_test_provider(
        Settings(environment=environment, identity_provider="fake"),
        "identity",
        [Return(caller)],
    )
    assert asyncio.run(provider.call()) is caller
    assert provider.call_count == 1 and provider.remaining == 0
    # A selected scripted fixture proves no public session. Browser input cannot
    # promote the returned context; the production HTTP path still needs a cookie.
    with client(state) as browser:
        result = browser.get(
            "/me/contacts",
            headers={"X-User-Id": str(caller.user_id), "X-Account-Class": "temporary"},
        )
        assert result.status_code == 401


def test_existing_auth_fake_rejects_production_even_with_unvalidated_settings():
    settings = Settings.model_construct(
        environment="production", identity_provider="fake"
    )
    with pytest.raises(ConfigurationError):
        make_test_provider(settings, "identity", [Return(None)])


def test_http_contact_source_survives_reset_without_login_or_lifetime_change(
    identity_runtime, caplog, monkeypatch
):
    state = identity_runtime
    contact = "synthetic-reset-contact@example.com"
    logger = logging.getLogger("clip")
    caplog.set_level(logging.INFO, logger="clip")
    # clip deliberately does not propagate to root. Capture its actual records
    # explicitly so privacy assertions cannot pass against an empty caplog.
    monkeypatch.setattr(logger, "handlers", [*logger.handlers, caplog.handler])
    with client(state) as browser:
        account = signup(state, browser).json()
        headers = protected_headers(browser)
        assert (
            browser.put(
                "/me/contacts/email", headers=headers, json={"value": contact}
            ).status_code
            == 204
        )
        assert (
            browser.patch(
                "/me/profile",
                headers=headers,
                json={"display_name": "Synthetic_retained_name"},
            ).status_code
            == 200
        )
        with state.connect() as c:
            original = c.execute(
                "SELECT activated_at,expires_at FROM identity.users"
            ).fetchone()
        state.clock[0] += timedelta(minutes=1)
        payload = {"email": EMAIL, "operation_id": str(uuid4())}
        request = browser.post(
            "/auth/temporary/password-reset-challenges", headers=HEADERS, json=payload
        )
        assert request.status_code == 202
        sent = len(state.mail.messages)
        repeated = browser.post(
            "/auth/temporary/password-reset-challenges", headers=HEADERS, json=payload
        )
        assert repeated.json() == request.json() and len(state.mail.messages) == sent
        new = "synthetic-Step10-replacement-passphrase"
        reset = {
            "challenge_id": request.json()["challenge_id"],
            "code": state.mail.code(),
            "new_password": new,
        }
        assert (
            browser.post(
                "/auth/temporary/password-resets", headers=HEADERS, json=reset
            ).status_code
            == 204
        )
        assert browser.get("/me/contacts").status_code == 401
        assert (
            browser.post(
                "/auth/temporary/password-resets", headers=HEADERS, json=reset
            ).status_code
            == 422
        )
        assert (
            browser.post(
                "/auth/temporary/sessions",
                headers=HEADERS,
                json={"email": EMAIL, "password": PASSWORD.get_secret_value()},
            ).status_code
            == 401
        )
        login = browser.post(
            "/auth/temporary/sessions",
            headers=HEADERS,
            json={"email": EMAIL, "password": new},
        )
        assert (
            login.status_code == 200 and login.json()["user_id"] == account["user_id"]
        )
        assert contact not in login.text
        assert browser.get("/me/contacts").json() == {
            "email": contact,
            "phone": None,
            "upi_id": None,
        }
        assert browser.get("/me").json()["display_name"] == "Synthetic_retained_name"
        # The old session's CSRF token cannot authorize writes in the new session.
        assert browser.delete("/me/contacts/email", headers=headers).status_code == 403
        headers = protected_headers(browser)
        assert browser.delete("/me/contacts/email", headers=headers).status_code == 204
        assert browser.get("/me/contacts").json()["email"] is None
        state.service.revoke_account(UUID(account["user_id"]))
        assert browser.get("/me/contacts").status_code == 401
        with state.connect() as c:
            assert (
                c.execute(
                    "SELECT activated_at,expires_at FROM identity.users"
                ).fetchone()
                == original
            )
            assert (
                c.execute(
                    "SELECT count(*) FROM identity.temporary_enrollments"
                ).fetchone()[0]
                == 1
            )
        records = [record for record in caplog.records if record.name == "clip"]
        assert len(records) >= 10
        rendered = [
            json.loads(SafeJsonFormatter().format(record)) for record in records
        ]
        assert {row["status"] for row in rendered if "status" in row} >= {
            200,
            201,
            202,
            204,
            401,
            403,
            422,
        }
        assert all(record.msg == "" and record.args == () for record in records)
        assert all(
            set(row)
            <= {
                "timestamp",
                "severity",
                "event",
                "request_id",
                "stage",
                "method",
                "route",
                "status",
                "duration_ms",
            }
            for row in rendered
        )
        # Inspect real formatted output for source contact/password content; body,
        # headers and OTP are excluded by the asserted metadata-only field set.
        assert contact not in json.dumps(rendered) and new not in json.dumps(rendered)


def test_profile_contact_cleanup_batch_excludes_active_and_is_repeat_safe(
    identity_runtime, signed_tokens
):
    state = identity_runtime
    active = regular(state, signed_tokens).identity.caller
    retired = [
        activate(state, email=f"synthetic-retired-{i}@example.invalid").identity.caller
        for i in range(2)
    ]
    for caller in [active, *retired]:
        state.service.contacts.set_contact(
            caller, "email", "synthetic-batch@example.com"
        )
        state.service.contacts.update_profile(
            caller, ProfilePatch(display_name="Synthetic_" + caller.user_id.hex[:12])
        )
    for caller in retired:
        state.service.revoke_account(caller.user_id)
    state.clock[0] += timedelta(days=30)
    for apply in (False, True, True):
        result = state.cleanup.run(apply=apply, batch_size=1)
        assert result.counts["contacts"] == result.counts["profiles"] == 1
    assert state.cleanup.run(apply=True, batch_size=1).counts["profiles"] == 0
    with state.connect() as c:
        assert c.execute("SELECT user_id FROM identity.contacts").fetchall() == [
            (active.user_id,)
        ]
        assert c.execute(
            "SELECT display_name,profile_removed_at FROM identity.users WHERE id=%s",
            (active.user_id,),
        ).fetchone() == ("Synthetic_" + active.user_id.hex[:12], None)
        assert c.execute("SELECT count(*) FROM identity.users").fetchone()[0] == 3
        assert (
            c.execute("SELECT count(*) FROM identity.temporary_enrollments").fetchone()[
                0
            ]
            == 2
        )


def test_terminal_cleanup_race_cannot_restore_profile_or_contacts(identity_runtime):
    state = identity_runtime
    caller = activate(state).identity.caller
    state.service.contacts.set_contact(caller, "phone", "+919876543210")
    state.service.contacts.update_profile(
        caller, ProfilePatch(display_name="Synthetic_retired_name")
    )
    state.service.revoke_account(caller.user_id)
    state.clock[0] += timedelta(days=30)
    barrier = Barrier(6)

    def run(index):
        barrier.wait(timeout=10)
        if index % 2 == 0:
            return state.cleanup.run(apply=True).counts
        for operation in (
            lambda: state.service.contacts.set_contact(
                caller, "phone", "+919876543210"
            ),
            lambda: state.service.contacts.update_profile(
                caller, ProfilePatch(display_name="Forbidden_restoration")
            ),
        ):
            with pytest.raises(PublicError) as error:
                operation()
            assert error.value.spec.status == 401
        return None

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(run, range(6)))
    assert sum(row["contacts"] for row in results if row) == 1
    assert sum(row["profiles"] for row in results if row) == 1
    with state.connect() as c:
        assert c.execute("SELECT count(*) FROM identity.contacts").fetchone()[0] == 0
        assert c.execute(
            "SELECT display_name,profile_removed_at FROM identity.users"
        ).fetchone() == (None, state.clock[0])
        assert (
            c.execute("SELECT count(*) FROM identity.temporary_enrollments").fetchone()[
                0
            ]
            == 1
        )


def test_expired_unused_otp_cleanup_exact_boundary_preserves_request(identity_runtime):
    state = identity_runtime
    request = state.service.challenges.start(
        EMAIL, "initial_verification", uuid4(), SOURCE
    )
    state.clock[0] = (
        request.expires_at + timedelta(hours=24) - timedelta(microseconds=1)
    )
    assert state.cleanup.run(apply=True).counts["otp_challenges"] == 0
    state.clock[0] += timedelta(microseconds=1)
    assert state.cleanup.run(apply=True).counts["otp_challenges"] == 1
    with state.connect() as c:
        assert (
            c.execute("SELECT count(*) FROM identity.otp_operations").fetchone()[0] == 1
        )


def test_revoked_session_cleanup_uses_earlier_terminal_time(identity_runtime):
    state = identity_runtime
    grant = activate(state)
    state.service.logout(grant.token.get_secret_value())
    terminal = state.clock[0]
    state.clock[0] = terminal + timedelta(days=7) - timedelta(microseconds=1)
    assert state.cleanup.run(apply=True).counts["sessions"] == 0
    state.clock[0] += timedelta(microseconds=1)
    assert state.cleanup.run(apply=True).counts["sessions"] == 1
    with state.connect() as c:
        assert c.execute("SELECT count(*) FROM identity.users").fetchone()[0] == 1
        assert (
            c.execute("SELECT count(*) FROM identity.temporary_credentials").fetchone()[
                0
            ]
            == 1
        )
