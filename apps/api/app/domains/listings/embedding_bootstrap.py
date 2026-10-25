"""Explicit operator-only pipeline preparation/coverage/activation; never startup.

Connections/targets are supplied by a separately approved operator. Operations
are bounded, resumable and never reset current jobs, invoke inference or replace
another serving pipeline. The normal dispatcher processes queued jobs separately.
"""

from dataclasses import dataclass
from typing import Any, Literal

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.domains.listings.embedding_store import EmbeddingStore
from app.domains.listings.embedding_types import PipelineSpec, default_pipeline_spec


class BootstrapBlocked(RuntimeError):
    """Fixed reason only; operator reports must never echo DB/source exceptions."""

    def __init__(self, code: str) -> None:
        """Accept only code-owned reasons, not caller text or database diagnostics."""
        if code not in {
            "unsupported_pipeline",
            "pipeline_absent",
            "pipeline_retired",
            "pipeline_not_building",
            "conflicting_serving_pipeline",
            "coverage_incomplete",
            "pipeline_mismatch",
        }:
            raise ValueError("Invalid bootstrap refusal code")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PipelineCoverage:
    """One SQL snapshot of aggregate coverage; no listing IDs/text/vectors escape."""

    pipeline_id: str
    state: Literal["absent", "planned", "building", "serving", "retired"]
    encoding_matches: bool
    conflicting_serving: bool
    live: int
    ready: int
    missing: int
    stale: int
    pending: int
    leased: int
    failed: int
    invalid_parts: int

    @property
    def complete(self) -> bool:
        """Complete means every live non-pending-retirement source is current/whole."""
        return self.encoding_matches and self.ready == self.live


# Entire live scope includes unavailable/future/ended listings as required by the
# registry guard. One statement measures pipeline and generation/chunk coverage.
_STATUS_SQL = """
WITH selected AS MATERIALIZED (
 SELECT state, encoding=%s::jsonb AS matches FROM listings.embedding_pipelines
 WHERE pipeline_id=%s
), covered AS MATERIALIZED (
 SELECT generation.state,
   generation.generation_id IS NULL AS missing,
   generation.source_fingerprint IS DISTINCT FROM
     listings.embedding_source_fingerprint(listing.title,listing.description) AS stale,
   COALESCE(generation.title_count=1 AND chunk.titles=1
     AND chunk.title_min=0 AND chunk.title_max=0
     AND generation.description_count BETWEEN 1 AND 96
     AND chunk.descriptions=generation.description_count
     AND chunk.description_min=0 AND chunk.description_max=generation.description_count-1, false) AS parts
 FROM listings.sale_listings AS listing
 LEFT JOIN listings.embedding_generations AS generation
   ON generation.listing_id=listing.id AND generation.pipeline_id=%s
 LEFT JOIN LATERAL (
   SELECT count(*) FILTER (WHERE part_kind='title') AS titles,
     min(ordinal) FILTER (WHERE part_kind='title') AS title_min,
     max(ordinal) FILTER (WHERE part_kind='title') AS title_max,
     count(*) FILTER (WHERE part_kind='description') AS descriptions,
     min(ordinal) FILTER (WHERE part_kind='description') AS description_min,
     max(ordinal) FILTER (WHERE part_kind='description') AS description_max
   FROM listings.embedding_chunks WHERE generation_id=generation.generation_id
 ) AS chunk ON true
 WHERE listing.retired_at IS NULL AND listing.retirement_pending_operation_id IS NULL
)
SELECT COALESCE((SELECT state FROM selected),'absent') AS state,
 COALESCE((SELECT matches FROM selected),false) AS encoding_matches,
 EXISTS(SELECT 1 FROM listings.embedding_pipelines WHERE state='serving' AND pipeline_id<>%s) AS conflicting_serving,
 count(*) AS live,
 count(*) FILTER (WHERE state='ready' AND NOT stale AND parts) AS ready,
 count(*) FILTER (WHERE missing) AS missing,
 count(*) FILTER (WHERE NOT missing AND stale) AS stale,
 count(*) FILTER (WHERE state='pending') AS pending,
 count(*) FILTER (WHERE state='leased') AS leased,
 count(*) FILTER (WHERE state='failed') AS failed,
 count(*) FILTER (WHERE state='ready' AND NOT parts) AS invalid_parts
FROM covered
"""


class EmbeddingBootstrap:
    """Run explicit pinned operations over an injected idle autocommit connection."""

    def __init__(
        self,
        connection: AsyncConnection[dict[str, Any]],
        spec: PipelineSpec | None = None,
    ) -> None:
        """Only the supported pinned manifest is an activation target; no inference."""
        self.spec = default_pipeline_spec() if spec is None else spec
        if self.spec != default_pipeline_spec():
            raise BootstrapBlocked("unsupported_pipeline")
        self.connection = connection
        self.store = EmbeddingStore(connection)

    async def _limits(self) -> None:
        """Bound operator statements and lock waiting inside this operation only."""
        await self.connection.execute("SET LOCAL statement_timeout='5s'")
        await self.connection.execute("SET LOCAL lock_timeout='1s'")

    async def _status(self) -> PipelineCoverage:
        """Read current aggregate state within an already-owned transaction."""
        row = await (
            await self.connection.execute(
                _STATUS_SQL,
                (
                    Jsonb(self.spec.encoding),
                    self.spec.pipeline_id,
                    self.spec.pipeline_id,
                    self.spec.pipeline_id,
                ),
            )
        ).fetchone()
        if row is None:
            raise BootstrapBlocked("pipeline_mismatch")
        return PipelineCoverage(pipeline_id=self.spec.pipeline_id.hex(), **row)

    async def status(self) -> PipelineCoverage:
        """Read-only transaction/snapshot; absence never registers anything."""
        self.store.assert_idle()
        async with self.connection.transaction():
            await self.connection.execute("SET TRANSACTION READ ONLY")
            await self._limits()
            return await self._status()

    async def prepare(self) -> PipelineCoverage:
        """Register planned->building once; resume building/serving without demotion."""
        self.store.assert_idle()
        async with self.connection.transaction():
            await self._limits()
            await self.connection.execute("SELECT pg_advisory_xact_lock(1129072976,21)")
            report = await self._status()
            if report.state == "retired":
                raise BootstrapBlocked("pipeline_retired")
            if report.state == "absent":
                await self.store.register(self.spec)
            elif not report.encoding_matches:
                raise BootstrapBlocked("pipeline_mismatch")
            if report.state in {"absent", "planned"}:
                await self.store.set_state(self.spec, "building")
            return await self._status()

    async def queue(self, limit: int) -> int:
        """Reconcile one1..1000batch; preserve current pending/leased/failed work."""
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("Invalid bootstrap batch bound")
        self.store.assert_idle()
        async with self.connection.transaction():
            await self._limits()
            await self.connection.execute("SELECT pg_advisory_xact_lock(1129072976,21)")
            report = await self._status()
            self._check_pipeline(report)
            return await self.store.queue_missing(self.spec, limit)

    def _check_pipeline(self, report: PipelineCoverage) -> None:
        """Refuse absent/retired/unprepared/mismatched space before any job mutation."""
        if report.state == "absent":
            raise BootstrapBlocked("pipeline_absent")
        if report.state == "retired":
            raise BootstrapBlocked("pipeline_retired")
        if not report.encoding_matches:
            raise BootstrapBlocked("pipeline_mismatch")
        if report.state not in {"building", "serving"}:
            raise BootstrapBlocked("pipeline_not_building")

    async def activate(self) -> PipelineCoverage:
        """Separate guarded transition; no partial coverage or replacement serving.

        Registry mutations share advisory lock21. The SQL trigger rechecks coverage
        at the transition; generation/chunk constraints apply at commit. Concurrent
        source commits can invalidate coverage afterward, so request guards remain
        mandatory and this operation makes no future/per-request readiness promise.
        """
        self.store.assert_idle()
        async with self.connection.transaction():
            await self._limits()
            await self.connection.execute("SELECT pg_advisory_xact_lock(1129072976,21)")
            report = await self._status()
            self._check_pipeline(report)
            if report.conflicting_serving:
                raise BootstrapBlocked("conflicting_serving_pipeline")
            if not report.complete:
                raise BootstrapBlocked("coverage_incomplete")
            if report.state != "serving":
                await self.store.set_state(self.spec, "serving")
            report = await self._status()
            if not report.complete:
                raise BootstrapBlocked("coverage_incomplete")
            return report
