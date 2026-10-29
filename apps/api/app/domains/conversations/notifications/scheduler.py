"""Cancellable in-process notification polling; no automatic startup."""

import asyncio
from collections.abc import Awaitable, Callable
import logging

logger = logging.getLogger(__name__)


async def run_polling_worker(
    run_once: Callable[[], Awaitable[object]],
    stop: asyncio.Event,
    *,
    interval_seconds: int = 60,
) -> None:
    """Run bounded batches while enabled, stopping between batches when requested.

    The caller supplies a configured batch and owns process lifecycle; this
    function never discovers providers or starts itself. Database due times
    remain authoritative and a failed batch is retried on the next interval.
    """
    if type(interval_seconds) is not int or not 1 <= interval_seconds <= 3600:
        raise ValueError("Invalid notification polling interval")
    while not stop.is_set():
        try:
            await run_once()
        except Exception:
            logger.warning("notification_poll_error reason=batch_unavailable")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except TimeoutError:
            pass
