"""Listings-owned hybrid reader used by the opt-in public Search runtime.

Authorization must precede this persistence boundary, as for browse_store.
One result statement checks the exact supported serving space and complete
current eligible-source coverage, then scores/unions/orders/pages its snapshot.
The existing keyword path remains independent. Never log query/vector/DB errors.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
from typing import Any

from psycopg import AsyncConnection, Error as DatabaseError
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from app.contracts.domain_types import ListingQuery, ListingSummary
from app.core.errors import ERRORS, FieldError, PublicError
from app.core.money import validate_paise
from app.core.pagination import Page, PageRequest, page_from_window
from app.domains.listings.browse_validation import normalize_query
from app.domains.listings.embedding_client import SemanticHelper, HelperUnavailable
from app.domains.listings.embedding_types import (
    PipelineSpec,
    default_pipeline_spec,
    validated_vector,
)
from app.domains.listings.lexical_expansion import TextQuery, compile_expansion
from app.domains.listings.vocabulary import load_vocabulary
from app.domains.listings.category_text import DISCOVERY_VECTOR_SQL

POLICY_VERSION = "hybrid-blend-v2-category"
TITLE_WEIGHT = 0.35
DESCRIPTION_WEIGHT = 0.65
SEMANTIC_THRESHOLD = 0.35
_STORAGE_MAX_PRICE = ((2**63 - 1) // 100) * 100
_SORTS = {
    "created_desc": "scored.created_at DESC, scored.listing_id DESC",
    "price_asc": "scored.asking_price_paise ASC, scored.listing_id ASC",
    "price_desc": "scored.asking_price_paise DESC, scored.listing_id DESC",
}
_RELEVANCE = "CASE WHEN scored.original_match THEN 2 WHEN scored.expanded_match THEN 1 ELSE 0 END DESC, scored.semantic_score DESC, scored.listing_id ASC"


@dataclass(frozen=True)
class QueryEmbedding:
    """Private exact query/model binding; vectors/digests excluded from repr.

    Construct via bind_query after a real helper call. In-process callers are
    trusted code: shape/binding validation does not attest model provenance.
    Native coordinate fixtures are explicitly mathematical tests only.
    """

    spec: PipelineSpec
    query_fingerprint: bytes = field(repr=False)
    vector: tuple[float, ...] = field(repr=False)


def bind_query(text: str, spec: PipelineSpec, vector: object) -> QueryEmbedding:
    """Bind the trimmed original text and exact current helper configuration."""
    if (
        not isinstance(text, str)
        or not text.strip()
        or len(text.strip()) > 120
        or spec != default_pipeline_spec()
    ):
        raise ValueError("Invalid hybrid query binding")
    return QueryEmbedding(
        spec, hashlib.sha256(text.strip().encode()).digest(), validated_vector(vector)
    )


def _text_request(request: ListingQuery) -> ListingQuery:
    """Preserve existing422 validation; this private operation requires text."""
    query = normalize_query(request)
    if query.q is None:
        raise PublicError(ERRORS[422], (FieldError("q", "nonblank_text_required"),))
    return query


def hybrid_statement(
    request: ListingQuery,
    now: datetime,
    sensitive_price_threshold_paise: int,
    embedding: QueryEmbedding,
    text_query: TextQuery,
    *,
    relevance: bool = False,
) -> tuple[str, tuple[object, ...]]:
    """Build one bounded parameterized snapshot read with an explicit summary.

    relevance=True selects original/expanded/semantic tiers and blended score.
    Otherwise preserve the public request's recency/price semantics. The caller
    chooses this reader for Hybrid mode. Model/query/compiler binding failures
    are dependency errors. bind_query validates the request vector; NOT NULL and
    the embedding_chunks CHECK validate stored vectors at every write. Compute
    the query norm once and inline the original ordered cosine arithmetic, so
    every candidate does not repeat validation and query-norm SQL. Retain exact
    norms rather than assuming that the allowed near-unit vectors have norm1.
    """
    query = _text_request(request)
    assert query.q is not None
    if (
        type(relevance) is not bool
        or not isinstance(now, datetime)
        or now.utcoffset() is None
        or type(sensitive_price_threshold_paise) is not int
        or sensitive_price_threshold_paise < 0
    ):
        raise ValueError("Invalid hybrid read configuration")
    validate_paise(sensitive_price_threshold_paise)
    checked = bind_query(query.q, embedding.spec, embedding.vector)
    if (
        checked.query_fingerprint != embedding.query_fingerprint
        or not text_query.parameters
        or text_query.parameters[0] != query.q
        or text_query.vocabulary_fingerprint != load_vocabulary().fingerprint
    ):
        raise ValueError("Invalid hybrid query binding")
    page = PageRequest(query.page, query.page_size)
    # Relevance tiers strictly dominate similarity. Skip lower tiers only when
    # higher tiers alone fill this exact page plus its has-next lookahead. Other
    # sorts need similarity only for non-lexical membership. Coverage still
    # checks every eligible source before either optimisation is allowed.
    tier_policy = (
        "CASE WHEN (SELECT count(*) FROM classified WHERE original_match)>=input.window_end THEN 2 "
        "WHEN (SELECT count(*) FROM classified WHERE original_match OR expanded_match)>=input.window_end THEN 1 ELSE 0 END"
        if relevance
        else "0"
    )
    tier_gate = (
        " AND (CASE WHEN current.original_match THEN 2 WHEN current.expanded_match THEN 1 ELSE 0 END)>=score_policy.minimum_tier"
        if relevance
        else ""
    )
    scoring_gate = (
        tier_gate
        if relevance
        else " AND NOT (current.original_match OR current.expanded_match)"
    )
    statement = (
        """WITH input_base AS MATERIALIZED (
        SELECT %s::bytea AS pipeline_id,%s::jsonb AS encoding,%s::real[] AS vector,
        %s::timestamptz AS now,%s::bigint AS sensitive_threshold,
        %s::double precision AS title_weight,%s::double precision AS description_weight,
        %s::double precision AS cutoff,
        plainto_tsquery('pg_catalog.english', %s) AS original, """
        + text_query.sql
        + """ AS expanded,%s::bigint AS window_end
    ), input AS MATERIALIZED (
        SELECT input_base.*,(SELECT sqrt(sum(component::double precision ^ 2 ORDER BY ordinal))
          FROM unnest(input_base.vector) WITH ORDINALITY AS item(component,ordinal)) AS query_norm
        FROM input_base
    ), catalogue AS MATERIALIZED (SELECT
        NOT EXISTS(SELECT 1 FROM unnest(%s::text[]) AS requested(code)
          WHERE NOT EXISTS(SELECT 1 FROM listings.categories WHERE code=requested.code AND active)) AS category_valid,
        NOT EXISTS(SELECT 1 FROM unnest(%s::text[]) AS requested(code)
          WHERE NOT EXISTS(SELECT 1 FROM listings.conditions WHERE code=requested.code AND active)) AS condition_valid
    ), pipeline AS MATERIALIZED (
        SELECT pipeline.pipeline_id FROM listings.embedding_pipelines AS pipeline,input
        WHERE pipeline.state='serving' AND pipeline.pipeline_id=input.pipeline_id AND pipeline.encoding=input.encoding
    ), eligible AS MATERIALIZED (
        SELECT listing.id AS listing_id,listing.title,listing.description,
        category.code AS category_code,category.label AS category_label,
        listing_condition.code AS condition_code,listing_condition.label AS condition_label,
        listing.asking_price_paise,listing.original_price_paise,listing.negotiable,listing.pickup_area,
        listing.available_from,listing.available_until,listing.availability,
        (category.sensitive_category OR listing.asking_price_paise>input.sensitive_threshold) AS sensitive_purchase,
        listing.created_at,listing.search_vector,
        """
        + DISCOVERY_VECTOR_SQL
        + """ AS discovery_vector
        FROM listings.sale_listings AS listing
        JOIN listings.categories AS category ON category.id=listing.category_id
        JOIN listings.conditions AS listing_condition ON listing_condition.code=listing.condition_code
        CROSS JOIN input
        WHERE listing.retired_at IS NULL AND listing.retirement_pending_operation_id IS NULL
          AND listing.availability='available' AND listing.available_from<=input.now
          AND (listing.available_until IS NULL OR listing.available_until>input.now)
    """
    )
    parameters: tuple[object, ...] = (
        checked.spec.pipeline_id,
        Jsonb(checked.spec.encoding),
        list(checked.vector),
        now.astimezone(UTC),
        # Stored prices cannot exceed this bound; clamping preserves the strict
        # greater-than policy comparison without an out-of-range bigint bind.
        min(sensitive_price_threshold_paise, _STORAGE_MAX_PRICE),
        TITLE_WEIGHT,
        DESCRIPTION_WEIGHT,
        SEMANTIC_THRESHOLD,
        query.q,
        *text_query.parameters,
        page.offset + page.page_size + 1,
        query.category_code,
        query.condition_code,
    )
    for values, predicate in (
        (query.category_code, "category.code=ANY(%s)"),
        (query.condition_code, "listing_condition.code=ANY(%s)"),
        (query.negotiable, "listing.negotiable=%s"),
    ):
        if values is not None and values != []:
            statement += " AND " + predicate
            parameters += (values,)
    if query.min_price_paise is not None:
        if query.min_price_paise > _STORAGE_MAX_PRICE:
            statement += " AND FALSE"
        else:
            statement += " AND listing.asking_price_paise>=%s"
            parameters += (query.min_price_paise,)
    if query.max_price_paise is not None and query.max_price_paise < _STORAGE_MAX_PRICE:
        statement += " AND listing.asking_price_paise<=%s"
        parameters += (query.max_price_paise,)
    statement += (
        """
    ), current AS MATERIALIZED (
        SELECT eligible.*,generation.generation_id,
        (generation.generation_id IS NOT NULL AND generation.title_count=1
          AND generation.description_count BETWEEN 1 AND 96
          AND parts.titles=1 AND parts.descriptions=generation.description_count
          AND parts.first_description=0 AND parts.last_description=generation.description_count-1) AS complete
        FROM eligible LEFT JOIN listings.embedding_generations AS generation
          ON generation.listing_id=eligible.listing_id
          AND generation.pipeline_id=(SELECT pipeline_id FROM pipeline)
          AND generation.state='ready'
          AND generation.source_fingerprint=listings.embedding_source_fingerprint(eligible.title,eligible.description)
        LEFT JOIN LATERAL (SELECT count(*) FILTER (WHERE part_kind='title') AS titles,
          count(*) FILTER (WHERE part_kind='description') AS descriptions,
          min(ordinal) FILTER (WHERE part_kind='description') AS first_description,
          max(ordinal) FILTER (WHERE part_kind='description') AS last_description
          FROM listings.embedding_chunks WHERE generation_id=generation.generation_id) AS parts ON true
    ), status AS MATERIALIZED (
        SELECT catalogue.*,(EXISTS(SELECT 1 FROM pipeline)
          AND NOT EXISTS(SELECT 1 FROM current WHERE complete IS DISTINCT FROM true)) AS ready FROM catalogue
    ), classified AS MATERIALIZED (
        SELECT current.*,current.discovery_vector @@ input.original AS original_match,
        current.discovery_vector @@ input.expanded AS expanded_match FROM current CROSS JOIN input
    ), score_policy AS MATERIALIZED (SELECT """
        + tier_policy
        + """ AS minimum_tier FROM input
    ), scored AS MATERIALIZED (
        SELECT current.*,
        input.title_weight*scores.title_score+input.description_weight*scores.description_score AS semantic_score
        FROM classified AS current CROSS JOIN input CROSS JOIN status CROSS JOIN score_policy
        CROSS JOIN LATERAL (SELECT
          max(math.cosine) FILTER (WHERE chunk.part_kind='title') AS title_score,
          max(math.cosine) FILTER (WHERE chunk.part_kind='description') AS description_score
          FROM listings.embedding_chunks AS chunk
          CROSS JOIN LATERAL (SELECT greatest(-1.0,least(1.0,
            sum(left_value::double precision * right_value::double precision ORDER BY ordinal)
            /(sqrt(sum(left_value::double precision ^ 2 ORDER BY ordinal))*input.query_norm))) AS cosine
            FROM unnest(chunk.vector,input.vector) WITH ORDINALITY
              AS component(left_value,right_value,ordinal)) AS math
          WHERE chunk.generation_id=current.generation_id AND status.ready AND current.complete"""
        + scoring_gate
        + """) AS scores
        WHERE status.ready AND current.complete"""
        + tier_gate
        + """
    ), ranked AS (
        SELECT scored.*,row_number() OVER (ORDER BY """
        + (_RELEVANCE if relevance else _SORTS[query.sort])
        + """) AS position
        FROM scored,input WHERE original_match OR expanded_match OR semantic_score>=input.cutoff
    ), page_window AS (
        SELECT * FROM ranked ORDER BY position LIMIT %s OFFSET %s
    ), payload AS (
        SELECT page_window.position,jsonb_build_object(
          'listing_id',page_window.listing_id,'title',page_window.title,'description',page_window.description,
          'category_code',page_window.category_code,'category_label',page_window.category_label,
          'condition_code',page_window.condition_code,'condition_label',page_window.condition_label,
          'asking_price_paise',page_window.asking_price_paise,'original_price_paise',page_window.original_price_paise,
          'negotiable',page_window.negotiable,'pickup_area',page_window.pickup_area,
          'available_from',page_window.available_from,'available_until',page_window.available_until,'availability',page_window.availability,
          'sensitive_purchase',page_window.sensitive_purchase,
          'image_ids',COALESCE((SELECT array_agg(image.id ORDER BY image.position,image.id) FROM listings.images AS image
            WHERE image.listing_id=page_window.listing_id AND image.retired_at IS NULL),ARRAY[]::uuid[])
        ) AS summary FROM page_window
    ) SELECT status.*,
      COALESCE((SELECT jsonb_agg(summary ORDER BY position) FROM payload),'[]'::jsonb) AS items FROM status"""
    )
    parameters += (page.page_size + 1, page.offset)
    return statement, parameters


async def read_hybrid_page(
    connection: AsyncConnection[dict[str, Any]],
    request: ListingQuery,
    now: datetime,
    sensitive_price_threshold_paise: int,
    embedding: QueryEmbedding,
    *,
    relevance: bool = False,
) -> Page[ListingSummary]:
    """Read one page from a bound vector; caller must have authorized eligibility.

    Only normalization precedes the single result snapshot. Catalogue flags,
    serving config, all filtered source coverage and payload share that snapshot.
    Missing capability/coverage raises existing dependency_unavailable503; no
    partial rows or private metadata escape. No native error text is forwarded.
    """
    query = _text_request(request)
    assert query.q is not None
    try:
        async with connection.transaction():
            await connection.execute("SET LOCAL statement_timeout='3s'")
            await connection.execute("SET LOCAL lock_timeout='1s'")
            compiled = await compile_expansion(connection, query.q)
            statement, parameters = hybrid_statement(
                query,
                now,
                sensitive_price_threshold_paise,
                embedding,
                compiled,
                relevance=relevance,
            )
            result = await (await connection.execute(statement, parameters)).fetchone()
        if result is None or any(
            type(result.get(key)) is not bool
            for key in ("category_valid", "condition_valid", "ready")
        ):
            raise ValueError("Invalid hybrid read result")
        for name, flag in [
            ("category_code", "category_valid"),
            ("condition_code", "condition_valid"),
        ]:
            if not result[flag]:
                raise PublicError(
                    ERRORS[422], (FieldError(name, "active_catalogue_value_required"),)
                )
        if not result["ready"]:
            raise PublicError(ERRORS[503])
        if not isinstance(result.get("items"), list):
            raise ValueError("Invalid hybrid read result")
        return page_from_window(
            PageRequest(query.page, query.page_size),
            [ListingSummary.model_validate(item) for item in result["items"]],
        )
    except PublicError:
        raise
    except DatabaseError, TimeoutError, ValueError, TypeError:
        raise PublicError(ERRORS[503]) from None


async def encode_hybrid_query(
    helper: SemanticHelper, request: ListingQuery
) -> QueryEmbedding:
    """Encode/bind original text before a search borrows a database connection.

    Only immutable query/model vectors can be reused by the helper. Current
    authorization, availability, coverage and ranking still run on every request.
    No inference failure falls back to keyword or previously retrieved results.
    """
    query = _text_request(request)
    assert query.q is not None
    try:
        async with asyncio.timeout(20):
            encoded = await helper.encode_query(query.q)
            return bind_query(query.q, helper.spec, encoded.vector)
    except HelperUnavailable, TimeoutError, ValueError, TypeError:
        raise PublicError(ERRORS[503]) from None


async def search_hybrid_page(
    connection: AsyncConnection[dict[str, Any]],
    helper: SemanticHelper,
    request: ListingQuery,
    now: datetime,
    sensitive_price_threshold_paise: int,
    *,
    relevance: bool = False,
) -> Page[ListingSummary]:
    """Explicit helper-to-reader bridge; public store requires managed injection.

    An idle dedicated autocommit connection prevents inference under caller-held
    DB locks. Original trimmed query goes unchanged to the shared helper. Overall
    work is20s (plus helper cancellation/reap allowance); capacity/failure is503,
    never keyword-only success. Authorization remains the upstream prerequisite.
    """
    query = _text_request(request)
    assert query.q is not None
    try:
        if (
            not connection.autocommit
            or connection.info.transaction_status != TransactionStatus.IDLE
        ):
            raise ValueError("Hybrid helper requires idle connection")
        async with asyncio.timeout(20):
            bound = await encode_hybrid_query(helper, query)
            return await read_hybrid_page(
                connection,
                query,
                now,
                sensitive_price_threshold_paise,
                bound,
                relevance=relevance,
            )
    except PublicError:
        raise
    except HelperUnavailable, DatabaseError, TimeoutError, ValueError, TypeError:
        raise PublicError(ERRORS[503]) from None
