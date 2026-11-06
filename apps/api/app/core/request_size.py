"""Reject oversized API request bodies before JSON parsing."""

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import ERRORS, error_response

# Encrypted messages fit within this API limit; images upload directly to S3.
MAX_API_BODY_BYTES = 1_048_576


class ApiRequestSizeMiddleware:
    """Buffer at most one bounded API body, including chunked/unknown lengths."""

    def __init__(self, app: ASGIApp, api_prefix_only: bool) -> None:
        self.app = app
        self.api_prefix_only = api_prefix_only

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope.get("method") in {"GET", "HEAD", "OPTIONS"}
            or (self.api_prefix_only and not scope.get("path", "").startswith("/api/"))
        ):
            await self.app(scope, receive, send)
            return
        lengths = [
            value
            for name, value in scope.get("headers", [])
            if name.lower() == b"content-length"
        ]
        if lengths:
            if len(lengths) != 1 or not lengths[0].isdigit() or len(lengths[0]) > 20:
                await error_response(Request(scope), ERRORS[400])(scope, receive, send)
                return
            if int(lengths[0]) > MAX_API_BODY_BYTES:
                await error_response(Request(scope), ERRORS[413])(scope, receive, send)
                return
        chunks = bytearray()
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                return
            body = message.get("body", b"")
            total += len(body)
            if total > MAX_API_BODY_BYTES:
                await error_response(Request(scope), ERRORS[413])(scope, receive, send)
                return
            chunks.extend(body)
            if not message.get("more_body", False):
                break
        buffered = bytes(chunks)
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": buffered, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
