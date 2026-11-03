"""Unwired, bounded synchronous Lambda Invoke transport for EXP-03.

The caller must build a reviewed event, keep it private, run this blocking
operation off the ASGI event loop, and supply a client configured without SDK
retries. This module does not create a client or connect to AWS by itself.
"""

import re
from typing import Any

from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.overflow_aws_errors import LambdaInvokeUnavailable, raise_for_invoke_error

_TARGET = re.compile(
    r"arn:aws:lambda:ap-south-1:335523638354:function:clip-exp03-[a-z0-9]{3,10}(?::[1-9][0-9]*)?"
)
_MAX_EVENT = 65536
_MAX_RESPONSE = 1048576


def invoke_read(client: Any, target: str, event: bytes) -> bytes:
    """Invoke one exact EXP-03 target once and return a bounded opaque response.

    Errors are sanitized and only a confirmed Invoke throttle signals fallback.
    A successful SDK status alone is insufficient: function errors, malformed
    responses and oversized payloads fail without ECS retry. Response content
    remains untrusted and requires separate protocol and correctness checks.
    """
    if (
        not isinstance(target, str)
        or _TARGET.fullmatch(target) is None
        or not isinstance(event, bytes)
        or not 0 < len(event) <= _MAX_EVENT
    ):
        raise ValueError("Invalid Lambda invocation input")
    config = getattr(getattr(client, "meta", None), "config", None)
    retries = getattr(config, "retries", None)
    if not isinstance(retries, dict) or retries.get("total_max_attempts") != 1:
        raise ValueError("Lambda client must disable retries")
    try:
        result = client.invoke(
            FunctionName=target,
            InvocationType="RequestResponse",
            LogType="None",
            Payload=event,
        )
    except ClientError as error:
        raise_for_invoke_error(error)
        raise AssertionError("Unreachable") from None
    except Exception:
        raise LambdaInvokeUnavailable() from None

    if not isinstance(result, dict):
        raise LambdaInvokeUnavailable() from None
    stream = result.get("Payload")
    try:
        if (
            result.get("StatusCode") != 200
            or result.get("FunctionError") is not None
            or stream is None
        ):
            raise LambdaInvokeUnavailable()
        payload = stream.read(_MAX_RESPONSE + 1)
        if not isinstance(payload, bytes) or len(payload) > _MAX_RESPONSE:
            raise LambdaInvokeUnavailable()
        return payload
    except Exception:
        raise LambdaInvokeUnavailable() from None
    finally:
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass
