"""Approved test-adapter behavior without domain provider APIs or external I/O."""

import asyncio
from datetime import UTC, datetime

import pytest

from app.core.auth import CallerContext
from app.core.config import ConfigurationError, Settings, load_settings
from clip_test_fixtures import (
    Fail,
    Return,
    ScriptExhausted,
    ScriptedTestProvider,
    TestProviderFailure,
    make_synthetic_ids,
    make_test_provider,
)


def selected_settings(monkeypatch, kind, mode="test"):
    """Load explicit process selections rather than relying on developer settings."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", mode)
    for name in ("identity", "email", "storage"):
        monkeypatch.setenv(
            "CLIP_" + name.upper() + "_PROVIDER", "fake" if name == kind else "disabled"
        )
    return load_settings()


@pytest.mark.parametrize("kind", ["identity", "email", "storage"])
@pytest.mark.parametrize("mode", ["local", "test"])
def test_explicit_selection_can_return_typed_synthetic_values(monkeypatch, kind, mode):
    """Each provider kind requires its own explicit selector and returns the scripted object."""
    ids = make_synthetic_ids()
    values = {
        "identity": CallerContext(
            ids.regular_user_id, "regular", datetime(2100, 1, 1, tzinfo=UTC)
        ),
        "email": None,
        "storage": ids.listing_id,
    }
    value = values[kind]
    provider = make_test_provider(
        selected_settings(monkeypatch, kind, mode), kind, [Return(value)]
    )
    assert asyncio.run(provider.call()) is value
    assert provider.call_count == 1
    assert provider.remaining == 0


@pytest.mark.parametrize("kind", ["identity", "email", "storage"])
@pytest.mark.parametrize("mode", ["local", "test", "production"])
def test_disabled_selection_refuses_both_construction_paths(monkeypatch, kind, mode):
    """No default enables a fake, including callers bypassing the named factory."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", mode)
    for name in ("identity", "email", "storage"):
        monkeypatch.setenv("CLIP_" + name.upper() + "_PROVIDER", "disabled")
    settings = load_settings()
    for constructor in (make_test_provider, ScriptedTestProvider):
        with pytest.raises(ConfigurationError):
            constructor(settings, kind, [Return(None)])


@pytest.mark.parametrize("kind", ["identity", "email", "storage"])
def test_factory_rechecks_production_even_with_unvalidated_settings(kind):
    """A test-only model-construction bypass cannot skip the factory's mode guard."""
    settings = Settings.model_construct(
        environment="production", **{kind + "_provider": "fake"}
    )
    with pytest.raises(ConfigurationError):
        make_test_provider(settings, kind, [Return(None)])


def test_one_provider_selector_does_not_enable_another(monkeypatch):
    """An email fake flag cannot silently grant identity/storage fake selection."""
    settings = selected_settings(monkeypatch, "email")
    for kind in ("identity", "storage"):
        with pytest.raises(ConfigurationError):
            make_test_provider(settings, kind, [Return(None)])


@pytest.mark.parametrize("reason", ["unavailable", "timeout", "denied", "invalid"])
def test_failures_consume_once_without_automatic_retry(monkeypatch, reason):
    """A failure remains visible; the next outcome needs a separate explicit call."""
    provider = make_test_provider(
        selected_settings(monkeypatch, "email"), "email", [Fail(reason), Return(None)]
    )
    with pytest.raises(TestProviderFailure) as captured:
        asyncio.run(provider.call())
    assert captured.value.reason == reason
    assert provider.call_count == provider.remaining == 1
    assert asyncio.run(provider.call()) is None
    assert provider.call_count == 2 and provider.remaining == 0


def test_script_exhaustion_is_visible_and_counts_attempts(monkeypatch):
    """Never repeat the final value or turn extra calls into fake success."""
    provider = make_test_provider(
        selected_settings(monkeypatch, "storage"),
        "storage",
        [Return(make_synthetic_ids().listing_id)],
    )
    asyncio.run(provider.call())
    for expected_count in (2, 3):
        with pytest.raises(ScriptExhausted):
            asyncio.run(provider.call())
        assert provider.call_count == expected_count
        assert provider.remaining == 0


def test_empty_script_rejects_an_unexpected_first_call(monkeypatch):
    """An empty script is a useful no-call expectation, not a default success."""
    provider = make_test_provider(selected_settings(monkeypatch, "email"), "email", [])
    with pytest.raises(ScriptExhausted):
        asyncio.run(provider.call())
    assert provider.call_count == 1


def test_concurrent_tasks_consume_distinct_outcomes(monkeypatch):
    """Script consumption stays deterministic on one asyncio event loop."""
    provider = make_test_provider(
        selected_settings(monkeypatch, "storage"),
        "storage",
        [Return(i) for i in range(4)],
    )

    async def scenario():
        """Run simultaneous callers without clocks, threads or external I/O."""
        return await asyncio.gather(*(provider.call() for _ in range(4)))

    assert asyncio.run(scenario()) == [0, 1, 2, 3]
    assert provider.call_count == 4 and provider.remaining == 0


def test_constructor_snapshots_the_script(monkeypatch):
    """Changing the caller's input list cannot replace queued outcomes."""
    outcomes = [Return(None)]
    provider = make_test_provider(
        selected_settings(monkeypatch, "email"), "email", outcomes
    )
    outcomes.clear()
    assert asyncio.run(provider.call()) is None


class Unrenderable:
    """Synthetic private payload whose representation must never be inspected."""

    def __repr__(self):
        """Fail if an outcome/provider repr attempts to reveal a private value."""
        raise AssertionError("Fixture value must not be rendered")


def test_repr_omits_return_values(monkeypatch):
    """Safe introspection displays counts and kind, without fixture data."""
    outcome = Return(Unrenderable())
    provider = make_test_provider(
        selected_settings(monkeypatch, "identity"), "identity", [outcome]
    )
    assert repr(outcome) == "Return()"
    assert (
        repr(provider) == "ScriptedTestProvider(kind='identity', calls=0, remaining=1)"
    )


@pytest.mark.parametrize("kind", ["unsupported", None, True])
def test_unknown_kind_is_rejected_without_echoing_values(monkeypatch, kind):
    """Configuration mistakes produce fixed safe errors, not dynamic input text."""
    with pytest.raises(ValueError, match="Unsupported synthetic provider kind"):
        make_test_provider(selected_settings(monkeypatch, "email"), kind, [])


@pytest.mark.parametrize("reason", ["synthetic-private-value", None, True])
def test_unknown_failure_reason_is_redacted(reason):
    """Both failure entry points reject arbitrary strings before retaining them."""
    for constructor in (Fail, TestProviderFailure):
        with pytest.raises(ValueError) as captured:
            constructor(reason)
        assert "synthetic-private-value" not in str(captured.value)


@pytest.mark.parametrize(
    "outcomes",
    [[None], ["synthetic-private-value"], "synthetic-private-value", iter(())],
)
def test_invalid_scripts_do_not_become_fallback_success(monkeypatch, outcomes):
    """Only reviewed outcome records in a finite sequence are accepted."""
    with pytest.raises(ValueError) as captured:
        make_test_provider(selected_settings(monkeypatch, "email"), "email", outcomes)
    assert "synthetic-private-value" not in str(captured.value)


def test_call_accepts_no_credential_or_content_arguments(monkeypatch):
    """The test seam cannot accidentally retain request credentials or email text."""
    provider = make_test_provider(
        selected_settings(monkeypatch, "email"), "email", [Return(None)]
    )
    with pytest.raises(TypeError):
        asyncio.run(provider.call(token="synthetic-private-value"))
    assert provider.call_count == 0
