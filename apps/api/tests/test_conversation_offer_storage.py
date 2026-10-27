"""Offer storage invariants on the harness-owned disposable PostgreSQL.

Direct synthetic fixtures exercise existing SQL protections, not authenticated
Listings offer commands. No service or encryption integration is claimed here.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from psycopg import IntegrityError
from psycopg.errors import CheckViolation, UniqueViolation
import pytest

from app.domains.conversations.cleanup import ConversationCleanup
from test_conversation_messages import run_scenario
from test_origin_retirement import seed_origin


async def seed_offer_thread(pool, kind="sale_listing"):
    """Reuse the reviewed synthetic origin fixture and return its member IDs."""
    _, threads = await seed_origin(pool, kind, [datetime.now(UTC)])
    async with pool.connection() as connection:
        row = await (
            await connection.execute(
                "SELECT initiator_id,counterparty_id FROM conversations.threads WHERE id=%s",
                (threads[0],),
            )
        ).fetchone()
    return threads[0], *row


async def append_revision(
    connection,
    thread,
    buyer,
    offer,
    amount,
    status="submitted",
    *,
    sender=None,
    operation=None,
):
    """Build a complete storage transaction; SQL, not this helper, validates it.

    Entry insertion locks the thread before offer state. SDK identity is explicit
    even on optional-note entries so a legacy envelope can bind to the operation.
    Caller owns the transaction, allowing failure/commit constraints to be tested.
    """
    entry, operation = uuid4(), operation or uuid4()
    await connection.execute(
        "INSERT INTO conversations.entries "
        "(id,conversation_id,sender_id,client_operation_id,kind,sdk_client_message_id) "
        "VALUES (%s,%s,%s,%s,'offer',%s)",
        (entry, thread, sender or buyer, operation, str(operation)),
    )
    row = await (
        await connection.execute(
            "SELECT next_revision FROM conversations.offers WHERE id=%s FOR UPDATE",
            (offer,),
        )
    ).fetchone()
    revision = row[0] if row else 1
    if row:
        await connection.execute(
            "UPDATE conversations.offers SET current_revision=%s,next_revision=%s,"
            "history_deleted_at=NULL WHERE id=%s",
            (revision, revision + 1, offer),
        )
    else:
        await connection.execute(
            "INSERT INTO conversations.offers "
            "(id,conversation_id,buyer_id,current_revision,next_revision) VALUES (%s,%s,%s,1,2)",
            (offer, thread, buyer),
        )
    await connection.execute(
        "INSERT INTO conversations.offer_revisions "
        "(offer_id,revision,entry_id,amount_paise,status) VALUES (%s,%s,%s,%s,%s)",
        (offer, revision, entry, amount, status),
    )
    return entry, revision


async def attach_note(connection, entry, buyer, seller, *, reverse_keys=False):
    """Attach opaque synthetic bytes; test key ownership without pretending crypto."""
    keys = [uuid4(), uuid4()]
    for key, user in zip(keys, (buyer, seller), strict=True):
        await connection.execute(
            "INSERT INTO conversations.public_key_versions "
            "(id,user_id,version,public_key_material,protocol_id) "
            "VALUES (%s,%s,1,%s,'open-e2ee-signal')",
            (key, user, b"synthetic-public-fixture"),
        )
    if reverse_keys:
        keys.reverse()
    await connection.execute(
        "INSERT INTO conversations.encrypted_payloads "
        "(entry_id,protocol_id,protocol_version,envelope_version,sdk_message_type,"
        "client_timestamp_ms,sender_key_version_id,recipient_key_version_id,envelope) "
        "VALUES (%s,'open-e2ee-signal','13.0.0',1,'ciphertext',1,%s,%s,%s)",
        (entry, *keys, b"opaque-synthetic-note"),
    )


async def thread_head(pool, thread):
    """Read the complete ordering/activity state for atomic rollback assertions."""
    async with pool.connection() as connection:
        return await (
            await connection.execute(
                "SELECT next_sequence,last_activity_at FROM conversations.threads WHERE id=%s",
                (thread,),
            )
        ).fetchone()


def test_offer_storage_lifecycle_keeps_one_identity_and_ordered_history():
    async def scenario(pool):
        thread, buyer, _ = await seed_offer_thread(pool)
        offer = uuid4()
        for amount, status in (
            (0, "submitted"),
            (1200, "submitted"),
            (1200, "withdrawn"),
            (2000, "submitted"),
        ):
            async with pool.connection() as connection, connection.transaction():
                await append_revision(connection, thread, buyer, offer, amount, status)
        async with pool.connection() as connection:
            assert await (
                await connection.execute(
                    "SELECT current_revision,next_revision,history_deleted_at "
                    "FROM conversations.offers WHERE id=%s",
                    (offer,),
                )
            ).fetchone() == (4, 5, None)
            rows = await (
                await connection.execute(
                    "SELECT r.revision,r.amount_paise,r.status,e.sequence "
                    "FROM conversations.offer_revisions r JOIN conversations.entries e "
                    "ON e.id=r.entry_id WHERE r.offer_id=%s ORDER BY r.revision",
                    (offer,),
                )
            ).fetchall()
            assert rows == [
                (1, 0, "submitted", 1),
                (2, 1200, "submitted", 2),
                (3, 1200, "withdrawn", 3),
                (4, 2000, "submitted", 4),
            ]
        assert (await thread_head(pool, thread))[0] == 5

    run_scenario(scenario)


@pytest.mark.parametrize(
    "amount,status",
    [
        (-100, "submitted"),
        (1, "submitted"),
        (150, "submitted"),
        (100, "accepted"),
    ],
)
def test_invalid_offer_values_roll_back_entry_pointer_and_activity(amount, status):
    async def scenario(pool):
        thread, buyer, _ = await seed_offer_thread(pool)
        offer, operation = uuid4(), uuid4()
        before = await thread_head(pool, thread)
        with pytest.raises(CheckViolation):
            async with pool.connection() as connection, connection.transaction():
                await append_revision(
                    connection,
                    thread,
                    buyer,
                    offer,
                    amount,
                    status,
                    operation=operation,
                )
        assert await thread_head(pool, thread) == before
        async with pool.connection() as connection:
            assert await (
                await connection.execute(
                    "SELECT EXISTS(SELECT 1 FROM conversations.offers WHERE id=%s),"
                    "EXISTS(SELECT 1 FROM conversations.entries WHERE client_operation_id=%s)",
                    (offer, operation),
                )
            ).fetchone() == (False, False)

    run_scenario(scenario)


@pytest.mark.parametrize("case", ["seller_offer", "seller_revision", "wanted_origin"])
def test_offer_storage_rejects_wrong_buyer_or_origin(case):
    async def scenario(pool):
        thread, buyer, seller = await seed_offer_thread(
            pool,
            "wanted_request" if case == "wanted_origin" else "sale_listing",
        )
        with pytest.raises(CheckViolation):
            async with pool.connection() as connection, connection.transaction():
                await append_revision(
                    connection,
                    thread,
                    seller if case == "seller_offer" else buyer,
                    uuid4(),
                    100,
                    sender=seller if case == "seller_revision" else None,
                )
        assert (await thread_head(pool, thread))[0] == 1

    run_scenario(scenario)


def test_offer_pair_unique_constraint_rejects_second_logical_offer():
    async def scenario(pool):
        thread, buyer, _ = await seed_offer_thread(pool)
        async with pool.connection() as connection, connection.transaction():
            await append_revision(connection, thread, buyer, uuid4(), 100)
        with pytest.raises(UniqueViolation):
            async with pool.connection() as connection, connection.transaction():
                await append_revision(connection, thread, buyer, uuid4(), 200)
        assert (await thread_head(pool, thread))[0] == 2

    run_scenario(scenario)


@pytest.mark.parametrize("case", ["rewrite_revision", "skip_revision"])
def test_offer_history_and_counter_cannot_be_rewritten(case):
    async def scenario(pool):
        thread, buyer, _ = await seed_offer_thread(pool)
        offer = uuid4()
        async with pool.connection() as connection, connection.transaction():
            await append_revision(connection, thread, buyer, offer, 100)
        with pytest.raises(CheckViolation):
            async with pool.connection() as connection, connection.transaction():
                if case == "rewrite_revision":
                    await connection.execute(
                        "UPDATE conversations.offer_revisions SET amount_paise=200 WHERE offer_id=%s",
                        (offer,),
                    )
                else:
                    await connection.execute(
                        "UPDATE conversations.offers SET current_revision=3,next_revision=4 WHERE id=%s",
                        (offer,),
                    )

    run_scenario(scenario)


@pytest.mark.parametrize(
    "case", ["first_withdrawal", "changed_amount", "second_withdrawal"]
)
def test_withdrawal_requires_submitted_predecessor_and_unchanged_amount(case):
    async def scenario(pool):
        thread, buyer, _ = await seed_offer_thread(pool)
        offer = uuid4()
        if case != "first_withdrawal":
            async with pool.connection() as connection, connection.transaction():
                await append_revision(connection, thread, buyer, offer, 100)
        if case == "second_withdrawal":
            async with pool.connection() as connection, connection.transaction():
                await append_revision(
                    connection, thread, buyer, offer, 100, "withdrawn"
                )
        before = await thread_head(pool, thread)
        with pytest.raises(CheckViolation):
            async with pool.connection() as connection, connection.transaction():
                await append_revision(
                    connection,
                    thread,
                    buyer,
                    offer,
                    200 if case == "changed_amount" else 100,
                    "withdrawn",
                )
        assert await thread_head(pool, thread) == before

    run_scenario(scenario)


def test_deferred_current_revision_requires_matching_history_at_commit():
    async def scenario(pool):
        thread, buyer, _ = await seed_offer_thread(pool)
        offer = uuid4()
        with pytest.raises(IntegrityError):
            async with pool.connection() as connection, connection.transaction():
                await connection.execute(
                    "INSERT INTO conversations.offers "
                    "(id,conversation_id,buyer_id,current_revision,next_revision) VALUES (%s,%s,%s,1,2)",
                    (offer, thread, buyer),
                )
        async with pool.connection() as connection:
            assert not (
                await (
                    await connection.execute(
                        "SELECT EXISTS(SELECT 1 FROM conversations.offers WHERE id=%s)",
                        (offer,),
                    )
                ).fetchone()
            )[0]

    run_scenario(scenario)


@pytest.mark.parametrize("reverse_keys", [False, True])
def test_optional_note_binds_encrypted_storage_to_buyer_and_peer(reverse_keys):
    async def scenario(pool):
        thread, buyer, seller = await seed_offer_thread(pool)
        before = await thread_head(pool, thread)

        async def write():
            async with pool.connection() as connection, connection.transaction():
                entry, _ = await append_revision(
                    connection, thread, buyer, uuid4(), 100
                )
                await attach_note(
                    connection, entry, buyer, seller, reverse_keys=reverse_keys
                )

        if reverse_keys:
            with pytest.raises(CheckViolation):
                await write()
            assert await thread_head(pool, thread) == before
        else:
            await write()
            assert (await thread_head(pool, thread))[0] == 2

    run_scenario(scenario)


def test_retention_preserves_offer_pair_counter_and_expired_operation_marker():
    async def scenario(pool):
        thread, buyer, seller = await seed_offer_thread(pool)
        offer, operation = uuid4(), uuid4()
        async with pool.connection() as connection, connection.transaction():
            entry, _ = await append_revision(
                connection, thread, buyer, offer, 100, operation=operation
            )
            await attach_note(connection, entry, buyer, seller)
        activity = (await thread_head(pool, thread))[1]
        await ConversationCleanup(pool, lambda: activity + timedelta(days=90)).run(
            apply=True,
            batch_size=1000,
        )
        async with pool.connection() as connection:
            assert await (
                await connection.execute(
                    "SELECT current_revision,next_revision,history_deleted_at IS NOT NULL "
                    "FROM conversations.offers WHERE id=%s",
                    (offer,),
                )
            ).fetchone() == (None, 2, True)
            assert await (
                await connection.execute(
                    "SELECT content_deleted_at IS NOT NULL,"
                    "EXISTS(SELECT 1 FROM conversations.encrypted_payloads WHERE entry_id=%s),"
                    "EXISTS(SELECT 1 FROM conversations.offer_revisions WHERE offer_id=%s) "
                    "FROM conversations.entries WHERE id=%s",
                    (entry, offer, entry),
                )
            ).fetchone() == (True, False, False)
        with pytest.raises(CheckViolation):
            async with pool.connection() as connection, connection.transaction():
                await connection.execute(
                    "DELETE FROM conversations.offers WHERE id=%s", (offer,)
                )
        with pytest.raises(UniqueViolation):
            async with pool.connection() as connection, connection.transaction():
                await append_revision(
                    connection, thread, buyer, offer, 100, operation=operation
                )
        async with pool.connection() as connection, connection.transaction():
            _, revision = await append_revision(connection, thread, buyer, offer, 200)
            assert revision == 2
        assert (await thread_head(pool, thread))[0] == 3

    run_scenario(scenario)
