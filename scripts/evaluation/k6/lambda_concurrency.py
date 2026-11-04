"""Bind Lambda capacity to the reviewed function or single-function account.

Unreserved capacity is safe for this bounded pilot only while the regional
quota stays ten and no other function competes. A pending quota increase must
not silently change the experiment: the runner polls and stops on drift.
"""

from typing import Any, cast


def validate_binding(value: Any, configuration: str) -> None:
    if configuration == "A" and value is None:
        return
    if (
        configuration != "B"
        or not isinstance(value, dict)
        or set(value) != {"mode", "maximum"}
        or type(value["maximum"]) is not int
        or not 1 <= value["maximum"] <= 20
        or value["mode"] not in {"reserved", "unreserved"}
        or (value["mode"] == "unreserved" and value["maximum"] != 10)
    ):
        raise ValueError("invalid_lambda_concurrency_binding")


def verify(lam: Any, function_arn: str, binding: dict[str, Any] | None) -> None:
    """Use the concurrency API; function configuration does not expose reservations."""
    reserved = lam.get_function_concurrency(FunctionName=function_arn).get(
        "ReservedConcurrentExecutions"
    )
    if binding is None:
        if type(reserved) is not int or not 1 <= reserved <= 20:
            raise ValueError("lambda_concurrency_unbounded")
        return
    if binding["mode"] == "reserved":
        if reserved != binding["maximum"]:
            raise ValueError("lambda_reserved_concurrency_drift")
        return
    limits = lam.get_account_settings()["AccountLimit"]
    if reserved is not None or any(
        limits.get(key) != binding["maximum"]
        for key in ("ConcurrentExecutions", "UnreservedConcurrentExecutions")
    ):
        raise ValueError("lambda_unreserved_quota_drift")
    functions = [
        row["FunctionArn"]
        for page in lam.get_paginator("list_functions").paginate()
        for row in page.get("Functions", [])
    ]
    if functions != [function_arn]:
        raise ValueError("lambda_unreserved_competing_function")


def run_guard(target: dict[str, Any]) -> Any:
    """Return a bounded read-only quota check for the runner, or no guard."""
    binding = target["resources"].get("lambda_concurrency")
    if target["configuration"] != "B" or not binding or binding["mode"] != "unreserved":
        return None
    from botocore.config import Config  # type: ignore[import-untyped]
    from data.generators.reference_login import sdk_profile_session

    session = cast(Any, sdk_profile_session)(
        profile_name=target["aws_profile"], region_name=target["region"]
    )
    lam = session.client(
        "lambda",
        config=Config(
            connect_timeout=2, read_timeout=2, retries={"total_max_attempts": 1}
        ),
    )
    return lambda: verify(lam, target["resources"]["lambda_function_arn"], binding)
