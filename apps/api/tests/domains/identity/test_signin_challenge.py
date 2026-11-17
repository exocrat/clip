"""Owned SQL/HTTP regressions for target and shared-network sign-in recovery.

Only the external challenge decision is controlled. Passwords, cookies, nonce
checks, counters, transactions and local replay protection use real services.
"""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

from app.application import create_app
from app.core.errors import ERRORS, PublicError
from app.domains.identity.signin_challenge import TurnstileVerifier
from apps.api.tests.domains.identity.session_fixtures import (
    EMAIL,
    PASSWORD,
    SOURCE,
    HEADERS,
    ORIGIN,
    activate,
    challenge,
)
from apps.api.tests.domains.identity.test_application_composition import compose


@pytest.fixture
def challenged_app(identity_runtime, signed_tokens, monkeypatch):
    """Install a controlled provider boundary in the normal real-SQL application."""
    service = identity_runtime.service
    verifier = TurnstileVerifier(
        "synthetic-site-key", SecretStr("synthetic-secret"), (ORIGIN,)
    )
    calls = []

    def verify(token):
        calls.append(token)
        if token == "provider-down":
            raise PublicError(ERRORS[503])
        if not token.startswith("verified-"):
            raise PublicError(ERRORS[429])

    monkeypatch.setattr(verifier, "verify", verify)
    service.challenge = verifier
    application, settings, bindings = compose(identity_runtime, signed_tokens)
    return identity_runtime, application, settings, bindings, calls


def login(client, proof=None, password=None, email=EMAIL):
    """Submit actual credential JSON without recording input values."""
    return client.post(
        "/auth/temporary/sessions",
        headers=HEADERS | ({"X-CLIP-Challenge-Token": proof} if proof else {}),
        json={"email": email, "password": password or PASSWORD.get_secret_value()},
    )


def test_target_lockout_recovery_from_different_ip(challenged_app):
    """RT-52: target history remains, but one verified proof lets the owner sign in."""
    state, app, _, _, calls = challenged_app
    account = activate(state)
    with TestClient(app, base_url=ORIGIN, client=("192.0.2.10", 40000)) as attacker:
        for _ in range(5):
            assert (
                login(attacker, password="synthetic wrong password").status_code == 401
            )
    with TestClient(app, base_url=ORIGIN, client=("192.0.2.11", 40000)) as owner:
        denied = login(owner)
        assert denied.status_code == 429
        assert denied.headers["x-clip-challenge-site-key"] == "synthetic-site-key"
        assert login(owner, "forged-proof").status_code == 429
        assert login(owner, "verified-owner").status_code == 200
        assert owner.get("/me").json()["user_id"] == str(
            account.identity.caller.user_id
        )
        assert (
            login(owner).status_code == 429
        )  # Successful proof never clears abuse history.
        assert login(owner, "verified-owner").status_code == 429  # Local replay check.
        assert (
            login(owner, "verified-wrong", password="still incorrect").status_code
            == 401
        )
        assert login(owner, "verified-fresh").status_code == 200
    assert calls


def exhaust_source(state):
    """Use real rotating-target failures to reach the existing source threshold."""
    for index in range(100):
        with pytest.raises(PublicError) as error:
            state.service.password_login(
                f"unknown{index}@example.invalid", PASSWORD, SOURCE
            )
        assert error.value.spec.status == 401


def test_shared_ip_source_and_api_limits_allow_challenged_signin(challenged_app):
    """RT-65: API and source limits together cannot deny a challenged neighbour."""
    state, _, settings, bindings, _ = challenged_app
    activate(state)
    exhaust_source(state)
    app = create_app(
        settings.model_copy(
            update={
                "api_read_requests_per_minute": 2,
                "api_write_requests_per_minute": 2,
            }
        ),
        identity=bindings,
    )
    with TestClient(app, base_url=ORIGIN, client=(str(SOURCE), 40000)) as attacker:
        assert Counter(attacker.get("/me").status_code for _ in range(601)) == {
            401: 2,
            429: 599,
        }
        for _ in range(3):
            assert login(attacker, email="unused@example.invalid").status_code == 429
    with TestClient(app, base_url=ORIGIN, client=(str(SOURCE), 40001)) as owner:
        owner.cookies.clear()  # Clearing cookies cannot erase either shared history.
        assert login(owner).status_code == 429
        assert login(owner, "verified-password-owner").status_code == 200
        assert owner.get("/me").status_code == 200
    # A fresh independent browser can also start/finish Microsoft SSO at those limits.
    with TestClient(app, base_url=ORIGIN, client=(str(SOURCE), 40002)) as browser:
        denied = browser.post("/auth/microsoft/login-attempts", headers=HEADERS)
        assert denied.status_code == 429
        attempt = browser.post(
            "/auth/microsoft/login-attempts",
            headers=HEADERS | {"X-CLIP-Challenge-Token": "verified-ms-start"},
        )
        assert attempt.status_code == 201
        # Wrong assertions still fail even with a successful challenge.
        bad = browser.post(
            "/auth/microsoft/sessions",
            headers=HEADERS | {"X-CLIP-Challenge-Token": "verified-ms-invalid"},
            json={"id_token": "not-a-jwt"},
        )
        assert bad.status_code in {401, 422}


def test_microsoft_exchange_at_shared_source_limit(challenged_app, signed_tokens):
    """Challenge exception preserves signed nonce validation and one-use redemption."""
    state, app, _, _, _ = challenged_app
    exhaust_source(state)
    with TestClient(app, base_url=ORIGIN, client=(str(SOURCE), 41000)) as browser:
        attempt = browser.post(
            "/auth/microsoft/login-attempts",
            headers=HEADERS | {"X-CLIP-Challenge-Token": "verified-ms-begin"},
        )
        assert attempt.status_code == 201
        token = signed_tokens.token({"nonce": attempt.json()["nonce"]})
        headers = HEADERS | {"X-CLIP-Challenge-Token": "verified-ms-complete"}
        result = browser.post(
            "/auth/microsoft/sessions", headers=headers, json={"id_token": token}
        )
        assert result.status_code == 200
        assert result.json()["account_class"] == "regular"
        assert browser.get("/me").status_code == 200
        assert (
            browser.post(
                "/auth/microsoft/sessions", headers=headers, json={"id_token": token}
            ).status_code
            == 429
        )


def test_provider_failure_does_not_break_normal_login(challenged_app):
    """Provider is unused below threshold; explicit failed checks never issue sessions."""
    state, app, _, _, calls = challenged_app
    activate(state)
    with TestClient(app, base_url=ORIGIN, client=(str(SOURCE), 40000)) as browser:
        assert login(browser, "provider-down").status_code == 503
        assert browser.get("/me").status_code == 401
        assert login(browser).status_code == 200
    assert calls == ["provider-down"]


def test_reset_preserves_revocation_and_challenge_recovery(challenged_app):
    """New password can recover a throttled account; old credentials stay invalid."""
    state, app, _, _, _ = challenged_app
    old_session = activate(state)
    for _ in range(5):
        with pytest.raises(PublicError):
            state.service.password_login(EMAIL, SecretStr("wrong password"), SOURCE)
    reset, code = challenge(state, "password_reset")
    new = SecretStr("synthetic-replacement-password")
    state.service.reset_password(reset.challenge_id, code, new)
    with pytest.raises(PublicError):
        state.service.authenticate(old_session.token.get_secret_value())
    with TestClient(app, base_url=ORIGIN, client=(str(SOURCE), 40000)) as browser:
        assert login(browser, "verified-old-password").status_code == 401
        assert (
            login(
                browser, "verified-new-password", password=new.get_secret_value()
            ).status_code
            == 200
        )


def test_challenge_consumption_is_atomic(challenged_app):
    """Concurrent workers cannot spend the same provider proof twice."""
    state, _, _, _, _ = challenged_app

    def consume():
        try:
            state.service.consume_signin_challenge("verified-concurrent")
            return 200
        except PublicError as error:
            return error.spec.status

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: consume(), range(2))) == [200, 429]


def test_proof_never_exempts_origin_or_other_operations(challenged_app):
    """The exception is neither CSRF bypass nor a general authenticated-write permit."""
    _, app, _, _, calls = challenged_app
    with TestClient(app, base_url=ORIGIN, client=(str(SOURCE), 41000)) as browser:
        denied = browser.post(
            "/auth/temporary/sessions",
            headers={
                "Origin": "https://foreign.example",
                "X-CLIP-Request": "1",
                "X-CLIP-Challenge-Token": "verified-origin-bypass",
            },
            json={"email": EMAIL, "password": PASSWORD.get_secret_value()},
        )
        assert denied.status_code == 403
        denied = browser.patch(
            "/me/profile",
            headers=HEADERS
            | {
                "X-CLIP-Challenge-Token": "verified-profile-bypass",
            },
            json={"display_name": "synthetic"},
        )
        assert denied.status_code == 401
        assert calls == []


@pytest.mark.parametrize("state_mode", ["expired", "revoked"])
def test_challenge_does_not_restore_ineligible_account(challenged_app, state_mode):
    """Human proof cannot revive an expired/revoked temporary account."""
    from datetime import timedelta

    state, app, _, _, _ = challenged_app
    account = activate(state)
    if state_mode == "expired":
        state.clock[0] += timedelta(days=14)
    else:
        state.service.revoke_account(account.identity.caller.user_id)
    with TestClient(app, base_url=ORIGIN, client=(str(SOURCE), 41000)) as browser:
        assert login(browser, "verified-ineligible").status_code == 401
        assert browser.get("/me").status_code == 401


def test_slow_challenges_do_not_fill_normal_request_workers(
    challenged_app, monkeypatch
):
    """Cap provider work at four; excess proofs cannot occupy all normal workers."""
    from threading import Event, Lock

    state, app, _, _, _ = challenged_app
    activate(state)
    release, entered = Event(), Event()
    lock = Lock()
    count = [0]

    def slow_verify(token):
        with lock:
            count[0] += 1
            if count[0] == 4:
                entered.set()
        assert release.wait(10)

    monkeypatch.setattr(state.service.challenge, "verify", slow_verify)
    with TestClient(app, base_url=ORIGIN, client=(str(SOURCE), 41000)) as browser:
        with ThreadPoolExecutor(max_workers=4) as executor:
            pending = [
                executor.submit(login, browser, f"verified-slow-{i}") for i in range(4)
            ]
            try:
                assert entered.wait(5)
                assert browser.get("/me").status_code == 401
                assert login(browser, "verified-excess").status_code == 503
                assert count[0] == 4
            finally:
                release.set()
            assert all(future.result().status_code == 200 for future in pending)
