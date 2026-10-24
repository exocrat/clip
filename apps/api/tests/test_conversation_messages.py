"""Database-backed message/read-state tests run only on the fresh CN-01 test DB."""

import asyncio
from base64 import b64encode
from datetime import UTC, datetime, timedelta
import os
from uuid import UUID, uuid4

import pytest
from psycopg_pool import AsyncConnectionPool

from app.contracts.domain_types import (
    CipherEnvelope,
    EntryQuery,
    MessageRequest,
    ReadAcknowledgement,
)
from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.domains.conversations.messages import PostgresMessageOperations

TEST_DATABASE_DSN = os.environ.get("CLIP_TEST_DATABASE_DSN")


def run_scenario(scenario) -> None:
    """Give each integration scenario an isolated async pool on the disposable DB."""
    if TEST_DATABASE_DSN is None:
        pytest.skip("run through scripts/check_conversations_retirement.py")

    async def run() -> None:
        pool = AsyncConnectionPool(
            conninfo=TEST_DATABASE_DSN,
            min_size=0,
            max_size=4,
            open=False,
        )
        await pool.open(wait=True)
        try:
            await scenario(pool)
        finally:
            await pool.close()

    asyncio.run(run())


def caller(user_id: UUID) -> CallerContext:
    """Create a short-lived synthetic Identity context for isolated tests only."""
    return CallerContext(
        user_id=user_id,
        account_class="regular",
        valid_until=datetime.now(UTC) + timedelta(hours=1),
    )


async def seed_thread(
    pool, *, responder_id: UUID | None = None
) -> tuple[UUID, UUID, UUID, UUID, UUID, UUID]:
    """Create two synthetic members, an owned request thread, and matching public keys."""
    author_id, responder_id, request_id, conversation_id = (
        uuid4(),
        responder_id or uuid4(),
        uuid4(),
        uuid4(),
    )
    author_key_id, responder_key_id = uuid4(), uuid4()
    async with pool.connection() as connection:
        async with connection.transaction():
            await connection.execute(
                "INSERT INTO identity.users (id, account_class, status) "
                "VALUES (%s, 'regular', 'active'), (%s, 'regular', 'active') "
                "ON CONFLICT (id) DO NOTHING",
                (author_id, responder_id),
            )
            cursor = await connection.execute(
                "SELECT id FROM listings.categories WHERE code = 'other'"
            )
            category_id = (await cursor.fetchone())[0]
            await connection.execute(
                "INSERT INTO search.wanted_requests "
                "(id, author_id, title, description, category_id, status) "
                "VALUES (%s, %s, 'Synthetic request', 'Test-only request', %s, 'open')",
                (request_id, author_id, category_id),
            )
            await connection.execute(
                "INSERT INTO conversations.threads "
                "(id, wanted_request_id, initiator_id, counterparty_id) "
                "VALUES (%s, %s, %s, %s)",
                (conversation_id, request_id, responder_id, author_id),
            )
            await connection.execute(
                "INSERT INTO conversations.members (conversation_id, user_id) "
                "VALUES (%s, %s), (%s, %s)",
                (conversation_id, responder_id, conversation_id, author_id),
            )
            await connection.execute(
                "INSERT INTO conversations.public_key_versions "
                "(id, user_id, version, public_key_material, protocol_id) "
                "VALUES (%s, %s, 1, %s, 'open-e2ee-signal'), "
                "(%s, %s, 1, %s, 'open-e2ee-signal') ON CONFLICT DO NOTHING",
                (
                    author_key_id,
                    author_id,
                    b"synthetic-author-public-key",
                    responder_key_id,
                    responder_id,
                    b"synthetic-responder-public-key",
                ),
            )
    return (
        author_id,
        responder_id,
        request_id,
        conversation_id,
        author_key_id,
        responder_key_id,
    )


def message_request(
    *,
    operation_id: UUID | None = None,
    payload: bytes = b"opaque-ciphertext",
    sdk_type: str = "ciphertext",
    sender_version: int | None = 1,
    recipient_version: int | None = 1,
    timestamp: int = 1_000,
) -> MessageRequest:
    """Build a synthetic opaque envelope; no fixture contains real text or keys."""
    envelope = CipherEnvelope(
        protocol_id="open-e2ee-signal",
        protocol_version="13.0.0",
        envelope_version=1,
        sdk_message_type=sdk_type,
        client_timestamp_ms=timestamp,
        sender_key_version=sender_version,
        recipient_key_version=recipient_version,
        payload_base64=b64encode(payload).decode("ascii"),
    )
    return MessageRequest(envelope=envelope, operation_id=operation_id or uuid4())


def test_wanted_request_author_can_send_and_retrieve_participant_messages():
    async def scenario(pool):
        author, responder, _request, conversation, _author_key, _responder_key = (
            await seed_thread(pool)
        )
        operations = PostgresMessageOperations(pool)

        author_send = await operations.submit_message(
            caller(author),
            conversation,
            message_request(payload=b"opaque-author-ciphertext", timestamp=10),
        )
        responder_send = await operations.submit_message(
            caller(responder),
            conversation,
            message_request(payload=b"opaque-responder-ciphertext", timestamp=11),
        )

        assert [author_send.entry.sequence, responder_send.entry.sequence] == [1, 2]
        author_view = await operations.read_entries(
            caller(author), conversation, EntryQuery()
        )
        responder_view = await operations.read_entries(
            caller(responder), conversation, EntryQuery()
        )
        for page in (author_view, responder_view):
            assert [entry.sequence for entry in page.items] == [1, 2]
            assert [entry.sender_user_id for entry in page.items] == [author, responder]
            assert [entry.envelope.payload_base64 for entry in page.items] == [
                b64encode(b"opaque-author-ciphertext").decode("ascii"),
                b64encode(b"opaque-responder-ciphertext").decode("ascii"),
            ]

    run_scenario(scenario)


def test_message_retry_ordering_private_controls_and_display_read_state():
    async def scenario(pool):
        alice, bob, _request, conversation, _alice_key, _bob_key = await seed_thread(
            pool
        )
        operations = PostgresMessageOperations(pool)
        first_request = message_request(timestamp=10)
        first = await operations.submit_message(
            caller(alice), conversation, first_request
        )
        replay = await operations.submit_message(
            caller(alice), conversation, first_request
        )
        assert first.entry.sequence == 1
        assert first.replayed is False
        assert replay.replayed is True
        assert replay.entry == first.entry

        changed = message_request(
            operation_id=first_request.operation_id,
            payload=b"different-opaque-bytes",
            timestamp=10,
        )
        with pytest.raises(PublicError) as conflict:
            await operations.submit_message(caller(alice), conversation, changed)
        assert conflict.value.spec.status == 409

        alice_page = await operations.read_entries(
            caller(alice), conversation, EntryQuery()
        )
        bob_page = await operations.read_entries(
            caller(bob), conversation, EntryQuery()
        )
        assert [entry.sequence for entry in alice_page.items] == [1]
        assert [entry.sequence for entry in bob_page.items] == [1]
        assert (
            alice_page.scanned_through_sequence
            == bob_page.scanned_through_sequence
            == 1
        )

        control_request = message_request(
            sdk_type="retry_request",
            sender_version=None,
            recipient_version=None,
            payload=b"opaque-retry-control",
        )
        control = await operations.submit_message(
            caller(alice), conversation, control_request
        )
        assert control.entry.kind == "protocol_control"
        assert control.entry.sequence == 2
        sender_page = await operations.read_entries(
            caller(alice),
            conversation,
            EntryQuery(after_sequence=1),
        )
        recipient_page = await operations.read_entries(
            caller(bob),
            conversation,
            EntryQuery(after_sequence=1),
        )
        assert sender_page.items == []
        assert sender_page.scanned_through_sequence == 2
        assert sender_page.has_more is False
        assert [entry.kind for entry in recipient_page.items] == ["protocol_control"]
        assert recipient_page.items[0].envelope.payload_base64 == b64encode(
            b"opaque-retry-control"
        ).decode("ascii")

        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT recipient_id FROM conversations.entries WHERE id = %s",
                (control.entry.entry_id,),
            )
            assert (await cursor.fetchone())[0] == bob
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.notification_intents "
                "WHERE conversation_id = %s AND event_kind = 'unread_reminder'",
                (conversation,),
            )
            assert (await cursor.fetchone())[0] == 1

        before_state = await operations.read_state(caller(bob), conversation)
        assert before_state.own_last_read_sequence == 0
        before_activity = None
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT last_activity_at FROM conversations.threads WHERE id = %s",
                (conversation,),
            )
            before_activity = (await cursor.fetchone())[0]
        acknowledged = await operations.acknowledge_read(
            caller(bob), conversation, ReadAcknowledgement(last_read_sequence=1)
        )
        assert acknowledged.own_last_read_sequence == 1
        assert (
            await operations.read_state(caller(alice), conversation)
        ).own_last_read_sequence == 0
        with pytest.raises(PublicError) as future:
            await operations.acknowledge_read(
                caller(bob), conversation, ReadAcknowledgement(last_read_sequence=3)
            )
        assert future.value.spec.status == 422
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT last_activity_at FROM conversations.threads WHERE id = %s",
                (conversation,),
            )
            assert (await cursor.fetchone())[0] == before_activity

    run_scenario(scenario)


def test_nonparticipant_id_substitution_and_wrong_key_version_fail_safely():
    async def scenario(pool):
        alice, _bob, _request, conversation, _alice_key, _bob_key = await seed_thread(
            pool
        )
        stranger = uuid4()
        async with pool.connection() as connection:
            await connection.execute(
                "INSERT INTO identity.users (id, account_class, status) "
                "VALUES (%s, 'regular', 'active')",
                (stranger,),
            )
        operations = PostgresMessageOperations(pool)
        for action in (
            lambda: operations.read_state(caller(stranger), conversation),
            lambda: operations.read_entries(
                caller(stranger), conversation, EntryQuery()
            ),
        ):
            with pytest.raises(PublicError) as denied:
                await action()
            assert denied.value.spec.status == 404

        wrong_key = message_request(recipient_version=9)
        with pytest.raises(PublicError) as invalid:
            await operations.submit_message(caller(alice), conversation, wrong_key)
        assert invalid.value.spec.status == 422

        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.entries WHERE conversation_id = %s",
                (conversation,),
            )
            assert (await cursor.fetchone())[0] == 0

    run_scenario(scenario)


def test_operation_id_is_global_per_sender_and_content_is_never_stored_as_plaintext():
    async def scenario(pool):
        alice, _bob, _request, conversation, _alice_key, _bob_key = await seed_thread(
            pool
        )
        _author2, _responder2, _request2, other_conversation, _key_a, _key_b = (
            await seed_thread(pool, responder_id=alice)
        )
        operations = PostgresMessageOperations(pool)
        operation_id = uuid4()
        payload = b"synthetic-ciphertext-only"
        first = await operations.submit_message(
            caller(alice),
            conversation,
            message_request(operation_id=operation_id, payload=payload),
        )
        with pytest.raises(PublicError) as reused:
            await operations.submit_message(
                caller(alice),
                other_conversation,
                message_request(operation_id=operation_id, payload=payload),
            )
        assert reused.value.spec.status == 409
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT entry.kind, payload.envelope, entry.client_operation_id "
                "FROM conversations.entries AS entry "
                "JOIN conversations.encrypted_payloads AS payload ON payload.entry_id = entry.id "
                "WHERE entry.id = %s",
                (first.entry.entry_id,),
            )
            row = await cursor.fetchone()
            assert row == ("message", payload, operation_id)
        assert other_conversation != conversation

    run_scenario(scenario)


def test_message_write_observes_no_write_marker_but_exact_retry_stays_idempotent():
    async def scenario(pool):
        alice, _bob, _request, conversation, _alice_key, _bob_key = await seed_thread(
            pool
        )
        operations = PostgresMessageOperations(pool)
        request = message_request()
        first = await operations.submit_message(caller(alice), conversation, request)
        async with pool.connection() as connection:
            await connection.execute(
                "UPDATE conversations.threads SET participant_writes_blocked_at = clock_timestamp() "
                "WHERE id = %s",
                (conversation,),
            )
        replay = await operations.submit_message(caller(alice), conversation, request)
        assert replay.replayed is True
        assert replay.entry.sequence == first.entry.sequence
        with pytest.raises(PublicError) as blocked:
            await operations.submit_message(
                caller(alice), conversation, message_request()
            )
        assert blocked.value.spec.status == 409

    run_scenario(scenario)
