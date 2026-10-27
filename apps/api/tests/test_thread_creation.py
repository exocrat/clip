"""Database integration checks for Conversations-owned thread creation."""

import asyncio
from datetime import UTC, datetime, timedelta
import os
from uuid import UUID, uuid4

import pytest
from psycopg_pool import AsyncConnectionPool

from app.contracts.domain_types import (
    AccountEligibility,
    ExistingWantedConversationLookup,
    ListingConversationContext,
    ListingThreadParticipantCheck,
    WantedConversationContext,
)
from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.domains.conversations.thread_creation import (
    PostgresThreadCreationOperations,
)
from app.domains.conversations.routes import create_public_provider

TEST_DATABASE_DSN = os.environ.get("CLIP_TEST_DATABASE_DSN")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_DSN is None,
    reason="run through scripts/check_conversations_retirement.py",
)


def run_scenario(scenario, *, max_size: int = 1) -> None:
    """Give each scenario an isolated async pool and close it on every path."""

    async def run() -> None:
        assert TEST_DATABASE_DSN is not None
        pool = AsyncConnectionPool(
            conninfo=TEST_DATABASE_DSN,
            min_size=0,
            max_size=max_size,
            open=False,
        )
        await pool.open(wait=True)
        try:
            await scenario(pool)
        finally:
            await pool.close()

    asyncio.run(run())


async def seed_users_and_listing(
    pool, *, temporary_buyer: bool = False
) -> tuple[UUID, UUID, UUID]:
    """Create synthetic users and a valid image-backed listing."""
    owner_id, buyer_id, listing_id = uuid4(), uuid4(), uuid4()
    upload_id, image_id = uuid4(), uuid4()
    object_key = f"test/thread-create/{image_id}"
    async with pool.connection() as connection:
        async with connection.transaction():
            await connection.execute(
                "INSERT INTO identity.users (id, account_class, status) "
                "VALUES (%s, 'regular', 'active')",
                (owner_id,),
            )
            if temporary_buyer:
                await connection.execute(
                    "INSERT INTO identity.users "
                    "(id, account_class, status, created_at, activated_at, expires_at) "
                    "VALUES (%s, 'temporary', 'active', CURRENT_TIMESTAMP - INTERVAL '1 hour', "
                    "CURRENT_TIMESTAMP - INTERVAL '1 hour', CURRENT_TIMESTAMP + INTERVAL '335 hours')",
                    (buyer_id,),
                )
            else:
                await connection.execute(
                    "INSERT INTO identity.users (id, account_class, status) "
                    "VALUES (%s, 'regular', 'active')",
                    (buyer_id,),
                )
            cursor = await connection.execute(
                "SELECT id FROM listings.categories WHERE code = 'other'"
            )
            category_id = (await cursor.fetchone())[0]
            await connection.execute(
                "INSERT INTO listings.sale_listings "
                "(id, owner_id, title, description, category_id, condition_code, "
                "asking_price_paise, negotiable, pickup_area, availability) "
                "VALUES (%s, %s, 'Synthetic item', 'Test-only description', %s, "
                "'good', 100, false, 'Test area', 'available')",
                (listing_id, owner_id, category_id),
            )
            await connection.execute(
                "INSERT INTO listings.image_uploads "
                "(id, owner_id, object_key, state, created_at, expires_at, confirmed_at, operation_id, confirmed_media_type, confirmed_size_bytes) "
                "VALUES (%s, %s, %s, 'confirmed', CURRENT_TIMESTAMP, "
                "CURRENT_TIMESTAMP + INTERVAL '24 hours', CURRENT_TIMESTAMP, %s, 'image/png', 1)",
                (upload_id, owner_id, object_key, uuid4()),
            )
            await connection.execute(
                "INSERT INTO listings.images "
                "(id, listing_id, upload_id, object_key, position, media_type, size_bytes) "
                "VALUES (%s, %s, %s, %s, 0, 'image/png', 1)",
                (image_id, listing_id, upload_id, object_key),
            )
    return owner_id, buyer_id, listing_id


async def seed_users_and_request(pool) -> tuple[UUID, UUID, UUID]:
    """Create a regular synthetic responder and an open Wanted Request."""
    author_id, responder_id, request_id = uuid4(), uuid4(), uuid4()
    async with pool.connection() as connection:
        async with connection.transaction():
            await connection.execute(
                "INSERT INTO identity.users (id, account_class, status) "
                "VALUES (%s, 'regular', 'active'), (%s, 'regular', 'active')",
                (author_id, responder_id),
            )
            cursor = await connection.execute(
                "SELECT id FROM listings.categories WHERE code = 'other'"
            )
            category_id = (await cursor.fetchone())[0]
            await connection.execute(
                "INSERT INTO search.wanted_requests "
                "(id, author_id, title, description, category_code, budget_paise, status) "
                "VALUES (%s, %s, 'Synthetic request', 'Test-only description', %s, 100, 'open')",
                (request_id, author_id, "other"),
            )
    return author_id, responder_id, request_id


def caller(user_id: UUID, account_class: str = "regular") -> CallerContext:
    """Build a current synthetic caller; this is not production authentication."""
    return CallerContext(
        user_id=user_id,
        account_class=account_class,
        valid_until=datetime.now(UTC) + timedelta(days=1),
    )


def eligibility_double(*, ineligible: set[UUID] | None = None, fail=False):
    """Return a recorded, reviewed-contract-shaped Identity test double."""
    calls: list[tuple[UUID, str | None]] = []

    async def check(user_id: UUID, required_class: str | None):
        calls.append((user_id, required_class))
        if fail:
            raise RuntimeError("synthetic Identity outage")
        return AccountEligibility(eligible=user_id not in (ineligible or set()))

    return check, calls


def test_listing_thread_creation_adds_two_members_and_one_owner_intent():
    async def scenario(pool):
        owner_id, buyer_id, listing_id = await seed_users_and_listing(pool)
        check, calls = eligibility_double()
        operations = PostgresThreadCreationOperations(pool, check)
        result = await operations.open_or_create_listing_conversation(
            caller(buyer_id),
            ListingConversationContext(listing_id=listing_id, owner_id=owner_id),
        )
        assert result.created is True
        assert calls == [(buyer_id, "regular"), (owner_id, "regular")]
        # Selection must bind every part of the relationship, not just a member
        # ID in some unrelated conversation. This exercises the actual provider.
        provider = create_public_provider(pool)
        participant = ListingThreadParticipantCheck(
            conversation_id=result.conversation_id,
            listing_id=listing_id,
            candidate_user_id=buyer_id,
        )
        assert (
            await provider.check_listing_thread_participant(
                caller(owner_id), participant
            )
        ).is_participant
        assert not (
            await provider.check_listing_thread_participant(
                caller(buyer_id), participant
            )
        ).is_participant
        for field in ("conversation_id", "listing_id", "candidate_user_id"):
            wrong = participant.model_copy(update={field: uuid4()})
            assert not (
                await provider.check_listing_thread_participant(caller(owner_id), wrong)
            ).is_participant
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT listing_id, initiator_id, counterparty_id, created_at, last_activity_at "
                "FROM conversations.threads WHERE id = %s",
                (result.conversation_id,),
            )
            row = await cursor.fetchone()
            assert row[:3] == (listing_id, buyer_id, owner_id)
            assert row[3] == row[4]
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.members WHERE conversation_id = %s",
                (result.conversation_id,),
            )
            assert (await cursor.fetchone())[0] == 2
            cursor = await connection.execute(
                "SELECT recipient_id, event_kind, deduplication_key "
                "FROM conversations.notification_intents WHERE conversation_id = %s",
                (result.conversation_id,),
            )
            assert await cursor.fetchone() == (
                owner_id,
                "new_conversation",
                f"new_conversation:{result.conversation_id}:{owner_id}",
            )

    run_scenario(scenario)


def test_listing_retry_after_unavailability_returns_existing_without_duplicate_intent():
    async def scenario(pool):
        owner_id, buyer_id, listing_id = await seed_users_and_listing(pool)
        operations = PostgresThreadCreationOperations(pool, eligibility_double()[0])
        request = ListingConversationContext(listing_id=listing_id, owner_id=owner_id)
        first = await operations.open_or_create_listing_conversation(
            caller(buyer_id), request
        )
        async with pool.connection() as connection:
            await connection.execute(
                "UPDATE listings.sale_listings SET availability = 'unavailable' "
                "WHERE id = %s",
                (listing_id,),
            )
        retry = await operations.open_or_create_listing_conversation(
            caller(buyer_id), request
        )
        assert retry.conversation_id == first.conversation_id
        assert retry.created is False
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.threads WHERE listing_id = %s",
                (listing_id,),
            )
            assert (await cursor.fetchone())[0] == 1
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.notification_intents "
                "WHERE conversation_id = %s",
                (first.conversation_id,),
            )
            assert (await cursor.fetchone())[0] == 1

    run_scenario(scenario)


def test_existing_pair_conflicts_if_origin_owner_context_changes():
    async def scenario(pool):
        owner_id, buyer_id, listing_id = await seed_users_and_listing(pool)
        other_owner_id = uuid4()
        async with pool.connection() as connection:
            await connection.execute(
                "INSERT INTO identity.users (id, account_class, status) "
                "VALUES (%s, 'regular', 'active')",
                (other_owner_id,),
            )
        operations = PostgresThreadCreationOperations(pool, eligibility_double()[0])
        first = await operations.open_or_create_listing_conversation(
            caller(buyer_id),
            ListingConversationContext(listing_id=listing_id, owner_id=owner_id),
        )
        with pytest.raises(PublicError) as error:
            await operations.open_or_create_listing_conversation(
                caller(buyer_id),
                ListingConversationContext(
                    listing_id=listing_id, owner_id=other_owner_id
                ),
            )
        assert error.value.spec.status == 409
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT counterparty_id FROM conversations.threads WHERE id = %s",
                (first.conversation_id,),
            )
            assert (await cursor.fetchone())[0] == owner_id

    run_scenario(scenario)


def test_temporary_buyer_can_start_listing_thread_but_owner_must_be_regular():
    async def scenario(pool):
        owner_id, buyer_id, listing_id = await seed_users_and_listing(
            pool, temporary_buyer=True
        )
        check, calls = eligibility_double()
        operations = PostgresThreadCreationOperations(pool, check)
        result = await operations.open_or_create_listing_conversation(
            caller(buyer_id, "temporary"),
            ListingConversationContext(listing_id=listing_id, owner_id=owner_id),
        )
        assert result.created is True
        assert calls == [(buyer_id, "temporary"), (owner_id, "regular")]

    run_scenario(scenario)


def test_wanted_request_creation_requires_regular_responder_and_notifies_author():
    async def scenario(pool):
        author_id, responder_id, request_id = await seed_users_and_request(pool)
        check, calls = eligibility_double()
        operations = PostgresThreadCreationOperations(pool, check)
        result = await operations.open_or_create_wanted_conversation(
            caller(responder_id),
            WantedConversationContext(request_id=request_id, author_id=author_id),
        )
        assert result.created is True
        assert calls == [(responder_id, "regular"), (author_id, None)]
        retry = await operations.open_or_create_wanted_conversation(
            caller(responder_id),
            WantedConversationContext(request_id=request_id, author_id=author_id),
        )
        assert retry.conversation_id == result.conversation_id
        assert retry.created is False
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT wanted_request_id, initiator_id, counterparty_id "
                "FROM conversations.threads WHERE id = %s",
                (result.conversation_id,),
            )
            assert await cursor.fetchone() == (request_id, responder_id, author_id)
            cursor = await connection.execute(
                "SELECT recipient_id, event_kind FROM conversations.notification_intents "
                "WHERE conversation_id = %s",
                (result.conversation_id,),
            )
            assert await cursor.fetchone() == (author_id, "new_conversation")
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.notification_intents "
                "WHERE conversation_id = %s",
                (result.conversation_id,),
            )
            assert (await cursor.fetchone())[0] == 1

    run_scenario(scenario)


def test_concurrent_wanted_request_creates_return_one_thread_and_one_intent():
    async def scenario(pool):
        author_id, responder_id, request_id = await seed_users_and_request(pool)
        operations = PostgresThreadCreationOperations(pool, eligibility_double()[0])
        request = WantedConversationContext(request_id=request_id, author_id=author_id)
        results = await asyncio.gather(
            operations.open_or_create_wanted_conversation(
                caller(responder_id), request
            ),
            operations.open_or_create_wanted_conversation(
                caller(responder_id), request
            ),
        )
        assert {result.created for result in results} == {False, True}
        assert results[0].conversation_id == results[1].conversation_id
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.threads WHERE wanted_request_id = %s",
                (request_id,),
            )
            assert (await cursor.fetchone())[0] == 1
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.notification_intents "
                "WHERE conversation_id = %s",
                (results[0].conversation_id,),
            )
            assert (await cursor.fetchone())[0] == 1

    run_scenario(scenario, max_size=2)


def test_temporary_account_cannot_start_wanted_request_response():
    async def scenario(pool):
        author_id, responder_id, request_id = await seed_users_and_request(pool)
        operations = PostgresThreadCreationOperations(pool, eligibility_double()[0])
        with pytest.raises(PublicError) as error:
            await operations.open_or_create_wanted_conversation(
                caller(responder_id, "temporary"),
                WantedConversationContext(request_id=request_id, author_id=author_id),
            )
        assert error.value.spec.status == 403
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.threads WHERE wanted_request_id = %s",
                (request_id,),
            )
            assert (await cursor.fetchone())[0] == 0

    run_scenario(scenario)


def test_self_conversation_and_ineligible_participant_fail_without_writes():
    async def scenario(pool):
        owner_id, buyer_id, listing_id = await seed_users_and_listing(pool)
        operations = PostgresThreadCreationOperations(pool, eligibility_double()[0])
        with pytest.raises(PublicError) as error:
            await operations.open_or_create_listing_conversation(
                caller(owner_id),
                ListingConversationContext(listing_id=listing_id, owner_id=owner_id),
            )
        assert error.value.spec.status == 403

        check, _ = eligibility_double(ineligible={owner_id})
        operations = PostgresThreadCreationOperations(pool, check)
        with pytest.raises(PublicError) as error:
            await operations.open_or_create_listing_conversation(
                caller(buyer_id),
                ListingConversationContext(listing_id=listing_id, owner_id=owner_id),
            )
        assert error.value.spec.status == 403
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.threads WHERE listing_id = %s",
                (listing_id,),
            )
            assert (await cursor.fetchone())[0] == 0

    run_scenario(scenario)


def test_identity_outage_fails_closed_before_database_write():
    async def scenario(pool):
        author_id, responder_id, request_id = await seed_users_and_request(pool)
        operations = PostgresThreadCreationOperations(
            pool, eligibility_double(fail=True)[0]
        )
        with pytest.raises(PublicError) as error:
            await operations.open_or_create_wanted_conversation(
                caller(responder_id),
                WantedConversationContext(request_id=request_id, author_id=author_id),
            )
        assert error.value.spec.status == 503
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.threads WHERE wanted_request_id = %s",
                (request_id,),
            )
            assert (await cursor.fetchone())[0] == 0

    run_scenario(scenario)


def test_concurrent_listing_creates_return_one_thread_and_one_notification():
    async def scenario(pool):
        owner_id, buyer_id, listing_id = await seed_users_and_listing(pool)
        operations = PostgresThreadCreationOperations(pool, eligibility_double()[0])
        request = ListingConversationContext(listing_id=listing_id, owner_id=owner_id)
        results = await asyncio.gather(
            operations.open_or_create_listing_conversation(caller(buyer_id), request),
            operations.open_or_create_listing_conversation(caller(buyer_id), request),
        )
        assert {result.created for result in results} == {False, True}
        assert results[0].conversation_id == results[1].conversation_id
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.threads WHERE listing_id = %s",
                (listing_id,),
            )
            assert (await cursor.fetchone())[0] == 1
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.notification_intents "
                "WHERE conversation_id = %s",
                (results[0].conversation_id,),
            )
            assert (await cursor.fetchone())[0] == 1

    run_scenario(scenario, max_size=2)


def test_real_search_response_uses_identity_and_closed_exact_pair_lookup():
    """Real owner SQL and public eligibility cooperate without sharing sessions."""
    import psycopg
    from psycopg.rows import dict_row
    from app.core.runtime_bindings import runtime_scope
    from app.domains.identity.capabilities import PostgresCapabilities
    from app.domains.conversations.provider import PostgresConversationServices
    from app.domains.search.wanted_response import WantedResponseService
    from app.domains.search.wanted_store import PostgresWantedStore

    async def scenario(pool):
        author, responder, request_id = await seed_users_and_request(pool)
        services = PostgresConversationServices(pool)
        capabilities = PostgresCapabilities(
            lambda: psycopg.connect(TEST_DATABASE_DSN), lambda: datetime.now(UTC)
        )
        search_pool = AsyncConnectionPool(
            conninfo=TEST_DATABASE_DSN,
            kwargs={"row_factory": dict_row},
            min_size=0,
            max_size=2,
            open=False,
        )
        await search_pool.open(wait=True)
        try:
            with runtime_scope(
                {
                    "identity.check_account_eligibility": capabilities.check_account_eligibility
                }
            ):
                lookup = ExistingWantedConversationLookup(request_id=request_id)
                assert (
                    await services.find_existing_wanted_conversation(
                        caller(responder), lookup
                    )
                    is None
                )
                response = WantedResponseService(
                    PostgresWantedStore(search_pool), conversations=services
                )
                first = await response.respond(caller(responder), request_id)
                assert first.created is True
                repeat = await response.respond(caller(responder), request_id)
                assert (
                    repeat.conversation_id == first.conversation_id
                    and repeat.created is False
                )
                async with pool.connection() as connection:
                    await connection.execute(
                        "UPDATE search.wanted_requests SET status='unavailable' WHERE id=%s",
                        (request_id,),
                    )
                closed = await response.respond(caller(responder), request_id)
                assert (
                    closed.conversation_id == first.conversation_id
                    and closed.created is False
                )
                with pytest.raises(PublicError) as absent:
                    await response.respond(caller(author), request_id)
                assert absent.value.spec.status == 403
                stranger = uuid4()
                async with pool.connection() as connection:
                    await connection.execute(
                        "INSERT INTO identity.users (id,account_class,status) VALUES (%s,'regular','active')",
                        (stranger,),
                    )
                with pytest.raises(PublicError) as no_pair:
                    await response.respond(caller(stranger), request_id)
                assert no_pair.value.spec.status == 404
                assert (
                    await services.find_existing_wanted_conversation(
                        caller(stranger), lookup
                    )
                    is None
                )
                with pytest.raises(PublicError) as temporary:
                    await response.respond(caller(responder, "temporary"), request_id)
                assert temporary.value.spec.status == 403
                async with pool.connection() as connection:
                    cursor = await connection.execute(
                        "SELECT count(*) FROM conversations.threads WHERE wanted_request_id=%s",
                        (request_id,),
                    )
                    assert (await cursor.fetchone())[0] == 1
                    cursor = await connection.execute(
                        "SELECT count(*) FROM conversations.notification_intents WHERE conversation_id=%s",
                        (first.conversation_id,),
                    )
                    assert (await cursor.fetchone())[0] == 1
        finally:
            await search_pool.close()

    run_scenario(scenario, max_size=2)
