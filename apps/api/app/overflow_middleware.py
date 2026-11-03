"""Explicit, not-yet-installed ECS middleware for Lambda-first Listing reads.

The caller must establish trusted proxy/HTTPS and provide a reviewed, no-retry
Lambda client. This component is not enabled by environment variables and is
not a deployment authorization or proof of real session parity.
"""

import asyncio
import re
from typing import Any

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import ERRORS, error_response
from app.overflow_dispatch import LambdaAtCapacity
from app.overflow_event import build_read_event, clean_ingress_headers
from app.overflow_invoke import invoke_read
from app.overflow_response import parse_read_response

_DETAIL = re.compile(
    r"/api/listings/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"
)


class OverflowCounts:
    """Keep process-local routing totals without request or identity data.

    These counters are updated on one ASGI event loop and are not durable or
    aggregated across processes. A reviewed exporter is still required.
    """

    def __init__(self) -> None:
        self.lambda_responses = 0
        self.capacity_fallbacks = 0
        self.lambda_failures = 0
        self.rejected_requests = 0

    def snapshot(self) -> dict[str, int]:
        """Return a copy of safe aggregate counts, not proof of completed work."""
        return {
            "lambda_responses": self.lambda_responses,
            "capacity_fallbacks": self.capacity_fallbacks,
            "lambda_failures": self.lambda_failures,
            "rejected_requests": self.rejected_requests,
        }


class OverflowReadMiddleware:
    """Route selected reads once to Lambda, falling back only on throttling."""

    def __init__(
        self,
        app: ASGIApp,
        client: Any,
        target: str,
        target_group: str,
        counts: OverflowCounts | None = None,
    ):
        """Bind an explicit client/targets; never discover credentials or endpoints."""
        self.app = app
        self.client = client
        self.target = target
        self.target_group = target_group
        self.counts = counts if counts is not None else OverflowCounts()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Keep other routes on ECS and fail closed on untrusted or broken input."""
        path = scope.get("path", "")
        if (
            scope["type"] != "http"
            or scope.get("method") != "GET"
            or not isinstance(path, str)
            or not (path == "/api/listings" or _DETAIL.fullmatch(path))
        ):
            await self.app(scope, receive, send)
            return
        if scope.get("scheme") != "https":
            self.counts.rejected_requests += 1
            await error_response(Request(scope), ERRORS[403])(scope, receive, send)
            return
        try:
            headers = scope.get("headers", [])
            lengths = [v for k, v in headers if k.lower() == b"content-length"]
            if len(lengths) > 1 or (lengths and lengths != [b"0"]):
                raise ValueError("Unexpected read body")
            if any(k.lower() == b"transfer-encoding" for k, _ in headers):
                raise ValueError("Unexpected read body")
            clean = clean_ingress_headers(scope.get("scheme", ""), headers)
            event = build_read_event(
                "GET",
                path,
                scope.get("query_string", b""),
                clean,
                self.target_group,
                trusted_https=True,
            )
        except TypeError, ValueError:
            self.counts.rejected_requests += 1
            await error_response(Request(scope), ERRORS[400])(scope, receive, send)
            return
        try:
            payload = await asyncio.to_thread(
                invoke_read, self.client, self.target, event
            )
        except LambdaAtCapacity:
            self.counts.capacity_fallbacks += 1
            await self.app(scope, receive, send)
            return
        except Exception:
            self.counts.lambda_failures += 1
            await error_response(Request(scope), ERRORS[503])(scope, receive, send)
            return
        try:
            response = parse_read_response(payload)
        except ValueError:
            self.counts.lambda_failures += 1
            await error_response(Request(scope), ERRORS[503])(scope, receive, send)
            return
        self.counts.lambda_responses += 1
        await send(
            {
                "type": "http.response.start",
                "status": response.status,
                "headers": list(response.headers)
                + [(b"content-length", str(len(response.body)).encode("ascii"))],
            }
        )
        await send({"type": "http.response.body", "body": response.body})
