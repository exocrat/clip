"""Explicit one-job DB/helper bridge; never dispatches itself or opens a DB.

An operator supplies an idle dedicated store and the shared real helper. Model
work uses committed source receipts with no DB transaction held. There is no
polling loop, registration, reconciliation, serving switch or app/HTTP binding.
"""

import asyncio
from dataclasses import dataclass
import threading
from typing import Literal, Protocol, Sequence

from app.domains.listings.embedding_client import (
    EncodedListing,
    HelperBusy,
    HelperUnavailable,
)
from app.domains.listings.embedding_types import (
    EmbeddingJob,
    EmbeddingPart,
    PipelineSpec,
    pipeline_spec,
    validate_parts,
)
from app.domains.listings.embedding_protocol import chunk_ranges, validate_ranges


class JobStore(Protocol):
    """Listings-owned persistence contract; real implementation is EmbeddingStore."""

    def assert_idle(self) -> None: ...
    async def claim(self, spec: PipelineSpec | None = None) -> EmbeddingJob | None: ...
    async def complete(
        self,
        job: EmbeddingJob,
        parts: Sequence[EmbeddingPart],
        expected_description_parts: int,
    ) -> bool: ...
    async def fail(
        self,
        job: EmbeddingJob,
        code: Literal["timeout", "helper_unavailable", "invalid_vectors"],
    ) -> bool: ...
    async def defer(self, job: EmbeddingJob) -> bool: ...


class ListingEncoder(Protocol):
    """Shared bounded encoder; bridge borrows it and never closes other requests."""

    spec: PipelineSpec

    async def encode_listing(self, title: str, description: str) -> EncodedListing: ...


class WorkerBusy(RuntimeError):
    """Another explicit worker invocation already owns the process slot."""


class WorkerUnavailable(RuntimeError):
    """Persistence is uncertain; leave durable leases for fenced recovery."""


@dataclass(frozen=True)
class WorkerLimits:
    """Allow shorter test/operational deadlines, never larger reviewed ceilings."""

    work: float = 20
    record: float = 3

    def __post_init__(self) -> None:
        """Refuse booleans, nonfinite and out-of-range budgets before any work."""
        for value, ceiling in ((self.work, 20), (self.record, 3)):
            if type(value) not in {int, float} or not 0 < value <= ceiling:
                raise ValueError("Invalid embedding worker limits")


class EmbeddingWorker:
    """Run at most one job per call/process; source/vector data never enter results."""

    _slot = threading.Lock()

    def __init__(
        self,
        store: JobStore,
        helper: ListingEncoder,
        *,
        limits: WorkerLimits | None = None,
    ) -> None:
        """Inject explicit dependencies; construction has no DB/process side effects."""
        self.store = store
        self.helper = helper
        self.limits = limits or WorkerLimits()

    async def _record(
        self,
        job: EmbeddingJob,
        code: Literal["timeout", "helper_unavailable", "invalid_vectors"] | None,
    ) -> Literal["deferred", "failure_recorded", "stale"]:
        """Bound failure/deferral writes; never retry an uncertain DB operation here."""
        async with asyncio.timeout(self.limits.record):
            recorded = (
                await self.store.defer(job)
                if code is None
                else await self.store.fail(job, code)
            )
        if not recorded:
            return "stale"
        return "deferred" if code is None else "failure_recorded"

    async def run_one(
        self,
    ) -> Literal["idle", "published", "stale", "deferred", "failure_recorded"]:
        """Claim/encode/publish within20s, excluding bounded cancellation cleanup.

        Helper cancellation may require its separate<=5s reap. Failure/deferral
        recording has<=3s, below the30s lease under ordinary cooperative I/O.
        SQL independently fences actual lease expiry; no local wall clock or
        heartbeat can extend it. External cancellation is propagated and leaves
        a reclaimable lease rather than dispatching background cleanup/writes.
        """
        if not EmbeddingWorker._slot.acquire(blocking=False):
            raise WorkerBusy("embedding_worker_busy")
        job = None
        try:
            self.store.assert_idle()
            try:
                try:
                    async with asyncio.timeout(self.limits.work):
                        job = await self.store.claim(self.helper.spec)
                        self.store.assert_idle()
                        if job is None:
                            return "idle"
                        if (
                            pipeline_spec(job.encoding) != self.helper.spec
                            or job.pipeline_id != self.helper.spec.pipeline_id
                        ):
                            raise HelperUnavailable("unsupported_embedding_pipeline")
                        try:
                            encoded = await self.helper.encode_listing(
                                job.title, job.description
                            )
                            validate_ranges(
                                [list(pair) for pair in encoded.ranges],
                                chunk_ranges(encoded.description_tokens),
                            )
                            checked = validate_parts(encoded.parts, len(encoded.ranges))
                        except ValueError:
                            raise HelperUnavailable(
                                "invalid_embedding_output",
                                failure_code="invalid_vectors",
                            ) from None
                        self.store.assert_idle()
                        published = await self.store.complete(
                            job, checked, len(encoded.ranges)
                        )
                        return "published" if published else "stale"
                except HelperBusy:
                    if job is None:
                        raise
                    return await self._record(job, None)
                except HelperUnavailable as error:
                    if job is None:
                        raise
                    return await self._record(job, error.failure_code)
                except TimeoutError:
                    if job is None:
                        raise
                    return await self._record(job, "timeout")
            except asyncio.CancelledError:
                raise
            except Exception:
                # Raw driver exceptions can contain SQL parameters/source text.
                # A broken/uncertain transaction is never blindly retried here.
                raise WorkerUnavailable("embedding_worker_unavailable") from None
        finally:
            EmbeddingWorker._slot.release()
