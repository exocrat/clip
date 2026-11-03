"""Explicit, not-yet-installed ECS middleware for Lambda-first Listing reads.

The caller must establish trusted proxy/HTTPS and provide a reviewed, no-retry
Lambda client. This component is not enabled by environment variables and is
not a deployment authorization or proof of real session parity.
"""

from dataclasses import dataclass, field
from functools import partial
import logging
import re
from typing import Any, Literal

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import ERRORS, error_response
from app.overflow_admission import (
    BoundedInvoker,
    RouterAtCapacity,
    RouterDeadlineExceeded,
)
from app.overflow_dispatch import LambdaAtCapacity
from app.overflow_event import build_read_event, clean_ingress_headers
from app.overflow_invoke import invoke_read
from app.overflow_response import parse_read_response
from app.overflow_event import _TARGET_GROUP
from app.overflow_invoke import _TARGET

_DETAIL = re.compile(
    r"/api/listings/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"
)


class OverflowCounts:
    """Keep process-local routing totals without request or identity data.

    These counters are updated on one ASGI event loop and emitted once at
    shutdown; aggregation across ECS tasks is a separate analysis step.
    """

    def __init__(self, run_id: str | None = None) -> None:
        if run_id is not None and (
            not isinstance(run_id, str)
            or not 3 <= len(run_id) <= 10
            or not run_id.isascii()
            or not run_id.isalnum()
            or run_id != run_id.lower()
        ):
            raise ValueError("Invalid overflow run identifier")
        self.run_id = run_id
        self.lambda_responses = 0
        self.capacity_fallbacks = 0
        self.router_capacity_rejections = 0
        self.deadline_failures = 0
        self.lambda_failures = 0
        self.rejected_requests = 0
        self.lambda_2xx = 0
        self.lambda_3xx = 0
        self.lambda_4xx = 0
        self.lambda_5xx = 0
        self.ecs_fallback_2xx = 0
        self.ecs_fallback_3xx = 0
        self.ecs_fallback_4xx = 0
        self.ecs_fallback_5xx = 0

    def snapshot(self) -> dict[str, int]:
        """Return a copy of safe aggregate counts, not proof of completed work."""
        return {
            "lambda_responses": self.lambda_responses,
            "capacity_fallbacks": self.capacity_fallbacks,
            "router_capacity_rejections": self.router_capacity_rejections,
            "deadline_failures": self.deadline_failures,
            "lambda_failures": self.lambda_failures,
            "rejected_requests": self.rejected_requests,
            "lambda_2xx": self.lambda_2xx,
            "lambda_3xx": self.lambda_3xx,
            "lambda_4xx": self.lambda_4xx,
            "lambda_5xx": self.lambda_5xx,
            "ecs_fallback_2xx": self.ecs_fallback_2xx,
            "ecs_fallback_3xx": self.ecs_fallback_3xx,
            "ecs_fallback_4xx": self.ecs_fallback_4xx,
            "ecs_fallback_5xx": self.ecs_fallback_5xx,
        }

    def record_response_status(
        self, backend: Literal["lambda", "ecs_fallback"], status: object
    ) -> None:
        """Count only a validated HTTP status group for one selected backend."""
        if type(status) is not int or not 200 <= status <= 599:
            return
        family = status // 100
        if family not in {2, 3, 4, 5}:
            return
        setattr(
            self, f"{backend}_{family}xx", getattr(self, f"{backend}_{family}xx") + 1
        )

    def emit_summary(self) -> None:
        """Write one privacy-safe process summary for later log aggregation."""
        fields: dict[str, int | str] = {**self.snapshot()}
        if self.run_id is not None:
            fields["run_id"] = self.run_id
        logging.getLogger("clip").info(
            "",
            extra={"event": "overflow_summary", **fields},
        )


@dataclass(frozen=True)
class OverflowDependencies:
    """Explicit private client and same-run targets supplied by trusted composition.

    Construction performs no credential lookup or network I/O. Live proxy
    trust, timeout, concurrency and IAM remain separate deployment checks.
    """

    client: Any = field(repr=False)
    target: str
    target_group: str
    invoker: BoundedInvoker = field(repr=False)
    counts: OverflowCounts = field(default_factory=OverflowCounts, repr=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.target, str)
            or _TARGET.fullmatch(self.target) is None
            or not isinstance(self.target_group, str)
            or _TARGET_GROUP.fullmatch(self.target_group) is None
            or not callable(getattr(self.client, "invoke", None))
            or not isinstance(self.counts, OverflowCounts)
            or not isinstance(self.invoker, BoundedInvoker)
        ):
            raise ValueError("Invalid overflow dependencies")
        target_run = self.target.split(":function:clip-exp03-", 1)[1].split(":", 1)[0]
        group_run = self.target_group.split(":targetgroup/clip-exp03-", 1)[1].split(
            "-ecs/", 1
        )[0]
        config = getattr(getattr(self.client, "meta", None), "config", None)
        retries = getattr(config, "retries", None)
        if (
            target_run != group_run
            or not isinstance(retries, dict)
            or retries.get("total_max_attempts") != 1
        ):
            raise ValueError("Invalid overflow dependencies")


class OverflowReadMiddleware:
    """Route selected reads once to Lambda, falling back only on throttling."""

    def __init__(
        self,
        app: ASGIApp,
        client: Any,
        target: str,
        target_group: str,
        invoker: BoundedInvoker,
        counts: OverflowCounts | None = None,
    ):
        """Bind an explicit client/targets; never discover credentials or endpoints."""
        self.app = app
        self.client = client
        self.target = target
        self.target_group = target_group
        self.invoker = invoker
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
            payload = await self.invoker.invoke(
                partial(invoke_read, self.client, self.target, event)
            )
        except LambdaAtCapacity:
            self.counts.capacity_fallbacks += 1

            async def send_fallback(message: Message) -> None:
                """Count fallback status only; never inspect response contents."""
                if message.get("type") == "http.response.start":
                    self.counts.record_response_status(
                        "ecs_fallback", message.get("status")
                    )
                await send(message)

            await self.app(scope, receive, send_fallback)
            return
        except RouterAtCapacity:
            self.counts.router_capacity_rejections += 1
            await error_response(Request(scope), ERRORS[503])(scope, receive, send)
            return
        except RouterDeadlineExceeded:
            self.counts.deadline_failures += 1
            await error_response(Request(scope), ERRORS[503])(scope, receive, send)
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
        self.counts.record_response_status("lambda", response.status)
        await send(
            {
                "type": "http.response.start",
                "status": response.status,
                "headers": list(response.headers)
                + [(b"content-length", str(len(response.body)).encode("ascii"))],
            }
        )
        await send({"type": "http.response.body", "body": response.body})
