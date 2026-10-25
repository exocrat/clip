"""Opt-in actual app.main lifespan probe on a newly owned native Search database.

Only caller/eligibility are synthetic. Existing bootstrap builds controlled real
vectors before the actual normal app opens its own helper/pools. No live server,
existing DB target, downloads, pipeline activation by app startup, or deployment.
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import sys
import time

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
from apps.api.tests.domains.search.native_preview import (  # noqa: E402
    NativeCluster,
    PreviewIdentity,
    CALLER,
    bootstrap,
)
from scripts.evaluation.semantic.ipc_probe import rss  # noqa: E402


async def probe(cluster: NativeCluster) -> None:
    """Bound6min/40windows/512MiB and one simultaneous real child; verify3states."""
    from app import main

    helpers = []
    owned = set()
    peak = 0
    simultaneous = 0
    faults = []
    observations = []
    started = time.monotonic()
    stopped = asyncio.Event()
    parent = os.getpid()
    task = asyncio.current_task()
    interpreter = ROOT / ".tools/semantic/venv/bin/python"
    model = ROOT / ".tools/semantic/model"
    old_factory = runtime_module.SemanticHelper
    old_settings = main.settings

    class ObservedHelper(SemanticHelper):
        """Instrumentation only; every start/encode/close uses the real implementation."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            helpers.append(self)

    async def monitor():
        nonlocal peak, simultaneous
        while not stopped.is_set():
            for helper in helpers:
                if helper.pid is not None:
                    owned.add(helper.pid)
            rows = await asyncio.to_thread(rss, {parent, *owned})
            active = [pid for pid in owned if pid in rows and rows[pid][0] == parent]
            peak = max(
                peak, rows.get(parent, (0, 0))[1] + sum(rows[pid][1] for pid in active)
            )
            simultaneous = max(simultaneous, len(active))
            if (
                parent not in rows
                or peak >= 512 * 1024 * 1024
                or simultaneous > 1
                or sum(helper.windows_started for helper in helpers) > 40
                or time.monotonic() - started > 360
            ):
                faults.append("supervision_limit")
                assert task is not None
                task.cancel()
                return
            await asyncio.sleep(0.05)

    async def request(query):
        """Use actual app routes/service/store with explicit test-only caller overrides."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app), base_url="http://127.0.0.1"
        ) as client:
            response = await client.get("/listings", params=query)
            assert response.headers["cache-control"] == "private, no-store"
            return response

    async def synthetic_eligible(user_id):
        return await PreviewIdentity().account_is_eligible(user_id)

    watchdog = asyncio.create_task(monitor())
    bootstrap_pool = AsyncConnectionPool(
        cluster.url,
        kwargs={"autocommit": True, "row_factory": dict_row},
        min_size=1,
        max_size=1,
        timeout=5,
        open=False,
    )
    bootstrap_helper = ObservedHelper(interpreter, model)
    try:
        await bootstrap_pool.open()
        await bootstrap_pool.wait(timeout=5)
        await bootstrap(bootstrap_pool, bootstrap_helper)
        await bootstrap_helper.close()
        await bootstrap_pool.close()
        runtime_module.SemanticHelper = ObservedHelper
        main.app.dependency_overrides[require_caller] = lambda: CallerContext(
            CALLER, "regular", datetime.now(UTC) + timedelta(minutes=1)
        )
        # This binding is confined to this explicit test process, not app startup.
        from types import SimpleNamespace

        main.app.state.listings_browse_identity = SimpleNamespace(
            account_is_eligible=synthetic_eligible
        )
        for mode in ("disabled", "ready", "unavailable"):
            enabled = mode != "disabled"
            options = (
                {
                    "hybrid_search_enabled": True,
                    "hybrid_search_interpreter": (
                        interpreter
                        if mode == "ready"
                        else cluster.directory / "missing-python"
                    ),
                    "hybrid_search_model_dir": model,
                }
                if enabled
                else {}
            )
            main.settings = Settings(
                environment="test", database_url=cluster.url, **options
            )
            async with main.lifespan(main.app):
                runtime = main.app.state.search_runtime
                store = main.app.state.listings_store
                assert runtime.state == mode
                assert store._pool is not runtime.pool
                async with store._pool.connection() as connection:
                    assert not connection.autocommit
                if mode == "ready":
                    async with runtime.pool.connection() as connection:
                        assert connection.autocommit
                    for text in (
                        "cycle",
                        "bicyle",
                        "vehicle",
                        "wheeled vehicle",
                        "keep food cold",
                    ):
                        response = await request(
                            {"q": text, "search_mode": "hybrid", "sort": "relevance"}
                        )
                        assert response.status_code == 200
                        titles = [item["title"] for item in response.json()["items"]]
                        expected = (
                            "Compact refrigerator"
                            if text == "keep food cold"
                            else "Campus bicycle"
                        )
                        assert expected in titles, (text, titles)
                        observations.append(
                            {"runtime": mode, "query": text, "titles": titles}
                        )
                else:
                    assert (
                        await request({"q": "cycle", "search_mode": "hybrid"})
                    ).status_code == 503
                assert (await request({"q": "cycle"})).status_code == 200
                assert (await request({"search_mode": "hybrid"})).status_code == 200
            assert store._pool.closed
            if runtime.pool is not None:
                assert runtime.pool.closed
                assert runtime.helper.pid is None
            observations.append(
                {
                    "runtime": mode,
                    "keyword": 200,
                    "blank_hybrid": 200,
                    "nonblank_hybrid": 200 if mode == "ready" else 503,
                    "cleanup": "closed",
                }
            )
    finally:
        runtime_module.SemanticHelper = old_factory
        main.settings = old_settings
        main.app.dependency_overrides.pop(require_caller, None)
        if hasattr(main.app.state, "listings_browse_identity"):
            del main.app.state.listings_browse_identity
        for helper in helpers:
            await helper.close()
        await bootstrap_pool.close()
        stopped.set()
        watchdog.cancel()
        await asyncio.gather(watchdog, return_exceptions=True)
        live = rss(owned) if owned else {}
        reaped = not any(pid in live for pid in owned)
        result = {
            "observations": observations,
            "peak_api_helper_rss_bytes": peak,
            "max_simultaneous_helpers": simultaneous,
            "windows": sum(helper.windows_started for helper in helpers),
            "all_helpers_reaped": reaped,
            "faults": faults,
            "elapsed_seconds": time.monotonic() - started,
        }
        (cluster.directory / "normal-runtime-result.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        assert reaped and not faults
        print(json.dumps(result), flush=True)


def main() -> None:
    """Only new private fixed native target and existing offline artifacts are allowed."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--isolated-normal-search", action="store_true")
    args = parser.parse_args()
    require_preview_settings(args.isolated_normal_search)
    cluster = NativeCluster()
    print(f"Normal API lifecycle evidence: {cluster.directory}", flush=True)
    try:
        cluster.start()
        asyncio.run(asyncio.wait_for(probe(cluster), 360))
    finally:
        cluster.stop()


if __name__ == "__main__":
    main()
