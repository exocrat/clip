"""Unit settings guards; entry-point rejection is covered in security-boundary tests."""

import pytest

from app.core.config import ConfigurationError, load_settings


@pytest.mark.parametrize("mode", ["local", "test", "production"])
def test_provider_defaults_are_disabled(mode, monkeypatch):
    """No mode silently gains fake identity or successful email delivery."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", mode)
    settings = load_settings()
    assert (
        settings.identity_provider
        == settings.email_provider
        == settings.storage_provider
        == "disabled"
    )
    assert settings.development_auth is False


@pytest.mark.parametrize("mode", ["local", "test"])
def test_fakes_require_explicit_nonproduction_selection(mode, monkeypatch):
    """Reserved adapters need deliberate selection and do not create providers."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", mode)
    monkeypatch.setenv("CLIP_IDENTITY_PROVIDER", "fake")
    monkeypatch.setenv("CLIP_EMAIL_PROVIDER", "fake")
    monkeypatch.setenv("CLIP_STORAGE_PROVIDER", "fake")
    monkeypatch.setenv("CLIP_DEVELOPMENT_AUTH", "true")
    settings = load_settings()
    assert (
        settings.identity_provider
        == settings.email_provider
        == settings.storage_provider
        == "fake"
    )
    assert settings.development_auth is True


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("CLIP_IDENTITY_PROVIDER", "fake"),
        ("CLIP_EMAIL_PROVIDER", "fake"),
        ("CLIP_STORAGE_PROVIDER", "fake"),
        ("CLIP_DEVELOPMENT_AUTH", "true"),
    ],
)
def test_production_settings_reject_test_controls(variable, value, monkeypatch):
    """Configuration fails closed for each unsafe control independently."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", "production")
    monkeypatch.setenv(variable, value)
    with pytest.raises(ConfigurationError) as captured:
        load_settings()
    assert variable in str(captured.value)


@pytest.mark.parametrize(
    "variable",
    [
        "CLIP_IDENTITY_PROVIDER",
        "CLIP_EMAIL_PROVIDER",
        "CLIP_STORAGE_PROVIDER",
        "CLIP_DEVELOPMENT_AUTH",
    ],
)
@pytest.mark.parametrize("value", ["", "synthetic-unsupported-setting"])
def test_bad_selection_is_redacted_and_never_falls_back(variable, value, monkeypatch):
    """Unknown/empty input must fail instead of silently becoming disabled/fake."""
    monkeypatch.setenv(variable, value)
    with pytest.raises(ConfigurationError) as captured:
        load_settings()
    assert variable in str(captured.value)
    assert "synthetic-unsupported-setting" not in str(captured.value)
