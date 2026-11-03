"""Bounded executor checks with synthetic local thread events only."""

import asyncio
from threading import Event

import pytest

from app.overflow_admission import (
    BoundedInvoker,
    RouterAtCapacity,
    RouterDeadlineExceeded,
)


def test_timed_out_worker_keeps_slot_until_it_finishes():
    started, release, finished = Event(), Event(), Event()
    router = BoundedInvoker(max_inflight=1, deadline_seconds=0.05)

    def blocked():
        started.set()
        try:
            assert release.wait(2)
            return "synthetic"
        finally:
            finished.set()

    async def run():
        try:
            with pytest.raises(RouterDeadlineExceeded):
                await router.invoke(blocked)
            assert started.is_set()
            with pytest.raises(RouterAtCapacity):
                await router.invoke(lambda: "must not run")
        finally:
            release.set()
            assert await asyncio.to_thread(finished.wait, 2)
            router.close()

    asyncio.run(run())


def test_one_success_and_closed_router_refusal():
    router = BoundedInvoker(max_inflight=1, deadline_seconds=1)

    async def run():
        assert await router.invoke(lambda: "ok") == "ok"
        router.close()
        with pytest.raises(RuntimeError, match="closed"):
            await router.invoke(lambda: "must not run")

    asyncio.run(run())


def test_cancelled_request_does_not_release_running_worker_slot():
    started, release, finished = Event(), Event(), Event()
    router = BoundedInvoker(max_inflight=1, deadline_seconds=1)

    def blocked():
        started.set()
        try:
            assert release.wait(2)
        finally:
            finished.set()

    async def run():
        try:
            task = asyncio.create_task(router.invoke(blocked))
            assert await asyncio.to_thread(started.wait, 1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            with pytest.raises(RouterAtCapacity):
                await router.invoke(lambda: "must not run")
        finally:
            release.set()
            assert await asyncio.to_thread(finished.wait, 2)
            router.close()

    asyncio.run(run())


@pytest.mark.parametrize("capacity,timeout", [(0, 1), (True, 1), (1, 0), (1, 5.1)])
def test_invalid_bounds_are_rejected(capacity, timeout):
    with pytest.raises(ValueError):
        BoundedInvoker(max_inflight=capacity, deadline_seconds=timeout)
