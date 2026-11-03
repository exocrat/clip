"""Local ALB-to-ASGI bridge; production handler and lifecycle are not installed."""

from collections.abc import Awaitable, Callable
import re
from typing import Any

from app.alb_event import parse_alb_read

ASGIApp = Callable[
    [dict[str, Any], Callable[..., Awaitable[Any]], Callable[..., Awaitable[Any]]],
    Awaitable[None],
]


async def invoke_read(
    app: ASGIApp, event: object, *, trusted_host: str
) -> dict[str, Any]:
    """Forward a parsed request to an injected app under an explicitly bound host.

    This helper does not authenticate requests or establish ingress trust. Its
    caller must validate the Lambda invocation source and bind the actual HTTPS
    host before it can be used outside a local synthetic test.
    """
    request = parse_alb_read(event)
    if not re.fullmatch(
        r"/(?:api/)?listings(?:/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})?",
        request.path,
    ):
        raise ValueError("Invalid ALB read route")
    if (
        not trusted_host
        or not trusted_host.isascii()
        or any(c in trusted_host for c in "/:\r\n ")
    ):
        raise ValueError("Invalid trusted host")
    supplied_hosts = [v for k, v in request.headers if k == b"host"]
    if supplied_hosts != [trusted_host.encode("ascii")]:
        raise ValueError("Invalid request host")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": request.method,
        "scheme": "https",
        "path": request.path,
        "raw_path": request.path.encode("utf-8"),
        "query_string": request.query_string,
        "headers": list(request.headers),
        "server": (trusted_host, 443),
        "client": None,
        "root_path": "",
    }
    status: int | None = None
    headers: dict[str, list[str]] = {}
    chunks: list[bytes] = []
    finished = False
    received = False

    async def receive() -> dict[str, Any]:
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        nonlocal status, finished
        kind = message.get("type")
        if kind == "http.response.start" and status is None:
            status = message["status"]
            for name, value in message.get("headers", []):
                headers.setdefault(name.decode("ascii").lower(), []).append(
                    value.decode("latin-1")
                )
        elif kind == "http.response.body" and status is not None and not finished:
            chunks.append(message.get("body", b""))
            if sum(map(len, chunks)) > 1_000_000:
                raise ValueError("Response too large")
            finished = not message.get("more_body", False)
        else:
            raise ValueError("Invalid ASGI response")

    await app(scope, receive, send)
    if (
        status is None
        or not finished
        or not isinstance(status, int)
        or not 100 <= status <= 599
    ):
        raise ValueError("Invalid ASGI response")
    import base64

    return {
        "statusCode": status,
        "multiValueHeaders": headers,
        "isBase64Encoded": True,
        "body": base64.b64encode(b"".join(chunks)).decode("ascii"),
    }
