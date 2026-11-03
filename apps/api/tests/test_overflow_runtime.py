"""Offline validation for the opt-in ECS Lambda client composition."""

from types import SimpleNamespace
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.core.config import ConfigurationError, IDENTITY_TEST_BROWSER_ORIGINS, Settings
from app.overflow_runtime import create_overflow_dependencies

FUNCTION = "arn:aws:lambda:ap-south-1:335523638354:function:clip-exp03-test001"
TARGET_GROUP = (
    "arn:aws:elasticloadbalancing:ap-south-1:335523638354:"
    "targetgroup/clip-exp03-test001-ecs/0123456789abcdef"
)


def test_disabled_router_does_not_create_an_sdk_client():
    """A and default config never create a Lambda client or executor."""
    called = False

    def client_factory(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("A must not create an SDK client")

    settings = Settings()
    assert (
        create_overflow_dependencies(
            settings,
            environ={"CLIP_EXP03_OVERFLOW_ENABLED": "false"},
            client_factory=client_factory,
        )
        is None
    )
    assert not called


def test_enabled_router_validates_full_configuration_before_client_creation():
    """Missing target or timeout inputs fail without asking for credentials."""
    called = False

    def client_factory(*args, **kwargs):
        nonlocal called
        called = True
        return object()

    settings = _hosted_test_settings()
    with pytest.raises(ConfigurationError, match="EXP-03 router"):
        create_overflow_dependencies(
            settings,
            environ={"CLIP_EXP03_OVERFLOW_ENABLED": "true"},
            client_factory=client_factory,
        )
    assert not called


def test_enabled_router_builds_one_attempt_bounded_dependencies():
    """B composes exact same-run targets and exposes no credentials or payloads."""
    captured = {}

    class Client:
        def __init__(self, config):
            self.meta = SimpleNamespace(config=config)

        def invoke(self, **kwargs):
            raise AssertionError("Configuration must not invoke Lambda")

    def client_factory(service, *, config):
        captured["service"] = service
        captured["config"] = config
        return Client(config)

    dependencies = create_overflow_dependencies(
        _hosted_test_settings(),
        environ=_enabled_environment(),
        client_factory=client_factory,
    )
    assert dependencies is not None
    assert captured["service"] == "lambda"
    assert captured["config"].retries["total_max_attempts"] == 1
    assert captured["config"].connect_timeout == 1
    assert captured["config"].read_timeout == 3
    assert dependencies.target == FUNCTION
    assert dependencies.target_group == TARGET_GROUP
    assert dependencies.counts.run_id == "test001"
    assert dependencies.invoker.max_inflight == 4
    dependencies.invoker.close()


def test_enabled_router_rejects_mismatched_run_before_client_creation():
    """A target from a different run is refused before SDK client creation."""
    called = False

    def client_factory(*args, **kwargs):
        nonlocal called
        called = True
        return object()

    environment = _enabled_environment()
    environment["CLIP_EXP03_INGRESS_TARGET_GROUP_ARN"] = TARGET_GROUP.replace(
        "test001", "test002"
    )
    with pytest.raises(ConfigurationError, match="EXP-03 router"):
        create_overflow_dependencies(
            _hosted_test_settings(),
            environ=environment,
            client_factory=client_factory,
        )
    assert not called


def test_router_slots_cannot_be_smaller_than_lambda_reserved_concurrency():
    """A single process cannot reject before the configured Lambda ceiling."""
    called = False

    def client_factory(*args, **kwargs):
        nonlocal called
        called = True
        return object()

    environment = _enabled_environment()
    environment["CLIP_EXP03_LAMBDA_RESERVED_CONCURRENCY"] = "5"
    with pytest.raises(ConfigurationError, match="EXP-03 router"):
        create_overflow_dependencies(
            _hosted_test_settings(),
            environ=environment,
            client_factory=client_factory,
        )
    assert not called


def _enabled_environment():
    """Return explicit synthetic B values without storing any secret inputs."""
    return {
        "CLIP_EXP03_OVERFLOW_ENABLED": "true",
        "CLIP_EXP03_LAMBDA_FUNCTION_ARN": FUNCTION,
        "CLIP_EXP03_INGRESS_TARGET_GROUP_ARN": TARGET_GROUP,
        "CLIP_EXP03_LAMBDA_RESERVED_CONCURRENCY": "4",
        "CLIP_EXP03_ROUTER_MAX_INFLIGHT": "4",
        "CLIP_EXP03_ROUTER_DEADLINE_SECONDS": "4",
        "CLIP_EXP03_INVOKE_CONNECT_TIMEOUT_SECONDS": "1",
        "CLIP_EXP03_INVOKE_READ_TIMEOUT_SECONDS": "3",
        "CLIP_EXP03_INVOKE_POOL_CONNECTIONS": "4",
    }


def _hosted_test_settings():
    """Create the same guarded Identity profile required by the ECS router."""
    return Settings(
        environment="test",
        identity_provider="microsoft",
        email_provider="dual",
        identity_runtime_enabled=True,
        identity_browser_origins=IDENTITY_TEST_BROWSER_ORIGINS,
        ses_test_recipients=("synthetic@example.invalid",),
        database_url=SecretStr("postgresql://fixture@localhost/clip"),
        serve_web_app=True,
        hybrid_search_enabled=True,
        hybrid_search_interpreter=Path("/tmp/clip-synthetic-python"),
        hybrid_search_model_dir=Path("/tmp/clip-synthetic-model"),
    )
