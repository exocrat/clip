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


def test_normal_hosted_ui_does_not_require_a_synthetic_caller(monkeypatch):
    """Production may serve the built website with normal trusted authentication."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", "production")
    monkeypatch.setenv("CLIP_SERVE_WEB_APP", "true")
    settings = load_settings()
    assert settings.serve_web_app
    assert not settings.isolated_listings_test_caller
    assert not settings.development_auth


def _set_isolated_test_profile(monkeypatch, **overrides):
    """Build one valid test profile, then apply a single adversarial setting."""
    values = {
        "CLIP_ENVIRONMENT": "test",
        "CLIP_DEVELOPMENT_AUTH": "true",
        "CLIP_ISOLATED_LISTINGS_TEST_CALLER": "true",
        "CLIP_ISOLATED_LISTINGS_MAX_COUNT": "10",
        "CLIP_DATABASE_URL": "postgresql://clip_test:secret@db.invalid/clip_test_listings",
        "CLIP_STORAGE_PROVIDER": "s3",
        "CLIP_IMAGE_BUCKET": "clip-test-listings-images-ap-south-1-li02",
        "CLIP_IMAGE_REGION": "ap-south-1",
        "CLIP_IMAGE_KEY_PREFIX": "listings/test/run-20261022",
    }
    values.update(overrides)
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_isolated_listings_test_caller_requires_the_private_test_configuration(
    monkeypatch,
):
    """Accept only its dedicated database, bucket and run-scoped key prefix."""
    _set_isolated_test_profile(monkeypatch)

    settings = load_settings()

    assert settings.isolated_listings_test_caller is True
    assert settings.database_url is not None
    assert settings.database_url.get_secret_value().endswith("/clip_test_listings")


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("CLIP_ENVIRONMENT", "production"),
        ("CLIP_ENVIRONMENT", "local"),
        ("CLIP_DEVELOPMENT_AUTH", "false"),
        (
            "CLIP_DATABASE_URL",
            "postgresql://clip_test:secret@db.invalid/clip_test",
        ),
        ("CLIP_STORAGE_PROVIDER", "fake"),
        ("CLIP_IMAGE_BUCKET", "shared-bucket"),
        ("CLIP_IMAGE_REGION", "us-east-1"),
        ("CLIP_IMAGE_KEY_PREFIX", "listings/shared/run-20261022"),
        ("CLIP_ISOLATED_LISTINGS_MAX_COUNT", "9"),
    ],
)
def test_isolated_listings_test_caller_rejects_nonisolated_targets(
    variable, value, monkeypatch
):
    """Refuse shared/prod settings and never expose supplied credentials."""
    _set_isolated_test_profile(monkeypatch, **{variable: value})

    with pytest.raises(ConfigurationError):
        load_settings()


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
