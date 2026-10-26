"""Approved wanted cleanup on real PostgreSQL, with explicit Conversations fixture.

All records/temporary failure triggers belong to the runner's fresh private DB.
No real Conversations locks, cloud cleanup or existing target is claimed here.
Immutable origin/key fixtures remain retained in the stopped disposable cluster.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from psycopg import AsyncConnection, sql
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
import pytest

from app.core.auth import CallerContext
from app.core.errors import PublicError
from app.domains.search.wanted import WantedService
from app.domains.search.wanted_models import WantedCreate, WantedState
from app.domains.search.wanted_retirement import (
    PendingWantedRetirement,
    WantedRetirementService,
)
from app.domains.search.wanted_store import PostgresWantedStore
from apps.api.tests.domains.listings.test_embedding_postgres import connect, target
from apps.api.tests.domains.search.doubles.wanted_retirement import (
    ConversationsRetirementDouble,
)
from apps.api.tests.domains.search.test_wanted_postgres import Dependencies


class Harness:
    """Own synthetic identity/requests; use real store and authorization service."""

    def __init__(self, pool, author):
        self.pool, self.author = pool, author
        self.store = PostgresWantedStore(pool)
        self.now = datetime.now(UTC)
        self.caller = CallerContext(author, "regular", self.now + timedelta(minutes=10))
        self.api = WantedService(self.store, Dependencies({author}))

    async def seed(self, delta=timedelta(), receipts=True):
        """Place an old unavailable fixture around the exact180day cutoff."""
        identifier, create_key = uuid4(), uuid4()
        async with self.pool.connection() as connection:
            await connection.execute(
                "INSERT INTO search.wanted_requests(id,author_id,title,description,category_code,budget_paise,status,created_at,closed_at) "
                "VALUES(%s,%s,'Synthetic retirement request','Controlled retirement fixture','books',1000,'unavailable',%s,%s)",
                (
                    identifier,
                    self.author,
                    self.now - timedelta(days=400),
                    self.now - timedelta(days=180) + delta,
                ),
            )
            if receipts:
                for kind in ["create", "edit", "state"]:
                    await connection.execute(
                        "INSERT INTO search.wanted_command_results(author_id,scope_id,command_kind,operation_id,request_id,request_payload,result_payload) "
                        "VALUES(%s,%s,%s,%s,%s,jsonb_build_object('synthetic','intent'),jsonb_build_object('synthetic','result'))",
                        (
                            self.author,
                            self.author if kind == "create" else identifier,
                            kind,
                            create_key if kind == "create" else uuid4(),
                            identifier,
                        ),
                    )
        return identifier, create_key

    async def row(self, identifier):
        """Inspect only this controlled fixture's local state."""
        async with self.pool.connection() as connection:
            return await (
                await connection.execute(
                    "SELECT * FROM search.wanted_requests WHERE id=%s", (identifier,)
                )
            ).fetchone()

    async def receipts(self, identifier):
        """Check every retained key and content-bearing payload of this fixture."""
        async with self.pool.connection() as connection:
            return await (
                await connection.execute(
                    "SELECT * FROM search.wanted_command_results WHERE request_id=%s ORDER BY command_kind",
                    (identifier,),
                )
            ).fetchall()


@asynccontextmanager
async def harness():
    """Validate exact disposable target before opening a bounded owned pool."""
    value = target()
    async with await connect(value):
        pass
    pool = AsyncConnectionPool[AsyncConnection[dict]](
        value, kwargs={"row_factory": dict_row}, min_size=1, max_size=4, open=False
    )
    await pool.open()
    try:
        await pool.wait(timeout=5)
        author = uuid4()
        async with pool.connection() as connection:
            await connection.execute(
                "INSERT INTO identity.users(id,account_class,status,display_name) VALUES(%s,'regular','active','Synthetic retirement author')",
                (author,),
            )
        yield Harness(pool, author)
    finally:
        await pool.close()


def test_native_retirement_180day_anchor_reset_and_pair_fences():
    asyncio.run(anchor_checks())


async def anchor_checks():
    """Validate microsecond boundary, exact pair fences and reopen/reset in SQL."""
    async with harness() as h:
        young, _ = await h.seed(timedelta(microseconds=1))
        assert await h.store.begin_retirement(young, h.now) is None
        identifier, _ = await h.seed()
        pending = await h.store.begin_retirement(identifier, h.now)
        assert pending is not None and pending.cutoff_utc == h.now - timedelta(days=90)
        assert (
            await h.store.begin_retirement(identifier, h.now + timedelta(seconds=1))
            == pending
        )
        wrong = PendingWantedRetirement(
            pending.operation_id, pending.cutoff_utc - timedelta(microseconds=1)
        )
        for action in [
            lambda: h.store.clear_retirement(identifier, wrong),
            lambda: h.store.finalize_retirement(identifier, wrong, h.now),
            lambda: h.store.finalize_retirement(
                identifier, pending, h.now - timedelta(microseconds=1)
            ),
        ]:
            with pytest.raises(PublicError) as failure:
                await action()
            assert failure.value.spec.status == 409
        assert all(
            row["request_payload"] is not None for row in await h.receipts(identifier)
        )
        await h.store.clear_retirement(identifier, pending)
        reopened = await h.api.state(
            h.caller,
            identifier,
            WantedState(expected_revision=1, state="open", operation_id=uuid4()),
        )
        assert (await h.row(identifier))["closed_at"] is None
        assert await h.store.begin_retirement(identifier, datetime.now(UTC)) is None
        await h.api.state(
            h.caller,
            identifier,
            WantedState(
                expected_revision=reopened.revision,
                state="unavailable",
                operation_id=uuid4(),
            ),
        )
        assert (await h.row(identifier))["closed_at"] > h.now - timedelta(days=1)
        assert await h.store.begin_retirement(identifier, datetime.now(UTC)) is None


def test_native_retirement_lost_result_blocked_retry_and_scrubbed_visibility():
    asyncio.run(replay_checks())


async def replay_checks():
    """Real persisted retries scrub all copies and preserve content-free keys."""
    async with harness() as h:
        identifier, key = await h.seed()
        before = await h.receipts(identifier)
        provider = ConversationsRetirementDouble(3, h.now - timedelta(days=91))
        provider.lose_result_once = True
        service = WantedRetirementService(h.store, provider, lambda: h.now)
        with pytest.raises(PublicError) as failure:
            await service.retire(identifier)
        assert failure.value.spec.status == 503
        pending_row = await h.row(identifier)
        assert (
            pending_row["retirement_pending_operation_id"]
            == provider.markers[0].operation_id
        )
        assert (
            pending_row["title"] is not None and await h.receipts(identifier) == before
        )
        service.clock = lambda: datetime.now(UTC)
        assert (await service.retire(identifier)).outcome == "marked"
        assert provider.markers[0] == provider.markers[1] and provider.effects == 1
        after = await h.row(identifier)
        assert after["retired_at"] is not None and after["revision"] == 2
        assert all(
            after[name] is None
            for name in [
                "title",
                "description",
                "category_code",
                "budget_paise",
                "retirement_pending_operation_id",
                "retirement_pending_cutoff_utc",
            ]
        )
        receipts = await h.receipts(identifier)
        assert len(receipts) == len(before) == 3
        assert [row["operation_id"] for row in receipts] == [
            row["operation_id"] for row in before
        ]
        assert all(
            row["request_payload"] is None and row["result_payload"] is None
            for row in receipts
        )
        assert await service.retire(identifier) is None
        for action, status in [
            (lambda: h.api.read(h.caller, identifier), 404),
            (
                lambda: h.api.state(
                    h.caller,
                    identifier,
                    WantedState(
                        expected_revision=2, state="open", operation_id=uuid4()
                    ),
                ),
                409,
            ),
            (
                lambda: h.api.create(
                    h.caller,
                    WantedCreate(
                        title="Synthetic late retry",
                        description="Controlled fixture",
                        category_code="books",
                        operation_id=key,
                    ),
                ),
                409,
            ),
        ]:
            with pytest.raises(PublicError) as failure:
                await action()
            assert failure.value.spec.status == status

        blocked, _ = await h.seed()
        recent = ConversationsRetirementDouble(2, h.now - timedelta(days=89))
        service = WantedRetirementService(h.store, recent, lambda: datetime.now(UTC))
        assert (await service.retire(blocked)).outcome == "blocked_recent_activity"
        assert (await h.row(blocked))["retirement_pending_operation_id"] is None
        assert all(
            row["request_payload"] is not None for row in await h.receipts(blocked)
        )
        first = recent.markers[0]
        recent.latest = h.now - timedelta(days=91)
        assert (await service.retire(blocked)).outcome == "marked"
        assert recent.markers[1].operation_id != first.operation_id
        assert recent.markers[1].cutoff_utc >= first.cutoff_utc


def test_native_retirement_atomic_rollback_and_competing_attempts():
    asyncio.run(atomic_checks())


async def atomic_checks():
    """Force actual SQL failure after receipt clear, then test competing callers."""
    async with harness() as h:
        identifier, _ = await h.seed()
        before = await h.receipts(identifier)
        provider = ConversationsRetirementDouble()
        service = WantedRetirementService(h.store, provider, lambda: datetime.now(UTC))
        function = "se02_failure_" + uuid4().hex
        trigger = "se02_failure_" + uuid4().hex
        async with h.pool.connection() as connection:
            await connection.execute(
                sql.SQL(
                    """CREATE FUNCTION search.{}() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN IF NEW.id::text=TG_ARGV[0] AND NEW.retired_at IS NOT NULL THEN
                    RAISE EXCEPTION 'Controlled finalization failure' USING ERRCODE='23514';
                END IF; RETURN NEW; END; $$"""
                ).format(sql.Identifier(function))
            )
            await connection.execute(
                sql.SQL(
                    "CREATE TRIGGER {} BEFORE UPDATE OF retired_at ON search.wanted_requests FOR EACH ROW EXECUTE FUNCTION search.{}({})"
                ).format(
                    sql.Identifier(trigger),
                    sql.Identifier(function),
                    sql.Literal(str(identifier)),
                )
            )
        try:
            with pytest.raises(PublicError) as failure:
                await service.retire(identifier)
            assert failure.value.spec.status == 503
            row = await h.row(identifier)
            assert (
                row["retirement_pending_operation_id"]
                == provider.markers[0].operation_id
            )
            assert row["retired_at"] is None and row["title"] is not None
            assert await h.receipts(identifier) == before
        finally:
            async with h.pool.connection() as connection:
                await connection.execute(
                    sql.SQL("DROP TRIGGER {} ON search.wanted_requests").format(
                        sql.Identifier(trigger)
                    )
                )
                await connection.execute(
                    sql.SQL("DROP FUNCTION search.{}()").format(
                        sql.Identifier(function)
                    )
                )
        assert (await service.retire(identifier)).outcome == "marked"
        assert provider.effects == 1 and provider.markers[0] == provider.markers[1]

        competing, _ = await h.seed()
        provider = ConversationsRetirementDouble()
        provider.wait_for = 2
        service = WantedRetirementService(h.store, provider, lambda: datetime.now(UTC))
        tasks = [asyncio.create_task(service.retire(competing)) for _ in range(2)]
        try:
            await asyncio.wait_for(provider.arrived.wait(), timeout=2)
            row = await h.row(competing)
            assert provider.markers[0] == provider.markers[1]
            with pytest.raises(PublicError) as failure:
                await h.api.state(
                    h.caller,
                    competing,
                    WantedState(
                        expected_revision=1, state="open", operation_id=uuid4()
                    ),
                )
            assert failure.value.spec.status == 409
            provider.release.set()
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=5)
            assert all(result.outcome == "marked" for result in results)
            assert provider.effects == 1 and (await h.row(competing))["revision"] == 2
        finally:
            provider.release.set()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
