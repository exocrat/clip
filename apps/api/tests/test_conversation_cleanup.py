"""Retention checks on the harness-owned disposable PostgreSQL, never a live DB."""

from datetime import timedelta
from uuid import uuid4

import pytest

from app.contracts.domain_types import EntryQuery
from app.core.errors import PublicError
from app.domains.conversations.cleanup import ConversationCleanup
from app.domains.conversations.messages import PostgresMessageOperations
from test_conversation_messages import (
    caller,
    message_request,
    run_scenario,
    seed_thread,
)


async def seeded_message(pool):
    """Commit one opaque message and capture its authoritative activity clock."""
    author, recipient, _, thread, _, _ = await seed_thread(pool)
    request = message_request()
    result = await PostgresMessageOperations(pool).submit_message(
        caller(author), thread, request
    )
    async with pool.connection() as connection:
        row = await (
            await connection.execute(
                "SELECT last_activity_at,next_sequence FROM conversations.threads WHERE id=%s",
                (thread,),
            )
        ).fetchone()
    return author, recipient, thread, result.entry.entry_id, request, row


async def retained(pool, entry):
    """Return marker/payload state without exposing any content."""
    async with pool.connection() as connection:
        return await (
            await connection.execute(
                "SELECT content_deleted_at,EXISTS(SELECT 1 FROM conversations.encrypted_payloads p "
                "WHERE p.entry_id=e.id) FROM conversations.entries e WHERE id=%s",
                (entry,),
            )
        ).fetchone()


def test_exact_cutoff_dry_run_idempotency_and_content_free_retry():
    async def scenario(pool):
        author, _, thread, entry, request, before = await seeded_message(pool)
        now = before[0] + timedelta(days=90)
        service = ConversationCleanup(pool, lambda: now - timedelta(microseconds=1))
        await service.run(apply=True, batch_size=1000)
        assert await retained(pool, entry) == (None, True)
        service = ConversationCleanup(pool, lambda: now)
        dry = await service.run(batch_size=1000)
        assert dry.dry_run and dry.entries >= 1
        assert await retained(pool, entry) == (None, True)
        applied = await service.run(apply=True, batch_size=1000)
        assert not applied.dry_run and applied.entries >= 1
        assert await retained(pool, entry) == (now, False)
        assert (await service.run(apply=True, batch_size=1000)).entries == 0
        async with pool.connection() as connection:
            row = await (
                await connection.execute(
                    "SELECT last_activity_at,next_sequence FROM conversations.threads WHERE id=%s",
                    (thread,),
                )
            ).fetchone()
            assert row == before
            assert (
                await (
                    await connection.execute(
                        "SELECT count(*) FROM conversations.members WHERE conversation_id=%s",
                        (thread,),
                    )
                ).fetchone()
            )[0] == 2
        page = await PostgresMessageOperations(pool).read_entries(
            caller(author), thread, EntryQuery()
        )
        assert page.items[0].content_deleted and page.items[0].envelope is None
        # The reviewed contract returns 409 once opaque-byte equality is no
        # longer provable. The retained operation ID prevents recreation.
        with pytest.raises(PublicError) as conflict:
            await PostgresMessageOperations(pool).submit_message(
                caller(author), thread, request
            )
        assert conflict.value.spec.status == 409
        assert await retained(pool, entry) == (now, False)

    run_scenario(scenario)


def test_activity_rechecked_after_candidate_selection():
    async def scenario(pool):
        author, _, thread, entry, _, before = await seeded_message(pool)

        class ConcurrentWrite(ConversationCleanup):
            """Commit a real message after the advisory scan, before cleanup's lock."""

            async def _purge_thread(self, thread_id, cutoff, now, apply):
                if thread_id == thread:
                    await PostgresMessageOperations(pool).submit_message(
                        caller(author), thread, message_request(timestamp=2000)
                    )
                return await super()._purge_thread(thread_id, cutoff, now, apply)

        service = ConcurrentWrite(pool, lambda: before[0] + timedelta(days=90))
        await service.run(apply=True, batch_size=1000)
        assert await retained(pool, entry) == (None, True)

    run_scenario(scenario)


def test_thread_transaction_rolls_back_partial_payload_removal():
    async def scenario(pool):
        _, _, thread, entry, _, before = await seeded_message(pool)

        class FailingCleanup(ConversationCleanup):
            """Fail after mutations to prove the entire thread transaction rolls back."""

            async def _purge_content(self, connection, thread_id, now):
                await super()._purge_content(connection, thread_id, now)
                if thread_id == thread:
                    raise RuntimeError("Synthetic failure")

        with pytest.raises(PublicError):
            await FailingCleanup(pool, lambda: before[0] + timedelta(days=90)).run(
                apply=True, batch_size=1000
            )
        assert await retained(pool, entry) == (None, True)

    run_scenario(scenario)


def test_offer_pointer_and_history_purge_preserves_offer_guard():
    async def scenario(pool):
        from test_thread_creation import seed_users_and_listing

        owner, buyer, listing = await seed_users_and_listing(pool)
        thread, entry, offer = uuid4(), uuid4(), uuid4()
        async with pool.connection() as connection:
            async with connection.transaction():
                await connection.execute(
                    "INSERT INTO conversations.threads (id,listing_id,initiator_id,counterparty_id) VALUES (%s,%s,%s,%s)",
                    (thread, listing, buyer, owner),
                )
                await connection.execute(
                    "INSERT INTO conversations.members (conversation_id,user_id) VALUES (%s,%s),(%s,%s)",
                    (thread, buyer, thread, owner),
                )
                await connection.execute(
                    "INSERT INTO conversations.entries (id,conversation_id,sender_id,client_operation_id,kind) VALUES (%s,%s,%s,%s,'offer')",
                    (entry, thread, buyer, uuid4()),
                )
                await connection.execute(
                    "INSERT INTO conversations.offers (id,conversation_id,buyer_id,current_revision,next_revision) VALUES (%s,%s,%s,1,2)",
                    (offer, thread, buyer),
                )
                await connection.execute(
                    "INSERT INTO conversations.offer_revisions (offer_id,revision,entry_id,amount_paise,status) VALUES (%s,1,%s,100,'submitted')",
                    (offer, entry),
                )
                activity = (
                    await (
                        await connection.execute(
                            "SELECT last_activity_at FROM conversations.threads WHERE id=%s",
                            (thread,),
                        )
                    ).fetchone()
                )[0]
        now = activity + timedelta(days=90)
        await ConversationCleanup(pool, lambda: now).run(apply=True, batch_size=1000)
        async with pool.connection() as connection:
            row = await (
                await connection.execute(
                    "SELECT current_revision,next_revision,history_deleted_at FROM conversations.offers WHERE id=%s",
                    (offer,),
                )
            ).fetchone()
            assert row == (None, 2, now)
            assert (
                await (
                    await connection.execute(
                        "SELECT count(*) FROM conversations.offer_revisions WHERE offer_id=%s",
                        (offer,),
                    )
                ).fetchone()
            )[0] == 0
        assert await retained(pool, entry) == (now, False)

    run_scenario(scenario)


def test_recovery_references_survive_content_purge():
    async def scenario(pool):
        from test_conversation_recovery_storage import (
            original_message,
            bind_family,
            control,
        )

        original = await original_message(pool)
        family, request_id = uuid4(), uuid4()
        async with pool.connection() as connection:
            async with connection.transaction():
                await bind_family(connection, original, family, request_id)
                await control(
                    connection, original, family, "retry-request", entry_id=request_id
                )
                await control(connection, original, family, "null")
            activity = (
                await (
                    await connection.execute(
                        "SELECT last_activity_at FROM conversations.threads WHERE id=%s",
                        (original["thread"],),
                    )
                ).fetchone()
            )[0]
        await ConversationCleanup(pool, lambda: activity + timedelta(days=90)).run(
            apply=True, batch_size=1000
        )
        async with pool.connection() as connection:
            assert (
                await (
                    await connection.execute(
                        "SELECT count(*) FROM conversations.recovery_families WHERE family_id=%s",
                        (family,),
                    )
                ).fetchone()
            )[0] == 1
            assert (
                await (
                    await connection.execute(
                        "SELECT count(*) FROM conversations.entries WHERE conversation_id=%s AND content_deleted_at IS NOT NULL",
                        (original["thread"],),
                    )
                ).fetchone()
            )[0] == 3
        assert (await retained(pool, original["entry"]))[1] is False

    run_scenario(scenario)


def test_purge_holds_thread_write_lock_and_allows_later_new_message():
    async def scenario(pool):
        import asyncio
        from psycopg.errors import LockNotAvailable

        author, _, thread, entry, _, before = await seeded_message(pool)
        acquired, release = asyncio.Event(), asyncio.Event()

        class PausingCleanup(ConversationCleanup):
            """Pause inside the locked mutation to probe its actual DB lock."""

            async def _purge_content(self, connection, thread_id, now):
                if thread_id == thread:
                    acquired.set()
                    await release.wait()
                await super()._purge_content(connection, thread_id, now)

        task = asyncio.create_task(
            PausingCleanup(pool, lambda: before[0] + timedelta(days=90)).run(
                apply=True, batch_size=1000
            )
        )
        try:
            await asyncio.wait_for(acquired.wait(), timeout=5)
            async with pool.connection() as connection:
                with pytest.raises(LockNotAvailable):
                    async with connection.transaction():
                        await connection.execute(
                            "SELECT id FROM conversations.threads WHERE id=%s FOR UPDATE NOWAIT",
                            (thread,),
                        )
        finally:
            release.set()
            await task
        assert (await retained(pool, entry))[1] is False
        sent = await PostgresMessageOperations(pool).submit_message(
            caller(author), thread, message_request(timestamp=3000)
        )
        assert sent.entry.sequence == 2 and not sent.entry.content_deleted

    run_scenario(scenario)


@pytest.mark.parametrize("batch", [0, 1001, True, 1.5])
def test_invalid_batch_refuses_before_database_access(batch):
    import asyncio

    with pytest.raises(ValueError):
        asyncio.run(ConversationCleanup(None).run(batch_size=batch))


def test_thread_batch_limit_is_enforced():
    async def scenario(pool):
        *_, before = await seeded_message(pool)
        await seeded_message(pool)
        result = await ConversationCleanup(
            pool, lambda: before[0] + timedelta(days=91)
        ).run(apply=True, batch_size=1)
        assert result.threads == 1

    run_scenario(scenario)


def test_cli_defaults_to_dry_run_and_refuses_mismatched_apply_target():
    import json
    import os
    import subprocess
    import sys
    from psycopg.conninfo import conninfo_to_dict
    from test_conversation_messages import TEST_DATABASE_DSN

    if TEST_DATABASE_DSN is None:
        pytest.skip("run through the disposable Conversations runner")
    info = conninfo_to_dict(TEST_DATABASE_DSN)
    command = [
        sys.executable,
        "scripts/conversations_cleanup.py",
        "--expected-database",
        info["dbname"],
        "--expected-host",
        info["host"],
        "--expected-port",
        info["port"],
    ]
    environment = os.environ | {"CLIP_CONVERSATIONS_DATABASE_URL": TEST_DATABASE_DSN}
    dry = subprocess.run(
        command, env=environment, capture_output=True, text=True, timeout=15
    )
    assert dry.returncode == 0 and not dry.stderr
    assert json.loads(dry.stdout)["dry_run"] is True
    command[3] = "wrong_synthetic_database"
    refused = subprocess.run(
        command + ["--apply"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert refused.returncode == 1 and not refused.stdout
    assert (
        refused.stderr
        == "Conversation cleanup failed; review target/configuration/state\n"
    )
