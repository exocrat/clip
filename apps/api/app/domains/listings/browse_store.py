"""Authoritative PostgreSQL browse query; no projection, cache or fake ranking."""

from datetime import datetime
from typing import Any

from psycopg import AsyncConnection

from app.contracts.domain_types import ListingSummary, ListingQuery
from app.core.errors import ERRORS, FieldError, PublicError
from app.core.pagination import Page, PageRequest, page_from_window
from app.domains.listings.browse_validation import normalize_query
from app.domains.listings.lexical_expansion import TextQuery, compile_expansion
from app.domains.listings.vocabulary import load_vocabulary

# Project only the reviewed public summary. Ownership, selection, revision,
# operational timestamps, upload metadata and object keys never enter this read.
# The image subquery returns references only, without transferring image bodies.
_BROWSE_SELECT_SQL = """
SELECT listing.id AS listing_id, listing.title, listing.description,
    category.code AS category_code, category.label AS category_label,
    listing_condition.code AS condition_code, listing_condition.label AS condition_label,
    listing.asking_price_paise, listing.negotiable, listing.pickup_area,
    listing.available_from, listing.available_until, listing.availability,
    (category.sensitive_category OR listing.asking_price_paise > %s) AS sensitive_purchase,
    COALESCE((SELECT array_agg(image.id ORDER BY image.position, image.id)
              FROM listings.images AS image
              WHERE image.listing_id = listing.id AND image.retired_at IS NULL),
             ARRAY[]::uuid[]) AS image_ids
FROM listings.sale_listings AS listing
JOIN listings.categories AS category ON category.id = listing.category_id
JOIN listings.conditions AS listing_condition ON listing_condition.code = listing.condition_code
WHERE listing.retired_at IS NULL
    AND listing.retirement_pending_operation_id IS NULL
    AND listing.availability = 'available'
    AND listing.available_from <= %s
    AND (listing.available_until IS NULL OR listing.available_until > %s)
"""

KEYWORD_RELEVANCE_POLICY_VERSION = "keyword-relevance-v1"

# Only code-owned fragments can select ordering; client input is never SQL.
_SORT_SQL = {
    "created_desc": "listing.created_at DESC, listing.id DESC",
    "price_asc": "listing.asking_price_paise ASC, listing.id ASC",
    "price_desc": "listing.asking_price_paise DESC, listing.id DESC",
}
# Storage representability, not a product price cap. Bounds beyond the largest
# whole-rupee bigint preserve exact comparison semantics without huge SQL values.
_STORAGE_MAX_PRICE = ((2**63 - 1) // 100) * 100


def browse_statement(
    request: ListingQuery,
    now: datetime,
    sensitive_price_threshold_paise: int,
    *,
    text_query: TextQuery | None = None,
    keyword_relevance: bool = False,
) -> tuple[str, tuple[object, ...]]:
    """Build parameterized browse/search SQL using the authoritative GIN vector.

    plainto_tsquery treats syntax characters as plain text and uses the same
    English normalization as the stored title/description vector. All normalized
    terms must match; an empty normalized query matches nothing. The private
    keyword_relevance option orders original matches before expanded/typo-only,
    then native cover-density rank and UUID. It never reads semantic state.
    Only code-owned SQL fragments are composed; user values stay bound.
    """
    query = normalize_query(request)
    if type(keyword_relevance) is not bool:
        raise ValueError("Invalid private relevance flag")
    if keyword_relevance:
        if query.q is None:
            raise PublicError(ERRORS[422], (FieldError("q", "nonblank_text_required"),))
        if (
            text_query is None
            or not text_query.parameters
            or text_query.parameters[0] != query.q
            or text_query.vocabulary_fingerprint != load_vocabulary().fingerprint
        ):
            raise ValueError("Keyword relevance requires the bound compiled query")
    page = PageRequest(page=query.page, page_size=query.page_size)
    statement = _BROWSE_SELECT_SQL
    # Match Hybrid: a policy threshold above every representable listing price
    # flags no additional purchases, while remaining safe to bind in PostgreSQL.
    parameters: tuple[object, ...] = (
        min(sensitive_price_threshold_paise, _STORAGE_MAX_PRICE),
        now,
        now,
    )
    if query.q is not None:
        # The public Keyword store supplies the reviewed vocabulary expansion.
        # Direct callers may omit it to request original full-text matching.
        if text_query is None:
            statement += " AND listing.search_vector @@ plainto_tsquery('pg_catalog.english', %s)\n"
            parameters += (query.q,)
        else:
            statement += " AND listing.search_vector @@ " + text_query.sql + "\n"
            parameters += text_query.parameters
    for value, predicate in (
        (query.category_code, "category.code = %s"),
        (query.condition_code, "listing_condition.code = %s"),
        (query.negotiable, "listing.negotiable = %s"),
    ):
        if value is not None:
            statement += " AND " + predicate + "\n"
            parameters += (value,)
    if query.min_price_paise is not None:
        if query.min_price_paise > _STORAGE_MAX_PRICE:
            statement += " AND FALSE\n"
        else:
            statement += " AND listing.asking_price_paise >= %s\n"
            parameters += (query.min_price_paise,)
    if query.max_price_paise is not None and query.max_price_paise < _STORAGE_MAX_PRICE:
        statement += " AND listing.asking_price_paise <= %s\n"
        parameters += (query.max_price_paise,)
    if keyword_relevance:
        assert query.q is not None and text_query is not None
        original = "plainto_tsquery('pg_catalog.english', %s)"
        # Ranking selects the query that actually matched within its own tier.
        # Default weights/normalization0 retain the existing positional vector;
        # zero-rank matches stay present and no numeric rank enters the summary.
        statement += (
            "ORDER BY CASE WHEN listing.search_vector @@ "
            + original
            + " THEN 1 ELSE 0 END DESC, CASE WHEN listing.search_vector @@ "
            + original
            + " THEN ts_rank_cd(listing.search_vector, "
            + original
            + ", 0)"
            + " ELSE ts_rank_cd(listing.search_vector, "
            + text_query.sql
            + ", 0) END DESC, listing.id ASC\nLIMIT %s OFFSET %s"
        )
        parameters += (query.q, query.q, query.q, *text_query.parameters)
    else:
        statement += "ORDER BY " + _SORT_SQL[query.sort] + "\nLIMIT %s OFFSET %s"
    return statement, parameters + (page.page_size + 1, page.offset)


async def validate_catalogue_filters(
    connection: AsyncConnection[dict[str, Any]], request: ListingQuery
) -> None:
    """Check active filter codes before missing semantic capability can mask422.

    Shared only inside Listings; no matching query or model work is performed.
    """
    if request.category_code is not None or request.condition_code is not None:
        # Validate against current owned catalogues, not a hard-coded code list
        # or the mere presence of matching listings. Empty valid filters are OK.
        checks = await connection.execute(
            """SELECT
            (%s::text IS NULL OR EXISTS(SELECT 1 FROM listings.categories
                WHERE code=%s AND active)) AS category_valid,
            (%s::text IS NULL OR EXISTS(SELECT 1 FROM listings.conditions
                WHERE code=%s AND active)) AS condition_valid""",
            (
                request.category_code,
                request.category_code,
                request.condition_code,
                request.condition_code,
            ),
        )
        flags = await checks.fetchone()
        if flags is None:
            raise PublicError(ERRORS[503])
        for field, key in (
            ("category_code", "category_valid"),
            ("condition_code", "condition_valid"),
        ):
            if not flags[key]:
                raise PublicError(
                    ERRORS[422], (FieldError(field, "active_catalogue_value_required"),)
                )


async def read_browse_page(
    connection: AsyncConnection[dict[str, Any]],
    request: ListingQuery,
    now: datetime,
    sensitive_price_threshold_paise: int,
    *,
    expanded_search: bool = False,
    keyword_relevance: bool = False,
) -> Page[ListingSummary]:
    """Validate catalogue filters, then fetch one window plus a lookahead row.

    Caller eligibility is enforced by ListingsBrowseService before this owned
    store operation. The result statement applies every visibility/text/filter
    predicate before LIMIT/OFFSET. Each sort has a UUID tie-break; concurrent
    mutations can shift pages. Catalogue validation uses this same connection.
    Private keyword relevance implies vocabulary/typo expansion but no model,
    embedding table or pipeline/configuration. Public dispatch selects this flag.
    """
    request = normalize_query(request)
    if type(keyword_relevance) is not bool:
        raise ValueError("Invalid private relevance flag")
    if keyword_relevance and request.q is None:
        raise PublicError(ERRORS[422], (FieldError("q", "nonblank_text_required"),))
    page = PageRequest(page=request.page, page_size=request.page_size)
    await validate_catalogue_filters(connection, request)
    text_query = (
        await compile_expansion(connection, request.q)
        if (expanded_search or keyword_relevance) and request.q is not None
        else None
    )
    statement, parameters = browse_statement(
        request,
        now,
        sensitive_price_threshold_paise,
        text_query=text_query,
        keyword_relevance=keyword_relevance,
    )
    cursor = await connection.execute(statement, parameters)
    rows = await cursor.fetchall()
    return page_from_window(page, [ListingSummary.model_validate(row) for row in rows])
