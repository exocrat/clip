"""Synthetic SDK-error classification checks; no client or AWS calls."""

import pytest
from botocore.exceptions import ClientError

from app.overflow_aws_errors import LambdaInvokeUnavailable, raise_for_invoke_error
from app.overflow_dispatch import LambdaAtCapacity


def sdk_error(code, status, operation="Invoke"):
    return ClientError(
        {
            "Error": {"Code": code, "Message": "synthetic private provider data"},
            "ResponseMetadata": {"HTTPStatusCode": status},
        },
        operation,
    )


def test_only_exact_invoke_throttle_enables_overflow():
    with pytest.raises(LambdaAtCapacity) as result:
        raise_for_invoke_error(sdk_error("TooManyRequestsException", 429))
    assert result.value.__suppress_context__
    assert "private" not in str(result.value)


@pytest.mark.parametrize(
    "code,status,operation",
    [
        ("TooManyRequestsException", 403, "Invoke"),
        ("TooManyRequestsException", 429, "Other"),
        ("AccessDeniedException", 403, "Invoke"),
        ("OtherException", 429, "Invoke"),
    ],
)
def test_other_failures_do_not_enable_overflow(code, status, operation):
    with pytest.raises(LambdaInvokeUnavailable) as result:
        raise_for_invoke_error(sdk_error(code, status, operation))
    assert result.value.__suppress_context__
    assert "private" not in str(result.value)
