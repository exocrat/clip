"""Per-share 30-day cleanup preserves ordered, content-free conversation entries."""

from base64 import b64encode
from datetime import timedelta
from uuid import uuid4

import pytest

from app.contracts.domain_types import CipherEnvelope, ContactShareRequest, EntryQuery
from app.core.auth import require_caller
from app.core.errors import PublicError
from app.domains.conversations.cleanup import ConversationCleanup
from app.domains.conversations.messages import PostgresMessageOperations
from test_conversation_offers import offer_environment, register_members, snapshot
from test_conversation_messages import caller, run_scenario, seed_thread
from test_thread_creation import caller as request_caller


def contact_request(sdk_message_type="ciphertext"):
    """Build opaque ciphertext metadata; tests never create or print contact values."""
    operation_id = uuid4()
    return ContactShareRequest(
        operation_id=operation_id,
        envelope=CipherEnvelope(
            protocol_id="open-e2ee-signal",
            protocol_version="13.0.0",
            envelope_version=2,
            sdk_message_type=sdk_message_type,
            sdk_client_message_id=str(operation_id),
            client_timestamp_ms=1_000,
            sender_key_version=1,
            recipient_key_version=1,
            payload_base64=b64encode(b"opaque synthetic ciphertext").decode("ascii"),
        ),
    )


async def stored_share(pool, entry_id):
    """Inspect only marker and payload/subtype existence, never bytes."""
    async with pool.connection() as connection:
        return await (
            await connection.execute(
                "SELECT e.content_deleted_at, "
                "EXISTS(SELECT 1 FROM conversations.encrypted_payloads p WHERE p.entry_id=e.id), "
                "EXISTS(SELECT 1 FROM conversations.contact_shares s WHERE s.entry_id=e.id) "
                "FROM conversations.entries e WHERE e.id=%s",
                (entry_id,),
            )
        ).fetchone()


def test_independent_share_expiry_exact_cutoff_and_content_free_marker():
    async def scenario(pool):
        author, _, _, thread, _, _ = await seed_thread(pool)
        service = PostgresMessageOperations(pool)
        request = contact_request()
        result = await service.submit_contact_share(caller(author), thread, request)
        entry_id = result.entry.entry_id
        async with pool.connection() as connection:
            created = (
                await (
                    await connection.execute(
                        "SELECT created_at FROM conversations.entries WHERE id=%s",
                        (entry_id,),
                    )
                ).fetchone()
            )[0]
        now = created + timedelta(days=30)
        async with pool.connection() as connection:
            before_thread = await (
                await connection.execute(
                    "SELECT last_activity_at,next_sequence FROM conversations.threads WHERE id=%s",
                    (thread,),
                )
            ).fetchone()
        early = ConversationCleanup(pool, lambda: now - timedelta(microseconds=1))
        assert (await early.run_contact_shares(apply=True)).contact_shares == 0
        assert await stored_share(pool, entry_id) == (None, True, True)
        exact = ConversationCleanup(pool, lambda: now)
        dry = await exact.run_contact_shares()
        assert dry.dry_run and dry.contact_shares == 1 and dry.entries == 1
        assert await stored_share(pool, entry_id) == (None, True, True)
        applied = await exact.run_contact_shares(apply=True)
        assert not applied.dry_run and applied.contact_shares == 1
        assert await stored_share(pool, entry_id) == (now, False, False)
        assert (await exact.run_contact_shares(apply=True)).contact_shares == 0
        async with pool.connection() as connection:
            after_thread = await (
                await connection.execute(
                    "SELECT last_activity_at,next_sequence FROM conversations.threads WHERE id=%s",
                    (thread,),
                )
            ).fetchone()
        assert after_thread == before_thread
        page = await service.read_entries(caller(author), thread, EntryQuery())
        assert page.items[0].kind == "contact_share" and page.items[0].content_deleted
        assert page.items[0].envelope is None
        with pytest.raises(PublicError) as conflict:
            await service.submit_contact_share(caller(author), thread, request)
        assert conflict.value.spec.status == 409

    run_scenario(scenario)


@pytest.mark.parametrize("sdk_message_type", ["ciphertext", "prekey_bundle"])
def test_contact_share_http_write_is_member_scoped_encrypted_and_idempotent(
    sdk_message_type,
):
    async def scenario(pool):
        async with offer_environment(pool) as state:
            await register_members(state)
            before = await snapshot(pool, state.thread)
            body = contact_request(sdk_message_type).model_dump(mode="json")
            root = f"/conversations/{state.thread}/contact-shares"
            first = await state.client.post(root, json=body)
            assert first.status_code == 201
            data = first.json()
            assert (
                data["kind"] == "contact_share"
                and data["envelope"]["payload_base64"]
                == body["envelope"]["payload_base64"]
            )
            assert "synthetic" not in first.text
            assert (await state.client.post(root, json=body)).status_code == 200
            changed = {
                **body,
                "envelope": {
                    **body["envelope"],
                    "payload_base64": b64encode(b"different ciphertext").decode(
                        "ascii"
                    ),
                },
            }
            assert (await state.client.post(root, json=changed)).status_code == 409
            after = await snapshot(pool, state.thread)
            assert after[0] == before[0] + 1 and after[2] == before[2] + 1
            assert after[1] > before[1] and after[3:] == before[3:]
            async with pool.connection() as connection:
                state_counts = await (
                    await connection.execute(
                        "SELECT (SELECT count(*) FROM conversations.contact_shares WHERE entry_id=%s), "
                        "(SELECT count(*) FROM conversations.encrypted_payloads WHERE entry_id=%s)",
                        (data["entry_id"], data["entry_id"]),
                    )
                ).fetchone()
            assert state_counts == (1, 1)
            state.app.dependency_overrides[require_caller] = lambda: request_caller(
                uuid4()
            )
            assert (
                await state.client.post(
                    root, json=contact_request().model_dump(mode="json")
                )
            ).status_code == 404

    run_scenario(scenario)


def test_offer_selection_and_contact_share_work_together_through_real_apis():
    async def scenario(pool):
        async with offer_environment(pool) as state:
            await register_members(state)
            offer_body = {"amount_paise": 20_000, "operation_id": str(uuid4())}
            offer_url = state.url + "/offer"
            offer = await state.client.put(offer_url, json=offer_body)
            assert offer.status_code == 200
            assert offer.json()["amount_paise"] == 20_000
            after_offer = await snapshot(pool, state.thread)

            listing = await state.store.read_listing(state.listing)
            selection_body = {
                "buyer_id": str(state.buyer),
                "conversation_id": str(state.thread),
                "expected_revision": listing.revision,
                "operation_id": str(uuid4()),
            }
            state.app.dependency_overrides[require_caller] = lambda: caller(state.owner)
            selection_url = f"/listings/{state.listing}/selection"
            selected = await state.client.put(selection_url, json=selection_body)
            assert selected.status_code == 200
            assert selected.json()["selected_buyer_id"] == str(state.buyer)
            assert selected.json()["availability"] == "unavailable"
            assert (
                await state.client.put(selection_url, json=selection_body)
            ).json() == selected.json()

            state.app.dependency_overrides[require_caller] = lambda: caller(state.buyer)
            unavailable_offer = await state.client.put(offer_url, json=offer_body)
            assert unavailable_offer.status_code == 409
            assert unavailable_offer.json()["error"]["details"] == [
                {"field": "listing_id", "code": "unavailable"}
            ]
            assert await snapshot(pool, state.thread) == after_offer

            contact_body = contact_request().model_dump(mode="json")
            share_url = f"/conversations/{state.thread}/contact-shares"
            share = await state.client.post(share_url, json=contact_body)
            assert share.status_code == 201
            assert share.json()["kind"] == "contact_share"
            assert share.json()["sequence"] == after_offer[0]
            replay = await state.client.post(share_url, json=contact_body)
            assert replay.status_code == 200
            assert replay.json() == share.json()

            state.app.dependency_overrides[require_caller] = lambda: caller(state.owner)
            current_offer = await state.client.get(state.read_url)
            assert current_offer.status_code == 200
            assert current_offer.json() == offer.json()
            entries = await state.client.get(f"/conversations/{state.thread}/entries")
            assert [entry["kind"] for entry in entries.json()["items"]] == [
                "contact_share"
            ]
            assert entries.json()["items"][0]["sequence"] == after_offer[0]
            assert entries.json()["scanned_through_sequence"] == after_offer[0]

    run_scenario(scenario)


def test_rejected_contact_envelope_does_not_echo_or_log_payload(caplog):
    async def scenario(pool):
        async with offer_environment(pool) as state:
            marker = b"synthetic-private-test-marker"
            encoded = b64encode(marker).decode("ascii")
            body = contact_request().model_dump(mode="json")
            body["envelope"]["sdk_message_type"] = "retry_request"
            body["envelope"]["payload_base64"] = encoded
            with caplog.at_level("DEBUG"):
                response = await state.client.post(
                    f"/conversations/{state.thread}/contact-shares", json=body
                )
            assert response.status_code == 422
            assert marker.decode("ascii") not in response.text
            assert encoded not in response.text
            assert marker.decode("ascii") not in caplog.text
            assert encoded not in caplog.text

    run_scenario(scenario)


def test_contact_share_cleanup_rolls_back_payload_subtype_and_marker_together():
    async def scenario(pool):
        author, _, _, thread, _, _ = await seed_thread(pool)
        result = await PostgresMessageOperations(pool).submit_contact_share(
            caller(author), thread, contact_request()
        )
        entry_id = result.entry.entry_id
        async with pool.connection() as connection:
            created = (
                await (
                    await connection.execute(
                        "SELECT created_at FROM conversations.entries WHERE id=%s",
                        (entry_id,),
                    )
                ).fetchone()
            )[0]

        class FailingShareCleanup(ConversationCleanup):
            """Fail after cleanup SQL to verify the transaction restores the full graph."""

            @staticmethod
            async def _delete_contact_share(connection, target_id, now):
                await ConversationCleanup._delete_contact_share(
                    connection, target_id, now
                )
                raise RuntimeError("synthetic cleanup failure")

        with pytest.raises(PublicError):
            await FailingShareCleanup(
                pool, lambda: created + timedelta(days=30)
            ).run_contact_shares(apply=True)
        assert await stored_share(pool, entry_id) == (None, True, True)

    run_scenario(scenario)
