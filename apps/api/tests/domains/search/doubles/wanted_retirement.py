"""Explicit Conversations contract fixture, never selected by application startup.

Models only content-free preflight and stable marker outcomes. It does not emulate
private Conversations SQL/locks or establish real cross-domain race acceptance.
"""

import asyncio

from app.contracts.domain_types import OriginActivityResult, RetirementMarkerResult


class ConversationsRetirementDouble:
    """Script zero/multiple threads, recent writes, unknown outcomes and replay."""

    def __init__(self, count=0, latest=None):
        """Bind controlled metadata; keep only typed origin requests/results."""
        self.count, self.latest = count, latest
        self.activity_error = None
        self.marker_error = None
        self.lose_result_once = False
        self.markers = []
        self.activity_requests = []
        self.results = {}
        self.effects = 0
        self.wait_for = 0
        self.arrived = asyncio.Event()
        self.release = asyncio.Event()

    async def get_origin_activity(self, context, request):
        """Return complete metadata or the explicitly scripted failure."""
        assert context.origin_kind == request.origin_kind == "wanted_request"
        self.activity_requests.append(request)
        if self.activity_error:
            raise self.activity_error
        return OriginActivityResult(
            thread_count=self.count, latest_participant_write_at=self.latest
        )

    async def mark_origin_retired(self, context, request):
        """Preserve exact operation/cutoff binding after a simulated lost result."""
        assert context.origin_kind == request.origin_kind == "wanted_request"
        self.markers.append(request)
        if self.wait_for and len(self.markers) >= self.wait_for:
            self.arrived.set()
        if self.wait_for:
            await self.release.wait()
        if self.marker_error:
            raise self.marker_error
        binding = (request.origin_kind, request.origin_id, request.cutoff_utc)
        if request.operation_id in self.results:
            previous, result = self.results[request.operation_id]
            assert previous == binding
        else:
            blocked = self.latest is not None and self.latest > request.cutoff_utc
            result = RetirementMarkerResult(
                outcome="blocked_recent_activity" if blocked else "marked",
                marked_count=0 if blocked else self.count,
            )
            self.results[request.operation_id] = binding, result
            if not blocked:
                self.effects += 1
        if self.lose_result_once:
            self.lose_result_once = False
            raise TimeoutError("controlled lost marker result")
        return result
