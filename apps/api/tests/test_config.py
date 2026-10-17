"""Verify safe configuration behavior and actual app-startup rejection."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.core.config import ConfigurationError, load_settings


def test_local_startup_needs_no_external_settings():
    """The liveness-only app must have safe credential-free local defaults."""
    settings = load_settings()
    assert settings.environment == "local"
    assert settings.debug is False


@pytest.mark.parametrize(
    ("environment", "debug", "expected_debug"),
    [("test", "true", True), ("production", "false", False)],
)
def test_environment_values_are_typed(monkeypatch, environment, debug, expected_debug):
    """Valid explicit process settings must override the local defaults."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", environment)
    monkeypatch.setenv("CLIP_DEBUG", debug)
    settings = load_settings()
    assert settings.environment == environment
    assert settings.debug is expected_debug


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("CLIP_ENVIRONMENT", "synthetic-invalid-value"),
        ("CLIP_ENVIRONMENT", ""),
        ("CLIP_DEBUG", "synthetic-invalid-value"),
        ("CLIP_DEBUG", ""),
    ],
)
def test_invalid_settings_fail_without_echoing_values(monkeypatch, variable, value):
    """Reject malformed/empty values with field names rather than input data."""
    monkeypatch.setenv(variable, value)
    with pytest.raises(ConfigurationError) as captured:
        load_settings()
    message = str(captured.value)
    assert variable in message
    assert "synthetic-invalid-value" not in message
    assert "input_value" not in message


def test_production_debug_is_rejected(monkeypatch):
    """Production must not enable detailed framework exception responses."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", "production")
    monkeypatch.setenv("CLIP_DEBUG", "true")
    with pytest.raises(ConfigurationError, match="must be false"):
        load_settings()


def test_settings_are_read_fresh(monkeypatch):
    """Earlier settings objects must not hide later environment changes."""
    before = load_settings()
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    after = load_settings()
    assert before.environment == "local"
    assert after.environment == "test"


def test_dotenv_and_examples_are_not_loaded(monkeypatch, tmp_path):
    """Synthetic local files must not silently become runtime configuration."""
    for name in (".env", ".env.example"):
        (tmp_path / name).write_text(
            "CLIP_ENVIRONMENT=synthetic-invalid-value\nCLIP_DEBUG=true\n",
            encoding="utf-8",
        )
    monkeypatch.chdir(tmp_path)
    settings = load_settings()
    assert settings.environment == "local"
    assert settings.debug is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"CLIP_ENVIRONMENT": "production", "CLIP_DEBUG": "true"},
        {"CLIP_ENVIRONMENT": "synthetic-invalid-value"},
    ],
)
def test_invalid_configuration_prevents_app_startup(overrides):
    """A fresh credential-free process must fail importing an invalid app.

    Importing the Uvicorn entry point runs the actual startup configuration
    boundary. A child avoids cached module state, and the timeout bounds hangs.
    """
    api_root = Path(__file__).resolve().parents[1]
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(api_root),
        "PYTHONDONTWRITEBYTECODE": "1",
        **overrides,
    }
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=api_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "ConfigurationError: Invalid API configuration" in result.stderr
    assert "synthetic-invalid-value" not in result.stderr
    assert "input_value" not in result.stderr
