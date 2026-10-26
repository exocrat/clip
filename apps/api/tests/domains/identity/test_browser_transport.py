"""Actual TS transport/HTTP/cookies/SQL using owned loopback and synthetic signers."""

from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import uvicorn

from app.application import create_app
from app.domains.identity.http import BrowserPolicy, IdentityHttpDependencies
from apps.api.tests.domains.identity.session_fixtures import activate
from apps.api.tests.domains.identity.test_application_composition import compose


def test_real_browser_transport_over_loopback(identity_runtime, signed_tokens):
    """Test both feature adapters against real Identity middleware/domain SQL.

    Node emulates browser cookie/Origin/proxy handling only; no HTTP auth bypass
    or OTP inbox route is installed. Only this test's synthetic DB contains rows.
    JWT signing/mail are the existing controlled upstream ports, not live providers.
    """
    state = identity_runtime
    _, settings, _ = compose(state, signed_tokens)
    policy = BrowserPolicy(("http://localhost:5173",), development=True)
    application = create_app(
        settings,
        identity=IdentityHttpDependencies(
            state.service,
            policy,
            state.mail,
            signed_tokens.validator(),
            lambda: state.clock[0],
        ),
    )
    # Authenticate through the real single-use nonce/assertion/cookie handlers.
    browser = TestClient(
        application, base_url="http://localhost:5173", client=("127.0.0.1", 50000)
    )
    headers = {"Origin": "http://localhost:5173", "X-CLIP-Request": "1"}
    attempt = browser.post("/auth/microsoft/login-attempts", headers=headers)
    assert attempt.status_code == 201
    result = browser.post(
        "/auth/microsoft/sessions",
        headers=headers,
        json={"id_token": signed_tokens.token({"nonce": attempt.json()["nonce"]})},
    )
    assert result.status_code == 200
    regular_cookie = browser.cookies.get(policy.session_cookie)
    owner = result.json()["user_id"]
    temporary = activate(state)
    listing, upload = uuid4(), uuid4()
    now = datetime.now(UTC)
    with state.connect() as c, c.transaction():
        # Reviewed synthetic confirmed-image metadata only; no S3 claim or call.
        c.execute(
            """
            INSERT INTO listings.sale_listings
              (id,owner_id,title,description,category_id,condition_code,asking_price_paise,
               negotiable,pickup_area,availability,available_from,created_at,updated_at)
            SELECT %s,%s,'Synthetic browser listing','Owned transport fixture',id,'good',0,
              false,'Synthetic area','available',%s,%s,%s FROM listings.categories WHERE code='books'
        """,
            (listing, owner, now, now, now),
        )
        c.execute(
            """
            INSERT INTO listings.image_uploads
              (id,owner_id,operation_id,object_key,state,created_at,expires_at,confirmed_at,
               requested_media_type,requested_size_bytes,confirmed_media_type,confirmed_size_bytes)
            VALUES (%s,%s,%s,%s,'confirmed',%s,%s,%s,'image/png',1,'image/png',1)
        """,
            (
                upload,
                owner,
                upload,
                "synthetic-browser/" + str(upload),
                now,
                now + timedelta(hours=24),
                now,
            ),
        )
        c.execute(
            """
            INSERT INTO listings.images(id,listing_id,upload_id,object_key,position,media_type,size_bytes)
            VALUES (%s,%s,%s,%s,0,'image/png',1)
        """,
            (upload, listing, upload, "synthetic-browser/" + str(upload)),
        )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            application,
            host="127.0.0.1",
            port=port,
            access_log=False,
            log_config=None,
            proxy_headers=False,
        )
    )
    thread = threading.Thread(
        target=lambda: server.run(sockets=[listener]), daemon=True
    )
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            if not thread.is_alive():
                raise AssertionError("Owned HTTP server startup failed")
            time.sleep(0.05)
        assert server.started
        env = {key: os.environ[key] for key in ("HOME", "PATH")}
        env["CLIP_IDENTITY_TRANSPORT_HTTP"] = json.dumps(
            {
                "port": port,
                "regularCookie": regular_cookie,
                "temporaryCookie": temporary.token.get_secret_value(),
                "listingId": str(listing),
            }
        )
        process = subprocess.run(
            ["npm", "test", "--", "session-fetch-http.test.ts"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        diagnostic = (
            (process.stdout + process.stderr)
            .replace(
                regular_cookie or "unavailable-cookie", "[synthetic-session-redacted]"
            )
            .replace(temporary.token.get_secret_value(), "[synthetic-session-redacted]")
        )
        Path("/tmp/clip-id-ready-csrf-http-node.log").write_text(diagnostic)
        assert (
            process.returncode == 0
        ), "Real TS/HTTP integration failed; synthetic diagnostics in captured output"
        assert "1 passed" in process.stdout
        with state.connect() as c:
            assert c.execute(
                "SELECT count(*) FROM search.wanted_requests"
            ).fetchone() == (2,)
            assert c.execute(
                "SELECT count(*) FROM search.saved_listings"
            ).fetchone() == (0,)
            assert c.execute(
                "SELECT revision,availability FROM listings.sale_listings WHERE id=%s",
                (listing,),
            ).fetchone() == (2, "unavailable")
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        if thread.is_alive():
            server.force_exit = True
            thread.join(timeout=5)
        listener.close()
        browser.close()
        assert not thread.is_alive(), "Owned HTTP server did not stop"
