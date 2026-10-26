"""Operator transport/refusal tests; native probe proves actual coverage/transitions."""

import asyncio
from dataclasses import replace, asdict
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from psycopg.pq import TransactionStatus
import pytest

from app.domains.listings.embedding_bootstrap import (
    EmbeddingBootstrap,
    BootstrapBlocked,
    PipelineCoverage,
    _STATUS_SQL,
)
from app.domains.listings.embedding_types import default_pipeline_spec, pipeline_spec


def report(state="building", **updates):
    value = PipelineCoverage(
        default_pipeline_spec().pipeline_id.hex(),
        state,
        state != "absent",
        False,
        3,
        3,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    return replace(value, **updates)


def connection():
    subject = MagicMock()
    subject.autocommit = True
    subject.info.transaction_status = TransactionStatus.IDLE
    subject.execute = AsyncMock()
    return subject


def test_status_is_read_only_bound_single_snapshot_and_aggregate_only():
    async def exercise():
        subject = connection()
        row = asdict(report())
        row.pop("pipeline_id")
        subject.execute.return_value.fetchone = AsyncMock(return_value=row)
        bootstrap = EmbeddingBootstrap(subject)
        observed = await bootstrap.status()
        assert observed.complete and observed == report()
        calls = [call.args for call in subject.execute.await_args_list]
        assert calls[0] == ("SET TRANSACTION READ ONLY",)
        statement, values = calls[-1]
        assert statement == _STATUS_SQL and len(values) == statement.count("%s") == 4
        assert "retirement_pending_operation_id IS NULL" in statement
        assert "availability='available'" not in statement
        assert (
            "chunk.title_min=0" in statement
            and "generation.description_count-1" in statement
        )
        assert not any(word in statement for word in ("INSERT ", "UPDATE ", "DELETE "))
        assert not {"title", "description", "vector", "listing_id"}.intersection(
            asdict(observed)
        )

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "autocommit,transaction",
    [(False, TransactionStatus.IDLE), (True, TransactionStatus.INTRANS)],
)
def test_unsafe_connection_rejected_before_sql(autocommit, transaction):
    async def exercise():
        subject = connection()
        subject.autocommit = autocommit
        subject.info.transaction_status = transaction
        with pytest.raises(ValueError):
            await EmbeddingBootstrap(subject).status()
        subject.execute.assert_not_awaited()

    asyncio.run(exercise())


def test_unsupported_space_refused_before_connection_use():
    subject = connection()
    other = pipeline_spec(
        {**default_pipeline_spec().encoding, "model_revision": "a" * 40}
    )
    with pytest.raises(BootstrapBlocked, match="unsupported_pipeline"):
        EmbeddingBootstrap(subject, other)
    subject.execute.assert_not_called()


@pytest.mark.parametrize(
    "state,register,transition",
    [
        ("absent", True, True),
        ("planned", False, True),
        ("building", False, False),
        ("serving", False, False),
    ],
)
def test_prepare_resumes_without_demotion_or_reset(state, register, transition):
    async def exercise():
        bootstrap = EmbeddingBootstrap(connection())
        bootstrap._status = AsyncMock(
            side_effect=[report(state), report("building" if transition else state)]
        )
        with (
            patch.object(bootstrap.store, "register", AsyncMock()) as registration,
            patch.object(bootstrap.store, "set_state", AsyncMock()) as change,
        ):
            result = await bootstrap.prepare()
        assert result.state == ("building" if transition else state)
        assert registration.await_count == int(register)
        assert change.await_count == int(transition)
        if transition:
            change.assert_awaited_once_with(bootstrap.spec, "building")

    asyncio.run(exercise())


@pytest.mark.parametrize("limit", [0, 1001, True, 1.5])
def test_queue_bounds_before_any_sql(limit):
    async def exercise():
        subject = connection()
        with pytest.raises(ValueError):
            await EmbeddingBootstrap(subject).queue(limit)
        subject.execute.assert_not_awaited()

    asyncio.run(exercise())


def test_queue_uses_existing_reconciliation_without_failed_retry():
    async def exercise():
        bootstrap = EmbeddingBootstrap(connection())
        bootstrap._status = AsyncMock(return_value=report(ready=1, pending=1, failed=1))
        with (
            patch.object(
                bootstrap.store, "queue_missing", AsyncMock(return_value=2)
            ) as queue,
            patch.object(bootstrap.store, "retry_failed", AsyncMock()) as retry,
        ):
            assert await bootstrap.queue(2) == 2
            queue.assert_awaited_once_with(bootstrap.spec, 2)
            retry.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "changed",
    [
        {"ready": 2, "missing": 1},
        {"ready": 2, "pending": 1},
        {"ready": 2, "leased": 1},
        {"ready": 2, "failed": 1},
        {"ready": 2, "stale": 1},
        {"ready": 2, "invalid_parts": 1},
    ],
)
def test_incomplete_activation_cannot_change_pipeline(changed):
    async def exercise():
        bootstrap = EmbeddingBootstrap(connection())
        bootstrap._status = AsyncMock(return_value=report(**changed))
        with patch.object(bootstrap.store, "set_state", AsyncMock()) as change:
            with pytest.raises(BootstrapBlocked, match="coverage_incomplete"):
                await bootstrap.activate()
            change.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "state,code",
    [
        ("absent", "pipeline_absent"),
        ("planned", "pipeline_not_building"),
        ("retired", "pipeline_retired"),
    ],
)
def test_unprepared_activation_refused(state, code):
    async def exercise():
        bootstrap = EmbeddingBootstrap(connection())
        bootstrap._status = AsyncMock(return_value=report(state))
        with pytest.raises(BootstrapBlocked, match=code):
            await bootstrap.activate()

    asyncio.run(exercise())


def test_conflicting_serving_never_replaced():
    async def exercise():
        bootstrap = EmbeddingBootstrap(connection())
        bootstrap._status = AsyncMock(return_value=report(conflicting_serving=True))
        with patch.object(bootstrap.store, "set_state", AsyncMock()) as change:
            with pytest.raises(BootstrapBlocked, match="conflicting_serving_pipeline"):
                await bootstrap.activate()
            change.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize("state,calls", [("building", 1), ("serving", 0)])
def test_complete_activation_and_repeat_are_explicit(state, calls):
    async def exercise():
        bootstrap = EmbeddingBootstrap(connection())
        bootstrap._status = AsyncMock(side_effect=[report(state), report("serving")])
        with patch.object(bootstrap.store, "set_state", AsyncMock()) as change:
            assert (await bootstrap.activate()).state == "serving"
            assert change.await_count == calls

    asyncio.run(exercise())


def test_second_snapshot_detects_change_before_return():
    async def exercise():
        bootstrap = EmbeddingBootstrap(connection())
        bootstrap._status = AsyncMock(
            side_effect=[report(), report("serving", ready=2, pending=1)]
        )
        with patch.object(bootstrap.store, "set_state", AsyncMock()):
            with pytest.raises(BootstrapBlocked, match="coverage_incomplete"):
                await bootstrap.activate()

    asyncio.run(exercise())
