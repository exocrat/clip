"""Reviewed public saved-target/summary scripts; no SQL or upstream implementation."""

import asyncio

from app.core.errors import ERRORS, PublicError


class SavedListingsDouble:
    """Return explicitly supplied current snapshots for known synthetic IDs."""

    def __init__(self):
        """Scripts are owned by each test and are never a production fallback."""
        self.targets = {}
        self.states = {}
        self.calls = []
        self.fail = False
        self.pause_target = None
        self.target_checked = asyncio.Event()
        self.resume_target = asyncio.Event()

    async def read_save_target(self, caller, listing_id):
        """Script discoverability without deriving it from stale saved state."""
        caller.require_current()
        self.calls.append(("target", caller.user_id, listing_id))
        if self.fail:
            raise TimeoutError("controlled target failure")
        if listing_id not in self.targets:
            raise PublicError(ERRORS[404])
        result = self.targets[listing_id]
        if self.pause_target == listing_id:
            self.target_checked.set()
            await self.resume_target.wait()
        return result

    async def read_saved_listing_summaries(self, caller, listing_ids):
        """Resolve only the supplied own-page IDs; record caller/request binding."""
        caller.require_current()
        assert len(listing_ids) <= 100
        self.calls.append(("summaries", caller.user_id, listing_ids))
        if self.fail:
            raise TimeoutError("controlled summaries failure")
        return tuple(
            self.states[identifier]
            for identifier in reversed(listing_ids)
            if identifier in self.states
        )
