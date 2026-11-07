"""Exercise client isolation and request-size checks at the ASGI boundary."""

import asyncio

from app.core.rate_limit import ApiRateLimitMiddleware
from app.core.request_size import ApiRequestSizeMiddleware


async def _ok(scope, receive, send):
    message = await receive()
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": message.get("body", b"")})


def _request(app, client, chunks, headers=(), method="POST"):
    async def run():
        messages = iter(chunks)
        sent = []

        async def receive():
            return next(messages, {"type": "http.disconnect"})

        async def send(message):
            sent.append(message)

        await app(
            {
                "type": "http",
                "method": method,
                "path": "/api/example",
                "headers": list(headers),
                "client": client,
            },
            receive,
            send,
        )
        return sent

    return asyncio.run(run())


def test_rate_limit_isolated_between_clients_and_ignores_forwarding():
    app = ApiRateLimitMiddleware(_ok, read_limit=2, write_limit=2, api_prefix_only=True)
    body = [{"type": "http.request", "body": b"", "more_body": False}]
    a, b = ("192.0.2.1", 10), ("192.0.2.2", 10)
    assert _request(app, a, body)[0]["status"] == 200
    assert _request(app, a, body)[0]["status"] == 200
    assert (
        _request(app, a, body, [(b"x-forwarded-for", b"192.0.2.2")])[0]["status"] == 429
    )
    assert _request(app, b, body)[0]["status"] == 200


def test_size_limit_checks_declared_and_streamed_lengths(monkeypatch):
    monkeypatch.setattr("app.core.request_size.MAX_API_BODY_BYTES", 4)
    app = ApiRequestSizeMiddleware(_ok, api_prefix_only=True)
    client = ("192.0.2.1", 10)
    assert _request(app, client, [], [(b"content-length", b"5")])[0]["status"] == 413
    assert (
        _request(
            app,
            client,
            [
                {"type": "http.request", "body": b"abc", "more_body": True},
                {"type": "http.request", "body": b"de", "more_body": False},
            ],
        )[0]["status"]
        == 413
    )
    result = _request(
        app,
        client,
        [
            {"type": "http.request", "body": b"ab", "more_body": True},
            {"type": "http.request", "body": b"cd", "more_body": False},
        ],
    )
    assert result[0]["status"] == 200 and result[1]["body"] == b"abcd"
