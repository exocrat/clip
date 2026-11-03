"""Synthetic in-process ALB/ASGI bridge tests; no listener or cloud calls."""

import asyncio
import base64

import pytest

from app.alb_asgi import invoke_read
from test_alb_event import event


def test_bridges_query_cookie_and_response():
    async def app(scope, receive, send):
        assert scope["scheme"] == "https"
        assert scope["query_string"] == b"category=books&category=music&q=red+bike"
        assert (b"cookie", b"synthetic=1") in scope["headers"]
        assert (await receive())["body"] == b""
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"set-cookie", b"a=1"), (b"set-cookie", b"b=2")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    result = asyncio.run(invoke_read(app, event(), trusted_host="example.invalid"))
    assert result["multiValueHeaders"]["set-cookie"] == ["a=1", "b=2"]
    assert base64.b64decode(result["body"]) == b"ok"


def test_allows_uuid_listing_detail_route():
    async def app(scope, receive, send):
        assert scope["path"].endswith("00000000-0000-0000-0000-000000000001")
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    request = event()
    request["path"] = "/api/listings/00000000-0000-0000-0000-000000000001"
    result = asyncio.run(invoke_read(app, request, trusted_host="example.invalid"))
    assert result["statusCode"] == 404


def test_rejects_unexpected_host_before_app():
    async def app(scope, receive, send):
        raise AssertionError("app must not run")

    with pytest.raises(ValueError, match="Invalid request host"):
        asyncio.run(invoke_read(app, event(), trusted_host="other.invalid"))


@pytest.mark.parametrize(
    "path",
    [
        "/listings/00000000-0000-0000-0000-000000000001/availability",
        "/images/00000000-0000-0000-0000-000000000001/delivery",
        "/api/me/listings",
    ],
)
def test_rejects_routes_outside_approved_listing_reads(path):
    async def app(scope, receive, send):
        raise AssertionError("app must not run")

    request = event()
    request["path"] = path
    with pytest.raises(ValueError, match="Invalid ALB read route"):
        asyncio.run(invoke_read(app, request, trusted_host="example.invalid"))


def test_rejects_incomplete_response():
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})

    with pytest.raises(ValueError, match="Invalid ASGI response"):
        asyncio.run(invoke_read(app, event(), trusted_host="example.invalid"))


def test_real_app_rejects_unauthenticated_listing_read(monkeypatch):
    """A fabricated caller header cannot replace the real caller dependency."""
    import os

    from app.application import create_app
    from app.core.config import Settings

    for key in tuple(os.environ):
        if key.startswith("CLIP_"):
            monkeypatch.delenv(key)
    app = create_app(Settings())
    request = event()
    request["path"] = "/listings"
    request["multiValueHeaders"]["x-user-id"] = ["00000000-0000-0000-0000-000000000001"]
    result = asyncio.run(invoke_read(app, request, trusted_host="example.invalid"))
    assert result["statusCode"] == 401
