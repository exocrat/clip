"""Bound aggregate API traffic per process without retaining client identifiers."""

from collections import deque
from time import monotonic

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import ERRORS, error_response


class ApiRateLimitMiddleware:
    """Apply separate rolling one-minute limits to API reads and writes.

    Counters are per process, reset on restart, and are not shared by replicas.
    Health checks and static frontend paths are excluded.
    """

    def __init__(
        self, app: ASGIApp, read_limit: int, write_limit: int, api_prefix_only: bool
    ) -> None:
        self.app = app
        self.read_limit = read_limit
        self.write_limit = write_limit
        self.api_prefix_only = api_prefix_only
        self.reads: deque[float] = deque()
        self.writes: deque[float] = deque()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        # Hosted traffic uses /api; direct local API routes have no prefix.
        if path == "/health" or (self.api_prefix_only and not path.startswith("/api/")):
            await self.app(scope, receive, send)
            return
        is_read = scope.get("method") in {"GET", "HEAD", "OPTIONS"}
        entries = self.reads if is_read else self.writes
        limit = self.read_limit if is_read else self.write_limit
        now = monotonic()
        while entries and entries[0] <= now - 60:
            entries.popleft()
        if len(entries) >= limit:
            retry = max(1, int(60 - (now - entries[0])) + 1)
            response = error_response(
                Request(scope), ERRORS[429], headers={"Retry-After": str(retry)}
            )
            await response(scope, receive, send)
            return
        entries.append(now)
        await self.app(scope, receive, send)
