"""Actual HTTP cookie/CSRF/context behavior with real SQL/RSA and synthetic mail."""

from datetime import timedelta
from uuid import uuid4

from fastapi import Depends
from fastapi.testclient import TestClient
import pytest

from app.core.auth import require_caller
from app.domains.identity.http import BrowserPolicy, create_identity_app
from apps.api.tests.domains.identity.session_fixtures import (
    HEADERS,
    ORIGIN,
    EMAIL,
    PASSWORD,
)


def client(state):
    return TestClient(state.app, base_url=ORIGIN, client=("192.0.2.27", 50000))


def signup(state, browser):
    result = browser.post(
        "/auth/temporary/registration-challenges",
        headers=HEADERS,
        json={"email": EMAIL, "operation_id": str(uuid4())},
    )
    assert result.status_code == 202, result.text
    result = browser.post(
        "/auth/temporary/accounts",
        headers=HEADERS,
        json={
            "challenge_id": result.json()["challenge_id"],
            "code": state.mail.code(),
            "password": PASSWORD.get_secret_value(),
        },
    )
    assert result.status_code == 201, result.text
    return result


def test_registration_activation_session_cookie_and_safe_summary(identity_runtime):
    state = identity_runtime
    with client(state) as browser:
        result = signup(state, browser)
        assert set(result.json()) == {
            "user_id",
            "account_class",
            "valid_until",
            "display_name",
        }
        cookie = result.headers["set-cookie"]
        assert "__Host-clip_session=" in cookie
        assert (
            "Secure" in cookie
            and "HttpOnly" in cookie
            and "SameSite=lax" in cookie
            and "Path=/" in cookie
        )
        assert "Domain=" not in cookie
        secret = browser.cookies.get(state.policy.session_cookie)
        assert secret not in result.text and EMAIL not in result.text
        me = browser.get("/me")
        assert (
            me.status_code == 200 and me.json()["user_id"] == result.json()["user_id"]
        )
        assert me.headers["cache-control"] == "no-store"
        csrf = browser.get("/auth/csrf")
        assert csrf.status_code == 200 and set(csrf.json()) == {"csrf_token"}
        assert secret not in csrf.text and csrf.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "https://attacker.invalid", "X-CLIP-Request": "1"},
        {"Origin": ORIGIN},
    ],
)
def test_public_unsafe_requests_require_exact_origin_and_non_simple_header(
    identity_runtime, headers
):
    with client(identity_runtime) as browser:
        result = browser.post("/auth/microsoft/login-attempts", headers=headers)
        assert result.status_code == 403
        assert result.headers["cache-control"] == "no-store"
    with identity_runtime.connect() as c:
        assert (
            c.execute(
                "SELECT count(*) FROM identity.microsoft_login_attempts"
            ).fetchone()[0]
            == 0
        )


def test_logout_requires_session_bound_csrf_and_revokes_cookie(identity_runtime):
    state = identity_runtime
    with client(state) as browser:
        signup(state, browser)
        assert browser.delete("/auth/session", headers=HEADERS).status_code == 403
        assert (
            browser.delete(
                "/auth/session", headers=HEADERS | {"X-CSRF-Token": "wrong"}
            ).status_code
            == 403
        )
        csrf = browser.get("/auth/csrf").json()["csrf_token"]
        result = browser.delete(
            "/auth/session", headers=HEADERS | {"X-CSRF-Token": csrf}
        )
        assert result.status_code == 204 and result.content == b""
        assert "Max-Age=0" in result.headers["set-cookie"]
        assert browser.get("/me").status_code == 401
        assert browser.get("/auth/csrf").status_code == 401


def test_csrf_from_another_session_is_rejected(identity_runtime):
    state = identity_runtime
    with client(state) as first, client(state) as second:
        signup(state, first)
        assert (
            second.post(
                "/auth/temporary/sessions",
                headers=HEADERS,
                json={"email": EMAIL, "password": PASSWORD.get_secret_value()},
            ).status_code
            == 200
        )
        other = second.get("/auth/csrf").json()["csrf_token"]
        assert (
            first.delete(
                "/auth/session", headers=HEADERS | {"X-CSRF-Token": other}
            ).status_code
            == 403
        )
        assert first.get("/me").status_code == 200


def test_server_context_ignores_forged_headers_and_rechecks_revocation(
    identity_runtime,
):
    state = identity_runtime

    @state.app.get("/protected-fixture")
    async def protected(caller=Depends(require_caller)):
        return {"user_id": str(caller.user_id), "account_class": caller.account_class}

    forged = {
        "X-User-Id": str(uuid4()),
        "X-Account-Class": "regular",
        "Authorization": "Bearer synthetic-forged",
    }
    with client(state) as browser:
        assert browser.get("/protected-fixture", headers=forged).status_code == 401
        signed = signup(state, browser).json()
        actual = browser.get(
            "/protected-fixture", headers=forged, params={"user_id": str(uuid4())}
        )
        assert actual.status_code == 200 and actual.json() == {
            "user_id": signed["user_id"],
            "account_class": "temporary",
        }
        from uuid import UUID

        state.service.revoke_account(UUID(signed["user_id"]))
        assert browser.get("/protected-fixture", headers=forged).status_code == 401


def test_expired_session_cookie_does_not_prevent_explicit_password_login(
    identity_runtime,
):
    state = identity_runtime
    with client(state) as browser:
        signup(state, browser)
        old = browser.cookies.get(state.policy.session_cookie)
        state.clock[0] += timedelta(hours=24)
        assert browser.get("/me").status_code == 401
        result = browser.post(
            "/auth/temporary/sessions",
            headers=HEADERS,
            json={"email": EMAIL, "password": PASSWORD.get_secret_value()},
        )
        assert result.status_code == 200
        assert browser.cookies.get(state.policy.session_cookie) != old


def test_real_http_reset_revokes_all_sessions_and_requires_normal_login(
    identity_runtime,
):
    state = identity_runtime
    with client(state) as browser:
        signup(state, browser)
        state.clock[0] += timedelta(minutes=1)
        request = browser.post(
            "/auth/temporary/password-reset-challenges",
            headers=HEADERS,
            json={"email": EMAIL, "operation_id": str(uuid4())},
        )
        assert request.status_code == 202
        new = "synthetic new HTTP password"
        result = browser.post(
            "/auth/temporary/password-resets",
            headers=HEADERS,
            json={
                "challenge_id": request.json()["challenge_id"],
                "code": state.mail.code(),
                "new_password": new,
            },
        )
        assert result.status_code == 204 and result.content == b""
        assert browser.get("/me").status_code == 401
        assert (
            browser.post(
                "/auth/temporary/sessions",
                headers=HEADERS,
                json={"email": EMAIL, "password": PASSWORD.get_secret_value()},
            ).status_code
            == 401
        )
        assert (
            browser.post(
                "/auth/temporary/sessions",
                headers=HEADERS,
                json={"email": EMAIL, "password": new},
            ).status_code
            == 200
        )


def test_microsoft_http_attempt_binds_nonce_and_clears_cookie(
    identity_runtime, signed_tokens
):
    state = identity_runtime
    with client(state) as browser:
        request = browser.post("/auth/microsoft/login-attempts", headers=HEADERS)
        assert request.status_code == 201 and set(request.json()) == {
            "nonce",
            "expires_at",
        }
        attempt = browser.cookies.get(state.policy.attempt_cookie)
        assert attempt not in request.text
        token = signed_tokens.token({"nonce": request.json()["nonce"]})
        result = browser.post(
            "/auth/microsoft/sessions", headers=HEADERS, json={"id_token": token}
        )
        assert result.status_code == 200 and result.json()["account_class"] == "regular"
        assert token not in result.text
        assert browser.cookies.get(state.policy.attempt_cookie) is None
        assert (
            browser.post(
                "/auth/microsoft/sessions", headers=HEADERS, json={"id_token": token}
            ).status_code
            == 401
        )


def test_same_operation_never_resends_after_uncertain_http_delivery(identity_runtime):
    state = identity_runtime
    state.mail.fail = True
    operation = str(uuid4())
    payload = {"email": EMAIL, "operation_id": operation}
    with client(state) as browser:
        first = browser.post(
            "/auth/temporary/registration-challenges", headers=HEADERS, json=payload
        )
        second = browser.post(
            "/auth/temporary/registration-challenges", headers=HEADERS, json=payload
        )
        assert (
            first.status_code == second.status_code == 202
            and first.json() == second.json()
        )
        assert len(state.mail.messages) == 1
        assert set(first.json()) == {"challenge_id", "expires_at"}
        assert "PRIVATE_PROVIDER_DETAIL" not in first.text
        assert browser.get("/me").status_code == 401


def test_ack_body_is_emitted_before_provider_dispatch(identity_runtime):
    state = identity_runtime
    trace = []
    original = state.mail.send

    def capture(*args):
        trace.append("provider")
        original(*args)

    state.mail.send = capture

    async def app(scope, receive, send):
        async def observed(message):
            if message["type"] == "http.response.body" and not message.get(
                "more_body", False
            ):
                trace.append("response")
            await send(message)

        await state.app(scope, receive, observed)

    with TestClient(app, base_url=ORIGIN, client=("192.0.2.27", 50000)) as browser:
        assert (
            browser.post(
                "/auth/temporary/registration-challenges",
                headers=HEADERS,
                json={"email": EMAIL, "operation_id": str(uuid4())},
            ).status_code
            == 202
        )
    assert trace == ["response", "provider"]


def test_unapproved_origin_cannot_read_csrf_and_secure_mode_refuses_http(
    identity_runtime,
):
    state = identity_runtime
    with client(state) as browser:
        signup(state, browser)
        assert (
            browser.get(
                "/auth/csrf", headers={"Origin": "https://evil.invalid"}
            ).status_code
            == 403
        )
    with TestClient(
        state.app, base_url="http://clip-iisc.site", client=("192.0.2.27", 50000)
    ) as browser:
        assert (
            browser.post("/auth/microsoft/login-attempts", headers=HEADERS).status_code
            == 403
        )
        assert browser.get("/me").status_code == 403


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "http://clip-iisc.site",
        "https://clip-iisc.site/path",
        "https://user@clip-iisc.site",
    ],
)
def test_invalid_browser_policy_rejected(origin):
    with pytest.raises(ValueError):
        BrowserPolicy((origin,))
    with pytest.raises(ValueError):
        BrowserPolicy(("http://clip-iisc.site",), development=True)


def test_loopback_development_cookie_is_explicit(identity_runtime, signed_tokens):
    state = identity_runtime
    policy = BrowserPolicy(("http://localhost:5173",), development=True)
    app = create_identity_app(
        state.service,
        policy,
        state.mail,
        signed_tokens.validator(),
        lambda: state.clock[0],
    )
    with TestClient(
        app, base_url="http://localhost:8000", client=("127.0.0.1", 50000)
    ) as browser:
        result = browser.post(
            "/auth/microsoft/login-attempts",
            headers={"Origin": "http://localhost:5173", "X-CLIP-Request": "1"},
        )
        assert result.status_code == 201
        cookie = result.headers["set-cookie"]
        assert "clip_ms_attempt_dev=" in cookie and "HttpOnly" in cookie
        assert "Secure" not in cookie and "Domain=" not in cookie


def test_cors_allows_only_exact_declared_browser_origin(identity_runtime):
    with client(identity_runtime) as browser:
        good = browser.options(
            "/auth/temporary/sessions",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-clip-request",
            },
        )
        assert (
            good.status_code == 200
            and good.headers["access-control-allow-origin"] == ORIGIN
        )
        bad = browser.options(
            "/auth/temporary/sessions",
            headers={
                "Origin": "https://evil.invalid",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert (
            bad.status_code == 400 and "access-control-allow-origin" not in bad.headers
        )


def test_development_policy_refuses_nonloopback_transport(
    identity_runtime, signed_tokens
):
    state = identity_runtime
    policy = BrowserPolicy(("http://localhost:5173",), development=True)
    app = create_identity_app(
        state.service,
        policy,
        state.mail,
        signed_tokens.validator(),
        lambda: state.clock[0],
    )
    with TestClient(
        app, base_url="http://localhost:8000", client=("192.0.2.27", 50000)
    ) as browser:
        assert browser.get("/me").status_code == 403


def test_reset_state_race_is409_only_with_correct_proof(identity_runtime):
    state = identity_runtime
    with client(state) as browser:
        result = signup(state, browser)
        state.clock[0] += timedelta(minutes=1)
        request = browser.post(
            "/auth/temporary/password-reset-challenges",
            headers=HEADERS,
            json={"email": EMAIL, "operation_id": str(uuid4())},
        ).json()
        code = state.mail.code()
        from uuid import UUID

        state.service.revoke_account(UUID(result.json()["user_id"]))
        wrong = ("0" if code[0] != "0" else "1") + code[1:]
        payload = {
            "challenge_id": request["challenge_id"],
            "code": wrong,
            "new_password": "synthetic reset replacement",
        }
        assert (
            browser.post(
                "/auth/temporary/password-resets", headers=HEADERS, json=payload
            ).status_code
            == 422
        )
        payload["code"] = code
        assert (
            browser.post(
                "/auth/temporary/password-resets", headers=HEADERS, json=payload
            ).status_code
            == 409
        )


def test_rejected_origin_cannot_extend_session_idle_time(identity_runtime):
    state = identity_runtime
    with client(state) as browser:
        signup(state, browser)
        original = state.clock[0]
        state.clock[0] += timedelta(hours=1)
        assert (
            browser.get("/me", headers={"Origin": "https://evil.invalid"}).status_code
            == 403
        )
        with state.connect() as c:
            assert (
                c.execute("SELECT last_seen_at FROM identity.sessions").fetchone()[0]
                == original
            )


def test_implemented_http_operation_ids_match_canonical_registry(identity_runtime):
    from contracts.source.identity import HTTP_OPERATIONS

    expected = {
        (operation["path"], operation["method"].lower()): operation["operation_id"]
        for operation in HTTP_OPERATIONS
    }
    schema = identity_runtime.app.openapi()
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            assert operation["operationId"] == expected[(path, method)]
