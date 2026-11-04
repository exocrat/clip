"""Central metadata redaction and real ASGI correlation lifecycle."""

import asyncio
import json
import logging
from types import SimpleNamespace

import pytest

from app.core.identifiers import parse_id
from app.core.logging import (
    RequestLoggingMiddleware,
    SafeJsonFormatter,
    configure_logging,
    request_id_context,
)
from app.core.timestamps import parse_timestamp

SENTINEL = "synthetic-private-value"


def test_stage_timing_preserves_failure_and_logs_only_safe_metadata(monkeypatch):
    """Stage instrumentation keeps exceptions and never emits request input."""
    import app.core.logging as module

    captured = []
    monkeypatch.setattr(
        module.logging.getLogger("clip"),
        "info",
        lambda _, extra: captured.append(extra),
    )
    ticks = iter([1.0, 1.025])
    monkeypatch.setattr(module, "monotonic", lambda: next(ticks))
    token = request_id_context.set("12345678-1234-4234-8234-123456789abc")
    try:
        with pytest.raises(RuntimeError, match=SENTINEL):
            with module.request_stage("identity.authenticate"):
                raise RuntimeError(SENTINEL)
    finally:
        request_id_context.reset(token)
    assert len(captured) == 1
    record = make_record(**captured[0])
    output = SafeJsonFormatter().format(record)
    body = json.loads(output)
    assert body["stage"] == "identity.authenticate" and body["duration_ms"] == 25
    assert SENTINEL not in output
    assert "stage" not in json.loads(
        SafeJsonFormatter().format(make_record(event="request_stage", stage=SENTINEL))
    )


def make_record(**extras):
    """Construct a synthetic record without opening a log file or external sink."""
    record = logging.LogRecord("clip", logging.INFO, __file__, 1, SENTINEL, (), None)
    record.__dict__.update(extras)
    return record


class Unrenderable:
    """Private objects must be discarded, not stringified by logging."""

    def __str__(self):
        """Fail if the formatter attempts to render arbitrary payload objects."""
        raise AssertionError("Private object must not be rendered")


@pytest.mark.parametrize(
    "key",
    [
        "token",
        "secret",
        "otp",
        "private_key",
        "message_plaintext",
        "message_ciphertext",
        "upi_id",
        "email",
        "phone",
        "body",
        "headers",
    ],
)
def test_unknown_sensitive_fields_and_raw_messages_are_omitted(key):
    """Central allowlisting drops every prohibited field and raw logging text."""
    record = make_record(**{key: SENTINEL, "event": "request_completed"})
    record.args = (Unrenderable(),)
    record.exc_info = (RuntimeError, RuntimeError(SENTINEL), None)
    record.exc_text = SENTINEL
    output = SafeJsonFormatter().format(record)
    parsed = json.loads(output)
    assert set(parsed) == {"timestamp", "severity", "event"}
    assert parsed["event"] == "request_completed"
    assert parse_timestamp(parsed["timestamp"])
    assert SENTINEL not in output


def test_log_values_are_structured_bounded_and_allowlisted():
    """Approved metadata remains useful while unknown events/methods are dropped."""
    record = make_record(
        event=SENTINEL,
        method=SENTINEL,
        route="/registered/" + "x" * 300,
        status=200,
        duration_ms=12.34567,
        request_id="not-a-uuid",
    )
    parsed = json.loads(SafeJsonFormatter().format(record))
    assert parsed["event"] == "runtime_event"
    assert "method" not in parsed and "request_id" not in parsed
    assert len(parsed["route"]) == 256
    assert parsed["status"] == 200
    assert parsed["duration_ms"] == 12.346


@pytest.mark.parametrize(
    ("status", "duration"),
    [(True, -1), (99, float("nan")), (600, float("inf")), ("200", SENTINEL)],
)
def test_invalid_numeric_metadata_is_not_emitted(status, duration):
    """Invalid numeric values cannot corrupt JSON or masquerade as diagnostics."""
    parsed = json.loads(
        SafeJsonFormatter().format(make_record(status=status, duration_ms=duration))
    )
    assert "status" not in parsed and "duration_ms" not in parsed


def test_logging_configuration_is_repeatable_and_protects_uvicorn(
    log_stream, monkeypatch
):
    """Repeated setup must not duplicate logs or render Uvicorn's raw messages."""
    # Pytest swaps stderr between fixture setup and call; bind the call stream.
    monkeypatch.setattr("sys.stderr", log_stream)
    configure_logging()
    for name in ("clip", "uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        assert len(logger.handlers) == 1
        assert logger.propagate is False
        logger.error(SENTINEL, exc_info=(RuntimeError, RuntimeError(SENTINEL), None))
    lines = log_stream.getvalue().splitlines()
    assert len(lines) == 4
    assert all(json.loads(line)["severity"] == "ERROR" for line in lines)
    assert SENTINEL not in log_stream.getvalue()


def test_concurrent_requests_keep_distinct_correlated_ids(log_stream):
    """Interleaved requests preserve their own context and restore the outer task."""

    async def scenario():
        """Run two real ASGI calls with a barrier forcing request overlap."""
        entered = 0
        ready = asyncio.Event()
        seen = []

        async def endpoint(scope, receive, send):
            """Observe context before/after interleaving and emit a tiny response."""
            nonlocal entered
            initial = request_id_context.get()
            entered += 1
            if entered == 2:
                ready.set()
            await ready.wait()
            assert request_id_context.get() == initial == scope["clip.request_id"]
            scope["route"] = SimpleNamespace(path="/items/{item_id}")
            seen.append(initial)
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"x-request-id", b"untrusted")],
                }
            )
            await send({"type": "http.response.body", "body": b"{}"})

        middleware = RequestLoggingMiddleware(endpoint)

        async def request():
            """Collect response messages without sockets or an HTTP client."""
            messages = []

            async def receive():
                """Supply a synthetic empty request if the app asks for one."""
                return {"type": "http.request", "body": b""}

            async def send(message):
                """Collect the server's response for assertions."""
                messages.append(message)

            scope = {
                "type": "http",
                "method": "GET",
                "path": "/" + SENTINEL,
                "query_string": SENTINEL.encode(),
                "headers": [(b"x-request-id", b"untrusted")],
            }
            await middleware(scope, receive, send)
            identifiers = [
                value.decode()
                for key, value in messages[0]["headers"]
                if key == b"x-request-id"
            ]
            assert identifiers == [scope["clip.request_id"]]
            assert parse_id(identifiers[0])
            return identifiers[0]

        outer = request_id_context.set("outer-test-context")
        try:
            identifiers = await asyncio.wait_for(
                asyncio.gather(request(), request()), timeout=3
            )
            assert len(set(identifiers)) == 2
            assert set(identifiers) == set(seen)
            assert request_id_context.get() == "outer-test-context"
            return identifiers
        finally:
            request_id_context.reset(outer)

    identifiers = asyncio.run(scenario())
    records = [json.loads(line) for line in log_stream.getvalue().splitlines()]
    assert {record["request_id"] for record in records} == set(identifiers)
    assert all(record["route"] == "/items/{item_id}" for record in records)
    assert SENTINEL not in log_stream.getvalue()


def test_failure_after_response_start_stays_a_transport_failure(log_stream):
    """A streaming failure cannot become success or leak its original exception."""
    messages = []

    async def scenario():
        """Exercise response-started failure directly at the ASGI boundary."""

        async def endpoint(scope, receive, send):
            """Send headers, then fail with controlled synthetic private text."""
            await send({"type": "http.response.start", "status": 200, "headers": []})
            raise RuntimeError(SENTINEL)

        async def receive():
            """Supply a synthetic empty request."""
            return {"type": "http.request", "body": b""}

        async def send(message):
            """Keep response messages in memory only."""
            messages.append(message)

        middleware = RequestLoggingMiddleware(endpoint)
        await middleware({"type": "http", "method": "GET"}, receive, send)

    with pytest.raises(RuntimeError, match="after headers were sent") as captured:
        asyncio.run(scenario())
    assert captured.value.__suppress_context__ is True
    assert SENTINEL not in str(captured.value) + log_stream.getvalue()
    assert len(messages) == 1
    assert json.loads(log_stream.getvalue())["event"] == "request_failed"
    assert request_id_context.get() is None


def test_non_http_scopes_pass_through_without_request_context(log_stream):
    """HTTP correlation must not change lifespan or WebSocket protocols."""

    async def scenario():
        """Verify exact scope/receive/send passthrough without a fake HTTP response."""
        scope = {"type": "lifespan"}

        async def receive():
            """Return a synthetic lifespan event only if requested."""
            return {"type": "lifespan.startup"}

        async def send(message):
            """Reject any unexpected middleware-generated protocol response."""
            raise AssertionError("No response expected")

        async def endpoint(actual_scope, actual_receive, actual_send):
            """Assert identity of protocol inputs forwarded by the middleware."""
            assert actual_scope is scope
            assert actual_receive is receive and actual_send is send
            assert "clip.request_id" not in scope

        await RequestLoggingMiddleware(endpoint)(scope, receive, send)

    asyncio.run(scenario())
    assert log_stream.getvalue() == ""
