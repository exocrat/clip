"""Opt-in real native/model calibration; final labels/readiness are never accepted."""

import asyncio
from datetime import datetime, UTC
import json
import os
import time

import pytest
import psycopg

from app.domains.listings.embedding_client import SemanticHelper
from apps.api.tests.domains.listings.test_embedding_postgres import (
    connect,
    target,
    ROOT,
)
from scripts.evaluation.semantic.calibration import (
    FIXTURE,
    analyze,
    development_set,
    measure,
    read_json,
)
from scripts.evaluation.semantic.ipc_probe import rss


def test_native_search_calibration():
    """Use only a newly-created runner DB and previously installed pinned model."""
    value = target()
    if os.environ.get("LISTINGS_TEST_SEARCH_CALIBRATION") != "1":
        pytest.skip("Use native-checks.sh --search-calibration for real measurements")
    asyncio.run(asyncio.wait_for(exercise(value), 600))


async def base_counts(connection):
    """Fixture safety check: calibration never populates real base/domain jobs."""
    return await (await connection.execute("""SELECT
        (SELECT count(*) FROM identity.users) AS users,
        (SELECT count(*) FROM listings.sale_listings) AS listings,
        (SELECT count(*) FROM listings.embedding_generations) AS generations,
        (SELECT count(*) FROM listings.embedding_chunks) AS chunks,
        (SELECT count(*) FROM listings.embedding_pipelines) AS pipelines""")).fetchone()


async def exercise(value):
    """Bound one actual helper/30 windows/10min/512MiB, retain safe fixed metrics."""
    dataset = development_set(read_json(FIXTURE, 65536))
    helper = SemanticHelper(
        ROOT / ".tools/semantic/venv/bin/python", ROOT / ".tools/semantic/model"
    )
    parent = os.getpid()
    owned = set()
    peak = simultaneous = 0
    started = time.monotonic()
    stop = asyncio.Event()
    faults = []

    async def monitor():
        nonlocal peak, simultaneous
        while not stop.is_set():
            if helper.pid is not None:
                owned.add(helper.pid)
            rows = await asyncio.to_thread(rss, {parent, *owned})
            if parent not in rows:
                faults.append("host_measurement_missing")
                await helper.close()
                return
            live = [pid for pid in owned if pid in rows and rows[pid][0] == parent]
            total = rows[parent][1] + sum(rows[pid][1] for pid in live)
            peak = max(peak, total)
            simultaneous = max(simultaneous, len(live))
            if (
                total >= 512 * 1024 * 1024
                or len(live) > 1
                or helper.windows_started > 30
                or time.monotonic() - started > 600
            ):
                faults.append("resource_or_duration_bound")
                await helper.close()
                return
            await asyncio.sleep(0.05)

    watchdog = asyncio.create_task(monitor())
    try:
        # The connect guard runs before fixture writes/model startup. Only this
        # private autocommit session receives temporary calibration tables.
        async with await connect(value) as connection:
            await connection.execute("SET statement_timeout='3s'")
            await connection.execute("SET lock_timeout='1s'")
            before = await base_counts(connection)
            # A name collision must not delete an existing session table. This
            # sentinel belongs to this test, never to measurement/another writer.
            await connection.execute(
                "CREATE TEMPORARY TABLE calibration_chunks(sentinel integer)"
            )
            await connection.execute(
                "INSERT INTO pg_temp.calibration_chunks VALUES (7)"
            )
            with pytest.raises(psycopg.errors.DuplicateTable):
                await measure(connection, helper, dataset)
            sentinel = await (
                await connection.execute(
                    "SELECT sentinel FROM pg_temp.calibration_chunks"
                )
            ).fetchone()
            assert sentinel == {"sentinel": 7} and helper.starts == 0
            await connection.execute("DROP TABLE pg_temp.calibration_chunks")
            matrix = await measure(connection, helper, dataset)
            assert await base_counts(connection) == before
            absent = await (
                await connection.execute(
                    "SELECT to_regclass('pg_temp.calibration_listings') IS NULL AND to_regclass('pg_temp.calibration_chunks') IS NULL AS absent"
                )
            ).fetchone()
            assert absent == {"absent": True}
            result = analyze(dataset, matrix)
            assert len(result["comparisons"]) == 90 and result["policy_frozen"] is False
            by_query = {item["key"]: item["rows"] for item in matrix["queries"]}
            by_key = {item["key"]: item for item in by_query["vehicle"]}
            assert by_key["cycle"]["expanded"] and not by_key["cycle"]["original"]
            assert by_key["poster"]["expanded"]  # Deliberate lexical false-positive.
            telescope = {item["key"]: item for item in by_query["literal_telescope"]}
            assert telescope["telescope_bundle"][
                "original"
            ]  # Full long ending retained by FTS.
    finally:
        await helper.close()
        stop.set()
        await watchdog
    assert not faults and helper.windows_started <= 30 and helper.starts == 1
    remaining = rss({parent, *owned})
    assert owned and all(pid not in remaining for pid in owned)
    metadata = {
        "captured_at": datetime.now(UTC).isoformat(),
        "development_only": True,
        "human_review_verified": False,
        "final_labels_used": False,
        "nfr_accepted": False,
        "policy_frozen": False,
        "fixture_fingerprint": dataset.fingerprint,
        "listings": len(dataset.document["listings"]),
        "queries": len(dataset.document["queries"]),
        "model_windows": helper.windows_started,
        "helper_starts": helper.starts,
        "max_simultaneous_owned_helpers": simultaneous,
        "sampled_peak_host_helper_rss_bytes": peak,
        "all_owned_helpers_reaped": True,
        "base_domain_counts_unchanged": True,
        "temporary_tables_removed": True,
        "elapsed_seconds": time.monotonic() - started,
    }
    folder = (
        ROOT
        / ".tools/semantic/calibration-probes"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    )
    folder.mkdir(parents=True, exist_ok=False)
    for name, document in [
        ("matrix", matrix),
        ("analysis", result),
        ("result", metadata),
    ]:
        (folder / (name + ".json")).write_text(json.dumps(document, indent=2) + "\n")
