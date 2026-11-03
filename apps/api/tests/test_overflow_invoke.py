"""Exercise the unwired Lambda transport using a strictly synthetic client."""

from io import BytesIO
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError

from app.overflow_aws_errors import LambdaInvokeUnavailable
from app.overflow_dispatch import LambdaAtCapacity
from app.overflow_invoke import invoke_read

TARGET = "arn:aws:lambda:ap-south-1:335523638354:function:clip-exp03-test001:1"


class FakeClient:
    def __init__(self, result=None, error=None, attempts=1):
        self.meta = SimpleNamespace(
            config=SimpleNamespace(retries={"total_max_attempts": attempts})
        )
        self.result = result
        self.error = error
        self.calls = []

    def invoke(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


def test_single_synchronous_call_closes_response():
    stream = BytesIO(b"synthetic")
    client = FakeClient({"StatusCode": 200, "Payload": stream})
    assert invoke_read(client, TARGET, b"{}") == b"synthetic"
    assert stream.closed
    assert client.calls == [
        {
            "FunctionName": TARGET,
            "InvocationType": "RequestResponse",
            "LogType": "None",
            "Payload": b"{}",
        }
    ]


def test_confirmed_throttle_is_passed_to_overflow():
    error = ClientError(
        {
            "Error": {"Code": "TooManyRequestsException"},
            "ResponseMetadata": {"HTTPStatusCode": 429},
        },
        "Invoke",
    )
    client = FakeClient(error=error)
    with pytest.raises(LambdaAtCapacity):
        invoke_read(client, TARGET, b"{}")
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    "result",
    [
        {
            "StatusCode": 200,
            "FunctionError": "Unhandled",
            "Payload": BytesIO(b"private"),
        },
        {"StatusCode": 200, "Payload": BytesIO(b"x" * (1048576 + 1))},
        {"StatusCode": 202, "Payload": BytesIO(b"")},
        {"StatusCode": 200},
    ],
)
def test_invalid_function_response_is_safe_failure(result):
    with pytest.raises(LambdaInvokeUnavailable):
        invoke_read(FakeClient(result), TARGET, b"{}")


@pytest.mark.parametrize(
    "target,event,attempts",
    [
        ("other", b"{}", 1),
        (TARGET, b"", 1),
        (TARGET, b"x" * 65537, 1),
        (TARGET, b"{}", 2),
    ],
)
def test_rejects_invalid_inputs_before_call(target, event, attempts):
    client = FakeClient(attempts=attempts)
    with pytest.raises(ValueError):
        invoke_read(client, target, event)
    assert not client.calls
