"""Listings-private lexical category extension; never an embedding input.

Read the joined catalogue label at query time so renames and reassignment take
effect without copying labels into listings or invalidating semantic generations.
Only trusted SQL fragments belong here; query text remains bound by callers.
"""

DISCOVERY_VECTOR_SQL = (
    "(listing.search_vector || "
    "to_tsvector('pg_catalog.english', coalesce(category.label, '')))"
)


def keyword_candidates_sql(query_sql: str) -> str:
    """Keep the GIN-compatible baseline and union category-assisted matches.

    The supplemental branch evaluates the combined vector, allowing independent
    terms across title/description/category. UNION deduplicates before pagination.
    It is a live-label scan, not a claim of indexed supplemental retrieval or NFR
    latency. The outer authorized query still applies every visibility/filter rule.
    query_sql must be a code-owned expression from the lexical compiler.
    """
    return (
        "WITH lexical_input AS MATERIALIZED (SELECT "
        + query_sql
        + " AS query), lexical_candidates AS ("
        "SELECT listing.id FROM listings.sale_listings AS listing, lexical_input "
        "WHERE listing.search_vector @@ lexical_input.query UNION "
        "SELECT listing.id FROM listings.sale_listings AS listing "
        "JOIN listings.categories AS category ON category.id=listing.category_id "
        "CROSS JOIN lexical_input WHERE "
        + DISCOVERY_VECTOR_SQL
        + " @@ lexical_input.query)\n"
    )
