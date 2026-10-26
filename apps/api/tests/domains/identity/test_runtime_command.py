"""Offline real-runtime command gates and composition; no provider/SSM/SQL calls."""

import subprocess
import sys
from types import SimpleNamespace

from fastapi import FastAPI
import pytest

from app.core.config import ConfigurationError, Settings
from scripts import identity_runtime as command


def settings(**overrides):
    """Synthetic local/test configuration; private example.invalid is never used."""
    values = dict(
        environment="test",
        identity_provider="microsoft",
        email_provider="dual",
        ses_test_recipients=("runtime@example.invalid",),
        database_url="postgresql://synthetic:synthetic@database.example.invalid/clip_test",
    )
    values.update(overrides)
    return Settings(**values)


def test_shared_composition_keeps_separate_settings_and_loopback_policy(monkeypatch):
    configuration = settings()
    identity = object()
    app = FastAPI()
    calls = []
    monkeypatch.setattr(command, "load_settings", lambda: configuration)

    def prepare(actual, policy):
        assert actual is configuration
        assert policy.origins == ("http://localhost:5173",)
        assert policy.development
        calls.append("identity")
        return identity

    def compose(actual, **kwargs):
        assert actual is configuration and kwargs["identity"] is identity
        calls.append("composition")
        return app

    monkeypatch.setattr(command, "prepare_local_identity", prepare)
    monkeypatch.setattr(command, "create_app", compose)
    assert command.prepare_application() is app
    assert calls == ["identity", "composition"]


@pytest.mark.parametrize("overrides", [{"database_url": None}, {"debug": True}])
def test_missing_listings_config_or_debug_fails_before_secret_reads(
    monkeypatch, overrides
):
    monkeypatch.setattr(command, "load_settings", lambda: settings(**overrides))

    def forbidden(*args):
        pytest.fail("Secret bootstrap must not execute")

    monkeypatch.setattr(command, "prepare_local_identity", forbidden)
    with pytest.raises(ConfigurationError):
        command.prepare_application()


@pytest.mark.parametrize(
    "arguments", [[], ["--check"], ["--serve"], ["--approved-bootstrap"]]
)
def test_no_mode_or_opt_in_never_bootstraps(monkeypatch, arguments):
    def forbidden():
        pytest.fail("No bootstrap without explicit action and acknowledgement")

    monkeypatch.setattr(command, "prepare_application", forbidden)
    with pytest.raises(SystemExit) as error:
        command.main(arguments)
    assert error.value.code == 2


def test_check_only_never_opens_listener(monkeypatch, capsys):
    monkeypatch.setattr(command, "prepare_application", lambda: FastAPI())

    def forbidden(*args, **kwargs):
        pytest.fail("Check-only must never construct a server")

    monkeypatch.setattr(command.uvicorn, "Server", forbidden)
    assert command.main(["--check", "--approved-bootstrap"]) == 0
    assert "Listings pool not checked" in capsys.readouterr().out


@pytest.mark.parametrize("failure", [RuntimeError, SystemExit])
def test_private_bootstrap_errors_are_contained(monkeypatch, capsys, failure):
    def unavailable():
        raise failure("private-synthetic-bootstrap-value")

    monkeypatch.setattr(command, "prepare_application", unavailable)
    assert command.main(["--check", "--approved-bootstrap"]) == 1
    captured = capsys.readouterr()
    assert "private-synthetic-bootstrap-value" not in captured.out + captured.err
    assert "Identity runtime failed" in captured.err


@pytest.mark.parametrize("started", [True, False])
def test_server_is_loopback_without_forwarded_header_trust(monkeypatch, started):
    app = FastAPI()
    monkeypatch.setattr(command, "prepare_application", lambda: app)
    monkeypatch.setattr(command, "configure_logging", lambda: None)

    def server(config):
        assert config.app is app
        assert config.host == "127.0.0.1" and config.port == 8000
        assert not config.proxy_headers and not config.access_log
        assert config.log_config is None and config.workers == 1
        assert not config.reload
        return SimpleNamespace(run=lambda: None, started=started)

    monkeypatch.setattr(command.uvicorn, "Server", server)
    assert command.main(["--serve", "--approved-bootstrap"]) == (0 if started else 1)


def test_help_in_fresh_process_performs_no_bootstrap():
    result = subprocess.run(
        [sys.executable, "scripts/identity_runtime.py", "--help"],
        cwd=command.ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        env={"PATH": "/usr/bin:/bin", "AWS_EC2_METADATA_DISABLED": "true"},
    )
    assert result.returncode == 0
    assert "--approved-bootstrap" in result.stdout
    assert not result.stderr


def test_loopback_command_composes_real_cookie_sql_and_listings(
    monkeypatch, identity_runtime, signed_tokens
):
    """Real app/SQL/OTP with offline signer/mail; bootstrap has no live SSM call."""
    from fastapi.testclient import TestClient
    from uuid import uuid4
    from app.domains.identity.http import IdentityHttpDependencies
    from apps.api.tests.domains.identity.test_application_composition import compose
    from apps.api.tests.domains.identity.session_fixtures import EMAIL, PASSWORD

    state = identity_runtime
    _, shared_settings, _ = compose(state, signed_tokens)
    configuration = settings(database_url=shared_settings.database_url)
    monkeypatch.setattr(command, "load_settings", lambda: configuration)

    def prepare(actual, policy):
        return IdentityHttpDependencies(
            state.service,
            policy,
            state.mail,
            signed_tokens.validator(),
            lambda: state.clock[0],
        )

    monkeypatch.setattr(command, "prepare_local_identity", prepare)
    application = command.prepare_application()
    headers = {"Origin": "http://localhost:5173", "X-CLIP-Request": "1"}
    with TestClient(
        application, base_url="http://localhost:5173", client=("127.0.0.1", 50000)
    ) as browser:
        assert browser.get("/health").status_code == 200
        requested = browser.post(
            "/auth/temporary/registration-challenges",
            headers=headers,
            json={"email": EMAIL, "operation_id": str(uuid4())},
        )
        assert requested.status_code == 202
        activated = browser.post(
            "/auth/temporary/accounts",
            headers=headers,
            json={
                "challenge_id": requested.json()["challenge_id"],
                "code": state.mail.code(),
                "password": PASSWORD.get_secret_value(),
            },
        )
        assert activated.status_code == 201
        assert "clip_session_dev" in browser.cookies
        assert browser.get("/me").status_code == 200
        assert browser.get("/me/listings").status_code == 200
        csrf = browser.get("/auth/csrf").json()["csrf_token"]
        denied = browser.post(
            "/image-uploads",
            headers=headers | {"X-CSRF-Token": csrf},
            json={
                "media_type": "image/png",
                "size_bytes": 100,
                "operation_id": str(uuid4()),
            },
        )
        assert denied.status_code == 403
        assert (
            browser.get(
                "/me", headers={"Origin": "https://hostile.example.invalid"}
            ).status_code
            == 403
        )
