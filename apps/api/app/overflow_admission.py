"""Bound concurrent blocking Lambda calls for the experimental ECS router.

No client, credentials or network are created here. The caller must select
reviewed capacity and timeout values and integrate shutdown with app lifecycle.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import math
from threading import BoundedSemaphore
from typing import TypeVar

T = TypeVar("T")


class RouterAtCapacity(Exception):
    """The router's own configured invocation slots are full."""


class RouterDeadlineExceeded(Exception):
    """A call exceeded the router deadline; it may still be running."""


class BoundedInvoker:
    """Limit outstanding blocking calls; retain slots until workers actually end.

    A timed-out or cancelled caller cannot stop a running SDK thread. Its slot
    stays occupied until that thread finishes, preventing hidden concurrency.
    The explicit capacity applies to this process, not all ECS processes.
    """

    def __init__(self, *, max_inflight: int, deadline_seconds: float) -> None:
        if type(max_inflight) is not int or max_inflight < 1:
            raise ValueError("Invalid invocation capacity")
        if (
            type(deadline_seconds) not in (int, float)
            or not math.isfinite(deadline_seconds)
            or not 0 < deadline_seconds <= 5
        ):
            raise ValueError("Invalid invocation deadline")
        self._slots = BoundedSemaphore(max_inflight)
        self._executor = ThreadPoolExecutor(
            max_workers=max_inflight, thread_name_prefix="clip-lambda"
        )
        self._max_inflight = max_inflight
        self._deadline = deadline_seconds
        self._closed = False

    @property
    def max_inflight(self) -> int:
        """Expose this process's configured slot cap for guarded diagnostics."""
        return self._max_inflight

    async def invoke(self, operation: Callable[[], T]) -> T:
        """Run one operation or refuse immediately when all slots are occupied."""
        if self._closed:
            raise RuntimeError("Invocation router is closed")
        if not self._slots.acquire(blocking=False):
            raise RouterAtCapacity() from None
        try:
            future = self._executor.submit(operation)
        except Exception:
            self._slots.release()
            raise RuntimeError("Invocation scheduling failed") from None
        future.add_done_callback(lambda _: self._slots.release())
        wrapped = asyncio.wrap_future(future)
        # Retrieve a late failure even after the requester times out/cancels.
        wrapped.add_done_callback(
            lambda item: None if item.cancelled() else item.exception()
        )
        done, _ = await asyncio.wait({wrapped}, timeout=self._deadline)
        if not done:
            raise RouterDeadlineExceeded() from None
        return wrapped.result()

    def close(self) -> None:
        """Stop admitting calls and cancel queued work without waiting on threads.

        Running operations still need their own finite SDK socket timeouts;
        closing this object does not interrupt them or prove their completion.
        """
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
