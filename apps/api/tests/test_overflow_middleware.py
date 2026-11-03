"""Offline HTTP checks for the explicitly injected overflow middleware."""

import asyncio
from io import BytesIO
import json
from types import SimpleNamespace

import httpx2
import pytest
from botocore.exceptions import ClientError

from app.overflow_middleware import OverflowReadMiddleware
from test_lambda_identity import bound_app  # noqa: F401

TARGET = "arn:aws:lambda:ap-south-1:335523638354:function:clip-exp03-test001:1"
TG = "arn:aws:elasticloadbalancing:ap-south-1:335523638354:targetgroup/clip-exp03-test001-lambda/0123456789abcdef"


class FakeClient:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []
        self.meta = SimpleNamespace(
            config=SimpleNamespace(retries={"total_max_attempts": 1})
        )

    def invoke(self, **kwargs):
        self.calls.append(kwargs)
        if self.outcome == "throttle":
            raise ClientError(
                {
                    "Error": {"Code": "TooManyRequestsException"},
                    "ResponseMetadata": {"HTTPStatusCode": 429},
                },
                "Invoke",
            )
        if self.outcome == "error":
            raise RuntimeError("synthetic private provider error")
        if self.outcome == "invalid":
            return {"StatusCode": 200, "Payload": BytesIO(b"invalid private response")}
        event = {
            "statusCode": 200,
            "multiValueHeaders": {"content-type": ["application/json"]},
            "isBase64Encoded": False,
            "body": '{"backend":"lambda"}',
        }
        return {"StatusCode": 200, "Payload": BytesIO(json.dumps(event).encode())}


def request(
    outcome,
    method="GET",
    path="/api/listings",
    *,
    base="https://clip-iisc.site",
    headers=None,
):
    calls = []
    client = FakeClient(outcome)

    async def ecs(scope, receive, send):
        calls.append(scope["path"])
        body = b'{"backend":"ecs"}'
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})

    async def run():
        app = OverflowReadMiddleware(ecs, client, TARGET, TG)
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url=base
        ) as http:
            return await http.request(method, path, headers=headers)

    return asyncio.run(run()), client, calls


@pytest.mark.parametrize("outcome,backend", [("ok", "lambda"), ("throttle", "ecs")])
def test_one_invocation_and_capacity_fallback(outcome, backend):
    response, client, calls = request(
        outcome,
        path="/api/listings?category=a&category=b",
        headers={"cookie": "synthetic=session"},
    )
    assert response.status_code == 200 and response.json()["backend"] == backend
    assert len(client.calls) == 1 and len(calls) == (outcome == "throttle")
    event = json.loads(client.calls[0]["Payload"])
    assert event["multiValueHeaders"]["x-forwarded-proto"] == ["https"]
    assert event["multiValueQueryStringParameters"]["category"] == ["a", "b"]


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/listings"),
        ("GET", "/api/conversations"),
        ("GET", "/api/listings/not-a-uuid"),
    ],
)
def test_other_routes_stay_on_ecs(method, path):
    response, client, calls = request("ok", method, path)
    assert response.json()["backend"] == "ecs" and len(calls) == 1
    assert not client.calls


def test_other_lambda_failure_is_safe_and_not_retried():
    response, client, calls = request("error")
    assert response.status_code == 503
    assert "private" not in response.text
    assert len(client.calls) == 1 and not calls


def test_malformed_lambda_response_is_safe_and_not_retried():
    response, client, calls = request("invalid")
    assert response.status_code == 503
    assert "private" not in response.text
    assert len(client.calls) == 1 and not calls


def test_untrusted_scheme_fails_before_lambda():
    response, client, calls = request("ok", base="http://clip-iisc.site")
    assert response.status_code == 403 and not client.calls and not calls


@pytest.mark.parametrize("authenticated", [False, True])
def test_throttle_falls_back_to_real_local_identity_and_read_route(
    bound_app, authenticated
):
    application, bindings, store = bound_app
    client = FakeClient("throttle")
    headers = (
        {"cookie": "__Host-clip_session=synthetic-cookie"} if authenticated else {}
    )

    async def run():
        app = OverflowReadMiddleware(application, client, TARGET, TG)
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="https://clip-iisc.site"
        ) as http:
            return await http.get("/api/listings?page=1", headers=headers)

    response = asyncio.run(run())
    assert response.status_code == (200 if authenticated else 401)
    assert len(client.calls) == 1
    if authenticated:
        bindings.sessions.authenticate.assert_called_once_with("synthetic-cookie")
        store.browse_available_listings.assert_awaited_once()
    else:
        bindings.sessions.authenticate.assert_not_called()
        store.browse_available_listings.assert_not_awaited()
