"""Listings-owned embedding job store; connection ownership stays with callers.

Every operation uses an injected connection, transactions and bound values.
The opt-in dispatcher and explicit operator tooling instantiate this store;
HTTP reads do not run embedding jobs. SQL triggers own text invalidation and
retirement; this store owns canonical listing-first job lock order.
"""

from typing import Any, Literal, Sequence
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from app.domains.listings.embedding_types import (
    EmbeddingJob,
    EmbeddingPart,
    PipelineSpec,
    validate_parts,
    pipeline_spec,
)


class EmbeddingStore:
    """Internal persistence only; caller must separately review targets/run bounds."""

    def __init__(self, connection: AsyncConnection[dict[str, Any]]) -> None:
        """Use an owned injected connection; never inspect ambient DB credentials."""
        self.connection = connection

    def assert_idle(self) -> None:
        """Require a dedicated idle autocommit connection before worker inference.

        Nested transactions would retain claim locks during model work. Never
        commit/rollback a caller's transaction to repair an unsafe connection.
        """
        if (
            not self.connection.autocommit
            or self.connection.info.transaction_status != TransactionStatus.IDLE
        ):
            raise ValueError("Embedding worker requires idle autocommit connection")

    async def _job_limits(self) -> None:
        """Bound each job statement/lock without changing caller session settings."""
        async with self.connection.cursor() as cursor:
            await cursor.execute("SET LOCAL statement_timeout='3s'")
            await cursor.execute("SET LOCAL lock_timeout='1s'")

    async def register(self, spec: PipelineSpec) -> None:
        """Register immutable encoding in planned state without backfill or serving."""
        if pipeline_spec(spec.encoding) != spec:
            raise ValueError("Embedding pipeline binding mismatch")
        async with self.connection.transaction():
            # Registry locks precede pipeline row/index locks, including retries.
            await self.connection.execute("SELECT pg_advisory_xact_lock(1129072976,21)")
            await self.connection.execute(
                "INSERT INTO listings.embedding_pipelines(pipeline_id,encoding) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (spec.pipeline_id, Jsonb(spec.encoding)),
            )
            row = await (
                await self.connection.execute(
                    "SELECT encoding FROM listings.embedding_pipelines WHERE pipeline_id=%s",
                    (spec.pipeline_id,),
                )
            ).fetchone()
            if row is None or row["encoding"] != spec.encoding:
                raise ValueError("Embedding pipeline binding mismatch")

    async def set_state(
        self,
        spec: PipelineSpec,
        state: Literal["planned", "building", "serving", "retired"],
    ) -> None:
        """Explicit operator transition; SQL guards enforce limits/coverage at commit."""
        if state not in {"planned", "building", "serving", "retired"}:
            raise ValueError("Invalid embedding pipeline state")
        async with self.connection.transaction():
            await self.connection.execute("SELECT pg_advisory_xact_lock(1129072976,21)")
            result = await self.connection.execute(
                "UPDATE listings.embedding_pipelines SET state=%s WHERE pipeline_id=%s AND encoding=%s",
                (state, spec.pipeline_id, Jsonb(spec.encoding)),
            )
            if result.rowcount != 1:
                raise ValueError("Embedding pipeline binding mismatch")

    async def queue_missing(self, spec: PipelineSpec, limit: int) -> int:
        """Reconcile <=1,000 missing/stale rows, listing lock first, no inference.

        A registry transition can race a writer; serving coverage must independently
        reject gaps. Reconciliation is resumable and never rewrites current jobs.
        """
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("Invalid embedding queue bound")
        queued = 0
        async with self.connection.transaction():
            rows = await (
                await self.connection.execute(
                    """SELECT listing.id, listings.embedding_source_fingerprint(listing.title,listing.description) AS fingerprint
                FROM listings.sale_listings AS listing
                JOIN listings.embedding_pipelines AS pipeline ON pipeline.pipeline_id=%s
                LEFT JOIN listings.embedding_generations AS generation
                  ON generation.listing_id=listing.id AND generation.pipeline_id=pipeline.pipeline_id
                WHERE pipeline.state IN ('building','serving') AND pipeline.encoding=%s
                  AND listing.retired_at IS NULL AND listing.retirement_pending_operation_id IS NULL
                  AND generation.source_fingerprint IS DISTINCT FROM
                      listings.embedding_source_fingerprint(listing.title,listing.description)
                ORDER BY listing.id LIMIT %s FOR UPDATE OF listing SKIP LOCKED""",
                    (spec.pipeline_id, Jsonb(spec.encoding), limit),
                )
            ).fetchall()
            for row in rows:
                current = await (
                    await self.connection.execute(
                        "SELECT source_fingerprint FROM listings.embedding_generations WHERE listing_id=%s AND pipeline_id=%s FOR UPDATE",
                        (row["id"], spec.pipeline_id),
                    )
                ).fetchone()
                if (
                    current is not None
                    and current["source_fingerprint"] == row["fingerprint"]
                ):
                    continue
                await self.connection.execute(
                    "DELETE FROM listings.embedding_generations WHERE listing_id=%s AND pipeline_id=%s",
                    (row["id"], spec.pipeline_id),
                )
                await self.connection.execute(
                    "INSERT INTO listings.embedding_generations(listing_id,pipeline_id,generation_id,source_fingerprint) VALUES (%s,%s,%s,%s)",
                    (row["id"], spec.pipeline_id, uuid4(), row["fingerprint"]),
                )
                queued += 1
        return queued

    async def retry_failed(self, spec: PipelineSpec, listing_id: UUID) -> bool:
        """Explicit single-row operator retry; new generation fences old receipts.

        This is not an automatic failed-job sweep or public route. Target/run
        approval remains the caller's responsibility before any real invocation.
        """
        async with self.connection.transaction():
            listing = await (
                await self.connection.execute(
                    """SELECT listings.embedding_source_fingerprint(title,description) AS fingerprint
                FROM listings.sale_listings WHERE id=%s AND retired_at IS NULL
                  AND retirement_pending_operation_id IS NULL FOR UPDATE""",
                    (listing_id,),
                )
            ).fetchone()
            if listing is None:
                return False
            generation = await (
                await self.connection.execute(
                    """SELECT generation.generation_id FROM listings.embedding_generations AS generation
                JOIN listings.embedding_pipelines AS pipeline ON pipeline.pipeline_id=generation.pipeline_id
                WHERE generation.listing_id=%s AND generation.pipeline_id=%s AND generation.state='failed'
                  AND pipeline.state IN ('building','serving') AND pipeline.encoding=%s FOR UPDATE OF generation""",
                    (listing_id, spec.pipeline_id, Jsonb(spec.encoding)),
                )
            ).fetchone()
            if generation is None:
                return False
            await self.connection.execute(
                "DELETE FROM listings.embedding_generations WHERE generation_id=%s",
                (generation["generation_id"],),
            )
            await self.connection.execute(
                "INSERT INTO listings.embedding_generations(listing_id,pipeline_id,generation_id,source_fingerprint) VALUES (%s,%s,%s,%s)",
                (listing_id, spec.pipeline_id, uuid4(), listing["fingerprint"]),
            )
        return True

    async def claim(self, spec: PipelineSpec | None = None) -> EmbeddingJob | None:
        """Lease one due job for30s; optionally restrict to an encoder's exact space.

        Workers pass their supported spec so a second building pipeline is never
        claimed/failed by the wrong encoder. Unfiltered native maintenance checks
        retain their existing explicit all-space behavior.
        """
        if spec is not None and pipeline_spec(spec.encoding) != spec:
            raise ValueError("Embedding pipeline binding mismatch")
        async with self.connection.transaction():
            await self._job_limits()
            listing = await (
                await self.connection.execute(
                    """SELECT listing.id,listing.title,listing.description,pipeline.pipeline_id,pipeline.encoding,
                listings.embedding_source_fingerprint(listing.title,listing.description) AS fingerprint
                FROM listings.sale_listings AS listing
                JOIN listings.embedding_generations AS generation ON generation.listing_id=listing.id
                JOIN listings.embedding_pipelines AS pipeline ON pipeline.pipeline_id=generation.pipeline_id
                WHERE pipeline.state IN ('building','serving')
                  AND (%s::bytea IS NULL OR (pipeline.pipeline_id=%s AND pipeline.encoding=%s))
                  AND listing.retired_at IS NULL
                  AND listing.retirement_pending_operation_id IS NULL
                  AND generation.source_fingerprint=listings.embedding_source_fingerprint(listing.title,listing.description)
                  AND ((generation.state='pending' AND generation.retry_after<=clock_timestamp())
                    OR (generation.state='leased' AND generation.lease_until<=clock_timestamp()))
                ORDER BY generation.retry_after,listing.id,pipeline.pipeline_id
                LIMIT 1 FOR UPDATE OF listing SKIP LOCKED""",
                    (
                        spec.pipeline_id if spec else None,
                        spec.pipeline_id if spec else None,
                        Jsonb(spec.encoding) if spec else None,
                    ),
                )
            ).fetchone()
            if listing is None:
                return None
            if pipeline_spec(listing["encoding"]).pipeline_id != listing["pipeline_id"]:
                raise ValueError("Embedding pipeline binding mismatch")
            generation = await (
                await self.connection.execute(
                    """SELECT generation.*, ((generation.state='pending' AND generation.retry_after<=clock_timestamp())
                        OR (generation.state='leased' AND generation.lease_until<=clock_timestamp())) AS due
                        FROM listings.embedding_generations AS generation
                        JOIN listings.embedding_pipelines AS pipeline ON pipeline.pipeline_id=generation.pipeline_id
                        WHERE generation.listing_id=%s AND generation.pipeline_id=%s
                          AND pipeline.state IN ('building','serving') AND pipeline.encoding=%s
                        FOR UPDATE OF generation""",
                    (listing["id"], listing["pipeline_id"], Jsonb(listing["encoding"])),
                )
            ).fetchone()
            if (
                generation is None
                or not generation["due"]
                or generation["source_fingerprint"] != listing["fingerprint"]
            ):
                return None
            if generation["attempts"] >= 5:
                await self.connection.execute(
                    "UPDATE listings.embedding_generations SET state='failed',lease_token=NULL,lease_until=NULL,failure_code='lease_exhausted',updated_at=clock_timestamp() WHERE generation_id=%s",
                    (generation["generation_id"],),
                )
                return None
            token = uuid4()
            leased = await (
                await self.connection.execute(
                    """UPDATE listings.embedding_generations SET state='leased',lease_token=%s,
                lease_until=clock_timestamp()+interval '30 seconds',attempts=attempts+1,
                failure_code=NULL,updated_at=clock_timestamp()
                WHERE generation_id=%s AND ((state='pending' AND retry_after<=clock_timestamp())
                    OR (state='leased' AND lease_until<=clock_timestamp()))
                RETURNING generation_id,source_fingerprint,lease_until""",
                    (token, generation["generation_id"]),
                )
            ).fetchone()
            if leased is None:
                return None
            return EmbeddingJob(
                listing["id"],
                listing["pipeline_id"],
                leased["generation_id"],
                leased["source_fingerprint"],
                token,
                leased["lease_until"],
                listing["title"],
                listing["description"],
                listing["encoding"],
            )

    async def _lock_current(
        self, job: EmbeddingJob, *, unexpired: bool
    ) -> dict[str, Any] | None:
        """Fence source/retirement before locking the generation; no reverse locks."""
        listing = await (
            await self.connection.execute(
                "SELECT retired_at,retirement_pending_operation_id,listings.embedding_source_fingerprint(title,description) AS fingerprint FROM listings.sale_listings WHERE id=%s FOR UPDATE",
                (job.listing_id,),
            )
        ).fetchone()
        if (
            listing is None
            or listing["retired_at"] is not None
            or listing["retirement_pending_operation_id"] is not None
            or listing["fingerprint"] != job.source_fingerprint
        ):
            return None
        return await (
            await self.connection.execute(
                """SELECT generation.attempts FROM listings.embedding_generations AS generation
            JOIN listings.embedding_pipelines AS pipeline ON pipeline.pipeline_id=generation.pipeline_id
            WHERE generation.listing_id=%s AND generation.pipeline_id=%s AND generation.generation_id=%s
              AND generation.source_fingerprint=%s AND generation.lease_token=%s AND generation.state='leased'
              AND pipeline.state IN ('building','serving') AND pipeline.encoding=%s
              AND (NOT %s OR generation.lease_until>clock_timestamp()) FOR UPDATE OF generation""",
                (
                    job.listing_id,
                    job.pipeline_id,
                    job.generation_id,
                    job.source_fingerprint,
                    job.lease_token,
                    Jsonb(job.encoding),
                    unexpired,
                ),
            )
        ).fetchone()

    async def complete(
        self,
        job: EmbeddingJob,
        parts: Sequence[EmbeddingPart],
        expected_description_parts: int,
    ) -> bool:
        """Publish complete vectors and ready marker atomically, or reject stale work."""
        checked = validate_parts(parts, expected_description_parts)
        async with self.connection.transaction():
            await self._job_limits()
            if await self._lock_current(job, unexpired=True) is None:
                return False
            await self.connection.execute(
                "SET CONSTRAINTS listings.embedding_generation_complete,listings.embedding_chunks_complete DEFERRED"
            )
            async with self.connection.cursor() as cursor:
                await cursor.executemany(
                    "INSERT INTO listings.embedding_chunks(generation_id,part_kind,ordinal,vector) VALUES (%s,%s,%s,%s)",
                    [
                        (job.generation_id, part.kind, part.ordinal, list(part.vector))
                        for part in checked
                    ],
                )
            await self.connection.execute(
                """UPDATE listings.embedding_generations SET state='ready',lease_token=NULL,lease_until=NULL,
                title_count=1,description_count=%s,failure_code=NULL,updated_at=clock_timestamp()
                WHERE generation_id=%s""",
                (expected_description_parts, job.generation_id),
            )
        return True

    async def fail(
        self,
        job: EmbeddingJob,
        code: Literal["timeout", "helper_unavailable", "invalid_vectors"],
    ) -> bool:
        """Record only the owned failure; bounded backoff and fifth-attempt stop."""
        if code not in {"timeout", "helper_unavailable", "invalid_vectors"}:
            raise ValueError("Invalid embedding failure code")
        async with self.connection.transaction():
            await self._job_limits()
            current = await self._lock_current(job, unexpired=False)
            if current is None:
                return False
            attempt = current["attempts"]
            delay = (5, 30, 120, 300, 300)[max(0, min(attempt - 1, 4))]
            await self.connection.execute(
                """UPDATE listings.embedding_generations SET state=%s,lease_token=NULL,lease_until=NULL,
                failure_code=%s,retry_after=clock_timestamp()+make_interval(secs=>%s),updated_at=clock_timestamp()
                WHERE generation_id=%s""",
                (
                    "failed" if attempt >= 5 else "pending",
                    code,
                    delay,
                    job.generation_id,
                ),
            )
        return True

    async def defer(self, job: EmbeddingJob) -> bool:
        """Release an owned capacity-blocked job for5s without consuming an attempt.

        Generation/token/source fences prevent a delayed deferral from changing
        edited, retired or reclaimed work. This is capacity, not model failure.
        """
        async with self.connection.transaction():
            await self._job_limits()
            if await self._lock_current(job, unexpired=False) is None:
                return False
            await self.connection.execute(
                """UPDATE listings.embedding_generations SET state='pending',
                lease_token=NULL,lease_until=NULL,attempts=greatest(attempts-1,0),
                failure_code=NULL,retry_after=clock_timestamp()+interval '5 seconds',
                updated_at=clock_timestamp() WHERE generation_id=%s""",
                (job.generation_id,),
            )
        return True
