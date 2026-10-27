"""Database integration checks for the Conversations retirement operations.

These tests run only through the loopback-only disposable PostgreSQL harness.
They use synthetic identities and origins, never a developer or shared database.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import os
from uuid import UUID, uuid4

import pytest
from psycopg_pool import AsyncConnectionPool

from app.contracts.domain_types import (
    OriginActivityRequest,
    OriginOwnerContext,
    OriginRetirementCommand,
)
from app.core.errors import PublicError
from app.domains.conversations.origin_retirement import (
    PostgresOriginRetirementOperations,
)

TEST_DATABASE_DSN = os.environ.get("CLIP_TEST_DATABASE_DSN")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_DSN is None,
    reason="run through scripts/check_conversations_retirement.py",
)


def run_scenario(scenario, *, max_size: int = 1) -> None:
    """Give each scenario one isolated async pool and close it on every path."""

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
            await scenario(PostgresOriginRetirementOperations(pool), pool)
        finally:
            await pool.close()

    asyncio.run(run())


async def seed_origin(
    pool, kind: str, activity_times, *, marked=()
) -> tuple[UUID, list[UUID]]:
    """Create synthetic owner, origin and thread rows in the disposable DB."""
    origin_id = uuid4()
    owner_id = uuid4()
    buyer_ids = [uuid4() for _ in activity_times]
    thread_ids = [uuid4() for _ in activity_times]
    upload_id = uuid4()
    image_id = uuid4()
    object_key = f"test/origin-retirement/{image_id}"
    category_id = None
    async with pool.connection() as connection:
        async with connection.transaction():
            cursor = await connection.execute(
                "SELECT id FROM listings.categories WHERE code = 'other'"
            )
            category_id = (await cursor.fetchone())[0]
            await connection.execute(
                "INSERT INTO identity.users (id, account_class, status) "
                "VALUES (%s, 'regular', 'active')",
                (owner_id,),
            )
            for buyer_id in buyer_ids:
                await connection.execute(
                    "INSERT INTO identity.users (id, account_class, status) "
                    "VALUES (%s, 'regular', 'active')",
                    (buyer_id,),
                )
            if kind == "sale_listing":
                await connection.execute(
                    "INSERT INTO listings.sale_listings "
                    "(id, owner_id, title, description, category_id, condition_code, "
                    "asking_price_paise, negotiable, pickup_area, availability) "
                    "VALUES (%s, %s, 'Synthetic item', 'Test-only description', %s, "
                    "'good', 100, false, 'Test area', 'available')",
                    (origin_id, owner_id, category_id),
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
                    (image_id, origin_id, upload_id, object_key),
                )
            else:
                await connection.execute(
                    "INSERT INTO search.wanted_requests "
                    "(id, author_id, title, description, category_code, budget_paise, status) "
                    "VALUES (%s, %s, 'Synthetic request', 'Test-only description', %s, 100, 'open')",
                    (origin_id, owner_id, "other"),
                )
            for index, (buyer_id, thread_id, activity) in enumerate(
                zip(buyer_ids, thread_ids, activity_times, strict=True)
            ):
                if kind == "sale_listing":
                    origin_column = "listing_id"
                else:
                    origin_column = "wanted_request_id"
                await connection.execute(
                    "INSERT INTO conversations.threads "
                    f"(id, {origin_column}, initiator_id, counterparty_id, created_at, last_activity_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (thread_id, origin_id, buyer_id, owner_id, activity, activity),
                )
                await connection.execute(
                    "INSERT INTO conversations.members (conversation_id, user_id) "
                    "VALUES (%s, %s), (%s, %s)",
                    (thread_id, buyer_id, thread_id, owner_id),
                )
                if index in marked:
                    await connection.execute(
                        "UPDATE conversations.threads "
                        "SET participant_writes_disabled_at = clock_timestamp() WHERE id = %s",
                        (thread_id,),
                    )
    return origin_id, thread_ids


def context(kind: str) -> OriginOwnerContext:
    """Build the server-only owner marker used by these isolated tests."""
    return OriginOwnerContext(origin_kind=kind)


def activity_request(kind: str, origin_id: UUID) -> OriginActivityRequest:
    """Build an owner-scoped query that contains no participant or content data."""
    return OriginActivityRequest(origin_kind=kind, origin_id=origin_id)


def retirement_command(
    kind: str, origin_id: UUID, operation_id: UUID, cutoff: datetime
):
    """Build a stable retirement request with an explicit UTC cutoff."""
    return OriginRetirementCommand(
        origin_kind=kind,
        origin_id=origin_id,
        operation_id=operation_id,
        cutoff_utc=cutoff,
    )


def test_activity_returns_zero_and_null_for_an_origin_without_threads():
    async def scenario(operations, pool):
        origin_id, _ = await seed_origin(pool, "sale_listing", [])
        result = await operations.get_origin_activity(
            context("sale_listing"), activity_request("sale_listing", origin_id)
        )
        assert result.thread_count == 0
        assert result.latest_participant_write_at is None

    run_scenario(scenario)


def test_activity_aggregates_only_count_and_latest_time_for_wanted_request():
    async def scenario(operations, pool):
        first = datetime(2026, 1, 1, tzinfo=UTC)
        latest = datetime(2026, 1, 3, 4, 5, 6, tzinfo=UTC)
        origin_id, _ = await seed_origin(pool, "wanted_request", [first, latest])
        result = await operations.get_origin_activity(
            context("wanted_request"),
            activity_request("wanted_request", origin_id),
        )
        assert result.thread_count == 2
        assert result.latest_participant_write_at == latest

    run_scenario(scenario)


def test_context_cannot_be_used_for_a_different_origin_kind():
    async def scenario(operations, pool):
        origin_id, _ = await seed_origin(pool, "sale_listing", [])
        with pytest.raises(PublicError) as error:
            await operations.get_origin_activity(
                context("wanted_request"), activity_request("sale_listing", origin_id)
            )
        assert error.value.spec.status == 403

    run_scenario(scenario)


def test_zero_thread_retirement_is_success_and_retry_returns_stored_result():
    async def scenario(operations, pool):
        origin_id, _ = await seed_origin(pool, "sale_listing", [])
        command = retirement_command(
            "sale_listing", origin_id, uuid4(), datetime.now(UTC)
        )
        first = await operations.mark_origin_retired(context("sale_listing"), command)
        retry = await operations.mark_origin_retired(context("sale_listing"), command)
        assert first.model_dump() == {"outcome": "marked", "marked_count": 0}
        assert retry == first

    run_scenario(scenario)


def test_eligible_threads_are_marked_atomically_and_retry_is_idempotent():
    async def scenario(operations, pool):
        old = datetime(2026, 1, 1, tzinfo=UTC)
        origin_id, thread_ids = await seed_origin(pool, "sale_listing", [old, old])
        command = retirement_command(
            "sale_listing", origin_id, uuid4(), datetime(2026, 4, 1, tzinfo=UTC)
        )
        first = await operations.mark_origin_retired(context("sale_listing"), command)
        retry = await operations.mark_origin_retired(context("sale_listing"), command)
        assert first.model_dump() == {"outcome": "marked", "marked_count": 2}
        assert retry == first
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.threads "
                "WHERE id = ANY(%s) AND participant_writes_disabled_at IS NOT NULL",
                (thread_ids,),
            )
            assert (await cursor.fetchone())[0] == 2

    run_scenario(scenario)


def test_recent_thread_blocks_all_markers_and_retry_returns_blocked_result():
    async def scenario(operations, pool):
        cutoff = datetime.now(UTC) - timedelta(days=90)
        old = cutoff - timedelta(days=1)
        recent = cutoff + timedelta(seconds=1)
        origin_id, thread_ids = await seed_origin(pool, "wanted_request", [old, recent])
        command = retirement_command("wanted_request", origin_id, uuid4(), cutoff)
        first = await operations.mark_origin_retired(context("wanted_request"), command)
        retry = await operations.mark_origin_retired(context("wanted_request"), command)
        assert first.model_dump() == {
            "outcome": "blocked_recent_activity",
            "marked_count": 0,
        }
        assert retry == first
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.threads "
                "WHERE id = ANY(%s) AND participant_writes_disabled_at IS NOT NULL",
                (thread_ids,),
            )
            assert (await cursor.fetchone())[0] == 0

    run_scenario(scenario)


def test_already_marked_reports_existing_count_and_persists_new_operation_result():
    async def scenario(operations, pool):
        old = datetime(2026, 1, 1, tzinfo=UTC)
        origin_id, _ = await seed_origin(
            pool, "wanted_request", [old, old], marked={0, 1}
        )
        command = retirement_command(
            "wanted_request", origin_id, uuid4(), datetime(2026, 4, 1, tzinfo=UTC)
        )
        result = await operations.mark_origin_retired(
            context("wanted_request"), command
        )
        retry = await operations.mark_origin_retired(context("wanted_request"), command)
        assert result.model_dump() == {"outcome": "already_marked", "marked_count": 2}
        assert retry == result

    run_scenario(scenario)


def test_mixed_marker_state_fails_closed_without_recording_an_outcome():
    async def scenario(operations, pool):
        old = datetime(2026, 1, 1, tzinfo=UTC)
        origin_id, _ = await seed_origin(pool, "sale_listing", [old, old], marked={0})
        operation_id = uuid4()
        command = retirement_command(
            "sale_listing", origin_id, operation_id, datetime(2026, 4, 1, tzinfo=UTC)
        )
        with pytest.raises(PublicError) as error:
            await operations.mark_origin_retired(context("sale_listing"), command)
        assert error.value.spec.status == 409
        async with pool.connection() as connection:
            cursor = await connection.execute(
                "SELECT count(*) FROM conversations.origin_retirement_operations "
                "WHERE operation_id = %s",
                (operation_id,),
            )
            assert (await cursor.fetchone())[0] == 0

    run_scenario(scenario)


def test_operation_id_cannot_be_reused_for_another_origin_or_cutoff():
    async def scenario(operations, pool):
        first_id, _ = await seed_origin(pool, "sale_listing", [])
        second_id, _ = await seed_origin(pool, "wanted_request", [])
        operation_id = uuid4()
        cutoff = datetime.now(UTC)
        first = retirement_command("sale_listing", first_id, operation_id, cutoff)
        await operations.mark_origin_retired(context("sale_listing"), first)
        conflicting_requests = (
            retirement_command(
                "sale_listing", first_id, operation_id, cutoff + timedelta(seconds=1)
            ),
            retirement_command("wanted_request", second_id, operation_id, cutoff),
        )
        for request in conflicting_requests:
            with pytest.raises(PublicError) as error:
                await operations.mark_origin_retired(
                    context(request.origin_kind), request
                )
            assert error.value.spec.status == 409

    run_scenario(scenario)


def test_concurrent_same_operation_returns_one_stored_outcome():
    async def scenario(operations, pool):
        old = datetime(2026, 1, 1, tzinfo=UTC)
        origin_id, _ = await seed_origin(pool, "sale_listing", [old])
        command = retirement_command(
            "sale_listing", origin_id, uuid4(), datetime(2026, 4, 1, tzinfo=UTC)
        )
        results = await asyncio.gather(
            operations.mark_origin_retired(context("sale_listing"), command),
            operations.mark_origin_retired(context("sale_listing"), command),
        )
        assert results[0] == results[1]
        assert results[0].model_dump() == {"outcome": "marked", "marked_count": 1}

    run_scenario(scenario, max_size=2)
