"""Run the normal app on loopback with disposable SQL and synthetic providers.

The launcher and its actor switch never enter the production application. All
marketplace mutations use the normal authenticated HTTP routes. Local signed
Microsoft assertions and local photo storage replace external provider calls.
Ctrl+C removes only this launcher's disposable database and temporary files.
"""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import html
import json
import os
from pathlib import Path
import secrets
import sys
from tempfile import TemporaryDirectory
from urllib.parse import quote, urlencode
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.testclient import TestClient
import httpx2 as httpx
from pydantic import SecretStr
import uvicorn
from app.application import create_app
from app.core.config import Settings
from app.domains.identity.http import BrowserPolicy, IdentityHttpDependencies
from app.domains.identity.sessions import IdentitySessions
from app.domains.identity.temporary_crypto import TemporaryKeys
from app.domains.listings.embedding_bootstrap import EmbeddingBootstrap
from apps.api.tests.domains.identity.microsoft_fixtures import SignedTokens
from apps.api.tests.domains.identity.postgres_fixtures import (
    disposable_identity_database,
)
from apps.api.tests.domains.identity.session_fixtures import CaptureMail
from apps.api.tests.domains.listings.browser_image_preview import install_image_preview

ORIGIN = "http://127.0.0.1:5174"
HEADERS = {"Origin": ORIGIN, "X-CLIP-Request": "1"}
ACTORS = ("seller", "buyer", "other-seller", "other-buyer", "new-member")
PAGINATION_ACTORS = tuple(f"pagination-{number:02d}" for number in range(1, 23))
TEMP_EMAIL = "inspection-newcomer@example.com"
TEMP_PASSWORD = "synthetic-inspection-passphrase"


def make_app(connect):
    """Compose actual session/domain services; keep provider replacements explicit."""
    clock = lambda: datetime.now(UTC)
    signer = SignedTokens(
        clock, rsa.generate_private_key(public_exponent=65537, key_size=2048)
    )
    mail = CaptureMail()
    sessions = IdentitySessions(
        connect,
        TemporaryKeys("inspection", *(secrets.token_bytes(32) for _ in range(3))),
        clock,
    )
    with connect() as connection:
        info = connection.info
        dsn = (
            "postgresql:///"
            + quote(info.dbname)
            + "?"
            + urlencode(
                {
                    "host": info.host,
                    "port": info.port,
                    "user": info.user,
                    "password": info.password,
                    "sslmode": "disable",
                }
            )
        )
    settings = Settings(
        environment="test",
        database_url=SecretStr(dsn),
        database_dsn=SecretStr(dsn),
        storage_provider="disabled",
        serve_web_app=False,
        development_auth=False,
        isolated_listings_test_caller=False,
        debug=False,
        hybrid_search_enabled=True,
        hybrid_worker_enabled=True,
        hybrid_search_interpreter=ROOT / ".tools/semantic/venv/bin/python",
        hybrid_search_model_dir=ROOT / ".tools/semantic/model",
    )
    inner = create_app(
        settings,
        identity=IdentityHttpDependencies(
            sessions,
            BrowserPolicy((ORIGIN,), development=True),
            mail,
            signer.validator(),
            clock,
        ),
    )

    @asynccontextmanager
    async def lifespan(outer):
        async with inner.router.lifespan_context(inner):
            inner.state.listings_image_storage = outer.state.listings_image_storage
            search = inner.state.search_runtime
            if search.state != "ready":
                raise RuntimeError("Real Hybrid search is unavailable")
            async with search.pool.connection() as connection:
                bootstrap = EmbeddingBootstrap(connection)
                await bootstrap.prepare()
                while await bootstrap.queue(1000) == 1000:
                    pass
                await bootstrap.activate()
            yield

    outer = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    outer.state.records = {}
    # Reuse the existing bounded, byte-inspecting photo adapter and real SPA build.
    install_image_preview(
        outer,
        Settings(environment="test", development_auth=True),
        ROOT / "apps/web/dist",
        notice_html='<aside style="padding:12px;background:#fef3c7">Synthetic inspection environment · <a href="/__inspection">Switch test account / records</a></aside>',
    )
    outer.mount("/api", inner)

    @outer.middleware("http")
    async def loopback_only(request, call_next):
        """Keep synthetic account issuance and photos private to this computer."""
        if (
            request.client is None
            or request.client.host not in {"127.0.0.1", "::1"}
            or request.url.hostname not in {"127.0.0.1", "localhost"}
            or request.headers.get("origin") not in {None, ORIGIN}
            or (
                request.method not in {"GET", "HEAD"}
                and request.headers.get("origin") != ORIGIN
            )
        ):
            return Response(status_code=403)
        return await call_next(request)

    @outer.post("/__inspection/login/{actor}")
    async def switch_actor(actor: str):
        """Exchange a fresh synthetic signed assertion through real Identity routes."""
        if actor not in ACTORS + PAGINATION_ACTORS + ("temporary",):
            raise HTTPException(404)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=inner, client=("127.0.0.1", 41000)),
            base_url=ORIGIN,
            headers=HEADERS,
        ) as client:
            if actor == "temporary":
                logged = await client.post(
                    "/auth/temporary/sessions",
                    json={"email": TEMP_EMAIL, "password": TEMP_PASSWORD},
                )
                logged.raise_for_status()
                response = RedirectResponse("/", status_code=303)
                for value in logged.headers.get_list("set-cookie"):
                    response.headers.append("set-cookie", value)
                return response
            attempt = await client.post("/auth/microsoft/login-attempts")
            attempt.raise_for_status()
            token = signer.token(
                {
                    "nonce": attempt.json()["nonce"],
                    "sub": "inspection-" + actor,
                    "email": "inspection-" + actor + "@iisc.ac.in",
                }
            )
            logged = await client.post(
                "/auth/microsoft/sessions", json={"id_token": token}
            )
            logged.raise_for_status()
            response = RedirectResponse("/", status_code=303)
            for value in logged.headers.get_list("set-cookie"):
                response.headers.append("set-cookie", value)
            return response

    @outer.get("/__inspection/files/{name}")
    async def fixture_file(name: str):
        """Download only the explicitly generated synthetic photo fixtures."""
        allowed = {
            "inspection-photo.png",
            "progress-photo.png",
            "invalid-photo.txt",
        } | {f"photo-{number}.png" for number in range(1, 10)}
        directory = getattr(outer.state, "fixture_directory", None)
        if name not in allowed or directory is None:
            raise HTTPException(404)
        return FileResponse(
            directory / name, filename=name, headers={"Cache-Control": "no-store"}
        )

    @outer.get("/__inspection", response_class=HTMLResponse)
    async def guide():
        """Actor switching is a clearly separate test control, never a product login."""
        forms = "".join(
            f'<form method="post" action="/__inspection/login/{actor}"><button>Use {actor}</button></form>'
            for actor in ACTORS + ("temporary",)
        )
        links = (
            "<h2>Prepared listings</h2><ul>"
            + "".join(
                f'<li><a href="/listings/{row["id"]}">{html.escape(row["title"])}</a> — {row["owner"]}</li>'
                for row in outer.state.records.get("listings", [])[:6]
            )
            + "</ul>"
        )
        links += (
            "<h2>Prepared conversations</h2><ul>"
            + "".join(
                f'<li><a href="/my/conversations/{row["id"]}">{row["id"][:8]} — {row["buyer"]}</a></li>'
                for row in (
                    outer.state.records.get("conversations", [])[:3]
                    + [
                        row
                        for row in outer.state.records.get("conversations", [])
                        if row["buyer"] == "other-buyer" or "wanted" in row
                    ][:2]
                )
            )
            + "</ul>"
        )
        return HTMLResponse(
            "<h1>Campus Marketplace inspection</h1><p>Synthetic data, real local app routes and SQL. External Microsoft/email/S3 are controlled test providers. Use separate browser profiles for simultaneous encrypted chat.</p>"
            + forms
            + links
            + '<h2>Download sample files</h2><p><a href="/__inspection/files/inspection-photo.png">Small photo</a> · <a href="/__inspection/files/progress-photo.png">Large progress photo</a> · <a href="/__inspection/files/invalid-photo.txt">Invalid photo</a></p><p>'
            + " ".join(
                f'<a href="/__inspection/files/photo-{number}.png">Photo {number}</a>'
                for number in range(1, 10)
            )
            + "</p>"
            + '<p><a href="/">Discover</a> · <a href="/my/listings">My Listings</a> · <a href="/my/conversations">Conversations</a> · <a href="/account/contacts">Account</a></p><details><summary>All synthetic record IDs and sample-photo path</summary><pre>'
            + html.escape(json.dumps(outer.state.records, indent=2))
            + "</pre></details>"
        )

    async def spa():
        """Serve the normal compiled product at the remaining approved SPA routes."""
        return HTMLResponse(
            (ROOT / "apps/web/dist/index.html")
            .read_text()
            .replace(
                "<body>",
                '<body><aside style="padding:12px;background:#fef3c7">Synthetic inspection environment · <a href="/__inspection">Switch test account / records</a></aside>',
            )
        )

    for route in (
        "/my/conversations",
        "/my/conversations/{conversation_id}",
        "/account/contacts",
        "/sign-in",
        "/auth/callback",
    ):
        outer.add_api_route(route, spa, methods=["GET"])
    outer.state.inner = inner
    outer.state.signer = signer
    outer.state.mail = mail
    return outer


def inspection_photo(large: bool = False):
    """Generate a deterministic valid PNG diagram for repeatable photo checks."""
    import struct
    import zlib

    width, height = (1024, 768) if large else (360, 220)
    rows = []
    import random

    noise = random.Random(42)
    for y in range(height):
        if large:
            rows.append(b"\0" + noise.randbytes(width * 3))
            continue
        row = bytearray()
        for x in range(width):
            wheel = any(
                abs((x - cx) ** 2 + (y - 150) ** 2 - 35**2) < 160 for cx in (85, 270)
            )
            frame = (
                (95 < x < 260 and abs(y - (190 - x / 3)) < 4)
                or (125 < x < 220 and abs(y - (x - 35)) < 4)
                or (125 < x < 220 and abs(y - 90) < 4)
            )
            row.extend(
                (25, 65, 100) if wheel else (38, 150, 100) if frame else (230, 242, 250)
            )
        rows.append(b"\0" + row)

    def chunk(kind, body):
        """Pack a length-delimited PNG chunk with its required integrity checksum."""
        return (
            struct.pack(">I", len(body))
            + kind
            + body
            + struct.pack(">I", zlib.crc32(kind + body))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )


def exercise_and_seed(app):
    """Create inspection fixtures through normal HTTP and assert cross-domain results.

    Cookies and synthetic provider material stay in memory. The emitted report
    contains only synthetic record IDs/titles, check names and counts.
    """
    checks = []
    actors = {}
    records = {"listings": [], "wanted": [], "conversations": []}
    png = inspection_photo()
    with TestClient(
        app,
        base_url=ORIGIN,
        client=("127.0.0.1", 41000),
        headers=HEADERS,
        follow_redirects=False,
    ) as c:

        def expect(method, path, status=200, **kwargs):
            """Assert the reviewed HTTP status; parse JSON only for body responses."""
            r = c.request(method, path, **kwargs)
            if r.status_code != status:
                raise AssertionError(
                    f"{method} {path}: expected {status}, got {r.status_code}: {r.text[:400]}"
                )
            return r.json() if r.content else None

        def use(actor):
            """Restore an isolated browser cookie jar and fetch its current CSRF proof."""
            c.cookies.clear()
            c.cookies.update(actors[actor]["cookies"])
            csrf = expect("GET", "/api/auth/csrf")["csrf_token"]
            c.headers["X-CSRF-Token"] = csrf

        def upload():
            """Exercise actual bounded byte upload, metadata inspection and confirmation retry."""
            intent = expect(
                "POST",
                "/api/image-uploads",
                201,
                json={
                    "media_type": "image/png",
                    "size_bytes": len(png),
                    "operation_id": str(uuid4()),
                },
            )
            expect(
                "PUT",
                intent["upload_url"],
                204,
                content=png,
                headers=intent["required_headers"],
            )
            result = expect(
                "POST", "/api/image-uploads/" + intent["upload_id"] + "/confirm"
            )
            assert (
                expect("POST", "/api/image-uploads/" + intent["upload_id"] + "/confirm")
                == result
            )
            return intent["upload_id"]

        assert c.get("/api/me").status_code == 401
        checks.append("anonymous protected-route denial")
        for actor in ACTORS:
            c.cookies.clear()
            c.headers.pop("X-CSRF-Token", None)
            expect("POST", "/__inspection/login/" + actor, 303)
            c.headers["X-CSRF-Token"] = expect("GET", "/api/auth/csrf")["csrf_token"]
            if actor != "new-member":
                expect(
                    "PATCH",
                    "/api/me/profile",
                    json={"display_name": "inspection_" + actor.replace("-", "_")},
                )
            user = expect("GET", "/api/me")
            actors[actor] = {"cookies": httpx.Cookies(c.cookies), "user": user}
        use("seller")
        catalogue = expect("GET", "/api/catalogue")
        categories = [x["code"] for x in catalogue["categories"]]
        conditions = [x["code"] for x in catalogue["conditions"]]
        for index in range(28):
            use("other-seller" if index % 3 == 2 else "seller")
            category = (
                "bicycles"
                if index == 0
                else (
                    next(
                        x["code"]
                        for x in catalogue["categories"]
                        if "appliance" in x["label"].lower()
                    )
                    if index == 1
                    else categories[index % len(categories)]
                )
            )
            title = (
                "Inspection campus bicycle"
                if index == 0
                else (
                    "Inspection electric kettle"
                    if index == 1
                    else f"Inspection market item {index:02d}"
                )
            )
            item = expect(
                "POST",
                "/api/listings",
                201,
                json={
                    "title": title,
                    "description": "Synthetic inspection fixture. "
                    + (
                        "Pedal bicycle with two wheels for riding around campus."
                        if index == 0
                        else "Useful campus item for the visual walkthrough."
                    ),
                    "category_code": category,
                    "condition_code": conditions[index % len(conditions)],
                    "asking_price_paise": (index + 1) * 10000,
                    "original_price_paise": (
                        (index + 2) * 15000 if index % 2 == 0 else None
                    ),
                    "negotiable": index % 2 == 0,
                    "image_upload_ids": [upload()],
                    "operation_id": str(uuid4()),
                },
            )
            records["listings"].append(
                {
                    "id": item["listing_id"],
                    "title": title,
                    "owner": "other-seller" if index % 3 == 2 else "seller",
                    "category": category,
                    "condition": conditions[index % len(conditions)],
                }
            )
        use("buyer")
        buyer_listing_title = "Inspection buyer-owned desk lamp"
        buyer_listing = expect(
            "POST",
            "/api/listings",
            201,
            json={
                "title": buyer_listing_title,
                "description": "Synthetic item owned by the inspection buyer for My Listings visual review.",
                "category_code": categories[0],
                "condition_code": conditions[1 % len(conditions)],
                "asking_price_paise": 45000,
                "original_price_paise": 90000,
                "negotiable": True,
                "image_upload_ids": [upload()],
                "operation_id": str(uuid4()),
            },
        )
        records["listings"].append(
            {
                "id": buyer_listing["listing_id"],
                "title": buyer_listing_title,
                "owner": "buyer",
                "category": categories[0],
                "condition": conditions[1 % len(conditions)],
            }
        )
        checks.append(
            "29 photo-backed listings: upload bytes, confirm/retry and publish, including a buyer-owned listing"
        )
        use("seller")
        bike = records["listings"][0]["id"]
        detail = expect("GET", "/api/listings/" + bike)
        delivery = expect("GET", "/api/images/" + detail["image_ids"][0] + "/delivery")
        assert c.get(delivery["url"]).content == png
        checks.append("authorized photo delivery returns uploaded bytes")
        absent_photo = str(uuid4())
        batch = c.get(
            "/api/images/delivery",
            params=[
                ("image_ids", detail["image_ids"][0]),
                ("image_ids", absent_photo),
            ],
        )
        assert batch.status_code == 200
        # Real Identity middleware may replace the route's private/no-store with
        # no-store; both forbid browser and shared-cache retention of signed links.
        assert "no-store" in {
            token.strip().lower() for token in batch.headers["cache-control"].split(",")
        }
        assert batch.json()["items"][1] == {"image_id": absent_photo, "delivery": None}
        assert c.get(batch.json()["items"][0]["delivery"]["url"]).content == png
        checks.append(
            "batch photo HTTP/SQL/signing preserves missing-ID isolation and private cache policy"
        )
        for index in range(25):
            use("other-seller" if index % 2 else "seller")
            title = (
                "Inspection bicycle wanted"
                if index == 0
                else f"Inspection wanted item {index:02d}"
            )
            item = expect(
                "POST",
                "/api/wanted-requests",
                201,
                json={
                    "title": title,
                    "description": (
                        "Synthetic campus bicycle request"
                        if index == 0
                        else "Synthetic physics textbook campus request"
                    ),
                    "category_code": (
                        "bicycles"
                        if index == 0
                        else categories[index % len(categories)]
                    ),
                    "budget_paise": None if index % 3 == 0 else index * 10000,
                    "operation_id": str(uuid4()),
                },
            )
            records["wanted"].append({"id": item["request_id"], "title": title})
        checks.append("25 Wanted requests with present, zero and absent budgets")
        use("buyer")
        for index in range(28):
            listing = records["listings"][index]["id"]
            chat = expect(
                "POST",
                f"/api/listings/{listing}/conversations",
                201,
                json={"operation_id": str(uuid4())},
            )
            records["conversations"].append(
                {"id": chat["conversation_id"], "listing": listing, "buyer": "buyer"}
            )
        use("other-buyer")
        chat = expect(
            "POST",
            f"/api/listings/{bike}/conversations",
            201,
            json={"operation_id": str(uuid4())},
        )
        records["conversations"].append(
            {"id": chat["conversation_id"], "listing": bike, "buyer": "other-buyer"}
        )
        use("buyer")
        wanted = records["wanted"][0]["id"]
        chat = expect(
            "POST",
            f"/api/wanted-requests/{wanted}/conversations",
            201,
            json={"operation_id": str(uuid4())},
        )
        records["conversations"].append(
            {"id": chat["conversation_id"], "wanted": wanted, "buyer": "buyer"}
        )
        for request in records["wanted"][1:]:
            chat = expect(
                "POST",
                f"/api/wanted-requests/{request['id']}/conversations",
                201,
                json={"operation_id": str(uuid4())},
            )
            records["conversations"].append(
                {
                    "id": chat["conversation_id"],
                    "wanted": request["id"],
                    "buyer": "buyer",
                }
            )
        buyer_wanted_title = "Inspection buyer wants a lab coat"
        buyer_wanted = expect(
            "POST",
            "/api/wanted-requests",
            201,
            json={
                "title": buyer_wanted_title,
                "description": "Synthetic buyer-owned request for My Wanted Requests visual review.",
                "category_code": categories[1 % len(categories)],
                "budget_paise": 125000,
                "operation_id": str(uuid4()),
            },
        )
        records["wanted"].append(
            {
                "id": buyer_wanted["request_id"],
                "title": buyer_wanted_title,
                "owner": "buyer",
            }
        )
        checks.append("buyer-owned Wanted Request appears in My Wanted Requests")
        assert expect("GET", "/api/conversations?page_size=20")["has_next"]
        assert expect("GET", "/api/conversations?page=2&page_size=20")["items"]
        checks.append("conversation pagination over sale and Wanted origins")
        first_chat = records["conversations"][0]["id"]
        offer_path = f"/api/listings/{bike}/conversations/{first_chat}"
        offered = expect(
            "PUT",
            offer_path + "/offer",
            json={"amount_paise": 5000, "operation_id": str(uuid4())},
        )
        assert (
            expect("GET", f"/api/conversations/{first_chat}/offer")["amount_paise"]
            == 5000
        )
        withdrawn = expect(
            "POST",
            offer_path + "/offer-withdrawals",
            json={
                "offer_id": offered["offer_id"],
                "expected_revision": offered["revision"],
                "operation_id": str(uuid4()),
            },
        )
        expect(
            "PUT",
            offer_path + "/offer",
            json={
                "amount_paise": 6000,
                "expected_revision": withdrawn["revision"],
                "operation_id": str(uuid4()),
            },
        )
        checks.append(
            "sale/Wanted conversation starts; offer submit/read/withdraw/resubmit"
        )
        expect(
            "PUT", f"/api/me/saved-listings/{bike}", json={"operation_id": str(uuid4())}
        )
        assert expect("GET", "/api/me/saved-listings")["items"]
        statuses = expect(
            "GET",
            "/api/me/saved-listings/status",
            params=[
                ("listing_ids", bike),
                ("listing_ids", str(uuid4())),
            ],
        )["items"]
        assert statuses[0] == {"listing_id": bike, "saved": True}
        assert statuses[1]["saved"] is False
        checks.append(
            "batch saved HTTP/SQL returns only caller membership without listing content"
        )
        expect("DELETE", f"/api/me/saved-listings/{bike}", 204)
        expect("DELETE", f"/api/me/saved-listings/{bike}", 204)
        checks.append("saved listing add/read/remove/idempotent retry")
        use("seller")
        inbox = expect("GET", "/api/conversations?view=origin_owner&origin_id=" + bike)
        assert len(inbox["items"]) == 2
        filtered = expect(
            "GET",
            "/api/conversations?origin_id="
            + bike
            + "&origin_id="
            + records["listings"][1]["id"]
            + "&counterparty_user_id="
            + actors["buyer"]["user"]["user_id"],
        )
        assert len(filtered["items"]) == 2
        checks.append("inbox seller view, multiple origins OR and partner AND")
        owned = expect("GET", "/api/me/listings")["items"]
        row = next(x for x in owned if x["listing_id"] == bike)
        selected = expect(
            "PUT",
            f"/api/listings/{bike}/selection",
            json={
                "buyer_id": actors["buyer"]["user"]["user_id"],
                "conversation_id": first_chat,
                "expected_revision": row["revision"],
                "operation_id": str(uuid4()),
            },
        )
        assert selected["availability"] == "available"
        expect(
            "PUT",
            f"/api/listings/{bike}/availability",
            json={
                "availability": "available",
                "expected_revision": selected["revision"],
                "operation_id": str(uuid4()),
            },
        )
        current = next(
            x
            for x in expect("GET", "/api/me/listings")["items"]
            if x["listing_id"] == bike
        )
        expect(
            "PUT",
            f"/api/listings/{bike}/selection",
            json={
                "buyer_id": None,
                "conversation_id": None,
                "expected_revision": current["revision"],
                "operation_id": str(uuid4()),
            },
        )

        # Private tracking remains usable after closing; it must not reopen or
        # close anything, and the pair can be cleared without changing state.
        def owner_bike():
            """Read the current owner revision through its real authorized API."""
            return next(
                x
                for x in expect("GET", "/api/me/listings")["items"]
                if x["listing_id"] == bike
            )

        expect(
            "PUT",
            f"/api/listings/{bike}/availability",
            json={
                "availability": "unavailable",
                "expected_revision": owner_bike()["revision"],
                "operation_id": str(uuid4()),
            },
        )
        tracked = expect(
            "PUT",
            f"/api/listings/{bike}/selection",
            json={
                "buyer_id": actors["buyer"]["user"]["user_id"],
                "conversation_id": first_chat,
                "expected_revision": owner_bike()["revision"],
                "operation_id": str(uuid4()),
            },
        )
        assert tracked["availability"] == "unavailable"
        cleared = expect(
            "PUT",
            f"/api/listings/{bike}/selection",
            json={
                "buyer_id": None,
                "conversation_id": None,
                "expected_revision": tracked["revision"],
                "operation_id": str(uuid4()),
            },
        )
        assert cleared["availability"] == "unavailable"
        expect(
            "PUT",
            f"/api/listings/{bike}/availability",
            json={
                "availability": "available",
                "expected_revision": cleared["revision"],
                "operation_id": str(uuid4()),
            },
        )
        checks.append("real cross-domain seller buyer selection and reopen")
        # Leave another owned listing unavailable for retained-history inspection.
        row = next(
            x
            for x in expect("GET", "/api/me/listings")["items"]
            if x["listing_id"] == records["listings"][3]["id"]
        )
        expect(
            "PUT",
            f'/api/listings/{row["listing_id"]}/availability',
            json={
                "availability": "unavailable",
                "expected_revision": row["revision"],
                "operation_id": str(uuid4()),
            },
        )
        checks.append("done-deal availability command and owner history")
        # Wait for actual asynchronous vectors, then query the normal Hybrid API.
        import time

        async def current_vectors():
            """Read real vector coverage on the application's own running event loop."""
            async with (
                app.state.inner.state.search_runtime.pool.connection() as connection
            ):
                return await EmbeddingBootstrap(connection).status()

        def wait_vectors():
            """Require current real generations, rather than relying on lexical fallback."""
            for _ in range(120):
                coverage = c.portal.call(current_vectors)
                if coverage.complete:
                    assert coverage.ready == 29 and coverage.failed == 0
                    return
                time.sleep(0.25)
            raise AssertionError("Actual Hybrid generations did not become current")

        wait_vectors()
        for query in ("Inspection campus bicycle", "wheeled vehicle"):
            for attempt in range(60):
                page = expect(
                    "GET",
                    "/api/listings",
                    params={"q": query, "sort": "relevance", "search_mode": "hybrid"},
                )
                if any(x["listing_id"] == bike for x in page["items"]):
                    break
                time.sleep(0.5)
            else:
                raise AssertionError(
                    "Hybrid bicycle query returned no bicycle: " + query
                )
        assert expect("GET", "/api/listings?q=zzzxqnevermatchzzzxq")["items"] == []
        assert (
            expect("GET", "/api/wanted-requests?q=zzzxqnevermatchzzzxq")["items"] == []
        )
        assert expect("GET", "/api/listings?page_size=20")["has_next"]
        assert expect("GET", "/api/wanted-requests?page_size=20")["has_next"]
        checks.append("real Hybrid exact/semantic search; no-match and pagination")
        owned_row = next(
            x
            for x in expect("GET", "/api/me/listings")["items"]
            if x["listing_id"] == bike
        )
        old_photo = owned_row["image_ids"][0]
        edit = {
            key: owned_row[key]
            for key in (
                "title",
                "description",
                "category_code",
                "condition_code",
                "asking_price_paise",
                "original_price_paise",
                "negotiable",
                "pickup_area",
                "available_from",
                "available_until",
                "proof_available",
            )
        }
        edit.update(
            expected_revision=owned_row["revision"],
            operation_id=str(uuid4()),
            images=[
                {"source": "upload", "upload_id": upload()},
                {"source": "existing", "image_id": old_photo},
            ],
        )
        edited = expect("PUT", f"/api/listings/{bike}", json=edit)
        edit.update(
            expected_revision=next(
                x
                for x in expect("GET", "/api/me/listings")["items"]
                if x["listing_id"] == bike
            )["revision"],
            operation_id=str(uuid4()),
            images=[{"source": "existing", "image_id": edited["image_ids"][0]}],
        )
        edited = expect("PUT", f"/api/listings/{bike}", json=edit)
        assert c.get(f"/api/images/{old_photo}/delivery").status_code == 404
        removed_batch = expect(
            "GET", "/api/images/delivery", params={"image_ids": old_photo}
        )
        assert removed_batch["items"] == [{"image_id": old_photo, "delivery": None}]
        assert edited["original_price_paise"] == owned_row["original_price_paise"]
        checks.append(
            "listing edit/photo replacement/removal revokes old delivery; Original price persists"
        )
        request_id = records["wanted"][0]["id"]
        mine = next(
            x
            for x in expect("GET", "/api/me/wanted-requests")["items"]
            if x["request_id"] == request_id
        )
        changed = expect(
            "PATCH",
            f"/api/wanted-requests/{request_id}",
            json={
                "expected_revision": mine["revision"],
                "operation_id": str(uuid4()),
                "budget_paise": 0,
            },
        )
        hidden = expect(
            "PUT",
            f"/api/wanted-requests/{request_id}/availability",
            json={
                "expected_revision": changed["revision"],
                "operation_id": str(uuid4()),
                "state": "unavailable",
            },
        )
        use("buyer")
        assert c.get(f"/api/wanted-requests/{request_id}").status_code == 404
        use("seller")
        expect(
            "PUT",
            f"/api/wanted-requests/{request_id}/availability",
            json={
                "expected_revision": hidden["revision"],
                "operation_id": str(uuid4()),
                "state": "open",
            },
        )
        checks.append("Wanted edit, zero budget, hide with owner history and reopen")
        query = [
            ("category_code", categories[0]),
            ("category_code", categories[1]),
            ("condition_code", conditions[0]),
            ("condition_code", conditions[1]),
            ("min_price_paise", "10000"),
            ("max_price_paise", "280000"),
            ("sort", "price_asc"),
        ]
        page = expect("GET", "/api/listings", params=query)
        assert page["items"]
        assert all(
            x["category_code"] in categories[:2]
            and x["condition_code"] in conditions[:2]
            and 10000 <= x["asking_price_paise"] <= 280000
            for x in page["items"]
        )
        amounts = [x["asking_price_paise"] for x in page["items"]]
        assert amounts == sorted(amounts)
        descending = expect("GET", "/api/listings?sort=price_desc")["items"]
        assert [x["asking_price_paise"] for x in descending] == sorted(
            (x["asking_price_paise"] for x in descending), reverse=True
        )
        all_rows = expect("GET", "/api/listings?page_size=100")["items"]
        assert len(all_rows) == 28
        assert len({x["listing_id"] for x in all_rows}) == 28
        checks.append(
            "sale OR category/condition, AND groups and inclusive prices; both price sorts and cleared filters"
        )
        # Exercise cancellable/missing-object upload states without fake metadata.
        intent = expect(
            "POST",
            "/api/image-uploads",
            201,
            json={
                "media_type": "image/png",
                "size_bytes": len(png),
                "operation_id": str(uuid4()),
            },
        )
        assert (
            c.post("/api/image-uploads/" + intent["upload_id"] + "/confirm").status_code
            == 404
        )
        expect("DELETE", "/api/image-uploads/" + intent["upload_id"], 204)
        expect("DELETE", "/api/image-uploads/" + intent["upload_id"], 204)
        checks.append("missing photo confirmation and cancel/retry")
        expect("PATCH", "/api/me/profile", json={"display_name": "inspection_seller"})
        expect(
            "PUT",
            "/api/me/contacts/email",
            204,
            json={"value": "inspection-seller@example.com"},
        )
        expect("PUT", "/api/me/contacts/phone", 204, json={"value": "+919876543210"})
        assert (
            expect("GET", "/api/me/contacts")["email"]
            == "inspection-seller@example.com"
        )
        expect("DELETE", "/api/me/contacts/phone", 204)
        checks.append("profile/contact edit/read/delete")
        positive = expect(
            "POST",
            "/api/wanted-requests/draft-matches",
            json={"draft_title": "Inspection campus bicycle"},
        )
        assert positive["items"]
        negative = expect(
            "POST",
            "/api/wanted-requests/draft-matches",
            json={"draft_title": "zzzxqnevermatchzzzxq"},
        )
        assert not negative["items"]
        checks.append("positive and negative transient Wanted matches")
        assert (
            c.get("/api/listings?search_mode=unsupported&q=bicycle").status_code == 422
        )
        bounded = expect(
            "GET", "/api/wanted-requests?min_budget_paise=10000&max_budget_paise=10000"
        )
        assert all(x["budget_paise"] == 10000 for x in bounded["items"])
        categories_query = [
            ("category_code", categories[0]),
            ("category_code", categories[1]),
        ]
        page = expect("GET", "/api/wanted-requests", params=categories_query)
        assert all(x["category_code"] in categories[:2] for x in page["items"])
        checks.append(
            "inclusive Wanted budget and multi-category OR; invalid sale mode"
        )
        wait_vectors()
        checks.append(
            "all 29 real Hybrid generations current, including buyer-owned item and edited bicycle"
        )
        expect("DELETE", "/api/auth/session", 204)
        assert c.get("/api/me").status_code == 401
        checks.append("logout invalidates session")
        # Actual OTP/account/session routes with a transient synthetic mailbox.
        requested = expect(
            "POST",
            "/api/auth/temporary/registration-challenges",
            202,
            json={"email": TEMP_EMAIL, "operation_id": str(uuid4())},
        )
        newcomer = expect(
            "POST",
            "/api/auth/temporary/accounts",
            201,
            json={
                "challenge_id": requested["challenge_id"],
                "code": app.state.mail.code(),
                "password": TEMP_PASSWORD,
            },
        )
        c.headers["X-CSRF-Token"] = expect("GET", "/api/auth/csrf")["csrf_token"]
        expect(
            "PATCH", "/api/me/profile", json={"display_name": "inspection_temporary"}
        )
        newcomer = expect("GET", "/api/me")
        assert newcomer["account_class"] == "temporary"
        actors["temporary"] = {"cookies": httpx.Cookies(c.cookies), "user": newcomer}
        use("temporary")
        assert (
            c.post(
                "/api/image-uploads",
                json={
                    "media_type": "image/png",
                    "size_bytes": len(png),
                    "operation_id": str(uuid4()),
                },
            ).status_code
            == 403
        )
        assert (
            c.post(
                f"/api/wanted-requests/{records['wanted'][0]['id']}/conversations",
                json={"operation_id": str(uuid4())},
            ).status_code
            == 403
        )
        newcomer_wanted = expect(
            "POST",
            "/api/wanted-requests",
            201,
            json={
                "title": "Inspection newcomer needs a bicycle",
                "description": "Synthetic temporary-account Wanted Request",
                "category_code": "bicycles",
                "operation_id": str(uuid4()),
            },
        )
        expect("DELETE", "/api/auth/session", 204)
        expect(
            "POST",
            "/api/auth/temporary/sessions",
            json={"email": TEMP_EMAIL, "password": TEMP_PASSWORD},
        )
        assert expect("GET", "/api/me")["account_class"] == "temporary"
        checks.append(
            "temporary OTP activation/login/logout; Wanted allowed, sale/respond denied"
        )
        # Earlier logout assertions intentionally revoke the stored sessions.
        # Issue fresh real sessions before exercising the new feedback features.
        for actor in ACTORS + ("temporary",):
            c.cookies.clear()
            c.headers.pop("X-CSRF-Token", None)
            expect("POST", "/__inspection/login/" + actor, 303)
            actors[actor]["cookies"] = httpx.Cookies(c.cookies)
            actors[actor]["user"] = expect("GET", "/api/me")
        use("buyer")
        expect(
            "PATCH", "/api/me/profile", 409, json={"display_name": "INSPECTION_SELLER"}
        )
        expect("PATCH", "/api/me/profile", 422, json={"display_name": "bad handle"})
        expect("PATCH", "/api/me/profile", json={"display_name": "inspection_buyer"})
        assert expect("GET", "/api/me")["handle_ready"] is True
        newcomer_thread = expect(
            "POST",
            f"/api/wanted-requests/{newcomer_wanted['request_id']}/conversations",
            201,
            json={"operation_id": str(uuid4())},
        )
        peer = expect("GET", f"/api/conversations/{newcomer_thread['conversation_id']}")
        assert (
            peer["counterparty_handle"] == "inspection_temporary"
            and peer["counterparty_account_class"] == "temporary"
        )
        records["conversations"].append(
            {
                "id": newcomer_thread["conversation_id"],
                "buyer": "buyer",
                "wanted": newcomer_wanted["request_id"],
                "label": "Temporary requester conversation",
            }
        )
        records["wanted"].append(
            {
                "id": newcomer_wanted["request_id"],
                "title": "Inspection newcomer needs a bicycle",
            }
        )
        use("buyer")
        for listing_record in records["listings"]:
            if listing_record["owner"] == "buyer":
                continue
            read = c.get(f"/api/listings/{listing_record['id']}")
            assert read.status_code in (200, 404)
            if (
                read.status_code == 404
            ):  # Deliberate retirement fixture from the earlier sweep.
                continue
            listing = read.json()
            if listing["availability"] == "available":
                response = c.post(
                    f"/api/listings/{listing_record['id']}/conversations",
                    json={"operation_id": str(uuid4())},
                )
                assert response.status_code in (200, 201)
        # Extra accounts exist solely to exercise the visible within-group pager.
        # They have safe Handles but no browser keys; use the named main actors
        # for interactive encrypted messaging, and these rows for paging/setup states.
        for actor in PAGINATION_ACTORS:
            c.cookies.clear()
            c.headers.pop("X-CSRF-Token", None)
            expect("POST", "/__inspection/login/" + actor, 303)
            c.headers["X-CSRF-Token"] = expect("GET", "/api/auth/csrf")["csrf_token"]
            expect(
                "PATCH",
                "/api/me/profile",
                json={"display_name": actor.replace("-", "_")},
            )
            thread = expect(
                "POST",
                f"/api/listings/{bike}/conversations",
                201,
                json={"operation_id": str(uuid4())},
            )
            records["conversations"].append(
                {"id": thread["conversation_id"], "listing": bike, "buyer": actor}
            )
        use("seller")
        group_page = expect("GET", "/api/conversations?group_by=item&page_size=20")
        bicycle_group = [
            item for item in group_page["items"] if item["origin_id"] == bike
        ]
        assert len(bicycle_group) == 20 and all(
            item["group_has_more"] for item in bicycle_group
        )
        more = expect("GET", f"/api/conversations?origin_id={bike}&page=2")
        assert len(more["items"]) == 4 and not more["has_next"]
        if group_page["has_next"]:
            next_page = expect(
                "GET", "/api/conversations?group_by=item&page_size=20&page=2"
            )
            assert {item["origin_id"] for item in group_page["items"]}.isdisjoint(
                {item["origin_id"] for item in next_page["items"]}
            )
        for actor in ACTORS + ("temporary",):
            use(actor)
            total = expect("GET", "/api/conversations/unread-count")["unread_count"]
            assert isinstance(total, int) and total >= 0
            for mode in ("all", "buying", "selling"):
                for grouping in ("item", "person"):
                    page = expect(
                        "GET",
                        f"/api/conversations?marketplace_mode={mode}&group_by={grouping}",
                    )
                    assert len(page["items"]) <= 400
                    for item in page["items"]:
                        buying = (item["origin_kind"] == "sale_listing") == (
                            item["caller_role"] == "initiator"
                        )
                        assert mode == "all" or buying == (mode == "buying")
                        assert "email" not in item
        checks.append(
            "unique Handle claim/edit/conflict and completed setup; participant Handle and Temporary badge projection"
        )
        checks.append(
            "all Buying/Selling and Item/Person combinations; authorized global unread aggregate"
        )

    records["actors"] = {
        label: actor["user"]["user_id"] for label, actor in actors.items()
    }
    app.state.records = records
    return {
        "checks": checks,
        "records": records,
        "actors": list(ACTORS + ("temporary",)),
    }


def main():
    """Require explicit test mode; own and clean up every inspection resource."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-inspection", action="store_true", required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--port", type=int, choices=(5174, 5175, 5176), default=5174)
    args = parser.parse_args()
    global ORIGIN, HEADERS
    ORIGIN = f"http://127.0.0.1:{args.port}"
    HEADERS = {"Origin": ORIGIN, "X-CLIP-Request": "1"}
    import apps.api.tests.domains.listings.browser_image_preview as photo_preview

    photo_preview.ORIGIN = ORIGIN
    if os.environ.get("CLIP_ENVIRONMENT") != "test":
        parser.error("CLIP_ENVIRONMENT=test is required")
    with TemporaryDirectory(prefix="clip-marketplace-inspection-") as directory:
        with disposable_identity_database(Path(directory)) as connect:
            app = make_app(connect)
            photo = Path(directory) / "inspection-photo.png"
            photo.write_bytes(inspection_photo())
            (Path(directory) / "progress-photo.png").write_bytes(
                inspection_photo(large=True)
            )
            for number in range(1, 10):
                (Path(directory) / f"photo-{number}.png").write_bytes(
                    inspection_photo()
                )
            (Path(directory) / "invalid-photo.txt").write_text(
                "Synthetic invalid photo"
            )
            app.state.fixture_directory = Path(directory)
            report = exercise_and_seed(app)
            app.state.records["photo_file"] = str(photo)
            report["photo_file"] = str(photo)
            report["stop_pid"] = os.getpid()
            print(json.dumps(report, indent=2), flush=True)
            if not args.check_only:
                print(
                    "Inspection ready: "
                    + ORIGIN
                    + "/__inspection ; Ctrl+C cleans up this session.",
                    flush=True,
                )
                uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
