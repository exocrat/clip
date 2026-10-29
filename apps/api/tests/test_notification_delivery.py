"""Real PostgreSQL delivery boundaries with explicitly synthetic email."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest
from app.domains.conversations.notifications.composition import run_batch
from app.domains.conversations.notifications.storage import PostgresNotificationDelivery
from app.domains.identity.notification_address import (
    NotificationAddressCipher,
    NotificationRecipientResolver,
)
from app.domains.identity.temporary_crypto import TemporaryKeys
from app.contracts.domain_types import (
    NotificationClaimRequest,
    NotificationAttemptResult,
    NotificationDispatchCheck,
    NotificationWorkerContext,
    ReadAcknowledgement,
)
from app.core.runtime_bindings import runtime_claims
from app.core.errors import PublicError
from app.domains.conversations.messages import PostgresMessageOperations
from test_conversation_messages import (
    TEST_DATABASE_DSN,
    run_scenario,
    seed_thread,
    caller,
    message_request,
)


@pytest.mark.parametrize(
    "failure,enabled", [(False, True), (True, True), (False, False)]
)
def test_real_new_conversation_delivery_is_claimed_once(failure, enabled):
    """Two workers race a real intent while Identity resolves only its own address."""

    async def scenario(pool):
        async with pool.connection() as connection:
            await connection.execute("DELETE FROM conversations.notification_intents")
        author, responder, _, conversation, _, _ = await seed_thread(pool)
        keys = TemporaryKeys("v1", b"a" * 32, b"b" * 32, b"c" * 32)
        cipher = NotificationAddressCipher(keys)
        async with pool.connection() as c:
            await c.execute(
                "UPDATE identity.users SET conversation_email_enabled=%s WHERE id=%s",
                (enabled, author),
            )
            await c.execute(
                "INSERT INTO identity.notification_destinations(user_id,ciphertext,key_version) VALUES(%s,%s,%s)",
                (author, cipher.encrypt(author, "test@example.invalid"), "v1"),
            )
            await c.execute(
                "INSERT INTO conversations.notification_intents(id,conversation_id,recipient_id,event_kind,deduplication_key,due_at,expires_at) "
                "SELECT %s,id,%s,'new_conversation',%s,created_at,created_at+interval '24 hours' FROM conversations.threads WHERE id=%s",
                (
                    uuid4(),
                    author,
                    f"new_conversation:{conversation}:{author}",
                    conversation,
                ),
            )
        calls = []

        async def send(claim, recipient):
            calls.append((claim.event_kind, recipient.email))
            if failure:
                raise TimeoutError("synthetic uncertain delivery")

        async def execute():
            permit = object()
            port = PostgresNotificationDelivery(pool, permit)
            recipient = NotificationRecipientResolver(
                lambda: psycopg.connect(TEST_DATABASE_DSN),
                lambda: datetime.now(UTC),
                keys,
                permit,
            )
            return await run_batch(
                port, recipient, permit, lambda: datetime.now(UTC), send
            )

        counts = await asyncio.gather(execute(), execute())
        async with pool.connection() as c:
            row = await (
                await c.execute(
                    "SELECT state,attempts FROM conversations.notification_intents WHERE conversation_id=%s",
                    (conversation,),
                )
            ).fetchone()
            assert sum(counts) == (1 if enabled else 0), (counts, len(calls), row)
            assert row == (
                ("pending" if failure else "sent") if enabled else "suppressed",
                1 if enabled else 0,
            )
        assert calls == (
            [("new_conversation", "test@example.invalid")] if enabled else []
        )
        if failure:
            assert await execute() == 0
            assert len(calls) == 1

    run_scenario(scenario)


def test_real_lease_rejects_stale_tokens_and_duplicate_dispatch():
    """Only the active lease can reserve a send; outcome replay is idempotent."""

    async def scenario(pool):
        async with pool.connection() as c:
            await c.execute("DELETE FROM conversations.notification_intents")
        author, _, _, conversation, _, _ = await seed_thread(pool)
        intent_id = uuid4()
        async with pool.connection() as c:
            await c.execute(
                "INSERT INTO conversations.notification_intents(id,conversation_id,recipient_id,event_kind,deduplication_key,due_at,expires_at) "
                "SELECT %s,id,%s,'new_conversation',%s,created_at,created_at+interval '24 hours' FROM conversations.threads WHERE id=%s",
                (
                    intent_id,
                    author,
                    f"new_conversation:{conversation}:{author}",
                    conversation,
                ),
            )
        permit = object()
        port, context = (
            PostgresNotificationDelivery(pool, permit),
            NotificationWorkerContext(),
        )
        with pytest.raises(PublicError):
            await port.claim_due_notification_intents(
                context, NotificationClaimRequest(now_utc=datetime.now(UTC))
            )
        with runtime_claims({"conversations.notification_worker": permit}):
            claims = await port.claim_due_notification_intents(
                context, NotificationClaimRequest(now_utc=datetime.now(UTC))
            )
            assert len(claims.claims) == 1
            token = claims.claims[0].fencing_token
            wrong = NotificationDispatchCheck(
                intent_id=intent_id, fencing_token=uuid4(), now_utc=datetime.now(UTC)
            )
            assert (
                await port.read_notification_dispatch_context(context, wrong)
            ).decision == "defer"
            check = NotificationDispatchCheck(
                intent_id=intent_id, fencing_token=token, now_utc=datetime.now(UTC)
            )
            assert (
                await port.read_notification_dispatch_context(context, check)
            ).decision == "send"
            assert (
                await port.read_notification_dispatch_context(context, check)
            ).decision == "defer"
            outcome = NotificationAttemptResult(
                intent_id=intent_id,
                fencing_token=token,
                outcome="delivered",
                attempted_at=datetime.now(UTC),
            )
            assert (
                await port.record_notification_attempt(context, outcome)
            ).attempt_count == 1
            assert (
                await port.record_notification_attempt(context, outcome)
            ).attempt_count == 1

    run_scenario(scenario)


def test_real_read_acknowledgement_suppresses_a_leased_reminder():
    """The final fenced check observes the actual member watermark."""

    async def scenario(pool):
        async with pool.connection() as c:
            await c.execute("DELETE FROM conversations.notification_intents")
        author, responder, _, conversation, _, _ = await seed_thread(pool)
        messages = PostgresMessageOperations(pool)
        result = await messages.submit_message(
            caller(author), conversation, message_request()
        )
        async with pool.connection() as c:
            async with c.transaction():
                # Synthetic owned database only: age the matching immutable source
                # and intent together to exercise a 15-minute deadline immediately.
                await c.execute("SET LOCAL session_replication_role='replica'")
                await c.execute(
                    "UPDATE conversations.entries SET created_at=created_at-interval '16 minutes' WHERE id=%s",
                    (result.entry.entry_id,),
                )
                await c.execute(
                    "UPDATE conversations.notification_intents SET due_at=due_at-interval '16 minutes',expires_at=expires_at-interval '16 minutes' WHERE conversation_id=%s",
                    (conversation,),
                )
                await c.execute("SET LOCAL session_replication_role='origin'")
        permit = object()
        port = PostgresNotificationDelivery(pool, permit)
        context = NotificationWorkerContext()
        with runtime_claims({"conversations.notification_worker": permit}):
            batch = await port.claim_due_notification_intents(
                context, NotificationClaimRequest(now_utc=datetime.now(UTC))
            )
            assert len(batch.claims) == 1
            claim = batch.claims[0]
            await messages.submit_message(
                caller(author), conversation, message_request()
            )
            await messages.acknowledge_read(
                caller(responder),
                conversation,
                ReadAcknowledgement(last_read_sequence=1),
            )
            async with pool.connection() as c:
                assert (
                    await (
                        await c.execute(
                            "SELECT unread_through_sequence FROM conversations.notification_intents WHERE id=%s",
                            (claim.intent_id,),
                        )
                    ).fetchone()
                )[0] == 2
            await messages.acknowledge_read(
                caller(responder),
                conversation,
                ReadAcknowledgement(last_read_sequence=2),
            )
            result = await port.read_notification_dispatch_context(
                context,
                NotificationDispatchCheck(
                    intent_id=claim.intent_id,
                    fencing_token=claim.fencing_token,
                    now_utc=datetime.now(UTC),
                ),
            )
            assert result.decision == "suppress"
        async with pool.connection() as c:
            assert (
                await (
                    await c.execute(
                        "SELECT state FROM conversations.notification_intents WHERE id=%s",
                        (claim.intent_id,),
                    )
                ).fetchone()
            )[0] == "suppressed"

    run_scenario(scenario)


@pytest.mark.parametrize("enabled,fail", [(False, False), (True, False), (True, True)])
def test_due_unread_reminder_delivery_and_primary_write_independence(enabled, fail):
    """A due reminder respects preference and failures preserve its message."""

    async def scenario(pool):
        async with pool.connection() as c:
            await c.execute("DELETE FROM conversations.notification_intents")
        author, responder, _, conversation, _, _ = await seed_thread(pool)
        keys = TemporaryKeys("v1", b"a" * 32, b"b" * 32, b"c" * 32)
        message = await PostgresMessageOperations(pool).submit_message(
            caller(author), conversation, message_request()
        )
        async with pool.connection() as c:
            async with c.transaction():
                await c.execute(
                    "INSERT INTO identity.notification_destinations(user_id,ciphertext,key_version) VALUES(%s,%s,%s)",
                    (
                        responder,
                        NotificationAddressCipher(keys).encrypt(
                            responder, "synthetic@example.invalid"
                        ),
                        "v1",
                    ),
                )
                await c.execute(
                    "UPDATE identity.users SET conversation_email_enabled=%s WHERE id=%s",
                    (enabled, responder),
                )
                # Age only the synthetic source and its matching immutable deadline.
                await c.execute("SET LOCAL session_replication_role='replica'")
                await c.execute(
                    "UPDATE conversations.entries SET created_at=created_at-interval '16 minutes' WHERE id=%s",
                    (message.entry.entry_id,),
                )
                await c.execute(
                    "UPDATE conversations.notification_intents SET due_at=due_at-interval '16 minutes',expires_at=expires_at-interval '16 minutes' WHERE conversation_id=%s",
                    (conversation,),
                )
                await c.execute("SET LOCAL session_replication_role='origin'")
        permit = object()
        delivery = PostgresNotificationDelivery(pool, permit)
        recipient = NotificationRecipientResolver(
            lambda: psycopg.connect(TEST_DATABASE_DSN),
            lambda: datetime.now(UTC),
            keys,
            permit,
        )
        sent = []

        async def send(claim, destination):
            sent.append(True)
            if fail:
                raise TimeoutError("synthetic provider failure")

        assert await run_batch(
            delivery, recipient, permit, lambda: datetime.now(UTC), send
        ) == int(enabled)
        async with pool.connection() as c:
            row = await (
                await c.execute(
                    "SELECT state,attempts,last_result_outcome FROM conversations.notification_intents WHERE conversation_id=%s",
                    (conversation,),
                )
            ).fetchone()
            assert row == (
                ("pending", 1, "ambiguous")
                if fail
                else (
                    ("sent", 1, "delivered")
                    if enabled
                    else ("suppressed", 0, "preference_suppressed")
                )
            )
            assert (
                await (
                    await c.execute(
                        "SELECT count(*) FROM conversations.entries WHERE id=%s",
                        (message.entry.entry_id,),
                    )
                ).fetchone()
            )[0] == 1
        assert sent == ([True] if enabled else [])

    run_scenario(scenario)


def test_message_read_before_due_is_suppressed():
    """Acknowledging an unread message before its due time prevents its email."""

    async def scenario(pool):
        async with pool.connection() as c:
            await c.execute("DELETE FROM conversations.notification_intents")
        author, responder, _, conversation, _, _ = await seed_thread(pool)
        messages = PostgresMessageOperations(pool)
        message = await messages.submit_message(
            caller(author), conversation, message_request()
        )
        await messages.acknowledge_read(
            caller(responder), conversation, ReadAcknowledgement(last_read_sequence=1)
        )
        async with pool.connection() as c:
            async with c.transaction():
                # Age the already-acknowledged synthetic source and matching deadline.
                await c.execute("SET LOCAL session_replication_role='replica'")
                await c.execute(
                    "UPDATE conversations.entries SET created_at=created_at-interval '16 minutes' WHERE id=%s",
                    (message.entry.entry_id,),
                )
                await c.execute(
                    "UPDATE conversations.notification_intents SET due_at=due_at-interval '16 minutes',expires_at=expires_at-interval '16 minutes' WHERE conversation_id=%s",
                    (conversation,),
                )
                await c.execute("SET LOCAL session_replication_role='origin'")
        permit, context = object(), NotificationWorkerContext()
        with runtime_claims({"conversations.notification_worker": permit}):
            claims = await PostgresNotificationDelivery(
                pool, permit
            ).claim_due_notification_intents(
                context, NotificationClaimRequest(now_utc=datetime.now(UTC))
            )
            assert claims.claims == []
        async with pool.connection() as c:
            assert (
                await (
                    await c.execute(
                        "SELECT state FROM conversations.notification_intents WHERE conversation_id=%s",
                        (conversation,),
                    )
                ).fetchone()
            )[0] == "suppressed"

    run_scenario(scenario)


@pytest.mark.parametrize("terminal", [False, True])
def test_real_failure_retries_are_bounded_and_terminal(terminal):
    """Real fenced outcomes use the selected backoffs and stop at the limit."""

    async def scenario(pool):
        async with pool.connection() as c:
            await c.execute("DELETE FROM conversations.notification_intents")
        author, _, _, conversation, _, _ = await seed_thread(pool)
        intent = uuid4()
        async with pool.connection() as c:
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
        permit, context = object(), NotificationWorkerContext()
        port = PostgresNotificationDelivery(pool, permit)
        with runtime_claims({"conversations.notification_worker": permit}):
            for attempt in range(1, 2 if terminal else 6):
                claims = await port.claim_due_notification_intents(
                    context, NotificationClaimRequest(now_utc=datetime.now(UTC))
                )
                assert len(claims.claims) == 1
                token = claims.claims[0].fencing_token
                check = NotificationDispatchCheck(
                    intent_id=intent, fencing_token=token, now_utc=datetime.now(UTC)
                )
                assert (
                    await port.read_notification_dispatch_context(context, check)
                ).decision == "send"
                result = NotificationAttemptResult(
                    intent_id=intent,
                    fencing_token=token,
                    outcome="terminal_failure" if terminal else "transient_failure",
                    attempted_at=datetime.now(UTC),
                )
                state = await port.record_notification_attempt(context, result)
                assert state.attempt_count == attempt
                if terminal or attempt == 5:
                    assert state.state == "terminal"
                else:
                    assert state.state == "pending"
                    async with pool.connection() as c:
                        seconds = (
                            await (
                                await c.execute(
                                    "SELECT extract(epoch FROM next_attempt_at-updated_at) FROM conversations.notification_intents WHERE id=%s",
                                    (intent,),
                                )
                            ).fetchone()
                        )[0]
                        assert seconds == (60, 300, 900, 3600)[attempt - 1]
                        # Synthetic clock advancement; no production timing change.
                        await c.execute(
                            "UPDATE conversations.notification_intents SET next_attempt_at=clock_timestamp()-interval '1 second' WHERE id=%s",
                            (intent,),
                        )
            assert (
                await port.claim_due_notification_intents(
                    context, NotificationClaimRequest(now_utc=datetime.now(UTC))
                )
            ).claims == []

    run_scenario(scenario)
