"""Translate synchronous Lambda Invoke SDK errors without exposing provider data.

This offline helper makes no SDK request. The eventual caller must disable SDK
retries and invoke synchronously; otherwise one logical request may result in
multiple attempts before this error reaches the routing policy.
"""

from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.overflow_dispatch import LambdaAtCapacity


class LambdaInvokeUnavailable(Exception):
    """The invocation failed without an eligible overflow signal."""


def raise_for_invoke_error(error: ClientError) -> None:
    """Raise a safe signal only for a Lambda Invoke throttling rejection.

    AWS documents TooManyRequestsException as a pre-execution Invoke failure.
    It may represent account or function limits; it is not proof that this
    function's configured concurrency alone was exhausted. Never inspect or
    propagate the provider message, which may include sensitive information.
    """
    details = error.response
    metadata = details.get("ResponseMetadata")
    service_error = details.get("Error")
    if (
        error.operation_name == "Invoke"
        and isinstance(metadata, dict)
        and metadata.get("HTTPStatusCode") == 429
        and isinstance(service_error, dict)
        and service_error.get("Code") == "TooManyRequestsException"
    ):
        raise LambdaAtCapacity() from None
    raise LambdaInvokeUnavailable() from None
