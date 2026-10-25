"""Real Identity cookies/SQL and Listings routes in the normal application factory.

Only the upstream signer/mail boundary is controlled. No fake caller dependency,
real provider, shared database, image storage or app-config credential discovery.
"""

from datetime import timedelta
from urllib.parse import quote, urlencode
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import FastAPI
from pydantic import SecretStr
import pytest

from app.core.config import ConfigurationError, Settings
from app.core.errors import install_error_handlers
from app.domains.identity.http import (
    IdentityBrowserMiddleware,
    IdentityHttpDependencies,
    install_identity_http,
)
from app.application import create_app
from apps.api.tests.domains.identity.session_fixtures import (
    EMAIL,
    HEADERS,
    ORIGIN,
    PASSWORD,
)


def compose(state, signed_tokens):
    """Use the owned disposable socket/credentials for the actual async store too."""
    with state.connect() as connection:
        info = connection.info
        dsn = (
            "postgresql:///"
            + quote(info.dbname, safe="")
            + "?"
            + urlencode(
                {
                    "host": info.host,
                    "port": info.port,
                    "user": info.user,
                    "password": info.password,
                    "sslmode": "disable",
                    "connect_timeout": 3,
                }
            )
        )
    bindings = IdentityHttpDependencies(
        state.service,
        state.policy,
        state.mail,
        signed_tokens.validator(),
        lambda: state.clock[0],
    )
    settings = Settings(environment="test", database_url=SecretStr(dsn))
    return create_app(settings, identity=bindings), settings, bindings


def regular(browser, signed_tokens):
    """Use server nonce/cookie and an actual signed synthetic assertion exchange."""
    attempt = browser.post("/auth/microsoft/login-attempts", headers=HEADERS)
    assert attempt.status_code == 201
    token = signed_tokens.token({"nonce": attempt.json()["nonce"]})
    result = browser.post(
        "/auth/microsoft/sessions", headers=HEADERS, json={"id_token": token}
    )
    assert result.status_code == 200
    assert result.json()["account_class"] == "regular"
    return result.json()


def temporary(browser, state):
    """Activate via real OTP reservation/mail-ticket/consumption/account/session."""
    requested = browser.post(
        "/auth/temporary/registration-challenges",
        headers=HEADERS,
        json={"email": EMAIL, "operation_id": str(uuid4())},
    )
    assert requested.status_code == 202
    result = browser.post(
        "/auth/temporary/accounts",
        headers=HEADERS,
        json={
            "challenge_id": requested.json()["challenge_id"],
            "code": state.mail.code(),
            "password": PASSWORD.get_secret_value(),
        },
    )
    assert result.status_code == 201
    return result.json()


def test_real_cookie_enables_existing_listings_and_own_contact_routes(
    identity_runtime, signed_tokens
):
    state = identity_runtime
    application, _, _ = compose(state, signed_tokens)
    with TestClient(
        application, base_url=ORIGIN, client=("192.0.2.27", 50000)
    ) as browser:
        assert browser.get("/health").json() == {"status": "ok"}
        assert browser.get("/catalogue").status_code == 401
        result = regular(browser, signed_tokens)
        catalogue = browser.get("/catalogue")
        assert catalogue.status_code == 200
        assert len(catalogue.json()["categories"]) == 8
        assert catalogue.headers["cache-control"] == "no-store"
        assert catalogue.headers.get("x-request-id")
        listings = browser.get("/me/listings")
        assert listings.status_code == 200 and listings.json()["items"] == []
        assert browser.get("/me").json()["user_id"] == result["user_id"]
        csrf = browser.get("/auth/csrf").json()["csrf_token"]
        assert (
            browser.put(
                "/me/contacts/phone", headers=HEADERS, json={"value": "+12025550100"}
            ).status_code
            == 403
        )
        saved = browser.put(
            "/me/contacts/phone",
            headers=HEADERS | {"X-CSRF-Token": csrf},
            json={"value": "+12025550100"},
        )
        assert saved.status_code == 204
        assert browser.get("/me/contacts").json()["phone"] == "+12025550100"
        assert (
            browser.delete(
                "/auth/session", headers=HEADERS | {"X-CSRF-Token": csrf}
            ).status_code
            == 204
        )
        assert browser.get("/catalogue").status_code == 401
    assert application.state.listings_store is not None
    assert application.state.listings_store._pool.closed


def test_temporary_cookie_does_not_authorize_seller_endpoints(
    identity_runtime, signed_tokens
):
    state = identity_runtime
    application, _, _ = compose(state, signed_tokens)
    with TestClient(
        application, base_url=ORIGIN, client=("192.0.2.27", 50000)
    ) as browser:
        account = temporary(browser, state)
        assert browser.get("/me").json()["account_class"] == "temporary"
        assert browser.get("/catalogue").status_code == 200
        # Existing owner-list reads are scoped to the actor and may return empty;
        # the reviewed restriction is on creating/managing sale listings.
        owned = browser.get("/me/listings")
        assert owned.status_code == 200 and owned.json()["items"] == []
        csrf = browser.get("/auth/csrf").json()["csrf_token"]
        denied = browser.post(
            "/image-uploads",
            headers=HEADERS
            | {
                "X-CSRF-Token": csrf,
                "X-Account-Class": "regular",
                "X-User-ID": str(uuid4()),
            },
            json={
                "media_type": "image/png",
                "size_bytes": 32,
                "operation_id": str(uuid4()),
            },
        )
        assert denied.status_code == 403
        sale = browser.post(
            "/listings",
            headers=HEADERS | {"X-CSRF-Token": csrf},
            json={
                "title": "Synthetic sale",
                "description": "Synthetic test only",
                "category_code": "mobile_phones",
                "condition_code": "used_good",
                "asking_price_paise": 100,
                "negotiable": False,
                "image_upload_ids": [str(uuid4())],
                "operation_id": str(uuid4()),
            },
        )
        assert sale.status_code == 403
        assert browser.get("/me").json()["user_id"] == account["user_id"]


@pytest.mark.parametrize("terminal", ["revoked", "expired"])
def test_listing_routes_recheck_real_session_lifecycle(
    identity_runtime, signed_tokens, terminal
):
    state = identity_runtime
    application, _, _ = compose(state, signed_tokens)
    with TestClient(
        application, base_url=ORIGIN, client=("192.0.2.27", 50000)
    ) as browser:
        user = regular(browser, signed_tokens)
        assert browser.get("/catalogue").status_code == 200
        if terminal == "expired":
            state.clock[0] += timedelta(days=8)
        else:
            from uuid import UUID

            state.service.revoke_account(UUID(user["user_id"]))
        assert browser.get("/catalogue").status_code == 401
        assert browser.get("/me/listings").status_code == 401


def test_untrusted_origin_and_csrf_cannot_mutate_listings(
    identity_runtime, signed_tokens
):
    application, _, _ = compose(identity_runtime, signed_tokens)
    with TestClient(
        application, base_url=ORIGIN, client=("192.0.2.27", 50000)
    ) as browser:
        regular(browser, signed_tokens)
        payload = {
            "media_type": "image/png",
            "size_bytes": 32,
            "operation_id": str(uuid4()),
        }
        assert (
            browser.post("/image-uploads", headers=HEADERS, json=payload).status_code
            == 403
        )
        csrf = browser.get("/auth/csrf").json()["csrf_token"]
        hostile = HEADERS | {
            "Origin": "https://hostile.example.invalid",
            "X-CSRF-Token": csrf,
        }
        assert (
            browser.post("/image-uploads", headers=hostile, json=payload).status_code
            == 403
        )


def test_composition_is_per_app_and_installed_once(identity_runtime, signed_tokens):
    default_app = create_app(Settings(environment="test"))
    original = set(default_app.openapi()["paths"])
    application, settings, bindings = compose(identity_runtime, signed_tokens)
    other = create_app(settings)
    assert "/auth/microsoft/sessions" in application.openapi()["paths"]
    assert "/auth/microsoft/sessions" not in other.openapi()["paths"]
    assert set(default_app.openapi()["paths"]) == original
    assert (
        sum(m.cls is IdentityBrowserMiddleware for m in application.user_middleware)
        == 1
    )
    with pytest.raises(ValueError, match="already installed"):
        install_identity_http(application, bindings)
    assert application.dependency_overrides == {}


def test_factory_rejects_production_missing_database_and_demo_mix(
    identity_runtime, signed_tokens
):
    _, settings, bindings = compose(identity_runtime, signed_tokens)
    with pytest.raises(ConfigurationError):
        create_app(Settings(environment="test"), identity=bindings)
    with pytest.raises(ConfigurationError):
        create_app(
            Settings(environment="production", database_url=settings.database_url),
            identity=bindings,
        )
    with pytest.raises(ConfigurationError):
        create_app(
            Settings(
                environment="test",
                database_url=settings.database_url,
                development_auth=True,
            ),
            identity=bindings,
        )
    demo = Settings(
        environment="test",
        development_auth=True,
        isolated_listings_test_caller=True,
        serve_web_app=True,
        database_url=SecretStr("postgresql://synthetic@localhost/clip_test_listings"),
        storage_provider="s3",
        image_bucket="clip-test-listings-images-ap-south-1-li02",
        image_region="ap-south-1",
        image_key_prefix="listings/test/synthetic",
        isolated_listings_max_count=10,
    )
    with pytest.raises(ConfigurationError):
        create_app(demo, identity=bindings)


def test_identity_api_prefix_matches_same_origin_web_transport(
    identity_runtime, signed_tokens
):
    """Hosted /api auth routes preserve the reviewed public-write exemption."""
    state = identity_runtime
    bindings = IdentityHttpDependencies(
        state.service,
        state.policy,
        state.mail,
        signed_tokens.validator(),
        lambda: state.clock[0],
    )
    application = FastAPI()
    install_error_handlers(application)
    install_identity_http(application, bindings, path_prefix="/api")

    with TestClient(
        application, base_url=ORIGIN, client=("192.0.2.27", 50000)
    ) as browser:
        attempt = browser.post(
            "/api/auth/temporary/sessions",
            headers={"Origin": ORIGIN, "X-CLIP-Request": "1"},
            json={"email": EMAIL, "password": "not-the-password"},
        )
        # A public authentication write is routed and reaches its normal
        # credential check without a CSRF token; it is not a successful login.
        assert attempt.status_code == 401


def test_hosted_test_app_serves_ui_and_identity_under_api_prefix(
    monkeypatch, tmp_path, identity_runtime, signed_tokens
):
    """The explicit same-origin hosted mode wires Identity beside feature APIs."""
    state = identity_runtime
    bindings = IdentityHttpDependencies(
        state.service,
        state.policy,
        state.mail,
        signed_tokens.validator(),
        lambda: state.clock[0],
    )
    web_root = tmp_path / "web"
    (web_root / "assets").mkdir(parents=True)
    (web_root / "index.html").write_text("<html></html>")
    monkeypatch.setattr("app.application.Path", lambda _path: web_root)
    settings = Settings(
        environment="test",
        identity_provider="microsoft",
        email_provider="dual",
        ses_test_recipients=(EMAIL,),
        identity_runtime_enabled=True,
        identity_browser_origins=(ORIGIN,),
        serve_web_app=True,
        database_url=SecretStr("postgresql://listings@db.invalid/clip_test"),
    )

    application = create_app(settings, identity=bindings)

    paths = application.openapi()["paths"]
    assert "/api/auth/microsoft/sessions" in paths
    assert "/api/auth/csrf" in paths
    assert "/auth/microsoft/sessions" not in paths
    assert "/api/listings" in paths


def test_incomplete_dependency_bundle_rejected(identity_runtime, signed_tokens):
    state = identity_runtime
    with pytest.raises(ValueError, match="Complete trusted"):
        IdentityHttpDependencies(
            state.service,
            state.policy,
            None,
            signed_tokens.validator(),
            lambda: state.clock[0],
        )


@pytest.mark.parametrize("account_class", ["regular", "temporary"])
def test_real_session_reaches_accepted_search_routes(
    identity_runtime, signed_tokens, account_class
):
    """Merge regression: actual shared stores/routes use the current Identity cookie.

    These empty-page reads verify composition only, not Step14's complete matrix,
    Search readiness or real Microsoft/mail delivery. No consumer fake is installed.
    """
    state = identity_runtime
    application, _, _ = compose(state, signed_tokens)
    with TestClient(
        application, base_url=ORIGIN, client=("192.0.2.27", 50000)
    ) as browser:
        if account_class == "regular":
            regular(browser, signed_tokens)
        else:
            temporary(browser, state)
        for path in ("/wanted-requests", "/me/wanted-requests", "/me/saved-listings"):
            result = browser.get(path)
            assert result.status_code == 200, path
            assert result.json()["items"] == []
            assert "no-store" in result.headers["cache-control"]
        # Bindings are app-specific; unconfigured default remains unavailable.
        assert browser.get("/me").json()["account_class"] == account_class
