"""Read-only vector/index fingerprint; no AWS, target discovery or raw vector output.

The caller binds and owns its exact connection/transaction. This pure snapshot
is shared by a fresh native rebuild and a separately approved read-only RDS
window; it cannot reset/reload, activate a role/pipeline or accept a target URL.
"""

import hashlib
import math

from data.generators.manifest import canonical_json


def vector_index_snapshot(connection):
    """Hash current ready parts/indexes in the native rebuild's canonical order.

    Exclude random generation IDs, leases and audit times. Validate count, finite
    384-dimensional parts and current source relation before emitting only hashes,
    counts and safe schema definitions. No source text or vector coordinates leave
    this function. Source identity/media integrity is checked by its caller.
    """
    rows = connection.execute("""SELECT g.listing_id::text,encode(g.pipeline_id,'hex'),
        encode(g.source_fingerprint,'hex'),c.part_kind,c.ordinal,c.vector
        FROM listings.embedding_generations g JOIN listings.embedding_chunks c
        ON c.generation_id=g.generation_id
        JOIN listings.sale_listings l ON l.id=g.listing_id
        WHERE g.state='ready' AND l.retired_at IS NULL AND l.retirement_pending_operation_id IS NULL
          AND g.source_fingerprint=listings.embedding_source_fingerprint(l.title,l.description)
        ORDER BY g.listing_id,c.part_kind,c.ordinal""").fetchall()
    if (
        len(rows) != 2000
        or len({r[0] for r in rows}) != 1000
        or any(
            r[3] not in {"title", "description"}
            or r[4] != 0
            or len(r[5]) != 384
            or any(not math.isfinite(value) for value in r[5])
            for r in rows
        )
    ):
        raise ValueError("snapshot_current_vector_scope_changed")
    if any(
        {r[3] for r in rows if r[0] == identifier} != {"title", "description"}
        for identifier in {r[0] for r in rows}
    ):
        raise ValueError("snapshot_parts_incomplete")
    indexes = connection.execute(
        """SELECT schemaname,indexname,indexdef FROM pg_indexes
        WHERE schemaname IN ('identity','listings') ORDER BY schemaname,indexname"""
    ).fetchall()
    if not indexes:
        raise ValueError("snapshot_indexes_missing")
    return {
        "listings": 1000,
        "vector_parts": len(rows),
        "logical_vectors_sha256": hashlib.sha256(canonical_json(rows)).hexdigest(),
        "indexes_sha256": hashlib.sha256(canonical_json(indexes)).hexdigest(),
        "indexes": indexes,
    }
