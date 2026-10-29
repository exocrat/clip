"""Notification retention tests on the harness's disposable PostgreSQL only."""

from uuid import uuid4

import psycopg
import pytest

from app.contracts.domain_types import NotificationWorkerContext
from app.contracts.domain_types import ReadAcknowledgement
from app.core.errors import PublicError
from app.core.runtime_bindings import runtime_claims
from app.domains.conversations.notifications.cleanup import NotificationCleanup
from app.domains.conversations.messages import PostgresMessageOperations
from test_conversation_messages import (
    run_scenario,
    seed_thread,
    caller,
    message_request,
)


def test_terminal_cleanup_cutoff_dry_run_and_replay_guard():
    """Delete only due terminal jobs; old source replay cannot restart delivery."""

    async def scenario(pool):
        async with pool.connection() as c:
            await c.execute("DELETE FROM conversations.notification_intents")
        author, _, _, conversation, _, _ = await seed_thread(pool)
        intent = uuid4()
        key = f"new_conversation:{conversation}:{author}"
        async with pool.connection() as c:
            async with c.transaction():
                await c.execute(
                    "INSERT INTO conversations.notification_intents(id,conversation_id,recipient_id,event_kind,deduplication_key,due_at,expires_at) "
                    "SELECT %s,id,%s,'new_conversation',%s,created_at,created_at+interval '24 hours' FROM conversations.threads WHERE id=%s",
                    (intent, author, key, conversation),
                )
                await c.execute(
                    "UPDATE conversations.notification_intents SET state='sent',completed_at=clock_timestamp() WHERE id=%s",
                    (intent,),
                )
                # Owned synthetic database only: age the immutable source and
                # terminal record consistently to exercise retention immediately.
                await c.execute("SET LOCAL session_replication_role='replica'")
                await c.execute(
                    "UPDATE conversations.threads SET created_at=created_at-interval '32 days' WHERE id=%s",
                    (conversation,),
                )
                await c.execute(
                    "UPDATE conversations.notification_intents SET due_at=due_at-interval '32 days',expires_at=expires_at-interval '32 days',completed_at=clock_timestamp()-interval '29 days' WHERE id=%s",
                    (intent,),
                )
                await c.execute("SET LOCAL session_replication_role='origin'")
        permit = object()
        operation = NotificationCleanup(pool, permit)
        context = NotificationWorkerContext()
        with pytest.raises(PublicError):
            await operation.run(context)
        with runtime_claims({"conversations.notification_worker": permit}):
            assert (await operation.run(context)).eligible == 0
            async with pool.connection() as c:
                await c.execute(
                    "UPDATE conversations.notification_intents SET completed_at=clock_timestamp()-interval '30 days' WHERE id=%s",
                    (intent,),
                )
            preview = await operation.run(context, batch_size=1)
            assert preview.dry_run and preview.eligible == 1 and preview.deleted == 0
            result = await operation.run(context, apply=True, batch_size=1)
            assert not result.dry_run and result.eligible == result.deleted == 1
            assert (await operation.run(context, apply=True)).deleted == 0
            with pytest.raises(ValueError):
                await operation.run(context, batch_size=101)
        async with pool.connection() as c:
            with pytest.raises(psycopg.IntegrityError):
                async with c.transaction():
                    await c.execute(
                        "INSERT INTO conversations.notification_intents(id,conversation_id,recipient_id,event_kind,deduplication_key,due_at,expires_at) "
                        "SELECT %s,id,%s,'new_conversation',%s,created_at,created_at+interval '24 hours' FROM conversations.threads WHERE id=%s",
                        (uuid4(), author, key, conversation),
                    )

    run_scenario(scenario)


def test_deleted_reminder_does_not_restart_the_same_unread_episode():
    """Persistent member state prevents a new reminder after record retention."""

    async def scenario(pool):
        async with pool.connection() as c:
            await c.execute("DELETE FROM conversations.notification_intents")
        author, responder, _, conversation, _, _ = await seed_thread(pool)
        messages = PostgresMessageOperations(pool)
        first = await messages.submit_message(
            caller(author), conversation, message_request()
        )
        async with pool.connection() as c:
            async with c.transaction():
                # Age this synthetic source and due time together; production
                # code never permits mutation of original source timestamps.
                await c.execute("SET LOCAL session_replication_role='replica'")
                await c.execute(
                    "UPDATE conversations.entries SET created_at=created_at-interval '32 days' WHERE id=%s",
                    (first.entry.entry_id,),
                )
                await c.execute(
                    "UPDATE conversations.notification_intents SET due_at=due_at-interval '32 days',expires_at=expires_at-interval '32 days' WHERE conversation_id=%s",
                    (conversation,),
                )
                await c.execute("SET LOCAL session_replication_role='origin'")
                await c.execute(
                    "UPDATE conversations.members SET reminder_sent_at=clock_timestamp()-interval '31 days' WHERE conversation_id=%s AND user_id=%s",
                    (conversation, responder),
                )
                await c.execute(
                    "UPDATE conversations.notification_intents SET state='sent',completed_at=clock_timestamp()-interval '31 days' WHERE conversation_id=%s",
                    (conversation,),
                )
        permit = object()
        with runtime_claims({"conversations.notification_worker": permit}):
            assert (
                await NotificationCleanup(pool, permit).run(
                    NotificationWorkerContext(), apply=True
                )
            ).deleted == 1
        await messages.submit_message(caller(author), conversation, message_request())
        async with pool.connection() as c:
            assert (
                await (
                    await c.execute(
                        "SELECT count(*) FROM conversations.notification_intents WHERE conversation_id=%s",
                        (conversation,),
                    )
                ).fetchone()
            )[0] == 0
        await messages.acknowledge_read(
            caller(responder), conversation, ReadAcknowledgement(last_read_sequence=2)
        )
        await messages.submit_message(caller(author), conversation, message_request())
        async with pool.connection() as c:
            assert (
                await (
                    await c.execute(
                        "SELECT count(*) FROM conversations.notification_intents WHERE conversation_id=%s",
                        (conversation,),
                    )
                ).fetchone()
            )[0] == 1

    run_scenario(scenario)


def test_cleanup_rechecks_changed_state_and_rolls_back_failure():
    """A concurrent transition or failed deletion cannot remove the intent."""

    async def scenario(pool):
        async with pool.connection() as c:
            await c.execute("DELETE FROM conversations.notification_intents")
        author, _, _, conversation, _, _ = await seed_thread(pool)
        intent = uuid4()
        async with pool.connection() as c:
            async with c.transaction():
                await c.execute(
                    "INSERT INTO conversations.notification_intents(id,conversation_id,recipient_id,event_kind,deduplication_key,due_at,expires_at) "
                    "SELECT %s,id,%s,'new_conversation',%s,created_at,created_at+interval '24 hours' FROM conversations.threads WHERE id=%s",
                    (
                        intent,
                        author,
                        f"new_conversation:{conversation}:{author}",
                        conversation,
                    ),
                )
                await c.execute(
                    "UPDATE conversations.notification_intents SET state='failed',completed_at=clock_timestamp() WHERE id=%s",
                    (intent,),
                )
                await c.execute("SET LOCAL session_replication_role='replica'")
                await c.execute(
                    "UPDATE conversations.threads SET created_at=created_at-interval '32 days' WHERE id=%s",
                    (conversation,),
                )
                await c.execute(
                    "UPDATE conversations.notification_intents SET due_at=due_at-interval '32 days',expires_at=expires_at-interval '32 days',completed_at=clock_timestamp()-interval '31 days' WHERE id=%s",
                    (intent,),
                )
                await c.execute("SET LOCAL session_replication_role='origin'")
        permit = object()
        operation = NotificationCleanup(pool, permit)
        original_lock = operation._delivery._locked

        async def transition_before_lock(connection, intent_id):
            async with pool.connection() as other:
                await other.execute(
                    "UPDATE conversations.notification_intents SET state='pending',completed_at=NULL WHERE id=%s",
                    (intent_id,),
                )
            return await original_lock(connection, intent_id)

        operation._delivery._locked = transition_before_lock
        with runtime_claims({"conversations.notification_worker": permit}):
            assert (
                await operation.run(NotificationWorkerContext(), apply=True)
            ).deleted == 0
        operation._delivery._locked = original_lock
        other_author, _, _, other_conversation, _, _ = await seed_thread(pool)
        leased_intent = uuid4()
        async with pool.connection() as c:
            await c.execute(
                "INSERT INTO conversations.notification_intents(id,conversation_id,recipient_id,event_kind,deduplication_key,due_at,expires_at) "
                "SELECT %s,id,%s,'new_conversation',%s,created_at,created_at+interval '24 hours' FROM conversations.threads WHERE id=%s",
                (
                    leased_intent,
                    other_author,
                    f"new_conversation:{other_conversation}:{other_author}",
                    other_conversation,
                ),
            )
            await c.execute(
                "UPDATE conversations.notification_intents SET state='leased',lease_token=%s,lease_until=clock_timestamp()+interval '1 minute' WHERE id=%s",
                (uuid4(), leased_intent),
            )
        with runtime_claims({"conversations.notification_worker": permit}):
            assert (
                await operation.run(NotificationWorkerContext(), apply=True)
            ).eligible == 0
        async with pool.connection() as c:
            await c.execute(
                "UPDATE conversations.notification_intents SET state='failed',completed_at=clock_timestamp()-interval '31 days' WHERE id=%s",
                (intent,),
            )
            await c.execute(
                "CREATE FUNCTION conversations.test_reject_notification_delete() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic'; END $$"
            )
            await c.execute(
                "CREATE TRIGGER test_reject_notification_delete BEFORE DELETE ON conversations.notification_intents FOR EACH ROW EXECUTE FUNCTION conversations.test_reject_notification_delete()"
            )
        try:
            with runtime_claims({"conversations.notification_worker": permit}):
                with pytest.raises(PublicError):
                    await operation.run(NotificationWorkerContext(), apply=True)
            async with pool.connection() as c:
                assert (
                    await (
                        await c.execute(
                            "SELECT count(*) FROM conversations.notification_intents WHERE id=%s",
                            (intent,),
                        )
                    ).fetchone()
                )[0] == 1
        finally:
            async with pool.connection() as c:
                await c.execute(
                    "DROP TRIGGER test_reject_notification_delete ON conversations.notification_intents"
                )
                await c.execute(
                    "DROP FUNCTION conversations.test_reject_notification_delete()"
                )

    run_scenario(scenario)
