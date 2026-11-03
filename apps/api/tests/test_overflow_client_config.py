"""Local SDK configuration checks; no client, credentials or AWS calls."""

import math

import pytest

from app.overflow_client_config import build_invoke_config


def test_explicit_sdk_config_disables_retries():
    config = build_invoke_config(connect_seconds=1, read_seconds=3, pool_connections=4)
    assert config.region_name == "ap-south-1"
    assert config.connect_timeout == 1 and config.read_timeout == 3
    assert config.max_pool_connections == 4
    assert config.retries == {"mode": "standard", "total_max_attempts": 1}


@pytest.mark.parametrize("value", [0, -1, 5.01, math.inf, math.nan, True, "1"])
def test_invalid_timeout_is_refused(value):
    with pytest.raises(ValueError):
        build_invoke_config(connect_seconds=value, read_seconds=1, pool_connections=1)
    with pytest.raises(ValueError):
        build_invoke_config(connect_seconds=1, read_seconds=value, pool_connections=1)


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_pool_size_is_refused(value):
    with pytest.raises(ValueError):
        build_invoke_config(connect_seconds=1, read_seconds=1, pool_connections=value)
