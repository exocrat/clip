"""Offline checks for the explicitly started notification polling loop."""

import asyncio
import logging

import pytest

from app.domains.conversations.notifications.scheduler import run_polling_worker


def test_scheduler_runs_once_and_stops_without_leaking_error(caplog):
    """A failed batch is logged safely and an explicit stop ends polling."""

    async def scenario():
        stop = asyncio.Event()
        calls = []

        async def work():
            calls.append(True)
            stop.set()
            raise RuntimeError("PRIVATE PROVIDER DATA")

        await run_polling_worker(work, stop, interval_seconds=1)
        assert len(calls) == 1

    with caplog.at_level(logging.WARNING):
        asyncio.run(scenario())
    assert "notification_poll_error" in caplog.text
    assert "PRIVATE" not in caplog.text


def test_scheduler_rejects_unbounded_interval():
    """Unsafe interval configuration fails without running the batch."""

    async def work():
        raise AssertionError("must not run")

    with pytest.raises(ValueError):
        asyncio.run(run_polling_worker(work, asyncio.Event(), interval_seconds=0))
