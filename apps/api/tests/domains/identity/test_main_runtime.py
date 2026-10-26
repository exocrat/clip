"""Default ASGI startup stays unbound unless the exact test opt-in is set."""

from pydantic import SecretStr

from app.core.config import Settings
from app.domains.identity.http import IdentityHttpDependencies
from app.main import create_configured_app
from apps.api.tests.domains.identity.session_fixtures import EMAIL


def test_default_asgi_factory_does_not_prepare_identity(monkeypatch):
    """Normal startup does not read SSM or install authentication routes."""

    def unexpected(_settings):
        raise AssertionError("default startup must not read Identity configuration")

    monkeypatch.setattr("app.main.prepare_hosted_test_identity", unexpected)
    app = create_configured_app(Settings(environment="test"))

    assert "/auth/microsoft/sessions" not in app.openapi()["paths"]


def test_asgi_factory_binds_only_the_explicit_test_runtime(
    monkeypatch, identity_runtime, signed_tokens
):
    """The opted-in test startup installs real handlers supplied by composition."""
    state = identity_runtime
    bindings = IdentityHttpDependencies(
        state.service,
        state.policy,
        state.mail,
        signed_tokens.validator(),
        lambda: state.clock[0],
    )
    settings = Settings(
        environment="test",
        identity_provider="microsoft",
        email_provider="dual",
        ses_test_recipients=(EMAIL,),
        identity_runtime_enabled=True,
        identity_browser_origins=("https://clip-iisc.site",),
        database_url=SecretStr("postgresql://listings@db.invalid/clip_test"),
    )
    calls = []

    def prepare(configured):
        calls.append(configured)
        return bindings

    monkeypatch.setattr("app.main.prepare_hosted_test_identity", prepare)
    app = create_configured_app(settings)

    assert calls == [settings]
    assert "/auth/microsoft/sessions" in app.openapi()["paths"]
