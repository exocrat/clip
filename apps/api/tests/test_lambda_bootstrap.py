"""Local-only tests for guarded Lambda database settings bootstrap."""

from os import environ

import pytest

from app.core.config import ConfigurationError
from app.domains.identity.runtime_configuration import (
    LISTINGS_DATABASE_PARAMETER,
    load_lambda_settings,
)


class FakeParameterClient:
    def __init__(self, value="postgresql://fixture:synthetic-secret@localhost/clip"):
        self.value = value
        self.calls = []

    def get_parameter(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "Parameter": {
                "Name": LISTINGS_DATABASE_PARAMETER,
                "Type": "SecureString",
                "Version": 1,
                "Value": self.value,
            }
        }


@pytest.fixture
def hosted_environment(monkeypatch):
    for key in list(environ):
        if key.startswith("CLIP_"):
            monkeypatch.delenv(key, raising=False)
    for key, value in {
        "AWS_LAMBDA_FUNCTION_NAME": "synthetic-lambda",
        "CLIP_LAMBDA_DATABASE_PARAMETER_ENABLED": "true",
        "CLIP_ENVIRONMENT": "test",
        "CLIP_IDENTITY_RUNTIME_ENABLED": "true",
        "CLIP_IDENTITY_PROVIDER": "microsoft",
        "CLIP_EMAIL_PROVIDER": "dual",
        "CLIP_SES_TEST_RECIPIENTS": '["fixture@example.invalid"]',
        "CLIP_IDENTITY_BROWSER_ORIGINS": '["https://clip-iisc.site"]',
    }.items():
        monkeypatch.setenv(key, value)


def test_fixed_secure_string_is_used_without_setting_environment(hosted_environment):
    client = FakeParameterClient()
    settings = load_lambda_settings(client=client)
    assert client.calls == [
        {"Name": LISTINGS_DATABASE_PARAMETER, "WithDecryption": True}
    ]
    assert settings.database_url.get_secret_value() == client.value
    assert "synthetic-secret" not in repr(settings)
    assert "CLIP_DATABASE_URL" not in environ


@pytest.mark.parametrize(
    "field,value",
    [
        ("AWS_LAMBDA_FUNCTION_NAME", ""),
        ("CLIP_ENVIRONMENT", "production"),
        ("CLIP_IDENTITY_RUNTIME_ENABLED", "false"),
        ("CLIP_DATABASE_URL", "postgresql://fixture@localhost/clip"),
        ("CLIP_LAMBDA_DATABASE_PARAMETER_ENABLED", "unexpected"),
        ("CLIP_IDENTITY_PROVIDER", "fake"),
        ("CLIP_IDENTITY_BROWSER_ORIGINS", "synthetic-private-invalid-json"),
    ],
)
def test_invalid_setup_fails_before_provider_read(
    hosted_environment, monkeypatch, field, value
):
    monkeypatch.setenv(field, value)
    client = FakeParameterClient()
    with pytest.raises(ConfigurationError) as failure:
        load_lambda_settings(client=client)
    assert client.calls == []
    assert "synthetic-private-invalid-json" not in str(failure.value)


def test_bad_secret_and_provider_failure_are_redacted(hosted_environment):
    client = FakeParameterClient("synthetic-private-invalid-database")
    with pytest.raises(ConfigurationError) as failure:
        load_lambda_settings(client=client)
    assert "synthetic-private-invalid-database" not in str(failure.value)

    class BrokenClient:
        def get_parameter(self, **kwargs):
            raise RuntimeError("synthetic-private-provider-error")

    with pytest.raises(ConfigurationError) as failure:
        load_lambda_settings(client=BrokenClient())
    assert "synthetic-private-provider-error" not in str(failure.value)


def test_default_mode_does_not_read_provider(monkeypatch):
    for key in list(environ):
        if key.startswith("CLIP_"):
            monkeypatch.delenv(key, raising=False)
    client = FakeParameterClient()
    settings = load_lambda_settings(client=client)
    assert not settings.identity_runtime_enabled
    assert client.calls == []
