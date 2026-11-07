"""Bound API traffic per verified account or anonymous transport peer."""

from collections import OrderedDict, deque
from dataclasses import dataclass, field
from time import monotonic

from starlette.requests import Request
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


class ApiRateLimitMiddleware:
    """Apply rolling limits to verified accounts or, when configured, peers.

    Anonymous requests share the transport peer's allowance; forwarded headers
    are never read here. Counters are per process, reset at restart, and are not
    shared by replicas. Health checks and static frontend paths are excluded.
    """

    def __init__(
        self,
        app: ASGIApp,
        read_limit: int,
        write_limit: int,
        api_prefix_only: bool,
        peer_only: bool = False,
    ) -> None:
        self.app = app
        self.read_limit = read_limit
        self.write_limit = write_limit
        self.api_prefix_only = api_prefix_only
        self.peer_only = peer_only
        self.clients: OrderedDict[tuple[str, str], ClientWindow] = OrderedDict()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == "/health" or (self.api_prefix_only and not path.startswith("/api/")):
            await self.app(scope, receive, send)
            return

        caller = scope.get("clip.caller")
        peer = scope.get("client")
        key = (
            ("user", str(caller.user_id))
            if not self.peer_only and isinstance(caller, CallerContext)
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
            response = error_response(
                Request(scope), ERRORS[429], headers={"Retry-After": "60"}
            )
            await response(scope, receive, send)
            return
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
            response = error_response(
                Request(scope), ERRORS[429], headers={"Retry-After": str(retry)}
            )
            await response(scope, receive, send)
            return
        entries.append(now)
        await self.app(scope, receive, send)
