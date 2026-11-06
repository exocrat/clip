"""Bound API traffic per transport-resolved client, without trusting request headers."""

from collections import OrderedDict, deque
from ipaddress import ip_address
from time import monotonic

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import ERRORS, error_response

# Retain at most this many active client addresses per process.
MAX_TRACKED_CLIENTS = 10000
WINDOW_SECONDS = 60


class ApiRateLimitMiddleware:
    """Keep bounded rolling read/write counters per client and process.

    The transport must establish scope.client using only trusted proxies. Missing
    or invalid addresses share an unknown bucket; forwarding headers are ignored.
    """

    def __init__(
        self, app: ASGIApp, read_limit: int, write_limit: int, api_prefix_only: bool
    ) -> None:
        self.app = app
        self.read_limit = read_limit
        self.write_limit = write_limit
        self.api_prefix_only = api_prefix_only
        self.clients: OrderedDict[str, tuple[float, deque[float], deque[float]]] = (
            OrderedDict()
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == "/health" or (self.api_prefix_only and not path.startswith("/api/")):
            await self.app(scope, receive, send)
            return
        try:
            client = str(ip_address(scope["client"][0]))
        except KeyError, TypeError, ValueError, IndexError:
            client = "unknown"
        now = monotonic()
        while self.clients:
            oldest = next(iter(self.clients))
            if self.clients[oldest][0] > now - WINDOW_SECONDS:
                break
            self.clients.popitem(last=False)
        record = self.clients.pop(client, None)
        if record is None:
            if len(self.clients) >= MAX_TRACKED_CLIENTS:
                response = error_response(
                    Request(scope),
                    ERRORS[429],
                    headers={"Retry-After": str(WINDOW_SECONDS)},
                )
                await response(scope, receive, send)
                return
            reads, writes = deque(), deque()
        else:
            _, reads, writes = record
        self.clients[client] = (now, reads, writes)
        is_read = scope.get("method") in {"GET", "HEAD", "OPTIONS"}
        entries = reads if is_read else writes
        limit = self.read_limit if is_read else self.write_limit
        while entries and entries[0] <= now - WINDOW_SECONDS:
            entries.popleft()
        if len(entries) >= limit:
            retry = max(1, int(WINDOW_SECONDS - (now - entries[0])) + 1)
            response = error_response(
                Request(scope), ERRORS[429], headers={"Retry-After": str(retry)}
            )
            await response(scope, receive, send)
            return
        entries.append(now)
        await self.app(scope, receive, send)
