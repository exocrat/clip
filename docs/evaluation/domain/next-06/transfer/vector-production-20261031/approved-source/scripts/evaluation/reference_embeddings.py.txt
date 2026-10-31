"""Real offline model/operator checks on the runner's newly owned reference DB.

This is engineering smoke evidence, not human relevance labels or cloud acceptance.
The caller owns the cluster and helper lifetime; no target URL is accepted here.
"""

import asyncio
from dataclasses import asdict

import psycopg
from psycopg.rows import dict_row

from app.domains.listings.embedding_bootstrap import EmbeddingBootstrap
from app.domains.listings.embedding_client import SemanticHelper, HelperUnavailable
from app.domains.listings.embedding_store import EmbeddingStore
from app.domains.listings.embedding_worker import EmbeddingWorker


class ReferenceHelper(SemanticHelper):
    """Keep the production per-call limits plus a finite local-run work budget."""

    async def _request(self, operation, fields):
        # A listing can consume at most97windows; leave room before admitting it.
        if self.windows_started > 2400:
            raise HelperUnavailable("reference_window_budget")
        return await super()._request(operation, fields)


def connection_options(cluster, database):
    """Only the owned Unix socket/role, with bounded autocommit statements."""
    from data.generators.reference_load import ROLE

    return dict(
        host=str(cluster.socket),
        port=55438,
        dbname=database,
        user=ROLE,
        connect_timeout=3,
        autocommit=True,
        row_factory=dict_row,
        options="-c statement_timeout=5000 -c lock_timeout=1000",
    )


async def prepare_reference(cluster, helper):
    """Prepare, queue, encode actual text, then guardedly activate all1000sources."""
    from data.generators.reference_load import DATABASE

    async with await psycopg.AsyncConnection.connect(
        **connection_options(cluster, DATABASE)
    ) as connection:
        operator = EmbeddingBootstrap(connection)
        before = await operator.status()
        if before.state != "absent" or before.live != 1000:
            raise ValueError("Reference pipeline initial state differs")
        await operator.prepare()
        queued = await operator.queue(1000)
        if queued != 1000:
            raise ValueError("Reference pipeline queue count differs")
        worker = EmbeddingWorker(EmbeddingStore(connection), helper)
        for index in range(1000):
            if await worker.run_one() != "published":
                raise ValueError("Real reference embedding job did not publish")
            if (index + 1) % 100 == 0:
                print(f"Real model vectors published: {index + 1}/1000", flush=True)
        if await worker.run_one() != "idle":
            raise ValueError("Unexpected extra embedding work")
        coverage = await operator.activate()
        require_coverage(coverage, 1000)
        return {"queued": queued, "published": 1000, "coverage": asdict(coverage)}


def require_coverage(coverage, count):
    """Reject partial/stale/failed coverage even if a pipeline is marked serving."""
    if (
        coverage.state != "serving"
        or not coverage.complete
        or coverage.live != count
        or coverage.conflicting_serving
        or any(
            getattr(coverage, key)
            for key in (
                "missing",
                "stale",
                "pending",
                "leased",
                "failed",
                "invalid_parts",
            )
        )
    ):
        raise ValueError("Reference vector coverage incomplete")


async def search_smoke(client, bundle):
    """Real HTTP modes, availability, pagination and Hybrid union; no quality labels."""
    available = {
        row["id"]
        for row in bundle["listings"]
        if row["availability_scenario"] == "available"
    }
    observations = []
    for query in (
        "cycle",
        "cycel",
        "vehicle",
        "wheeled vehicle",
        "books",
        "office chair",
    ):
        modes = {}
        for mode in ("keyword", "hybrid"):
            ids = []
            for page in range(1, 12):
                response = await client.get(
                    "/listings",
                    params={
                        "q": query,
                        "search_mode": mode,
                        "sort": "relevance",
                        "page": page,
                        "page_size": 100,
                    },
                )
                if response.status_code != 200:
                    raise ValueError(
                        f"Reference {mode} query status={response.status_code}"
                    )
                rows = response.json()["items"]
                ids.extend(row["listing_id"] for row in rows)
                if len(rows) < 100:
                    break
            else:
                raise ValueError("Reference search pagination exceeded bound")
            if len(ids) != len(set(ids)) or not set(ids) <= available:
                raise ValueError("Reference search leaked hidden/duplicate rows")
            modes[mode] = ids
        if not modes["keyword"] or not set(modes["keyword"]) <= set(modes["hybrid"]):
            raise ValueError("Reference known-vocabulary Hybrid union failed")
        observations.append(
            {
                "query": query,
                "keyword_count": len(modes["keyword"]),
                "hybrid_count": len(modes["hybrid"]),
                "hybrid_first_five": modes["hybrid"][:5],
            }
        )
    return {
        "cases": observations,
        "human_relevance_review": "pending; no labels inferred",
    }


async def wait_for_publication(cluster, dispatcher):
    """Observe the real background worker after normal HTTP creation, never encode manually."""
    async with asyncio.timeout(30):
        while dispatcher.status.published != 1:
            if dispatcher.status.state in {"failed", "unavailable"}:
                raise ValueError("Normal publication dispatcher unavailable")
            await asyncio.sleep(0.1)
        async with await psycopg.AsyncConnection.connect(
            **connection_options(cluster, "clip_test_next06_probe")
        ) as connection:
            coverage = await EmbeddingBootstrap(connection).status()
            require_coverage(coverage, 1001)
            return asdict(coverage)
