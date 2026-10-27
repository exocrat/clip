"""Opt-in loopback E2EE exercise: real marketplace SQL/SDK, fixed identities.

Not an authentication test or deployment factory. Two separate local origins
serve the normal built UI against real Listings and Conversations routes. Only
request authentication is synthetic. No identity selector, live provider,
credential input, shared target or production activation exists.
"""

import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
import os
from pathlib import Path
import secrets
import socket
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
import uvicorn

from app.contracts.domain_types import CsrfToken, SessionView
from app.core.auth import CallerContext, require_caller
from app.core.errors import ERRORS, PublicError, error_response, install_error_handlers
from app.domains.conversations.routes import (
    create_public_provider,
    router as conversations_router,
)
from app.domains.conversations.thread_creation import PostgresThreadCreationOperations
from app.domains.identity.capabilities import PostgresCapabilities
from app.domains.listings.postgres_store import PostgresListingsStore
from app.domains.listings.routes import router as listings_router
from apps.api.tests.domains.identity.postgres_fixtures import (
    disposable_identity_database,
)
from apps.api.tests.test_thread_creation import seed_users_and_listing

PORTS = (5273, 5274)
DIST = ROOT / "apps/web/dist"


def validate_environment(environment):
    """Refuse ambient targets/providers and require explicit test activation."""
    if environment.get("CLIP_ENVIRONMENT") != "test" or any(
        environment.get(name)
        for name in (
            "CLIP_DATABASE_URL",
            "CLIP_DATABASE_DSN",
            "DATABASE_URL",
            "CLIP_IDENTITY_PROVIDER",
            "CLIP_EMAIL_PROVIDER",
        )
    ):
        raise ValueError(
            "Explicit test environment with no target/provider settings required"
        )


def connection_string(connect):
    """Build private connection information from this run's owned socket only."""
    with connect() as connection:
        info = connection.info
        if info.dbname != "clip_test_identity" or not info.host.startswith("/tmp/"):
            raise ValueError("Owned disposable socket required")
        return "postgresql:///?" + urlencode(
            {
                "dbname": info.dbname,
                "host": info.host,
                "port": info.port,
                "user": info.user,
                "password": info.password,
                "connect_timeout": 3,
            }
        )


async def seed_conversation(dsn, connect):
    """Seed one valid synthetic listing; create its thread through the actual port.

    Only request authentication is doubled. Eligibility uses real Identity SQL;
    no key, plaintext message or ciphertext is preloaded into the database.
    """
    async with AsyncConnectionPool(dsn, min_size=0, max_size=1, open=False) as pool:
        owner, buyer, listing = await seed_users_and_listing(pool)
        from app.contracts.domain_types import ListingConversationContext

        capabilities = PostgresCapabilities(connect, lambda: datetime.now(UTC))
        operations = PostgresThreadCreationOperations(
            pool, capabilities.check_account_eligibility
        )
        caller = CallerContext(buyer, "regular", datetime.now(UTC) + timedelta(hours=1))
        result = await operations.open_or_create_listing_conversation(
            caller, ListingConversationContext(listing_id=listing, owner_id=owner)
        )
    return owner, buyer, listing, result.conversation_id


class _BrowserListingsIdentity:
    """Use real Identity SQL for the harness's synthetic accounts."""

    def __init__(self, capabilities):
        self._capabilities = capabilities

    async def account_is_eligible(self, user_id):
        result = await self._capabilities.check_account_eligibility(user_id)
        return result.eligible


def browser_app(dsn, connect, actor, listing_id, conversation_id, port, *, dist=DIST):
    """Test-only composition with real Listings/Conversations and fixed identities.

    IDs from HTTP never select an actor. Host, peer, Origin and CSRF checks limit
    this fixture to its two explicitly bound origins; these are not real sessions.
    """
    validate_environment(os.environ)
    if port not in PORTS:
        raise ValueError("Fixed loopback ports required")
    origin = f"http://127.0.0.1:{port}"
    caller = CallerContext(actor, "regular", datetime.now(UTC) + timedelta(hours=1))
    csrf = secrets.token_urlsafe(32)
    active = True

    @asynccontextmanager
    async def lifespan(app):
        """Give each fixed-actor app bounded domain pools; always close them."""
        async with AsyncConnectionPool(dsn, min_size=0, max_size=1, open=False) as pool:
            async with AsyncConnectionPool(
                dsn,
                kwargs={"row_factory": dict_row},
                min_size=0,
                max_size=1,
                open=False,
            ) as listings_pool:
                app.state.database_pool = pool
                app.state.listings_store = PostgresListingsStore(listings_pool, 500_000)
                app.state.listings_identity = _BrowserListingsIdentity(
                    PostgresCapabilities(connect, lambda: datetime.now(UTC))
                )
                app.state.listings_conversations = create_public_provider(pool)
                app.state.listings_image_storage = None
                try:
                    yield
                finally:
                    app.state.database_pool = None

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.fixed_actor_id = actor
    install_error_handlers(app)

    async def fixed_actor():
        """Only this process's synthetic actor; logout permanently ends this side."""
        if not active:
            raise PublicError(ERRORS[401])
        caller.require_current()
        return caller

    app.dependency_overrides[require_caller] = fixed_actor

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        """Reject foreign hosts/peers/origins before any chat or key operation."""
        try:
            local = (
                request.client is not None
                and ip_address(request.client.host).is_loopback
            )
        except ValueError:
            local = False
        if (
            not local
            or request.url.scheme != "http"
            or request.headers.get("host") != f"127.0.0.1:{port}"
            or request.headers.get("origin", origin) != origin
            or request.headers.get("sec-fetch-site") == "cross-site"
        ):
            return error_response(
                request, ERRORS[403], headers={"Cache-Control": "no-store"}
            )
        if request.method not in {"GET", "HEAD"} and (
            request.headers.get("origin") != origin
            or request.headers.get("x-clip-request") != "1"
            or not secrets.compare_digest(
                request.headers.get("x-csrf-token", "").encode("utf-8"),
                csrf.encode("ascii"),
            )
        ):
            return error_response(
                request, ERRORS[403], headers={"Cache-Control": "no-store"}
            )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    app.include_router(conversations_router, prefix="/api")
    app.include_router(listings_router, prefix="/api")

    @app.get("/api/me", response_model=SessionView)
    async def me(verified: CallerContext = Depends(require_caller)):
        """Expose the fixed synthetic summary expected by the normal UI."""
        return SessionView(
            user_id=verified.user_id,
            account_class=verified.account_class,
            valid_until=verified.valid_until,
        )

    @app.get("/api/auth/csrf", response_model=CsrfToken)
    async def token(verified: CallerContext = Depends(require_caller)):
        """In-memory fixture write token; never a real login/session credential."""
        return CsrfToken(csrf_token=csrf)

    @app.delete("/api/auth/session", status_code=204)
    async def logout(verified: CallerContext = Depends(require_caller)):
        """End this fixed side without a public re-login or identity switch route."""
        nonlocal active
        active = False
        return Response(status_code=204)

    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def website(path: str):
        """Serve the actual bundle with a prominent test-only disclosure."""
        if path.startswith("api/"):
            raise PublicError(ERRORS[404])
        html = (dist / "index.html").read_text()
        side = "A · seller" if port == PORTS[0] else "B · buyer"
        banner = (
            f'<aside role="note"><strong>LOCAL E2EE TEST — {side} — synthetic data only</strong>'
            " · Fixed test identity, not real sign-in. Actual encryption/IndexedDB and temporary Listings/Conversations SQL."
            " Use made-up messages only. "
            f'<a href="/my/conversations/{conversation_id}">Open test chat</a>'
            ' · <a href="/my/conversations">Inbox</a></aside>'
        )
        return HTMLResponse(html.replace("<body>", "<body>" + banner, 1))

    return app


def check_apps(apps, listing_id, conversation_id):
    """Smoke real Listings/Conversations SQL routes and local guards."""
    from fastapi.testclient import TestClient

    for index, (app, port) in enumerate(zip(apps, PORTS, strict=True)):
        origin = f"http://127.0.0.1:{port}"
        with TestClient(app, base_url=origin, client=("127.0.0.1", 41000)) as client:
            assert client.get("/api/me").status_code == 200
            own_listings = client.get("/api/me/listings?page=1")
            assert own_listings.status_code == 200
            if index == 0:
                item = next(
                    row
                    for row in own_listings.json()["items"]
                    if row["listing_id"] == str(listing_id)
                )
                headers = {
                    "Origin": origin,
                    "X-CLIP-Request": "1",
                    "X-CSRF-Token": client.get("/api/auth/csrf").json()["csrf_token"],
                }
                selected = client.put(
                    f"/api/listings/{listing_id}/selection",
                    headers=headers,
                    json={
                        "buyer_id": str(apps[1].state.fixed_actor_id),
                        "conversation_id": str(conversation_id),
                        "expected_revision": item["revision"],
                        "operation_id": str(uuid4()),
                    },
                )
                assert selected.status_code == 200, selected.text
                assert selected.json()["selected_buyer_id"] == str(
                    apps[1].state.fixed_actor_id
                )
                assert selected.json()["selected_conversation_id"] == str(
                    conversation_id
                )
                cleared = client.put(
                    f"/api/listings/{listing_id}/selection",
                    headers=headers,
                    json={
                        "buyer_id": None,
                        "conversation_id": None,
                        "expected_revision": selected.json()["revision"],
                        "operation_id": str(uuid4()),
                    },
                )
                assert cleared.status_code == 200, cleared.text
                assert cleared.json()["selected_buyer_id"] is None
            else:
                assert own_listings.json()["items"] == []
            assert (
                client.get(
                    "/api/conversations?view=all&page=1&page_size=100"
                ).status_code
                == 200
            )
            assert (
                client.get(f"/api/conversations/{conversation_id}").status_code == 200
            )
            assert (
                client.get(
                    f"/api/conversations/{conversation_id}/entries?after_sequence=0&page_size=100"
                ).json()["items"]
                == []
            )
            assert (
                client.get(
                    "/api/me", headers={"Origin": "https://foreign.invalid"}
                ).status_code
                == 403
            )
            assert client.put("/api/me/conversation-key", json={}).status_code == 403
            assert "LOCAL E2EE TEST" in client.get("/my/conversations").text


async def serve_apps(apps, listeners, seconds):
    """Stop both bounded servers when either ends or the time cap is reached."""
    servers = [
        uvicorn.Server(
            uvicorn.Config(app, access_log=False, log_config=None, proxy_headers=False)
        )
        for app in apps
    ]
    tasks = [
        asyncio.create_task(server.serve(sockets=[listener]))
        for server, listener in zip(servers, listeners, strict=True)
    ]
    try:
        async with asyncio.timeout(10):
            while not all(server.started for server in servers):
                if any(task.done() for task in tasks):
                    raise RuntimeError("Owned browser listener failed to start")
                await asyncio.sleep(0.05)
        for port in PORTS:
            print(
                f"LOCAL SYNTHETIC E2EE TEST READY: http://127.0.0.1:{port}/my/conversations",
                flush=True,
            )
        await asyncio.wait(tasks, timeout=seconds, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for server in servers:
            server.should_exit = True
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=15)


def main():
    """Fresh owned DB only, two fixed loopback ports, no background services."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--isolated-conversation-browser", action="store_true", required=True
    )
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--seconds", type=int, default=1800)
    args = parser.parse_args()
    listeners = []
    try:
        validate_environment(os.environ)
        if not 60 <= args.seconds <= 3600 or not (DIST / "index.html").is_file():
            raise ValueError("Build the web app first; use a 60–3600 second cap")
        if not args.check_only:
            for port in PORTS:
                listener = socket.socket()
                listeners.append(listener)
                listener.bind(("127.0.0.1", port))
                listener.listen()
        with TemporaryDirectory(
            prefix="clip-conversation-browser-", dir="/tmp"
        ) as directory:
            with disposable_identity_database(Path(directory)) as connect:
                dsn = connection_string(connect)
                owner, buyer, listing, conversation = asyncio.run(
                    seed_conversation(dsn, connect)
                )
                apps = [
                    browser_app(dsn, connect, actor, listing, conversation, port)
                    for actor, port in zip((owner, buyer), PORTS, strict=True)
                ]
                check_apps(apps, listing, conversation)
                if args.check_only:
                    print(
                        "PASS: isolated Listings/Conversations SQL, selection API and loopback guards; browser checks pending"
                    )
                else:
                    print(
                        "Real encryption; fixed fixture identities, no real sign-in. Stop with Ctrl+C.",
                        flush=True,
                    )
                    asyncio.run(serve_apps(apps, listeners, args.seconds))
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        print(
            "Local browser setup failed; details withheld. Check build, ports and local Docker.",
            file=sys.stderr,
        )
        return 1
    finally:
        for listener in listeners:
            listener.close()


if __name__ == "__main__":
    raise SystemExit(main())
