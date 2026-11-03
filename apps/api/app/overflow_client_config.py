"""Explicit SDK connection settings for the experimental Lambda read router.

This builds configuration only; it does not create a client, look up
credentials or contact AWS. The caller must review the selected values against
the experiment deadline and shared database budget before installation.
"""

import math

from botocore.config import Config  # type: ignore[import-untyped]


def build_invoke_config(
    *, connect_seconds: float, read_seconds: float, pool_connections: int
) -> Config:
    """Require explicit finite timeouts, a connection-pool size and no retries.

    The five-second limits follow the comparison client timeout. Socket timeout
    settings do not themselves enforce a total request deadline or bound the
    number of concurrent invocations; those remain separate integration gates.
    """
    for value in (connect_seconds, read_seconds):
        if (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not 0 < value <= 5
        ):
            raise ValueError("Invalid Lambda transport timeout")
    if type(pool_connections) is not int or pool_connections < 1:
        raise ValueError("Invalid Lambda connection-pool size")
    return Config(
        region_name="ap-south-1",
        connect_timeout=connect_seconds,
        read_timeout=read_seconds,
        max_pool_connections=pool_connections,
        retries={"mode": "standard", "total_max_attempts": 1},
    )
