"""Turnstile network boundary checks: no provider traffic or real credentials."""

import json
from types import SimpleNamespace

from pydantic import SecretStr
import pytest

from app.core.config import Settings
from app.core.errors import PublicError
from app.domains.identity import signin_challenge as module


@pytest.mark.parametrize(
    "result,status",
    [
        ({"success": True, "hostname": "clip-iisc.site", "action": "clip_signin"}, 200),
        ({"success": False}, 429),
        (
            {"success": "true", "hostname": "clip-iisc.site", "action": "clip_signin"},
            429,
        ),
        (
            {"success": True, "hostname": "foreign.example", "action": "clip_signin"},
            429,
        ),
        ({"success": True, "hostname": "clip-iisc.site", "action": "other"}, 429),
        ([], 503),
    ],
)
def test_verifier_checks_hostname_action_and_boolean(monkeypatch, result, status):
    """Success from another site/action or a malformed response never grants an exception."""

    class Reply:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            assert limit == 16385
            return json.dumps(result).encode()

    def open_request(request, timeout):
        assert request.full_url == module.SITEVERIFY
        assert timeout == 3
        assert request.method == "POST"
        return Reply()

    monkeypatch.setattr(
        module, "build_opener", lambda *args: SimpleNamespace(open=open_request)
    )
    verifier = module.TurnstileVerifier(
        "synthetic-site-key", SecretStr("synthetic-secret"), ("https://clip-iisc.site",)
    )
    if status == 200:
        verifier.verify("synthetic-token")
    else:
        with pytest.raises(PublicError) as error:
            verifier.verify("synthetic-token")
        assert error.value.spec.status == status


@pytest.mark.parametrize("mode", ["timeout", "large", "bad-json", "status"])
def test_provider_failures_are_safe_503(monkeypatch, mode):
    """No raw provider/body/secret diagnostic is returned on upstream failure."""

    class Reply:
        status = 500 if mode == "status" else 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return b"x" * 16385 if mode == "large" else b"not-json"

    def open_request(*args, **kwargs):
        if mode == "timeout":
            raise TimeoutError("PRIVATE_UPSTREAM_TEXT")
        return Reply()

    monkeypatch.setattr(
        module, "build_opener", lambda *args: SimpleNamespace(open=open_request)
    )
    verifier = module.TurnstileVerifier(
        "synthetic-site-key", SecretStr("synthetic-secret"), ("https://clip-iisc.site",)
    )
    with pytest.raises(PublicError) as error:
        verifier.verify("synthetic-token")
    assert error.value.spec.status == 503
    assert str(error.value) == "dependency_unavailable"


@pytest.mark.parametrize("token", ["", "x" * 2049, "\N{SNOWMAN}"])
def test_invalid_tokens_do_not_contact_provider(monkeypatch, token):
    def forbidden(*args):
        raise AssertionError("No provider request expected")

    monkeypatch.setattr(module, "build_opener", forbidden)
    verifier = module.TurnstileVerifier(
        "synthetic-site-key", SecretStr("synthetic-secret"), ("https://clip-iisc.site",)
    )
    with pytest.raises(PublicError) as error:
        verifier.verify(token)
    assert error.value.spec.status == 429


def test_settings_require_paired_keys():
    with pytest.raises(ValueError):
        Settings(turnstile_site_key="synthetic-site-key")
    with pytest.raises(ValueError):
        Settings(turnstile_secret_key=SecretStr("synthetic-secret"))
    assert Settings(
        turnstile_site_key="synthetic-site-key",
        turnstile_secret_key=SecretStr("synthetic-secret"),
    )
