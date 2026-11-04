"""Fresh SQL candidate snapshots and bounded immutable-vector application scoring.

Only the existing source/coverage part of the Hybrid SQL is reused. No public
projection, authorization or result page is cached. Ready generation vectors
are immutable under the supported write protocol; a replacement gets a new ID.
Do not log snapshots, vectors, text, DB errors or numerical intermediates.
"""

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
import base64
import struct
from threading import Lock
import time
from typing import Any, Callable
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from psycopg import AsyncConnection, Error as DatabaseError
from psycopg.types.json import Jsonb

from app.contracts.domain_types import ListingQuery, ListingSummary
from app.core.errors import ERRORS, FieldError, PublicError
from app.core.pagination import Page, PageRequest, page_from_window
from app.domains.listings.hybrid_read import (
    DESCRIPTION_WEIGHT,
    SEMANTIC_THRESHOLD,
    TITLE_WEIGHT,
    QueryEmbedding,
    hybrid_statement,
)
from app.domains.listings.lexical_expansion import TextQuery, compile_expansion


@dataclass(frozen=True)
class GenerationVectors:
    """Checked ordered vectors/norms only; arrays become read-only before sharing."""

    matrix: NDArray[np.float64] = field(repr=False)
    norms: NDArray[np.float64] = field(repr=False)
    expires: float


class HybridVectorCache:
    """Bound process memory to4096parts/2048generations, with finite retention.

    A caller takes an immutable dictionary snapshot before SQL. References remain
    valid through concurrent eviction/refresh. Source/pipeline/readiness is always
    checked by the database, so cache hits alone never authorize an old result.
    Five-minute expiry is spread over30seconds to avoid one full-corpus refresh
    cliff; cache expiry never changes correctness or skips a candidate.
    """

    def __init__(
        self, *, max_parts: int = 4096, clock: Callable[[], float] = time.monotonic
    ) -> None:
        if type(max_parts) is not int or not 1 <= max_parts <= 4096:
            raise ValueError("Invalid vector-cache bound")
        self._maximum = max_parts
        self._clock = clock
        self._lock = Lock()
        self._entries: OrderedDict[tuple[bytes, str], GenerationVectors] = OrderedDict()
        self._parts = 0

    def snapshot(self, pipeline: bytes) -> dict[str, GenerationVectors]:
        """Copy current numerical references; do not retain private query/result data."""
        if type(pipeline) is not bytes or len(pipeline) != 32:
            raise ValueError("Invalid vector-cache pipeline")
        now = self._clock()
        with self._lock:
            expired = [
                key for key, value in self._entries.items() if value.expires <= now
            ]
            for key in expired:
                self._parts -= len(self._entries.pop(key).matrix)
            return {
                key[1]: value
                for key, value in self._entries.items()
                if key[0] == pipeline
            }

    def store(self, pipeline: bytes, values: dict[str, GenerationVectors]) -> None:
        """Merge fully checked generations; oversized items remain usable uncached."""
        with self._lock:
            for identifier, value in values.items():
                key = (pipeline, identifier)
                previous = self._entries.pop(key, None)
                if previous is not None:
                    self._parts -= len(previous.matrix)
                if len(value.matrix) <= self._maximum:
                    self._entries[key] = value
                    self._parts += len(value.matrix)
            while self._parts > self._maximum or len(self._entries) > 2048:
                self._parts -= len(self._entries.popitem(last=False)[1].matrix)

    def expiry(self, generation: str) -> float:
        """Use stable per-generation spreading; no randomness affects search order."""
        return self._clock() + 270 + UUID(generation).int % 31


def snapshot_statement(
    request: ListingQuery,
    now: datetime,
    threshold: int,
    embedding: QueryEmbedding,
    compiled: TextQuery,
    cached: dict[str, GenerationVectors],
    *,
    relevance: bool,
) -> tuple[str, tuple[object, ...]]:
    """Keep canonical eligibility/coverage predicates and return missing vectors.

    The existing builder validates exact model/query/compiler/filter binding.
    Its source CTE boundary is explicit and regression-tested; the old numerical
    SQL suffix is never executed by this reader. All metadata/vectors share one
    SQL snapshot. Binary real[] transport preserves stored float32 bits and avoids
    converting hundreds of thousands of vector components into JSON numbers.
    """
    original, parameters = hybrid_statement(
        request, now, threshold, embedding, compiled, relevance=relevance
    )
    header, separator, _ = original.partition("), scored AS MATERIALIZED (")
    if not separator:
        raise ValueError("Invalid Hybrid source template")
    tier_gate = (
        "AND (CASE WHEN current.original_match THEN 2 WHEN current.expanded_match THEN 1 ELSE 0 END)>=score_policy.minimum_tier"
        if relevance
        else ""
    )
    need_score = (
        "true"
        if relevance
        else "NOT (current.original_match OR current.expanded_match)"
    )
    statement = (
        header
        + """), candidates AS MATERIALIZED (
      SELECT current.*, """
        + need_score
        + """ AS needs_score
      FROM classified AS current CROSS JOIN status CROSS JOIN score_policy
      WHERE status.ready AND current.complete """
        + tier_gate
        + """
    ), missing AS MATERIALIZED (
      SELECT chunk.generation_id,chunk.part_kind,chunk.ordinal,
        encode(array_send(chunk.vector),'base64') AS binary_vector
      FROM listings.embedding_chunks AS chunk JOIN candidates
        ON candidates.generation_id=chunk.generation_id
      WHERE candidates.needs_score AND NOT (chunk.generation_id=ANY(%s::uuid[]))
    ), metadata AS (
      SELECT listing_id,jsonb_build_object(
        'listing_id',listing_id,'generation_id',generation_id,
        'original_match',original_match,'expanded_match',expanded_match,
        'needs_score',needs_score,'created_at',created_at,
        'summary',jsonb_build_object(
          'listing_id',listing_id,'title',title,'description',description,
          'category_code',category_code,'category_label',category_label,
          'condition_code',condition_code,'condition_label',condition_label,
          'asking_price_paise',asking_price_paise,'original_price_paise',original_price_paise,
          'negotiable',negotiable,'pickup_area',pickup_area,
          'available_from',available_from,'available_until',available_until,'availability',availability,
          'sensitive_purchase',sensitive_purchase,
          'image_ids',COALESCE((SELECT array_agg(image.id ORDER BY image.position,image.id)
            FROM listings.images AS image WHERE image.listing_id=candidates.listing_id
              AND image.retired_at IS NULL),ARRAY[]::uuid[])
        )) AS item FROM candidates
    ) SELECT status.*,
      COALESCE((SELECT jsonb_agg(item ORDER BY listing_id) FROM metadata),'[]'::jsonb) AS candidates,
      COALESCE((SELECT jsonb_agg(jsonb_build_array(generation_id,part_kind,ordinal,binary_vector)
        ORDER BY generation_id,part_kind DESC,ordinal) FROM missing),'[]'::jsonb) AS vectors
      FROM status"""
    )
    return statement, parameters[:-2] + ([UUID(key) for key in cached],)


async def read_snapshot(
    connection: AsyncConnection[dict[str, Any]],
    request: ListingQuery,
    now: datetime,
    threshold: int,
    embedding: QueryEmbedding,
    cached: dict[str, GenerationVectors],
    *,
    relevance: bool,
) -> dict[str, Any]:
    """Fetch one fresh result snapshot; caller returns its lease before scoring."""
    try:
        if request.q is None:
            raise ValueError("Hybrid query text required")
        async with connection.transaction():
            await connection.execute("SET LOCAL statement_timeout='3s'")
            await connection.execute("SET LOCAL lock_timeout='1s'")
            compiled = await compile_expansion(connection, request.q)
            statement, parameters = snapshot_statement(
                request,
                now,
                threshold,
                embedding,
                compiled,
                cached,
                relevance=relevance,
            )
            result = await (await connection.execute(statement, parameters)).fetchone()
        if result is None or any(
            type(result.get(key)) is not bool
            for key in ("ready", "category_valid", "condition_valid")
        ):
            raise ValueError("Invalid Hybrid snapshot")
        for field_name, flag in (
            ("category_code", "category_valid"),
            ("condition_code", "condition_valid"),
        ):
            if not result[flag]:
                raise PublicError(
                    ERRORS[422],
                    (FieldError(field_name, "active_catalogue_value_required"),),
                )
        if not result["ready"]:
            raise PublicError(ERRORS[503])
        if not isinstance(result.get("candidates"), list) or not isinstance(
            result.get("vectors"), list
        ):
            raise ValueError("Invalid Hybrid snapshot")
        return result
    except PublicError:
        raise
    except DatabaseError, ValueError, TypeError:
        raise PublicError(ERRORS[503]) from None


def decode_generations(
    rows: list[Any], cache: HybridVectorCache
) -> dict[str, GenerationVectors]:
    """Decode PostgreSQL's real[] binary representation and precompute exact norms."""
    groups: dict[str, dict[tuple[str, int], NDArray[np.float64]]] = {}
    for generation, kind, ordinal, encoded in rows:
        identifier = str(UUID(generation))
        if (
            kind not in ("title", "description")
            or type(ordinal) is not int
            or not 0 <= ordinal <= 95
            or (kind == "title" and ordinal != 0)
        ):
            raise ValueError("Invalid vector part")
        raw = base64.b64decode(encoded, validate=False)
        if len(raw) != 20 + 384 * 8 or struct.unpack("!iiIii", raw[:20]) != (
            1,
            0,
            700,
            384,
            1,
        ):
            raise ValueError("Invalid vector encoding")
        lengths = np.ndarray((384,), dtype=">i4", buffer=raw, offset=20, strides=(8,))
        if not np.all(lengths == 4):
            raise ValueError("Invalid vector encoding")
        vector = np.ndarray(
            (384,), dtype=">f4", buffer=raw, offset=24, strides=(8,)
        ).astype(np.float64)
        parts = groups.setdefault(identifier, {})
        if (kind, ordinal) in parts:
            raise ValueError("Duplicate vector part")
        parts[kind, ordinal] = vector
    result = {}
    for identifier, parts in groups.items():
        descriptions = len(parts) - 1
        if not 1 <= descriptions <= 96 or set(parts) != {("title", 0)} | {
            ("description", index) for index in range(descriptions)
        }:
            raise ValueError("Incomplete vector generation")
        matrix = np.stack(
            [
                parts["title", 0],
                *(parts["description", index] for index in range(descriptions)),
            ]
        )
        norms = np.sqrt(np.cumsum(matrix * matrix, axis=1)[:, -1])
        if (
            not np.isfinite(matrix).all()
            or not np.isfinite(norms).all()
            or np.any(np.abs(norms - 1) > 0.001)
        ):
            raise ValueError("Invalid stored vector")
        matrix.flags.writeable = False
        norms.flags.writeable = False
        result[identifier] = GenerationVectors(matrix, norms, cache.expiry(identifier))
    return result


def score_snapshot(
    snapshot: dict[str, Any],
    request: ListingQuery,
    embedding: QueryEmbedding,
    cached: dict[str, GenerationVectors],
    cache: HybridVectorCache,
) -> Page[ListingSummary]:
    """Pure snapshot ranking in application memory; never opens a DB connection.

    Sequential float64 accumulation intentionally mirrors PostgreSQL's ordered
    sums instead of BLAS dot/pairwise sum. Query inputs round to real[] float32.
    Only complete checked generations enter the bounded process cache. Result
    visibility/fields/lexical tiers always come from this request's SQL snapshot.
    """
    try:
        fresh = decode_generations(snapshot["vectors"], cache)
        available = cached | fresh
        candidates = snapshot["candidates"]
        needed = [row for row in candidates if row["needs_score"]]
        generations = [available[row["generation_id"]] for row in needed]
        numerical = np.empty(0)
        if generations:
            matrix = np.concatenate([value.matrix for value in generations])
            norms = np.concatenate([value.norms for value in generations])
            query = np.asarray(embedding.vector, dtype=np.float32).astype(np.float64)
            query_norm = np.sqrt(np.cumsum(query * query)[-1])
            dots = np.cumsum(matrix * query, axis=1)[:, -1]
            cosines = np.clip(dots / (norms * query_norm), -1, 1)
            counts = np.asarray(
                [len(value.matrix) for value in generations], dtype=np.int64
            )
            starts = np.cumsum(counts) - counts
            title_scores = cosines[starts]
            descriptions = np.ones(len(cosines), dtype=bool)
            descriptions[starts] = False
            description_starts = np.cumsum(counts - 1) - (counts - 1)
            description_scores = np.maximum.reduceat(
                cosines[descriptions], description_starts
            )
            numerical = (
                TITLE_WEIGHT * title_scores + DESCRIPTION_WEIGHT * description_scores
            )
        scores = {
            row["listing_id"]: float(value)
            for row, value in zip(needed, numerical, strict=True)
        }
        rows = [
            row
            for row in candidates
            if row["original_match"]
            or row["expanded_match"]
            or scores[row["listing_id"]] >= SEMANTIC_THRESHOLD
        ]
        if request.sort == "relevance":
            rows.sort(
                key=lambda row: (
                    -(
                        2
                        if row["original_match"]
                        else 1 if row["expanded_match"] else 0
                    ),
                    -scores[row["listing_id"]],
                    UUID(row["listing_id"]).int,
                )
            )
        elif request.sort == "created_desc":
            rows.sort(
                key=lambda row: (
                    datetime.fromisoformat(row["created_at"]),
                    UUID(row["listing_id"]).int,
                ),
                reverse=True,
            )
        elif request.sort in ("price_asc", "price_desc"):
            rows.sort(
                key=lambda row: (
                    row["summary"]["asking_price_paise"],
                    UUID(row["listing_id"]).int,
                ),
                reverse=request.sort == "price_desc",
            )
        else:
            raise ValueError("Invalid Hybrid sort")
        page = PageRequest(request.page, request.page_size)
        output = page_from_window(
            page,
            [
                ListingSummary.model_validate(row["summary"])
                for row in rows[page.offset : page.offset + page.page_size + 1]
            ],
        )
        cache.store(embedding.spec.pipeline_id, fresh)
        return output
    except ValueError, TypeError, KeyError, OverflowError, struct.error:
        raise PublicError(ERRORS[503]) from None
