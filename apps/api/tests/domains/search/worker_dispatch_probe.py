"""Real normal-API dispatcher/edit/reindex probe on one new private native DB.

The explicit test bootstrap is separate from the dispatcher. Only caller and
eligibility are synthetic; model, SQL, invalidation, queue/lease and HTTP are real.
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

import httpx2 as httpx  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402
from psycopg_pool import AsyncConnectionPool  # noqa: E402
from app.core.auth import CallerContext, require_caller  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.domains.listings.embedding_client import SemanticHelper  # noqa: E402
import app.domains.listings.search_runtime as runtime_module  # noqa: E402
from apps.api.tests.domains.search.browser_preview import (
    require_preview_settings,
)  # noqa: E402
from apps.api.tests.domains.search.native_preview import (
    NativeCluster,
    PreviewIdentity,
    CALLER,
    bootstrap,
)  # noqa: E402
from scripts.evaluation.semantic.ipc_probe import rss  # noqa: E402


async def until(predicate) -> None:
    """Bound each native scheduling observation; no sleep-based success assumption."""
    async with asyncio.timeout(12):
        while not predicate():
            await asyncio.sleep(0.05)


async def probe(cluster: NativeCluster) -> None:
    """One shared helper at a time, <=40windows/6min/512MiB sampled API+helper."""
    from app import main

    helpers = []
    owned = set()
    faults = []
    observations = []
    peak = 0
    simultaneous = 0
    stopped = asyncio.Event()
    parent = os.getpid()
    owner = asyncio.current_task()
    started = time.monotonic()
    old_settings = main.settings
    old_factory = runtime_module.SemanticHelper
    interpreter = ROOT / ".tools/semantic/venv/bin/python"
    model = ROOT / ".tools/semantic/model"

    class ObservedHelper(SemanticHelper):
        """Observe real helper instances; no encode/start/close behavior is replaced."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            helpers.append(self)

    async def monitor():
        nonlocal peak, simultaneous
        while not stopped.is_set():
            for helper in helpers:
                if helper.pid is not None:
                    owned.add(helper.pid)
            try:
                rows = await asyncio.to_thread(rss, {parent, *owned})
            except OSError, ValueError, subprocess.SubprocessError:
                rows = {}
            active = [pid for pid in owned if pid in rows and rows[pid][0] == parent]
            simultaneous = max(simultaneous, len(active))
            peak = max(
                peak, rows.get(parent, (0, 0))[1] + sum(rows[pid][1] for pid in active)
            )
            if (
                parent not in rows
                or peak >= 512 * 1024 * 1024
                or simultaneous > 1
                or sum(helper.windows_started for helper in helpers) > 40
                or time.monotonic() - started > 360
            ):
                faults.append("supervision_limit")
                assert owner is not None
                owner.cancel()
                return
            await asyncio.sleep(0.05)

    async def eligible(user_id):
        return await PreviewIdentity().account_is_eligible(user_id)

    async def request(mode):
        """Exercise the actual normal app collection router/service/SQL/helper."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app), base_url="http://127.0.0.1"
        ) as client:
            response = await client.get(
                "/listings",
                params={"q": "cycle", "search_mode": mode, "sort": "relevance"},
            )
            assert response.headers["cache-control"] == "private, no-store"
            return response

    control = AsyncConnectionPool(
        cluster.url,
        kwargs={"autocommit": True, "row_factory": dict_row},
        min_size=1,
        max_size=1,
        open=False,
    )
    watchdog = asyncio.create_task(monitor())
    bootstrap_helper = ObservedHelper(interpreter, model)
    runtime_module.SemanticHelper = ObservedHelper
    main.settings = Settings(
        environment="test",
        database_url=cluster.url,
        hybrid_search_enabled=True,
        hybrid_worker_enabled=True,
        hybrid_search_interpreter=interpreter,
        hybrid_search_model_dir=model,
    )
    main.app.dependency_overrides[require_caller] = lambda: CallerContext(
        CALLER, "regular", datetime.now(UTC) + timedelta(minutes=5)
    )
    main.app.state.listings_browse_identity = SimpleNamespace(
        account_is_eligible=eligible
    )
    try:
        await control.open()
        await control.wait(timeout=5)
        async with main.lifespan(main.app):
            runtime = main.app.state.search_runtime
            dispatch = runtime.dispatcher
            assert dispatch is not None
            await until(lambda: dispatch.status.last_outcome == "idle")
            async with control.connection() as connection:
                count = await (
                    await connection.execute(
                        "SELECT count(*) AS n FROM listings.embedding_pipelines"
                    )
                ).fetchone()
                assert count["n"] == 0
            assert dispatch.status.published == 0
            observations.append(
                {"case": "empty_registry", "outcome": "idle", "pipeline_count": 0}
            )
        assert runtime.helper.pid is None and dispatch._pool.closed
        # Explicit fixture preparation only, after the no-bootstrap assertion.
        await bootstrap(control, bootstrap_helper)
        await bootstrap_helper.close()
        async with main.lifespan(main.app):
            runtime = main.app.state.search_runtime
            dispatch = runtime.dispatcher
            assert dispatch is not None and dispatch._helper is runtime.helper
            assert dispatch._pool is not runtime.pool
            await until(lambda: dispatch.status.last_outcome == "idle")
            async with dispatch._pool.connection() as connection:
                assert connection.autocommit
            async with control.connection() as connection:
                row = await (
                    await connection.execute(
                        "SELECT id FROM listings.sale_listings WHERE title='Campus bicycle'"
                    )
                ).fetchone()
                listing = row["id"]
                before = await (
                    await connection.execute(
                        "SELECT generation_id FROM listings.embedding_generations WHERE listing_id=%s",
                        (listing,),
                    )
                ).fetchone()
                text = "A pedal powered bicycle for commuting around campus. Freshly serviced brakes and lights."
                async with connection.transaction():
                    await connection.execute(
                        "UPDATE listings.sale_listings SET description=%s WHERE id=%s",
                        (text, listing),
                    )
                    # A controlled future due time gates the worker so HTTP coverage
                    # failure can be checked deterministically before publication.
                    await connection.execute(
                        "UPDATE listings.embedding_generations SET retry_after=clock_timestamp()+interval '1 hour' WHERE listing_id=%s",
                        (listing,),
                    )
                changed = await (
                    await connection.execute(
                        "SELECT generation.generation_id,generation.state,(SELECT count(*) FROM listings.embedding_chunks AS chunk WHERE chunk.generation_id=generation.generation_id) AS chunks FROM listings.embedding_generations AS generation WHERE generation.listing_id=%s",
                        (listing,),
                    )
                ).fetchone()
                old_chunks = await (
                    await connection.execute(
                        "SELECT count(*) AS n FROM listings.embedding_chunks WHERE generation_id=%s",
                        (before["generation_id"],),
                    )
                ).fetchone()
                assert old_chunks["n"] == 0
                assert (
                    changed["generation_id"] != before["generation_id"]
                    and changed["state"] == "pending"
                    and changed["chunks"] == 0
                )
                assert (await request("hybrid")).status_code == 503
                keyword = await request("keyword")
                assert (
                    keyword.status_code == 200
                    and keyword.json()["items"][0]["description"] == text
                )
                await connection.execute(
                    "UPDATE listings.embedding_generations SET retry_after=clock_timestamp() WHERE listing_id=%s",
                    (listing,),
                )
            await until(lambda: dispatch.status.published == 1)
            async with control.connection() as connection:
                ready = await (
                    await connection.execute(
                        "SELECT state,source_fingerprint=listings.embedding_source_fingerprint(listing.title,listing.description) AS current FROM listings.embedding_generations AS generation JOIN listings.sale_listings AS listing ON listing.id=generation.listing_id WHERE listing.id=%s",
                        (listing,),
                    )
                ).fetchone()
                assert ready == {"state": "ready", "current": True}
            page = await request("hybrid")
            assert (
                page.status_code == 200
                and page.json()["items"][0]["description"] == text
            )
            observations.append(
                {
                    "case": "edit_reindex",
                    "old_chunks_removed": True,
                    "pending_hybrid": 503,
                    "pending_keyword": 200,
                    "dispatcher_publications": dispatch.status.published,
                    "current_source_ready": True,
                    "recovered_hybrid": 200,
                }
            )
            # Fail only the worker connection; read/helper ownership is separate.
            await dispatch._pool.close()
            await until(lambda: dispatch.status.state == "unavailable")
            assert (await request("keyword")).status_code == 200
            assert (await request("hybrid")).status_code == 200
            observations.append(
                {
                    "case": "worker_pool_failure",
                    "keyword": 200,
                    "complete_hybrid": 200,
                    "dispatcher": "unavailable",
                }
            )
        assert (
            runtime.helper.pid is None and runtime.pool.closed and dispatch._pool.closed
        )
    finally:
        runtime_module.SemanticHelper = old_factory
        main.settings = old_settings
        main.app.dependency_overrides.pop(require_caller, None)
        if hasattr(main.app.state, "listings_browse_identity"):
            del main.app.state.listings_browse_identity
        for helper in helpers:
            await helper.close()
        await control.close()
        stopped.set()
        watchdog.cancel()
        await asyncio.gather(watchdog, return_exceptions=True)
        live = rss(owned) if owned else {}
        result = {
            "observations": observations,
            "peak_api_helper_rss_bytes": peak,
            "max_simultaneous_helpers": simultaneous,
            "windows": sum(helper.windows_started for helper in helpers),
            "all_helpers_reaped": not any(pid in live for pid in owned),
            "faults": faults,
            "elapsed_seconds": time.monotonic() - started,
        }
        (cluster.directory / "worker-dispatch-result.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        assert not faults and result["all_helpers_reaped"]
        print(json.dumps(result), flush=True)


def main() -> None:
    """Accept only explicit isolated test settings; never an existing target."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--isolated-worker-dispatch", action="store_true")
    args = parser.parse_args()
    require_preview_settings(args.isolated_worker_dispatch)
    cluster = NativeCluster()
    print(f"Worker dispatcher evidence: {cluster.directory}", flush=True)
    try:
        cluster.start()
        asyncio.run(asyncio.wait_for(probe(cluster), 360))
    finally:
        cluster.stop()


if __name__ == "__main__":
    main()
