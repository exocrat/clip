"""Step6 local rebuild comparisons; no target arguments, fake vectors or acceptance."""

import hashlib

from data.generators.manifest import canonical_json


def vector_snapshot(cluster):
    """Hash logical source/vector parts and real indexes, excluding random job IDs/times."""
    with cluster.connection() as connection:
        rows = connection.execute(
            """SELECT g.listing_id::text, encode(g.pipeline_id,'hex'),
            encode(g.source_fingerprint,'hex'), c.part_kind, c.ordinal, c.vector
            FROM listings.embedding_generations g JOIN listings.embedding_chunks c
            ON c.generation_id=g.generation_id WHERE g.state='ready'
            ORDER BY g.listing_id,c.part_kind,c.ordinal"""
        ).fetchall()
        indexes = connection.execute(
            """SELECT schemaname,indexname,indexdef FROM pg_indexes
            WHERE schemaname IN ('identity','listings') ORDER BY schemaname,indexname"""
        ).fetchall()
    if len(rows) != 2000 or len({r[0] for r in rows}) != 1000:
        raise ValueError("Expected1000sources/2000actual vector parts")
    return {
        "listings": 1000,
        "vector_parts": len(rows),
        "logical_vectors_sha256": hashlib.sha256(canonical_json(rows)).hexdigest(),
        "indexes_sha256": hashlib.sha256(canonical_json(indexes)).hexdigest(),
        "indexes": indexes,
    }


async def build_before_reset(cluster):
    """Encode all sources before reset, close/reap helper, retain comparison evidence."""
    from scripts.evaluation.reference_local import ROOT
    from scripts.evaluation.reference_embeddings import (
        ReferenceHelper,
        prepare_reference,
    )

    helper = ReferenceHelper(
        ROOT / ".tools/semantic/venv/bin/python", ROOT / ".tools/semantic/model"
    )
    try:
        await helper.start()
        coverage = await prepare_reference(cluster, helper)
        snapshot = vector_snapshot(cluster)
    finally:
        await helper.close()
    if helper.pid is not None or helper.starts != 1:
        raise ValueError("Pre-reset helper lifecycle differs")
    return {
        "pipeline": coverage,
        "snapshot": snapshot,
        "helper_stopped": True,
        "helper_starts": helper.starts,
        "windows_started": helper.windows_started,
    }
