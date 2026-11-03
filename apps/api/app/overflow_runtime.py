"""Build the optional ECS Lambda router from explicit task-role configuration.

The default and A configuration create no SDK client. B requires a hosted test
Identity app plus explicit function, ingress, timeout, pool and concurrency
settings. The client uses the ECS task role and performs no call until a request
invokes Lambda.
"""

from collections.abc import Callable, Mapping
import os
import re
from typing import Any

import boto3  # type: ignore[import-untyped]

from app.core.config import ConfigurationError, Settings
from app.overflow_admission import BoundedInvoker
from app.overflow_client_config import build_invoke_config
from app.overflow_middleware import OverflowCounts, OverflowDependencies

_POSITIVE_INT = re.compile(r"[1-9][0-9]{0,3}")
_POSITIVE_FLOAT = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_FUNCTION_ARN = re.compile(
    r"arn:aws:lambda:ap-south-1:335523638354:function:clip-exp03-(?P<run>[a-z0-9]{3,10})"
)
_TARGET_GROUP_ARN = re.compile(
    r"arn:aws:elasticloadbalancing:ap-south-1:335523638354:targetgroup/clip-exp03-(?P<run>[a-z0-9]{3,10})-ecs/[0-9a-f]{16}"
)


def _integer(environ: Mapping[str, str], name: str, maximum: int) -> int:
    """Read a bounded positive integer without accepting ambiguous formats."""
    value = environ.get(name, "")
    if _POSITIVE_INT.fullmatch(value) is None:
        raise ConfigurationError("Invalid EXP-03 router configuration")
    parsed = int(value)
    if parsed > maximum:
        raise ConfigurationError("Invalid EXP-03 router configuration")
    return parsed


def _seconds(environ: Mapping[str, str], name: str) -> float:
    """Read a finite decimal timeout; the shared validator enforces its cap."""
    value = environ.get(name, "")
    if _POSITIVE_FLOAT.fullmatch(value) is None:
        raise ConfigurationError("Invalid EXP-03 router configuration")
    parsed = float(value)
    if parsed <= 0:
        raise ConfigurationError("Invalid EXP-03 router configuration")
    return parsed


def create_overflow_dependencies(
    settings: Settings,
    *,
    environ: Mapping[str, str] | None = None,
    client_factory: Callable[..., Any] | None = None,
) -> OverflowDependencies | None:
    """Return no router for default/A, or build a bounded B router explicitly.

    `client_factory` is injectable for offline tests. In runtime the SDK client
    uses the ECS task role, performs no request during construction, and is
    configured for one attempt. Missing or inconsistent B settings fail closed.
    """
    values = os.environ if environ is None else environ
    enabled = values.get("CLIP_EXP03_OVERFLOW_ENABLED", "false")
    if enabled == "false":
        return None
    if enabled != "true" or (
        settings.environment != "test"
        or not settings.identity_runtime_enabled
        or not settings.serve_web_app
        or settings.development_auth
        or settings.isolated_listings_test_caller
        or not settings.hybrid_search_enabled
    ):
        raise ConfigurationError("Invalid EXP-03 router configuration")

    function_arn = values.get("CLIP_EXP03_LAMBDA_FUNCTION_ARN", "")
    target_group_arn = values.get("CLIP_EXP03_INGRESS_TARGET_GROUP_ARN", "")
    function_match = _FUNCTION_ARN.fullmatch(function_arn)
    target_group_match = _TARGET_GROUP_ARN.fullmatch(target_group_arn)
    if (
        function_match is None
        or target_group_match is None
        or function_match.group("run") != target_group_match.group("run")
    ):
        raise ConfigurationError("Invalid EXP-03 router configuration")
    maximum_inflight = _integer(values, "CLIP_EXP03_ROUTER_MAX_INFLIGHT", 1000)
    lambda_reserved_concurrency = _integer(
        values, "CLIP_EXP03_LAMBDA_RESERVED_CONCURRENCY", 20
    )
    if maximum_inflight < lambda_reserved_concurrency:
        raise ConfigurationError("Invalid EXP-03 router configuration")
    deadline_seconds = _seconds(values, "CLIP_EXP03_ROUTER_DEADLINE_SECONDS")
    connect_seconds = _seconds(values, "CLIP_EXP03_INVOKE_CONNECT_TIMEOUT_SECONDS")
    read_seconds = _seconds(values, "CLIP_EXP03_INVOKE_READ_TIMEOUT_SECONDS")
    pool_connections = _integer(values, "CLIP_EXP03_INVOKE_POOL_CONNECTIONS", 1000)
    try:
        config = build_invoke_config(
            connect_seconds=connect_seconds,
            read_seconds=read_seconds,
            pool_connections=pool_connections,
        )
        client = (
            client_factory("lambda", config=config)
            if client_factory is not None
            else boto3.client("lambda", config=config)
        )
        invoker = BoundedInvoker(
            max_inflight=maximum_inflight,
            deadline_seconds=deadline_seconds,
        )
        return OverflowDependencies(
            client=client,
            target=function_arn,
            target_group=target_group_arn,
            invoker=invoker,
            counts=OverflowCounts(function_match.group("run")),
        )
    except Exception:
        raise ConfigurationError("Invalid EXP-03 router configuration") from None
