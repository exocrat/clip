"""Offline session-only composition checks; no real secret, SQL or provider I/O."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import httpx2
from pydantic import SecretStr
import pytest
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.application import create_app
from app.contracts.domain_types import AccountEligibility
from app.core.auth import CallerContext
from app.core.config import ConfigurationError, Settings
from app.core.errors import ERRORS, PublicError
from app.core.pagination import Page
from app.domains.identity.http import (
    BrowserPolicy,
    IdentityReadDependencies,
    install_identity_reads,
)
from app.domains.identity.sessions import IdentitySessions, SessionIdentity
from app.domains.listings.browse_routes import browse_service
from app.domains.listings.browse import ListingsBrowseService, PublicBrowseIdentity

ORIGIN = "https://clip-iisc.site"
USER = UUID("10000000-0000-4000-8000-000000000001")
SESSION = UUID("20000000-0000-4000-8000-000000000001")


def hosted_settings() -> Settings:
    """Use synthetic configuration satisfying the existing hosted test gate."""
    return Settings(
        environment="test",
        identity_runtime_enabled=True,
        identity_provider="microsoft",
        email_provider="dual",
        ses_test_recipients=("fixture@example.invalid",),
        identity_browser_origins=(ORIGIN,),
        database_url=SecretStr("postgresql://fixture@database.invalid/clip"),
    )


def read_bindings(account_class="temporary"):
    """Mock only the real service boundary; no fake default or HTTP auth bypass."""
    sessions = MagicMock(spec=IdentitySessions)
    sessions.capabilities = SimpleNamespace(
        check_account_eligibility=AsyncMock(
            return_value=AccountEligibility(eligible=True)
        )
    )
    sessions.contacts = SimpleNamespace(
        get_shareable_contact_options=AsyncMock(),
        get_selected_own_contacts=AsyncMock(),
    )
    sessions.authenticate.return_value = SessionIdentity(
        CallerContext(USER, account_class, datetime(2099, 1, 1, tzinfo=UTC)),
        SESSION,
        None,
    )
    return IdentityReadDependencies(sessions, BrowserPolicy((ORIGIN,)))


def request(
    application,
    path="/api/listings",
    *,
    scheme="https",
    headers=None,
    peer="127.0.0.1",
):
    """Use in-process ASGI without entering startup or opening sockets."""

    async def run():
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=application, client=(peer, 12345)),
            base_url=f"{scheme}://clip-iisc.site",
        ) as client:
            return await client.get(path, headers=headers or {})

    return asyncio.run(run())


@pytest.fixture
def bound_app(monkeypatch):
    """Exercise the real middleware/public eligibility dispatch with offline ports.

    Inline only the synthetic authenticate call because this sandbox cannot use
    its threadpool reliably; production keeps Starlette's threadpool dispatch.
    """
    import app.domains.identity.http as transport

    async def inline(function, *args):
        return function(*args)

    monkeypatch.setattr(transport, "run_in_threadpool", inline)
    bindings = read_bindings()
    application = create_app(
        hosted_settings(), identity_reads=bindings, listings_read_only=True
    )
    store = SimpleNamespace(
        browse_available_listings=AsyncMock(return_value=Page((), 1, 20, False))
    )

    async def provider():
        return ListingsBrowseService(store, PublicBrowseIdentity())

    application.dependency_overrides[browse_service] = provider
    return application, bindings, store


@pytest.mark.parametrize("account_class", ["regular", "temporary"])
def test_cookie_authentication_and_real_public_eligibility_binding(
    bound_app, account_class
):
    application, bindings, store = bound_app
    identity = bindings.sessions.authenticate.return_value
    bindings.sessions.authenticate.return_value = SessionIdentity(
        CallerContext(USER, account_class, identity.caller.valid_until), SESSION, None
    )
    response = request(
        application, headers={"Cookie": "__Host-clip_session=synthetic-cookie"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "page_size": 20,
        "has_next": False,
    }
    assert response.headers["cache-control"] == "no-store"
    assert "synthetic-cookie" not in response.text
    bindings.sessions.authenticate.assert_called_once_with("synthetic-cookie")
    bindings.sessions.capabilities.check_account_eligibility.assert_awaited_once_with(
        USER, None
    )
    store.browse_available_listings.assert_awaited_once()
    assert set(application.openapi()["paths"]) == {
        "/health",
        "/api/listings",
        "/api/listings/{listing_id}",
    }


@pytest.mark.parametrize("failure", [401, 503])
def test_session_denial_and_dependency_failure_stop_before_listing_data(
    bound_app, failure
):
    application, bindings, store = bound_app
    bindings.sessions.authenticate.side_effect = PublicError(ERRORS[failure])
    response = request(
        application, headers={"Cookie": "__Host-clip_session=synthetic-cookie"}
    )
    assert response.status_code == failure
    assert response.json()["error"]["code"] == ERRORS[failure].code
    store.browse_available_listings.assert_not_awaited()


def test_missing_cookie_cannot_be_replaced_by_user_headers(bound_app):
    application, bindings, store = bound_app
    response = request(application, headers={"X-User-Id": str(USER)})
    assert response.status_code == 401
    bindings.sessions.authenticate.assert_not_called()
    store.browse_available_listings.assert_not_awaited()


@pytest.mark.parametrize(
    ("peer", "forwarded_proto", "expected"),
    [
        ("127.0.0.1", "https", 200),
        ("127.0.0.1", "http", 403),
        ("127.0.0.1", None, 403),
        ("192.0.2.45", "https", 403),
    ],
)
def test_uvicorn_proxy_scheme_requires_a_trusted_peer_and_https(
    bound_app, peer, forwarded_proto, expected
):
    """Exercise Uvicorn's proxy policy with synthetic ASGI peers and sessions.

    This does not exercise the AWS adapter or prove a client cannot forge an ALB
    event; actual Lambda invocation permissions and ingress remain review gates.
    """
    application, bindings, store = bound_app
    proxied = ProxyHeadersMiddleware(application, trusted_hosts="127.0.0.1")
    headers = {"Cookie": "__Host-clip_session=synthetic-cookie"}
    if forwarded_proto is not None:
        headers["X-Forwarded-Proto"] = forwarded_proto
    response = request(proxied, scheme="http", headers=headers, peer=peer)
    assert response.status_code == expected
    if expected == 200:
        bindings.sessions.authenticate.assert_called_once_with("synthetic-cookie")
        store.browse_available_listings.assert_awaited_once()
    else:
        bindings.sessions.authenticate.assert_not_called()
        store.browse_available_listings.assert_not_awaited()


@pytest.mark.parametrize(
    ("peer", "expected"),
    [("10.64.0.37", 200), ("10.64.3.44", 200), ("10.64.2.88", 403)],
)
def test_uvicorn_accepts_forwarding_only_from_reviewed_alb_subnets(
    bound_app, peer, expected
):
    """A local CIDR check does not establish real ALB or security-group behavior."""
    application, bindings, _ = bound_app
    proxied = ProxyHeadersMiddleware(
        application, trusted_hosts="10.64.0.0/24,10.64.3.0/24"
    )
    response = request(
        proxied,
        scheme="http",
        peer=peer,
        headers={
            "Cookie": "__Host-clip_session=synthetic-cookie",
            "X-Forwarded-Proto": "https",
        },
    )
    assert response.status_code == expected
    if expected == 200:
        bindings.sessions.authenticate.assert_called_once()
    else:
        bindings.sessions.authenticate.assert_not_called()


@pytest.mark.parametrize(
    "scheme,origin", [("http", ORIGIN), ("https", "https://other.invalid")]
)
def test_hostile_transport_or_origin_rejected_before_authentication(
    bound_app, scheme, origin
):
    application, bindings, _ = bound_app
    response = request(
        application,
        scheme=scheme,
        headers={"Origin": origin, "Cookie": "__Host-clip_session=synthetic-cookie"},
    )
    assert response.status_code == 403
    bindings.sessions.authenticate.assert_not_called()


def test_current_account_ineligibility_denies_browse(bound_app):
    application, bindings, store = bound_app
    bindings.sessions.capabilities.check_account_eligibility.return_value = (
        AccountEligibility(eligible=False)
    )
    response = request(
        application, headers={"Cookie": "__Host-clip_session=synthetic-cookie"}
    )
    assert response.status_code == 403
    store.browse_available_listings.assert_not_awaited()


def test_expired_trusted_context_is_still_denied(bound_app):
    application, bindings, store = bound_app
    bindings.sessions.authenticate.return_value = SessionIdentity(
        CallerContext(USER, "temporary", datetime(2000, 1, 1, tzinfo=UTC)),
        SESSION,
        None,
    )
    response = request(
        application, headers={"Cookie": "__Host-clip_session=synthetic-cookie"}
    )
    assert response.status_code == 401
    store.browse_available_listings.assert_not_awaited()


def test_entry_point_selects_read_bootstrap_only_when_enabled(monkeypatch):
    import app.core.config as configuration

    monkeypatch.setattr(
        configuration, "load_settings", lambda: Settings(identity_runtime_enabled=False)
    )
    from app import lambda_main

    prepare = MagicMock(return_value=read_bindings())
    monkeypatch.setattr(lambda_main, "prepare_hosted_test_identity_reads", prepare)
    unbound = lambda_main.create_configured_app(
        Settings(identity_runtime_enabled=False)
    )
    assert unbound.state.identity_read_dependencies is None
    prepare.assert_not_called()
    configured = lambda_main.create_configured_app(hosted_settings())
    assert configured.state.identity_read_dependencies is prepare.return_value
    prepare.assert_called_once()


def test_read_binding_cannot_expand_or_mix_identity_modes(bound_app):
    application, bindings, _ = bound_app
    with pytest.raises(ValueError, match="already installed"):
        install_identity_reads(application, bindings)
    with pytest.raises(ConfigurationError):
        create_app(hosted_settings(), identity_reads=bindings)
    with pytest.raises(ConfigurationError):
        create_app(
            Settings(environment="test"),
            identity_reads=bindings,
            listings_read_only=True,
        )


def test_read_bootstrap_reads_only_auth_and_db_and_never_prepares_mail(monkeypatch):
    import app.domains.identity.runtime_configuration as runtime

    bindings = read_bindings()
    reads = []
    client = object()
    keys = object()
    connect = object()

    def read(_client, name):
        assert _client is client
        reads.append(name)
        return SecretStr("synthetic")

    def forbidden(*args, **kwargs):
        raise AssertionError("email startup is forbidden for the read binding")

    monkeypatch.setattr(runtime, "read_secure_parameter", read)
    monkeypatch.setattr(runtime, "parse_authentication_keys", lambda value: keys)
    monkeypatch.setattr(runtime, "connection_factory", lambda dsn, environment: connect)
    audit = MagicMock()
    monkeypatch.setattr(runtime, "validate_database", audit)
    pooled = MagicMock()
    pool_factory = MagicMock(return_value=pooled)
    monkeypatch.setattr(runtime, "IdentityConnectionPool", pool_factory)
    constructor = MagicMock(return_value=bindings.sessions)
    monkeypatch.setattr(runtime, "IdentitySessions", constructor)
    monkeypatch.setattr(runtime, "RefreshingEmailSender", forbidden)
    monkeypatch.setattr(runtime, "SesEmailSender", forbidden)
    result = runtime.prepare_hosted_test_identity_reads(
        hosted_settings(), client=client
    )
    assert result.sessions is bindings.sessions
    assert reads == [
        "/clip/test/identity/authentication-keys",
        "/clip/test/identity/database-url",
    ]
    audit.assert_called_once_with(connect, keys)
    constructor.assert_called_once()
    pool_factory.assert_called_once_with(
        SecretStr("synthetic"), "test", max_size=1, retain_idle=False
    )
    assert constructor.call_args.args[0] is pooled
    assert result.close == pooled.close


def test_read_bootstrap_refuses_unenabled_mode_before_reading_secrets(monkeypatch):
    import app.domains.identity.runtime_configuration as runtime

    reader = MagicMock(side_effect=AssertionError("must not read"))
    monkeypatch.setattr(runtime, "read_secure_parameter", reader)
    with pytest.raises(ConfigurationError):
        runtime.prepare_hosted_test_identity_reads(Settings(environment="test"))
    reader.assert_not_called()


def test_read_bootstrap_sanitizes_failed_secret_input(monkeypatch):
    import app.domains.identity.runtime_configuration as runtime

    monkeypatch.setattr(
        runtime,
        "read_secure_parameter",
        MagicMock(side_effect=RuntimeError("private diagnostic")),
    )
    with pytest.raises(
        ConfigurationError, match="Identity read startup validation failed"
    ) as error:
        runtime.prepare_hosted_test_identity_reads(hosted_settings(), client=object())
    assert "private diagnostic" not in str(error.value)
