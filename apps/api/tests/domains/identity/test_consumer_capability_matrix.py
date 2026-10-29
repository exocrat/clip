"""Step14 real-cookie/service/SQL matrix; no consumer or caller override.

Only the reviewed external signing/mail fixtures and controlled Identity clock
are used. Listing/image metadata is synthetic SQL fixture data, NOT S3 upload,
confirmation, delivery or SDK encryption evidence. Those positive integration
cells stay pending. No shared target, live credentials, helper or cloud calls.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from contracts.source import identity, listings, search, conversations
from fastapi.testclient import TestClient
from psycopg import sql
import pytest

from apps.api.tests.domains.identity.session_fixtures import (
    HEADERS,
    ORIGIN,
    PASSWORD,
    EMAIL,
)
from apps.api.tests.domains.identity.test_application_composition import (
    compose,
    temporary,
)
from apps.api.tests.domains.identity.test_contacts import VALUES
from apps.api.tests.test_conversation_directory import public_bundle, prekey
from apps.api.tests.test_conversation_messages import message_request
from apps.api.tests.test_conversation_contact_share_cleanup import contact_request

ROOT = Path(__file__).resolve().parents[5]
MATRIX = json.loads(
    (ROOT / "docs/evaluation/identity/id-01-step-14/capability-matrix.json").read_text()
)
ROWS = {row["id"]: row for row in MATRIX["rows"]}

OPERATIONS = {
    (operation["method"], operation["path"]): operation
    for domain in (identity, listings, search, conversations)
    for operation in domain.HTTP_OPERATIONS
}


@dataclass(repr=False)
class Actor:
    """Transient browser summary/cookie jar; never an injected CallerContext."""

    summary: dict
    cookies: dict
    headers: dict


def use(browser, actor):
    """Switch browser jars only; the actual middleware verifies every request."""
    browser.cookies.clear()
    browser.cookies.update(actor.cookies)
    return actor.headers


def regular_actor(browser, signer, label):
    """Establish a real server session via nonce/cookie and signed assertion."""
    browser.cookies.clear()
    attempt = browser.post("/auth/microsoft/login-attempts", headers=HEADERS)
    assert attempt.status_code == 201
    assertion = signer.token(
        {
            "nonce": attempt.json()["nonce"],
            "sub": "step14-" + label,
            "email": "step14-" + label + "@iisc.ac.in",
        }
    )
    response = browser.post(
        "/auth/microsoft/sessions", headers=HEADERS, json={"id_token": assertion}
    )
    assert response.status_code == 200
    csrf = browser.get("/auth/csrf")
    assert csrf.status_code == 200
    return Actor(
        response.json(),
        dict(browser.cookies),
        HEADERS | {"X-CSRF-Token": csrf.json()["csrf_token"]},
    )


def seed_listing(state, owner):
    """Insert valid fixture SQL metadata, with no object-store substitute or claim.

    This prepares existent rows for authorization/visibility and real SQL consumer
    checks. It does not prove image bytes exist or replace an S3 positive test.
    """
    listing, upload, image, spare = (uuid4() for _ in range(4))
    with state.connect() as c, c.transaction():
        assert c.execute(
            "SELECT current_database(),inet_server_addr() IS NULL"
        ).fetchone() == ("clip_test_identity", True)
        category = c.execute(
            "SELECT id FROM listings.categories WHERE code='books'"
        ).fetchone()[0]
        c.execute(
            "INSERT INTO listings.sale_listings(id,owner_id,title,description,category_id,condition_code,asking_price_paise,negotiable,availability) VALUES(%s,%s,'Synthetic step14 bicycle','Owned authorization fixture',%s,'good',100,false,'available')",
            (listing, UUID(owner.summary["user_id"]), category),
        )
        for identifier in (upload, spare):
            c.execute(
                "INSERT INTO listings.image_uploads(id,owner_id,object_key,state,created_at,expires_at,confirmed_at,operation_id,requested_media_type,requested_size_bytes,confirmed_media_type,confirmed_size_bytes) VALUES(%s,%s,%s,'confirmed',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP+INTERVAL '24hours',CURRENT_TIMESTAMP,%s,'image/png',1,'image/png',1)",
                (
                    identifier,
                    UUID(owner.summary["user_id"]),
                    "step14-fixture/" + str(identifier),
                    uuid4(),
                ),
            )
        c.execute(
            "INSERT INTO listings.images(id,listing_id,upload_id,object_key,position,media_type,size_bytes) VALUES(%s,%s,%s,%s,0,'image/png',1)",
            (image, listing, upload, "step14-fixture/" + str(upload)),
        )
    return SimpleNamespace(
        id=str(listing), upload=str(upload), image=str(image), spare=str(spare)
    )


def fingerprint(state):
    """Return hashes only for owned disposable domain rows/own private profiles.

    No raw contact/ciphertext/keys leave SQL. Includes content, not merely counts,
    so denied edits/selections/watermarks cannot hide behind unchanged row totals.
    Session idle timestamps are intentionally outside this domain-effect audit.
    """
    with state.connect() as c, c.transaction():
        assert c.execute(
            "SELECT current_database(),inet_server_addr() IS NULL"
        ).fetchone() == ("clip_test_identity", True)
        c.execute("SET TRANSACTION READ ONLY")
        names = c.execute(
            "SELECT schemaname,tablename FROM pg_tables WHERE schemaname IN ('listings','search','conversations') ORDER BY 1,2"
        ).fetchall()
        values = {}
        for schema, name in [*names, ("identity", "contacts")]:
            query = sql.SQL(
                "SELECT md5(coalesce(string_agg(row_to_json(t)::text,',' ORDER BY row_to_json(t)::text),'')) FROM {} t"
            ).format(sql.Identifier(schema, name))
            values[schema + "." + name] = c.execute(query).fetchone()[0]
        values["profiles"] = c.execute(
            "SELECT md5(coalesce(string_agg(x::text,',' ORDER BY x::text),'')) FROM (SELECT id,display_name,profile_removed_at,expires_at FROM identity.users) x"
        ).fetchone()[0]
        return values


@pytest.fixture
def matrix_case(identity_runtime, signed_tokens, request):
    """Compose actual stores/public providers over the fixture-owned PostgreSQL.

    Actors are created through Identity routes. Wanted origins, thread pairs,
    keys, offers and a message use actual HTTP services. Only image metadata is
    prepared as explicitly limited SQL fixture data, without a storage fake.
    """
    state = identity_runtime
    app, settings, bindings = compose(state, signed_tokens)
    cohort = getattr(request, "param", "regular")
    if cohort.endswith("-conversation-role"):
        # Only the tuple pool changes; auth and marketplace retain their real paths.
        from urllib.parse import urlsplit, parse_qsl, urlencode
        import secrets
        from pydantic import SecretStr
        from app.application import create_app

        role = "clip_test_conversations_app"
        password = secrets.token_urlsafe(32)
        with state.connect() as connection:
            assert connection.execute(
                "SELECT current_database(),inet_server_addr() IS NULL"
            ).fetchone() == ("clip_test_identity", True)
            if connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)
            ).fetchone():
                connection.execute(
                    sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role))
                )
                connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
            connection.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
                ).format(sql.Identifier(role), sql.Literal(password))
            )
            # These revocations affect only this newly owned disposable database.
            connection.execute("REVOKE TEMP ON DATABASE clip_test_identity FROM PUBLIC")
            connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            connection.execute(
                "GRANT CONNECT ON DATABASE clip_test_identity TO clip_test_conversations_app"
            )
            connection.execute(
                (
                    ROOT
                    / "docs/evaluation/identity/id-01-step-14/conversations-runtime.sql.proposed"
                ).read_text()
            )
        parts = urlsplit(settings.database_url.get_secret_value())
        query = dict(parse_qsl(parts.query)) | {"user": role, "password": password}
        conversation_dsn = (
            settings.database_url.get_secret_value().split("?", 1)[0]
            + "?"
            + urlencode(query)
        )
        settings = settings.model_copy(
            update={"database_dsn": SecretStr(conversation_dsn)}
        )
        app = create_app(settings, identity=bindings)
    assert not app.dependency_overrides
    with TestClient(app, base_url=ORIGIN, client=("192.0.2.27", 51000)) as browser:
        seller = regular_actor(browser, signed_tokens, "seller")
        peer = regular_actor(browser, signed_tokens, "peer")
        stranger = regular_actor(browser, signed_tokens, "stranger")
        if cohort.startswith("temporary"):
            browser.cookies.clear()
            summary = temporary(browser, state)
            csrf = browser.get("/auth/csrf").json()["csrf_token"]
            actor = Actor(
                summary, dict(browser.cookies), HEADERS | {"X-CSRF-Token": csrf}
            )
        else:
            actor = seller
        own = seed_listing(state, seller)
        foreign = seed_listing(state, peer)
        headers = use(browser, actor)
        opened = browser.post(
            "/listings/" + foreign.id + "/conversations",
            headers=headers,
            json={"operation_id": str(uuid4())},
        )
        assert opened.status_code == 201
        chat = opened.json()["conversation_id"]
        headers = use(browser, stranger)
        selected = browser.post(
            "/listings/" + own.id + "/conversations",
            headers=headers,
            json={"operation_id": str(uuid4())},
        )
        assert selected.status_code == 201
        key_body = None
        for member in (actor, peer):
            headers = use(browser, member)
            bundle = public_bundle().model_dump(mode="json")
            response = browser.put("/me/conversation-key", headers=headers, json=bundle)
            assert response.status_code == 200
            if member is actor:
                key_body = bundle
        headers = use(browser, peer)
        batch = {
            "key_version": 1,
            "prekeys": [
                prekey(10).model_dump(mode="json"),
                prekey(11, kem=True).model_dump(mode="json"),
            ],
            "operation_id": str(uuid4()),
        }
        assert (
            browser.post(
                "/me/conversation-prekeys", headers=headers, json=batch
            ).status_code
            == 200
        )
        wanted = {}
        for name, member in [("own", actor), ("other", peer)]:
            headers = use(browser, member)
            response = browser.post(
                "/wanted-requests",
                headers=headers,
                json={
                    "title": "Synthetic step14 wanted",
                    "description": "Actual author workflow",
                    "category_code": "books",
                    "operation_id": str(uuid4()),
                },
            )
            assert response.status_code == 201
            wanted[name] = response.json()
        headers = use(browser, actor)
        offer = browser.put(
            "/listings/" + foreign.id + "/conversations/" + chat + "/offer",
            headers=headers,
            json={"amount_paise": 100, "operation_id": str(uuid4())},
        )
        assert offer.status_code == 200
        message = browser.post(
            "/conversations/" + chat + "/messages",
            headers=headers,
            json=message_request().model_dump(mode="json"),
        )
        assert message.status_code == 201
        yield SimpleNamespace(
            state=state,
            app=app,
            browser=browser,
            actor=actor,
            seller=seller,
            peer=peer,
            stranger=stranger,
            own=own,
            foreign=foreign,
            chat=chat,
            selection_chat=selected.json()["conversation_id"],
            wanted=wanted,
            offer=offer.json(),
            key_body=key_body,
        )


def request_spec(case, identifier):
    """Build contract-valid shapes using existent fixture IDs, never actor flags."""
    row = ROWS[identifier]
    listing = case.foreign if identifier in ("M02", "M14", "M15") else case.own
    replacements = {
        "listing_id": listing.id,
        "upload_id": case.own.spare if identifier == "M06" else case.own.upload,
        "image_id": case.own.image,
        "request_id": case.wanted["other" if identifier == "M23" else "own"][
            "request_id"
        ],
        "conversation_id": case.chat,
        "contact_kind": "email",
    }
    path = row["path"]
    for key, value in replacements.items():
        path = path.replace("{" + key + "}", value)
    operation = str(uuid4())
    basic = {
        "title": "Synthetic step14 sale",
        "description": "Fixture image metadata, no S3 claim",
        "category_code": "books",
        "condition_code": "good",
        "asking_price_paise": 100,
        "negotiable": False,
        "operation_id": operation,
    }
    payloads = {
        "M02": {"operation_id": operation},
        "M04": {"media_type": "image/png", "size_bytes": 1, "operation_id": operation},
        "M08": basic | {"image_upload_ids": [case.own.spare]},
        "M11": basic
        | {
            "expected_revision": 1,
            "pickup_area": None,
            "available_from": datetime(2020, 1, 1, tzinfo=UTC).isoformat(),
            "available_until": None,
            "proof_available": None,
            "images": [{"source": "existing", "image_id": case.own.image}],
        },
        "M12": {
            "expected_revision": 1,
            "availability": "unavailable",
            "operation_id": operation,
        },
        "M13": {
            "buyer_id": case.stranger.summary["user_id"],
            "conversation_id": case.selection_chat,
            "expected_revision": 1,
            "operation_id": operation,
        },
        "M14": {
            "amount_paise": 200,
            "expected_revision": case.offer["revision"],
            "operation_id": operation,
        },
        "M15": {
            "offer_id": case.offer["offer_id"],
            "expected_revision": case.offer["revision"],
            "operation_id": operation,
        },
        "M16": {"draft_title": "Synthetic bicycle"},
        "M19": {
            "title": "Synthetic step14 wanted",
            "description": "Owned fixture",
            "category_code": "books",
            "operation_id": operation,
        },
        "M21": {
            "title": "Changed synthetic wanted",
            "expected_revision": case.wanted["own"]["revision"],
            "operation_id": operation,
        },
        "M22": {
            "state": "unavailable",
            "expected_revision": case.wanted["own"]["revision"],
            "operation_id": operation,
        },
        "M23": {"operation_id": operation},
        "M25": {"operation_id": operation},
        "M28": {"fields": ["email"]},
        "M29": message_request().model_dump(mode="json"),
        "M30": contact_request().model_dump(mode="json"),
        "M34": {"last_read_sequence": 1},
        "M39": case.key_body,
        "M41": {
            "key_version": 1,
            "prekeys": [
                prekey(20).model_dump(mode="json"),
                prekey(21, kem=True).model_dump(mode="json"),
            ],
            "operation_id": operation,
        },
        "M42": {"operation_id": operation},
        "M44": {"display_name": "Synthetic step14 profile"},
        "M46": {"value": "step14-contact@example.invalid"},
    }
    body = payloads.get(identifier)
    mounted = case.app.openapi()["paths"][row["path"]][row["method"].lower()]
    assert mounted["operationId"] == row["operation_id"]
    operation = OPERATIONS[(row["method"], row["path"])]
    assert operation["operation_id"] == row["operation_id"]
    if "body" in operation:
        assert body is not None
        operation["body"].model_validate(body)
    else:
        assert body is None
    return row["method"], path, body


def call(case, identifier, *, headers=None):
    """Invoke a real mounted route; leave responses/cookies transient."""
    method, path, body = request_spec(case, identifier)
    options = {"headers": case.actor.headers if headers is None else headers}
    if body is not None:
        options["json"] = body
    return case.browser.request(method, path, **options)


TERMINAL = [
    ("regular", "session_expired"),
    ("regular", "account_revoked"),
    ("regular", "logout"),
    ("temporary", "session_expired"),
    ("temporary", "account_expired"),
    ("temporary", "account_revoked"),
    ("temporary", "logout"),
    ("temporary", "password_reset"),
]


@pytest.mark.parametrize("matrix_case,terminal", TERMINAL, indirect=["matrix_case"])
def test_all47_endpoints_reject_terminal_real_sessions(matrix_case, terminal):
    """Eight real lifecycle transitions deny all routes and preserve domain state.

    Account expiry uses a fresh login immediately before the14day boundary; its
    validity is correctly clipped to the account expiry. No invalid long-lived
    session or account lifetime is fabricated with SQL.
    """
    case = matrix_case
    specs = {key: request_spec(case, key) for key in ROWS}
    browser, state, actor = case.browser, case.state, case.actor
    use(browser, actor)
    if terminal == "account_expired":
        state.clock[0] += timedelta(days=13, hours=23, minutes=59)
        # Credential login starts a fresh jar; restored replay cookies otherwise
        # coexist with the new domain-scoped cookie in httpx's test client.
        browser.cookies.clear()
        response = browser.post(
            "/auth/temporary/sessions",
            headers=HEADERS,
            json={"email": EMAIL, "password": PASSWORD.get_secret_value()},
        )
        assert response.status_code == 200
        actor.cookies = dict(browser.cookies)
        csrf = browser.get("/auth/csrf")
        assert csrf.status_code == 200
        actor.headers = HEADERS | {"X-CSRF-Token": csrf.json()["csrf_token"]}
        state.clock[0] += timedelta(minutes=1)
    elif terminal == "session_expired":
        state.clock[0] += timedelta(days=8)
    elif terminal == "account_revoked":
        state.service.revoke_account(UUID(actor.summary["user_id"]))
    elif terminal == "logout":
        assert browser.delete("/auth/session", headers=actor.headers).status_code == 204
    elif terminal == "password_reset":
        state.clock[0] += timedelta(minutes=1)
        challenge = browser.post(
            "/auth/temporary/password-reset-challenges",
            headers=HEADERS,
            json={"email": EMAIL, "operation_id": str(uuid4())},
        )
        assert challenge.status_code == 202
        reset = browser.post(
            "/auth/temporary/password-resets",
            headers=HEADERS,
            json={
                "challenge_id": challenge.json()["challenge_id"],
                "code": state.mail.code(),
                "new_password": "synthetic-step14-reset-passphrase",
            },
        )
        assert reset.status_code == 204
    use(browser, actor)
    before = fingerprint(state)
    for key, (method, path, body) in specs.items():
        options = {
            "headers": actor.headers
            | {"X-Account-Class": "regular", "X-User-ID": case.peer.summary["user_id"]}
        }
        if body is not None:
            options["json"] = body
        response = browser.request(method, path, **options)
        assert (
            response.status_code == 401
        ), f"{key} {terminal}: expected terminal auth denial"
        assert "no-store" in response.headers["cache-control"]
    assert (
        fingerprint(state) == before
    ), "Terminal request changed consumer/profile state"


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_nonempty_reads_saved_wanted_and_profile_use_actual_providers(matrix_case):
    """Both classes traverse real listing resolvers and persist only owned state."""
    case = matrix_case
    browser = case.browser
    headers = use(browser, case.actor)
    for key in (
        "M01",
        "M03",
        "M09",
        "M10",
        "M17",
        "M18",
        "M20",
        "M24",
        "M27",
        "M31",
        "M32",
        "M33",
        "M35",
        "M36",
        "M37",
        "M38",
        "M40",
        "M43",
        "M45",
    ):
        response = call(case, key)
        assert response.status_code == 200, f"{key}: active read unavailable"
    page = call(case, "M01").json()
    assert len(page["items"]) == 2
    assert all(
        "owner_id" not in item and "selected_buyer_id" not in item
        for item in page["items"]
    )
    assert call(case, "M25").status_code == 200
    saved = call(case, "M24").json()["items"]
    assert len(saved) == 1
    assert call(case, "M26").status_code == 204
    assert call(case, "M24").json()["items"] == []
    before_expiry = browser.get("/me").json()["valid_until"]
    changed = call(case, "M21")
    assert changed.status_code == 200
    case.wanted["own"] = changed.json()
    assert call(case, "M22").status_code == 200
    assert browser.get("/me").json()["valid_until"] == before_expiry
    for field, value in VALUES.items():
        assert (
            browser.put(
                "/me/contacts/" + field, headers=headers, json={"value": value}
            ).status_code
            == 204
        )
    options = call(case, "M27").json()
    assert all(options.values())
    selected = call(case, "M28").json()
    assert (
        selected["email"] == VALUES["email"]
        and selected["phone"] is None
        and selected["upi_id"] is None
    )
    assert call(case, "M44").status_code == 200
    assert call(case, "M47").status_code == 204
    assert browser.get("/me/contacts").json()["email"] is None
    assert call(case, "M27").json()["email_available"] is False
    assert call(case, "M28").status_code == 422
    for field in ("phone", "upi_id"):
        assert (
            browser.delete("/me/contacts/" + field, headers=headers).status_code == 204
        )
    assert all(value is None for value in browser.get("/me/contacts").json().values())
    assert browser.get("/me").json()["valid_until"] == before_expiry


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_actual_conversation_keys_prekeys_and_contact_share(matrix_case):
    """Real member/key persistence; opaque test envelopes are not SDK crypto proof."""
    case = matrix_case
    browser = case.browser
    headers = use(browser, case.actor)
    assert call(case, "M39").status_code == 200
    assert call(case, "M41").status_code == 200
    own = call(case, "M40").json()
    assert own["ec_one_time_count"] == own["kem_one_time_count"] == 1
    method, path, body = request_spec(case, "M42")
    first = browser.request(method, path, headers=headers, json=body)
    assert first.status_code == 200
    assert (
        browser.request(method, path, headers=headers, json=body).json() == first.json()
    )
    assert first.json()["key_bundle"]["user_id"] == case.peer.summary["user_id"]
    method, path, body = request_spec(case, "M30")
    shared = browser.request(method, path, headers=headers, json=body)
    assert shared.status_code == 201
    repeated = browser.request(method, path, headers=headers, json=body)
    assert repeated.status_code == 200
    assert repeated.json() == shared.json()
    assert call(case, "M34").status_code == 200
    assert call(case, "M32").json()["own_last_read_sequence"] == 1
    own_before = fingerprint(case.state)
    use(browser, case.stranger)
    for key in (
        "M27",
        "M28",
        "M29",
        "M30",
        "M31",
        "M32",
        "M34",
        "M36",
        "M37",
        "M38",
        "M42",
    ):
        assert call(case, key, headers=case.stranger.headers).status_code == 404, key
    assert fingerprint(case.state) == own_before, "Nonmember modified consumer state"


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_every_unsafe_business_route_requires_origin_and_csrf(matrix_case):
    """Valid sessions cannot mutate through hostile origin or missing CSRF."""
    case = matrix_case
    use(case.browser, case.actor)
    before = fingerprint(case.state)
    for key, row in ROWS.items():
        if row["method"] == "GET":
            continue
        assert call(case, key, headers=HEADERS).status_code == 403, key
        assert (
            call(
                case,
                key,
                headers=case.actor.headers | {"Origin": "https://hostile.invalid"},
            ).status_code
            == 403
        ), key
    assert (
        fingerprint(case.state) == before
    ), "Rejected transport changed consumer state"


def test_temporary_class_cannot_be_promoted_by_headers(matrix_case):
    """Use a real temporary account; no fake eligibility or caller injection."""
    # This separate actor is created through OTP, then the same actual routes are used.
    case = matrix_case
    case.browser.cookies.clear()
    summary = temporary(case.browser, case.state)
    csrf = case.browser.get("/auth/csrf").json()["csrf_token"]
    actor = Actor(summary, dict(case.browser.cookies), HEADERS | {"X-CSRF-Token": csrf})
    case.actor = actor
    use(case.browser, actor)
    before = fingerprint(case.state)
    headers = actor.headers | {
        "X-Account-Class": "regular",
        "X-User-ID": case.seller.summary["user_id"],
    }
    for key in ("M04", "M08", "M11", "M12", "M13", "M23"):
        assert call(case, key, headers=headers).status_code == 403, key
    assert (
        fingerprint(case.state) == before
    ), "Temporary class denial changed consumer state"


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_offer_revision_withdrawal_exact_retry_and_other_buyer_denial(matrix_case):
    """Actual SQL receipts replay exactly; another buyer cannot change an offer."""
    case = matrix_case
    headers = use(case.browser, case.actor)
    method, path, body = request_spec(case, "M14")
    revised = case.browser.request(method, path, headers=headers, json=body)
    assert revised.status_code == 200
    assert revised.json()["revision"] == case.offer["revision"] + 1
    assert (
        case.browser.request(method, path, headers=headers, json=body).json()
        == revised.json()
    )
    altered = body | {"amount_paise": 300}
    before = fingerprint(case.state)
    assert (
        case.browser.request(method, path, headers=headers, json=altered).status_code
        == 409
    )
    assert fingerprint(case.state) == before
    case.offer = revised.json()
    method, path, body = request_spec(case, "M15")
    withdrawn = case.browser.request(method, path, headers=headers, json=body)
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"
    assert (
        case.browser.request(method, path, headers=headers, json=body).json()
        == withdrawn.json()
    )
    before = fingerprint(case.state)
    use(case.browser, case.stranger)
    for key in ("M14", "M15"):
        assert call(case, key, headers=case.stranger.headers).status_code == 404
    assert fingerprint(case.state) == before


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_wanted_response_class_replay_and_foreign_author_denial(matrix_case):
    """Real temporary authors remain authors, but only regular users may respond."""
    case = matrix_case
    headers = use(case.browser, case.actor)
    method, path, body = request_spec(case, "M23")
    before = fingerprint(case.state)
    response = case.browser.request(method, path, headers=headers, json=body)
    if case.actor.summary["account_class"] == "temporary":
        assert response.status_code == 403
        assert fingerprint(case.state) == before
    else:
        assert response.status_code == 201
        replay = case.browser.request(method, path, headers=headers, json=body)
        assert replay.status_code == 200
        assert replay.json()["conversation_id"] == response.json()["conversation_id"]
        assert response.json()["created"] is True
        assert replay.json()["created"] is False
    use(case.browser, case.peer)
    before = fingerprint(case.state)
    for key in ("M21", "M22"):
        assert call(case, key, headers=case.peer.headers).status_code == 404
    assert fingerprint(case.state) == before


def test_foreign_seller_commands_and_forged_body_cannot_change_ownership(matrix_case):
    """Existing owner resources remain protected against another signed-in user."""
    case = matrix_case
    use(case.browser, case.peer)
    before = fingerprint(case.state)
    for key in ("M06", "M11", "M12", "M13"):
        expected = 404 if key == "M06" else 403
        assert call(case, key, headers=case.peer.headers).status_code == expected
    assert fingerprint(case.state) == before
    headers = use(case.browser, case.actor)
    method, path, body = request_spec(case, "M08")
    forged = body | {
        "owner_id": case.peer.summary["user_id"],
        "account_class": "regular",
    }
    assert (
        case.browser.request(method, path, headers=headers, json=forged).status_code
        == 422
    )
    assert fingerprint(case.state) == before


def test_regular_owner_sale_commands_and_public_selection_privacy(matrix_case):
    """Real owner commands use SQL image metadata; no S3 upload claim is made."""
    case = matrix_case
    headers = use(case.browser, case.actor)
    assert call(case, "M06").status_code == 204
    replaced = call(case, "M11")
    assert replaced.status_code == 200

    # Public command responses omit management fields; read the owner endpoint.
    def management():
        """Read the current persisted owner revision through the actual API."""
        response = case.browser.get("/me/listings")
        assert response.status_code == 200
        return next(
            item
            for item in response.json()["items"]
            if item["listing_id"] == case.own.id
        )

    current = management()
    assert current["owner_id"] == case.actor.summary["user_id"]
    assert current["title"] == "Synthetic step14 sale"
    method, path, body = request_spec(case, "M12")
    body["expected_revision"] = current["revision"]
    closed = case.browser.request(method, path, headers=headers, json=body)
    assert closed.status_code == 200
    assert closed.json()["availability"] == "unavailable"
    reopened = case.browser.request(
        method,
        path,
        headers=headers,
        json=body
        | {
            "expected_revision": management()["revision"],
            "availability": "available",
            "operation_id": str(uuid4()),
        },
    )
    assert reopened.status_code == 200
    method, path, body = request_spec(case, "M13")
    body["expected_revision"] = management()["revision"]
    selected = case.browser.request(method, path, headers=headers, json=body)
    assert selected.status_code == 200
    assert selected.json()["selected_buyer_id"] == case.stranger.summary["user_id"]
    assert selected.json()["selected_conversation_id"] == case.selection_chat
    # An owner still receives the public projection from the public detail route.
    public = case.browser.get("/listings/" + case.own.id)
    assert public.status_code == 200
    assert (
        not {"owner_id", "selected_buyer_id", "selected_conversation_id", "revision"}
        & public.json().keys()
    )
    case.own = seed_listing(case.state, case.actor)
    created = call(case, "M08")
    assert created.status_code == 201
    assert len(created.json()["image_ids"]) == 1
    assert created.json()["title"] == "Synthetic step14 sale"


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_keyword_filters_draft_matches_and_closed_wanted_visibility(matrix_case):
    """Both active classes use real indexed search; closed Wanted is author-only."""
    case = matrix_case
    headers = use(case.browser, case.actor)
    query = {
        "q": "bicycle",
        "search_mode": "keyword",
        "category_code": "books",
        "condition_code": "good",
        "min_price_paise": 100,
        "max_price_paise": 100,
        "sort": "price_asc",
    }
    for sort in ("price_asc", "price_desc", "created_desc", "relevance"):
        response = case.browser.get("/listings", params=query | {"sort": sort})
        assert response.status_code == 200
        assert len(response.json()["items"]) == 2
        assert all(
            item["asking_price_paise"] == 100 for item in response.json()["items"]
        )
    empty = case.browser.get(
        "/listings", params=query | {"min_price_paise": 200, "max_price_paise": 200}
    )
    assert empty.status_code == 200 and empty.json()["items"] == []
    second = case.browser.get("/listings", params=query | {"page": 2})
    assert second.status_code == 200 and second.json()["items"] == []
    before = fingerprint(case.state)
    matches = call(case, "M16")
    assert matches.status_code == 200
    assert len(matches.json()["items"]) == 2
    assert fingerprint(case.state) == before, "Draft matching persisted state"
    closed = call(case, "M22")
    assert closed.status_code == 200
    identifier = case.wanted["own"]["request_id"]
    path = "/wanted-requests/" + identifier
    assert case.browser.get(path).status_code == 200
    assert identifier not in {
        item["request_id"]
        for item in case.browser.get("/wanted-requests").json()["items"]
    }
    assert identifier in {
        item["request_id"]
        for item in case.browser.get("/me/wanted-requests").json()["items"]
    }
    use(case.browser, case.peer)
    before = fingerprint(case.state)
    assert case.browser.get(path).status_code == 404
    denied = case.browser.post(
        path + "/conversations",
        headers=case.peer.headers,
        json={"operation_id": str(uuid4())},
    )
    assert denied.status_code == 404
    assert fingerprint(case.state) == before


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_cross_domain_validation_errors_never_reflect_private_input(matrix_case):
    """Malformed payloads use bounded public errors, never submitted private data."""
    case = matrix_case
    headers = use(case.browser, case.actor)
    marker = "synthetic-private-value-do-not-reflect"
    before = fingerprint(case.state)
    for key in ("M08", "M19", "M29", "M44"):
        method, path, body = request_spec(case, key)
        response = case.browser.request(
            method, path, headers=headers, json=body | {marker: marker}
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
        assert marker not in response.text
        assert "no-store" in response.headers["cache-control"]
    assert fingerprint(case.state) == before


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_wanted_self_response_and_existing_pair_survive_ordinary_closure(matrix_case):
    """Class/owner gates hold while an existing regular responder keeps its pair."""
    case = matrix_case
    path = "/wanted-requests/" + case.wanted["own"]["request_id"]
    headers = use(case.browser, case.actor)
    before = fingerprint(case.state)
    assert (
        case.browser.post(
            path + "/conversations",
            headers=headers,
            json={"operation_id": str(uuid4())},
        ).status_code
        == 403
    )
    assert fingerprint(case.state) == before
    peer_headers = use(case.browser, case.peer)
    started = case.browser.post(
        path + "/conversations",
        headers=peer_headers,
        json={"operation_id": str(uuid4())},
    )
    assert started.status_code == 201
    use(case.browser, case.actor)
    closed = call(case, "M22")
    assert closed.status_code == 200
    use(case.browser, case.peer)
    before = fingerprint(case.state)
    for _ in range(2):
        repeated = case.browser.post(
            path + "/conversations",
            headers=peer_headers,
            json={"operation_id": str(uuid4())},
        )
        assert repeated.status_code == 200
        assert repeated.json() == {
            "conversation_id": started.json()["conversation_id"],
            "created": False,
        }
    assert fingerprint(case.state) == before
    use(case.browser, case.stranger)
    assert (
        case.browser.post(
            path + "/conversations",
            headers=case.stranger.headers,
            json={"operation_id": str(uuid4())},
        ).status_code
        == 404
    )
    assert fingerprint(case.state) == before


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_real_retirement_scrubs_wanted_and_denies_owner_and_other_access(matrix_case):
    """Actual retirement services handle an aged SQL fixture; no scheduler/cloud."""
    from app.domains.search.wanted_retirement import WantedRetirementService

    case = matrix_case
    identifier = uuid4()
    now = datetime.now(UTC)
    with case.state.connect() as connection:
        assert connection.execute(
            "SELECT current_database(),inet_server_addr() IS NULL"
        ).fetchone() == ("clip_test_identity", True)
        connection.execute(
            "INSERT INTO search.wanted_requests(id,author_id,title,description,category_code,status,created_at,closed_at) VALUES(%s,%s,'Synthetic aged request','Retirement authorization fixture','books','unavailable',%s,%s)",
            (
                identifier,
                UUID(case.actor.summary["user_id"]),
                now - timedelta(days=400),
                now - timedelta(days=181),
            ),
        )
    service = WantedRetirementService(
        case.app.state.wanted_store, case.app.state.conversations_public, lambda: now
    )
    result = case.browser.portal.call(service.retire, identifier)
    assert result.outcome == "marked" and result.marked_count == 0
    assert case.browser.portal.call(service.retire, identifier) is None
    with case.state.connect() as connection:
        row = connection.execute(
            "SELECT title,description,category_code,budget_paise,retired_at IS NOT NULL FROM search.wanted_requests WHERE id=%s",
            (identifier,),
        ).fetchone()
        assert row == (None, None, None, None, True)
    path = "/wanted-requests/" + str(identifier)
    before = fingerprint(case.state)
    for member in (case.actor, case.peer):
        headers = use(case.browser, member)
        assert case.browser.get(path).status_code == 404
        mutation_status = 409 if member is case.actor else 404
        assert (
            case.browser.patch(
                path,
                headers=headers,
                json={
                    "title": "Synthetic retry",
                    "expected_revision": 2,
                    "operation_id": str(uuid4()),
                },
            ).status_code
            == mutation_status
        )
        assert (
            case.browser.put(
                path + "/availability",
                headers=headers,
                json={
                    "state": "open",
                    "expected_revision": 2,
                    "operation_id": str(uuid4()),
                },
            ).status_code
            == mutation_status
        )
        expected = 403 if member.summary["account_class"] == "temporary" else 404
        assert (
            case.browser.post(
                path + "/conversations",
                headers=headers,
                json={"operation_id": str(uuid4())},
            ).status_code
            == expected
        )
        assert str(identifier) not in {
            item["request_id"]
            for item in case.browser.get("/me/wanted-requests").json()["items"]
        }
    assert fingerprint(case.state) == before


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_closed_sale_preserves_existing_pair_and_blocks_new_offer(matrix_case):
    """Ordinary closure preserves access to existing chat but cannot create a pair."""
    case = matrix_case
    headers = use(case.browser, case.peer)
    path = "/listings/" + case.foreign.id
    closed = case.browser.put(
        path + "/availability",
        headers=headers,
        json={
            "expected_revision": 1,
            "availability": "unavailable",
            "operation_id": str(uuid4()),
        },
    )
    assert closed.status_code == 200
    headers = use(case.browser, case.actor)
    before = fingerprint(case.state)
    reopened_chat = case.browser.post(
        path + "/conversations", headers=headers, json={"operation_id": str(uuid4())}
    )
    assert reopened_chat.status_code == 200
    assert reopened_chat.json() == {"conversation_id": case.chat, "created": False}
    assert call(case, "M14").status_code == 409
    assert fingerprint(case.state) == before
    use(case.browser, case.stranger)
    assert (
        case.browser.post(
            path + "/conversations",
            headers=case.stranger.headers,
            json={"operation_id": str(uuid4())},
        ).status_code
        == 404
    )
    assert fingerprint(case.state) == before
    use(case.browser, case.peer)
    assert (
        case.browser.post(
            path + "/conversations",
            headers=case.peer.headers,
            json={"operation_id": str(uuid4())},
        ).status_code
        == 403
    )
    assert fingerprint(case.state) == before
    use(case.browser, case.actor)
    assert call(case, "M15").status_code == 200


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_prekey_depletion_rotation_retry_and_empty_draft_match(matrix_case):
    """Actual SQL prekeys are reserved once; fixture public bytes do not prove crypto."""
    case = matrix_case
    headers = use(case.browser, case.actor)
    before = fingerprint(case.state)
    empty = case.browser.post(
        "/wanted-requests/draft-matches",
        headers=headers,
        json={"draft_title": "Unmatchedsynthetictoken"},
    )
    assert empty.status_code == 200 and empty.json()["items"] == []
    assert fingerprint(case.state) == before
    method, path, body = request_spec(case, "M42")
    first = case.browser.request(method, path, headers=headers, json=body)
    assert first.status_code == 200
    assert first.json()["ec_one_time_prekey"] is not None
    assert first.json()["kem_one_time_prekey"] is not None
    repeated = case.browser.request(method, path, headers=headers, json=body)
    assert repeated.status_code == 200 and repeated.json() == first.json()
    depleted = case.browser.request(
        method, path, headers=headers, json={"operation_id": str(uuid4())}
    )
    assert depleted.status_code == 200
    assert depleted.json()["ec_one_time_prekey"] is None
    assert depleted.json()["kem_one_time_prekey"] is None
    peer_headers = use(case.browser, case.peer)
    inventory = case.browser.get("/me/conversation-prekeys").json()
    assert inventory["ec_one_time_count"] == inventory["kem_one_time_count"] == 0
    rotated = case.browser.put(
        "/me/conversation-key",
        headers=peer_headers,
        json=public_bundle(registration_id=2).model_dump(mode="json"),
    )
    assert rotated.status_code == 200 and rotated.json()["key_version"] == 2
    before = fingerprint(case.state)
    stale = case.browser.post(
        "/me/conversation-prekeys",
        headers=peer_headers,
        json={
            "key_version": 1,
            "prekeys": [prekey(30).model_dump(mode="json")],
            "operation_id": str(uuid4()),
        },
    )
    assert stale.status_code == 409
    assert fingerprint(case.state) == before
    use(case.browser, case.actor)
    current = case.browser.request(
        method, path, headers=headers, json={"operation_id": str(uuid4())}
    )
    assert (
        current.status_code == 200 and current.json()["key_bundle"]["key_version"] == 2
    )
    assert (
        case.browser.request(method, path, headers=headers, json=body).json()
        == first.json()
    )


def test_selection_binding_stale_revision_and_clear_without_reopen(matrix_case):
    """Seller cannot select unrelated thread/user IDs or overwrite a stale revision."""
    case = matrix_case
    headers = use(case.browser, case.actor)
    method, path, body = request_spec(case, "M13")
    before = fingerprint(case.state)
    for changes, expected in (
        ({"conversation_id": case.chat}, 404),
        ({"buyer_id": case.peer.summary["user_id"]}, 404),
        ({"buyer_id": case.actor.summary["user_id"]}, 403),
        ({"expected_revision": 999}, 409),
    ):
        assert (
            case.browser.request(
                method, path, headers=headers, json=body | changes
            ).status_code
            == expected
        )
        assert fingerprint(case.state) == before
    method2, path2, replacement = request_spec(case, "M11")
    assert (
        case.browser.request(
            method2,
            path2,
            headers=headers,
            json=replacement | {"expected_revision": 999},
        ).status_code
        == 409
    )
    assert fingerprint(case.state) == before
    selected = case.browser.request(method, path, headers=headers, json=body)
    assert selected.status_code == 200
    assert selected.json()["availability"] == "unavailable"
    cleared = case.browser.request(
        method,
        path,
        headers=headers,
        json={
            "buyer_id": None,
            "conversation_id": None,
            "expected_revision": selected.json()["revision"],
            "operation_id": str(uuid4()),
        },
    )
    assert cleared.status_code == 200
    assert cleared.json()["selected_buyer_id"] is None
    assert cleared.json()["selected_conversation_id"] is None
    assert cleared.json()["availability"] == "unavailable"


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_wanted_revision_replay_reopen_and_message_operation_binding(matrix_case):
    """Actual owner revisions/retries and message receipts cannot rewrite history."""
    case = matrix_case
    headers = use(case.browser, case.actor)
    method, path, body = request_spec(case, "M21")
    changed = case.browser.request(method, path, headers=headers, json=body)
    assert changed.status_code == 200
    before = fingerprint(case.state)
    replay = case.browser.request(method, path, headers=headers, json=body)
    assert replay.status_code == 200 and replay.json() == changed.json()
    assert (
        case.browser.request(
            method, path, headers=headers, json=body | {"operation_id": str(uuid4())}
        ).status_code
        == 409
    )
    assert fingerprint(case.state) == before
    case.wanted["own"] = changed.json()
    closed = call(case, "M22")
    assert closed.status_code == 200
    reopened = case.browser.put(
        path + "/availability",
        headers=headers,
        json={
            "state": "open",
            "expected_revision": closed.json()["revision"],
            "operation_id": str(uuid4()),
        },
    )
    assert reopened.status_code == 200 and reopened.json()["state"] == "open"
    method, path, body = request_spec(case, "M29")
    sent = case.browser.request(method, path, headers=headers, json=body)
    assert sent.status_code == 201
    before = fingerprint(case.state)
    repeated = case.browser.request(method, path, headers=headers, json=body)
    assert repeated.status_code == 200 and repeated.json() == sent.json()
    altered = message_request(
        operation_id=UUID(body["operation_id"]), payload=b"different-synthetic-envelope"
    ).model_dump(mode="json")
    assert (
        case.browser.request(method, path, headers=headers, json=altered).status_code
        == 409
    )
    assert fingerprint(case.state) == before


@pytest.mark.parametrize("matrix_case", ["regular", "temporary"], indirect=True)
def test_concurrent_http_prekey_requests_reserve_each_key_once(matrix_case):
    """Concurrent real HTTP requests use the shipped bounded pool, not a fake store."""
    import asyncio
    from httpx2 import ASGITransport, AsyncClient

    case = matrix_case
    path = "/conversations/" + case.chat + "/prekey-bundle"
    operations = [str(uuid4()), str(uuid4())]

    async def concurrent_requests():
        """Use the app's existing event loop and isolated browser cookies per client."""

        async def request(operation):
            async with AsyncClient(
                transport=ASGITransport(app=case.app),
                base_url=ORIGIN,
                cookies=case.actor.cookies,
                headers=case.actor.headers,
            ) as client:
                return await client.post(path, json={"operation_id": operation})

        return await asyncio.gather(*(request(operation) for operation in operations))

    responses = case.browser.portal.call(concurrent_requests)
    assert all(response.status_code == 200 for response in responses)
    for field in ("ec_one_time_prekey", "kem_one_time_prekey"):
        assert sum(response.json()[field] is not None for response in responses) == 1
    headers = use(case.browser, case.actor)
    before = fingerprint(case.state)
    for operation, original in zip(operations, responses, strict=True):
        repeated = case.browser.post(
            path, headers=headers, json={"operation_id": operation}
        )
        assert repeated.status_code == 200 and repeated.json() == original.json()
    assert fingerprint(case.state) == before


@pytest.mark.parametrize(
    "matrix_case",
    ["regular-conversation-role", "temporary-conversation-role"],
    indirect=True,
)
def test_pending_and_threaded_retirement_blocks_real_participant_writes(matrix_case):
    """Real marker coordination uses the distinct login and an aged fixture thread."""
    from app.domains.search.wanted_retirement import WantedRetirementService

    case = matrix_case
    identifier, chat = uuid4(), uuid4()
    now = datetime.now(UTC)
    with case.state.connect() as connection, connection.transaction():
        assert connection.execute(
            "SELECT current_database(),inet_server_addr() IS NULL"
        ).fetchone() == ("clip_test_identity", True)
        connection.execute(
            "INSERT INTO search.wanted_requests(id,author_id,title,description,category_code,status,created_at,closed_at) VALUES(%s,%s,'Synthetic threaded request','Aged authorization fixture','books','unavailable',%s,%s)",
            (
                identifier,
                UUID(case.actor.summary["user_id"]),
                now - timedelta(days=400),
                now - timedelta(days=181),
            ),
        )
        connection.execute(
            "INSERT INTO conversations.threads(id,wanted_request_id,initiator_id,counterparty_id,created_at,last_activity_at) VALUES(%s,%s,%s,%s,%s,%s)",
            (
                chat,
                identifier,
                UUID(case.peer.summary["user_id"]),
                UUID(case.actor.summary["user_id"]),
                now - timedelta(days=200),
                now - timedelta(days=100),
            ),
        )
        connection.execute(
            "INSERT INTO conversations.members(conversation_id,user_id) VALUES(%s,%s),(%s,%s)",
            (
                chat,
                UUID(case.peer.summary["user_id"]),
                chat,
                UUID(case.actor.summary["user_id"]),
            ),
        )
    pending = case.browser.portal.call(
        case.app.state.wanted_store.begin_retirement, identifier, now
    )
    assert pending is not None
    path = "/wanted-requests/" + str(identifier)
    headers = use(case.browser, case.actor)
    before = fingerprint(case.state)
    assert (
        case.browser.patch(
            path,
            headers=headers,
            json={
                "title": "Denied change",
                "expected_revision": 1,
                "operation_id": str(uuid4()),
            },
        ).status_code
        == 409
    )
    peer_headers = use(case.browser, case.peer)
    assert (
        case.browser.post(
            path + "/conversations",
            headers=peer_headers,
            json={"operation_id": str(uuid4())},
        ).status_code
        == 404
    )
    assert fingerprint(case.state) == before
    service = WantedRetirementService(
        case.app.state.wanted_store, case.app.state.conversations_public, lambda: now
    )
    result = case.browser.portal.call(service.retire, identifier)
    assert result.outcome == "marked" and result.marked_count == 1
    before = fingerprint(case.state)
    for member in (case.actor, case.peer):
        headers = use(case.browser, member)
        chat_path = "/conversations/" + str(chat)
        assert case.browser.get(chat_path).status_code == 200
        assert (
            case.browser.post(
                chat_path + "/messages",
                headers=headers,
                json=message_request().model_dump(mode="json"),
            ).status_code
            == 409
        )
        assert case.browser.post(
            path + "/conversations",
            headers=headers,
            json={"operation_id": str(uuid4())},
        ).status_code == (
            403 if member.summary["account_class"] == "temporary" else 404
        )
    assert fingerprint(case.state) == before
    with case.state.connect() as connection:
        assert connection.execute(
            "SELECT participant_writes_disabled_at IS NOT NULL FROM conversations.threads WHERE id=%s",
            (chat,),
        ).fetchone() == (True,)
        assert connection.execute(
            "SELECT count(*) FROM conversations.members WHERE conversation_id=%s",
            (chat,),
        ).fetchone() == (2,)
