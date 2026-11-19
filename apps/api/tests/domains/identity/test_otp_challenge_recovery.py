"""Real HTTP/SQL OTP abuse recovery; only the external proof decision is doubled."""

from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from apps.api.tests.domains.identity.session_fixtures import (
    EMAIL,
    PASSWORD,
    HEADERS,
    ORIGIN,
    SOURCE,
    activate,
)
from apps.api.tests.domains.identity.test_signin_challenge import challenged_app


def start(browser, purpose, *, email=EMAIL, proof=None, operation=None):
    """Send one real challenge request; generated operations never hit real email."""
    return browser.post(
        f"/auth/temporary/{purpose}-challenges",
        headers=HEADERS | ({"X-CLIP-Challenge-Token": proof} if proof else {}),
        json={"email": email, "operation_id": str(operation or uuid4())},
    )


def finish(browser, purpose, identifier, code, *, proof=None):
    """Exercise actual activation or password reset with a synthetic credential."""
    return browser.post(
        (
            "/auth/temporary/accounts"
            if purpose == "registration"
            else "/auth/temporary/password-resets"
        ),
        headers=HEADERS | ({"X-CLIP-Challenge-Token": proof} if proof else {}),
        json={
            "challenge_id": identifier,
            "code": code,
            (
                "password" if purpose == "registration" else "new_password"
            ): PASSWORD.get_secret_value(),
        },
    )


@pytest.mark.parametrize("purpose", ["registration", "password-reset"])
def test_unverified_stranger_cannot_replace_live_mailbox_code(challenged_app, purpose):
    state, app, *_ = challenged_app
    if purpose == "password-reset":
        activate(state)
    with (
        TestClient(app, base_url=ORIGIN, client=("198.51.100.10", 40000)) as owner,
        TestClient(app, base_url=ORIGIN, client=("203.0.113.50", 40001)) as stranger,
    ):
        original = start(owner, purpose)
        assert original.status_code == 202
        code = state.mail.code()
        state.clock[0] += timedelta(seconds=61)
        denied = start(stranger, purpose)
        assert denied.status_code == 429
        assert denied.headers["x-clip-challenge-site-key"] == "synthetic-site-key"
        assert len(state.mail.messages) == (2 if purpose == "password-reset" else 1)
        assert finish(
            owner, purpose, original.json()["challenge_id"], code
        ).status_code == (201 if purpose == "registration" else 204)


@pytest.mark.parametrize("purpose", ["registration", "password-reset"])
def test_owner_recovers_from_preempted_exhausted_challenge(challenged_app, purpose):
    state, app, *_ = challenged_app
    if purpose == "password-reset":
        activate(state)
    with (
        TestClient(app, base_url=ORIGIN, client=("203.0.113.50", 40000)) as stranger,
        TestClient(app, base_url=ORIGIN, client=("198.51.100.10", 40001)) as owner,
    ):
        intercepted = start(stranger, purpose)
        assert intercepted.status_code == 202
        code = state.mail.code()
        wrong = [
            value for value in ("000000", "111111", "222222", "333333") if value != code
        ][:3]
        for value in wrong:
            assert (
                finish(
                    stranger, purpose, intercepted.json()["challenge_id"], value
                ).status_code
                == 422
            )
        assert (
            finish(owner, purpose, intercepted.json()["challenge_id"], code).status_code
            == 429
        )
        assert start(owner, purpose).status_code == 429
        assert start(owner, purpose, proof="forged-proof").status_code == 429
        assert start(owner, purpose, proof="provider-down").status_code == 503
        recovered = start(owner, purpose, proof="verified-otp-owner")
        assert recovered.status_code == 202
        assert start(owner, purpose, proof="verified-otp-owner").status_code == 429
        assert finish(
            owner, purpose, recovered.json()["challenge_id"], state.mail.code()
        ).status_code == (201 if purpose == "registration" else 204)


def test_suppressed_password_resets_do_not_charge_registration(challenged_app):
    state, app, *_ = challenged_app
    with TestClient(app, base_url=ORIGIN, client=("198.51.100.20", 40000)) as browser:
        for index in range(6):
            state.clock[0] += timedelta(seconds=61)
            assert (
                start(
                    browser, "password-reset", proof=f"verified-reset-{index}"
                ).status_code
                == 202
            )
        assert state.mail.messages == []
        assert start(browser, "registration").status_code == 202
        assert len(state.mail.messages) == 1


@pytest.mark.parametrize("purpose", ["registration", "password-reset"])
def test_shared_source_exhaustion_has_single_use_proof_recovery(
    challenged_app, purpose
):
    state, app, *_ = challenged_app
    if purpose == "password-reset":
        activate(state)
    for index in range(99 if purpose == "password-reset" else 100):
        state.service.challenges.start(
            f"unknown{index}@example.invalid", "password_reset", uuid4(), SOURCE
        )
    with TestClient(app, base_url=ORIGIN, client=(str(SOURCE), 40001)) as owner:
        denied = start(owner, purpose)
        assert denied.status_code == 429
        assert denied.headers["retry-after"] == "3600"
        recovered = start(owner, purpose, proof="verified-nat-owner")
        assert recovered.status_code == 202
        assert start(owner, purpose, proof="verified-nat-owner").status_code == 429
        assert finish(
            owner, purpose, recovered.json()["challenge_id"], state.mail.code()
        ).status_code == (201 if purpose == "registration" else 204)


def test_recovery_operation_is_idempotent_and_cannot_unlock_other_purpose(
    challenged_app,
):
    state, app, *_ = challenged_app
    with TestClient(app, base_url=ORIGIN, client=("198.51.100.20", 40000)) as browser:
        assert start(browser, "registration").status_code == 202
        operation = uuid4()
        recovered = start(
            browser, "registration", proof="verified-resend", operation=operation
        )
        assert recovered.status_code == 202
        count = len(state.mail.messages)
        duplicate = start(browser, "registration", operation=operation)
        assert duplicate.status_code == 202 and duplicate.json() == recovered.json()
        assert len(state.mail.messages) == count
        assert (
            start(browser, "password-reset", proof="verified-resend").status_code == 429
        )


@pytest.mark.parametrize("purpose", ["registration", "password-reset"])
def test_correct_otp_can_recover_exhausted_attempt_budget_without_resend(
    challenged_app, purpose
):
    state, app, *_ = challenged_app
    if purpose == "password-reset":
        activate(state)
    with TestClient(app, base_url=ORIGIN, client=("198.51.100.20", 40000)) as owner:
        challenge = start(owner, purpose)
        assert challenge.status_code == 202
        identifier = challenge.json()["challenge_id"]
        code = state.mail.code()
        wrong = "0" * 6 if code != "0" * 6 else "1" * 6
        for _ in range(3):
            assert finish(owner, purpose, identifier, wrong).status_code == 422
        assert finish(owner, purpose, identifier, code).status_code == 429
        # Extra wrong proof-assisted attempts must not overflow the schema cap.
        assert (
            finish(
                owner, purpose, identifier, wrong, proof="verified-wrong-code"
            ).status_code
            == 422
        )
        assert (
            finish(owner, purpose, identifier, code, proof="forged").status_code == 429
        )
        assert finish(
            owner, purpose, identifier, code, proof="verified-correct-code"
        ).status_code == (201 if purpose == "registration" else 204)
        assert (
            finish(
                owner, purpose, identifier, code, proof="verified-consumed"
            ).status_code
            == 422
        )


@pytest.mark.parametrize("purpose", ["registration", "password-reset"])
def test_api_exhaustion_allows_both_issuance_and_final_otp_operation(
    challenged_app, purpose
):
    from app.application import create_app

    state, _, settings, bindings, _ = challenged_app
    if purpose == "password-reset":
        activate(state)
    app = create_app(
        settings.model_copy(update={"api_write_requests_per_minute": 1}),
        identity=bindings,
    )
    with TestClient(app, base_url=ORIGIN, client=("198.51.100.20", 40000)) as owner:
        # Consume this IP's API write allowance without touching the victim target.
        assert (
            start(owner, "password-reset", email="other@example.invalid").status_code
            == 202
        )
        assert start(owner, purpose).status_code == 429
        challenge = start(owner, purpose, proof="verified-api-issuance")
        assert challenge.status_code == 202
        identifier, code = challenge.json()["challenge_id"], state.mail.code()
        assert finish(owner, purpose, identifier, code).status_code == 429
        assert finish(
            owner, purpose, identifier, code, proof="verified-api-finish"
        ).status_code == (201 if purpose == "registration" else 204)


@pytest.mark.parametrize("purpose", ["registration", "password-reset"])
def test_final_otp_step_recovers_shared_api_limit(challenged_app, purpose):
    from app.application import create_app

    state, _, settings, bindings, _ = challenged_app
    if purpose == "password-reset":
        activate(state)
    app = create_app(
        settings.model_copy(update={"api_write_requests_per_minute": 1}),
        identity=bindings,
    )
    with TestClient(app, base_url=ORIGIN, client=("198.51.100.20", 40000)) as owner:
        requested = start(owner, purpose)
        assert requested.status_code == 202
        identifier, code = requested.json()["challenge_id"], state.mail.code()
        denied = finish(owner, purpose, identifier, code)
        assert denied.status_code == 429
        assert denied.headers["x-clip-challenge-site-key"] == "synthetic-site-key"
        accepted = finish(owner, purpose, identifier, code, proof="verified-completion")
        assert accepted.status_code == (201 if purpose == "registration" else 204)


@pytest.mark.parametrize(
    "mode", ["expired-code", "expired-account", "revoked-account", "wrong-purpose"]
)
def test_verified_proof_cannot_bypass_otp_or_account_lifecycle(challenged_app, mode):
    """Challenge recovery opens one attempt, never revives invalid proof/account state."""
    state, app, *_ = challenged_app
    grant = activate(state)
    if mode == "expired-account":
        state.clock[0] += timedelta(days=14, minutes=-1)
    with TestClient(app, base_url=ORIGIN, client=("198.51.100.20", 40000)) as owner:
        issued = start(owner, "password-reset")
        assert issued.status_code == 202
        identifier, code = issued.json()["challenge_id"], state.mail.code()
        if mode == "expired-code":
            state.clock[0] += timedelta(minutes=11)
        elif mode == "expired-account":
            state.clock[0] += timedelta(minutes=2)
        elif mode == "revoked-account":
            state.service.revoke_account(grant.identity.caller.user_id)
        response = finish(
            owner,
            "registration" if mode == "wrong-purpose" else "password-reset",
            identifier,
            code,
            proof="verified-lifecycle",
        )
        assert response.status_code == (
            422 if mode in {"expired-code", "wrong-purpose"} else 409
        )
