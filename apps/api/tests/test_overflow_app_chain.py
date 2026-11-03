"""Synthetic end-to-end overflow checks through real app route and middleware.

The Lambda SDK, ALB/ASGI bridge, session service and data store are all local
test doubles. This does not validate deployed ingress or live parity.
"""

import asyncio
from io import BytesIO
import json
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError

from app.alb_asgi import invoke_read as invoke_synthetic_asgi
from app.overflow_dispatch import dispatch_read
from app.overflow_event import build_read_event
from app.overflow_invoke import invoke_read
from app.overflow_response import parse_read_response
from test_lambda_identity import bound_app  # noqa: F401

TARGET = "arn:aws:lambda:ap-south-1:335523638354:function:clip-exp03-test001:1"
TG = "arn:aws:elasticloadbalancing:ap-south-1:335523638354:targetgroup/clip-exp03-test001-ecs/0123456789abcdef"


class FakeLambda:
    """Run the injected ASGI app or return a synthetic pre-invocation throttle."""

    def __init__(self, application, throttle):
        self.application = application
        self.throttle = throttle
        self.meta = SimpleNamespace(
            config=SimpleNamespace(retries={"total_max_attempts": 1})
        )
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
        response = asyncio.run(
            invoke_synthetic_asgi(
                self.application,
                json.loads(kwargs["Payload"]),
                trusted_host="clip-iisc.site",
            )
        )
        return {"StatusCode": 200, "Payload": BytesIO(json.dumps(response).encode())}


@pytest.mark.parametrize("throttle", [False, True])
@pytest.mark.parametrize("authenticated", [False, True])
def test_read_authentication_and_ecs_fallback(bound_app, throttle, authenticated):
    application, bindings, store = bound_app
    headers = [(b"host", b"clip-iisc.site")]
    if authenticated:
        headers.append((b"cookie", b"__Host-clip_session=synthetic-cookie"))
    event = build_read_event("GET", "/api/listings", b"page=1", headers, TG)
    client = FakeLambda(application, throttle)
    fallback_calls = []

    async def run():
        async def lambda_read():
            payload = await asyncio.to_thread(invoke_read, client, TARGET, event)
            return parse_read_response(payload)

        async def ecs_read():
            fallback_calls.append(1)
            response = await invoke_synthetic_asgi(
                application, json.loads(event), trusted_host="clip-iisc.site"
            )
            return parse_read_response(json.dumps(response).encode())

        return await dispatch_read(lambda_read, ecs_read)

    result = asyncio.run(run())
    assert client.calls == 1
    assert len(fallback_calls) == int(throttle)
    assert result.backend == ("ecs" if throttle else "lambda")
    assert result.response.status == (200 if authenticated else 401)
    if authenticated:
        assert json.loads(result.response.body)["items"] == []
        bindings.sessions.authenticate.assert_called_once_with("synthetic-cookie")
        store.browse_available_listings.assert_awaited_once()
    else:
        bindings.sessions.authenticate.assert_not_called()
        store.browse_available_listings.assert_not_awaited()
