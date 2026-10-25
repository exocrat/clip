"""Bridge scheduling/failure contracts; actual SQL/model evidence is separate."""

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest
from psycopg.pq import TransactionStatus

from app.domains.listings.embedding_client import (
    EncodedListing,
    HelperBusy,
    HelperUnavailable,
)
from app.domains.listings.embedding_store import EmbeddingStore
from app.domains.listings.embedding_worker import (
    EmbeddingWorker,
    WorkerLimits,
    WorkerBusy,
    WorkerUnavailable,
)
from apps.api.tests.domains.listings.test_embedding_store import job, parts


def dependencies():
    """Script only public operation receipts; no fake SQL/ranking state machine."""
    store = MagicMock(spec=EmbeddingStore)
    store.claim = AsyncMock(return_value=job())
    store.complete = AsyncMock(return_value=True)
    store.fail = AsyncMock(return_value=True)
    store.defer = AsyncMock(return_value=True)
    helper = MagicMock()
    from app.domains.listings.embedding_types import default_pipeline_spec

    helper.spec = default_pipeline_spec()
    helper.encode_listing = AsyncMock(
        return_value=EncodedListing(parts(), 1, 1, ((0, 1),))
    )
    return store, helper


@pytest.mark.parametrize(
    "limits",
    [
        dict(work=True),
        dict(work=21),
        dict(record=4),
        dict(work=0),
        dict(record=float("nan")),
    ],
)
def test_limits_cannot_raise_caps(limits):
    with pytest.raises(ValueError):
        WorkerLimits(**limits)


def test_idle_and_success_are_single_job_calls():
    async def exercise():
        store, helper = dependencies()
        worker = EmbeddingWorker(store, helper)
        assert await worker.run_one() == "published"
        helper.encode_listing.assert_awaited_once_with(job().title, job().description)
        store.complete.assert_awaited_once_with(store.claim.return_value, parts(), 1)
        store.claim.assert_awaited_once_with(helper.spec)
        assert store.assert_idle.call_count == 3
        store.fail.assert_not_awaited()
        store.claim.return_value = None
        assert await worker.run_one() == "idle"
        assert helper.encode_listing.await_count == 1

    asyncio.run(exercise())


@pytest.mark.parametrize("code", ["timeout", "invalid_vectors", "helper_unavailable"])
def test_fixed_helper_failures_are_recorded(code):
    async def exercise():
        store, helper = dependencies()
        helper.encode_listing.side_effect = HelperUnavailable("safe", failure_code=code)
        assert await EmbeddingWorker(store, helper).run_one() == "failure_recorded"
        store.fail.assert_awaited_once_with(store.claim.return_value, code)
        store.complete.assert_not_awaited()

    asyncio.run(exercise())


def test_capacity_deferral_and_stale_receipt():
    async def exercise():
        store, helper = dependencies()
        helper.encode_listing.side_effect = HelperBusy("capacity")
        worker = EmbeddingWorker(store, helper)
        assert await worker.run_one() == "deferred"
        store.defer.assert_awaited_once_with(store.claim.return_value)
        store.fail.assert_not_awaited()
        store.defer.return_value = False
        assert await worker.run_one() == "stale"

    asyncio.run(exercise())


def test_pipeline_binding_refuses_inference():
    async def exercise():
        store, helper = dependencies()
        encoding = job().encoding.copy()
        encoding["numpy"] = "0.0.1"
        store.claim.return_value = replace(job(), encoding=encoding)
        assert await EmbeddingWorker(store, helper).run_one() == "failure_recorded"
        helper.encode_listing.assert_not_awaited()
        store.fail.assert_awaited_once_with(
            store.claim.return_value, "helper_unavailable"
        )

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "output",
    [
        EncodedListing(parts()[:1], 1, 1, ((0, 1),)),
        EncodedListing(parts(), 1, 10, ((0, 1),)),
    ],
)
def test_partial_or_inconsistent_outputs_never_publish(output):
    async def exercise():
        store, helper = dependencies()
        helper.encode_listing.return_value = output
        assert await EmbeddingWorker(store, helper).run_one() == "failure_recorded"
        store.fail.assert_awaited_once_with(store.claim.return_value, "invalid_vectors")
        store.complete.assert_not_awaited()

    asyncio.run(exercise())


def test_overall_budget_includes_claim_not_just_encoding():
    async def exercise():
        store, helper = dependencies()

        async def slow_claim(*args):
            await asyncio.sleep(0.02)
            return job()

        async def compute(*args):
            await asyncio.Event().wait()

        store.claim.side_effect = slow_claim
        helper.encode_listing.side_effect = compute
        assert (
            await EmbeddingWorker(
                store, helper, limits=WorkerLimits(work=0.04)
            ).run_one()
            == "failure_recorded"
        )
        assert store.fail.await_args.args[1] == "timeout"
        store.complete.assert_not_awaited()

    asyncio.run(exercise())


def test_cancel_leaves_lease_and_releases_process_slot():
    async def exercise():
        store, helper = dependencies()
        entered = asyncio.Event()

        async def blocked(*args):
            entered.set()
            await asyncio.Event().wait()

        helper.encode_listing.side_effect = blocked
        first = asyncio.create_task(EmbeddingWorker(store, helper).run_one())
        await asyncio.wait_for(entered.wait(), 1)
        with pytest.raises(WorkerBusy):
            await EmbeddingWorker(*dependencies()).run_one()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        store.complete.assert_not_awaited()
        store.fail.assert_not_awaited()
        store.defer.assert_not_awaited()
        assert await EmbeddingWorker(*dependencies()).run_one() == "published"

    asyncio.run(exercise())


@pytest.mark.parametrize("phase", ["claim", "complete", "fail", "defer"])
def test_database_errors_are_safe_and_never_replayed(phase):
    async def exercise():
        store, helper = dependencies()
        if phase == "fail":
            helper.encode_listing.side_effect = HelperUnavailable("safe")
        if phase == "defer":
            helper.encode_listing.side_effect = HelperBusy("safe")
        getattr(store, phase).side_effect = RuntimeError(
            "PRIVATE SOURCE / DRIVER PARAMETERS"
        )
        with pytest.raises(WorkerUnavailable) as raised:
            await EmbeddingWorker(store, helper).run_one()
        assert str(raised.value) == "embedding_worker_unavailable"
        assert getattr(store, phase).await_count == 1

    asyncio.run(exercise())


def test_timeout_before_receipt_and_failure_record_timeout_leave_reclaimable_job():
    async def exercise():
        for phase in ("claim", "fail"):
            store, helper = dependencies()

            async def blocked(*args):
                await asyncio.Event().wait()

            getattr(store, phase).side_effect = blocked
            if phase == "fail":
                helper.encode_listing.side_effect = HelperUnavailable("safe")
            with pytest.raises(WorkerUnavailable):
                await EmbeddingWorker(
                    store, helper, limits=WorkerLimits(work=0.02, record=0.02)
                ).run_one()
            store.complete.assert_not_awaited()

    asyncio.run(exercise())


def test_stale_completion_never_claims_published():
    async def exercise():
        store, helper = dependencies()
        store.complete.return_value = False
        assert await EmbeddingWorker(store, helper).run_one() == "stale"
        store.fail.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "autocommit,status",
    [
        (False, TransactionStatus.IDLE),
        (True, TransactionStatus.INTRANS),
        (True, TransactionStatus.ACTIVE),
        (True, TransactionStatus.UNKNOWN),
    ],
)
def test_real_store_refuses_unsafe_connection_without_repair(autocommit, status):
    connection = MagicMock()
    connection.autocommit = autocommit
    connection.info.transaction_status = status
    with pytest.raises(ValueError, match="idle autocommit"):
        EmbeddingStore(connection).assert_idle()
    connection.commit.assert_not_called()
    connection.rollback.assert_not_called()
