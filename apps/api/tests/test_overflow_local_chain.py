"""Local proof that the proposed pieces compose, using synthetic adapters only.

The injected bridge is not AWS Lambda Web Adapter and the app is not the real
Identity/Listings stack; real transport, authentication and parity stay open.
"""

import asyncio
from io import BytesIO
import json
from types import SimpleNamespace

from botocore.exceptions import ClientError

from app.alb_asgi import invoke_read as invoke_synthetic_asgi
from app.overflow_dispatch import dispatch_read
from app.overflow_event import build_read_event
from app.overflow_invoke import invoke_read
from app.overflow_response import ReadResponse, parse_read_response

TARGET = "arn:aws:lambda:ap-south-1:335523638354:function:clip-exp03-test001:1"
TG = "arn:aws:elasticloadbalancing:ap-south-1:335523638354:targetgroup/clip-exp03-test001-ecs/0123456789abcdef"


async def synthetic_app(scope, receive, send):
    """Return selected request properties without any real account or database."""
    assert scope["scheme"] == "https"
    assert (b"cookie", b"synthetic=session") in scope["headers"]
    body = json.dumps({"query": scope["query_string"].decode()}).encode()
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": body})


class SyntheticClient:
    """Mimic one synchronous SDK invocation without contacting AWS."""

    def __init__(self, throttle):
        self.meta = SimpleNamespace(
            config=SimpleNamespace(retries={"total_max_attempts": 1})
        )
        self.throttle = throttle
        self.calls = 0

    def invoke(self, **kwargs):
        self.calls += 1
        if self.throttle:
            raise ClientError(
                {
                    "Error": {"Code": "TooManyRequestsException"},
                    "ResponseMetadata": {"HTTPStatusCode": 429},
                },
                "Invoke",
            )
        result = asyncio.run(
            invoke_synthetic_asgi(
                synthetic_app,
                json.loads(kwargs["Payload"]),
                trusted_host="clip-iisc.site",
            )
        )
        return {"StatusCode": 200, "Payload": BytesIO(json.dumps(result).encode())}


def test_composed_synthetic_lambda_path_and_ecs_capacity_fallback():
    async def run(throttle):
        client = SyntheticClient(throttle)
        event = build_read_event(
            "GET",
            "/api/listings",
            b"category=a&category=b",
            [(b"host", b"clip-iisc.site"), (b"cookie", b"synthetic=session")],
            TG,
        )
        ecs_calls = []

        async def invoke_lambda():
            raw = await asyncio.to_thread(invoke_read, client, TARGET, event)
            return parse_read_response(raw)

        async def ecs():
            ecs_calls.append(1)
            return ReadResponse(200, (), b"synthetic ecs")

        result = await dispatch_read(invoke_lambda, ecs)
        return result, client.calls, ecs_calls

    lambda_result, calls, ecs_calls = asyncio.run(run(False))
    assert lambda_result.backend == "lambda"
    assert json.loads(lambda_result.response.body) == {"query": "category=a&category=b"}
    assert calls == 1 and not ecs_calls
    ecs_result, calls, ecs_calls = asyncio.run(run(True))
    assert ecs_result.backend == "ecs"
    assert ecs_result.response.body == b"synthetic ecs"
    assert calls == 1 and ecs_calls == [1]
