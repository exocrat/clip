"""Controlled JSON diagnostics and ASGI request correlation without private input."""

from contextvars import ContextVar
from datetime import UTC, datetime
import json
import logging
import math
import sys
from time import monotonic

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import ERRORS, error_response
from app.core.identifiers import format_id, new_id, parse_id
from app.core.timestamps import format_timestamp

request_id_context: ContextVar[str | None] = ContextVar("clip_request_id", default=None)
_EVENTS = {
    "request_completed",
    "request_failed",
    "runtime_event",
    "provider_unavailable",
}
_METHODS = {
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
    "TRACE",
    "CONNECT",
}


class SafeJsonFormatter(logging.Formatter):
    """Allow only controlled fields; discard message/args/exceptions and unknown extras.

    This also protects Uvicorn's access/error records, whose normal text can
    contain request targets or raw exception data. No repr/str of payload objects
    is used. Callers still must not place sensitive data in approved fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Serialize bounded diagnostic metadata, ignoring arbitrary log content."""
        event = getattr(record, "event", None)
        output = {
            "timestamp": format_timestamp(datetime.now(UTC)),
            "severity": logging.getLevelName(record.levelno),
            "event": (
                event
                if isinstance(event, str) and event in _EVENTS
                else "runtime_event"
            ),
        }
        identifier = getattr(record, "request_id", None) or request_id_context.get()
        if isinstance(identifier, str):
            try:
                output["request_id"] = format_id(parse_id(identifier))
            except ValueError:
                pass
        method = getattr(record, "method", None)
        if isinstance(method, str) and method in _METHODS:
            output["method"] = method
        # route is a code-owned template, never scope.path or a user-supplied URL.
        route = getattr(record, "route", None)
        if isinstance(route, str):
            output["route"] = route[:256]
        status = getattr(record, "status", None)
        if type(status) is int and 100 <= status <= 599:
            output["status"] = status
        duration = getattr(record, "duration_ms", None)
        if type(duration) in (int, float) and math.isfinite(duration) and duration >= 0:
            output["duration_ms"] = round(duration, 3)
        return json.dumps(output, ensure_ascii=True, allow_nan=False)


def configure_logging() -> None:
    """Configure application/Uvicorn diagnostics once, without logging configuration.

    Other libraries are not granted a shared-core safe logging guarantee. Provider
    integrations must review their own logging and must not enable payload dumps.
    """
    for name in ("clip", "uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(SafeJsonFormatter())
        logger.handlers = [handler]
        logger.propagate = False
        logger.setLevel(logging.INFO)


class RequestLoggingMiddleware:
    """Assign request IDs, emit safe metadata, and contain unexpected HTTP failures."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap ASGI directly to preserve streaming and request-context isolation."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Propagate correlation and record status without reading request content."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        identifier = format_id(new_id())
        scope["clip.request_id"] = identifier
        token = request_id_context.set(identifier)
        started_at = monotonic()
        status = 500
        response_started = False
        failed = False

        async def send_correlated(message: Message) -> None:
            """Set the authoritative response ID and observe status only."""
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status = message["status"]
                response_started = True
                message = dict(message)
                message["headers"] = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower() != b"x-request-id"
                ] + [(b"x-request-id", identifier.encode("ascii"))]
            await send(message)

        try:
            await self.app(scope, receive, send_correlated)
        except Exception:
            failed = True
            if response_started:
                # A streaming response cannot be replaced. Keep the transport
                # failure visible while preventing the original private message
                # from escaping to server diagnostics.
                raise RuntimeError(
                    "HTTP response failed after headers were sent"
                ) from None
            response = error_response(Request(scope), ERRORS[500])
            await response(scope, receive, send_correlated)
        finally:
            try:
                route = getattr(scope.get("route"), "path", "[unmatched]")
                logging.getLogger("clip").info(
                    "",
                    extra={
                        "event": "request_failed" if failed else "request_completed",
                        "request_id": identifier,
                        "method": scope.get("method"),
                        "route": route,
                        "status": status,
                        "duration_ms": (monotonic() - started_at) * 1000,
                    },
                )
            finally:
                request_id_context.reset(token)
