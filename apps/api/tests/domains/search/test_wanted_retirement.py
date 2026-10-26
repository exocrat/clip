"""Coordinator checks through reviewed store/Conversations contracts only."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.contracts.domain_types import OriginActivityResult, RetirementMarkerResult
from app.core.errors import PublicError
from app.domains.search.wanted_retirement import (
    PendingWantedRetirement,
    WantedRetirementService,
)
from apps.api.tests.domains.search.doubles.wanted_retirement import (
    ConversationsRetirementDouble,
)

NOW = datetime(2026, 10, 25, tzinfo=UTC)


def setup():
    """Script committed pending identity without pretending to evaluate SQL."""
    pending = PendingWantedRetirement(uuid4(), NOW - timedelta(days=90))
    store = AsyncMock()
    store.begin_retirement.return_value = pending
    return store, pending, uuid4()


def test_ineligible_or_retired_does_not_call_dependency():
    async def exercise():
        store, _, identifier = setup()
        store.begin_retirement.return_value = None
        provider = AsyncMock()
        assert (
            await WantedRetirementService(store, provider, lambda: NOW).retire(
                identifier
            )
            is None
        )
        provider.get_origin_activity.assert_not_awaited()
        store.finalize_retirement.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "count,delta,blocked",
    [(0, None, False), (3, -1, False), (3, 0, False), (3, 1, True)],
)
def test_exact_ninety_day_cutoff_and_complete_marker(count, delta, blocked):
    async def exercise():
        store, pending, identifier = setup()
        latest = (
            None
            if delta is None
            else pending.cutoff_utc + timedelta(microseconds=delta)
        )
        provider = ConversationsRetirementDouble(count, latest)
        result = await WantedRetirementService(store, provider, lambda: NOW).retire(
            identifier
        )
        assert result.outcome == ("blocked_recent_activity" if blocked else "marked")
        assert provider.markers[0].operation_id == pending.operation_id
        assert provider.markers[0].cutoff_utc == pending.cutoff_utc
        if blocked:
            store.clear_retirement.assert_awaited_once_with(identifier, pending)
            store.finalize_retirement.assert_not_awaited()
        else:
            store.finalize_retirement.assert_awaited_once_with(identifier, pending, NOW)
            store.clear_retirement.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize("stage", ["preflight", "marker"])
@pytest.mark.parametrize(
    "error", [NotImplementedError, TimeoutError, OSError, RuntimeError]
)
def test_dependency_failure_preserves_pending_pair(stage, error):
    async def exercise():
        store, _, identifier = setup()
        provider = ConversationsRetirementDouble()
        if stage == "preflight":
            provider.activity_error = error("controlled")
        else:
            provider.marker_error = error("controlled")
        with pytest.raises(PublicError) as failure:
            await WantedRetirementService(store, provider, lambda: NOW).retire(
                identifier
            )
        assert failure.value.spec.status == 503
        store.clear_retirement.assert_not_awaited()
        store.finalize_retirement.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "activity",
    [
        None,
        OriginActivityResult(thread_count=1, latest_participant_write_at=None),
        OriginActivityResult(thread_count=0, latest_participant_write_at=NOW),
    ],
)
def test_incomplete_preflight_never_calls_marker(activity):
    async def exercise():
        store, _, identifier = setup()
        provider = AsyncMock()
        provider.get_origin_activity.return_value = activity
        with pytest.raises(PublicError) as failure:
            await WantedRetirementService(store, provider, lambda: NOW).retire(
                identifier
            )
        assert failure.value.spec.status == 503
        provider.mark_origin_retired.assert_not_awaited()
        store.clear_retirement.assert_not_awaited()

    asyncio.run(exercise())


def test_invalid_blocked_count_keeps_pending_and_real_default_fails_closed():
    async def exercise():
        store, _, identifier = setup()
        provider = AsyncMock()
        provider.get_origin_activity.return_value = OriginActivityResult(
            thread_count=0, latest_participant_write_at=None
        )
        provider.mark_origin_retired.return_value = RetirementMarkerResult(
            outcome="blocked_recent_activity", marked_count=1
        )
        with pytest.raises(PublicError) as failure:
            await WantedRetirementService(store, provider, lambda: NOW).retire(
                identifier
            )
        assert failure.value.spec.status == 503
        store.clear_retirement.assert_not_awaited()
        with pytest.raises(PublicError) as failure:
            await WantedRetirementService(store, clock=lambda: NOW).retire(identifier)
        assert failure.value.spec.status == 503

    asyncio.run(exercise())


def test_unknown_committed_marker_reuses_same_pair_after_clock_advances():
    async def exercise():
        store, pending, identifier = setup()
        provider = ConversationsRetirementDouble(2, NOW - timedelta(days=91))
        provider.lose_result_once = True
        service = WantedRetirementService(store, provider, lambda: NOW)
        with pytest.raises(PublicError):
            await service.retire(identifier)
        store.finalize_retirement.assert_not_awaited()
        service.clock = lambda: NOW + timedelta(days=1)
        assert (await service.retire(identifier)).outcome == "marked"
        assert provider.markers[0] == provider.markers[1]
        assert provider.effects == 1
        store.finalize_retirement.assert_awaited_once_with(
            identifier, pending, NOW + timedelta(days=1)
        )

    asyncio.run(exercise())


def test_deadline_and_clock_regression_leave_pending(monkeypatch):
    async def exercise():
        from app.domains.search import wanted_retirement as module

        store, _, identifier = setup()
        provider = AsyncMock()

        async def hang(*args):
            """A cooperative stalled public dependency must be cancelled."""
            await asyncio.Event().wait()

        provider.get_origin_activity.side_effect = hang
        monkeypatch.setattr(module, "_DEPENDENCY_TIMEOUT", 0.01)
        with pytest.raises(PublicError):
            await WantedRetirementService(store, provider, lambda: NOW).retire(
                identifier
            )
        provider.get_origin_activity.reset_mock()
        with pytest.raises(PublicError):
            await WantedRetirementService(
                store, provider, lambda: NOW - timedelta(seconds=1)
            ).retire(identifier)
        provider.get_origin_activity.assert_not_awaited()
        store.clear_retirement.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize("outcome", ["marked", "already_marked"])
def test_both_confirmed_marker_outcomes_allow_atomic_finalization(outcome):
    """A retained authoritative already-marked result is safe to resume."""

    async def exercise():
        store, pending, identifier = setup()
        provider = AsyncMock()
        provider.get_origin_activity.return_value = OriginActivityResult(
            thread_count=0, latest_participant_write_at=None
        )
        provider.mark_origin_retired.return_value = RetirementMarkerResult(
            outcome=outcome, marked_count=0
        )
        assert (
            await WantedRetirementService(store, provider, lambda: NOW).retire(
                identifier
            )
        ).outcome == outcome
        store.finalize_retirement.assert_awaited_once_with(identifier, pending, NOW)

    asyncio.run(exercise())


def test_external_cancellation_does_not_clear_pending_or_start_cleanup():
    """Cancellation propagates without treating an unknown provider result as safe."""

    async def exercise():
        store, _, identifier = setup()
        provider = AsyncMock()
        entered = asyncio.Event()

        async def hang(*args):
            """Signal that the committed-pending phase already finished."""
            entered.set()
            await asyncio.Event().wait()

        provider.get_origin_activity.side_effect = hang
        task = asyncio.create_task(
            WantedRetirementService(store, provider, lambda: NOW).retire(identifier)
        )
        await asyncio.wait_for(entered.wait(), timeout=1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        store.finalize_retirement.assert_not_awaited()
        store.clear_retirement.assert_not_awaited()

    asyncio.run(exercise())
