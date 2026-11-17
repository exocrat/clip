"""Unit tests for the in-process image-cleanup scheduler (issue #69).

These use lightweight fakes for the pool and the cleanup service, so they run
without a database and assert the leader-gating, pass loop, deferral handling,
and cancellable scheduler loop directly.
"""

import asyncio

import pytest

from app.core.errors import ERRORS, PublicError
import app.domains.listings.image_cleanup_scheduler as scheduler


class FakeCursor:
    def __init__(self, row):
        self._row = row

    async def fetchone(self):
        return self._row


class FakeConnection:
    """Record the advisory lock/unlock SQL a cycle issues."""

    def __init__(self, held: bool):
        self._held = held
        self.unlocked = False

    async def execute(self, sql, params=None):
        if "pg_try_advisory_lock" in sql:
            return FakeCursor({"held": self._held})
        if "pg_advisory_unlock" in sql:
            self.unlocked = True
            return FakeCursor(None)
        raise AssertionError(f"unexpected sql: {sql}")


class FakePool:
    def __init__(self, connection: FakeConnection):
        self._connection = connection

    def connection(self):
        connection = self._connection

        class _Ctx:
            async def __aenter__(self):
                return connection

            async def __aexit__(self, *exc):
                return False

        return _Ctx()


class FakeService:
    """Return a scripted sequence of reclaimed counts, optionally then a 503."""

    def __init__(self, counts=None, raise_503_after=None):
        self._counts = list(counts or [])
        self._raise_503_after = raise_503_after
        self.calls = 0

    async def cleanup_image_objects(self, limit):
        self.calls += 1
        if self._raise_503_after is not None and self.calls > self._raise_503_after:
            raise PublicError(ERRORS[503])
        return self._counts.pop(0) if self._counts else 0


def test_non_leader_skips_without_touching_storage():
    connection = FakeConnection(held=False)
    service = FakeService(counts=[100])
    result = asyncio.run(scheduler.run_cleanup_cycle(FakePool(connection), service))
    assert result == {"leader": False, "deleted": 0, "passes": 0, "deferred": False}
    assert service.calls == 0
    assert connection.unlocked is False


def test_leader_runs_until_a_pass_reclaims_nothing_then_unlocks():
    connection = FakeConnection(held=True)
    service = FakeService(counts=[100, 40, 0])
    result = asyncio.run(scheduler.run_cleanup_cycle(FakePool(connection), service))
    assert result == {"leader": True, "deleted": 140, "passes": 3, "deferred": False}
    assert connection.unlocked is True


def test_leader_stops_and_unlocks_when_deletes_are_deferred():
    connection = FakeConnection(held=True)
    # First pass reclaims 100; the second raises 503 (uncertain deletes deferred).
    service = FakeService(counts=[100], raise_503_after=1)
    result = asyncio.run(scheduler.run_cleanup_cycle(FakePool(connection), service))
    assert result["leader"] is True
    assert result["deleted"] == 100
    assert result["deferred"] is True
    assert connection.unlocked is True


def test_non_503_public_error_propagates():
    connection = FakeConnection(held=True)

    class Boom(FakeService):
        async def cleanup_image_objects(self, limit):
            raise PublicError(ERRORS[409])

    with pytest.raises(PublicError):
        asyncio.run(scheduler.run_cleanup_cycle(FakePool(connection), Boom()))
    # The lock is still released on the way out.
    assert connection.unlocked is True


def test_scheduler_runs_a_cycle_then_cancels_cleanly(monkeypatch):
    async def scenario():
        ran = asyncio.Event()
        calls: list[int] = []

        async def fake_cycle(pool, service, batch_size):
            calls.append(batch_size)
            ran.set()
            return {"leader": True, "deleted": 1, "passes": 1, "deferred": False}

        monkeypatch.setattr(scheduler, "run_cleanup_cycle", fake_cycle)
        task = asyncio.create_task(
            scheduler.run_scheduler(
                None, None, interval_seconds=1000, initial_delay_seconds=0, batch_size=7
            )
        )
        await asyncio.wait_for(ran.wait(), timeout=2)
        task.cancel()
        await task  # run_scheduler swallows CancelledError and returns.
        assert calls == [7]

    asyncio.run(scenario())
