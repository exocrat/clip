"""Bound API traffic per verified account or anonymous transport peer."""

from collections import OrderedDict, deque
from dataclasses import dataclass, field
from time import monotonic

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.auth import CallerContext
from app.core.errors import ERRORS, error_response

# Bound memory even when a large number of different peers contact this process.
MAX_ACTIVE_CLIENTS = 10000


@dataclass
class ClientWindow:
    """Retain one client's recent reads and writes, never credentials or headers."""

    reads: deque[float] = field(default_factory=deque)
    writes: deque[float] = field(default_factory=deque)
    last_seen: float = 0


class ApiRateLimiter:
    """Reserve a rolling request budget after trusted session classification.

    Verified accounts have independent budgets; only anonymous requests share
    a transport peer's allowance. Cookies and forwarded headers never select
    an account key. Reservation is synchronous so one event-loop invocation
    checks and charges a budget without yielding. Counters are bounded, local
    to one process, and reset at restart; replicas do not share them.
    """

    def __init__(
        self,
        read_limit: int,
        write_limit: int,
        api_prefix_only: bool,
    ) -> None:
        self.read_limit = read_limit
        self.write_limit = write_limit
        self.api_prefix_only = api_prefix_only
        self.clients: OrderedDict[tuple[str, str], ClientWindow] = OrderedDict()

    def reject(self, scope: Scope) -> Response | None:
        """Charge one request, or return a safe 429 without running its handler.

        Identity calls this after setting or rejecting the trusted caller, even
        when it will reject the request itself. With no Identity runtime, the
        standalone middleware uses the same budget before calling the app.
        """
        if scope["type"] != "http":
            return None
        path = scope.get("path", "")
        if path == "/health" or (self.api_prefix_only and not path.startswith("/api/")):
            return None

        caller = scope.get("clip.caller")
        peer = scope.get("client")
        key = (
            ("user", str(caller.user_id))
            if isinstance(caller, CallerContext)
            else ("peer", str(peer[0]) if peer else "unknown")
        )
        now = monotonic()
        while self.clients:
            oldest = next(iter(self.clients))
            if self.clients[oldest].last_seen > now - 60:
                break
            self.clients.popitem(last=False)
        window = self.clients.get(key)
        if window is None and len(self.clients) >= MAX_ACTIVE_CLIENTS:
            return error_response(
                Request(scope), ERRORS[429], headers={"Retry-After": "60"}
            )
        if window is None:
            window = ClientWindow()
            self.clients[key] = window
        window.last_seen = now
        self.clients.move_to_end(key)
        is_read = scope.get("method") in {"GET", "HEAD", "OPTIONS"}
        entries = window.reads if is_read else window.writes
        limit = self.read_limit if is_read else self.write_limit
        while entries and entries[0] <= now - 60:
            entries.popleft()
        if len(entries) >= limit:
            retry = max(1, int(60 - (now - entries[0])) + 1)
            return error_response(
                Request(scope), ERRORS[429], headers={"Retry-After": str(retry)}
            )
        entries.append(now)
        return None


class ApiRateLimitMiddleware(ApiRateLimiter):
    """Apply the same budget to apps without the trusted Identity boundary."""

    def __init__(
        self,
        app: ASGIApp,
        read_limit: int,
        write_limit: int,
        api_prefix_only: bool,
    ) -> None:
        super().__init__(read_limit, write_limit, api_prefix_only)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Reject before the handler, preserving health/static/non-HTTP bypasses."""
        rejection = self.reject(scope)
        if rejection is not None:
            await rejection(scope, receive, send)
            return
        await self.app(scope, receive, send)
