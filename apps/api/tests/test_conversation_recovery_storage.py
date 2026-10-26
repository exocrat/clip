"""Recovery schema checks on the disposable CN-01 database, with opaque fixtures.

Recovery writes are rolled back after checking deferred integrity. HTTP v2 and
SDK recovery integration are later checkpoints, not claims of these SQL tests.
"""

from pathlib import Path
from uuid import uuid4

import pytest
from psycopg import IntegrityError, errors

from app.domains.conversations.messages import PostgresMessageOperations
from test_conversation_messages import (
    caller,
    message_request,
    run_scenario,
    seed_thread,
)

MIGRATION = Path("database/migrations/20261026090300_conversation_recovery_storage.sql")


async def original_message(pool):
    """Commit a v1 author message; new recovery storage must preserve this path."""
    author, recipient, _, thread, author_key, recipient_key = await seed_thread(pool)
    sent = await PostgresMessageOperations(pool).submit_message(
        caller(author), thread, message_request(timestamp=1000)
    )
    return {
        "author": author,
        "recipient": recipient,
        "thread": thread,
        "entry": sent.entry.entry_id,
        "author_key": author_key,
        "recipient_key": recipient_key,
    }


async def bind_family(connection, original, family, request_id):
    """Stage a binding whose first request must exist before transaction commit."""
    await connection.execute(
        "INSERT INTO conversations.recovery_families "
        "(requester_id, family_id, conversation_id, original_entry_id, first_request_entry_id) "
        "VALUES (%s, %s, %s, %s, %s)",
        (
            original["recipient"],
            family,
            original["thread"],
            original["entry"],
            request_id,
        ),
    )


async def control(
    connection, original, family, recovery_kind, *, attempt=1, entry_id=None, **changes
):
    """Write one raw v2 storage fixture, including its immutable opaque payload."""
    data = {
        "id": entry_id or uuid4(),
        "thread": original["thread"],
        "sender": (
            original["recipient"]
            if recovery_kind == "retry-request"
            else original["author"]
        ),
        "recipient": (
            original["author"]
            if recovery_kind == "retry-request"
            else original["recipient"]
        ),
        "operation": uuid4(),
        "sdk_id": f"{family}:{recovery_kind}" + (f":{attempt}" if attempt != 1 else ""),
        "target": original["entry"],
        "requester": original["recipient"],
        "family": family,
        "attempt": attempt,
        "kind": recovery_kind,
        "sdk_type": (
            "retry_request" if recovery_kind == "retry-request" else "ciphertext"
        ),
        "version": 2,
        "timestamp": 1000,
        "sender_key": original["author_key"] if recovery_kind == "resend" else None,
        "recipient_key": (
            original["recipient_key"] if recovery_kind == "resend" else None
        ),
        **changes,
    }
    await connection.execute(
        "INSERT INTO conversations.entries "
        "(id, conversation_id, sender_id, client_operation_id, kind, recipient_id, "
        "sdk_client_message_id, recovery_for_entry_id, recovery_requester_id, "
        "recovery_family_id, recovery_attempt, recovery_kind) "
        "VALUES (%(id)s, %(thread)s, %(sender)s, %(operation)s, 'protocol_control', "
        "%(recipient)s, %(sdk_id)s, %(target)s, %(requester)s, %(family)s, %(attempt)s, %(kind)s)",
        data,
    )
    await connection.execute(
        "INSERT INTO conversations.encrypted_payloads "
        "(entry_id, protocol_id, protocol_version, envelope_version, sdk_message_type, "
        "client_timestamp_ms, sender_key_version_id, recipient_key_version_id, envelope) "
        "VALUES (%(id)s, 'open-e2ee-signal', '13.0.0', %(version)s, %(sdk_type)s, "
        "%(timestamp)s, %(sender_key)s, %(recipient_key)s, %(payload)s)",
        data | {"payload": b"synthetic opaque recovery bytes"},
    )
    return data["id"]


def test_recovery_migration_roundtrip_preserves_existing_v1_ciphertext():
    async def scenario(pool):
        original = await original_message(pool)
        up, down = MIGRATION.read_text().split("-- migrate:down", 1)
        async with pool.connection() as connection:
            async with connection.transaction(force_rollback=True):
                await connection.execute(down)
                cursor = await connection.execute(
                    "SELECT envelope FROM conversations.encrypted_payloads WHERE entry_id = %s",
                    (original["entry"],),
                )
                before = (await cursor.fetchone())[0]
                await connection.execute(up)
                cursor = await connection.execute(
                    "SELECT entry.sdk_client_message_id = entry.client_operation_id::text, "
                    "payload.envelope FROM conversations.entries entry "
                    "JOIN conversations.encrypted_payloads payload ON payload.entry_id = entry.id "
                    "WHERE entry.id = %s",
                    (original["entry"],),
                )
                restored, after = await cursor.fetchone()
                assert restored is True
                assert after == before

    run_scenario(scenario)


def test_request_resend_null_and_second_attempt_preserve_independent_sdk_ids():
    async def scenario(pool):
        original = await original_message(pool)
        family, first = uuid4(), uuid4()
        async with pool.connection() as connection:
            async with connection.transaction(force_rollback=True):
                await bind_family(connection, original, family, first)
                await control(
                    connection, original, family, "retry-request", entry_id=first
                )
                await control(connection, original, family, "resend")
                await control(connection, original, family, "null")
                await control(connection, original, family, "retry-request", attempt=2)
                await control(connection, original, family, "resend", attempt=2)
                await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
                cursor = await connection.execute(
                    "SELECT sequence, sdk_client_message_id, client_operation_id::text, "
                    "recovery_for_entry_id, kind FROM conversations.entries "
                    "WHERE recovery_family_id = %s ORDER BY sequence",
                    (family,),
                )
                rows = await cursor.fetchall()
                assert [row[0] for row in rows] == [2, 3, 4, 5, 6]
                assert [row[1] for row in rows] == [
                    f"{family}:retry-request",
                    f"{family}:resend",
                    f"{family}:null",
                    f"{family}:retry-request:2",
                    f"{family}:resend:2",
                ]
                assert all(
                    row[1] != row[2]
                    and row[3] == original["entry"]
                    and row[4] == "protocol_control"
                    for row in rows
                )
                cursor = await connection.execute(
                    "SELECT count(*) FROM conversations.notification_intents WHERE conversation_id = %s",
                    (original["thread"],),
                )
                assert (await cursor.fetchone())[0] == 1

    run_scenario(scenario)


@pytest.mark.parametrize(
    "change",
    [
        {"sdk_id": "invalid:retry-request"},
        {"sdk_id": "x" * 129},
        {"attempt": 0},
        {"attempt": 9_007_199_254_740_992},
        {"kind": None},
        {"version": 1},
        {"sdk_type": "ciphertext"},
    ],
)
def test_recovery_rejects_malformed_metadata_and_v1_claims(change):
    async def scenario(pool):
        original = await original_message(pool)
        family, first = uuid4(), uuid4()
        async with pool.connection() as connection:
            async with connection.transaction(force_rollback=True):
                await bind_family(connection, original, family, first)
                with pytest.raises(IntegrityError):
                    async with connection.transaction():
                        await control(
                            connection,
                            original,
                            family,
                            "retry-request",
                            entry_id=first,
                            **change,
                        )

    run_scenario(scenario)


def test_recovery_requires_atomic_first_request_and_correct_requester():
    async def scenario(pool):
        original = await original_message(pool)
        family, first = uuid4(), uuid4()
        async with pool.connection() as connection:
            async with connection.transaction(force_rollback=True):
                await bind_family(connection, original, family, first)
                with pytest.raises(IntegrityError):
                    async with connection.transaction():
                        await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
                with pytest.raises(errors.CheckViolation):
                    async with connection.transaction():
                        await control(connection, original, family, "resend")
                with pytest.raises(errors.CheckViolation):
                    async with connection.transaction():
                        await control(
                            connection,
                            original,
                            family,
                            "retry-request",
                            sender=original["author"],
                            recipient=original["recipient"],
                        )
                await control(
                    connection, original, family, "retry-request", entry_id=first
                )
                with pytest.raises(errors.CheckViolation):
                    async with connection.transaction():
                        await control(connection, original, family, "resend", attempt=2)
                await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

    run_scenario(scenario)


def test_recovery_sdk_id_uniqueness_and_immutable_bindings():
    async def scenario(pool):
        original = await original_message(pool)
        family, first = uuid4(), uuid4()
        async with pool.connection() as connection:
            async with connection.transaction(force_rollback=True):
                await bind_family(connection, original, family, first)
                await control(
                    connection, original, family, "retry-request", entry_id=first
                )
                # A fresh API UUID cannot reuse an existing ordinary SDK ID,
                # even when it is not a recovery-family attempt.
                with pytest.raises(errors.UniqueViolation) as duplicate:
                    async with connection.transaction():
                        await connection.execute(
                            "INSERT INTO conversations.entries "
                            "(id, conversation_id, sender_id, client_operation_id, kind, sdk_client_message_id) "
                            "SELECT %s, conversation_id, sender_id, %s, 'message', sdk_client_message_id "
                            "FROM conversations.entries WHERE id = %s",
                            (uuid4(), uuid4(), original["entry"]),
                        )
                assert duplicate.value.diag.constraint_name == "entries_sdk_id_unique"
                for query, params in (
                    (
                        "UPDATE conversations.entries SET sdk_client_message_id = %s WHERE id = %s",
                        (str(uuid4()), first),
                    ),
                    (
                        "UPDATE conversations.recovery_families SET original_entry_id = %s WHERE family_id = %s",
                        (first, family),
                    ),
                    (
                        "DELETE FROM conversations.recovery_families WHERE family_id = %s",
                        (family,),
                    ),
                ):
                    with pytest.raises(errors.CheckViolation):
                        async with connection.transaction():
                            await connection.execute(query, params)
                with pytest.raises(errors.UniqueViolation):
                    async with connection.transaction():
                        await control(connection, original, family, "retry-request")
                await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

    run_scenario(scenario)


def test_recovery_rejects_wrong_target_peer_context_and_purged_original():
    async def scenario(pool):
        original = await original_message(pool)
        other = await original_message(pool)
        family, first = uuid4(), uuid4()
        async with pool.connection() as connection:
            async with connection.transaction(force_rollback=True):
                with pytest.raises(errors.CheckViolation):
                    async with connection.transaction():
                        await bind_family(
                            connection,
                            original | {"entry": other["entry"]},
                            family,
                            first,
                        )
                await bind_family(connection, original, family, first)
                await control(
                    connection, original, family, "retry-request", entry_id=first
                )
                for change in (
                    {"target": other["entry"]},
                    {"timestamp": 1001},
                    {"sender_key": original["recipient_key"]},
                    {"sender": original["recipient"], "recipient": original["author"]},
                ):
                    with pytest.raises(IntegrityError):
                        async with connection.transaction():
                            await control(
                                connection, original, family, "resend", **change
                            )
                await connection.execute(
                    "DELETE FROM conversations.encrypted_payloads WHERE entry_id = %s",
                    (original["entry"],),
                )
                await connection.execute(
                    "UPDATE conversations.entries SET content_deleted_at = clock_timestamp() WHERE id = %s",
                    (original["entry"],),
                )
                with pytest.raises(errors.CheckViolation):
                    async with connection.transaction():
                        await control(
                            connection, original, family, "retry-request", attempt=2
                        )
                await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

    run_scenario(scenario)


def test_recovery_honors_retirement_marker_and_refuses_destructive_rollback():
    async def scenario(pool):
        original = await original_message(pool)
        family, first = uuid4(), uuid4()
        async with pool.connection() as connection:
            async with connection.transaction(force_rollback=True):
                await bind_family(connection, original, family, first)
                await control(
                    connection, original, family, "retry-request", entry_id=first
                )
                down = MIGRATION.read_text().split("-- migrate:down", 1)[1]
                with pytest.raises(errors.RaiseException):
                    async with connection.transaction():
                        await connection.execute(down)
                await connection.execute(
                    "UPDATE conversations.threads SET participant_writes_disabled_at = clock_timestamp() WHERE id = %s",
                    (original["thread"],),
                )
                with pytest.raises(errors.CheckViolation):
                    async with connection.transaction():
                        await control(connection, original, family, "resend")
                with pytest.raises(errors.CheckViolation):
                    async with connection.transaction():
                        await bind_family(connection, original, uuid4(), uuid4())
                await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

    run_scenario(scenario)
