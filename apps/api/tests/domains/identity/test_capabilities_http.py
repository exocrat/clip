"""Session-backed HTTP probes of policy/public binding; no marketplace route claim."""

from uuid import uuid4

from fastapi import Depends
from fastapi.testclient import TestClient

from app.core.auth import require_caller
from app.domains.identity.capabilities import Capability
from app.domains.identity.public import check_account_eligibility
from apps.api.tests.domains.identity.session_fixtures import (
    HEADERS,
    ORIGIN,
    EMAIL,
    PASSWORD,
)


def client(state):
    return TestClient(state.app, base_url=ORIGIN, client=("192.0.2.27", 50000))


def temporary(state, browser):
    request = browser.post(
        "/auth/temporary/registration-challenges",
        headers=HEADERS,
        json={"email": EMAIL, "operation_id": str(uuid4())},
    ).json()
    result = browser.post(
        "/auth/temporary/accounts",
        headers=HEADERS,
        json={
            "challenge_id": request["challenge_id"],
            "code": state.mail.code(),
            "password": PASSWORD.get_secret_value(),
        },
    )
    assert result.status_code == 201
    return result.json()


def regular(browser, signed_tokens):
    attempt = browser.post("/auth/microsoft/login-attempts", headers=HEADERS).json()
    result = browser.post(
        "/auth/microsoft/sessions",
        headers=HEADERS,
        json={"id_token": signed_tokens.token({"nonce": attempt["nonce"]})},
    )
    assert result.status_code == 200
    return result.json()


def probes(state):
    """Code-owned fixture routes: no listing/thread data or ownership is simulated."""

    @state.app.post("/policy-fixture/sale")
    async def sale(caller=Depends(require_caller)):
        state.service.capabilities.require_capability(
            caller, Capability.MANAGE_SALE_LISTINGS
        )
        return {"allowed": True}

    @state.app.post("/policy-fixture/wanted-response")
    async def wanted(caller=Depends(require_caller)):
        state.service.capabilities.require_capability(
            caller, Capability.START_WANTED_RESPONSE
        )
        return {"allowed": True}

    @state.app.post("/policy-fixture/existing-thread")
    async def existing(caller=Depends(require_caller)):
        state.service.capabilities.require_capability(
            caller, Capability.USE_AUTHORIZED_CONVERSATIONS
        )
        return {"policy_allowed": True}

    @state.app.get("/policy-fixture/eligibility")
    async def eligibility(caller=Depends(require_caller)):
        # Target is server-established caller, never browser query/body/header.
        return await check_account_eligibility(caller.user_id)


def protected_headers(browser):
    csrf = browser.get("/auth/csrf").json()["csrf_token"]
    return HEADERS | {
        "X-CSRF-Token": csrf,
        "X-Account-Class": "regular",
        "X-User-Id": str(uuid4()),
    }


def test_temporary_denials_preserve_existing_thread_policy_and_private_target(
    identity_runtime,
):
    state = identity_runtime
    probes(state)
    with client(state) as browser:
        assert browser.get("/policy-fixture/eligibility").status_code == 401
        temporary(state, browser)
        headers = protected_headers(browser)
        for path in ("sale", "wanted-response"):
            result = browser.post(
                "/policy-fixture/" + path,
                headers=headers,
                json={
                    "account_class": "regular",
                    "can_sell": True,
                    "user_id": str(uuid4()),
                },
            )
            assert result.status_code == 403
        assert (
            browser.post("/policy-fixture/existing-thread", headers=headers).status_code
            == 200
        )
        result = browser.get(
            "/policy-fixture/eligibility", params={"user_id": str(uuid4())}
        )
        assert result.status_code == 200 and result.json() == {"eligible": True}


def test_regular_permissions_use_real_session_and_public_provider(
    identity_runtime, signed_tokens
):
    state = identity_runtime
    probes(state)
    with client(state) as browser:
        regular(browser, signed_tokens)
        headers = protected_headers(browser)
        assert browser.post("/policy-fixture/sale", headers=headers).status_code == 200
        assert (
            browser.post("/policy-fixture/wanted-response", headers=headers).status_code
            == 200
        )
        assert browser.get("/policy-fixture/eligibility").json() == {"eligible": True}


def test_actual_me_uses_fresh_capability_check_and_no_new_lookup_route(
    identity_runtime, monkeypatch
):
    state = identity_runtime
    original = state.service.capabilities.require_capability
    observed = []

    def check(caller, capability):
        observed.append(capability)
        return original(caller, capability)

    monkeypatch.setattr(state.service.capabilities, "require_capability", check)
    with client(state) as browser:
        temporary(state, browser)
        assert browser.get("/me").status_code == 200
        assert observed == [Capability.READ_OWN_PROFILE]
        assert (
            browser.get(
                "/account-eligibility", params={"user_id": str(uuid4())}
            ).status_code
            == 404
        )
        assert browser.get("/me").json()["account_class"] == "temporary"
