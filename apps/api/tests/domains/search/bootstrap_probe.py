"""Real operator CLI/bootstrap/activation probe; fresh private native DB only.

Only identity is a double. Sources, unavailable coverage, real background worker,
model, operator subprocess target guards and request-time coverage are exercised.
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
from app.domains.listings.embedding_store import EmbeddingStore  # noqa: E402
from app.domains.listings.embedding_types import (
    default_pipeline_spec,
    pipeline_spec,
)  # noqa: E402
import app.domains.listings.search_runtime as runtime_module  # noqa: E402
from apps.api.tests.domains.search.browser_preview import (
    require_preview_settings,
)  # noqa: E402
from apps.api.tests.domains.search.native_preview import (
    NativeCluster,
    PreviewIdentity,
    SOURCES,
)  # noqa: E402
from apps.api.tests.domains.listings.test_embedding_postgres import (
    seed_listing,
)  # noqa: E402
from apps.api.tests.domains.search.worker_dispatch_probe import until  # noqa: E402
from scripts.evaluation.semantic.ipc_probe import rss  # noqa: E402
from data.generators.preview import stable_id  # noqa: E402
from uuid import UUID  # noqa: E402

SEED = 95200
CALLER = UUID(stable_id(SEED, "user_placeholder", 1))


async def probe(cluster: NativeCluster) -> None:
    """<=10min/40windows/1simultaneous helper/512MiB sampled API+helper, no listener."""
    from app import main

    helpers = []
    owned = set()
    peak = 0
    simultaneous = 0
    faults = []
    observations = []
    stopped = asyncio.Event()
    started = time.monotonic()
    owner = asyncio.current_task()
    parent = os.getpid()
    spec = default_pipeline_spec()
    old_settings = main.settings
    old_factory = runtime_module.SemanticHelper

    class ObservedHelper(SemanticHelper):
        """Measure actual helper lifecycle; no inference/process implementation replaced."""

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
                or time.monotonic() - started > 600
            ):
                faults.append("supervision_limit")
                assert owner is not None
                owner.cancel()
                return
            await asyncio.sleep(0.05)

    async def command(action, *, batch=None, success=True):
        """Run the real target-bound operator process with this exact new DB secret."""
        argv = [
            sys.executable,
            str(ROOT / "scripts/search_pipeline.py"),
            action,
            "--expected-host",
            str(cluster.socket),
            "--expected-port",
            "55438",
            "--expected-database",
            "clip_test_ci",
            "--expected-role",
            "clip_ci",
            "--pipeline-id",
            spec.pipeline_id.hex(),
        ]
        if action != "status":
            argv.append("--execute")
        if batch is not None:
            argv.extend(["--batch-size", str(batch)])
        child = await asyncio.create_subprocess_exec(
            *argv,
            cwd=ROOT,
            env={
                "PATH": "/usr/bin:/bin",
                "CLIP_DATABASE_URL": cluster.url,
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(child.communicate(), 15)
        except BaseException:
            if child.returncode is None:
                child.kill()
            await child.wait()
            raise
        assert child.returncode == (0 if success else 2), (
            action,
            child.returncode,
            stderr.decode(),
        )
        return json.loads((stdout if success else stderr).decode())

    async def request(mode):
        """Use the actual normal API store/query/helper under test-only caller context."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app), base_url="http://127.0.0.1"
        ) as client:
            response = await client.get(
                "/listings",
                params={"q": "cycle", "search_mode": mode, "sort": "relevance"},
            )
            assert response.headers["cache-control"] == "private, no-store"
            return response

    async def eligible(user_id):
        return user_id == CALLER

    control = AsyncConnectionPool(
        cluster.url,
        kwargs={"autocommit": True, "row_factory": dict_row},
        min_size=1,
        max_size=1,
        open=False,
    )
    watchdog = asyncio.create_task(monitor())
    runtime_module.SemanticHelper = ObservedHelper
    main.settings = Settings(
        environment="test",
        database_url=cluster.url,
        hybrid_search_enabled=True,
        hybrid_worker_enabled=True,
        hybrid_search_interpreter=ROOT / ".tools/semantic/venv/bin/python",
        hybrid_search_model_dir=ROOT / ".tools/semantic/model",
    )
    main.app.dependency_overrides[require_caller] = lambda: CallerContext(
        CALLER, "regular", datetime.now(UTC) + timedelta(minutes=10)
    )
    main.app.state.listings_browse_identity = SimpleNamespace(
        account_is_eligible=eligible
    )
    try:
        await control.open()
        await control.wait(timeout=5)
        absent = await command("status")
        assert absent["state"] == "absent" and not absent["complete"]
        async with control.connection() as connection:
            store = EmbeddingStore(connection)
            # Empty alternative metadata space exercises conflict refusal only;
            # no fake vectors/model or real listing is assigned to this space.
            other = pipeline_spec({**spec.encoding, "model_revision": "a" * 40})
            await store.register(other)
            await store.set_state(other, "serving")
            assert (await command("prepare"))["state"] == "building"
            assert (await command("activate", success=False))[
                "error"
            ] == "conflicting_serving_pipeline"
            await store.set_state(other, "retired")
            # Test-only reset to planned precedes all source inserts; production
            # prepare never demotes a building/serving pipeline.
            await store.set_state(spec, "planned")
            ids = []
            for index, (title, description, category) in enumerate(SOURCES):
                async with connection.transaction():
                    listing = await seed_listing(connection, SEED + index)
                    await connection.execute(
                        "UPDATE listings.sale_listings SET title=%s,description=%s,category_id=(SELECT id FROM listings.categories WHERE code=%s),availability=%s,available_from=clock_timestamp()-interval '1 day',available_until=NULL WHERE id=%s",
                        (
                            title,
                            description,
                            category,
                            "unavailable" if index == 2 else "available",
                            listing,
                        ),
                    )
                    ids.append(listing)
        status = await command("status")
        assert status["live"] == 3 and status["missing"] == 3
        assert (await command("prepare"))["state"] == "building"
        assert (await command("activate", success=False))[
            "error"
        ] == "coverage_incomplete"
        assert (await command("queue", batch=1))["queued"] == 1
        assert (await command("queue", batch=2))["queued"] == 2
        async with control.connection() as connection:
            before = await (
                await connection.execute(
                    "SELECT listing_id,generation_id FROM listings.embedding_generations WHERE pipeline_id=%s ORDER BY listing_id",
                    (spec.pipeline_id,),
                )
            ).fetchall()
            assert (await command("queue", batch=3))["queued"] == 0
            assert (await command("prepare"))["pending"] == 3
            after = await (
                await connection.execute(
                    "SELECT listing_id,generation_id FROM listings.embedding_generations WHERE pipeline_id=%s ORDER BY listing_id",
                    (spec.pipeline_id,),
                )
            ).fetchall()
            assert before == after
            await connection.execute(
                "UPDATE listings.embedding_generations SET state='failed',attempts=5,failure_code='helper_unavailable' WHERE listing_id=%s AND pipeline_id=%s",
                (ids[2], spec.pipeline_id),
            )
            assert (await command("status"))["failed"] == 1
            assert (await command("activate", success=False))[
                "error"
            ] == "coverage_incomplete"
            assert (await command("queue", batch=3))["queued"] == 0
            assert (await command("status"))["failed"] == 1
            assert await EmbeddingStore(connection).retry_failed(spec, ids[2])
            job = await EmbeddingStore(connection).claim(spec)
            assert job is not None
            assert (await command("status"))["leased"] == 1
            assert (await command("activate", success=False))[
                "error"
            ] == "coverage_incomplete"
            assert await EmbeddingStore(connection).defer(job)
            await connection.execute(
                "UPDATE listings.embedding_generations SET retry_after=clock_timestamp() WHERE pipeline_id=%s",
                (spec.pipeline_id,),
            )
        observations.append(
            {
                "case": "prepare_queue_refusals",
                "full_live_scope": 3,
                "unavailable_included": True,
                "bounded_batches": [1, 2, 0],
                "resume_preserved_generations": True,
                "missing_pending_failed_leased_blocked": True,
                "failed_not_reset": True,
                "conflicting_serving_refused": True,
            }
        )
        async with main.lifespan(main.app):
            runtime = main.app.state.search_runtime
            await until(lambda: runtime.dispatcher.status.published == 3)
            ready = await command("status")
            assert (
                ready["state"] == "building"
                and ready["complete"]
                and ready["ready"] == 3
            )
            assert (await request("hybrid")).status_code == 503
            assert (await request("keyword")).status_code == 200
            text = "A pedal powered bicycle with recently serviced brakes and lights for campus commuting."
            async with control.connection() as connection:
                async with connection.transaction():
                    await connection.execute(
                        "UPDATE listings.sale_listings SET description=%s WHERE id=%s",
                        (text, ids[0]),
                    )
                    await connection.execute(
                        "UPDATE listings.embedding_generations SET retry_after=clock_timestamp()+interval '1 hour' WHERE listing_id=%s AND pipeline_id=%s",
                        (ids[0], spec.pipeline_id),
                    )
                    activation = await command("activate")
                    assert activation["state"] == "serving" and activation["complete"]
                incomplete = await command("status")
                assert (
                    incomplete["state"] == "serving"
                    and not incomplete["complete"]
                    and incomplete["pending"] == 1
                )
                assert (await request("hybrid")).status_code == 503
                assert (await request("keyword")).status_code == 200
                assert (await command("activate", success=False))[
                    "error"
                ] == "coverage_incomplete"
                await connection.execute(
                    "UPDATE listings.embedding_generations SET retry_after=clock_timestamp() WHERE listing_id=%s AND pipeline_id=%s",
                    (ids[0], spec.pipeline_id),
                )
            await until(lambda: runtime.dispatcher.status.published == 4)
            activated = await command("activate")
            assert activated["state"] == "serving" and activated["complete"]
            assert (await command("activate"))["state"] == "serving"
            assert (await command("prepare"))["state"] == "serving"
            page = await request("hybrid")
            assert (
                page.status_code == 200
                and page.json()["items"][0]["description"] == text
            )
            observations.append(
                {
                    "case": "real_worker_activation_and_concurrent_edit",
                    "initial_ready": 3,
                    "building_hybrid": 503,
                    "activation_old_snapshot": True,
                    "later_committed_edit_status_incomplete": True,
                    "later_edit_hybrid": 503,
                    "keyword": 200,
                    "current_recovery": True,
                    "repeat_preserves_serving": True,
                    "final_hybrid": 200,
                }
            )
        assert (
            runtime.helper.pid is None
            and runtime.pool.closed
            and runtime.dispatcher._pool.closed
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
        (cluster.directory / "bootstrap-result.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        assert not faults and result["all_helpers_reaped"]
        print(json.dumps(result), flush=True)


def main() -> None:
    """Only explicit isolated settings and a newly owned private target are allowed."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--isolated-bootstrap", action="store_true")
    args = parser.parse_args()
    require_preview_settings(args.isolated_bootstrap)
    cluster = NativeCluster()
    print(f"Bootstrap evidence: {cluster.directory}", flush=True)
    try:
        cluster.start()
        asyncio.run(asyncio.wait_for(probe(cluster), 600))
    finally:
        cluster.stop()


if __name__ == "__main__":
    main()
