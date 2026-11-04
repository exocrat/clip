"""Real disposable PostgreSQL bridge checks; actual model requires explicit opt-in.

Reuses the native suite's guarded target/controlled fixtures. Fault pipes prove
failure handling only; the separately opted-in model test proves real persistence.
No existing/shared database or application startup accepts this test flag.
"""

import asyncio
from datetime import datetime, UTC
import json
import os
from pathlib import Path
import time

import pytest
from psycopg.pq import TransactionStatus

from app.domains.listings.embedding_client import (
    SemanticHelper,
    HelperLimits,
    HelperBusy,
)
from app.domains.listings.embedding_store import EmbeddingStore
from app.domains.listings.embedding_worker import (
    EmbeddingWorker,
    WorkerLimits,
    WorkerUnavailable,
)
from app.domains.listings.embedding_types import default_pipeline_spec
from apps.api.tests.domains.listings.test_embedding_postgres import (
    connect,
    target,
    seed_listing,
    retire,
    ROOT,
    math_pipeline,
)
from apps.api.tests.domains.listings.test_embedding_client import FaultClient


def test_runtime_column_grants_allow_claim_and_publication():
    """Catch the deployed missing-grant failure using a real restricted local role."""
    asyncio.run(exercise_runtime_grants(target()))


async def exercise_runtime_grants(value):
    """Apply only the proposed worker columns in the owned disposable database.

    Coordinate vectors prove permission/transaction behavior, not search quality.
    The target guard refuses every retained or remote database before any DDL.
    """
    from psycopg.errors import InsufficientPrivilege
    from apps.api.tests.domains.listings.test_embedding_postgres import PARTS

    async with await connect(value) as connection:
        role = "clip_test_marketplace_app"
        assert (
            await (
                await connection.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)
                )
            ).fetchone()
            is None
        )
        store = EmbeddingStore(connection)
        spec = math_pipeline(97651)
        await store.register(spec)
        await store.set_state(spec, "building")
        listing = None
        created = False
        try:
            async with connection.transaction():
                listing = await seed_listing(connection, 97651)
            await connection.execute(
                "CREATE ROLE clip_test_marketplace_app NOLOGIN NOINHERIT"
            )
            created = True
            await connection.execute(
                "GRANT USAGE ON SCHEMA listings TO clip_test_marketplace_app"
            )
            await connection.execute(
                "GRANT SELECT ON listings.sale_listings,listings.embedding_pipelines,listings.embedding_generations,listings.embedding_chunks TO clip_test_marketplace_app"
            )
            await connection.execute(
                "GRANT UPDATE(updated_at) ON listings.sale_listings TO clip_test_marketplace_app"
            )
            await connection.execute("SET ROLE clip_test_marketplace_app")
            with pytest.raises(InsufficientPrivilege):
                await store.claim(spec)
            await connection.execute("RESET ROLE")
            await connection.execute(
                (
                    ROOT / "database/roles/marketplace-embedding-worker.sql.proposed"
                ).read_text()
            )
            await connection.execute("SET ROLE clip_test_marketplace_app")
            job = await store.claim(spec)
            assert job is not None and job.listing_id == listing
            assert await store.complete(job, PARTS, 1)
            row = await (
                await connection.execute(
                    "SELECT state FROM listings.embedding_generations WHERE generation_id=%s",
                    (job.generation_id,),
                )
            ).fetchone()
            assert row == {"state": "ready"}
        finally:
            await connection.execute("RESET ROLE")
            if created:
                await connection.execute("DROP OWNED BY clip_test_marketplace_app")
                await connection.execute("DROP ROLE clip_test_marketplace_app")
            if listing is not None:
                async with connection.transaction():
                    await retire(connection, listing)
            await store.set_state(spec, "retired")


async def generation(connection, listing):
    """Read only this fixture's current durable job metadata, never log its source."""
    return await (
        await connection.execute(
            "SELECT * FROM listings.embedding_generations WHERE listing_id=%s AND pipeline_id=%s",
            (listing, default_pipeline_spec().pipeline_id),
        )
    ).fetchone()


async def make_due(connection, listing):
    """Advance only controlled job scheduling, without weakening production clocks."""
    await connection.execute(
        "UPDATE listings.embedding_generations SET retry_after=clock_timestamp()-interval '1 second' WHERE listing_id=%s",
        (listing,),
    )


async def fixture(connection, seed):
    """Commit one synthetic source; do not reconcile or compute other fixture rows."""
    store = EmbeddingStore(connection)
    spec = default_pipeline_spec()
    await store.register(spec)
    await store.set_state(spec, "building")
    async with connection.transaction():
        listing = await seed_listing(connection, seed)
    return listing


def test_native_worker_faults_and_recovery(tmp_path):
    asyncio.run(exercise_faults(target(), tmp_path))


async def exercise_faults(value, tmp_path):
    """Real SQL with controlled pipe faults: retry, defer, cancellation and reclaim."""
    async with await connect(value) as connection:
        store = EmbeddingStore(connection)
        other = math_pipeline(94021)
        await store.register(other)
        await store.set_state(other, "building")
        listing = await fixture(connection, 94021)
        try:
            for mode, code in [
                ("hang", "timeout"),
                ("bad_coverage", "invalid_vectors"),
                ("crash_once", "helper_unavailable"),
            ]:
                client = FaultClient(
                    tmp_path,
                    mode,
                    HelperLimits(
                        startup=1,
                        inference=0.2,
                        request=0.4,
                        cleanup=1,
                        restart_delay=0.01,
                    ),
                )
                try:
                    await make_due(connection, listing)
                    assert (
                        await EmbeddingWorker(
                            store,
                            client,
                            limits=WorkerLimits(work=0.15 if mode == "hang" else 2),
                        ).run_one()
                        == "failure_recorded"
                    )
                    row = await generation(connection, listing)
                    assert row["state"] == "pending" and row["failure_code"] == code
                    assert row["lease_token"] is None and row["title_count"] == 0
                    assert client.pid is None
                finally:
                    await client.close()
            row = await generation(connection, listing)
            assert row["attempts"] == 3
            untouched = await (
                await connection.execute(
                    "SELECT state,attempts FROM listings.embedding_generations WHERE listing_id=%s AND pipeline_id=%s",
                    (listing, other.pipeline_id),
                )
            ).fetchone()
            assert untouched == {"state": "pending", "attempts": 0}

            class FullQueue:
                """Capacity-only fixture; never supplies fake success or ranking."""

                spec = default_pipeline_spec()

                async def encode_listing(self, title, description):
                    raise HelperBusy("capacity")

            await make_due(connection, listing)
            assert await EmbeddingWorker(store, FullQueue()).run_one() == "deferred"
            row = await generation(connection, listing)
            assert row["attempts"] == 3 and row["failure_code"] is None
            assert row["state"] == "pending" and row["retry_after"] > datetime.now(UTC)
            await make_due(connection, listing)
            client = FaultClient(
                tmp_path,
                "hang",
                HelperLimits(
                    startup=1, inference=2, request=3, cleanup=1, restart_delay=0.01
                ),
            )
            task = asyncio.create_task(EmbeddingWorker(store, client).run_one())
            try:
                async with asyncio.timeout(3):
                    while client.windows_started < 2:
                        await asyncio.sleep(0.001)
                before = await generation(connection, listing)
                assert (
                    before["state"] == "leased"
                    and connection.info.transaction_status == TransactionStatus.IDLE
                )
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
                after = await generation(connection, listing)
                assert (
                    after["lease_token"] == before["lease_token"]
                    and after["state"] == "leased"
                )
                assert client.pid is None
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                await client.close()
            await connection.execute(
                "UPDATE listings.embedding_generations SET lease_until=clock_timestamp()-interval '1 second' WHERE listing_id=%s AND state='leased'",
                (listing,),
            )
            client = FaultClient(tmp_path, "ok")
            try:
                assert await EmbeddingWorker(store, client).run_one() == "published"
                row = await generation(connection, listing)
                assert row["state"] == "ready" and row["attempts"] == 5
                assert row["lease_token"] is None and row["description_count"] == 1
            finally:
                await client.close()
        finally:
            async with connection.transaction():
                await retire(connection, listing)
            await store.set_state(other, "retired")
            await connection.execute(
                "DELETE FROM listings.embedding_pipelines WHERE pipeline_id=%s",
                (other.pipeline_id,),
            )


class GateEncoder:
    """Pause after actual inference so committed mutations precede publication."""

    def __init__(self, helper):
        self.helper = helper
        self.spec = helper.spec
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.output = None

    async def encode_listing(self, title, description):
        self.output = await self.helper.encode_listing(title, description)
        self.entered.set()
        await self.release.wait()
        return self.output


async def gated_run(store, helper, observer, listing, mutation):
    """Prove claim committed/no listing lock, mutate, then inspect actual fencing."""
    gate = GateEncoder(helper)
    task = asyncio.create_task(EmbeddingWorker(store, gate).run_one())
    try:
        await asyncio.wait_for(gate.entered.wait(), 10)
        assert store.connection.info.transaction_status == TransactionStatus.IDLE
        async with observer.transaction():
            await observer.execute(
                "SELECT id FROM listings.sale_listings WHERE id=%s FOR UPDATE NOWAIT",
                (listing,),
            )
            await mutation(observer, listing)
        gate.release.set()
        return await asyncio.wait_for(task, 5), gate.output
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def test_native_worker_actual_model():
    """Opt-in only, existing fixed model/interpreter; never downloads dependencies."""
    value = target()
    if os.environ.get("LISTINGS_TEST_EMBEDDING_WORKER_MODEL") != "1":
        pytest.skip("Use native-checks.sh --embedding-worker for actual model bridge")
    asyncio.run(asyncio.wait_for(exercise_actual(value), 600))


class CrashOnceHelper(SemanticHelper):
    """Kill only this real model child after its first armed progress frame.

    No fake frames/vectors are injected: the real pipe read provides the barrier.
    The ordinary client must discard/reap the crashed stream before restarting.
    """

    armed = False

    async def _line(self, timeout):
        frame = await super()._line(timeout)
        if self.armed and frame.get("kind") == "progress":
            self.armed = False
            assert self._process is not None and self.pid == self._process.pid
            self._process.kill()
        return frame


async def exercise_actual(value):
    """Bound <=30 windows/one helper/512MiB host+helper; retain safe metrics only."""
    from scripts.evaluation.semantic.ipc_probe import rss

    client = CrashOnceHelper(
        ROOT / ".tools/semantic/venv/bin/python", ROOT / ".tools/semantic/model"
    )
    started = time.monotonic()
    parent = os.getpid()
    owned = set()
    peak = 0
    stop = asyncio.Event()
    faults = []

    async def monitor():
        nonlocal peak
        while not stop.is_set():
            if client.pid is not None:
                owned.add(client.pid)
            rows = await asyncio.to_thread(rss, {parent, *owned})
            if parent not in rows:
                faults.append("process_missing")
                await client.close()
                return
            live = [pid for pid in owned if pid in rows and rows[pid][0] == parent]
            total = sum(rows[pid][1] for pid in [parent, *live] if pid in rows)
            peak = max(peak, total)
            if (
                total >= 512 * 1024 * 1024
                or len(live) > 1
                or client.windows_started > 30
                or time.monotonic() - started > 600
            ):
                faults.append("resource_bound")
                await client.close()
                return
            await asyncio.sleep(0.05)

    watchdog = asyncio.create_task(monitor())
    try:
        async with await connect(value) as connection, await connect(value) as observer:
            store = EmbeddingStore(connection)
            listing = await fixture(connection, 94022)
            try:
                await connection.execute(
                    "UPDATE listings.sale_listings SET description=%s WHERE id=%s",
                    ("ordinary filler " * 300 + " collectible telescope", listing),
                )

                # Gate the first successful publication to inspect both the idle
                # connection and exact output later stored as PostgreSQL real[].
                async def no_change(db, item):
                    pass

                result, output = await gated_run(
                    store, client, observer, listing, no_change
                )
                assert (
                    result == "published"
                    and len(output.ranges) == 4
                    and output.description_tokens == 903
                )
                vectors = await (
                    await observer.execute(
                        "SELECT part_kind,ordinal,vector FROM listings.embedding_chunks WHERE generation_id=(SELECT generation_id FROM listings.embedding_generations WHERE listing_id=%s AND pipeline_id=%s) ORDER BY part_kind,ordinal",
                        (listing, client.spec.pipeline_id),
                    )
                ).fetchall()
                expected = {
                    (part.kind, part.ordinal): part.vector for part in output.parts
                }
                assert len(vectors) == 5
                for row in vectors:
                    assert row["vector"] == pytest.approx(
                        expected[(row["part_kind"], row["ordinal"])], abs=1e-7
                    )
                await connection.execute(
                    "UPDATE listings.sale_listings SET description='Controlled crash recovery source' WHERE id=%s",
                    (listing,),
                )
                client.armed = True
                assert (
                    await EmbeddingWorker(store, client).run_one() == "failure_recorded"
                )
                crashed = await generation(observer, listing)
                assert (
                    crashed["state"] == "pending"
                    and crashed["failure_code"] == "helper_unavailable"
                )
                assert client.pid is None
                await make_due(connection, listing)
                assert await EmbeddingWorker(store, client).run_one() == "published"
                await connection.execute(
                    "UPDATE listings.sale_listings SET description='Controlled short bridge source' WHERE id=%s",
                    (listing,),
                )

                async def aba(db, item):
                    await db.execute(
                        "UPDATE listings.sale_listings SET description='Temporary controlled source' WHERE id=%s",
                        (item,),
                    )
                    await db.execute(
                        "UPDATE listings.sale_listings SET description='Controlled short bridge source' WHERE id=%s",
                        (item,),
                    )

                assert (await gated_run(store, client, observer, listing, aba))[
                    0
                ] == "stale"
                assert (await generation(observer, listing))["state"] == "pending"
                assert await EmbeddingWorker(store, client).run_one() == "published"
                # A nontext edit preserves the receipt and therefore may publish.
                await connection.execute(
                    "UPDATE listings.sale_listings SET description='Controlled price change source' WHERE id=%s",
                    (listing,),
                )

                async def price(db, item):
                    await db.execute(
                        "UPDATE listings.sale_listings SET asking_price_paise=12300 WHERE id=%s",
                        (item,),
                    )

                assert (await gated_run(store, client, observer, listing, price))[
                    0
                ] == "published"
                await connection.execute(
                    "UPDATE listings.sale_listings SET description='Controlled retirement source' WHERE id=%s",
                    (listing,),
                )
                assert (await gated_run(store, client, observer, listing, retire))[
                    0
                ] == "stale"
                assert await generation(observer, listing) is None
                assert await EmbeddingWorker(store, client).run_one() == "idle"
            finally:
                async with connection.transaction():
                    row = await (
                        await connection.execute(
                            "SELECT retired_at FROM listings.sale_listings WHERE id=%s",
                            (listing,),
                        )
                    ).fetchone()
                    if row["retired_at"] is None:
                        await retire(connection, listing)
    finally:
        await client.close()
        stop.set()
        await watchdog
    assert not faults and client.windows_started <= 30 and client.starts == 2
    remaining = rss({parent, *owned})
    assert owned and all(pid not in remaining for pid in owned)
    result = {
        "captured_at": datetime.now(UTC).isoformat(),
        "isolated_only": True,
        "actual_model": True,
        "public_activation": False,
        "nfr_accepted": False,
        "cases": [
            "full_long_source_publication",
            "idle_connection_and_unlocked_listing",
            "persisted_vectors_match_encoder",
            "actual_helper_crash_records_failure",
            "new_request_restarts_and_recovers",
            "ABA_rejects_old_generation",
            "fresh_generation_recovers",
            "nontext_change_preserves_work",
            "retirement_rejects_publication",
            "no_job_idle",
        ],
        "windows": client.windows_started,
        "helper_starts": client.starts,
        "sampled_peak_host_helper_rss_bytes": peak,
        "owned_helpers_reaped": True,
        "elapsed_seconds": time.monotonic() - started,
    }
    folder = (
        ROOT
        / ".tools/semantic/worker-probes"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    )
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
