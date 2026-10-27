"""Real cookie/CSRF/Identity SQL through the shared Conversations application.

Only external Microsoft signing/mail/image storage are controlled; every database
belongs to the disposable fixture. No live credentials, caller override or target.
"""

from datetime import timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from apps.api.tests.domains.identity.conftest import (
    disposable_database,
    jwt_clock,
    signed_tokens,
    signing_key,
)
from apps.api.tests.domains.identity.session_fixtures import identity_runtime, HEADERS
from apps.api.tests.domains.identity.test_application_composition import (
    compose,
    regular,
    temporary,
)
from apps.api.tests.domains.listings.test_image_upload_service import _ImageStorage
from app.domains.listings.service import StoredImageMetadata
from apps.api.tests.test_conversation_directory import public_bundle
from apps.api.tests.test_conversation_messages import message_request


def signed_actor(client, signer, label):
    """Create a distinct real cookie session through the controlled OIDC exchange.

    Keep one application lifespan/pool set; switching cookie jars models separate
    browsers without starting or stopping the shared application for each actor.
    """
    client.cookies.clear()
    attempt = client.post("/auth/microsoft/login-attempts", headers=HEADERS)
    assert attempt.status_code == 201
    token = signer.token(
        {
            "nonce": attempt.json()["nonce"],
            "sub": "synthetic-chat-" + label,
            "email": "synthetic-chat-" + label + "@iisc.ac.in",
        }
    )
    session = client.post(
        "/auth/microsoft/sessions", headers=HEADERS, json={"id_token": token}
    )
    assert session.status_code == 200
    csrf = client.get("/auth/csrf")
    assert csrf.status_code == 200
    return (
        session.json(),
        dict(client.cookies),
        HEADERS | {"X-CSRF-Token": csrf.json()["csrf_token"]},
    )


def use_actor(client, actor):
    """Restore only the browser cookie jar, never a caller or provider override."""
    client.cookies.clear()
    client.cookies.update(actor[1])
    return actor[2]


def temporary_actor(client, state):
    """Activate a temporary buyer/author through real OTP and cookie endpoints."""
    client.cookies.clear()
    session = temporary(client, state)
    csrf = client.get("/auth/csrf").json()["csrf_token"]
    return session, dict(client.cookies), HEADERS | {"X-CSRF-Token": csrf}


def test_signed_listing_publication_to_temporary_buyer_conversation(
    identity_runtime, signed_tokens
):
    """Publish through upload/confirm/create HTTP, then open/reopen the real pair.

    Only external image storage is controlled. Real owner-bound upload records,
    confirmed metadata, listing publication and Conversations persistence run SQL.
    No precreated listing/thread is copied into place to satisfy the workflow.
    """
    state = identity_runtime
    app, _, _ = compose(state, signed_tokens)
    with TestClient(
        app, base_url="https://clip-iisc.site", client=("192.0.2.27", 41000)
    ) as client:
        storage = _ImageStorage()
        app.state.listings_image_storage = storage
        seller = signed_actor(client, signed_tokens, "seller")
        headers = use_actor(client, seller)
        upload = client.post(
            "/image-uploads",
            headers=headers,
            json={
                "media_type": "image/png",
                "size_bytes": 32,
                "operation_id": str(uuid4()),
            },
        )
        assert upload.status_code == 201, upload.text
        upload_id = upload.json()["upload_id"]
        # The controlled object-store port reports receipt of synthetic bytes;
        # confirmation still validates that metadata through the real service.
        storage.objects[storage.object_key_for(UUID(upload_id))] = StoredImageMetadata(
            media_type="image/png", size_bytes=32
        )
        confirmed = client.post(
            "/image-uploads/" + upload_id + "/confirm", headers=headers
        )
        assert confirmed.status_code == 200, confirmed.text
        listing = client.post(
            "/listings",
            headers=headers,
            json={
                "title": "Synthetic signed-in sale",
                "description": "Controlled integration fixture only",
                "category_code": "mobile_phone",
                "condition_code": "good",
                "asking_price_paise": 100,
                "negotiable": False,
                "image_upload_ids": [upload_id],
                "operation_id": str(uuid4()),
            },
        )
        assert listing.status_code == 201, listing.text
        origin = "/listings/" + listing.json()["listing_id"]
        assert (
            client.post(
                origin + "/conversations",
                headers=headers,
                json={"operation_id": str(uuid4())},
            ).status_code
            == 403
        )
        buyer = temporary_actor(client, state)
        account = buyer[0]
        headers = use_actor(client, buyer)
        opened = client.post(
            origin + "/conversations",
            headers=headers,
            json={"operation_id": str(uuid4())},
        )
        assert opened.status_code == 201, opened.text
        chat = "/conversations/" + opened.json()["conversation_id"]
        summary = client.get(chat)
        assert summary.status_code == 200
        assert summary.json()["initiator_user_id"] == account["user_id"]
        assert summary.json()["counterparty_user_id"] == seller[0]["user_id"]
        # Real temporary-account cookies, CSRF, membership and Identity contacts
        # participate in the same app; preparation must not publish an entry.
        synthetic_email = "synthetic-contact@example.com"
        assert (
            client.put(
                "/me/contacts/email", headers=headers, json={"value": synthetic_email}
            ).status_code
            == 204
        )
        assert (
            client.put(
                "/me/contacts/phone", headers=headers, json={"value": "+919876543210"}
            ).status_code
            == 204
        )
        options = client.get(chat + "/contact-options")
        assert options.status_code == 200
        assert options.json() == {
            "email_available": True,
            "phone_available": True,
            "upi_available": False,
        }
        assert (
            client.post(
                chat + "/contact-preparations",
                headers=HEADERS,
                json={"fields": ["email"]},
            ).status_code
            == 403
        )
        assert (
            client.post(
                chat + "/contact-preparations",
                headers=headers | {"Origin": "https://foreign.invalid"},
                json={"fields": ["email"]},
            ).status_code
            == 403
        )
        prepared = client.post(
            chat + "/contact-preparations", headers=headers, json={"fields": ["email"]}
        )
        assert (
            prepared.status_code == 200
            and prepared.headers["cache-control"] == "no-store"
        )
        selected_only = prepared.json() == {
            "email": synthetic_email,
            "phone": None,
            "upi_id": None,
        }
        assert selected_only, "selected own-contact projection mismatch"
        assert client.get(chat).json() == summary.json()
        assert client.get(chat + "/entries").json()["items"] == []
        assert client.delete("/me/contacts/phone", headers=headers).status_code == 204
        assert (
            client.post(
                chat + "/contact-preparations",
                headers=headers,
                json={"fields": ["phone"]},
            ).status_code
            == 422
        )
        use_actor(client, seller)
        assert client.get(chat + "/contact-options").json() == {
            "email_available": False,
            "phone_available": False,
            "upi_available": False,
        }
        for actor in (seller, buyer):
            headers = use_actor(client, actor)
            key = client.put(
                "/me/conversation-key",
                headers=headers,
                json=public_bundle().model_dump(mode="json"),
            )
            assert key.status_code == 200
        sent = client.post(
            chat + "/messages",
            headers=headers,
            json=message_request().model_dump(mode="json"),
        )
        assert sent.status_code == 201 and sent.json()["sequence"] == 1
        headers = use_actor(client, seller)
        owned = client.get("/me/listings").json()["items"]
        assert len(owned) == 1
        assert client.get(chat + "/entries").json()["items"] == [sent.json()]
        reply = client.post(
            chat + "/messages",
            headers=headers,
            json=message_request(payload=b"opaque-seller-reply").model_dump(
                mode="json"
            ),
        )
        assert reply.status_code == 201 and reply.json()["sequence"] == 2
        # Exercise the real buyer offer path with cookies and CSRF, not a caller
        # override. The optional note is deliberately opaque synthetic ciphertext.
        headers = use_actor(client, buyer)
        offer_body = {
            "amount_paise": 0,
            "operation_id": str(uuid4()),
            "note_envelope": message_request().envelope.model_dump(mode="json"),
        }
        offer_url = origin + "/conversations/" + opened.json()["conversation_id"]
        offered = client.put(offer_url + "/offer", headers=headers, json=offer_body)
        assert offered.status_code == 200, offered.text
        assert (
            client.put(offer_url + "/offer", headers=headers, json=offer_body).json()
            == offered.json()
        )
        headers = use_actor(client, seller)
        assert client.get(chat + "/offer").json() == offered.json()
        page = client.get(chat + "/entries").json()
        assert page["items"] == [sent.json(), reply.json()]
        assert page["scanned_through_sequence"] == 3
        closed = client.put(
            origin + "/availability",
            headers=headers,
            json={
                "availability": "unavailable",
                "expected_revision": owned[0]["revision"],
                "operation_id": str(uuid4()),
            },
        )
        assert closed.status_code == 200, closed.text
        headers = use_actor(client, buyer)
        retry = client.put(offer_url + "/offer", headers=headers, json=offer_body)
        assert retry.status_code == 409
        assert retry.json()["error"]["details"] == [
            {"field": "listing_id", "code": "unavailable"}
        ]
        assert client.get(chat + "/offer").json() == offered.json()
        withdrawn = client.post(
            offer_url + "/offer-withdrawals",
            headers=headers,
            json={
                "offer_id": offered.json()["offer_id"],
                "expected_revision": 1,
                "operation_id": str(uuid4()),
            },
        )
        assert (
            withdrawn.status_code == 200 and withdrawn.json()["status"] == "withdrawn"
        )
        reopened = client.post(
            origin + "/conversations",
            headers=headers,
            json={"operation_id": str(uuid4())},
        )
        assert reopened.status_code == 200 and reopened.json()["created"] is False
        assert reopened.json()["conversation_id"] == opened.json()["conversation_id"]
        stranger = signed_actor(client, signed_tokens, "listing-stranger")
        assert (
            client.post(
                origin + "/conversations",
                headers=stranger[2],
                json={"operation_id": str(uuid4())},
            ).status_code
            == 404
        )
        assert client.get(chat).status_code == 404
        assert client.get(chat + "/contact-options").status_code == 404
        assert (
            client.post(
                chat + "/contact-preparations",
                headers=stranger[2],
                json={"fields": ["email"]},
            ).status_code
            == 404
        )


@pytest.mark.parametrize("terminal", ["logout", "revoked", "expired"])
@pytest.mark.parametrize("author_class", ["regular", "temporary"])
def test_signed_wanted_origin_to_messages_and_read_state(
    identity_runtime, signed_tokens, terminal, author_class
):
    """Owner HTTP creates the origin/thread; cookies govern every message/read.

    Public keys/envelopes are shape-valid opaque synthetic bytes, not proof of
    encryption. Actual SDK encryption remains covered by the separate SDK/browser
    checks. No origin, thread, member, message or receipt is inserted by fixture SQL.
    """
    state = identity_runtime
    app, _, _ = compose(state, signed_tokens)
    with TestClient(
        app, base_url="https://clip-iisc.site", client=("192.0.2.27", 41000)
    ) as client:
        author = (
            signed_actor(client, signed_tokens, "author")
            if author_class == "regular"
            else temporary_actor(client, state)
        )
        responder = signed_actor(client, signed_tokens, "responder")
        stranger = signed_actor(client, signed_tokens, "stranger")
        headers = use_actor(client, author)
        created = client.post(
            "/wanted-requests",
            headers=headers,
            json={
                "title": "Synthetic signed-in conversation request",
                "description": "Controlled integration fixture only",
                "category_code": "books",
                "operation_id": str(uuid4()),
            },
        )
        assert created.status_code == 201, created.text
        origin = "/wanted-requests/" + created.json()["request_id"]
        assert (
            client.post(
                origin + "/conversations",
                headers=headers,
                json={"operation_id": str(uuid4())},
            ).status_code
            == 403
        )
        if author_class == "regular":
            temporary_responder = temporary_actor(client, state)
            assert (
                client.post(
                    origin + "/conversations",
                    headers=temporary_responder[2],
                    json={"operation_id": str(uuid4())},
                ).status_code
                == 403
            )
        headers = use_actor(client, responder)
        intent = {"operation_id": str(uuid4())}
        assert client.post(origin + "/conversations", json=intent).status_code == 403
        opened = client.post(origin + "/conversations", headers=headers, json=intent)
        assert opened.status_code == 201, opened.text
        retry = client.post(origin + "/conversations", headers=headers, json=intent)
        assert retry.status_code == 200 and retry.json()["created"] is False
        assert retry.json()["conversation_id"] == opened.json()["conversation_id"]
        chat = "/conversations/" + opened.json()["conversation_id"]
        for actor in (author, responder):
            headers = use_actor(client, actor)
            saved = client.put(
                "/me/conversation-key",
                headers=headers,
                json=public_bundle().model_dump(mode="json"),
            )
            assert saved.status_code == 200, saved.text
            assert saved.json()["user_id"] == actor[0]["user_id"]
        body = message_request().model_dump(mode="json")
        wrong_key = message_request(recipient_version=99).model_dump(mode="json")
        rejected_key = client.post(chat + "/messages", headers=headers, json=wrong_key)
        assert rejected_key.status_code == 422
        assert (
            rejected_key.json()["error"]["details"][0]["code"] == "invalid_key_version"
        )
        assert (
            client.post(
                chat + "/messages",
                headers=headers,
                json=body | {"sender_user_id": author[0]["user_id"]},
            ).status_code
            == 422
        )
        assert client.get(chat + "/entries").json()["items"] == []
        sent = client.post(chat + "/messages", headers=headers, json=body)
        assert sent.status_code == 201, sent.text
        assert sent.json()["sequence"] == 1
        assert sent.json()["sender_user_id"] == responder[0]["user_id"]
        replay = client.post(chat + "/messages", headers=headers, json=body)
        assert replay.status_code == 200 and replay.json() == sent.json()
        headers = use_actor(client, author)
        inbox = client.get("/conversations").json()["items"]
        assert len(inbox) == 1 and inbox[0]["unread_count"] == 1
        entries = client.get(chat + "/entries")
        assert entries.status_code == 200 and len(entries.json()["items"]) == 1
        assert client.get(chat + "/read-state").json()["own_last_read_sequence"] == 0
        # Fetching never acknowledges display; only the explicit owner write does.
        acknowledged = client.put(
            chat + "/read-state", headers=headers, json={"last_read_sequence": 1}
        )
        assert acknowledged.status_code == 200
        assert client.get("/conversations").json()["items"][0]["unread_count"] == 0
        headers = use_actor(client, stranger)
        assert client.get("/conversations").json()["items"] == []
        for suffix in ("", "/entries", "/keys", "/read-state"):
            assert client.get(chat + suffix).status_code == 404
        assert (
            client.post(chat + "/messages", headers=headers, json=body).status_code
            == 404
        )
        assert (
            client.put(
                chat + "/read-state", headers=headers, json={"last_read_sequence": 1}
            ).status_code
            == 404
        )
        headers = use_actor(client, responder)
        if terminal == "logout":
            assert client.delete("/auth/session", headers=headers).status_code == 204
            use_actor(client, responder)  # Even replaying the old cookie is denied.
        elif terminal == "revoked":
            state.service.revoke_account(UUID(responder[0]["user_id"]))
        else:
            state.clock[0] += timedelta(days=15)
        assert client.get(chat + "/entries").status_code == 401
        assert (
            client.post(chat + "/messages", headers=headers, json=body).status_code
            == 401
        )
        assert (
            client.put(
                chat + "/read-state", headers=headers, json={"last_read_sequence": 1}
            ).status_code
            == 401
        )
        # Read-only independent persistence audit: retries/denials cannot add
        # entries or membership. All writes above used the real HTTP workflows.
        with state.connect() as connection:
            conversation_id = UUID(opened.json()["conversation_id"])
            assert (
                connection.execute(
                    "SELECT count(*) FROM conversations.threads WHERE wanted_request_id = %s",
                    (UUID(created.json()["request_id"]),),
                ).fetchone()[0]
                == 1
            )
            assert (
                connection.execute(
                    "SELECT count(*) FROM conversations.entries WHERE conversation_id = %s",
                    (conversation_id,),
                ).fetchone()[0]
                == 1
            )
            assert (
                connection.execute(
                    "SELECT count(*) FROM conversations.members WHERE conversation_id = %s",
                    (conversation_id,),
                ).fetchone()[0]
                == 2
            )


def test_real_session_and_csrf_authorize_conversation_key_writes(
    identity_runtime, signed_tokens
):
    """Cookies establish actor identity; CSRF gates writes; logout revokes access."""
    app, _, _ = compose(identity_runtime, signed_tokens)
    with TestClient(
        app, base_url="https://clip-iisc.site", client=("192.0.2.27", 41000)
    ) as client:
        conversation_pool = app.state.database_pool
        assert not conversation_pool.closed
        assert client.get("/conversations").status_code == 401
        session = regular(client, signed_tokens)
        assert client.get("/conversations").status_code == 200
        assert client.get("/conversations").json()["items"] == []
        assert client.get("/me/conversation-key").json() is None
        body = public_bundle().model_dump(mode="json")
        assert client.put("/me/conversation-key", json=body).status_code == 403
        csrf = client.get("/auth/csrf").json()["csrf_token"]
        headers = HEADERS | {"X-CSRF-Token": csrf}
        saved = client.put("/me/conversation-key", json=body, headers=headers)
        assert saved.status_code == 200
        assert saved.json()["user_id"] == session["user_id"]
        assert client.get("/me/conversation-key").status_code == 200
        assert client.delete("/auth/session", headers=headers).status_code == 204
        assert client.get("/conversations").status_code == 401
    assert conversation_pool.closed
    assert app.state.database_pool is None
    assert app.state.conversations_public is None
