"""Preserve redacted Conversations DSN checks beside the merged URL settings."""

import pytest
from app.core.config import ConfigurationError, load_settings


def test_database_dsn_is_optional_and_secret_masked(monkeypatch):
    """Dedicated Conversations connection info is optional and never in repr."""
    assert load_settings().database_dsn is None
    dsn = "postgresql://clip_user:synthetic-secret@localhost/clip"
    monkeypatch.setenv("CLIP_DATABASE_DSN", dsn)
    settings = load_settings()
    assert settings.database_dsn.get_secret_value() == dsn
    assert "synthetic-secret" not in repr(settings)


@pytest.mark.parametrize(
    "dsn", ["", "   ", 'postgresql://clip_user:synthetic-secret@localhost/clip?bad="']
)
def test_invalid_database_dsn_fails_without_echoing_secret(monkeypatch, dsn):
    """Reject malformed/empty libpq inputs with only the setting name exposed."""
    monkeypatch.setenv("CLIP_DATABASE_DSN", dsn)
    with pytest.raises(ConfigurationError) as captured:
        load_settings()
    assert "CLIP_DATABASE_DSN" in str(captured.value)
    assert "synthetic-secret" not in str(captured.value)
