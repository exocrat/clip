"""Connection cleanup must precede Lambda's observable completed HTTP response."""

import asyncio
from contextlib import asynccontextmanager
import pytest
from app.domains.identity.http import IdentityInvocationConnectionsMiddleware


def test_terminal_response_is_forwarded_only_after_owned_connections_close():
    async def exercise():
        events, sent = [], []

        @asynccontextmanager
        async def request_scope():
            events.append("opened")
            try:
                yield
            finally:
                events.append("closed")

        async def application(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"test", b"same")],
                }
            )
            await send(
                {"type": "http.response.body", "body": b"first", "more_body": True}
            )
            await send({"type": "http.response.body", "body": b"last"})
            events.append("handler-returned")

        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.body" and not message.get("more_body"):
                assert events[-1] == "closed"
            sent.append(message)

        await IdentityInvocationConnectionsMiddleware(application, request_scope)(
            {"type": "http", "path": "/api/listings"}, receive, send
        )
        assert events == ["opened", "handler-returned", "closed"]
        assert sent[0]["status"] == 200 and sent[0]["headers"] == [(b"test", b"same")]
        assert (
            b"".join(x["body"] for x in sent if x["type"] == "http.response.body")
            == b"firstlast"
        )

    asyncio.run(exercise())


def test_cleanup_failure_never_completes_a_successful_body():
    async def exercise():
        sent = []

        @asynccontextmanager
        async def request_scope():
            yield
            raise RuntimeError("synthetic cleanup failure")

        async def application(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"success"})

        async def send(message):
            sent.append(message)

        with pytest.raises(RuntimeError):
            await IdentityInvocationConnectionsMiddleware(application, request_scope)(
                {"type": "http", "path": "/api/listings"}, None, send
            )
        assert all(message["type"] != "http.response.body" for message in sent)

    asyncio.run(exercise())
